"""
TripAdvisor MCP Server

This MCP server provides tools to search TripAdvisor China (tripadvisor.cn)
for travel information including hotels, restaurants, attractions, and activities.
It integrates with travel planners to provide rich search results with images and URLs.
"""

import asyncio
import csv
import json
import logging
import os
import re
import time
import urllib.parse
from pathlib import Path
from typing import Any, Optional
from urllib.parse import quote, urlencode

import anthropic
import httpx
from bs4 import BeautifulSoup
from mcp.server import Server
from mcp.types import Tool, TextContent, ImageContent, EmbeddedResource
from playwright.async_api import async_playwright

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("tripadvisor-mcp")

# Initialize MCP server
app = Server("tripadvisor-mcp")

# Constants
BASE_URL = "https://www.tripadvisor.cn"
SEARCH_URL = f"{BASE_URL}/Search"
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"

# HTTP client
http_client: Optional[httpx.AsyncClient] = None

# Geo ID cache (in-memory)
_geo_id_cache: dict[str, str] = {}

# CSV-based location database
_location_database: dict[str, list[dict[str, str]]] = {}

# Chinese to English city name mapping for common cities
# This helps match Chinese input to English names in CSV
CITY_NAME_ALIASES = {
    # Major world cities
    "东京": "tokyo",
    "纽约": "new york",
    "洛杉矶": "los angeles",
    "旧金山": "san francisco",
    "芝加哥": "chicago",
    "伦敦": "london",
    "巴黎": "paris",
    "柏林": "berlin",
    "罗马": "rome",
    "马德里": "madrid",
    "悉尼": "sydney",
    "墨尔本": "melbourne",
    "多伦多": "toronto",
    "温哥华": "vancouver",
    "首尔": "seoul",
    "曼谷": "bangkok",
    "新加坡": "singapore",
    "吉隆坡": "kuala lumpur",
    "雅加达": "jakarta",
    "马尼拉": "manila",
    "河内": "hanoi",
    "胡志明市": "ho chi minh city",
    "迪拜": "dubai",
    "开罗": "cairo",
    "伊斯坦布尔": "istanbul",
    "莫斯科": "moscow",
    "圣彼得堡": "saint petersburg",
    "孟买": "mumbai",
    "德里": "delhi",
    "加尔各答": "kolkata",
    "班加罗尔": "bangalore",
    "布宜诺斯艾利斯": "buenos aires",
    "圣保罗": "sao paulo",
    "里约热内卢": "rio de janeiro",
    "墨西哥城": "mexico city",
}


def load_location_database():
    """
    Load location-to-geo-ID mappings from CSV file.

    Loads data/tripadvisor_geo_map/locations.csv into memory.
    Structure: {location_name_lower: [{"locationId": "...", "url": "..."}, ...]}

    Multiple entries per location are supported (e.g., Washington in different states).
    """
    global _location_database

    if _location_database:
        # Already loaded
        return

    # Find CSV file relative to this module
    module_dir = Path(__file__).parent
    project_root = module_dir.parent.parent
    csv_path = project_root / "data" / "tripadvisor_geo_map" / "locations.csv"

    if not csv_path.exists():
        logger.error(f"CSV file not found: {csv_path}")
        return

    total_loaded = 0

    try:
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                location = row.get("location", "").strip()
                location_id = row.get("locationId", "").strip()
                url = row.get("url", "").strip()

                if not location or not location_id:
                    continue

                # Normalize location name (lowercase for matching)
                location_lower = location.lower()

                # Store as list since some locations have multiple entries
                if location_lower not in _location_database:
                    _location_database[location_lower] = []

                _location_database[location_lower].append({
                    "location": location,  # Keep original for display
                    "locationId": location_id,
                    "url": url,
                })
                total_loaded += 1

        logger.info(f"Location database loaded: {len(_location_database)} unique locations, {total_loaded} total entries")

    except Exception as e:
        logger.error(f"Error loading {csv_path}: {e}")


