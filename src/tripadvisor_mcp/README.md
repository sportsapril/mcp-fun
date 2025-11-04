# TripAdvisor MCP Server

An MCP (Model Context Protocol) server for searching and retrieving travel information from TripAdvisor China (tripadvisor.cn). This server provides intelligent location lookup with multi-tier resolution, supporting both Chinese and English city names with automatic discovery for unknown locations.

## Features

- **Search TripAdvisor China** for:
  - ✓ **Restaurants** - FULLY WORKING
  - ✓ **Attractions/Things to Do** - FULLY WORKING
  - ⚠️ **Hotels** - Limited (hotel data loads dynamically via AJAX)

- **Advanced Location Resolution** (4-Tier System):
  - **Tier 1:** CSV database lookup for worldwide cities from unified locations.csv
  - **Tier 2:** Hardcoded Chinese cities for fast lookup
  - **Tier 3:** LLM-powered intelligent matching (handles Chinese/English, variations, misspellings)
  - **Tier 4:** Dynamic Playwright-based discovery for unknown cities (auto-saves to database)

- **Extract Structured Data:**
  - Title and URL
  - Image URLs
  - Ratings and review counts
  - Descriptions and tags
  - Cuisines (for restaurants)
  - Categories (Restaurant/Attraction/Hotel)
  - Addresses and prices (when available)

- **Flexible Input/Output:**
  - Supports both English and Chinese location names (e.g., "Tokyo" / "东京")
  - Handles city name variations (e.g., "NYC" → "New York", "San Fran" → "San Francisco")
  - Returns formatted markdown text with images and raw JSON data

## Current Status

**Working Categories:**
- ✓ **Restaurants** - Extracts name, rating, reviews, cuisines, URL from `__NEXT_DATA__` JSON
- ✓ **Attractions** - Extracts name, rating, reviews, description, images, URL from `__NEXT_DATA__` JSON

**Known Limitations:**
- ⚠️ **Hotels** - Hotel listings load dynamically via AJAX after page load, so they're not available in the initial HTML. The server attempts to extract from `__NEXT_DATA__` but availability is limited.

**Location Support:**

**Hardcoded Chinese Cities (26 cities):**
- **Tier 1 Cities:** Shanghai (上海), Beijing (北京), Guangzhou (广州), Shenzhen (深圳)
- **Major Tourist Cities:** Xi'an (西安), Chengdu (成都), Hangzhou (杭州), Nanjing (南京), Chongqing (重庆), Suzhou (苏州), Guilin (桂林), Sanya (三亚)
- **Additional Cities:** Xiamen (厦门), Qingdao (青岛), Kunming (昆明), Dalian (大连), Wuhan (武汉), Tianjin (天津), Harbin (哈尔滨), Shenyang (沈阳), Changsha (长沙), Lijiang (丽江), Zhangjiajie (张家界), Huangshan (黄山), Urumqi (乌鲁木齐), Fuzhou (福州), Dezhou (德州)

**CSV Database Support:**
- All locations loaded from unified [data/tripadvisor_geo_map/locations.csv](../../data/tripadvisor_geo_map/locations.csv)
- Contains 1,100+ cities worldwide (USA and international)

**LLM-Powered Matching:**
- Uses Claude Haiku to intelligently match user input to available cities
- Handles Chinese ↔ English translation (e.g., "东京" → "Tokyo")
- Handles variations (e.g., "NYC" → "New York", "San Fran" → "San Francisco")
- Handles misspellings and abbreviations

**Dynamic Discovery:**
- For unknown cities, uses Playwright to visit TripAdvisor and extract location ID
- Auto-saves discovered cities to [locations.csv](../../data/tripadvisor_geo_map/locations.csv) for future lookups
- Provides universal coverage for any city on TripAdvisor

## Installation

### Prerequisites

