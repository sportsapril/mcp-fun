#!/usr/bin/env python3
import httpx
import json
from bs4 import BeautifulSoup

# Fetch search page
url = "https://www.tripadvisor.cn/Search?q=%E7%BF%A0%E6%B9%96%E5%85%AC%E5%9B%AD&geo=298558"
response = httpx.get(url, timeout=30)

# Parse HTML
soup = BeautifulSoup(response.text, "html.parser")
next_data_script = soup.find("script", {"id": "__NEXT_DATA__"})

if next_data_script:
    data = json.loads(next_data_script.string)

    # Print structure
    page_props = data.get("props", {}).get("pageProps", {})

    print("=== PageProps Keys ===")
    print(list(page_props.keys()))
    print()

    # Check for urqlState
    if "urqlState" in page_props:
        print("=== urqlState Keys ===")
        urql_state = page_props["urqlState"]
        print(list(urql_state.keys())[:5])  # First 5 keys
        print()

        # Find data in urqlState
        for key, value in list(urql_state.items())[:3]:
            print(f"=== urqlState['{key[:50]}...'] ===")
            if isinstance(value, dict) and "data" in value:
                print("Has 'data' key!")
                data_obj = value["data"]
                print("Data keys:", list(data_obj.keys()) if isinstance(data_obj, dict) else type(data_obj))

                # Check for locations
                if isinstance(data_obj, dict) and "locations" in data_obj:
                    locations = data_obj["locations"]
                    print(f"Found {len(locations)} locations")
                    if len(locations) > 0:
                        print("First location keys:", list(locations[0].keys()) if isinstance(locations[0], dict) else type(locations[0]))
                        print("First location:", json.dumps(locations[0], indent=2, ensure_ascii=False)[:500])
            print()

    # Check initialState
    if "initialState" in page_props:
        print("=== initialState ===")
        init_state = page_props["initialState"]
        print("Keys:", list(init_state.keys()))
else:
    print("No __NEXT_DATA__ found")