def get_http_client() -> httpx.AsyncClient:
    """Get or create HTTP client with proper headers."""
    global http_client
    if http_client is None:
        http_client = httpx.AsyncClient(
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
            },
            timeout=30.0,
            follow_redirects=True,
        )
    return http_client


def lookup_geo_id_from_csv(city: str) -> Optional[str]:
    """
    Look up geo ID from CSV database with bilingual support.

    Supports both English and Chinese city names by checking:
    1. Direct match (e.g., "Tokyo", "tokyo", "TOKYO")
    2. Chinese to English aliases (e.g., "东京" → "tokyo")

    Args:
        city: City name (e.g., "New York", "Tokyo", "东京", "纽约")

    Returns:
        Geo ID string (e.g., "g60763") or None if not found
    """
    # Ensure database is loaded
    if not _location_database:
        load_location_database()

    city_lower = city.lower()

    # Try direct lookup first
    if city_lower in _location_database:
        entries = _location_database[city_lower]
        location_id = entries[0]["locationId"]
        geo_id = f"g{location_id}"

        if len(entries) == 1:
            logger.info(f"✅ Found geo ID for '{city}' in CSV: {geo_id}")
        else:
            logger.info(f"✅ Found geo ID for '{city}' in CSV: {geo_id} (using first of {len(entries)} matches)")

        return geo_id

    # Try alias lookup (e.g., 东京 → tokyo)
    if city in CITY_NAME_ALIASES:
        english_name = CITY_NAME_ALIASES[city]
        logger.info(f"Translating '{city}' to '{english_name}' for CSV lookup")

        if english_name in _location_database:
            entries = _location_database[english_name]
            location_id = entries[0]["locationId"]
            geo_id = f"g{location_id}"
            logger.info(f"✅ Found geo ID for '{city}' (as '{english_name}') in CSV: {geo_id}")
            return geo_id

    return None


async def match_city_with_llm(user_input: str, available_cities: list[str]) -> Optional[str]:
    """
    Use Claude Haiku 3 to intelligently match user input to available city names.

    Handles:
    - Chinese to English matching (东京 → tokyo)
    - Variations and suffixes (Tokyo City → tokyo, 纽约市 → new york)
    - Typos and misspellings
    - Abbreviations (NYC → new york)

    Args:
        user_input: User's city input (e.g., "东京", "New York City", "纽约市")
        available_cities: List of city names from CSV (lowercase)

    Returns:
        Matched city name from available_cities, or None if no good match
    """
    try:
        # Get API key from environment
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            logger.warning("ANTHROPIC_API_KEY not set, skipping LLM matching")
            return None

        # Sample cities if list is too large (to keep prompt concise)
        # For now, use first 200 cities as representative sample
        sample_cities = available_cities[:200] if len(available_cities) > 200 else available_cities

        # Create Anthropic client
        client = anthropic.Anthropic(api_key=api_key)

        prompt = f"""You are a city name matcher. The user is searching for a city.

User input: "{user_input}"

Available cities in database (lowercase): {', '.join(sample_cities[:100])}
{f'...and {len(sample_cities) - 100} more cities' if len(sample_cities) > 100 else ''}

Task: Find the BEST matching city name from the database list.

Consider:
- Chinese and English names refer to the same city (e.g., 东京 = Tokyo, 纽约 = New York)
- City suffixes should be ignored (市, City, Prefecture)
- Common variations (NYC = New York, LA = Los Angeles)
- Typos and misspellings

Rules:
1. Return ONLY the exact city name from the database (lowercase)
2. If no good match exists, return "NONE"
3. Do NOT add explanations, just the city name

Example:
User: "东京" → tokyo
User: "New York City" → new york
User: "纽约市" → new york
User: "LA" → los angeles
User: "unknowncity123" → NONE

Your answer:"""

        # Call Claude Haiku 3 (fast and cheap)
        message = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=50,
            temperature=0,
            messages=[{"role": "user", "content": prompt}]
        )

        matched_city = message.content[0].text.strip().lower()

        logger.info(f"LLM matched '{user_input}' → '{matched_city}'")

        # Validate the response is in our city list
        if matched_city in available_cities:
            return matched_city
        elif matched_city == "none":
            logger.info(f"LLM could not find a match for '{user_input}'")
            return None
        else:
            logger.warning(f"LLM returned invalid city: '{matched_city}'")
            return None

    except Exception as e:
        logger.error(f"Error during LLM city matching: {e}")
        return None


