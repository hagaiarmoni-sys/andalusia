# extract_osm_hotels.py
"""
Extract hotels from OpenStreetMap for Andalusian cities
"""

import requests
import json
import time
import os
from datetime import datetime

# ============================================================================
# CONFIGURATION
# ============================================================================

OUTPUT_FILE = "data/andalusia_hotels_osm.json"
BACKUP_FILE = f"data/backup_hotels_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

# Major Andalusian cities (add more as needed)
CITIES = [
    # Major cities
    {"name": "Sevilla", "country": "España"},
    {"name": "Granada", "country": "España"},
    {"name": "Córdoba", "country": "España"},
    {"name": "Málaga", "country": "España"},
    {"name": "Almería", "country": "España"},
    {"name": "Cádiz", "country": "España"},
    {"name": "Jaén", "country": "España"},
    {"name": "Huelva", "country": "España"},
    
    # Popular tourist destinations
    {"name": "Marbella", "country": "España"},
    {"name": "Ronda", "country": "España"},
    {"name": "Jerez de la Frontera", "country": "España"},
    {"name": "Nerja", "country": "España"},
    {"name": "Tarifa", "country": "España"},
    {"name": "Antequera", "country": "España"},
    {"name": "Úbeda", "country": "España"},
    {"name": "Baeza", "country": "España"},
    {"name": "Carmona", "country": "España"},
    {"name": "Osuna", "country": "España"},
    {"name": "Sanlúcar de Barrameda", "country": "España"},
    {"name": "El Puerto de Santa María", "country": "España"},
    {"name": "Estepona", "country": "España"},
    {"name": "Torremolinos", "country": "España"},
    {"name": "Fuengirola", "country": "España"},
]

HOTELS_PER_CITY = 15  # Number of hotels to fetch per city
DELAY_BETWEEN_REQUESTS = 3  # Seconds (be nice to OSM servers!)

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_osm_hotels(city_name, country="España", limit=15):
    """
    Fetch hotels from OpenStreetMap using Overpass API
    
    Args:
        city_name: Name of the city
        country: Country name (default España)
        limit: Maximum number of hotels to return
    
    Returns:
        List of hotel dictionaries
    """
    
    overpass_url = "http://overpass-api.de/api/interpreter"
    
    # Overpass QL query to find hotels in a city
    query = f"""
    [out:json][timeout:25];
    area["name"="{city_name}"]["admin_level"~"[68]"]->.searchArea;
    (
      node["tourism"="hotel"](area.searchArea);
      way["tourism"="hotel"](area.searchArea);
      relation["tourism"="hotel"](area.searchArea);
    );
    out center {limit};
    """
    
    try:
        print(f"  Querying OpenStreetMap for {city_name}...")
        response = requests.post(
            overpass_url, 
            data={"data": query}, 
            timeout=30,
            headers={'User-Agent': 'Andalusia-Travel-App/1.0'}
        )
        
        if response.status_code != 200:
            print(f"  ❌ HTTP {response.status_code} for {city_name}")
            return []
        
        data = response.json()
        
        hotels = []
        for element in data.get("elements", []):
            # Get coordinates
            if element.get("type") == "node":
                lat = element.get("lat")
                lon = element.get("lon")
            else:  # way or relation
                center = element.get("center", {})
                lat = center.get("lat")
                lon = center.get("lon")
            
            if not lat or not lon:
                continue
            
            tags = element.get("tags", {})
            
            # Parse star rating
            stars = tags.get("stars")
            if stars:
                try:
                    stars = int(stars)
                except:
                    stars = None
            
            # Create hotel object
            hotel = {
                "id": f"OSM_{element.get('type')}_{element.get('id')}",
                "name": tags.get("name", f"Hotel in {city_name}"),
                "city": city_name,
                "category": "Hotel",
                "coordinates": {
                    "lat": float(lat),
                    "lon": float(lon)
                },
                "star_rating": stars,
                "avg_price_per_night_couple": None,  # OSM doesn't have prices
                "guest_rating": None,
                "website": tags.get("website") or tags.get("contact:website"),
                "phone": tags.get("phone") or tags.get("contact:phone"),
                "email": tags.get("email") or tags.get("contact:email"),
                "opening_hours": tags.get("opening_hours"),
                "amenities": [],
                "source": "OpenStreetMap",
                "osm_id": element.get("id"),
                "osm_type": element.get("type")
            }
            
            # Extract amenities
            amenities = []
            if tags.get("internet_access") == "wlan":
                amenities.append("WiFi")
            if tags.get("parking") == "yes":
                amenities.append("Parking")
            if tags.get("wheelchair") == "yes":
                amenities.append("Wheelchair accessible")
            if tags.get("air_conditioning") == "yes":
                amenities.append("Air conditioning")
            if tags.get("swimming_pool") == "yes":
                amenities.append("Swimming pool")
            if tags.get("restaurant") == "yes":
                amenities.append("Restaurant")
            
            hotel["amenities"] = amenities
            
            hotels.append(hotel)
        
        return hotels
        
    except requests.exceptions.Timeout:
        print(f"  ⏱️ Timeout for {city_name}")
        return []
    except requests.exceptions.RequestException as e:
        print(f"  ❌ Request error for {city_name}: {e}")
        return []
    except json.JSONDecodeError as e:
        print(f"  ❌ JSON decode error for {city_name}: {e}")
        return []
    except Exception as e:
        print(f"  ❌ Unexpected error for {city_name}: {e}")
        return []

