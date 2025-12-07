"""
POI Enrichment & Discovery Script
- Enriches existing POIs with review counts
- Discovers NEW high-quality POIs (4.5+ rating, 500+ reviews)
"""

import json
import requests
import time
from collections import defaultdict

GOOGLE_API_KEY = "YOUR_API_KEY_HERE"

# Andalusian cities to search
ANDALUSIA_CITIES = [
    "Málaga", "Seville", "Granada", "Córdoba", "Cádiz", "Marbella", 
    "Ronda", "Nerja", "Antequera", "Jerez de la Frontera", "Almería",
    "Huelva", "Jaén", "Úbeda", "Baeza", "Tarifa", "Frigiliana",
    "Carmona", "Osuna", "Écija", "Vejer de la Frontera"
]

# POI types to search for (Google Places categories)
POI_TYPES = [
    'tourist_attraction',
    'museum',
    'art_gallery',
    'church',
    'mosque',
    'synagogue',
    'park',
    'zoo',
    'aquarium',
    'amusement_park',
    'natural_feature',
    'point_of_interest',
    'historic',
    'castle',
    'palace'
]

def get_place_details_for_poi(name, city, lat, lon):
    """
    Get review count for existing POI
    """
    
    # Search for place
    search_url = "https://maps.googleapis.com/maps/api/place/findplacefromtext/json"
    search_params = {
        'input': f"{name} {city} Spain",
        'inputtype': 'textquery',
        'fields': 'place_id,name',
        'locationbias': f'point:{lat},{lon}',
        'key': GOOGLE_API_KEY
    }
    
    try:
        response = requests.get(search_url, params=search_params)
        data = response.json()
        
        if data['status'] != 'OK' or not data.get('candidates'):
            return None
        
        place_id = data['candidates'][0]['place_id']
        
        # Get details
        details_url = "https://maps.googleapis.com/maps/api/place/details/json"
        details_params = {
            'place_id': place_id,
            'fields': 'user_ratings_total,rating,types,formatted_address',
            'key': GOOGLE_API_KEY
        }
        
        response = requests.get(details_url, params=details_params)
        details = response.json()
        
        if details['status'] != 'OK':
            return None
        
        result = details.get('result', {})
        return {
            'reviews_count': result.get('user_ratings_total', 0),
            'google_rating': result.get('rating'),
            'google_types': result.get('types', []),
            'google_address': result.get('formatted_address')
        }
    
    except Exception as e:
        print(f"Error: {e}")
        return None

def search_nearby_pois(city, poi_type):
    """
    Search for NEW high-quality POIs in a city
    Returns POIs with 4.5+ rating and 500+ reviews
    """
    
    # First, geocode the city to get coordinates
    geocode_url = "https://maps.googleapis.com/maps/api/geocode/json"
    geocode_params = {
        'address': f"{city}, Andalusia, Spain",
        'key': GOOGLE_API_KEY
    }
    
    try:
        response = requests.get(geocode_url, params=geocode_params)
        data = response.json()
        
        if data['status'] != 'OK' or not data.get('results'):
            return []
        
        location = data['results'][0]['geometry']['location']
        lat = location['lat']
        lng = location['lng']
        
        # Search for places nearby
        search_url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
        search_params = {
            'location': f"{lat},{lng}",
            'radius': 15000,  # 15km radius
            'type': poi_type,
            'key': GOOGLE_API_KEY
        }
        
        response = requests.get(search_url, params=search_params)
        data = response.json()
        
        if data['status'] not in ['OK', 'ZERO_RESULTS']:
            return []
        
        high_quality_pois = []
        
        for place in data.get('results', []):
            rating = place.get('rating', 0)
            reviews = place.get('user_ratings_total', 0)
            
            # Filter: 4.5+ rating AND 500+ reviews
            if rating >= 4.5 and reviews >= 500:
                
                # Get full details
                place_id = place['place_id']
                details_url = "https://maps.googleapis.com/maps/api/place/details/json"
                details_params = {
                    'place_id': place_id,
                    'fields': 'name,rating,user_ratings_total,formatted_address,geometry,types,website,formatted_phone_number,opening_hours',
                    'key': GOOGLE_API_KEY
                }
                
                response = requests.get(details_url, params=details_params)
                details = response.json()
                
                if details['status'] == 'OK':
                    result = details['result']
                    location = result['geometry']['location']
                    
                    poi = {
                        'name': result.get('name'),
                        'city': city,
                        'category': map_google_type_to_category(result.get('types', [])),
                        'rating': result.get('rating'),
                        'reviews_count': result.get('user_ratings_total'),
                        'address': result.get('formatted_address'),
                        'lat': location['lat'],
                        'lon': location['lng'],
                        'coordinates': {
                            'lat': location['lat'],
                            'lon': location['lng']
                        },
                        'website': result.get('website', ''),
                        'phone': result.get('formatted_phone_number', ''),
                        'opening_hours': result.get('opening_hours', {}).get('weekday_text', []),
                        'source': 'Google Places Discovery',
                        'google_types': result.get('types', [])
                    }
                    
                    high_quality_pois.append(poi)
                
                time.sleep(0.05)  # Rate limiting
        
        return high_quality_pois
    
    except Exception as e:
        print(f"Error searching {city}: {e}")
        return []