TOURISM_URL_RE = re.compile(r"https?://[^\"']*/Tourism-g\d+-[^\"']*?-Vacations\.html", re.I)


def _normalize_city_for_match(city: str) -> str:
    """Normalize city name for URL matching."""
    return re.sub(r"\s+", "_", city.strip(), flags=re.I)


async def find_tripadvisor_tourism_links(
    city: str,
    domain: str = "tripadvisor.cn",
    timeout_ms: int = 45000,
    headless: bool = True,
    must_match_city: bool = True,
) -> list[str]:
    """
    Visit TripAdvisor search page for `city` and return any observed Tourism page links.

    Uses Playwright for better JavaScript rendering and network monitoring.

    Args:
        city: City name (e.g., "Dezhou", "德州")
        domain: TripAdvisor domain (default: tripadvisor.cn)
        timeout_ms: Page load timeout
        headless: Run browser in headless mode
        must_match_city: Only keep links matching the city name

    Returns:
        Sorted list of unique tourism URLs
    """
    q = city.strip()
    search_url = f"https://{domain}/Search?" + urllib.parse.urlencode({"q": q, "searchNearby": "false"})
    found = set()
    city_marker = _normalize_city_for_match(city).lower()

    # Check if city contains Chinese characters - if so, accept any Tourism link
    has_chinese = any('\u4e00' <= char <= '\u9fff' for char in city)

    def _scan_text(t: str):
        for m in TOURISM_URL_RE.finditer(t or ""):
            url = m.group(0)
            # If Chinese city name, accept first Tourism link (TripAdvisor search handles translation)
            # Otherwise, check if city name appears in URL
            if has_chinese or not must_match_city or city_marker in url.lower():
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
                if has_chinese or not must_match_city or city_marker in href.lower():
                    found.add(href)

        await browser.close()

    return sorted(found)


def save_city_to_csv(city: str, location_id: str, url: str) -> None:
    """
    Save a new city to the locations.csv file.

    Args:
        city: City name (lowercase for English, original for Chinese)
        location_id: Location ID (e.g., "1017006")
        url: Full TripAdvisor URL
    """
    module_dir = Path(__file__).parent
    project_root = module_dir.parent.parent
    csv_path = project_root / "data" / "tripadvisor_geo_map" / "locations.csv"

    if not csv_path.exists():
        logger.error(f"CSV file not found: {csv_path}")
        return

    try:
        # Read existing entries to check for duplicates
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

            # Check if this city already exists
            for row in rows:
                if row.get("location", "").lower() == city.lower() and row.get("locationId") == location_id:
                    logger.info(f"City '{city}' (g{location_id}) already exists in locations.csv")
                    return

            next_row = len(rows) + 1

        # Append new entry
        with open(csv_path, "a", encoding="utf-8", newline="") as f:
            f.write(f"{next_row},{city},{location_id},{url}\n")

        logger.info(f"✅ Saved '{city}' (g{location_id}) to locations.csv")

        # Also update in-memory database
        if city.lower() not in _location_database:
            _location_database[city.lower()] = []
        _location_database[city.lower()].append({
            "location": city,
            "locationId": location_id,
            "url": url,
        })

    except Exception as e:
        logger.error(f"Error saving city to CSV: {e}")


