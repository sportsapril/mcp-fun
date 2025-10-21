# Twitter Developer Portal Invoice Downloader

Automate downloading invoices from the Twitter/X Developer Portal billing page to send to your accounting team.

## Features

- **Automated Login**: Supports manual authentication (recommended for security)
- **Batch Download**: Download all available invoices or just the latest one
- **Smart Naming**: Automatically organizes invoices with transaction IDs and dates
- **PDF Export**: Downloads invoices as PDF files ready to email
- **Configurable**: Set custom download directories and preferences

## Prerequisites

1. **Python 3.8+** installed on your system
2. **Google Chrome** browser installed
3. **ChromeDriver** (will be managed automatically)

## Installation

### Step 1: Install Dependencies

```bash
pip install -r requirements-invoice.txt
```

This will install:
- `selenium` - For browser automation
- `webdriver-manager` - For automatic ChromeDriver management

### Step 2: Configure (Optional)

Copy the template configuration file:

```bash
cp .env.template .env
```

Edit `.env` to customize your settings:

```bash
# Optional: Set custom download directory
INVOICE_DOWNLOAD_DIR=./invoices

# Note: For security, we recommend NOT storing credentials
# The script supports manual login through the browser
```

## Usage

### Quick Start - Download Latest Invoice

```bash
python twitter_invoice_downloader.py --latest
```

### Download All Available Invoices

```bash
python twitter_invoice_downloader.py --all
```

### How It Works

1. **Script launches Chrome browser** - You'll see the browser window open
2. **Navigate to Twitter Developer Portal** - Goes to the billing page
3. **Manual Authentication** - You log in through the browser as normal
4. **Auto-Download** - Once logged in, press Enter and the script downloads invoices
5. **Save to Folder** - Invoices are saved to `./invoices/` directory

### Example Output

```
Navigating to Twitter Developer Portal...
Please complete the login process manually...
This script will wait for you to complete authentication.
Press Enter once you're on the billing page...

Finding invoice download links...
Found 11 invoices to download
Downloading invoice #668250 from Sep 15, 2025...
Downloading invoice #653340 from Aug 15, 2025...
...

Downloaded 11 out of 11 invoices
Invoices saved to: /Users/aprilxu/Documents/GitHub/mcp-fun/invoices
```

## Automation Options

### Schedule Monthly Downloads (macOS/Linux)

Add to your crontab to run on the 1st of each month:

```bash
# Edit crontab
crontab -e

# Add this line to run at 9 AM on the 1st of each month
0 9 1 * * cd /Users/aprilxu/Documents/GitHub/mcp-fun && /usr/bin/python3 twitter_invoice_downloader.py --latest
```

### Schedule Monthly Downloads (Windows)

Use Task Scheduler:

1. Open Task Scheduler
2. Create Basic Task
3. Set trigger: Monthly, Day 1, Time 9:00 AM
4. Action: Start a program
   - Program: `python`
   - Arguments: `twitter_invoice_downloader.py --latest`
   - Start in: `C:\path\to\mcp-fun\`

### Email Integration

You can extend the script to automatically email invoices to your accounting team. Here's a simple example:

```python
# Add this to the end of twitter_invoice_downloader.py

def send_invoice_email(invoice_path: str):
    """Send invoice to accounting team"""
    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.base import MIMEBase
    from email import encoders

    sender = "you@company.com"
    receiver = "accounting@company.com"

    msg = MIMEMultipart()
    msg['From'] = sender
    msg['To'] = receiver
    msg['Subject'] = f"Twitter Dev Portal Invoice - {datetime.now().strftime('%B %Y')}"

    # Attach PDF
    with open(invoice_path, 'rb') as f:
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(f.read())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f'attachment; filename={os.path.basename(invoice_path)}')
        msg.attach(part)

    # Send email
    with smtplib.SMTP('smtp.gmail.com', 587) as server:
        server.starttls()
        server.login(sender, "your_app_password")
        server.send_message(msg)
```

## Troubleshooting

### ChromeDriver Issues

If you get ChromeDriver errors:

```bash
# Install webdriver-manager
pip install webdriver-manager

# Update the script to use webdriver-manager
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service

service = Service(ChromeDriverManager().install())
self.driver = webdriver.Chrome(service=service, options=chrome_options)
```

### PDFs Not Downloading

If PDFs open in browser instead of downloading:

1. Check Chrome settings: `chrome://settings/downloads`
2. Ensure "Ask where to save each file before downloading" is OFF
3. The script sets this automatically, but manual browser settings may override

### Authentication Issues

The script uses manual authentication for security. If you want to automate this:

⚠️ **Security Warning**: Storing credentials is not recommended
- Consider using a password manager or secrets vault
- Use 2FA and app-specific passwords when possible

### Script Hangs or Freezes

- Increase `time.sleep()` values if your connection is slow
- Check if the Twitter Developer Portal UI has changed
- Update selectors in the script if needed

## Security Best Practices

1. **Never commit credentials** to version control
2. **Use manual login** rather than storing passwords
3. **Keep .env in .gitignore** (already configured)
4. **Use 2FA** on your Twitter Developer account
5. **Review downloaded files** before emailing

## Customization

### Change Download Directory

Edit `.env`:
```bash
INVOICE_DOWNLOAD_DIR=/path/to/invoices
```

Or use environment variable:
```bash
INVOICE_DOWNLOAD_DIR=/custom/path python twitter_invoice_downloader.py --latest
```

### Run Headless (No Browser Window)

Edit `twitter_invoice_downloader.py` and uncomment:
```python
chrome_options.add_argument("--headless")
```

### Filter Specific Invoices

Modify the `get_invoice_links()` method to filter by date, amount, or status:

```python
def get_invoice_links(self, status_filter="paid"):
    """Get only paid invoices"""
    rows = self.driver.find_elements(By.XPATH, "//table//tr")

    filtered_buttons = []
    for row in rows:
        status = row.find_elements(By.TAG_NAME, "td")[4].text  # Status column
        if status.lower() == status_filter.lower():
            button = row.find_element(By.XPATH, ".//button[contains(., 'pdf')]")
            filtered_buttons.append(button)

    return filtered_buttons
```

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review the Twitter Developer Portal for UI changes
3. Open an issue in this repository

## License

This tool is provided as-is for automation of legitimate billing tasks.
