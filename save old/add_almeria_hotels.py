# add_almeria_hotels.py
import json

# Load existing hotels
with open("data/andalusia_hotels_osm.json", "r", encoding="utf-8") as f:
    hotels = json.load(f)

# Backup
with open("data/andalusia_hotels_osm_backup2.json", "w", encoding="utf-8") as f:
    json.dump(hotels, f, indent=2, ensure_ascii=False)

# Add some Almería hotels manually
almeria_hotels = [
    {
        "id": "MANUAL_ALMERIA_001",
        "name": "Hotel Catedral Almería",
        "city": "Almería",
        "category": "Hotel",
        "coordinates": {"lat": 36.8400, "lon": -2.4681},
        "star_rating": 4,
        "avg_price_per_night_couple": 100,
        "guest_rating": None,
        "website": None,
        "phone": None,
        "amenities": ["WiFi", "Air conditioning"],
        "source": "Manual",
    },
    {
        "id": "MANUAL_ALMERIA_002",
        "name": "Hotel Nuevo Torreluz",
        "city": "Almería",
        "category": "Hotel",
        "coordinates": {"lat": 36.8389, "lon": -2.4631},
        "star_rating": 4,
        "avg_price_per_night_couple": 90,
        "guest_rating": None,
        "website": None,
        "phone": None,
        "amenities": ["WiFi", "Parking"],
        "source": "Manual",
    },
    {
        "id": "MANUAL_ALMERIA_003",
        "name": "AC Hotel Almería",
        "city": "Almería",
        "category": "Hotel",
        "coordinates": {"lat": 36.8370, "lon": -2.4580},
        "star_rating": 4,
        "avg_price_per_night_couple": 110,
        "guest_rating": None,
        "website": None,
        "phone": None,
        "amenities": ["WiFi", "Swimming pool", "Restaurant"],
        "source": "Manual",
    },
    {
        "id": "MANUAL_ALMERIA_004",
        "name": "Hotel Costasol",
        "city": "Almería",
        "category": "Hotel",
        "coordinates": {"lat": 36.8350, "lon": -2.4620},
        "star_rating": 3,
        "avg_price_per_night_couple": 75,
        "guest_rating": None,
        "website": None,
        "phone": None,
        "amenities": ["WiFi"],
        "source": "Manual",
    },
    {
        "id": "MANUAL_ALMERIA_005",
        "name": "Hotel AM Torreluz",
        "city": "Almería",
        "category": "Hotel",
        "coordinates": {"lat": 36.8380, "lon": -2.4640},
        "star_rating": 3,
        "avg_price_per_night_couple": 80,
        "guest_rating": None,
        "website": None,
        "phone": None,
        "amenities": ["WiFi", "Air conditioning"],
        "source": "Manual",
    },
]

# Add to existing hotels
hotels.extend(almeria_hotels)

# Save
with open("data/andalusia_hotels_osm.json", "w", encoding="utf-8") as f:
    json.dump(hotels, f, indent=2, ensure_ascii=False)

print(f"✅ Added {len(almeria_hotels)} hotels for Almería")
print(f"✅ Total hotels now: {len(hotels)}")

# Verify
almeria_count = sum(1 for h in hotels if "almer" in h.get("city", "").lower())
print(f"✅ Almería now has {almeria_count} hotels")