async def lookup_geo_id_dynamic(city: str) -> Optional[str]:
    """
    Dynamically look up geo ID using Playwright browser automation.

    Uses Playwright to search TripAdvisor, find Tourism links, and extract geo IDs.
    If found, automatically saves the city to locations.csv for future use.

    Args:
        city: City name in Chinese or English (e.g., "德州", "Dezhou")

    Returns:
        Geo ID string (e.g., "g1017006") or None if not found
    """
    # Check cache first
    city_lower = city.lower()
    if city_lower in _geo_id_cache:
        logger.info(f"Found cached geo ID for {city}: {_geo_id_cache[city_lower]}")
        return _geo_id_cache[city_lower]

    logger.info(f"Looking up geo ID for '{city}' using Playwright (may take 15-20 seconds)...")

    try:
        # Find tourism links using Playwright
        links = await find_tripadvisor_tourism_links(city)

        if not links:
            logger.warning(f"No tourism links found for '{city}'")
            return None

        # Extract geo ID from first link
        first_link = links[0]
        logger.info(f"Found tourism link: {first_link}")

        geo_id_match = re.search(r'Tourism-g(\d+)-', first_link)
        if geo_id_match:
            location_id = geo_id_match.group(1)
            geo_id = f"g{location_id}"
            logger.info(f"✅ Found geo ID for '{city}': {geo_id}")

            # Cache it
            _geo_id_cache[city_lower] = geo_id
            if city != city_lower:
                _geo_id_cache[city] = geo_id

            # Save to CSV for future use
            save_city_to_csv(city_lower, location_id, first_link)

            return geo_id
        else:
            logger.warning(f"Could not extract geo ID from URL: {first_link}")
            return None

    except Exception as e:
        logger.error(f"Error during Playwright geo ID lookup: {e}")
        return None


# Geo IDs for major Chinese cities
# To find geo IDs: visit tripadvisor.cn, search for city, check URL for -gXXXXXX- pattern
LOCATION_GEO_IDS = {
    # Tier 1 Cities
    "上海": "g308272",
    "shanghai": "g308272",
    "北京": "g294212",
    "beijing": "g294212",
    "广州": "g298555",
    "guangzhou": "g298555",
    "深圳": "g297415",
    "shenzhen": "g297415",

    # Major Tourist Cities
    "西安": "g298557",
    "xian": "g298557",
    "xi'an": "g298557",
    "成都": "g297463",
    "chengdu": "g297463",
    "杭州": "g298559",
    "hangzhou": "g298559",
    "南京": "g294220",
    "nanjing": "g294220",
    "重庆": "g294213",
    "chongqing": "g294213",
    "苏州": "g297442",
    "suzhou": "g297442",

    # Additional Major Cities (16 more - total 26 cities)
    "厦门": "g297407",
    "xiamen": "g297407",
    "青岛": "g297458",
    "qingdao": "g297458",
    "昆明": "g298558",
    "kunming": "g298558",
    "大连": "g297452",
    "dalian": "g297452",
    "武汉": "g297446",
    "wuhan": "g297446",
    "天津": "g311293",
    "tianjin": "g311293",
    "哈尔滨": "g297445",
    "harbin": "g297445",
    "沈阳": "g297462",
    "shenyang": "g297462",
    "长沙": "g494933",
    "changsha": "g494933",
    "桂林": "g298556",
    "guilin": "g298556",
    "三亚": "g303719",
    "sanya": "g303719",
    "丽江": "g303718",
    "lijiang": "g303718",
    "张家界": "g297459",
    "zhangjiajie": "g297459",
    "黄山": "g303685",
    "huangshan": "g303685",
    "乌鲁木齐": "g297461",
    "urumqi": "g297461",
    "福州": "g297405",
    "fuzhou": "g297405",
    "德州": "g1017006",  # Dezhou, Shandong
    "dezhou": "g1017006",
}


