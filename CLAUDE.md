# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This repository contains **two separate projects** that should be split into separate directories:

1. **Twitter Invoice Downloader** - Automate downloading invoices from Twitter/X Developer Portal
2. **Dataset Analysis MCP** - MCP server for analyzing Hugging Face datasets

**Current structure**: Both projects share a single `pyproject.toml` and are in `src/dataset_analysis/` and `src/twitter_invoice_mcp/`

**Recommended**: Split into separate subdirectories (`invoice/` and `data-analysis/`) with their own `pyproject.toml` files.

## Installation

```bash
# Install both projects
pip install -e .

# Or using uv (recommended)
uv pip install -e .
```

This creates two entry points:
- `twitter-invoice` - MCP server for invoice management
- `dataset-analysis` - MCP server for dataset analysis

## Twitter Invoice Downloader

### Architecture

**Two implementations with shared logic:**

1. **MCP Server** ([src/twitter_invoice_mcp/server.py](src/twitter_invoice_mcp/server.py))
   - Runs as Model Context Protocol server for Claude Desktop
   - Uses standard MCP Server (not FastMCP)
   - Exposes tools: `open_billing_page`, `list_invoices`, `download_invoice`, `download_all_invoices`, `download_latest_invoice`, `close_browser`

2. **Standalone CLI Script** ([twitter_invoice_downloader.py](twitter_invoice_downloader.py))
   - Direct command-line usage with argparse
   - Same Selenium automation logic as MCP server
   - Usage: `python twitter_invoice_downloader.py --latest` or `--all`

**Core Logic** (`TwitterInvoiceManager` / `TwitterInvoiceDownloader` class):
- Uses Selenium WebDriver with Chrome
- Navigates to `https://developer.x.com/en/account/billing`
- No credentials stored - manual browser authentication required
- Extracts invoice table data and downloads PDFs via button clicks
- Default download directory: `./invoices/` (configurable via `INVOICE_DOWNLOAD_DIR` env var)

### Authentication Flow

**Critical**: No credentials are stored anywhere. The authentication flow is:

1. Script/server opens Chrome browser window
2. Navigates to Twitter Developer Portal billing page
3. User manually logs in through the browser (supports 2FA)
4. Script waits up to 5 minutes (300 seconds) for user to authenticate
5. Once URL contains "billing", authentication is confirmed
6. Browser session remains open for subsequent operations

### Running the MCP Server

**For Claude Desktop Integration:**

Add to `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS):

```json
{
  "mcpServers": {
    "twitter-invoice": {
      "command": "twitter-invoice"
    }
  }
}
```

Restart Claude Desktop. The browser will open when you ask Claude to access invoices.

### Running the CLI Script

```bash
# Download latest invoice
python twitter_invoice_downloader.py --latest

# Download all invoices
python twitter_invoice_downloader.py --all

# With custom config file
python twitter_invoice_downloader.py --config /path/to/.env --latest
```

### Configuration

Create `.env` file (optional):

```bash
INVOICE_DOWNLOAD_DIR=./invoices
# Note: TWITTER_USERNAME and TWITTER_PASSWORD are intentionally NOT used
# for security - manual authentication only
```

### Key Implementation Details

**Selenium Setup** ([src/twitter_invoice_mcp/server.py](src/twitter_invoice_mcp/server.py#L43-L69)):
- Chrome options set download directory and disable PDF viewer
- Prefs: `plugins.always_open_pdf_externally: true` to force PDF download
- Can optionally enable headless mode (line 60) but won't work for manual auth
- Can uncomment line 66 to use persistent Chrome profile for session reuse

**Invoice Detection** ([src/twitter_invoice_mcp/server.py](src/twitter_invoice_mcp/server.py#L124-L167)):
- Waits for `<table>` element on billing page
- Parses table rows to extract: transaction_id, date, subscription_period, amount, status
- Finds download buttons: `//button[contains(., 'pdf')]`
- Returns list of downloadable invoices

