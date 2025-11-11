#!/bin/bash
# Change to src directory and add it to PYTHONPATH
cd /opt/render/project/src
export PYTHONPATH="/opt/render/project/src:${PYTHONPATH}"

# Start uvicorn from the src directory
exec uvicorn tripadvisor_mcp.fastapi_server:app --host 0.0.0.0 --port $PORT