async def determine_category_and_url(query: str, location: Optional[str] = None) -> tuple[str, str, str, bool]:
    """
    Determine the category and build the appropriate URL.

    Returns:
        (category, url, geo_id, location_known)
    """
    query_lower = query.lower()

    # Determine geo ID using four-tier lookup system:
    # 1. CSV direct match - fast, exact matches
    # 2. Hardcoded Chinese cities - fast, legacy support
    # 3. LLM intelligent matching - handles Chinese/English variations
    # 4. Selenium dynamic lookup - slow, last resort

    geo_id = None
    location_known = False
    if location:
        location_lower = location.lower()

        # Tier 1: Try CSV database first (direct match)
        geo_id = lookup_geo_id_from_csv(location)

        # Tier 2: Try hardcoded Chinese cities dictionary
        if not geo_id:
            geo_id = LOCATION_GEO_IDS.get(location_lower)
            if geo_id:
                logger.info(f"✅ Found geo ID for '{location}' in hardcoded list: {geo_id}")

        # Tier 3: Try LLM-based intelligent matching
        if not geo_id:
            logger.info(f"Location '{location}' not found directly. Trying LLM matching...")

            # Load all cities from CSV
            if not _location_database:
                load_location_database()

            available_cities = list(_location_database.keys())
            matched_city = await match_city_with_llm(location, available_cities)

            if matched_city:
                # Look up the matched city in CSV
                entries = _location_database[matched_city]
                location_id = entries[0]["locationId"]
                geo_id = f"g{location_id}"
                logger.info(f"✅ LLM matched '{location}' to '{matched_city}', geo ID: {geo_id}")

        # Tier 4: Selenium dynamic lookup as absolute last resort
        if not geo_id:
            logger.info(f"Location '{location}' not found via LLM. Attempting Selenium dynamic lookup...")
            geo_id = await lookup_geo_id_dynamic(location)

        location_known = geo_id is not None

    # Determine category and build URL
    if "hotel" in query_lower or "酒店" in query_lower:
        category = "hotels"
        if geo_id:
            url = f"{BASE_URL}/Hotels-{geo_id}-{location}-Hotels.html"
        else:
            url = f"{BASE_URL}/Hotels"

    elif "restaurant" in query_lower or "餐厅" in query_lower or "美食" in query_lower:
        category = "restaurants"
        if geo_id:
            url = f"{BASE_URL}/Restaurants-{geo_id}-{location}.html"
        else:
            url = f"{BASE_URL}/Restaurants"

    elif "attraction" in query_lower or "景点" in query_lower or "things to do" in query_lower or "活动" in query_lower:
        category = "attractions"
        if geo_id:
            url = f"{BASE_URL}/Attractions-{geo_id}-Activities-{location}.html"
        else:
            url = f"{BASE_URL}/Attractions"

    else:
        # Default to attractions for general queries
        category = "attractions"
        if geo_id:
            url = f"{BASE_URL}/Attractions-{geo_id}-Activities-{location}.html"
        else:
            url = f"{BASE_URL}/Tourism"

    return category, url, geo_id or "unknown", location_known


