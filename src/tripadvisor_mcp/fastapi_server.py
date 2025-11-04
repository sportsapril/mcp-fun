"""
FastAPI HTTP Bridge for TripAdvisor MCP Server

This provides an HTTP REST API wrapper around the tripadvisor_mcp
to enable integration with Supabase Edge Functions and other HTTP clients.
"""

import asyncio
import logging
from typing import Any, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Import the search function from the MCP server
from .server import search_tripadvisor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("tripadvisor-fastapi")

# Initialize FastAPI app
app = FastAPI(
    title="TripAdvisor MCP HTTP Bridge",
    description="HTTP REST API wrapper for TripAdvisor MCP server",
    version="1.0.0",
)

# Enable CORS for Supabase Edge Functions
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to your Supabase domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request/Response Models

class SearchRequest(BaseModel):
    """Request model for single search query"""
    query: str = Field(..., description="Search query (e.g., 'restaurants', 'attractions', 'hotels')")
    location: str = Field(..., description="City name in English or Chinese")
    max_results: int = Field(default=10, ge=1, le=50, description="Maximum results to return")


class EntitySearchRequest(BaseModel):
    """Request model for batch entity searches"""
    entities: list[dict[str, str]] = Field(
        ...,
        description="List of entities with name, type, and city",
        example=[
            {"name": "筑地市场", "type": "attraction", "city": "Tokyo"},
            {"name": "Sushi Dai", "type": "restaurant", "city": "Tokyo"}
        ]
    )
    max_results_per_entity: int = Field(default=3, ge=1, le=10)


class SearchResponse(BaseModel):
    """Response model for search results"""
    success: bool
    query: Optional[str] = None
    location: Optional[str] = None
    category: Optional[str] = None
    results_count: int = 0
    results: list[dict[str, Any]] = []
    error: Optional[str] = None


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    service: str
    version: str


# API Endpoints

@app.get("/", response_model=HealthResponse)
async def root():
    """Root endpoint - health check"""
    return {
        "status": "healthy",
        "service": "TripAdvisor MCP HTTP Bridge",
        "version": "1.0.0"
    }


@app.get("/health", response_model=HealthResponse)
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "TripAdvisor MCP HTTP Bridge",
        "version": "1.0.0"
    }


@app.post("/search", response_model=SearchResponse)
async def search(request: SearchRequest):
    """
    Search TripAdvisor for a single query

    Example:
        POST /search
        {
            "query": "restaurants",
            "location": "Tokyo",
            "max_results": 5
        }
    """
    try:
        logger.info(f"Search request: query={request.query}, location={request.location}")

        result = await search_tripadvisor(
            query=request.query,
            location=request.location,
            max_results=request.max_results,
        )

        return result

    except Exception as e:
        logger.error(f"Error during search: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/search/batch")
async def batch_search(request: EntitySearchRequest):
    """
    Batch search for multiple entities

    Example:
        POST /search/batch
        {
            "entities": [
                {"name": "筑地市场", "type": "attraction", "city": "Tokyo"},
                {"name": "Sushi Dai", "type": "restaurant", "city": "Tokyo"}
            ],
            "max_results_per_entity": 3
        }

    Returns:
        {
            "results": [
                {
                    "entity": "筑地市场",
                    "type": "attraction",
                    "city": "Tokyo",
                    "data": { ... TripAdvisor results ... }
                },
                ...
            ]
        }
    """
    try:
        logger.info(f"Batch search request: {len(request.entities)} entities")

        # Search for each entity in parallel
        tasks = []
        for entity in request.entities:
            entity_name = entity.get("name", "")
            entity_type = entity.get("type", "attraction")
            city = entity.get("city", "")

            # Construct query based on type
            if entity_type == "restaurant":
                query = "restaurants"
            elif entity_type == "hotel":
                query = "hotels"
            else:
                query = "attractions"

            # Create search task
            task = search_tripadvisor(
                query=query,
                location=city,
                max_results=request.max_results_per_entity,
            )
            tasks.append((entity_name, entity_type, city, task))

        # Execute all searches in parallel
        results = []
        for entity_name, entity_type, city, task in tasks:
            try:
                search_result = await task

                # Filter results to find best match for entity name
                filtered_results = []
                if search_result.get("success") and search_result.get("results"):
                    for result in search_result["results"]:
                        # Simple name matching (case-insensitive, partial match)
                        result_title = result.get("title", "").lower()
                        entity_name_lower = entity_name.lower()

                        # Check if entity name appears in result title
                        if (entity_name_lower in result_title or
                            result_title in entity_name_lower or
                            # For Chinese names, just return all results
                            any('\u4e00' <= char <= '\u9fff' for char in entity_name)):
                            filtered_results.append(result)

                    # If no exact matches, return top results anyway
                    if not filtered_results:
                        filtered_results = search_result["results"][:request.max_results_per_entity]

                results.append({
                    "entity": entity_name,
                    "type": entity_type,
                    "city": city,
                    "success": search_result.get("success", False),
                    "data": filtered_results[0] if filtered_results else None,
                    "all_results": filtered_results,
                })

            except Exception as e:
                logger.error(f"Error searching for {entity_name}: {e}")
                results.append({
                    "entity": entity_name,
                    "type": entity_type,
                    "city": city,
                    "success": False,
                    "error": str(e),
                })

        return {"results": results}

    except Exception as e:
        logger.error(f"Error during batch search: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Run with: uvicorn tripadvisor_mcp.fastapi_server:app --host 0.0.0.0 --port 8000 --reload
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
