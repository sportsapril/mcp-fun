#!/usr/bin/env python3
"""
Twitter Developer Portal Invoice Downloader

This script automates downloading invoices from the Twitter Developer Portal.
It uses Selenium to navigate the portal, authenticate, and download invoice PDFs.
"""

import os
import time
from datetime import datetime
from pathlib import Path
from typing import Optional
import json
import argparse

try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
except ImportError:
    print("Selenium not installed. Please run: pip install selenium")
    exit(1)


class TwitterInvoiceDownloader:
    """Automate downloading invoices from Twitter Developer Portal"""

    def __init__(self, config_path: str = ".env"):
        """Initialize the downloader with configuration"""
        self.config_path = config_path
        self.load_config()
        self.driver = None

    def load_config(self):
        """Load configuration from .env file or environment"""
        # Try to load from .env file
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        os.environ[key.strip()] = value.strip()

        # Get credentials from environment
        self.username = os.getenv('TWITTER_USERNAME')
        self.password = os.getenv('TWITTER_PASSWORD')
        self.download_dir = os.getenv('INVOICE_DOWNLOAD_DIR', './invoices')

        # Create download directory if it doesn't exist
        Path(self.download_dir).mkdir(parents=True, exist_ok=True)

    def setup_driver(self):
        """Setup Chrome WebDriver with appropriate options"""
        chrome_options = Options()

        # Set download directory
        prefs = {
            "download.default_directory": str(Path(self.download_dir).absolute()),
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "plugins.always_open_pdf_externally": True  # Download PDFs instead of opening
        }
        chrome_options.add_experimental_option("prefs", prefs)

        # Uncomment to run headless (without browser UI)
        # chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")

        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.set_window_size(1920, 1080)

    def login(self):
        """Login to Twitter Developer Portal"""
        print("Navigating to Twitter Developer Portal...")
        self.driver.get("https://developer.x.com/en/account/billing")

        # Wait for login page or billing page
        time.sleep(3)

        # Check if already logged in
        if "billing" in self.driver.current_url.lower():
            print("Already logged in!")
            return True

        print("Please complete the login process manually...")
        print("This script will wait for you to complete authentication.")
        print("Press Enter once you're on the billing page...")
        input()

        return True

    def get_invoice_links(self):
        """Extract all invoice download links from the billing page"""
        print("Finding invoice download links...")

        try:
            # Wait for the transaction table to load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//table"))
            )

            # Find all PDF download buttons
            pdf_buttons = self.driver.find_elements(By.XPATH, "//button[contains(., 'pdf')]")

            print(f"Found {len(pdf_buttons)} invoices to download")
            return pdf_buttons

        except Exception as e:
            print(f"Error finding invoices: {e}")
            return []

    def download_invoice(self, button, index: int):
        """Click a download button to download an invoice"""
        try:
            # Get transaction ID from the row
            row = button.find_element(By.XPATH, "./ancestor::tr")
            transaction_cells = row.find_elements(By.TAG_NAME, "td")

            if len(transaction_cells) > 0:
                transaction_id = transaction_cells[0].text.strip()
                transaction_date = transaction_cells[1].text.strip() if len(transaction_cells) > 1 else ""

                print(f"Downloading invoice {transaction_id} from {transaction_date}...")
            else:
                print(f"Downloading invoice {index + 1}...")

            # Scroll to button
            self.driver.execute_script("arguments[0].scrollIntoView(true);", button)
            time.sleep(0.5)

            # Click the download button
            button.click()

            # Wait for download to start
            time.sleep(2)

            return True

        except Exception as e:
            print(f"Error downloading invoice: {e}")
            return False

    def download_all_invoices(self):
        """Download all available invoices"""
        if not self.driver:
            self.setup_driver()

        if not self.login():
            print("Login failed!")
            return False

        # Navigate to billing page if not already there
        if "billing" not in self.driver.current_url.lower():
            self.driver.get("https://developer.x.com/en/account/billing")
            time.sleep(3)

        # Get all invoice links
        invoice_buttons = self.get_invoice_links()

        if not invoice_buttons:
            print("No invoices found!")
            return False

        # Download each invoice
        successful_downloads = 0
        for i, button in enumerate(invoice_buttons):
            if self.download_invoice(button, i):
                successful_downloads += 1
            time.sleep(1)  # Wait between downloads

        print(f"\nDownloaded {successful_downloads} out of {len(invoice_buttons)} invoices")
        print(f"Invoices saved to: {Path(self.download_dir).absolute()}")

        return True

    def download_latest_invoice(self):
        """Download only the most recent invoice"""
        if not self.driver:
            self.setup_driver()

        if not self.login():
            print("Login failed!")
            return False

        # Navigate to billing page if not already there
        if "billing" not in self.driver.current_url.lower():
            self.driver.get("https://developer.x.com/en/account/billing")
            time.sleep(3)

        # Get all invoice links
        invoice_buttons = self.get_invoice_links()

        if not invoice_buttons:
            print("No invoices found!")
            return False

        # Download first invoice (most recent)
        if self.download_invoice(invoice_buttons[0], 0):
            print(f"\nInvoice saved to: {Path(self.download_dir).absolute()}")
            return True

        return False

    def cleanup(self):
        """Close the browser and cleanup"""
        if self.driver:
            self.driver.quit()


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Download invoices from Twitter Developer Portal"
    )
    parser.add_argument(
        "--latest",
        action="store_true",
        help="Download only the latest invoice"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Download all available invoices"
    )
    parser.add_argument(
        "--config",
        default=".env",
        help="Path to configuration file (default: .env)"
    )

    args = parser.parse_args()

    # Default to downloading latest if no option specified
    if not args.latest and not args.all:
        args.latest = True

    downloader = TwitterInvoiceDownloader(config_path=args.config)

    try:
        if args.all:
            downloader.download_all_invoices()
        else:
            downloader.download_latest_invoice()
    except KeyboardInterrupt:
        print("\nDownload interrupted by user")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        downloader.cleanup()


if __name__ == "__main__":
    main()
