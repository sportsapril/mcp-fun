#!/usr/bin/env python3
import asyncio
from playwright.async_api import async_playwright

async def debug_network():
    """Debug network requests to find the search API"""
    url = "https://www.tripadvisor.cn/Search?q=%E5%AE%BD%E7%AA%84%E5%B7%B7%E5%AD%90&geo=297463"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, channel="chromium")
        page = await browser.new_page()

        # Track API calls
        api_calls = []

        async def handle_response(response):
            if 'api' in response.url.lower() or 'graphql' in response.url.lower() or 'search' in response.url.lower():
                api_calls.append({
                    'url': response.url,
                    'status': response.status,
                    'content_type': response.headers.get('content-type', '')
                })

        page.on('response', handle_response)

        print(f"Navigating to: {url}")
        await page.goto(url, wait_until="networkidle", timeout=30000)

        # Wait for results to load
        await page.wait_for_timeout(5000)

        print(f"\n=== API Calls ({len(api_calls)} total) ===")
        for call in api_calls:
            print(f"\nURL: {call['url']}")
            print(f"Status: {call['status']}")
            print(f"Content-Type: {call['content_type']}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_network())
