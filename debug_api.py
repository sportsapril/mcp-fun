#!/usr/bin/env python3
import asyncio
import json
from playwright.async_api import async_playwright

async def capture_api():
    """Capture the globalSearch API response"""
    url = "https://www.tripadvisor.cn/Search?q=%E5%AE%BD%E7%AA%84%E5%B7%B7%E5%AD%90&geo=297463"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, channel="chromium")
        page = await browser.new_page()

        # Capture API response
        global_search_data = None

        async def handle_response(response):
            nonlocal global_search_data
            if 'globalSearch' in response.url:
                try:
                    json_data = await response.json()
                    global_search_data = json_data
                    print(f"Captured globalSearch API response!")
                except Exception as e:
                    print(f"Error parsing JSON: {e}")

        page.on('response', handle_response)

        print(f"Navigating to: {url}")
        await page.goto(url, wait_until="networkidle", timeout=30000)

        # Wait for API call
        await page.wait_for_timeout(3000)

        if global_search_data:
            # Save to file
            with open('globalsearch_response.json', 'w', encoding='utf-8') as f:
                json.dump(global_search_data, f, indent=2, ensure_ascii=False)
            print("Saved API response to globalsearch_response.json")

            # Print first result
            if 'data' in global_search_data and 'locations' in global_search_data['data']:
                locations = global_search_data['data']['locations']
                print(f"\nFound {len(locations)} locations")

                for i, loc in enumerate(locations[:3]):
                    print(f"\n{i+1}. {loc.get('name', 'N/A')}")
                    print(f"   Type: {loc.get('type', 'N/A')}")
                    print(f"   URL: {loc.get('url', 'N/A')}")
                    print(f"   Reviews: {loc.get('reviewCount', 'N/A')}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(capture_api())
