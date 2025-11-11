#!/bin/bash
# Set PYTHONPATH to include src directory
export PYTHONPATH="/opt/render/project/src:${PYTHONPATH}"

# Start uvicorn (it will find the module via PYTHONPATH)
exec uvicorn tripadvisor_mcp.fastapi_server:app --host 0.0.0.0 --port $PORT