# ============================================================================
# MAIN EXTRACTION
# ============================================================================

def main():
    print("=" * 70)
    print("OSM HOTEL EXTRACTION FOR ANDALUSIA")
    print("=" * 70)
    print("\n⚠️ Starting fresh extraction (ignoring existing hotels)")
    
    # Create data directory if it doesn't exist
    os.makedirs("data", exist_ok=True)
    
    # Start with empty list
    existing_hotels = []
    existing_ids = set()
    
    # Fetch hotels from OSM
    print(f"\n" + "=" * 70)
    print(f"FETCHING HOTELS FROM {len(CITIES)} CITIES")
    print("=" * 70)
    
    all_new_hotels = []
    
    for i, city_info in enumerate(CITIES, 1):
        city_name = city_info["name"]
        print(f"\n[{i}/{len(CITIES)}] {city_name}")
        
        hotels = get_osm_hotels(city_name, limit=HOTELS_PER_CITY)
        
        if hotels:
            # Filter out duplicates
            new_hotels = [h for h in hotels if h.get("id") not in existing_ids]
            all_new_hotels.extend(new_hotels)
            
            print(f"  ✅ Found {len(hotels)} hotels ({len(new_hotels)} new)")
            
            # Add new IDs to existing set
            existing_ids.update(h.get("id") for h in new_hotels)
        else:
            print(f"  ⚠️ No hotels found")
        
        # Rate limiting - be nice to OSM servers
        if i < len(CITIES):
            print(f"  ⏳ Waiting {DELAY_BETWEEN_REQUESTS}s...")
            time.sleep(DELAY_BETWEEN_REQUESTS)
    
    # ========================================================================
    # SAVE RESULTS
    # ========================================================================
    
    print("\n" + "=" * 70)
    print("SAVING RESULTS")
    print("=" * 70)
    
    # Save extracted hotels
    all_hotels = all_new_hotels
    
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(all_hotels, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Saved {len(all_hotels)} hotels to {OUTPUT_FILE}")
    
    # ========================================================================
    # STATISTICS
    # ========================================================================
    
    print("\n" + "=" * 70)
    print("STATISTICS BY CITY")
    print("=" * 70)
    
    city_counts = {}
    for hotel in all_hotels:
        city = hotel.get("city", "Unknown")
        city_counts[city] = city_counts.get(city, 0) + 1
    
    for city, count in sorted(city_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"{city:30} {count:3} hotels")
    
    print("\n" + "=" * 70)
    print("✅ EXTRACTION COMPLETE!")
    print("=" * 70)
    
    print(f"\nNext steps:")
    print(f"1. Review {OUTPUT_FILE}")
    print(f"2. Update app.py to use: data/andalusia_hotels_osm.json")
    print(f"3. Test trip generation with new hotels!")

# ============================================================================
# RUN
# ============================================================================

if __name__ == "__main__":
    main()