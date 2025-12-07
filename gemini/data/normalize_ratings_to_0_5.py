import json
from pathlib import Path

INPUT_FILE = Path("andalusia_attractions_filtered.json")
OUTPUT_FILE = Path("andalusia_attractions_filtered_ratings_fixed.json")

def safe_float(x):
    if x is None:
        return None
    try:
        return float(x)
    except (ValueError, TypeError):
        return None

def normalize_rating_0_5(raw):
    """
    Convert mixed 0–10 / 0–5 ratings into a unified 0–5 rating
    with 1 decimal place.
    """
    r = safe_float(raw)
    if r is None:
        return None

    # If rating > 5, assume it was on a 0–10 scale → convert to 0–5
    if r > 5:
        r = r / 2.0

    # Clamp just in case of weird values
    if r < 0:
        r = 0.0
    if r > 5:
        r = 5.0

    return round(r, 1)

def main():
    if not INPUT_FILE.exists():
        print(f"ERROR: Cannot find {INPUT_FILE}")
        return

    pois = json.loads(INPUT_FILE.read_text(encoding="utf-8"))
    if not isinstance(pois, list):
        print("ERROR: Expected a JSON array of POIs at top level.")
        return

    changed = 0
    for poi in pois:
        old_rating = poi.get("rating", None)
        new_rating = normalize_rating_0_5(old_rating)

        # Only touch the field if we could interpret it
        if new_rating is not None:
            if new_rating != old_rating:
                changed += 1
            poi["rating"] = new_rating
        else:
            # Keep as null / missing if we couldn't parse
            poi["rating"] = None

    OUTPUT_FILE.write_text(
        json.dumps(pois, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print(f"Processed {len(pois)} POIs.")
    print(f"Ratings normalized/changed for about {changed} POIs.")
    print(f"Output written to: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