def map_google_type_to_category(types):
    """
    Map Google Place types to your categories
    """
    
    type_mapping = {
        'museum': 'Museum',
        'art_gallery': 'Museum',
        'church': 'Religious Site',
        'mosque': 'Religious Site',
        'synagogue': 'Religious Site',
        'park': 'Park',
        'natural_feature': 'Nature',
        'zoo': 'Family Activity',
        'aquarium': 'Family Activity',
        'amusement_park': 'Family Activity',
        'tourist_attraction': 'Landmark',
        'point_of_interest': 'Landmark',
        'castle': 'Historic Site',
        'palace': 'Historic Site'
    }
    
    for t in types:
        if t in type_mapping:
            return type_mapping[t]
    
    return 'Landmark'

def enrich_existing_pois():
    """
    Enrich existing POIs with review counts from Google
    """
    
    print("="*80)
    print("PHASE 1: ENRICHING EXISTING POIs")
    print("="*80)
    
    # Load existing POIs
    with open('andalusia_attractions_filtered.json', 'r', encoding='utf-8') as f:
        pois = json.load(f)
    
    print(f"\nEnriching {len(pois)} existing POIs...")
    
    enriched_count = 0
    failed_count = 0
    
    for i, poi in enumerate(pois):
        # Skip if already has review count
        if poi.get('reviews_count') and poi.get('reviews_count') > 0:
            continue
        
        name = poi.get('name', '')
        city = poi.get('city', '')
        lat = poi.get('lat')
        lon = poi.get('lon')
        
        if not (name and city and lat and lon):
            failed_count += 1
            continue
        
        print(f"[{i+1}/{len(pois)}] {name} ({city})...", end=' ')
        
        try:
            google_data = get_place_details_for_poi(name, city, lat, lon)
            
            if google_data and google_data['reviews_count'] > 0:
                poi['reviews_count'] = google_data['reviews_count']
                poi['google_rating'] = google_data['google_rating']
                poi['google_types'] = google_data['google_types']
                
                print(f"✅ {google_data['reviews_count']} reviews")
                enriched_count += 1
            else:
                print("❌ Not found")
                failed_count += 1
            
            time.sleep(0.05)
            
        except Exception as e:
            print(f"❌ Error: {e}")
            failed_count += 1
    
    print(f"\n{'='*80}")
    print(f"✅ Enriched: {enriched_count}")
    print(f"❌ Failed: {failed_count}")
    
    return pois

def discover_new_pois():
    """
    Discover NEW high-quality POIs (4.5+ rating, 500+ reviews)
    """
    
    print("\n" + "="*80)
    print("PHASE 2: DISCOVERING NEW HIGH-QUALITY POIs")
    print("="*80)
    print("Criteria: Rating ≥ 4.5 AND Reviews ≥ 500")
    print("="*80)
    
    all_new_pois = []
    city_stats = defaultdict(int)
    
    for city in ANDALUSIA_CITIES:
        print(f"\n🔍 Searching {city}...")
        
        city_pois = []
        
        for poi_type in POI_TYPES:
            print(f"  [{poi_type}]...", end=' ')
            
            try:
                pois = search_nearby_pois(city, poi_type)
                
                if pois:
                    print(f"✅ Found {len(pois)}")
                    city_pois.extend(pois)
                else:
                    print("❌ None")
                
                time.sleep(0.1)  # Rate limiting
                
            except Exception as e:
                print(f"❌ Error: {e}")
        
        # Remove duplicates within city
        unique_pois = {poi['name']: poi for poi in city_pois}
        city_pois = list(unique_pois.values())
        
        print(f"  📊 Total unique POIs found in {city}: {len(city_pois)}")
        city_stats[city] = len(city_pois)
        
        all_new_pois.extend(city_pois)
    
    print(f"\n{'='*80}")
    print("DISCOVERY SUMMARY:")
    print("="*80)
    for city, count in sorted(city_stats.items(), key=lambda x: x[1], reverse=True):
        print(f"  {city}: {count} new POIs")
    
    print(f"\n📊 Total new POIs discovered: {len(all_new_pois)}")
    
    return all_new_pois

