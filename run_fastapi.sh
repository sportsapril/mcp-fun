#!/bin/bash
# Script to run TripAdvisor MCP FastAPI server

# Set environment variables if needed
# export ANTHROPIC_API_KEY="your-key-here"

# Run the FastAPI server with uvicorn
echo "Starting TripAdvisor MCP FastAPI server on http://localhost:8000"
echo "API docs will be available at http://localhost:8000/docs"
echo ""

cd "$(dirname "$0")"

# Add src directory to PYTHONPATH so imports work correctly
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"

uvicorn tripadvisor_mcp.fastapi_server:app --host 0.0.0.0 --port 8000 --reload
