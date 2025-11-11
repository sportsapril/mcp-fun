#!/usr/bin/env python3
import asyncio
from playwright.async_api import async_playwright

async def debug_search():
    """Debug what selectors exist on TripAdvisor search page"""
    url = "https://www.tripadvisor.cn/Search?q=%E5%AE%BD%E7%AA%84%E5%B7%B7%E5%AD%90&geo=297463"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, channel="chromium")  # visible browser
        page = await browser.new_page()

        print(f"Navigating to: {url}")
        await page.goto(url, wait_until="networkidle", timeout=30000)

        # Wait a bit for JavaScript to load
        await page.wait_for_timeout(5000)

        # Try to find search results with different selectors
        selectors_to_try = [
            'div[data-automation="cardWrapper"]',
            'div[data-test="search-result"]',
            'a[href*="Attraction_Review"]',
            'div.result-card',
            'div[class*="result"]',
            '.listing',
        ]

        for selector in selectors_to_try:
            elements = await page.query_selector_all(selector)
            print(f"\nSelector '{selector}': found {len(elements)} elements")

            if len(elements) > 0:
                # Get first element's HTML
                first = elements[0]
                html = await first.inner_html()
                print(f"First element HTML (truncated):\n{html[:500]}")

        # Get page HTML to inspect
        html = await page.content()

        # Look for links with "Attraction_Review" or "Review"
        review_links = await page.query_selector_all('a[href*="Review"]')
        print(f"\n\nFound {len(review_links)} links with 'Review' in href")

        for i, link in enumerate(review_links[:5]):
            href = await link.get_attribute('href')
            text = await link.inner_text()
            print(f"{i+1}. {text[:50]} -> {href[:100]}")

        # Now check result-card elements specifically
        print("\n\n=== Result Cards ===")
        result_cards = await page.query_selector_all('div.result-card')
        print(f"Found {len(result_cards)} result cards")

        for i, card in enumerate(result_cards[:5]):
            # Try to find link within card
            link = await card.query_selector('a[href*="Review"]')
            if link:
                href = await link.get_attribute('href')
                text = await link.inner_text()
                print(f"\n{i+1}. Title: {text.strip()}")
                print(f"   URL: {href}")
            else:
                # Try any link
                any_link = await card.query_selector('a')
                if any_link:
                    href = await any_link.get_attribute('href')
                    text = await any_link.inner_text()
                    print(f"\n{i+1}. (No Review link) Title: {text.strip()[:50]}")
                    print(f"   URL: {href}")

        # Save HTML for inspection
        with open('/Users/aprilxu/Documents/GitHub/mcp-fun/search_page.html', 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"\n\nSaved full HTML to search_page.html")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_search())