- **Python**: 3.12 or higher
- **Anthropic API Key**: Required for LLM-based city matching (Tier 3)
  - Sign up at [Anthropic Console](https://console.anthropic.com/)
  - Set environment variable: `export ANTHROPIC_API_KEY=your-api-key`
- **Playwright** (optional but recommended): For dynamic city discovery (Tier 4)
  - Will be installed automatically with dependencies
  - Run `playwright install chromium` after installation

### Install Package

```bash
# Clone the repository (if not already)
git clone <repository-url>
cd mcp-fun

# Install with pip
pip install -e .

# Or using uv (recommended for faster installation)
uv pip install -e .

# Install Playwright browsers (for Tier 4 dynamic discovery)
playwright install chromium
```

This will install the `tripadvisor-mcp` command and all dependencies.

### Dependencies

The following packages will be installed:

| Package | Version | Purpose |
|---------|---------|---------|
| `mcp` | >=1.1.2 | Model Context Protocol framework |
| `httpx` | >=0.28.1 | Async HTTP client for TripAdvisor requests |
| `beautifulsoup4` | >=4.12.0 | HTML parsing for data extraction |
| `playwright` | >=1.40.0 | Browser automation for dynamic discovery |
| `anthropic` | >=0.39.0 | Claude API for intelligent city matching |
| `google-auth-*` | Various | Legacy dependencies (may be removed) |
| `keyring` | >=24.0.0 | Secure credential storage |

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

### Example Queries

Once integrated with Claude Desktop, you can ask:

**Simple Queries:**
- "Find restaurants in Tokyo"
- "Search for attractions in Shanghai"
- "Show me things to do in Paris"

**Detailed Queries:**
- "Find mid-range restaurants in Beijing with good ratings"
- "Search for budget hotels in New York for November 1st, 2025"
- "Show me top attractions in 东京 (Tokyo in Chinese)"

**What Happens Under the Hood:**

When you ask "Find restaurants in Tokyo":
1. Claude calls `search_tripadvisor` tool with:
   ```json
   {
     "query": "restaurants",
     "location": "Tokyo",
     "max_results": 10
   }
   ```
2. Server resolves "Tokyo" → geo_id "g298184" (from CSV database)
3. Server fetches `https://www.tripadvisor.cn/Restaurants-g298184-Tokyo.html`
4. Server extracts restaurant data from `__NEXT_DATA__` JSON
5. Server returns formatted results with images and details
6. Claude displays the results to you

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
  "query": "string (required) - e.g., 'hotels', 'restaurants', 'things to do', 'attractions'",
  "location": "string (optional) - City name in English or Chinese. Examples:",
  "          - English: 'Tokyo', 'New York', 'London', 'San Francisco'",
  "          - Chinese: '东京', '上海', '北京', '纽约'",
  "          - Variations: 'NYC', 'San Fran' (LLM will match intelligently)",
  "date": "string (optional) - YYYY-MM-DD format",
  "price_range": "string (optional) - e.g., 'budget', 'mid-range', 'luxury'",
  "max_results": "integer (optional) - default: 10"
}
```

**Note:** The old `mcp_action` wrapper format is also supported for backwards compatibility with travel planners:

```json
{
  "mcp_action": {
    "mcp_name": "tripadvisor",
    "search_params": {
      "query": "hotel",
      "location": "上海"
    }
  }
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

1. **Location Resolution System** (4-Tier Lookup)
   - **Tier 1:** CSV Database Lookup ([lookup_geo_id_from_csv()](server.py#L157-L184))
     - Loads unified [locations.csv](../../data/tripadvisor_geo_map/locations.csv) with 1,100+ cities
     - Fast exact matching with normalized lookups
     - In-memory cache for performance

   - **Tier 2:** Hardcoded Cities Dictionary ([LOCATION_GEO_IDS](server.py#L501-L562))
     - 26 pre-configured Chinese cities
     - Fast fallback for common searches

   - **Tier 3:** LLM Intelligent Matching ([match_city_with_llm()](server.py#L277-L367))
     - Uses Claude Haiku API (`claude-3-5-haiku-20241022`)
     - Handles Chinese ↔ English translation
     - Handles city name variations and misspellings
     - Returns best match from available cities

   - **Tier 4:** Dynamic Playwright Discovery ([lookup_geo_id_dynamic()](server.py#L436-L498))
     - Headless browser automation as last resort
     - Visits TripAdvisor search page
     - Extracts geo ID from Tourism page URL
     - Auto-saves to [locations.csv](../../data/tripadvisor_geo_map/locations.csv) for future use

2. **HTTP Client** ([get_http_client()](server.py#L163-L170))
   - Async `httpx.AsyncClient` with 30s timeout
   - Modern Chrome User-Agent to avoid blocking
   - Chinese language preference in Accept-Language header
   - Automatic redirect following

3. **Category Detection & URL Building** ([determine_category_and_url()](server.py#L565-L680))
   - Detects category from query keywords (hotel/restaurant/attraction)
   - Determines geo ID using 4-tier lookup system
   - Builds proper TripAdvisor.cn URLs with location ID

4. **Search & Data Extraction** ([search_tripadvisor()](server.py#L683-L1027))
   - Makes HTTP GET request to TripAdvisor
   - Parses HTML using BeautifulSoup
   - Extracts `__NEXT_DATA__` JSON from Next.js framework
   - Category-specific extraction:
     - **Restaurants:** Extracts from `middleRestaurants` and `topRestaurants`
     - **Attractions:** Extracts from `verticalData` section
     - **Hotels:** Attempts extraction from `hotels`, `hotelList`, `recentHotelList`

5. **Result Formatter** ([format_results_for_display()](server.py#L1030-L1082))
   - Creates markdown-formatted text with search summary
   - Formats individual results with title, rating, reviews, images
   - Embeds image URLs as ImageContent
   - Returns both formatted text and raw JSON

6. **MCP Tool Handler** ([call_tool()](server.py#L1085-L1082))
   - Implements MCP protocol
   - Handles both direct and `mcp_action` wrapper formats
   - Calls search function
   - Returns formatted results as list of TextContent and ImageContent

### Data Extraction Strategy

**Primary Strategy:** Extract from Next.js `__NEXT_DATA__` JSON
- TripAdvisor uses Next.js framework
- All page data is embedded in `<script id="__NEXT_DATA__">` tag
- Parse JSON to extract structured data
- More reliable than HTML scraping as data structure is consistent

**Benefits:**
- Robust against HTML/CSS changes
- Structured data with predictable schema
- Includes rich metadata (ratings, reviews, images, prices)
- Single extraction point for all data

## Configuration

### Environment Variables

**Required:**
- `ANTHROPIC_API_KEY` - Required for Tier 3 LLM-based city matching
  - Used by Claude Haiku to intelligently match city names
  - If not set, Tier 3 is skipped and system falls back to Tier 4 (Playwright)
  - Get your API key from [Anthropic Console](https://console.anthropic.com/)

**Optional:**
- No other environment variables are currently required

**Future Configuration (not yet implemented):**
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

1. **Data Extraction Method**: Relies on extracting JSON from Next.js `__NEXT_DATA__` tag
   - If TripAdvisor changes their Next.js data structure, extraction may break
   - More stable than CSS selectors but still subject to changes

2. **Hotels Category**: Limited functionality due to dynamic AJAX loading
   - Hotel listings are not always available in initial page load
   - May return empty results or incomplete data

3. **Rate Limiting**: No built-in rate limiting
   - Be mindful of request frequency to avoid being blocked
   - TripAdvisor may throttle or block excessive requests

4. **Region-Specific**: Designed for TripAdvisor China (tripadvisor.cn)
   - Results are from Chinese version of TripAdvisor
   - Content may be in Chinese or mixed Chinese/English

5. **API Dependencies**:
   - Tier 3 matching requires `ANTHROPIC_API_KEY`
   - Tier 4 dynamic lookup requires Playwright browser installation
   - Internet connection required for all lookups

6. **Scope**: Search functionality only
   - No booking capabilities
   - No detailed individual page scraping
   - No user authentication features
   - No review posting or user interaction

## Troubleshooting

### No Results Found

**Possible Causes:**
- The search query didn't match any listings
- Location couldn't be resolved (check logs for location lookup flow)
- TripAdvisor's `__NEXT_DATA__` structure changed

**Solutions:**
1. Try simplifying your search query (e.g., "restaurant" instead of "italian restaurant")
2. Try both English and Chinese location names
3. Check server logs for location resolution details:
   - Look for messages like "✅ Found geo ID for 'Tokyo' in CSV: g298184"
   - Or "❌ Failed to find geo ID for 'UnknownCity'"
4. Enable debug logging: `export LOG_LEVEL=DEBUG` before running server

### Location Not Found

**Error:** "Could not determine location ID for: [city name]"

**Solutions:**
1. Check if city name is spelled correctly
2. Try variations: "New York", "NYC", "new york city"
3. Try Chinese name if applicable: "纽约" for New York
4. Check if `ANTHROPIC_API_KEY` is set for LLM matching
5. Ensure Playwright is installed for dynamic discovery: `playwright install chromium`
6. Check [locations.csv](../../data/tripadvisor_geo_map/locations.csv) for available cities

### HTTP Errors

**Possible Causes:**
- Internet connection issue
- TripAdvisor blocking requests (403/429 errors)
- TripAdvisor.cn not accessible from your location

**Solutions:**
1. Check your internet connection
2. Wait a few minutes if rate-limited (429 error)
3. Try accessing https://www.tripadvisor.cn in browser
4. Check if VPN is interfering with requests

### Parsing/Extraction Errors

**Error:** "Could not find __NEXT_DATA__ in page" or "No results extracted"

**Possible Causes:**
- TripAdvisor changed their Next.js data structure
- Page loaded incorrectly
- Category-specific data location changed

**Solutions:**
1. Enable debug logging: `export LOG_LEVEL=DEBUG`
2. Check the [server.py](server.py) logs for the raw HTML structure
3. Verify `__NEXT_DATA__` script tag exists on TripAdvisor page
4. Update extraction logic in [search_tripadvisor()](server.py#L683-L1027) if structure changed

### LLM Matching Failures

**Error:** "LLM matching failed" or matching returns incorrect city

**Solutions:**
1. Verify `ANTHROPIC_API_KEY` is set correctly
2. Check API key has sufficient credits
3. Review LLM matching logic in [match_city_with_llm()](server.py#L277-L367)
4. Add manual entry to [LOCATION_GEO_IDS](server.py#L501-L562) for frequently used cities

### Playwright/Dynamic Lookup Issues

**Error:** "Playwright browser not installed" or "Dynamic lookup failed"

**Solutions:**
1. Install Playwright browsers: `playwright install chromium`
2. Ensure sufficient disk space for browser download
3. Check [lookup_geo_id_dynamic()](server.py#L370-L498) logs for specific errors
4. Manually add city to CSV if dynamic lookup keeps failing

## Development

### Project Structure

```
mcp-fun/
├── src/
│   └── tripadvisor_mcp/
│       ├── __init__.py          # Package init with main_entry
│       ├── server.py            # Main MCP server implementation (1082 lines)
│       └── README.md            # This file
├── data/
│   └── tripadvisor_geo_map/
│       └── locations.csv        # Unified location database (1,100+ cities, auto-updated)
├── pyproject.toml               # Package configuration and dependencies
└── README.md                    # Project root README
```

### Key Files

| File | Lines | Purpose |
|------|-------|---------|
| [server.py](server.py) | 1082 | Core MCP server logic, all tiers, search, extraction |
| [__init__.py](__init__.py) | ~10 | Entry point for `tripadvisor-mcp` command |
| [locations.csv](../../data/tripadvisor_geo_map/locations.csv) | 1,164 | Unified worldwide location database (grows as cities are discovered) |

### Making Changes

1. Edit [server.py](server.py) with your modifications
2. Reinstall the package: `pip install -e .` or `uv pip install -e .`
3. Restart Claude Desktop or your MCP client
4. Test your changes with example queries
5. Check logs for debugging: `tail -f ~/.claude/logs/mcp*.log` (macOS)

### Adding Features

**High-Priority Improvements:**
- **Caching**: Add Redis or file-based cache for repeated searches
- **Rate Limiting**: Implement exponential backoff and retry logic
- **Better Hotel Support**: Investigate AJAX endpoints for dynamic hotel data
- **More Extraction Fields**: Add phone numbers, hours, exact addresses
- **Response Streaming**: Stream results as they're found instead of waiting for all

**Medium-Priority:**
- **Individual Page Scraping**: Fetch detailed info from restaurant/attraction detail pages
- **Multi-Region Support**: Add support for other TripAdvisor domains (.com, .co.uk, etc.)
- **Image Processing**: Download and cache images locally, resize for display
- **Search Filters**: Support more TripAdvisor filters (price, rating, cuisine type)
- **Reviews Extraction**: Extract actual review text and sentiment

**Nice-to-Have:**
- **Booking Integration**: Add links or API integration for reservations
- **User Reviews Posting**: Support authenticated actions
- **Map Integration**: Return coordinates for mapping
- **Localization**: Better handling of Chinese/English mixed content

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

## Technical Details

### How Location Lookup Works

When you search for "restaurants in Tokyo", here's the full flow:

1. **Query Parsing**: Extract location "Tokyo" from query
2. **4-Tier Lookup**:
   - **Tier 1 (CSV)**: Check [locations.csv](../../data/tripadvisor_geo_map/locations.csv)
     - Normalize: "Tokyo" → "tokyo"
     - Search: Found! locationId=298184, geo_id=g298184
   - ✅ **Success**: Skip Tiers 2-4
3. **URL Building**: `https://www.tripadvisor.cn/Restaurants-g298184-Tokyo.html`
4. **Data Extraction**: Fetch page, parse `__NEXT_DATA__`, extract restaurant data
5. **Result Formatting**: Return formatted markdown + images + raw JSON

**For Unknown City (e.g., "restaurants in Smalltown, USA"):**

1. **Tier 1 (CSV)**: Not found in locations.csv
2. **Tier 2 (Hardcoded)**: Not in LOCATION_GEO_IDS (Chinese cities only)
3. **Tier 3 (LLM)**:
   - Load all available cities from CSV
   - Call Claude Haiku: "Match 'Smalltown, USA' to best city from [list]"
   - LLM returns: No good match
4. **Tier 4 (Playwright)**:
   - Launch headless Chromium browser
   - Navigate to `https://www.tripadvisor.cn/Search?q=Smalltown%20USA`
   - Click first "Tourism" link
   - Extract geo ID from URL: `https://www.tripadvisor.cn/Tourism-g12345-Smalltown.html` → g12345
   - Save to locations.csv: `Smalltown,12345,https://www.tripadvisor.cn/Tourism-g12345`
   - ✅ **Success**: Return g12345
5. Next search for "Smalltown" will hit **Tier 1** (CSV) directly!

### Data Extraction from __NEXT_DATA__

TripAdvisor uses Next.js framework. All page data is in a JSON blob:

```html
<script id="__NEXT_DATA__" type="application/json">
{
  "props": {
    "pageProps": {
      "urqlState": {
        "...": {
          "data": {
            "locations": [...],
            "middleRestaurants": [...],  # Restaurant data here!
            "verticalData": [...],       # Attraction data here!
            ...
          }
        }
      }
    }
  }
}
</script>
```

The server extracts this JSON and navigates to the relevant section based on category.

## Support

**For Issues:**
- Check this README's [Troubleshooting](#troubleshooting) section first
- Review server logs for error messages
- Verify all prerequisites are installed
- Check [GitHub Issues](https://github.com/your-org/mcp-fun/issues) for known problems

**For Questions:**
- Review the [Architecture](#architecture) section
- Check [MCP Protocol Documentation](https://modelcontextprotocol.io/)
- Review [TripAdvisor.cn](https://www.tripadvisor.cn) website structure
- Ask in GitHub Discussions

**For Contributing:**
- See [Development](#development) section
- Follow existing code style
- Add tests for new features
- Update this README with any new functionality
