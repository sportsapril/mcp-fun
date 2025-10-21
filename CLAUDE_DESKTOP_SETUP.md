# Setting Up Twitter Invoice MCP Server in Claude Desktop

This guide will help you configure the Twitter Invoice MCP server to work with Claude Desktop.

## Prerequisites

1. **Claude Desktop** installed
2. **Python 3.12+** installed
3. **Chrome browser** installed
4. **Project dependencies** installed

## Installation Steps

### 1. Install the MCP Server

From the project directory:

```bash
# Install the project and dependencies
pip install -e .

# Or if using uv (recommended)
uv pip install -e .
```

This will install:
- The `twitter-invoice` command
- All required dependencies (mcp, selenium, httpx)

### 2. Verify Installation

Test that the server is installed correctly:

```bash
# Check if the command is available
which twitter-invoice

# Or on Windows
where twitter-invoice
```

### 3. Configure Claude Desktop

Add the MCP server to your Claude Desktop configuration file:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`

**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

**Linux**: `~/.config/Claude/claude_desktop_config.json`

Add this configuration:

```json
{
  "mcpServers": {
    "twitter-invoice": {
      "command": "twitter-invoice"
    }
  }
}
```

If you already have other MCP servers configured, add the twitter-invoice entry to your existing config:

```json
{
  "mcpServers": {
    "dataset-analysis": {
      "command": "dataset-analysis"
    },
    "twitter-invoice": {
      "command": "twitter-invoice"
    }
  }
}
```

### 4. Restart Claude Desktop

After updating the configuration:
1. Completely quit Claude Desktop (not just close the window)
2. Restart Claude Desktop
3. The MCP server should now be available

## Usage in Claude Desktop

Once configured, you can ask Claude to help with invoice management:

### Example Conversations

**Download the latest invoice:**
```
Please download my latest Twitter Developer invoice
```

**List all invoices:**
```
Show me all my Twitter Developer Portal invoices
```

**Download all invoices:**
```
Download all my Twitter invoices
```

**Download specific invoice:**
```
Download invoice #668250 from my Twitter Developer account
```

## How It Works

### No Credentials Stored

The MCP server **does not store any credentials**. Instead:

1. When you ask Claude to access invoices, it will open a Chrome browser
2. You'll see the Twitter Developer Portal login page
3. You log in manually using your regular credentials (including 2FA if enabled)
4. The browser stays open for 5 minutes (300 seconds) waiting for you to complete authentication
5. Once logged in, Claude can access the billing page and download invoices
6. The browser window stays open until you ask Claude to close it or the conversation ends

### Security Benefits

- **No stored passwords**: Your credentials are never saved
- **2FA supported**: You can use your normal 2FA flow
- **Browser-based**: Uses the same authentication flow as if you were doing it manually
- **Session-based**: Reuses your browser session if you're already logged in

## Available Tools

The MCP server provides these tools to Claude:

1. **open_billing_page** - Opens the Twitter Developer Portal and handles authentication
2. **list_invoices** - Shows all available invoices with details
3. **download_invoice** - Downloads a specific invoice by ID
4. **download_all_invoices** - Downloads all available invoices
5. **download_latest_invoice** - Downloads only the most recent invoice
6. **close_browser** - Closes the browser window

## Downloaded Files Location

Invoices are downloaded to: `./invoices/` in your project directory

Or the path specified in your `.env` file:
```bash
INVOICE_DOWNLOAD_DIR=/path/to/invoices
```

## Troubleshooting

### Server Not Showing Up

1. Check that the command is installed:
   ```bash
   twitter-invoice --help
   ```

2. Check the path in your Claude Desktop config:
   ```bash
   which twitter-invoice  # Use this path in the config
   ```

3. Try using the full path in the config:
   ```json
   {
     "mcpServers": {
       "twitter-invoice": {
         "command": "/full/path/to/twitter-invoice"
       }
     }
   }
   ```

### Browser Not Opening

1. Make sure Chrome is installed
2. Check that selenium is installed:
   ```bash
   pip list | grep selenium
   ```

3. Install ChromeDriver if needed:
   ```bash
   pip install webdriver-manager
   ```

### Authentication Timeout

If the 5-minute timeout isn't enough:

1. Edit [src/twitter_invoice_mcp/server.py](src/twitter_invoice_mcp/server.py)
2. Find the line: `auth_result = invoice_manager.wait_for_authentication(timeout=300)`
3. Change `300` to a longer timeout (in seconds)

### PDFs Not Downloading

1. Check the download directory exists and is writable
2. Check Chrome download settings
3. Look in your Chrome default downloads folder

## Advanced Configuration

### Custom Download Directory

Create a `.env` file in the project root:

```bash
INVOICE_DOWNLOAD_DIR=/Users/yourusername/Documents/Twitter-Invoices
```

### Headless Mode (No Browser Window)

Edit [src/twitter_invoice_mcp/server.py](src/twitter_invoice_mcp/server.py#L53):

```python
self.setup_driver(headless=True)  # Change False to True
```

**Note**: Headless mode won't work for manual authentication. Use only if you have an existing authenticated session.

### Using Existing Chrome Profile

To reuse your existing Chrome session (stay logged in):

Edit [src/twitter_invoice_mcp/server.py](src/twitter_invoice_mcp/server.py#L72):

Uncomment:
```python
chrome_options.add_argument(f"user-data-dir={Path.home()}/.chrome-mcp-profile")
```

## Example Workflow

Here's a typical monthly workflow:

1. **First day of the month**, open Claude Desktop
2. Ask: "Please download my latest Twitter Developer invoice"
3. Claude opens the browser to Twitter Developer Portal
4. You log in (if needed)
5. Claude downloads the invoice
6. Invoice saved to `./invoices/` directory
7. You can then email it to accounting or have Claude help with that

## Automation Ideas

### Send to Accounting Team

You could extend this to automatically email invoices:

"Claude, download my latest Twitter invoice and draft an email to accounting@company.com with the invoice attached"

### Monthly Report

"Claude, list all my Twitter invoices from this year and create a summary report with total costs"

### Bulk Download

"Claude, download all my Twitter invoices from the past 6 months"

## Privacy & Security Notes

- The server runs locally on your machine
- No data is sent to external servers (except Twitter/X for authentication)
- Your credentials are never stored in files or environment variables
- The browser session is temporary and cleaned up when closed
- All invoice PDFs are saved locally to your specified directory

## Support

If you encounter issues:

1. Check the Claude Desktop logs
2. Check the terminal output when running `twitter-invoice` directly
3. Verify Chrome and ChromeDriver are compatible versions
4. Make sure you have the latest version of the code

## Uninstalling

To remove the MCP server:

1. Remove the entry from Claude Desktop config
2. Restart Claude Desktop
3. Optionally uninstall the package:
   ```bash
   pip uninstall dataset-analysis-mcp
   ```
