# TripAdvisor MCP - Claude Desktop Integration Guide

## Quick Setup (3 Steps)

### Step 1: Set Your Anthropic API Key

Replace `YOUR_API_KEY_HERE` in the config with your actual API key:

**Edit**: `~/Library/Application Support/Claude/claude_desktop_config.json`

```json
"tripadvisor": {
  "command": "/Users/aprilxu/miniconda3/bin/tripadvisor-mcp",
  "env": {
    "ANTHROPIC_API_KEY": "sk-ant-api03-..."  // ← Put your real API key here
  }
}
```

**How to get your API key**:
1. Go to https://console.anthropic.com/
2. Navigate to "API Keys" section
3. Create a new key or copy existing one

### Step 2: Restart Claude Desktop

**Important**: You MUST restart Claude Desktop for the new MCP server to load.

1. Quit Claude Desktop completely (⌘+Q)
2. Reopen Claude Desktop

### Step 3: Test It!

In Claude Desktop, try these example prompts:

```
"Find top 3 restaurants in 东京"
"Show me attractions in NYC"
"What are the best things to do in 上海?"
"Find hotels in LA"
```

## Configuration Details

### Your Current Config

I've already added the TripAdvisor MCP to your config at:

**File**: `~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "filesystem": { ... },
    "research": { ... },
    "fetch": { ... },
    "dataset-analysis": { ... },
    "twitter-invoice": { ... },
    "gmail": { ... },
    "tripadvisor": {
      "command": "/Users/aprilxu/miniconda3/bin/tripadvisor-mcp",
      "env": {
        "ANTHROPIC_API_KEY": "YOUR_API_KEY_HERE"  // ← UPDATE THIS!
      }
    }
  }
}
```

### Why ANTHROPIC_API_KEY is Required

The TripAdvisor MCP uses Claude Haiku 3 for intelligent bilingual city name matching. This allows you to search with:
- Chinese city names: 东京, 纽约, 上海
- English variations: Tokyo City, New York City
- Abbreviations: LA, NYC, SF
- And it automatically matches them to the correct location!

**Cost**: Extremely cheap (~$0.0001 per search)

## Available Tools

Once configured, Claude Desktop will have access to these tools:

### 1. `search_tripadvisor`
Search for restaurants, attractions, hotels, or things to do in any city.

**Parameters**:
- `query`: What to search for (e.g., "restaurants", "attractions", "hotels", "things to do")
- `location`: City name in English or Chinese (e.g., "Tokyo", "东京", "NYC", "纽约")
- `max_results`: Number of results to return (default: 10)

**Examples**:
```
"Find restaurants in Tokyo"
"Show me top 5 attractions in 纽约"
"What are the best hotels in LA?"
```

## Supported Locations

The MCP has access to:
- **982 cities worldwide** from CSV database (usa.csv + world.csv)
- **26 major Chinese cities** with hardcoded mappings
- **LLM-powered matching** for variations and Chinese names
- **Dynamic lookup** as fallback for unlisted cities

### Major Cities Included
- 🇺🇸 USA: New York, Los Angeles, San Francisco, Chicago, Las Vegas, Miami, etc.
- 🇨🇳 China: 北京, 上海, 广州, 深圳, 杭州, 成都, 西安, etc.
- 🇯🇵 Japan: Tokyo, Osaka, Kyoto, etc.
- 🇬🇧 UK: London, Edinburgh, Manchester, etc.
- 🇫🇷 France: Paris, Lyon, Marseille, etc.
- 🇮🇹 Italy: Rome, Venice, Florence, etc.
- And many more worldwide destinations!

## How It Works

### Four-Tier Intelligent Lookup

1. **CSV Database** (fastest): Checks 982 cities from csv files
2. **Hardcoded Chinese Cities**: Checks 26 major Chinese cities
3. **LLM Semantic Matching**: Claude Haiku 3 matches variations
4. **Selenium Dynamic Lookup**: Browser automation as last resort

### Example Flow

**User asks**: "Find restaurants in 东京"

```
Input: "东京"
  ↓
Tier 1: Direct CSV lookup → Not found (CSV has "tokyo" not "东京")
  ↓
Tier 2: Hardcoded Chinese → Not found
  ↓
Tier 3: LLM matching → "东京" matches "tokyo" ✅
  ↓
Lookup geo ID for "tokyo" → g298184
  ↓
Fetch results from: https://www.tripadvisor.cn/Restaurants-g298184
  ↓
Return: Top restaurants with ratings, images, descriptions
```

