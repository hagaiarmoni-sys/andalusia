"""
Enrich Hotels & Restaurants with Google Places API Review Counts
"""

import json
import requests
import time

# Get your API key from: https://console.cloud.google.com/google/maps-apis
GOOGLE_API_KEY = "YOUR_API_KEY_HERE"

def get_place_details(name, address, lat, lon):
    """
    Search for place and get review count from Google Places
    """
    
    # Step 1: Find Place (search by name + location)
    search_url = "https://maps.googleapis.com/maps/api/place/findplacefromtext/json"
    search_params = {
        'input': f"{name} {address}",
        'inputtype': 'textquery',
        'fields': 'place_id,name',
        'locationbias': f'point:{lat},{lon}',
        'key': GOOGLE_API_KEY
    }
    
    response = requests.get(search_url, params=search_params)
    data = response.json()
    
    if data['status'] != 'OK' or not data.get('candidates'):
        return None
    
    place_id = data['candidates'][0]['place_id']
    
    # Step 2: Get Place Details (including review count)
    details_url = "https://maps.googleapis.com/maps/api/place/details/json"
    details_params = {
        'place_id': place_id,
        'fields': 'user_ratings_total,rating,price_level,formatted_phone_number',
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
        'google_price_level': result.get('price_level'),
        'phone': result.get('formatted_phone_number')
    }

def enrich_restaurants():
    """
    Enrich restaurants_andalusia.json with Google Places data
    """
    
    # Load existing data
    with open('restaurants_andalusia.json', 'r', encoding='utf-8') as f:
        restaurants = json.load(f)
    
    print(f"Enriching {len(restaurants)} restaurants...")
    
    enriched_count = 0
    failed_count = 0
    
    for i, restaurant in enumerate(restaurants):
        # Skip if already has review count
        if restaurant.get('reviews_count'):
            continue
        
        # Try to get from Google
        name = restaurant.get('name', '')
        address = restaurant.get('address', '')
        lat = restaurant.get('lat')
        lon = restaurant.get('lon')
        
        if not (name and lat and lon):
            failed_count += 1
            continue
        
        print(f"[{i+1}/{len(restaurants)}] {name}...", end=' ')
        
        try:
            google_data = get_place_details(name, address, lat, lon)
            
            if google_data and google_data['reviews_count'] > 0:
                # Add Google data to restaurant
                restaurant['reviews_count'] = google_data['reviews_count']
                restaurant['google_rating'] = google_data['google_rating']
                restaurant['google_price_level'] = google_data['google_price_level']
                if google_data['phone']:
                    restaurant['phone'] = google_data['phone']
                
                print(f"✅ {google_data['reviews_count']} reviews")
                enriched_count += 1
            else:
                print("❌ Not found")
                failed_count += 1
            
            # Rate limiting (Google allows ~50 requests/second)
            time.sleep(0.05)  # 50ms delay
            
        except Exception as e:
            print(f"❌ Error: {e}")
            failed_count += 1
    
    # Save enriched data
    with open('restaurants_andalusia_enriched.json', 'w', encoding='utf-8') as f:
        json.dump(restaurants, f, indent=2, ensure_ascii=False)
    
    print(f"\n{'='*60}")
    print(f"✅ Enriched: {enriched_count}")
    print(f"❌ Failed: {failed_count}")
    print(f"💾 Saved to: restaurants_andalusia_enriched.json")

def enrich_hotels():
    """
    Enrich hotels JSON with Google Places data
    """
    
    # Load existing data
    with open('andalusia_hotels_osm.json', 'r', encoding='utf-8') as f:
        hotels = json.load(f)
    
    print(f"Enriching {len(hotels)} hotels...")
    
    enriched_count = 0
    failed_count = 0
    
    for i, hotel in enumerate(hotels):
        # Skip if already has review count
        if hotel.get('reviews_count'):
            continue
        
        name = hotel.get('name', '')
        address = hotel.get('address', '')
        lat = hotel.get('lat')
        lon = hotel.get('lon')
        
        if not (name and lat and lon):
            failed_count += 1
            continue
        
        print(f"[{i+1}/{len(hotels)}] {name}...", end=' ')
        
        try:
            google_data = get_place_details(name, address, lat, lon)
            
            if google_data and google_data['reviews_count'] > 0:
                hotel['reviews_count'] = google_data['reviews_count']
                hotel['google_rating'] = google_data['google_rating']
                hotel['google_price_level'] = google_data['google_price_level']
                if google_data['phone']:
                    hotel['phone'] = google_data['phone']
                
                print(f"✅ {google_data['reviews_count']} reviews")
                enriched_count += 1
            else:
                print("❌ Not found")
                failed_count += 1
            
            time.sleep(0.05)
            
        except Exception as e:
            print(f"❌ Error: {e}")
            failed_count += 1
    
    # Save enriched data
    with open('hotels_andalusia_enriched.json', 'w', encoding='utf-8') as f:
        json.dump(hotels, f, indent=2, ensure_ascii=False)
    
    print(f"\n{'='*60}")
    print(f"✅ Enriched: {enriched_count}")
    print(f"❌ Failed: {failed_count}")
    print(f"💾 Saved to: hotels_andalusia_enriched.json")

if __name__ == "__main__":
    print("Google Places API Enrichment Tool")
    print("="*60)
    
    # Get API key
    api_key = input("Enter your Google Places API key: ")
    if api_key:
        GOOGLE_API_KEY = api_key
    
    # Choose what to enrich
    print("\n1. Enrich Restaurants")
    print("2. Enrich Hotels")
    print("3. Enrich Both")
    
    choice = input("\nChoice (1/2/3): ")
    
    if choice in ['1', '3']:
        enrich_restaurants()
    
    if choice in ['2', '3']:
        enrich_hotels()
    
    print("\n✅ Done!")