**Download Process** ([src/twitter_invoice_mcp/server.py](src/twitter_invoice_mcp/server.py#L169-L207)):
- Finds row by transaction ID
- Scrolls button into view
- Clicks PDF download button
- Waits 3 seconds for download to start

### Testing

**Test MCP Server Locally:**

```bash
# Run server directly to see stdio communication
twitter-invoice

# Or run the Python module
python -m twitter_invoice_mcp.server
```

**Test CLI Script:**

```bash
# Dry run - opens browser and lists invoices without downloading
python twitter_invoice_downloader.py --latest
```

### Common Issues

**ChromeDriver not found**: Selenium auto-downloads ChromeDriver, but if issues occur:
```bash
pip install webdriver-manager
```

**PDFs open in browser instead of downloading**: Check Chrome settings or the prefs in [src/twitter_invoice_mcp/server.py](src/twitter_invoice_mcp/server.py#L51-L56)

**Authentication timeout**: Increase timeout at [src/twitter_invoice_mcp/server.py](src/twitter_invoice_mcp/server.py#L341) from 300 to higher value

**UI selectors changed**: Twitter may update their portal UI. Update XPath selectors in:
- Table detection: line 132
- Row parsing: line 136
- PDF buttons: line 153

## Dataset Analysis MCP

### Architecture

**MCP Server** ([src/dataset_analysis/server.py](src/dataset_analysis/server.py)):
- Uses FastMCP framework (simpler than standard MCP)
- Wraps Hugging Face Dataset Viewer API
- Async implementation with httpx client
- Optional HF_TOKEN environment variable for private datasets

### Tools Provided

- `validate` - Check if dataset exists
- `get_info` - Get dataset metadata and structure

### Running

```bash
dataset-analysis
```

Add to Claude Desktop config:

```json
{
  "mcpServers": {
    "dataset-analysis": {
      "command": "dataset-analysis"
    }
  }
}
```

## Development Workflow

### Making Changes

1. **Edit source files** in `src/twitter_invoice_mcp/` or `src/dataset_analysis/`
2. **Reinstall** if entry points or dependencies change: `pip install -e .`
3. **Restart Claude Desktop** to reload MCP servers
4. **Test manually** by asking Claude to use the tools

### Adding New MCP Tools

**For Twitter Invoice Server** ([src/twitter_invoice_mcp/server.py](src/twitter_invoice_mcp/server.py)):

1. Add tool definition in `list_tools()` function (line 252)
2. Add handler in `call_tool()` function (line 325)
3. Implement logic in `TwitterInvoiceManager` class if needed

**For Dataset Analysis Server** ([src/dataset_analysis/server.py](src/dataset_analysis/server.py)):

1. Use `@mcp.tool()` decorator
2. FastMCP handles registration automatically

### Project Structure

```
mcp-fun/
├── src/
│   ├── dataset_analysis/           # Dataset MCP server
│   │   ├── __init__.py
│   │   └── server.py
│   └── twitter_invoice_mcp/        # Invoice MCP server
│       ├── __init__.py
│       └── server.py
├── twitter_invoice_downloader.py   # Standalone CLI script
├── pyproject.toml                  # Shared package config
├── prepare_dataset.ipynb          # Jupyter notebook for dataset work
├── data/                          # Dataset files
└── invoices/                      # Downloaded invoice PDFs (created at runtime)
```

### Recommended Reorganization

Consider splitting into:

```
mcp-fun/
├── invoice/
│   ├── pyproject.toml
│   ├── src/twitter_invoice_mcp/
│   ├── twitter_invoice_downloader.py
│   └── README.md
└── data-analysis/
    ├── pyproject.toml
    ├── src/dataset_analysis/
    ├── prepare_dataset.ipynb
    └── README.md
```

## Important Notes

- **Security**: Never commit `.env` files with credentials (already in `.gitignore`)
- **Browser State**: The MCP server keeps the browser open between tool calls - use `close_browser` tool to cleanup
- **Session Reuse**: Uncomment [line 66 in server.py](src/twitter_invoice_mcp/server.py#L66) to reuse Chrome profile and stay logged in
- **Error Handling**: Both MCP servers return errors as JSON strings, not exceptions
- **Async Context**: Dataset server is fully async; Invoice server uses sync Selenium in async wrapper

## Reference Documentation

- [MCP Server Documentation](https://modelcontextprotocol.io/)
- [FastMCP Documentation](https://github.com/jlowin/fastmcp)
- [Selenium WebDriver Docs](https://selenium-python.readthedocs.io/)
- [Hugging Face Dataset Viewer API](https://huggingface.co/docs/datasets-server/)
