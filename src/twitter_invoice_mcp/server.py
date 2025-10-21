"""
MCP Server for Twitter Developer Portal Invoice Management

This server provides tools to automate downloading invoices from the
Twitter/X Developer Portal. No credentials are stored - authentication
happens through the browser using your existing session or manual login.
"""

import asyncio
import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
import sys

from mcp.server import Server
from mcp.types import Tool, TextContent, ImageContent, EmbeddedResource

# Selenium imports
try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.options import Options
    from selenium.common.exceptions import TimeoutException, NoSuchElementException
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False


class TwitterInvoiceManager:
    """Manages browser automation for invoice downloads"""

    def __init__(self, download_dir: str = "./invoices"):
        self.download_dir = Path(download_dir).expanduser().absolute()
        self.driver = None
        self._authenticated = False

    def _ensure_download_dir(self):
        """Create download directory if it doesn't exist"""
        try:
            self.download_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            # If we can't create in current dir, use home directory
            self.download_dir = Path.home() / "Downloads" / "twitter-invoices"
            self.download_dir.mkdir(parents=True, exist_ok=True)

    def setup_driver(self, headless: bool = False):
        """Setup Chrome WebDriver with appropriate options"""
        if not SELENIUM_AVAILABLE:
            raise RuntimeError("Selenium not installed. Install with: pip install selenium")

        # Ensure download directory exists before setting up Chrome
        self._ensure_download_dir()

        chrome_options = Options()

        # Set download directory
        prefs = {
            "download.default_directory": str(self.download_dir.absolute()),
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "plugins.always_open_pdf_externally": True
        }
        chrome_options.add_experimental_option("prefs", prefs)

        if headless:
            chrome_options.add_argument("--headless")

        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")

        # Use persistent Chrome profile to stay logged in between sessions
        profile_dir = Path.home() / ".chrome-mcp-profile"

        # Try to kill any existing Chrome processes using this profile
        try:
            import subprocess
            # Kill using multiple patterns to be more thorough
            subprocess.run(["pkill", "-f", "chrome.*mcp-profile"], capture_output=True)
            subprocess.run(["pkill", "-f", "chromedriver"], capture_output=True)
            time.sleep(2)  # Give processes time to die
            print("Cleaned up existing Chrome processes", file=sys.stderr)
        except Exception as e:
            print(f"Warning: Could not kill existing Chrome processes: {e}", file=sys.stderr)

        chrome_options.add_argument(f"user-data-dir={profile_dir}")

        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.set_window_size(1920, 1080)

    def navigate_to_billing(self) -> Dict[str, Any]:
        """Navigate to Twitter Developer Portal billing page"""
        if not self.driver:
            self.setup_driver(headless=False)

        print("Navigating to Twitter Developer Portal billing page...", file=sys.stderr)

        # Navigate to the billing page
        target_url = "https://developer.x.com/en/account/billing"
        self.driver.get(target_url)

        # Wait longer for page to load and check multiple times
        max_attempts = 10
        for attempt in range(max_attempts):
            time.sleep(2)
            current_url = self.driver.current_url
            print(f"Attempt {attempt + 1}: Current URL: {current_url}", file=sys.stderr)

            # Check if we're on the billing page
            if "billing" in current_url.lower() and "developer" in current_url.lower():
                self._authenticated = True
                print("Successfully reached billing page", file=sys.stderr)
                return {
                    "status": "authenticated",
                    "message": "Already logged in and on billing page",
                    "url": current_url
                }

            # If we got redirected to x.com/home or login, we need authentication
            if "x.com/home" in current_url or "login" in current_url.lower():
                print(f"Redirected to {current_url}, need to navigate back", file=sys.stderr)
                # Try navigating to billing page again
                if attempt < max_attempts - 1:
                    self.driver.get(target_url)
                    continue
                else:
                    self._authenticated = False
                    return {
                        "status": "needs_auth",
                        "message": "Please complete login in the browser window. The browser will remain open for you to authenticate.",
                        "url": current_url
                    }

            # If we're on some intermediate page, wait a bit more
            if attempt < max_attempts - 1:
                time.sleep(1)

        # After all attempts, check final state
        current_url = self.driver.current_url
        if "billing" in current_url.lower():
            self._authenticated = True
            return {
                "status": "authenticated",
                "message": "Already logged in and on billing page",
                "url": current_url
            }
        else:
            self._authenticated = False
            return {
                "status": "needs_auth",
                "message": "Please complete login in the browser window. The browser will remain open for you to authenticate.",
                "url": current_url
            }

    def wait_for_authentication(self, timeout: int = 300) -> Dict[str, Any]:
        """Wait for user to complete authentication manually"""
        if not self.driver:
            return {"status": "error", "message": "Browser not initialized"}

        print(f"Waiting up to {timeout} seconds for authentication...", file=sys.stderr)
        start_time = time.time()

        while time.time() - start_time < timeout:
            current_url = self.driver.current_url
            if "billing" in current_url.lower():
                self._authenticated = True
                return {
                    "status": "authenticated",
                    "message": "Successfully authenticated and on billing page",
                    "url": current_url
                }
            time.sleep(2)

        return {
            "status": "timeout",
            "message": "Authentication timeout. Please try again."
        }

    def get_invoice_list(self) -> List[Dict[str, str]]:
        """Extract invoice information from the billing page"""
        if not self._authenticated:
            return []

        try:
            # Wait for the transaction table to load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//table"))
            )

            # Find all table rows with invoices
            rows = self.driver.find_elements(By.XPATH, "//table//tbody//tr")

            invoices = []
            for row in rows:
                try:
                    cells = row.find_elements(By.TAG_NAME, "td")
                    if len(cells) >= 5:
                        invoice_data = {
                            "transaction_id": cells[0].text.strip(),
                            "date": cells[1].text.strip(),
                            "subscription_period": cells[2].text.strip() if len(cells) > 2 else "",
                            "amount": cells[3].text.strip() if len(cells) > 3 else "",
                            "status": cells[4].text.strip() if len(cells) > 4 else "",
                        }

                        # Check if download button exists
                        try:
                            button = row.find_element(By.XPATH, ".//button[contains(., 'pdf')]")
                            invoice_data["downloadable"] = True
                        except NoSuchElementException:
                            invoice_data["downloadable"] = False

                        invoices.append(invoice_data)
                except Exception as e:
                    print(f"Error parsing row: {e}", file=sys.stderr)
                    continue

            return invoices

        except Exception as e:
            print(f"Error getting invoice list: {e}", file=sys.stderr)
            return []

    def download_invoice_by_id(self, transaction_id: str) -> Dict[str, Any]:
        """Download a specific invoice by transaction ID"""
        if not self._authenticated:
            return {"status": "error", "message": "Not authenticated"}

        try:
            # Ensure transaction ID has # prefix for matching
            if not transaction_id.startswith("#"):
                transaction_id = f"#{transaction_id}"

            print(f"Looking for invoice with ID: {transaction_id}", file=sys.stderr)

            # Wait for the table to be fully loaded
            time.sleep(2)

            # Find the row containing this transaction ID
            row = None

            # Try multiple approaches to find the row
            # Approach 1: Find row by link text
            try:
                link = self.driver.find_element(By.LINK_TEXT, transaction_id)
                row = link.find_element(By.XPATH, "./ancestor::tr")
                print(f"Found row using link text: {transaction_id}", file=sys.stderr)
            except NoSuchElementException:
                print(f"Link text approach failed, trying XPath...", file=sys.stderr)

            # Approach 2: Find row by text content anywhere in the row
            if not row:
                try:
                    row = self.driver.find_element(
                        By.XPATH,
                        f"//tr[.//*[contains(text(), '{transaction_id}')]]"
                    )
                    print(f"Found row using XPath text search: {transaction_id}", file=sys.stderr)
                except NoSuchElementException:
                    print(f"XPath text search failed for {transaction_id}", file=sys.stderr)

            # Approach 3: Search through all rows manually
            if not row:
                try:
                    print(f"Trying to search all rows manually...", file=sys.stderr)
                    transaction_id_no_hash = transaction_id.lstrip("#")
                    all_rows = self.driver.find_elements(By.XPATH, "//table//tbody//tr")
                    print(f"Found {len(all_rows)} total rows to search", file=sys.stderr)

                    for idx, table_row in enumerate(all_rows):
                        try:
                            # Get the first cell which should contain the transaction ID
                            first_cell = table_row.find_element(By.TAG_NAME, "td")
                            cell_text = first_cell.text.strip()

                            # Check if this row contains our transaction ID
                            if transaction_id in cell_text or transaction_id_no_hash in cell_text:
                                print(f"Found matching row at index {idx}, cell text: '{cell_text}'", file=sys.stderr)
                                row = table_row
                                break
                        except Exception as e:
                            continue

                    if not row:
                        print(f"Manual search through all rows failed to find {transaction_id}", file=sys.stderr)
                except Exception as e:
                    print(f"Error during manual row search: {e}", file=sys.stderr)

            if not row:
                return {
                    "status": "error",
                    "message": f"Invoice {transaction_id} not found"
                }

            # Now find the download button in this row
            button = None
            try:
                # Try to find button containing "pdf" text
                buttons = row.find_elements(By.TAG_NAME, "button")
                print(f"Found {len(buttons)} buttons in row", file=sys.stderr)

                for idx, btn in enumerate(buttons):
                    btn_text = btn.text.lower()
                    print(f"Button {idx}: text='{btn.text}', visible={btn.is_displayed()}", file=sys.stderr)
                    if 'pdf' in btn_text:
                        button = btn
                        print(f"Selected button {idx} with pdf text", file=sys.stderr)
                        break

                # If no button with "pdf", just take the last button (should be download)
                if not button and buttons:
                    button = buttons[-1]
                    print(f"Using last button as fallback", file=sys.stderr)

            except Exception as e:
                print(f"Error finding buttons: {e}", file=sys.stderr)

            if not button:
                print(f"Could not find download button for {transaction_id}", file=sys.stderr)
                return {
                    "status": "error",
                    "message": f"Download button not found for invoice {transaction_id}"
                }

            # Scroll to button and ensure it's visible
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", button)
            time.sleep(1)

            # Try clicking with JavaScript if regular click fails
            try:
                button.click()
                print(f"Clicked download button for {transaction_id}", file=sys.stderr)
            except Exception as e:
                print(f"Regular click failed: {e}, trying JavaScript click", file=sys.stderr)
                self.driver.execute_script("arguments[0].click();", button)
                print(f"JavaScript click executed for {transaction_id}", file=sys.stderr)

            time.sleep(3)  # Wait for download to start

            return {
                "status": "success",
                "message": f"Invoice {transaction_id} download initiated",
                "download_dir": str(self.download_dir.absolute())
            }

        except NoSuchElementException as e:
            print(f"NoSuchElementException: {str(e)}", file=sys.stderr)
            return {
                "status": "error",
                "message": f"Invoice {transaction_id} not found or not downloadable"
            }
        except Exception as e:
            print(f"Exception during download: {str(e)}", file=sys.stderr)
            return {
                "status": "error",
                "message": f"Error downloading invoice: {str(e)}"
            }

    def download_all_invoices(self) -> Dict[str, Any]:
        """Download all available invoices"""
        if not self._authenticated:
            return {"status": "error", "message": "Not authenticated"}

        invoices = self.get_invoice_list()
        downloadable = [inv for inv in invoices if inv.get("downloadable", False)]

        downloaded = []
        failed = []

        for invoice in downloadable:
            result = self.download_invoice_by_id(invoice["transaction_id"])
            if result["status"] == "success":
                downloaded.append(invoice["transaction_id"])
            else:
                failed.append(invoice["transaction_id"])
            time.sleep(1)  # Wait between downloads

        return {
            "status": "completed",
            "downloaded": downloaded,
            "failed": failed,
            "total": len(downloadable),
            "download_dir": str(self.download_dir.absolute())
        }

    def cleanup(self):
        """Close the browser"""
        if self.driver:
            self.driver.quit()
            self.driver = None
            self._authenticated = False


