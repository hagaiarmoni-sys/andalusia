# add_missing_hotels.py
import json

# Load existing hotels
with open("data/andalusia_hotels_osm.json", "r", encoding="utf-8") as f:
    hotels = json.load(f)

# Backup
with open("data/andalusia_hotels_osm_backup3.json", "w", encoding="utf-8") as f:
    json.dump(hotels, f, indent=2, ensure_ascii=False)

# Add hotels for missing cities
missing_city_hotels = [
    # Cádiz
    {
        "id": "MANUAL_CADIZ_001",
        "name": "Hotel Parador de Cádiz",
        "city": "Cádiz",
        "category": "Hotel",
        "coordinates": {"lat": 36.5289, "lon": -6.2931},
        "star_rating": 4,
        "avg_price_per_night_couple": 120,
        "guest_rating": None,
        "website": None,
        "phone": None,
        "amenities": ["WiFi", "Swimming pool", "Restaurant"],
        "source": "Manual",
    },
    {
        "id": "MANUAL_CADIZ_002",
        "name": "Hotel Monte Puertatierra",
        "city": "Cádiz",
        "category": "Hotel",
        "coordinates": {"lat": 36.5250, "lon": -6.2900},
        "star_rating": 4,
        "avg_price_per_night_couple": 95,
        "guest_rating": None,
        "website": None,
        "phone": None,
        "amenities": ["WiFi", "Parking"],
        "source": "Manual",
    },
    {
        "id": "MANUAL_CADIZ_003",
        "name": "Hotel Spa Cádiz Plaza",
        "city": "Cádiz",
        "category": "Hotel",
        "coordinates": {"lat": 36.5280, "lon": -6.2950},
        "star_rating": 4,
        "avg_price_per_night_couple": 110,
        "guest_rating": None,
        "website": None,
        "phone": None,
        "amenities": ["WiFi", "Spa"],
        "source": "Manual",
    },
    
    # Almería
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
        "amenities": ["WiFi", "Swimming pool"],
        "source": "Manual",
    },
    
    # Ronda
    {
        "id": "MANUAL_RONDA_001",
        "name": "Hotel Catalonia Ronda",
        "city": "Ronda",
        "category": "Hotel",
        "coordinates": {"lat": 36.7425, "lon": -5.1642},
        "star_rating": 4,
        "avg_price_per_night_couple": 100,
        "guest_rating": None,
        "website": None,
        "phone": None,
        "amenities": ["WiFi", "Restaurant"],
        "source": "Manual",
    },
    {
        "id": "MANUAL_RONDA_002",
        "name": "Parador de Ronda",
        "city": "Ronda",
        "category": "Hotel",
        "coordinates": {"lat": 36.7408, "lon": -5.1653},
        "star_rating": 4,
        "avg_price_per_night_couple": 130,
        "guest_rating": None,
        "website": None,
        "phone": None,
        "amenities": ["WiFi", "Restaurant", "Parking"],
        "source": "Manual",
    },
    {
        "id": "MANUAL_RONDA_003",
        "name": "Hotel Maestranza",
        "city": "Ronda",
        "category": "Hotel",
        "coordinates": {"lat": 36.7400, "lon": -5.1650},
        "star_rating": 3,
        "avg_price_per_night_couple": 85,
        "guest_rating": None,
        "website": None,
        "phone": None,
        "amenities": ["WiFi"],
        "source": "Manual",
    },
    
    # Huelva
    {
        "id": "MANUAL_HUELVA_001",
        "name": "Hotel Exe Tartessos",
        "city": "Huelva",
        "category": "Hotel",
        "coordinates": {"lat": 37.2614, "lon": -6.9447},
        "star_rating": 4,
        "avg_price_per_night_couple": 90,
        "guest_rating": None,
        "website": None,
        "phone": None,
        "amenities": ["WiFi", "Parking"],
        "source": "Manual",
    },
    {
        "id": "MANUAL_HUELVA_002",
        "name": "AC Hotel Huelva",
        "city": "Huelva",
        "category": "Hotel",
        "coordinates": {"lat": 37.2600, "lon": -6.9500},
        "star_rating": 4,
        "avg_price_per_night_couple": 95,
        "guest_rating": None,
        "website": None,
        "phone": None,
        "amenities": ["WiFi", "Air conditioning"],
        "source": "Manual",
    },
    
    # Jaén
    {
        "id": "MANUAL_JAEN_001",
        "name": "Parador de Jaén",
        "city": "Jaén",
        "category": "Hotel",
        "coordinates": {"lat": 37.7647, "lon": -3.7683},
        "star_rating": 4,
        "avg_price_per_night_couple": 110,
        "guest_rating": None,
        "website": None,
        "phone": None,
        "amenities": ["WiFi", "Swimming pool", "Restaurant"],
        "source": "Manual",
    },
    {
        "id": "MANUAL_JAEN_002",
        "name": "Hotel Infanta Cristina",
        "city": "Jaén",
        "category": "Hotel",
        "coordinates": {"lat": 37.7650, "lon": -3.7700},
        "star_rating": 4,
        "avg_price_per_night_couple": 85,
        "guest_rating": None,
        "website": None,
        "phone": None,
        "amenities": ["WiFi", "Parking"],
        "source": "Manual",
    },
    
    # Antequera
    {
        "id": "MANUAL_ANTEQUERA_001",
        "name": "Parador de Antequera",
        "city": "Antequera",
        "category": "Hotel",
        "coordinates": {"lat": 37.0236, "lon": -4.5481},
        "star_rating": 4,
        "avg_price_per_night_couple": 95,
        "guest_rating": None,
        "website": None,
        "phone": None,
        "amenities": ["WiFi", "Swimming pool"],
        "source": "Manual",
    },
    {
        "id": "MANUAL_ANTEQUERA_002",
        "name": "Hotel Convento La Magdalena",
        "city": "Antequera",
        "category": "Hotel",
        "coordinates": {"lat": 37.0200, "lon": -4.5500},
        "star_rating": 3,
        "avg_price_per_night_couple": 80,
        "guest_rating": None,
        "website": None,
        "phone": None,
        "amenities": ["WiFi"],
        "source": "Manual",
    },
    
    # Úbeda
    {
        "id": "MANUAL_UBEDA_001",
        "name": "Parador de Úbeda",
        "city": "Úbeda",
        "category": "Hotel",
        "coordinates": {"lat": 38.0075, "lon": -3.3708},
        "star_rating": 4,
        "avg_price_per_night_couple": 105,
        "guest_rating": None,
        "website": None,
        "phone": None,
        "amenities": ["WiFi", "Restaurant"],
        "source": "Manual",
    },
    {
        "id": "MANUAL_UBEDA_002",
        "name": "Hotel Palacio de Úbeda",
        "city": "Úbeda",
        "category": "Hotel",
        "coordinates": {"lat": 38.0080, "lon": -3.3700},
        "star_rating": 4,
        "avg_price_per_night_couple": 90,
        "guest_rating": None,
        "website": None,
        "phone": None,
        "amenities": ["WiFi", "Parking"],
        "source": "Manual",
    },
    
    # Baeza
    {
        "id": "MANUAL_BAEZA_001",
        "name": "Hotel Puerta de la Luna",
        "city": "Baeza",
        "category": "Hotel",
        "coordinates": {"lat": 37.9931, "lon": -3.4697},
        "star_rating": 4,
        "avg_price_per_night_couple": 95,
        "guest_rating": None,
        "website": None,
        "phone": None,
        "amenities": ["WiFi", "Restaurant"],
        "source": "Manual",
    },
]

# Add to existing hotels
hotels.extend(missing_city_hotels)

# Save
with open("data/andalusia_hotels_osm.json", "w", encoding="utf-8") as f:
    json.dump(hotels, f, indent=2, ensure_ascii=False)

print(f"✅ Added {len(missing_city_hotels)} hotels for missing cities")
print(f"✅ Total hotels now: {len(hotels)}")

# Show hotels by city
print("\n📊 Hotels by city:")
cities = {}
for h in hotels:
    city = h.get("city", "Unknown")
    cities[city] = cities.get(city, 0) + 1

for city, count in sorted(cities.items()):
    print(f"  {city}: {count} hotels")