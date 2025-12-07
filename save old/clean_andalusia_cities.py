# clean_andalusia_cities.py
import json
from datetime import datetime

with open("data/andalusia_attractions_enriched.json", "r", encoding="utf-8") as f:
    pois = json.load(f)

# Backup
backup = f"backup_before_city_cleanup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
with open(f"data/{backup}", "w", encoding="utf-8") as f:
    json.dump(pois, f, indent=2, ensure_ascii=False)

# Remove POIs with "Andalusia" as city (it's a region, not a city)
original_count = len(pois)
pois = [p for p in pois if p.get('city') != 'Andalusia']
removed = original_count - len(pois)

# Save cleaned data
with open("data/andalusia_attractions_enriched.json", "w", encoding="utf-8") as f:
    json.dump(pois, f, indent=2, ensure_ascii=False)

print(f"✅ Removed {removed} POIs with city='Andalusia'")
print(f"✅ Remaining POIs: {len(pois)}")