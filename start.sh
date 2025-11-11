#!/bin/bash
# Set PYTHONPATH to include the src directory
export PYTHONPATH="${PYTHONPATH}:/opt/render/project/src"

# Start uvicorn
cd /opt/render/project/src
uvicorn tripadvisor_mcp.fastapi_server:app --host 0.0.0.0 --port $PORT
