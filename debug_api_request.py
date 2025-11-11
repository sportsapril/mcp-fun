#!/usr/bin/env python3
import asyncio
import json
from playwright.async_api import async_playwright

async def capture_request():
    """Capture the actual globalSearch API request"""
    url = "https://www.tripadvisor.cn/Search?q=%E5%AE%BD%E7%AA%84%E5%B7%B7%E5%AD%90&geo=297463"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, channel="chromium")
        page = await browser.new_page()

        # Capture request payload
        async def handle_request(request):
            if 'globalSearch' in request.url:
                print(f"\n=== Request to globalSearch ===")
                print(f"URL: {request.url}")
                print(f"Method: {request.method}")
                print(f"Headers: {json.dumps(dict(request.headers), indent=2)}")
                if request.post_data:
                    print(f"\nPost Data:")
                    try:
                        payload = json.loads(request.post_data)
                        print(json.dumps(payload, indent=2, ensure_ascii=False))
                    except:
                        print(request.post_data)

        page.on('request', handle_request)

        print(f"Navigating to: {url}")
        await page.goto(url, wait_until="networkidle", timeout=30000)

        # Wait for API call
        await page.wait_for_timeout(3000)

        await browser.close()

if __name__ == "__main__":
    asyncio.run(capture_request())
