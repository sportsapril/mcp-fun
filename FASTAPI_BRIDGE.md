# TripAdvisor MCP FastAPI HTTP Bridge

This FastAPI server provides an HTTP REST API wrapper around the TripAdvisor MCP server, enabling integration with Supabase Edge Functions and other HTTP clients.

## Setup

### 1. Install Dependencies

```bash
cd /Users/aprilxu/Documents/GitHub/mcp-fun
pip install -r requirements-fastapi.txt
```

Or with uv:
```bash
uv pip install -r requirements-fastapi.txt
```

### 2. Install Playwright Browsers

```bash
playwright install chromium
```

### 3. Set Environment Variables

```bash
export ANTHROPIC_API_KEY="sk-ant-api03-..."
```

## Running the Server

### Option 1: Using the Run Script

```bash
./run_fastapi.sh
```

### Option 2: Using Uvicorn Directly

```bash
uvicorn src.tripadvisor_mcp.fastapi_server:app --host 0.0.0.0 --port 8000 --reload
```

### Option 3: Using Python

```bash
python -m src.tripadvisor_mcp.fastapi_server
```

## API Endpoints

### Health Check

```bash
GET http://localhost:8000/health
```

Response:
```json
{
  "status": "healthy",
  "service": "TripAdvisor MCP HTTP Bridge",
  "version": "1.0.0"
}
```

### Single Search

```bash
POST http://localhost:8000/search
Content-Type: application/json

{
  "query": "restaurants",
  "location": "Tokyo",
  "max_results": 5
}
```

Response:
```json
{
  "success": true,
  "query": "restaurants",
  "location": "Tokyo",
  "category": "restaurants",
  "results_count": 5,
  "results": [
    {
      "title": "Sushi Dai",
      "url": "https://www.tripadvisor.cn/Restaurant_Review-...",
      "rating": "4.5",
      "reviews": "1234 reviews",
      "category": "Restaurant",
      "cuisines": "Japanese, Sushi",
      "image_url": "https://media-cdn.tripadvisor.com/..."
    }
  ]
}
```

### Batch Search (For Multiple Entities)

```bash
POST http://localhost:8000/search/batch
Content-Type: application/json

{
  "entities": [
    {
      "name": "筑地市场",
      "type": "attraction",
      "city": "Tokyo"
    },
    {
      "name": "Sushi Dai",
      "type": "restaurant",
      "city": "Tokyo"
    }
  ],
  "max_results_per_entity": 3
}
```

Response:
```json
{
  "results": [
    {
      "entity": "筑地市场",
      "type": "attraction",
      "city": "Tokyo",
      "success": true,
      "data": {
        "title": "Tsukiji Fish Market",
        "url": "...",
        "rating": "4.5",
        "reviews": "1234 reviews",
        "image_url": "..."
      },
      "all_results": [...]
    },
    {
      "entity": "Sushi Dai",
      "type": "restaurant",
      "city": "Tokyo",
      "success": true,
      "data": {...},
      "all_results": [...]
    }
  ]
}
```

## Interactive API Documentation

Once the server is running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Testing

### Using cURL

```bash
# Health check
curl http://localhost:8000/health

# Search restaurants
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "restaurants",
    "location": "Tokyo",
    "max_results": 5
  }'

# Batch search
curl -X POST http://localhost:8000/search/batch \
  -H "Content-Type: application/json" \
  -d '{
    "entities": [
      {"name": "筑地市场", "type": "attraction", "city": "Tokyo"}
    ],
    "max_results_per_entity": 3
  }'
```

### Using Python

```python
import requests

# Single search
response = requests.post(
    "http://localhost:8000/search",
    json={
        "query": "restaurants",
        "location": "Tokyo",
        "max_results": 5
    }
)
print(response.json())

# Batch search
response = requests.post(
    "http://localhost:8000/search/batch",
    json={
        "entities": [
            {"name": "筑地市场", "type": "attraction", "city": "Tokyo"},
            {"name": "Sushi Dai", "type": "restaurant", "city": "Tokyo"}
        ],
        "max_results_per_entity": 3
    }
)
print(response.json())
```

## Deployment

### Local Network Access

The server runs on `0.0.0.0:8000` by default, making it accessible from your local network.

### Production Deployment Options

1. **Cloud Run / Cloud Functions**: Deploy as a containerized service
2. **Railway / Render**: Simple deployment with automatic HTTPS
3. **AWS Lambda / Azure Functions**: Serverless deployment
4. **VPS / Dedicated Server**: Traditional hosting

### Docker Deployment

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements-fastapi.txt .
RUN pip install -r requirements-fastapi.txt

# Install Playwright
RUN playwright install-deps
RUN playwright install chromium

# Copy source code
COPY src ./src

# Expose port
EXPOSE 8000

# Run server
CMD ["uvicorn", "src.tripadvisor_mcp.fastapi_server:app", "--host", "0.0.0.0", "--port", "8000"]
```

Build and run:
```bash
docker build -t tripadvisor-mcp-fastapi .
docker run -p 8000:8000 -e ANTHROPIC_API_KEY="your-key" tripadvisor-mcp-fastapi
```

## CORS Configuration

By default, CORS is enabled for all origins (`allow_origins=["*"]`).

For production, restrict to your Supabase domain:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://zchvpcuuayzexbhyrxau.supabase.co",
        "http://localhost:8080"  # For local development
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## Integration with Supabase Edge Functions

Once deployed, your Supabase Edge Function can call this API:

```typescript
// In your Edge Function
const response = await fetch("http://your-fastapi-server:8000/search/batch", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    entities: [
      { name: "筑地市场", type: "attraction", city: "Tokyo" }
    ],
    max_results_per_entity: 3
  })
});

const data = await response.json();
```

## Troubleshooting

### Port Already in Use

```bash
# Find process using port 8000
lsof -i :8000

# Kill it
kill -9 <PID>
```

### Missing ANTHROPIC_API_KEY

If Tier 3 LLM matching fails, the server will fall back to Tier 4 (Playwright). This is slower but still works.

### Playwright Issues

```bash
# Reinstall browsers
playwright install chromium --with-deps
```

## Performance Notes

- **Tier 1 (CSV lookup)**: <1ms
- **Tier 2 (Hardcoded)**: <1ms
- **Tier 3 (LLM matching)**: ~200-500ms
- **Tier 4 (Playwright)**: 15-20 seconds (one-time per new city)

For best performance, ensure the `data/tripadvisor_geo_map/locations.csv` is up to date with all cities you plan to search.
