import json
from pathlib import Path

# 🔧 CHANGE THIS to the file your app is actually using now:
INPUT_FILE = Path("andalusia_attractions_filtered.json")
OUTPUT_FILE = Path("andalusia_attractions_fixed_osuna_categories.json")

CATEGORY_MAP = {
    "Religious": "religious",
    "Religious Site": "religious",
    "Church": "religious",
    "Convent Church": "religious",

    "Street/Architecture": "neighborhoods",
    "Street": "neighborhoods",

    "Architectural Building": "architecture",
    "Monument": "history",
    "Civic": "architecture",

    "Museum/Art": "museums",

    "Historic Towns": "history",
    "Historic Site": "history",
}

def fix_osuna_categories(path_in: Path, path_out: Path):
    data = json.loads(path_in.read_text(encoding="utf-8"))

    changed = 0
    for poi in data:
        if poi.get("city") != "Osuna":
            continue

        cat = poi.get("category")
        new_cat = CATEGORY_MAP.get(cat)
        if new_cat and new_cat != cat:
            poi["category"] = new_cat
            changed += 1

    print(f"Changed categories for {changed} Osuna POIs")
    path_out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Written fixed file to: {path_out}")

if __name__ == "__main__":
    fix_osuna_categories(INPUT_FILE, OUTPUT_FILE)
