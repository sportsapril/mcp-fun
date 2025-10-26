# MCP Fun - Collection of MCP Servers

A collection of Model Context Protocol (MCP) servers for various tasks including dataset analysis, travel planning, invoice management, and email operations.

## Available MCP Servers

### 1. TripAdvisor MCP ✨ NEW
Search and retrieve travel information from TripAdvisor China (tripadvisor.cn). Integrates with travel planners to provide rich search results with images, URLs, ratings, and reviews.

**Features:**
- ✓ Search for restaurants and attractions (WORKING)
- ⚠ Hotels limited (data loads dynamically)
- Extract structured data with images, ratings, reviews, cuisines
- Designed for integration with travel planning agents
- Accepts planner output format
- **Supports 25 major Chinese cities** (expanded!)
- Graceful error handling for unsupported cities

[Full Documentation](src/tripadvisor_mcp/README.md)

**Quick Test:**
```bash
python test_tripadvisor_simple.py
```

### 2. Dataset Analysis MCP
An MCP server for analyzing datasets using the Hugging Face Dataset Viewer API.

**Features:**
- Dataset validation and metadata retrieval
- Data retrieval with pagination
- Full-text search within datasets
- SQL-like filtering capabilities
- Statistical analysis
- Parquet file export URLs

### 3. Twitter Invoice MCP
Automate downloading invoices from Twitter/X Developer Portal using Selenium.

**Features:**
- Browser-based authentication (no stored credentials)
- List and download invoices
- Standalone CLI and MCP server modes

[Full Documentation](CLAUDE.md#twitter-invoice-downloader)

### 4. Gmail MCP
Manage Gmail operations including reading and sending emails.

**Features:**
- OAuth2 authentication
- Read and send emails
- Search and filter messages

## Installation

Install all MCP servers in development mode:

```bash
# Using pip
pip install -e .

# Using uv (recommended)
uv pip install -e .
```

This installs the following commands:
- `tripadvisor-mcp` - TripAdvisor search server
- `dataset-analysis` - Dataset analysis server
- `twitter-invoice` - Twitter invoice downloader
- `gmail-mcp` - Gmail operations server

## Configuration

### Claude Desktop Setup

Add to your Claude Desktop config file:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "tripadvisor": {
      "command": "tripadvisor-mcp"
    },
    "dataset-analysis": {
      "command": "dataset-analysis"
    },
    "twitter-invoice": {
      "command": "twitter-invoice"
    },
    "gmail": {
      "command": "gmail-mcp"
    }
  }
}
```

See [claude_desktop_config_example.json](claude_desktop_config_example.json) for a complete example.

## Quick Start

### TripAdvisor MCP

```bash
# Run the server
tripadvisor-mcp

# Or test programmatically
python test_tripadvisor.py
```

Example planner input:
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

### Dataset Analysis MCP

```bash
# Run the server
dataset-analysis

# Set HF token for private datasets (optional)
export HF_TOKEN=your_token_here
```

### Twitter Invoice MCP

```bash
# Run as MCP server
twitter-invoice

# Or use standalone CLI
python twitter_invoice_downloader.py --latest
```

### Gmail MCP

```bash
# Run the server
gmail-mcp

# First run will prompt for OAuth2 authentication
```

## Requirements

- Python 3.12+
- Dependencies:
  - `mcp>=1.1.2`
  - `httpx>=0.28.1`
  - `selenium>=4.15.0`
  - `beautifulsoup4>=4.12.0`
  - Google API clients (for Gmail)

## Project Structure

```
mcp-fun/
├── src/
│   ├── tripadvisor_mcp/       # TripAdvisor search MCP
│   ├── dataset_analysis/       # Dataset analysis MCP
│   ├── twitter_invoice_mcp/    # Twitter invoice MCP
│   └── gmail_mcp/              # Gmail operations MCP
├── test_tripadvisor.py         # Test script for TripAdvisor
├── pyproject.toml              # Package configuration
├── README.md                   # This file
└── CLAUDE.md                   # Detailed project documentation
```

## Documentation

- [TripAdvisor MCP Documentation](src/tripadvisor_mcp/README.md)
- [Complete Project Documentation](CLAUDE.md)
- [Example Claude Desktop Config](claude_desktop_config_example.json)

## Testing

```bash
# Test TripAdvisor MCP
python test_tripadvisor.py

# Test individual servers
tripadvisor-mcp
dataset-analysis
twitter-invoice
gmail-mcp
```

## Development

See [CLAUDE.md](CLAUDE.md) for detailed development instructions and architecture documentation.

## License

MIT License - See LICENSE file for details.