## Example Conversations

### Example 1: Chinese City Name
**You**: "Find top 5 restaurants in 东京"

**Claude** (using MCP):
*Searches TripAdvisor China for Tokyo restaurants*
- いぬカフェRIO 浅草店 (4.9★)
- メイドカフェ MAID MADE (4.8★)
- ...

### Example 2: Abbreviations
**You**: "What are the best things to do in LA?"

**Claude** (using MCP):
*Automatically matches "LA" to "Los Angeles"*
- Getty Center (4.8★)
- Griffith Observatory (4.7★)
- ...

### Example 3: City Variations
**You**: "Show me hotels in 纽约市"

**Claude** (using MCP):
*Matches "纽约市" to "New York"*
- [Hotels list with ratings and prices]

## Troubleshooting

### MCP Server Not Appearing

**Symptom**: Claude Desktop doesn't show TripAdvisor tools

**Solution**:
1. Check config file syntax is valid JSON (no trailing commas!)
2. Verify command path exists: `ls /Users/aprilxu/miniconda3/bin/tripadvisor-mcp`
3. Restart Claude Desktop completely (⌘+Q, then reopen)
4. Check Claude Desktop logs: `~/Library/Logs/Claude/mcp*.log`

### "ANTHROPIC_API_KEY not set" Warning

**Symptom**: Searches work but LLM matching is skipped

**Solution**:
- Replace `"YOUR_API_KEY_HERE"` with your actual API key in the config
- Restart Claude Desktop after updating

### City Not Found

**Symptom**: "Location not found" error

**Solution**:
1. Try different city name variations (English, Chinese, abbreviation)
2. Check if city is in the database: `python -c "from src.tripadvisor_mcp.server import _location_database, load_location_database; load_location_database(); print('tokyo' in _location_database)"`
3. Add city manually to CSV files if needed (see CLAUDE.md)

### Slow Response

**Symptom**: Takes long time to get results

**Solution**:
- First search loads CSV database (~1-2 seconds)
- Subsequent searches are fast
- LLM matching adds ~200-500ms (only for non-direct matches)
- If it takes 10+ seconds, dynamic Selenium lookup is running (last resort)

## Verifying Installation

### Check MCP is Running

After restarting Claude Desktop, you can verify by looking at the logs:

```bash
tail -f ~/Library/Logs/Claude/mcp-server-tripadvisor.log
```

You should see:
```
INFO:tripadvisor-mcp:Loaded usa.csv: 294 unique locations
INFO:tripadvisor-mcp:Loaded world.csv: 982 unique locations
INFO:tripadvisor-mcp:Location database loaded: 982 locations, 1155 total entries
```

### Test from Command Line

You can also test the MCP server directly:

```bash
echo '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' | /Users/aprilxu/miniconda3/bin/tripadvisor-mcp
```

Should return available tools including `search_tripadvisor`.

## Features

### ✅ What Works Great
- 982 worldwide cities with instant CSV lookup
- Bilingual support (Chinese + English)
- Handles abbreviations (LA, NYC, SF)
- Understands city variations (Tokyo City, 东京都, 纽约市)
- Fast (<1 second for cached cities)
- Extremely affordable (<$0.0001 per search)

### ⚠️ Known Limitations
- Dynamic lookup (Tier 4) has limited reliability
- Requires internet connection
- Images from TripAdvisor may have CORS restrictions
- Some small cities may not be in database

## Cost Breakdown

### Per Search Costs
- **CSV/Hardcoded lookup**: Free (local)
- **LLM matching**: ~$0.0001 (when city name needs translation)
- **Selenium lookup**: Free (but slow and unreliable)

### Monthly Estimate
Assuming 1000 searches/month with 50% requiring LLM matching:
- 500 searches × $0.0001 = **$0.05/month**

Extremely affordable! 🎉

## Support

For issues or questions:
1. Check [CLAUDE.md](CLAUDE.md) for detailed documentation
2. Review [LLM_MATCHING_SUCCESS.md](LLM_MATCHING_SUCCESS.md) for matching details
3. Check GitHub issues or create a new one

## Next Steps

1. ✅ Update `ANTHROPIC_API_KEY` in config
2. ✅ Restart Claude Desktop
3. ✅ Try example prompts
4. 🎉 Enjoy searching TripAdvisor in any language!
