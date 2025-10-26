"""
Helper script to add a new city to the CSV database.

Usage:
    python add_city_to_csv.py "无棣" "https://www.tripadvisor.cn/Tourism-g1795759-Wudi_County_Shandong-Vacations.html"

Or run interactively:
    python add_city_to_csv.py
"""
import csv
import re
import sys
from pathlib import Path

def extract_geo_id(url):
    """Extract geo ID from TripAdvisor URL"""
    match = re.search(r'[-/]g(\d+)[-/]', url)
    if match:
        return match.group(1)
    return None

def add_city(city_name, url, csv_file="data/tripadvisor_geo_map/world.csv"):
    """Add a city to the CSV file"""

    # Extract geo ID from URL
    geo_id = extract_geo_id(url)
    if not geo_id:
        print(f"❌ Could not extract geo ID from URL: {url}")
        return False

    print(f"Found geo ID: g{geo_id}")

    # Read existing CSV
    csv_path = Path(csv_file)
    if not csv_path.exists():
        print(f"❌ CSV file not found: {csv_file}")
        return False

    # Check if city already exists
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['location'].lower() == city_name.lower():
                print(f"⚠️  City '{city_name}' already exists in CSV with geo ID: {row['locationId']}")
                return False

    # Append new row
    with open(csv_path, 'a', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['', city_name, geo_id, url])

    print(f"✅ Added '{city_name}' (g{geo_id}) to {csv_file}")
    return True

def main():
    if len(sys.argv) == 3:
        city_name = sys.argv[1]
        url = sys.argv[2]
    else:
        print("Add a new city to TripAdvisor CSV database")
        print("=" * 60)
        print("\n1. Go to https://www.tripadvisor.cn")
        print("2. Search for your city")
        print("3. Click the first result (the destination page)")
        print("4. Copy the full URL from your browser\n")

        city_name = input("Enter city name (Chinese or English): ").strip()
        if not city_name:
            print("❌ City name cannot be empty")
            return

        url = input("Enter the full Tourism URL: ").strip()
        if not url:
            print("❌ URL cannot be empty")
            return

    # Add to CSV
    success = add_city(city_name, url)

    if success:
        print("\n📝 Next steps:")
        print("1. Commit the updated CSV file to git")
        print("2. The city will be available immediately in the MCP")
        print(f"3. Test with: python -c \"from src.tripadvisor_mcp.server import lookup_geo_id_from_csv; print(lookup_geo_id_from_csv('{city_name}'))\"")

if __name__ == "__main__":
    main()
