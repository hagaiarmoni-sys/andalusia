import json
import time
import pathlib
import requests

# -------------------------
# CONFIG
# -------------------------

# Path to a single file (Córdoba)
CORDOBA_FILE = r"C:\Users\Hagai\PycharmProjects\pythonProject4\andalusia-app\data\andalusia_hotels_osm.json"

# Or, if you want to process all restaurant files at once, you can use a glob:
# REST_FILES_GLOB = r"C:\Users\Hagai\PycharmProjects\pythonProject4\andalusia-app-GPT-v2\Restaurants_*.json"

# Nominatim base URL
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"

# IMPORTANT: Put your email in the User-Agent as per Nominatim usage policy
HEADERS = {
    "User-Agent": "andalusia-app-gpt/1.0 (your_email@example.com)"
}

# Seconds between requests (please be nice – 1 second is recommended)
REQUEST_SLEEP_SECONDS = 1.1


# -------------------------
# HELPER FUNCTIONS
# -------------------------

def load_json(path: pathlib.Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: pathlib.Path, data):
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def build_query(restaurant: dict) -> str:
    """
    Build a search query for Nominatim.
    Example: 'Bodegas Mezquita Cruz Del Rastro, Córdoba, Andalusia, Spain'
    """
    name = restaurant.get("name", "")
    city = restaurant.get("city", "")
    parts = [name]
    if city:
        parts.append(city)
    parts.append("Andalusia")
    parts.append("Spain")
    return ", ".join(p for p in parts if p)


def lookup_address(query: str):
    """
    Call Nominatim and return (display_name, lat, lon) or (None, None, None)
    """
    params = {
        "q": query,
        "format": "json",
        "addressdetails": 1,
        "limit": 1,
    }

    try:
        resp = requests.get(NOMINATIM_URL, params=params, headers=HEADERS, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        print(f"  ⚠️ Request failed for '{query}': {e}")
        return None, None, None

    data = resp.json()
    if not data:
        print(f"  ❌ No results for '{query}'")
        return None, None, None

    best = data[0]
    display_name = best.get("display_name")
    lat = best.get("lat")
    lon = best.get("lon")

    return display_name, lat, lon


def enrich_file(path: pathlib.Path):
    print(f"\n=== Processing {path.name} ===")
    items = load_json(path)

    updated = 0
    total = len(items)

    for idx, r in enumerate(items, start=1):
        addr = r.get("address", "").strip()
        if addr:
            # Already has an address – skip
            continue

        query = build_query(r)
        print(f"[{idx}/{total}] Looking up: {query}")

        display_name, lat, lon = lookup_address(query)

        # Respect rate limit
        time.sleep(REQUEST_SLEEP_SECONDS)

        if display_name:
            r["address"] = display_name
            if lat and lon:
                # Add coordinates if not present
                r["lat"] = float(lat)
                r["lon"] = float(lon)
            updated += 1
            print(f"  ✅ Found: {display_name}")
        else:
            # Mark explicitly as not found (optional)
            # r["address"] = ""
            print("  ⛔ Not found")

    save_json(path, items)
    print(f"Done {path.name}: updated {updated} / {total} restaurants.")


def main():
    # Option A: just Córdoba
    path = pathlib.Path(CORDOBA_FILE)
    enrich_file(path)

    # Option B: uncomment to process all matching files:
    # base = pathlib.Path(r"C:\Users\Hagai\PycharmProjects\pythonProject4\andalusia-app-GPT-v2")
    # for file in base.glob("Restaurants_*.json"):
    #     enrich_file(file)


if __name__ == "__main__":
    main()