async def search_tripadvisor(
    query: str,
    location: Optional[str] = None,
    date: Optional[str] = None,
    price_range: Optional[str] = None,
    max_results: int = 10,
) -> dict[str, Any]:
    """
    Search TripAdvisor China for travel information.

    Args:
        query: Search query (e.g., "hotel", "restaurant", "things to do")
        location: Location to search in (e.g., "上海", "北京")
        date: Date in YYYY-MM-DD format (if applicable)
        price_range: Price range filter (e.g., "budget", "mid-range", "luxury")
        max_results: Maximum number of results to return

    Returns:
        Dictionary with search results including titles, descriptions, images, URLs, and ratings
    """
    try:
        client = get_http_client()

        # Determine category and build URL
        category, search_url, geo_id, location_known = await determine_category_and_url(query, location)

        # Warn if location is unknown (both hardcoded and dynamic lookup failed)
        if location and not location_known:
            logger.warning(f"Could not find geo ID for location: {location}")
            return {
                "success": False,
                "error": f"Could not find location '{location}' on TripAdvisor. Please check the spelling or try a different city name.",
                "query": query,
                "location": location,
                "category": category,
                "suggestion": f"Visit {BASE_URL} directly to search for {location}.",
            }

        logger.info(f"Searching TripAdvisor: {search_url} (category: {category}, geo: {geo_id})")

        # Make request
        response = await client.get(search_url)
        response.raise_for_status()

        # Parse HTML to extract Next.js data
        soup = BeautifulSoup(response.text, "html.parser")

        # Find __NEXT_DATA__ script tag
        next_data_script = soup.find("script", {"id": "__NEXT_DATA__"})

        if not next_data_script:
            logger.error("No __NEXT_DATA__ found in page")
            return {
                "success": False,
                "error": "Could not find data in page. TripAdvisor structure may have changed.",
                "query": query,
                "location": location,
            }

        # Parse JSON data
        import json as json_module
        next_data = json_module.loads(next_data_script.string)

        # Extract results based on category
        results = []
        page_props = next_data.get("props", {}).get("pageProps", {})
        initial_state = page_props.get("initialState", {})

        logger.info(f"Extracting {category} from Next.js data")

        # Extract based on category
        if category == "restaurants":
            # Restaurants are in middleRestaurants and topRestaurants
            middle_restaurants = initial_state.get("middleRestaurants", [])
            top_restaurants = initial_state.get("topRestaurants", [])

            for section in middle_restaurants + top_restaurants:
                if isinstance(section, dict) and "restaurants" in section:
                    for restaurant in section["restaurants"][:max_results]:
                        # Use the url field from restaurant data if available (it's the correct full URL)
                        restaurant_url = restaurant.get('url', '')
                        if restaurant_url and not restaurant_url.startswith('http'):
                            restaurant_url = f"{BASE_URL}/{restaurant_url}"
                        elif not restaurant_url:
                            # Fallback to constructing URL (though this may not work)
                            restaurant_geo_id = restaurant.get('geoId') or geo_id.replace('g', '')
                            restaurant_url = f"{BASE_URL}/Restaurant_Review-g{restaurant_geo_id}-d{restaurant.get('restaurantId', '')}.html"

                        result = {
                            "title": restaurant.get("name", ""),
                            "url": restaurant_url,
                            "rating": restaurant.get("commentRating", ""),
                            "reviews": f"{restaurant.get('commentCount', 0)} reviews",
                            "category": "Restaurant",
                        }

                        # Extract cuisines
                        cuisines = restaurant.get("cuisines", [])
                        if cuisines:
                            cuisine_names = [c.get("name", "") for c in cuisines if c.get("name")]
                            result["cuisines"] = ", ".join(cuisine_names[:3])

                        # Extract address if available
                        if restaurant.get("address"):
                            result["address"] = restaurant["address"]

                        # Extract cover image
                        cover_image = restaurant.get("coverImage", {})
                        if cover_image and isinstance(cover_image, dict):
                            images = cover_image.get("images", {})
                            if images:
                                # Try to get the large image, or medium, or small
                                for size in ["large", "medium", "small"]:
                                    img_data = images.get(size)
                                    if img_data and isinstance(img_data, dict) and img_data.get("url"):
                                        result["image_url"] = img_data["url"]
                                        break

                        results.append(result)
                        logger.info(f"Added restaurant: {result['title']}")

                        if len(results) >= max_results:
                            break

                if len(results) >= max_results:
                    break

        elif category == "attractions":
            # Attractions are in verticalData
            vertical_data = initial_state.get("verticalData", [])

            for attraction in vertical_data[:max_results]:
                # Use the url field from attraction data if available (like restaurants)
                attraction_url = attraction.get('url', '')
                if attraction_url and not attraction_url.startswith('http'):
                    attraction_url = f"{BASE_URL}/{attraction_url}"
                elif not attraction_url:
                    # Fallback to constructing URL
                    geo_id_num = geo_id.replace('g', '') if geo_id.startswith('g') else geo_id
                    attraction_url = f"{BASE_URL}/Attraction_Review-g{geo_id_num}-d{attraction.get('taSightId', '')}.html"

                result = {
                    "title": attraction.get("displayName", ""),
                    "url": attraction_url,
                    "category": "Attraction",
                }

                # Extract rating and reviews
                ranking_data = attraction.get("rankingData", {})
                if ranking_data:
                    if ranking_data.get("rating"):
                        result["rating"] = f"{ranking_data['rating']}/5.0"

                # Reviews count
                if attraction.get("reviewsCount"):
                    result["reviews"] = f"{attraction['reviewsCount']} reviews"
                elif attraction.get("reviewsCountString"):
                    result["reviews"] = attraction["reviewsCountString"]

                # Extract tags/description
                tags_desc = attraction.get("tagsDesc")
                if tags_desc:
                    result["description"] = tags_desc

                # Extract image
                cover_image = attraction.get("coverImage", {})
                if cover_image and cover_image.get("url"):
                    result["image_url"] = cover_image["url"]

                results.append(result)
                logger.info(f"Added attraction: {result['title']}")

        elif category == "hotels":
            # Hotels load dynamically, data is not in initial state
            # Try to find any available hotel data
            hotel_list = initial_state.get("hotelList")
            hotels = initial_state.get("hotels")
            recent_hotels = initial_state.get("recentHotelList")

            # Check if any hotel data is available
            hotel_data = None
            if isinstance(hotels, list) and len(hotels) > 0:
                hotel_data = hotels
            elif isinstance(hotel_list, list) and len(hotel_list) > 0:
                hotel_data = hotel_list
            elif isinstance(recent_hotels, list) and len(recent_hotels) > 0:
                hotel_data = recent_hotels

            if hotel_data:
                for hotel in hotel_data[:max_results]:
                    result = {
                        "title": hotel.get("name", ""),
                        "url": f"{BASE_URL}/Hotel_Review-g{hotel.get('geoId', '')}-d{hotel.get('hotelId', '')}.html",
                        "rating": hotel.get("rating", ""),
                        "reviews": f"{hotel.get('reviewCount', 0)} reviews",
                        "category": "Hotel",
                    }

                    # Extract price
                    if hotel.get("price"):
                        result["price"] = hotel["price"]

                    # Extract address
                    if hotel.get("address"):
                        result["address"] = hotel["address"]

                    # Extract image
                    if hotel.get("image"):
                        result["image_url"] = hotel["image"]

                    results.append(result)
                    logger.info(f"Added hotel: {result['title']}")
            else:
                # Hotel data loads dynamically via AJAX
                logger.warning("Hotel data not available in initial page load (loads dynamically)")
                return {
                    "success": False,
                    "error": "Hotel data loads dynamically and is not available in initial page. Try using 'restaurants' or 'attractions' instead, or visit the URL directly.",
                    "query": query,
                    "location": location,
                    "category": category,
                    "suggestion_url": search_url,
                }

        logger.info(f"Extracted {len(results)} results")

        return {
            "success": True,
            "query": query,
            "location": location,
            "date": date,
            "price_range": price_range,
            "category": category,
            "results_count": len(results),
            "results": results,
        }

    except httpx.HTTPError as e:
        logger.error(f"HTTP error during search: {e}")
        return {
            "success": False,
            "error": f"HTTP error: {str(e)}",
            "query": query,
        }
    except Exception as e:
        logger.error(f"Error during search: {e}")
        return {
            "success": False,
            "error": str(e),
            "query": query,
        }


