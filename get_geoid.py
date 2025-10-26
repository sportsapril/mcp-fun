import asyncio, re, urllib.parse
from playwright.async_api import async_playwright

TOURISM_URL_RE = re.compile(r"https?://[^\"']*/Tourism-g\d+-[^\"']*?-Vacations\.html", re.I)

def _normalize_city_for_match(city: str) -> str:
    # Tourism URLs often use Title_Case_With_Underscores for the city segment.
    # We'll just do a loose match on the city name (case-insensitive) anywhere in the URL.
    return re.sub(r"\s+", "_", city.strip(), flags=re.I)

async def find_tripadvisor_tourism_links_for_city(
    city: str,
    domain: str = "tripadvisor.cn",
    timeout_ms: int = 45000,
    headless: bool = True,
    must_match_city: bool = True,
) -> list[str]:
    """
    Visit Tripadvisor search page for `city` and return any observed Tourism page links.

    Args:
        city: e.g. "Dezhou"
        domain: "tripadvisor.cn" (default) or "tripadvisor.com"
        timeout_ms: page goto timeout
        headless: Playwright headless browser
        must_match_city: if True, only keep tourism links that contain the city name (loose match)

    Returns:
        Sorted list of unique tourism URLs.
    """
    q = city.strip()
    search_url = f"https://{domain}/Search?" + urllib.parse.urlencode({"q": q, "searchNearby": "false"})
    found = set()
    city_marker = _normalize_city_for_match(city).lower()

    def _scan_text(t: str):
        for m in TOURISM_URL_RE.finditer(t or ""):
            url = m.group(0)
            if not must_match_city or city_marker in url.lower():
                found.add(url)

    async def _resp_handler(response):
        ct = (response.headers.get("content-type") or "").lower()
        try:
            if "application/json" in ct:
                try:
                    data = await response.json()
                except Exception:
                    data = await response.text()
                _scan_text(str(data))
            elif "text/html" in ct or "text/plain" in ct:
                _scan_text(await response.text())
        except Exception:
            pass

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        context = await browser.new_context(
            user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/124.0.0.0 Safari/537.36")
        )
        page = await context.new_page()
        page.on("response", lambda r: asyncio.create_task(_resp_handler(r)))

        await page.goto(search_url, wait_until="networkidle", timeout=timeout_ms)

        # Also scan anchors in the hydrated DOM
        anchors = await page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
        for href in anchors:
            if href and TOURISM_URL_RE.search(href):
                if not must_match_city or city_marker in href.lower():
                    found.add(href)

        await browser.close()

    return sorted(found)

# --- Example (Jupyter / IPython):
# links = await find_tripadvisor_tourism_links_for_city("Dezhou")
# links[:3], len(links)
