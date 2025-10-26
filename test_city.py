#!/usr/bin/env python3
"""
Simple test script to check if a city can be found in TripAdvisor MCP

Usage:
    python test_city.py <city_name>
    python test_city.py Dezhou
    python test_city.py 德州
    python test_city.py "New York"
"""
import asyncio
import sys

sys.path.insert(0, 'src')

from tripadvisor_mcp.server import (
    lookup_geo_id_from_csv,
    match_city_with_llm,
    lookup_geo_id_dynamic,
    LOCATION_GEO_IDS,
    load_location_database,
    _location_database,
)


async def test_city(city_name: str):
    """Test if a city can be found using the four-tier lookup system"""

    print("=" * 80)
    print(f"TESTING CITY: {city_name}")
    print("=" * 80)
    print()

    # Tier 1: CSV lookup
    print("[Tier 1] CSV Database Lookup")
    print("-" * 60)
    geo_id = lookup_geo_id_from_csv(city_name)
    if geo_id:
        print(f"✅ FOUND in CSV: {geo_id}")
        print(f"   This is the fastest lookup method (<1ms)")
        return geo_id
    else:
        print(f"❌ Not found in CSV database")
    print()

    # Tier 2: Hardcoded Chinese cities
    print("[Tier 2] Hardcoded Chinese Cities")
    print("-" * 60)
    geo_id = LOCATION_GEO_IDS.get(city_name.lower())
    if geo_id:
        print(f"✅ FOUND in hardcoded list: {geo_id}")
        print(f"   This is very fast (<1ms)")
        return geo_id
    else:
        print(f"❌ Not found in hardcoded list")
    print()

    # Tier 3: LLM matching
    print("[Tier 3] LLM Intelligent Matching")
    print("-" * 60)
    try:
        import os
        if not os.getenv("ANTHROPIC_API_KEY"):
            print("⚠️  ANTHROPIC_API_KEY not set - skipping LLM matching")
        else:
            print(f"Asking Claude Haiku 3 to match '{city_name}' to database...")
            load_location_database()
            available_cities = list(_location_database.keys())
            matched_city = await match_city_with_llm(city_name, available_cities)

            if matched_city and matched_city in _location_database:
                entries = _location_database[matched_city]
                location_id = entries[0]["locationId"]
                geo_id = f"g{location_id}"
                print(f"✅ LLM matched '{city_name}' → '{matched_city}': {geo_id}")
                print(f"   This takes ~200-500ms")
                return geo_id
            else:
                print(f"❌ LLM could not find a match")
    except Exception as e:
        print(f"❌ LLM matching failed: {e}")
    print()

    # Tier 4: Playwright dynamic lookup
    print("[Tier 4] Playwright Dynamic Lookup")
    print("-" * 60)
    print(f"⚠️  This may take 15-20 seconds...")
    print(f"Searching TripAdvisor for '{city_name}'...")
    geo_id = await lookup_geo_id_dynamic(city_name)
    if geo_id:
        print(f"✅ FOUND via Playwright: {geo_id}")
        print(f"   This took 15-20 seconds")
        print(f"   City has been saved to world.csv for future instant lookups!")
        return geo_id
    else:
        print(f"❌ Could not find city via Playwright")
    print()

    return None


async def main():
    if len(sys.argv) < 2:
        print("Usage: python test_city.py <city_name>")
        print()
        print("Examples:")
        print("  python test_city.py Dezhou")
        print("  python test_city.py 德州")
        print("  python test_city.py \"New York\"")
        print("  python test_city.py Tokyo")
        sys.exit(1)

    city_name = " ".join(sys.argv[1:])  # Join all args in case city has spaces

    geo_id = await test_city(city_name)

    print("=" * 80)
    if geo_id:
        print(f"✅ SUCCESS: City '{city_name}' found with geo ID: {geo_id}")
        print()
        print("You can now search this city in TripAdvisor MCP:")
        print(f"  - Restaurants: search_tripadvisor(query='restaurants', location='{city_name}')")
        print(f"  - Attractions: search_tripadvisor(query='attractions', location='{city_name}')")
    else:
        print(f"❌ FAILED: Could not find city '{city_name}'")
        print()
        print("Possible reasons:")
        print("  - City name misspelled")
        print("  - City not covered by TripAdvisor")
        print("  - Network issues during Playwright lookup")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
