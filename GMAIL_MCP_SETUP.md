# Gmail MCP Server Setup Guide

## Overview

This Gmail MCP server provides secure Gmail integration for Claude Desktop with:
- **OAuth2 Authentication** - No passwords stored, only OAuth tokens
- **Encrypted Storage** - Tokens stored in macOS Keychain (encrypted)
- **Minimal Scopes** - Only requests `gmail.readonly` and `gmail.send` permissions
- **Audit Logging** - All operations logged to `~/.gmail-mcp/audit.log`
- **Limited Functionality** - Only search, read, and reply features (no delete/modify)

## Security Features

✅ **No password storage** - Uses Google OAuth2
✅ **Encrypted tokens** - Stored in macOS Keychain
✅ **Minimal permissions** - Only read and send (no delete/modify)
✅ **Audit trail** - All operations logged
✅ **Revokable access** - Can revoke from Google Account settings anytime
✅ **Local only** - No third-party services or data sharing

## Prerequisites

1. Python 3.12+ installed
2. Google Account with Gmail
3. Access to Google Cloud Console

## Step 1: Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or select existing one)
3. Name it something like "Claude Gmail MCP"

## Step 2: Enable Gmail API

1. In your Google Cloud project, go to **APIs & Services** > **Library**
2. Search for "Gmail API"
3. Click **Enable**

## Step 3: Create OAuth Credentials

1. Go to **APIs & Services** > **Credentials**
2. Click **Create Credentials** > **OAuth client ID**
3. If prompted, configure the OAuth consent screen:
   - User Type: **External** (unless you have a Google Workspace)
   - App name: `Claude Gmail MCP`
   - User support email: Your email
   - Developer contact: Your email
   - Scopes: Click **Add or Remove Scopes**, then add:
     - `https://www.googleapis.com/auth/gmail.readonly`
     - `https://www.googleapis.com/auth/gmail.send`
   - Test users: Add your email address
4. Back to Create OAuth client ID:
   - Application type: **Desktop app**
   - Name: `Claude Gmail MCP`
5. Click **Create**
6. Download the credentials JSON file
7. Save it as: `~/.gmail-mcp/credentials.json`

```bash
mkdir -p ~/.gmail-mcp
# Move your downloaded file to:
mv ~/Downloads/client_secret_*.json ~/.gmail-mcp/credentials.json
```

## Step 4: Install the Package

The package is already installed if you ran:

```bash
cd /Users/aprilxu/Documents/GitHub/mcp-fun
pip install -e .
```

Verify the command is available:

```bash
which gmail-mcp
# Should output: /Users/aprilxu/miniconda3/bin/gmail-mcp
```

## Step 5: Configure Claude Desktop

Add the Gmail MCP server to your Claude Desktop config:

```bash
# Edit the config file
code ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

Add this entry to the `mcpServers` section:

```json
{
    "mcpServers": {
        "gmail": {
            "command": "/Users/aprilxu/miniconda3/bin/gmail-mcp"
        }
    }
}
```

Full example config:

```json
{
    "mcpServers": {
        "filesystem": {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-filesystem", "/Users/aprilxu/Desktop/mcp_project/"]
        },
        "research": {
            "command": "uv",
            "args": ["--directory", "/Users/aprilxu/Desktop/mcp_project/", "run", "research_server.py"]
        },
        "fetch": {
            "command": "uvx",
            "args": ["mcp-server-fetch"]
        },
        "dataset-analysis": {
            "command": "/Users/aprilxu/miniconda3/bin/dataset-analysis"
        },
        "twitter-invoice": {
            "command": "/Users/aprilxu/miniconda3/bin/twitter-invoice"
        },
        "gmail": {
            "command": "/Users/aprilxu/miniconda3/bin/gmail-mcp"
        }
    }
}
```

## Step 6: First Run Authentication

1. **Restart Claude Desktop** completely (Quit and reopen)

2. In Claude Desktop, ask: `"Please authenticate with Gmail"`

3. A browser window will open with Google OAuth consent screen:
   - Select your Google account
   - Review permissions (read and send only)
   - Click **Allow**

4. You'll see "The authentication flow has completed. You may close this window."

5. Your OAuth tokens are now stored in macOS Keychain (encrypted)

## Step 7: Verify It Works

Try these commands in Claude Desktop:

```
Search for emails from april.xu@masterclass.com with subject containing "Coupa"
```

```
Show me my latest 5 emails
```

## Available Tools

### 1. `authenticate_gmail`
Authenticate with Gmail (run this first)

### 2. `search_emails`
Search for emails using Gmail search syntax

**Examples:**
- `from:user@example.com`
- `subject:invoice`
- `from:user@example.com subject:important`
- `has:attachment`
- `after:2025/10/01`

### 3. `get_email`
Get full email content by message ID

### 4. `reply_email`
Reply to an email with optional attachments

**Options:**
- `reply_all`: true/false (default: false)
- `attachments`: Array of file paths

## Usage Example

**Your original request:**

> "Look for an email from april.xu@masterclass.com with subject [ACTION REQUIRED] Coupa vCard Receipt. Reply all with the PDF as an attachment."

**How Claude will handle it:**

1. Authenticate (if needed)
2. Search: `from:april.xu@masterclass.com subject:"[ACTION REQUIRED] Coupa vCard Receipt"`
3. Get the email content
4. Reply all with the invoice PDF attached

## Security Best Practices

### Viewing Stored Credentials

```bash
# Check audit log
cat ~/.gmail-mcp/audit.log

