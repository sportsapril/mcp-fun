"""
FastAPI HTTP Bridge for TripAdvisor MCP Server

This provides an HTTP REST API wrapper around the tripadvisor_mcp
to enable integration with Supabase Edge Functions and other HTTP clients.
"""

import asyncio
import csv
import logging
import os
from pathlib import Path
from typing import Any, Optional, Dict

from fastapi import FastAPI, HTTPException, Header, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field

# Import the search function and constants from the MCP server
from .server import search_tripadvisor, BASE_URL
# import tripadvisor_mcp.server as ta_server: AX: this is the original one

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("tripadvisor-fastapi")

# Get optional API key from environment
FASTAPI_API_KEY = os.getenv("FASTAPI_API_KEY")
if FASTAPI_API_KEY:
    logger.info("API key authentication enabled")
else:
    logger.warning("API key authentication disabled - set FASTAPI_API_KEY to enable")

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

# API Key security scheme (optional)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

def verify_api_key(x_api_key: str = Security(api_key_header)) -> bool:
    """
    Verify API key if FASTAPI_API_KEY is set.
    If not set, allow all requests (for local development).
    """
    if not FASTAPI_API_KEY:
        # No API key configured - allow request
        return True

    if not x_api_key:
        raise HTTPException(
            status_code=401,
            detail="Missing API key. Provide X-API-Key header."
        )

    if x_api_key != FASTAPI_API_KEY:
        raise HTTPException(
            status_code=403,
            detail="Invalid API key"
        )

    return True


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
    max_results_per_entity: int = Field(default=5, ge=1, le=10)


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
async def search(request: SearchRequest, authorized: bool = Security(verify_api_key)):
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
async def batch_search(request: EntitySearchRequest, authorized: bool = Security(verify_api_key)):
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

            # Construct query by including entity name + type
            # This gives much better search results than just searching by type
            if entity_type == "restaurant":
                query = f"{entity_name} restaurant"
            elif entity_type == "hotel":
                query = f"{entity_name} hotel"
            else:
                query = f"{entity_name} attraction"

            logger.info(f"Searching for: query='{query}', location='{city}'")

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
                    filtered_results = search_result["results"][:request.max_results_per_entity]

                # Add result to list
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


@app.get("/location-ids")
async def get_location_ids(authorized: bool = Security(verify_api_key)) -> Dict[str, str]:
    """
    Load TripAdvisor location IDs from CSV file.
    Returns a mapping of location names to their g-numbers.

    Example response:
    {
        "Chengdu": "g297463",
        "Beijing": "g294212",
        "成都": "g297463",
        ...
    }
    """
    try:
        # Path to CSV file
        csv_path = Path(__file__).parent.parent.parent / "data" / "tripadvisor_geo_map" / "locations.csv"

        if not csv_path.exists():
            logger.error(f"Location CSV not found at: {csv_path}")
            raise HTTPException(status_code=500, detail="Location data file not found")

        location_map: Dict[str, str] = {}

        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                location_name = row['location']
                location_id = row['locationId']

                # Store with g-prefix
                g_id = f"g{location_id}"
                location_map[location_name] = g_id

        logger.info(f"Loaded {len(location_map)} location IDs from CSV")
        return location_map

    except Exception as e:
        logger.error(f"Error loading location IDs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/chinese-to-english-cities")
async def get_chinese_to_english_cities(authorized: bool = Security(verify_api_key)) -> Dict[str, str]:
    """
    Load Chinese to English city name mapping from CSV file.
    Returns a mapping of Chinese city names to English city names.
    Data source: /data/chinese_cities_translated.csv
    """
    try:
        csv_path = Path(__file__).parent.parent.parent / "data" / "chinese_cities_translated.csv"

        if not csv_path.exists():
            logger.error(f"Chinese cities CSV not found at: {csv_path}")
            raise HTTPException(status_code=500, detail="Chinese cities data file not found")

        city_map: Dict[str, str] = {}

        with open(csv_path, 'r', encoding='utf-8-sig') as f:  # utf-8-sig handles BOM
            reader = csv.DictReader(f)
            for row in reader:
                # Skip rows that don't have the required columns
                if 'city_chinese' not in row or 'city' not in row:
                    continue
                if not row['city_chinese'] or not row['city']:
                    continue

                chinese_name = row['city_chinese']
                english_name = row['city']
                # Map Chinese name to English name
                city_map[chinese_name] = english_name

        logger.info(f"Loaded {len(city_map)} Chinese-to-English city mappings from CSV")
        return city_map

    except Exception as e:
        logger.error(f"Error loading Chinese city mappings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class LogEntry(BaseModel):
    """Log entry for TripAdvisor search activity"""
    timestamp: str
    event_type: str  # REQUEST, RESPONSE, VALIDATION, DECISION
    message: str


@app.post("/log-tripadvisor-activity")
async def log_tripadvisor_activity(entry: LogEntry, authorized: bool = Security(verify_api_key)) -> Dict[str, str]:
    """
    Append a log entry to the TripAdvisor search activity log file.

    Log file location preference:
    1. /Users/aprilxu/Documents/GitHub/ai-lu-xing-jie-jie/tripadvisor-search.log
    2. Fallback: /Users/aprilxu/Documents/GitHub/mcp-fun/tripadvisor-search.log
    """
    try:
        # Try primary location first
        primary_log_path = Path("/Users/aprilxu/Documents/GitHub/ai-lu-xing-jie-jie/tripadvisor-search.log")
        fallback_log_path = Path(__file__).parent.parent.parent / "tripadvisor-search.log"

        log_path = primary_log_path if primary_log_path.parent.exists() else fallback_log_path

        # Format log entry
        log_line = f"[{entry.timestamp}] [{entry.event_type}] {entry.message}\n"

        # Append to log file
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(log_line)

        return {"status": "success", "log_path": str(log_path)}

    except Exception as e:
        logger.error(f"Error writing to log file: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Run with: uvicorn tripadvisor_mcp.fastapi_server:app --host 0.0.0.0 --port 8000 --reload
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
