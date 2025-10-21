"""
Gmail MCP Server - Secure Gmail Integration

This server provides secure Gmail access for Claude Desktop using:
- OAuth2 authentication (no password storage)
- macOS Keychain for encrypted token storage
- Minimal API scopes (gmail.readonly, gmail.send)
- Audit logging of all operations
- Tools: search, read, reply, reply all with attachments
"""

import asyncio
import json
import os
import sys
import base64
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

from mcp.server import Server
from mcp.types import Tool, TextContent

# Google API imports
try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    GOOGLE_API_AVAILABLE = True
except ImportError:
    GOOGLE_API_AVAILABLE = False

# Keychain storage import
try:
    import keyring
    KEYRING_AVAILABLE = True
except ImportError:
    KEYRING_AVAILABLE = False


# Gmail API scopes - minimal permissions
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send'
]

# Keychain service name
KEYCHAIN_SERVICE = "claude-gmail-mcp"
KEYCHAIN_USERNAME = "oauth-tokens"

# Audit log setup
LOG_DIR = Path.home() / ".gmail-mcp"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "audit.log"

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stderr)
    ]
)
logger = logging.getLogger(__name__)


class GmailManager:
    """Manages Gmail API operations with secure credential storage"""

    def __init__(self, credentials_path: Optional[str] = None):
        """
        Initialize Gmail manager

        Args:
            credentials_path: Path to Google OAuth credentials JSON file
        """
        if not GOOGLE_API_AVAILABLE:
            raise RuntimeError(
                "Google API libraries not installed. "
                "Install with: pip install google-auth-oauthlib google-auth-httplib2 google-api-python-client"
            )

        if not KEYRING_AVAILABLE:
            logger.warning("Keyring not available. Tokens will be stored in plaintext. Install with: pip install keyring")

        self.credentials_path = credentials_path or str(LOG_DIR / "credentials.json")
        self.service = None
        self._authenticated = False

    def _save_credentials(self, creds: Credentials) -> None:
        """Save credentials to keychain (encrypted) or file (fallback)"""
        creds_data = {
            'token': creds.token,
            'refresh_token': creds.refresh_token,
            'token_uri': creds.token_uri,
            'client_id': creds.client_id,
            'client_secret': creds.client_secret,
            'scopes': creds.scopes
        }

        creds_json = json.dumps(creds_data)

        if KEYRING_AVAILABLE:
            try:
                keyring.set_password(KEYCHAIN_SERVICE, KEYCHAIN_USERNAME, creds_json)
                logger.info("Credentials saved to macOS Keychain (encrypted)")
                return
            except Exception as e:
                logger.warning(f"Failed to save to keychain: {e}. Falling back to file storage.")

        # Fallback: save to file
        token_path = LOG_DIR / "token.json"
        with open(token_path, 'w') as f:
            json.dump(creds_data, f)
        logger.warning(f"Credentials saved to {token_path} (plaintext - less secure)")

    def _load_credentials(self) -> Optional[Credentials]:
        """Load credentials from keychain or file"""
        creds_json = None

        # Try keychain first
        if KEYRING_AVAILABLE:
            try:
                creds_json = keyring.get_password(KEYCHAIN_SERVICE, KEYCHAIN_USERNAME)
                if creds_json:
                    logger.info("Credentials loaded from macOS Keychain")
            except Exception as e:
                logger.warning(f"Failed to load from keychain: {e}")

        # Fallback: try file
        if not creds_json:
            token_path = LOG_DIR / "token.json"
            if token_path.exists():
                with open(token_path, 'r') as f:
                    creds_json = f.read()
                logger.warning("Credentials loaded from file (less secure)")

        if not creds_json:
            return None

        try:
            creds_data = json.loads(creds_json)
            creds = Credentials(
                token=creds_data['token'],
                refresh_token=creds_data.get('refresh_token'),
                token_uri=creds_data['token_uri'],
                client_id=creds_data['client_id'],
                client_secret=creds_data['client_secret'],
                scopes=creds_data['scopes']
            )
            return creds
        except Exception as e:
            logger.error(f"Failed to parse credentials: {e}")
            return None

    def authenticate(self) -> Dict[str, Any]:
        """Authenticate with Gmail API using OAuth2"""
        logger.info("Starting Gmail authentication")

        creds = self._load_credentials()

        # Refresh token if expired
        if creds and creds.expired and creds.refresh_token:
            try:
                logger.info("Refreshing expired token")
                creds.refresh(Request())
                self._save_credentials(creds)
            except Exception as e:
                logger.error(f"Token refresh failed: {e}")
                creds = None

        # New authentication flow if no valid credentials
        if not creds or not creds.valid:
            if not os.path.exists(self.credentials_path):
                return {
                    "status": "error",
                    "message": f"Credentials file not found at {self.credentials_path}. "
                               f"Please download OAuth credentials from Google Cloud Console."
                }

            try:
                logger.info("Starting new OAuth flow")
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path, SCOPES
                )
                creds = flow.run_local_server(port=0)
                self._save_credentials(creds)
                logger.info("Authentication successful")
            except Exception as e:
                logger.error(f"Authentication failed: {e}")
                return {
                    "status": "error",
                    "message": f"Authentication failed: {str(e)}"
                }

        # Build Gmail service
        try:
            self.service = build('gmail', 'v1', credentials=creds)
            self._authenticated = True
            logger.info("Gmail service initialized")
            return {
                "status": "authenticated",
                "message": "Successfully authenticated with Gmail"
            }
        except Exception as e:
            logger.error(f"Failed to build Gmail service: {e}")
            return {
                "status": "error",
                "message": f"Failed to initialize Gmail service: {str(e)}"
            }

    def search_emails(
        self,
        query: str,
        max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search for emails using Gmail search syntax

        Args:
            query: Gmail search query (e.g., "from:user@example.com subject:important")
            max_results: Maximum number of results to return
        """
        if not self._authenticated:
            return []

        logger.info(f"Searching emails: query='{query}', max_results={max_results}")

        try:
            results = self.service.users().messages().list(
                userId='me',
                q=query,
                maxResults=max_results
            ).execute()

            messages = results.get('messages', [])
            logger.info(f"Found {len(messages)} messages")

            email_list = []
            for msg in messages:
                msg_data = self.service.users().messages().get(
                    userId='me',
                    id=msg['id'],
                    format='metadata',
                    metadataHeaders=['From', 'To', 'Cc', 'Subject', 'Date']
                ).execute()

                headers = {h['name']: h['value'] for h in msg_data['payload']['headers']}

                email_list.append({
                    'id': msg['id'],
                    'thread_id': msg['threadId'],
                    'from': headers.get('From', ''),
                    'to': headers.get('To', ''),
                    'cc': headers.get('Cc', ''),
                    'subject': headers.get('Subject', ''),
                    'date': headers.get('Date', '')
                })

            return email_list

        except HttpError as e:
            logger.error(f"Gmail API error: {e}")
            return []
        except Exception as e:
            logger.error(f"Error searching emails: {e}")
            return []

    def get_email(self, message_id: str) -> Dict[str, Any]:
        """
        Get full email content by message ID

        Args:
            message_id: Gmail message ID
        """
        if not self._authenticated:
            return {"status": "error", "message": "Not authenticated"}

        logger.info(f"Getting email: message_id={message_id}")

        try:
            msg = self.service.users().messages().get(
                userId='me',
                id=message_id,
                format='full'
            ).execute()

            headers = {h['name']: h['value'] for h in msg['payload']['headers']}

            # Extract body
            body = ""
            if 'parts' in msg['payload']:
                for part in msg['payload']['parts']:
                    if part['mimeType'] == 'text/plain':
                        body = base64.urlsafe_b64decode(
                            part['body']['data']
                        ).decode('utf-8')
                        break
            elif 'body' in msg['payload'] and 'data' in msg['payload']['body']:
                body = base64.urlsafe_b64decode(
                    msg['payload']['body']['data']
                ).decode('utf-8')

            result = {
                'id': msg['id'],
                'thread_id': msg['threadId'],
                'from': headers.get('From', ''),
                'to': headers.get('To', ''),
                'cc': headers.get('Cc', ''),
                'subject': headers.get('Subject', ''),
                'date': headers.get('Date', ''),
                'body': body
            }

            logger.info(f"Retrieved email from {result['from']}")
            return result

        except HttpError as e:
            logger.error(f"Gmail API error: {e}")
            return {"status": "error", "message": str(e)}
        except Exception as e:
            logger.error(f"Error getting email: {e}")
            return {"status": "error", "message": str(e)}

    def reply_email(
        self,
        message_id: str,
        body: str,
        reply_all: bool = False,
        attachments: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Reply to an email

        Args:
            message_id: Gmail message ID to reply to
            body: Reply message body
            reply_all: If True, reply to all recipients
            attachments: List of file paths to attach
        """
        if not self._authenticated:
            return {"status": "error", "message": "Not authenticated"}

        logger.info(f"Replying to email: message_id={message_id}, reply_all={reply_all}")

        try:
            # Get original message
            original = self.service.users().messages().get(
                userId='me',
                id=message_id,
                format='full'
            ).execute()

            headers = {h['name']: h['value'] for h in original['payload']['headers']}
            thread_id = original['threadId']

            # Create reply message
            if attachments:
                message = MIMEMultipart()
                message.attach(MIMEText(body, 'plain'))

                # Add attachments
                for file_path in attachments:
                    if not os.path.exists(file_path):
                        logger.warning(f"Attachment not found: {file_path}")
                        continue

                    with open(file_path, 'rb') as f:
                        part = MIMEBase('application', 'octet-stream')
                        part.set_payload(f.read())
                        encoders.encode_base64(part)
                        part.add_header(
                            'Content-Disposition',
                            f'attachment; filename={os.path.basename(file_path)}'
                        )
                        message.attach(part)
                    logger.info(f"Attached file: {file_path}")
            else:
                message = MIMEText(body, 'plain')

            # Set headers
            message['To'] = headers.get('From', '')
            if reply_all:
                cc_list = []
                if 'To' in headers:
                    cc_list.append(headers['To'])
                if 'Cc' in headers:
                    cc_list.append(headers['Cc'])
                if cc_list:
                    message['Cc'] = ', '.join(cc_list)

            message['Subject'] = f"Re: {headers.get('Subject', '')}"
            message['In-Reply-To'] = headers.get('Message-ID', '')
            message['References'] = headers.get('Message-ID', '')

            # Encode and send
            raw = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')

            send_result = self.service.users().messages().send(
                userId='me',
                body={'raw': raw, 'threadId': thread_id}
            ).execute()

            logger.info(f"Email sent successfully: id={send_result['id']}")
            return {
                "status": "success",
                "message": f"Reply sent successfully",
                "message_id": send_result['id']
            }

        except HttpError as e:
            logger.error(f"Gmail API error: {e}")
            return {"status": "error", "message": str(e)}
        except Exception as e:
            logger.error(f"Error replying to email: {e}")
            return {"status": "error", "message": str(e)}


    def find_latest_invoice(self, invoice_dir: Optional[str] = None) -> Dict[str, Any]:
        """
        Find the latest Twitter invoice PDF in the downloads directory

        Args:
            invoice_dir: Directory to search for invoices (default: ~/Downloads/twitter-invoices)

        Returns:
            Dict with file info or error
        """
        if invoice_dir is None:
            invoice_dir = Path.home() / "Downloads" / "twitter-invoices"
        else:
            invoice_dir = Path(invoice_dir)

        logger.info(f"Looking for latest invoice in {invoice_dir}")

        if not invoice_dir.exists():
            return {
                "status": "error",
                "message": f"Invoice directory not found: {invoice_dir}"
            }

        # Find all PDF files
        pdf_files = list(invoice_dir.glob("*.pdf"))

        if not pdf_files:
            return {
                "status": "error",
                "message": f"No PDF files found in {invoice_dir}"
            }

        # Sort by modification time, newest first
        pdf_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
        latest_file = pdf_files[0]

        # Get file info
        stat_info = latest_file.stat()
        modified_time = datetime.fromtimestamp(stat_info.st_mtime)

        logger.info(f"Found latest invoice: {latest_file.name}, modified: {modified_time}")

        return {
            "status": "success",
            "file_path": str(latest_file.absolute()),
            "file_name": latest_file.name,
            "modified_time": modified_time.strftime("%Y-%m-%d %H:%M:%S"),
            "size_bytes": stat_info.st_size,
            "size_kb": round(stat_info.st_size / 1024, 2)
        }


# Global Gmail manager instance
gmail_manager = GmailManager()

# Create MCP server
app = Server("gmail-server")


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available Gmail tools"""
    return [
        Tool(
            name="authenticate_gmail",
            description="Authenticate with Gmail using OAuth2. Run this first before using other tools.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="search_emails",
            description="Search for emails using Gmail search syntax. "
                        "Examples: 'from:user@example.com', 'subject:important', 'has:attachment'",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Gmail search query"
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of results (default: 10)",
                        "default": 10
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="get_email",
            description="Get full email content by message ID",
            inputSchema={
                "type": "object",
                "properties": {
                    "message_id": {
                        "type": "string",
                        "description": "Gmail message ID"
                    }
                },
                "required": ["message_id"]
            }
        ),
        Tool(
            name="reply_email",
            description="Reply to an email. Can reply to sender only or reply all. Supports attachments.",
            inputSchema={
                "type": "object",
                "properties": {
                    "message_id": {
                        "type": "string",
                        "description": "Gmail message ID to reply to"
                    },
                    "body": {
                        "type": "string",
                        "description": "Reply message body"
                    },
                    "reply_all": {
                        "type": "boolean",
                        "description": "If true, reply to all recipients (default: false)",
                        "default": False
                    },
                    "attachments": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of file paths to attach"
                    }
                },
                "required": ["message_id", "body"]
            }
        ),
        Tool(
            name="find_latest_invoice",
            description="ALWAYS use this tool first when user asks to attach or send a Twitter invoice. "
                        "Automatically finds the latest Twitter invoice PDF file in ~/Downloads/twitter-invoices/. "
                        "Returns file info (name, path, timestamp). "
                        "IMPORTANT: After getting the file info, present it to the user for confirmation before sending: "
                        "'I found: [filename] (saved: [timestamp]). Should I attach this and send the email?' "
                        "Wait for user confirmation (yes/proceed) before calling reply_email.",
            inputSchema={
                "type": "object",
                "properties": {
                    "invoice_dir": {
                        "type": "string",
                        "description": "Directory to search (default: ~/Downloads/twitter-invoices)"
                    }
                },
                "required": []
            }
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls"""

    if not GOOGLE_API_AVAILABLE:
        return [TextContent(
            type="text",
            text="Error: Google API libraries not installed. "
                 "Install with: pip install google-auth-oauthlib google-auth-httplib2 google-api-python-client"
        )]

    try:
        if name == "authenticate_gmail":
            result = gmail_manager.authenticate()
            return [TextContent(
                type="text",
                text=json.dumps(result, indent=2)
            )]

        elif name == "search_emails":
            query = arguments.get("query", "")
            max_results = arguments.get("max_results", 10)

            if not query:
                return [TextContent(
                    type="text",
                    text="Error: query parameter is required"
                )]

            emails = gmail_manager.search_emails(query, max_results)
            return [TextContent(
                type="text",
                text=json.dumps({
                    "status": "success",
                    "count": len(emails),
                    "emails": emails
                }, indent=2)
            )]

        elif name == "get_email":
            message_id = arguments.get("message_id", "")

            if not message_id:
                return [TextContent(
                    type="text",
                    text="Error: message_id parameter is required"
                )]

            email = gmail_manager.get_email(message_id)
            return [TextContent(
                type="text",
                text=json.dumps(email, indent=2)
            )]

        elif name == "reply_email":
            message_id = arguments.get("message_id", "")
            body = arguments.get("body", "")
            reply_all = arguments.get("reply_all", False)
            attachments = arguments.get("attachments", [])

            if not message_id or not body:
                return [TextContent(
                    type="text",
                    text="Error: message_id and body parameters are required"
                )]

            result = gmail_manager.reply_email(
                message_id,
                body,
                reply_all,
                attachments
            )
            return [TextContent(
                type="text",
                text=json.dumps(result, indent=2)
            )]

        elif name == "find_latest_invoice":
            invoice_dir = arguments.get("invoice_dir")
            result = gmail_manager.find_latest_invoice(invoice_dir)
            return [TextContent(
                type="text",
                text=json.dumps(result, indent=2)
            )]

        else:
            return [TextContent(
                type="text",
                text=f"Error: Unknown tool '{name}'"
            )]

    except Exception as e:
        logger.error(f"Tool execution error: {e}")
        return [TextContent(
            type="text",
            text=f"Error: {str(e)}"
        )]


async def main():
    """Run the MCP server"""
    from mcp.server.stdio import stdio_server

    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())
