# TripAdvisor MCP Server

An MCP (Model Context Protocol) server for searching and retrieving travel information from TripAdvisor China (tripadvisor.cn). This server is designed to integrate with travel planning systems and provides rich search results with images, URLs, ratings, and reviews.

## Features

- Search TripAdvisor China for:
  - ✓ **Restaurants** - FULLY WORKING
  - ✓ **Attractions/Things to Do** - FULLY WORKING
  - ⚠ **Hotels** - Limited (hotel data loads dynamically via AJAX)
- Extract structured data including:
  - Title and URL
  - Images (for attractions)
  - Ratings and reviews
  - Descriptions
  - Cuisines (for restaurants)
  - Categories
- Accepts planner output format for seamless integration
- Returns formatted results with both human-readable and JSON formats

## Current Status

**Working Categories:**
- ✓ Restaurants - Extracts name, rating, reviews, cuisines, URL
- ✓ Attractions - Extracts name, rating, reviews, description, images, URL

**Known Limitations:**
- ⚠ Hotels - Hotel listings load dynamically via AJAX after page load, so they're not available in the initial page data. The MCP returns a helpful error message with a direct URL to visit instead.

**Supported Cities (25 Total):**
- **Tier 1:** Shanghai (上海), Beijing (北京), Guangzhou (广州), Shenzhen (深圳)
- **Tourist Cities:** Xi'an (西安), Chengdu (成都), Hangzhou (杭州), Nanjing (南京), Chongqing (重庆), Suzhou (苏州), Guilin (桂林), Sanya (三亚)
- **Additional:** Xiamen (厦门), Qingdao (青岛), Kunming (昆明), Dalian (大连), Wuhan (武汉), Tianjin (天津), Harbin (哈尔滨), Shenyang (沈阳), Changsha (长沙), Lijiang (丽江), Zhangjiajie (张家界), Huangshan (黄山), Urumqi (乌鲁木齐)

**Unknown Cities:** If you request a city not in this list, the MCP returns a helpful error with the list of supported cities and a suggestion to visit TripAdvisor.cn directly.

## Installation

Install the package with its dependencies:

```bash
# Using pip
pip install -e .

# Using uv (recommended)
uv pip install -e .
```

This will install the `tripadvisor-mcp` command.

## Usage

### Running as MCP Server

For integration with Claude Desktop or other MCP clients:

```bash
tripadvisor-mcp
```

### Claude Desktop Configuration

Add to your Claude Desktop config file:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "tripadvisor": {
      "command": "tripadvisor-mcp"
    }
  }
}
```

Restart Claude Desktop after updating the configuration.

### Using with Travel Planners

This MCP server is designed to work with travel planning agents. The planner should output:

```json
{
  "mcp_action": {
    "mcp_name": "tripadvisor",
    "search_params": {
      "query": "hotel",
      "location": "上海",
      "date": "2025-11-01",
      "price_range": "mid-range"
    }
  }
}
```

The MCP server will then:
1. Search TripAdvisor China with the provided parameters
2. Extract relevant results with images and metadata
3. Format and return the results for display

## API Reference

### Tool: `search_tripadvisor`

Search TripAdvisor China for travel information.

**Input Schema:**

```json
{
  "mcp_action": {
    "mcp_name": "tripadvisor",
    "search_params": {
      "query": "string (required) - e.g., 'hotel', 'restaurant', 'things to do'",
      "location": "string (optional) - e.g., '上海', '北京'",
      "date": "string (optional) - YYYY-MM-DD format",
      "price_range": "string (optional) - e.g., 'budget', 'mid-range', 'luxury'"
    }
  },
  "max_results": "integer (optional) - default: 10"
}
```

**Output:**

Returns a list of content items including:
- Summary with search parameters
- Individual results with:
  - Title
  - URL
  - Image URL
  - Rating
  - Number of reviews
  - Description
  - Price (if available)
  - Category (if available)
- Raw JSON data for programmatic access

**Example Usage:**

```python
# Example planner output
planner_output = {
    "mcp_action": {
        "mcp_name": "tripadvisor",
        "search_params": {
            "query": "restaurant",
            "location": "北京",
            "price_range": "mid-range"
        }
    },
    "max_results": 5
}
```

## Architecture

### Components

1. **HTTP Client** ([server.py](server.py#L38-L51))
   - Uses `httpx.AsyncClient` for async HTTP requests
   - Configured with proper User-Agent and headers
   - Follows redirects automatically

2. **Search Function** ([server.py](server.py#L54-L220))
   - Builds search URLs with parameters
   - Makes HTTP requests to TripAdvisor
   - Parses HTML using BeautifulSoup
   - Extracts structured data from search results

3. **Result Formatter** ([server.py](server.py#L223-L297))
   - Formats search results for display
   - Creates rich text content with markdown
   - Includes images and metadata
   - Provides both formatted and raw JSON output

4. **MCP Tool Handler** ([server.py](server.py#L302-L405))
   - Implements MCP protocol
   - Validates planner input format
   - Calls search function
   - Returns formatted results

### Web Scraping Strategy

The server uses multiple fallback strategies for parsing TripAdvisor search results:

1. **Primary Strategy**: Look for result containers with common class patterns
   - Divs with "result" in class name
   - Articles with data-test attributes
   - Extract title, link, image, rating, reviews, description, price, category

2. **Fallback Strategy**: If primary fails, use simpler link-based extraction
   - Find all internal links
   - Extract nearby images
   - Build minimal result objects

This dual-strategy approach handles changes to TripAdvisor's HTML structure.

## Configuration

### Environment Variables

Currently no environment variables are required. Future versions may add:

- `TRIPADVISOR_BASE_URL` - Override base URL (default: https://www.tripadvisor.cn)
- `TRIPADVISOR_TIMEOUT` - HTTP timeout in seconds (default: 30)
- `TRIPADVISOR_MAX_RESULTS` - Default max results (default: 10)

## Testing

### Test the MCP Server

```bash
# Run the server directly to see stdio communication
tripadvisor-mcp