# View token in keychain (requires authentication)
security find-generic-password -s "claude-gmail-mcp" -w
```

### Revoking Access

To revoke Gmail access:

1. Go to [Google Account Permissions](https://myaccount.google.com/permissions)
2. Find "Claude Gmail MCP"
3. Click **Remove Access**

Or delete stored credentials:

```bash
# Remove from keychain
security delete-generic-password -s "claude-gmail-mcp"

# Remove backup file (if exists)
rm ~/.gmail-mcp/token.json

# Remove credentials (will require re-download from Google Cloud)
rm ~/.gmail-mcp/credentials.json
```

### Viewing Audit Log

All Gmail operations are logged:

```bash
tail -f ~/.gmail-mcp/audit.log
```

Example log entries:
```
2025-10-20 17:50:12,345 - INFO - Starting Gmail authentication
2025-10-20 17:50:15,123 - INFO - Credentials loaded from macOS Keychain
2025-10-20 17:50:16,789 - INFO - Gmail service initialized
2025-10-20 17:51:20,456 - INFO - Searching emails: query='from:april.xu@masterclass.com', max_results=10
2025-10-20 17:51:22,123 - INFO - Found 3 messages
2025-10-20 17:52:10,789 - INFO - Replying to email: message_id=abc123, reply_all=True
2025-10-20 17:52:12,456 - INFO - Attached file: /Users/aprilxu/Downloads/twitter-invoices/X-API-Invoice-683795.pdf
2025-10-20 17:52:15,123 - INFO - Email sent successfully: id=xyz789
```

## Troubleshooting

### Error: "Credentials file not found"

Create the credentials file:
```bash
mkdir -p ~/.gmail-mcp
# Download from Google Cloud Console and save as:
mv ~/Downloads/client_secret_*.json ~/.gmail-mcp/credentials.json
```

### Error: "Failed to save to keychain"

Keyring might not be working. The system will fall back to file storage:
```bash
# Check if token file was created
ls -la ~/.gmail-mcp/token.json
```

### Error: "Invalid grant" or "Token expired"

Re-authenticate:
```bash
# Delete old tokens
security delete-generic-password -s "claude-gmail-mcp"
rm ~/.gmail-mcp/token.json

# Restart Claude Desktop and authenticate again
```

### MCP Server Not Showing Up

1. Check the config file path is correct:
   ```bash
   which gmail-mcp
   ```

2. Restart Claude Desktop completely (Quit and reopen)

3. Check logs:
   ```bash
   tail -f ~/Library/Logs/Claude/mcp-server-gmail.log
   ```

## Limitations

- **Read-only and send only** - Cannot delete or permanently modify emails
- **No drafts** - Cannot save drafts (would require additional scope)
- **No labels** - Cannot modify labels (would require gmail.modify scope)
- **Attachment size** - Gmail limits attachments to 25MB
- **Rate limits** - Subject to Gmail API rate limits

## Files and Directories

- `~/.gmail-mcp/credentials.json` - OAuth credentials from Google Cloud
- `~/.gmail-mcp/token.json` - Backup token storage (if keychain fails)
- `~/.gmail-mcp/audit.log` - Audit log of all operations
- `macOS Keychain` - Encrypted token storage (service: "claude-gmail-mcp")

## Support

For issues or questions:
1. Check the audit log: `~/.gmail-mcp/audit.log`
2. Check Claude Desktop logs: `~/Library/Logs/Claude/`
3. Review Google Cloud Console for API errors

## Architecture

```
Claude Desktop
    ↓
MCP Protocol (stdio)
    ↓
Gmail MCP Server (Python)
    ↓
Google OAuth2 + Gmail API
    ↓
Your Gmail Account
```

**Token Flow:**
1. First auth: Browser OAuth → Tokens saved to Keychain (encrypted)
2. Subsequent uses: Load from Keychain → Refresh if expired
3. Revoke: Delete from Keychain or Google Account settings