# Global manager instance
invoice_manager = TwitterInvoiceManager()


# Create MCP server
app = Server("twitter-invoice-server")


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available invoice management tools"""
    return [
        Tool(
            name="open_billing_page",
            description="Open the Twitter Developer Portal billing page in a browser. "
                        "If not logged in, you'll need to authenticate manually in the browser window. "
                        "The browser will stay open for you to complete authentication.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="list_invoices",
            description="List all available invoices from the Twitter Developer Portal. "
                        "Shows transaction IDs, dates, amounts, and download status. "
                        "You must open the billing page first.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="download_invoice",
            description="Download a specific invoice by transaction ID. "
                        "The invoice will be saved as a PDF in the downloads folder.",
            inputSchema={
                "type": "object",
                "properties": {
                    "transaction_id": {
                        "type": "string",
                        "description": "The transaction ID of the invoice to download (e.g., #668250)"
                    }
                },
                "required": ["transaction_id"]
            }
        ),
        Tool(
            name="download_all_invoices",
            description="Download all available invoices from the Twitter Developer Portal. "
                        "All PDFs will be saved in the downloads folder.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="download_latest_invoice",
            description="Download only the most recent invoice. "
                        "Useful for monthly automation tasks.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="close_browser",
            description="Close the browser window and cleanup resources.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls"""

    if not SELENIUM_AVAILABLE:
        return [TextContent(
            type="text",
            text="Error: Selenium not installed. Please install with: pip install selenium"
        )]

    try:
        if name == "open_billing_page":
            result = invoice_manager.navigate_to_billing()

            if result["status"] == "needs_auth":
                # Wait for authentication
                auth_result = invoice_manager.wait_for_authentication(timeout=300)
                result = auth_result

            return [TextContent(
                type="text",
                text=json.dumps(result, indent=2)
            )]

        elif name == "list_invoices":
            if not invoice_manager._authenticated:
                return [TextContent(
                    type="text",
                    text="Error: Not authenticated. Please use 'open_billing_page' tool first."
                )]

            invoices = invoice_manager.get_invoice_list()
            return [TextContent(
                type="text",
                text=json.dumps({
                    "status": "success",
                    "count": len(invoices),
                    "invoices": invoices
                }, indent=2)
            )]

        elif name == "download_invoice":
            transaction_id = arguments.get("transaction_id", "").strip()
            if not transaction_id:
                return [TextContent(
                    type="text",
                    text="Error: transaction_id is required"
                )]

            # Remove # if present
            transaction_id = transaction_id.lstrip("#")

            result = invoice_manager.download_invoice_by_id(transaction_id)
            return [TextContent(
                type="text",
                text=json.dumps(result, indent=2)
            )]

        elif name == "download_all_invoices":
            result = invoice_manager.download_all_invoices()
            return [TextContent(
                type="text",
                text=json.dumps(result, indent=2)
            )]

        elif name == "download_latest_invoice":
            invoices = invoice_manager.get_invoice_list()
            if not invoices:
                return [TextContent(
                    type="text",
                    text="Error: No invoices found"
                )]

            # Get the first (most recent) downloadable invoice
            latest = None
            for inv in invoices:
                if inv.get("downloadable", False):
                    latest = inv
                    break

            if not latest:
                return [TextContent(
                    type="text",
                    text="Error: No downloadable invoices found"
                )]

            # Strip # from transaction_id to match download_invoice behavior
            transaction_id = latest["transaction_id"].lstrip("#")
            result = invoice_manager.download_invoice_by_id(transaction_id)
            return [TextContent(
                type="text",
                text=json.dumps(result, indent=2)
            )]

        elif name == "close_browser":
            invoice_manager.cleanup()
            return [TextContent(
                type="text",
                text=json.dumps({
                    "status": "success",
                    "message": "Browser closed successfully"
                }, indent=2)
            )]

        else:
            return [TextContent(
                type="text",
                text=f"Error: Unknown tool '{name}'"
            )]

    except Exception as e:
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