def merge_and_deduplicate(existing_pois, new_pois):
    """
    Merge new POIs with existing, removing duplicates
    """
    
    print("\n" + "="*80)
    print("PHASE 3: MERGING AND DEDUPLICATING")
    print("="*80)
    
    # Create set of existing POI names (normalized)
    existing_names = {poi['name'].lower().strip() for poi in existing_pois}
    
    # Filter out duplicates
    truly_new = []
    duplicates = 0
    
    for poi in new_pois:
        name_lower = poi['name'].lower().strip()
        if name_lower not in existing_names:
            truly_new.append(poi)
            existing_names.add(name_lower)
        else:
            duplicates += 1
    
    print(f"🔍 Found {len(new_pois)} POIs from discovery")
    print(f"❌ Removed {duplicates} duplicates")
    print(f"✅ Adding {len(truly_new)} truly new POIs")
    
    # Merge
    merged = existing_pois + truly_new
    
    print(f"\n📊 Final POI count: {len(merged)}")
    print(f"   - Existing (enriched): {len(existing_pois)}")
    print(f"   - New discoveries: {len(truly_new)}")
    
    return merged

def main():
    """
    Main execution
    """
    
    print("\n" + "="*80)
    print("🚀 POI ENRICHMENT & DISCOVERY TOOL")
    print("="*80)
    print("This script will:")
    print("1. Enrich existing POIs with review counts")
    print("2. Discover NEW high-quality POIs (4.5+ rating, 500+ reviews)")
    print("3. Merge and deduplicate everything")
    print("="*80)
    
    # Get API key
    global GOOGLE_API_KEY
    api_key = input("\nEnter your Google Places API key: ")
    if api_key:
        GOOGLE_API_KEY = api_key
    
    print("\n⚠️ WARNING: This will take 1-2 HOURS and use ~3,000-5,000 API requests")
    choice = input("Continue? (yes/no): ")
    
    if choice.lower() != 'yes':
        print("Cancelled.")
        return
    
    # Phase 1: Enrich existing POIs
    enriched_pois = enrich_existing_pois()
    
    # Phase 2: Discover new POIs
    new_pois = discover_new_pois()
    
    # Phase 3: Merge and deduplicate
    final_pois = merge_and_deduplicate(enriched_pois, new_pois)
    
    # Save results
    output_file = 'andalusia_attractions_enriched.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(final_pois, f, indent=2, ensure_ascii=False)
    
    print(f"\n{'='*80}")
    print(f"✅ COMPLETE!")
    print(f"💾 Saved to: {output_file}")
    print(f"📊 Total POIs: {len(final_pois)}")
    print(f"{'='*80}")
    
    # Show quality breakdown
    print("\nQUALITY BREAKDOWN:")
    with_reviews = sum(1 for p in final_pois if p.get('reviews_count', 0) > 0)
    high_quality = sum(1 for p in final_pois if p.get('reviews_count', 0) >= 500 and p.get('rating', 0) >= 4.5)
    
    print(f"  POIs with review counts: {with_reviews}/{len(final_pois)} ({100*with_reviews/len(final_pois):.1f}%)")
    print(f"  High-quality (4.5+, 500+ reviews): {high_quality} ({100*high_quality/len(final_pois):.1f}%)")
    
    print("\n✅ Done! Replace your original file:")
    print(f"   copy andalusia_attractions_filtered.json andalusia_attractions_backup.json")
    print(f"   move {output_file} andalusia_attractions_filtered.json")

if __name__ == "__main__":
    main()
