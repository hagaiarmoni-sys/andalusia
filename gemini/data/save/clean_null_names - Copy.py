# clean_null_names.py
import json
from datetime import datetime

print("Cleaning POIs with null names...")

with open("andalusia_attractions_enriched.json", "r", encoding="utf-8") as f:
    pois = json.load(f)

# Backup first
backup_file = f"backup_before_cleaning_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
with open(backup_file, "w", encoding="utf-8") as f:
    json.dump(pois, f, indent=2, ensure_ascii=False)
print(f"✅ Backup created: {backup_file}")

# Remove POIs with null names
original_count = len(pois)
pois = [p for p in pois if p.get('name')]
removed_count = original_count - len(pois)

# Save cleaned data
with open("andalusia_attractions_enriched.json", "w", encoding="utf-8") as f:
    json.dump(pois, f, indent=2, ensure_ascii=False)

print(f"✅ Removed {removed_count} POIs with null names")
print(f"✅ Remaining POIs: {len(pois)}")