# You can then send MCP protocol messages via stdin
```

### Test with Example Input

Create a test file `test_input.json`:

```json
{
  "mcp_action": {
    "mcp_name": "tripadvisor",
    "search_params": {
      "query": "hotel",
      "location": "上海"
    }
  },
  "max_results": 3
}
```

Then use the MCP inspector or Claude Desktop to test.

## Limitations

1. **Web Scraping**: This server relies on web scraping, which may break if TripAdvisor changes their HTML structure
2. **Rate Limiting**: No built-in rate limiting - be mindful of request frequency
3. **Region-Specific**: Designed for TripAdvisor China (tripadvisor.cn)
4. **No Authentication**: Does not handle authenticated TripAdvisor features
5. **Search Only**: Only provides search functionality, not booking or detailed page scraping

## Troubleshooting

### No Results Found

- Try simplifying your search query
- Check if the location name is correct (Chinese characters may work better)
- TripAdvisor's HTML structure may have changed - check logs

### HTTP Errors

- Check your internet connection
- TripAdvisor may be blocking requests - try adjusting User-Agent
- Check if TripAdvisor.cn is accessible from your location

### Parsing Errors

- Enable debug logging: `export LOG_LEVEL=DEBUG`
- Check the HTML structure has changed
- Update selectors in [server.py](server.py)

## Development

### Project Structure

```
src/tripadvisor_mcp/
├── __init__.py          # Package init with main_entry
├── server.py            # Main MCP server implementation
└── README.md            # This file
```

### Making Changes

1. Edit [server.py](server.py)
2. Reinstall: `pip install -e .`
3. Restart Claude Desktop or MCP client
4. Test your changes

### Adding Features

Consider adding:
- Caching for repeated searches
- More detailed page scraping (individual hotel/restaurant pages)
- Image downloading and local storage
- Support for other TripAdvisor regions
- Rate limiting and retry logic
- More sophisticated error handling

## Integration with Travel Planning Flow

This MCP is designed to be part of a larger travel planning system:

```
User Query
    ↓
Travel Planner Agent (generates structured search params)
    ↓
TripAdvisor MCP (searches and formats results)
    ↓
Display Agent (shows results to user)
    ↓
Booking Agent (handles reservations)
```

The planner agent should:
1. Understand user's travel needs
2. Generate appropriate search parameters
3. Call this MCP with structured input
4. Process and present results to user

## License

Same as parent project.

## Contributing

Contributions welcome! Please ensure:
- Code follows existing style
- Add tests for new features
- Update documentation
- Test with Claude Desktop before submitting

## Support

For issues and questions:
- Check the main project README
- Review TripAdvisor's website structure
- Check MCP protocol documentation
- Open an issue on GitHub
