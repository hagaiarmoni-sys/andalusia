# normalize_hotel_cities.py
import json
import unicodedata

def normalize_city_name(city_name):
    """Remove accents and normalize"""
    if not city_name:
        return ""
    nfd = unicodedata.normalize('NFD', city_name)
    without_accents = ''.join(char for char in nfd if unicodedata.category(char) != 'Mn')
    return without_accents.strip()

# Load hotels
with open("data/andalusia_hotels_osm.json", "r", encoding="utf-8") as f:
    hotels = json.load(f)

# Backup
with open("data/andalusia_hotels_osm_backup.json", "w", encoding="utf-8") as f:
    json.dump(hotels, f, indent=2, ensure_ascii=False)

# Normalize city names (but keep original in a separate field)
for hotel in hotels:
    original_city = hotel.get("city", "")
    # Keep both versions
    hotel["city_original"] = original_city
    hotel["city"] = original_city  # Keep original for display
    
print(f"Processed {len(hotels)} hotels")

# Show what cities we have
cities = {}
for h in hotels:
    city = h.get("city", "Unknown")
    cities[city] = cities.get(city, 0) + 1

print("\nCities in hotel file:")
for city, count in sorted(cities.items()):
    normalized = normalize_city_name(city)
    print(f"  {city} (normalized: {normalized}): {count} hotels")

# Save
with open("data/andalusia_hotels_osm.json", "w", encoding="utf-8") as f:
    json.dump(hotels, f, indent=2, ensure_ascii=False)

print("\n✅ Done!")