def format_results_for_display(search_data: dict[str, Any]) -> list[TextContent | ImageContent]:
    """
    Format search results for rich display in MCP client.

    Args:
        search_data: Search results from search_tripadvisor()

    Returns:
        List of MCP content items (text and images)
    """
    contents = []

    if not search_data.get("success"):
        contents.append(
            TextContent(
                type="text",
                text=f"Search failed: {search_data.get('error', 'Unknown error')}",
            )
        )
        return contents

    # Add summary
    summary_text = f"""# TripAdvisor Search Results

**Query:** {search_data.get('query', 'N/A')}
**Location:** {search_data.get('location', 'N/A')}
**Date:** {search_data.get('date', 'N/A')}
**Price Range:** {search_data.get('price_range', 'N/A')}
**Results Found:** {search_data.get('results_count', 0)}

---

"""

    contents.append(TextContent(type="text", text=summary_text))

    # Add each result
    results = search_data.get("results", [])

    if not results:
        contents.append(
            TextContent(
                type="text",
                text="No results found. Try adjusting your search parameters.",
            )
        )
        return contents

    for idx, result in enumerate(results, 1):
        # Text content for each result
        result_text = f"## {idx}. {result.get('title', 'Untitled')}\n\n"

        if result.get("rating"):
            result_text += f"**Rating:** {result['rating']}\n"

        if result.get("reviews"):
            result_text += f"**Reviews:** {result['reviews']}\n"

        if result.get("category"):
            result_text += f"**Category:** {result['category']}\n"

        if result.get("price"):
            result_text += f"**Price:** {result['price']}\n"

        if result.get("description"):
            result_text += f"\n{result['description']}\n"

        result_text += f"\n**URL:** {result.get('url', 'N/A')}\n\n"

        if result.get("image_url"):
            result_text += f"**Image:** {result['image_url']}\n"

        result_text += "---\n\n"

        contents.append(TextContent(type="text", text=result_text))

    return contents


# MCP Tool Handlers

@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available TripAdvisor MCP tools."""
    return [
        Tool(
            name="search_tripadvisor",
            description=(
                "Search TripAdvisor China (tripadvisor.cn) for restaurants, attractions, hotels, or things to do in any city. "
                "Supports Chinese and English city names (e.g., '东京', 'Tokyo', 'NYC', '纽约'). "
                "Returns pictures, URLs, ratings, reviews, and descriptions."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "What to search for. Use: 'restaurants', 'attractions', 'hotels', or 'things to do'",
                    },
                    "location": {
                        "type": "string",
                        "description": "City name in English or Chinese (e.g., 'Tokyo', '东京', 'New York', '纽约', 'LA', 'SF')",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of results to return (default: 10)",
                        "default": 10,
                    },
                },
                "required": ["query", "location"],
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """Handle tool calls."""
    try:
        if name == "search_tripadvisor":
            # Extract parameters directly from arguments
            query = arguments.get("query", "")
            location = arguments.get("location")
            max_results = arguments.get("max_results", 10)

            # Perform search
            search_data = await search_tripadvisor(
                query=query,
                location=location,
                max_results=max_results,
            )

            # Format results for display
            contents = format_results_for_display(search_data)

            # Also return raw JSON for programmatic access
            contents.append(
                TextContent(
                    type="text",
                    text=f"\n\n**Raw JSON Data:**\n```json\n{json.dumps(search_data, indent=2, ensure_ascii=False)}\n```",
                )
            )

            return contents

        else:
            return [
                TextContent(
                    type="text",
                    text=json.dumps({"success": False, "error": f"Unknown tool: {name}"}, indent=2),
                )
            ]

    except Exception as e:
        logger.error(f"Error calling tool {name}: {e}")
        return [
            TextContent(
                type="text",
                text=json.dumps({"success": False, "error": str(e)}, indent=2),
            )
        ]


async def main():
    """Run the TripAdvisor MCP server."""
    from mcp.server.stdio import stdio_server

    async with stdio_server() as (read_stream, write_stream):
        logger.info("TripAdvisor MCP Server starting...")
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options(),
        )


if __name__ == "__main__":
    asyncio.run(main())
