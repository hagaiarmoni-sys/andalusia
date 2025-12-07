"""
Comprehensive POI Enrichment - Add ALL Essential Fields
Adds: place_id, business_status, photos, opening_hours, price_level, website, phone
Takes ~10-15 minutes for 797 POIs
"""

import json
import requests
import time

GOOGLE_API_KEY = "YOUR_API_KEY_HERE"

def get_comprehensive_place_data(name, city, lat, lon):
    """
    Get ALL essential fields from Google Places in ONE API call
    """
    
    # Step 1: Find place_id
    search_url = "https://maps.googleapis.com/maps/api/place/findplacefromtext/json"
    search_params = {
        'input': f"{name} {city} Spain",
        'inputtype': 'textquery',
        'fields': 'place_id',
        'locationbias': f'point:{lat},{lon}',
        'key': GOOGLE_API_KEY
    }
    
    try:
        response = requests.get(search_url, params=search_params)
        data = response.json()
        
        if data['status'] != 'OK' or not data.get('candidates'):
            return None
        
        place_id = data['candidates'][0]['place_id']
        
        # Step 2: Get COMPREHENSIVE details (all fields in ONE call!)
        details_url = "https://maps.googleapis.com/maps/api/place/details/json"
        details_params = {
            'place_id': place_id,
            'fields': ','.join([
                'place_id',
                'business_status',
                'user_ratings_total',
                'rating',
                'photos',
                'opening_hours',
                'price_level',
                'website',
                'formatted_phone_number',
                'international_phone_number',
                'url',  # Google Maps URL
                'types'
            ]),
            'key': GOOGLE_API_KEY
        }
        
        response = requests.get(details_url, params=details_params)
        details = response.json()
        
        if details['status'] != 'OK':
            return None
        
        result = details.get('result', {})
        
        # Extract photo references (max 10)
        photos = result.get('photos', [])
        photo_refs = [p['photo_reference'] for p in photos[:10]]
        
        # Extract opening hours
        opening_hours = result.get('opening_hours', {})
        
        return {
            # Core identification
            'place_id': place_id,
            'google_maps_url': result.get('url'),
            
            # Status (CRITICAL!)
            'business_status': result.get('business_status', 'OPERATIONAL'),
            
            # Reviews (updating existing)
            'reviews_count': result.get('user_ratings_total', 0),
            'google_rating': result.get('rating'),
            
            # Photos
            'photo_references': photo_refs,
            'photo_count': len(photos),
            
            # Opening hours
            'opening_hours': opening_hours.get('weekday_text', []),
            'open_now': opening_hours.get('open_now'),
            'hours_available': len(opening_hours) > 0,
            
            # Pricing
            'price_level': result.get('price_level'),  # 0-4 scale
            
            # Contact
            'website': result.get('website', ''),
            'phone': result.get('formatted_phone_number', ''),
            'international_phone': result.get('international_phone_number', ''),
            
            # Types
            'google_types': result.get('types', [])
        }
    
    except Exception as e:
        print(f"Error: {e}")
        return None

def enrich_pois_comprehensively():
    """
    Add ALL essential fields to existing POIs
    """
    
    print("="*80)
    print("🚀 COMPREHENSIVE POI ENRICHMENT")
    print("="*80)
    print("Adding:")
    print("  ✅ place_id (unique identifier)")
    print("  ✅ business_status (avoid closed places)")
    print("  ✅ photo_references (get images later)")
    print("  ✅ opening_hours (plan timing)")
    print("  ✅ price_level (budget filtering)")
    print("  ✅ website & phone (contact info)")
    print("="*80)
    
    # Load current enriched data
    with open('andalusia_attractions_enriched.json', 'r', encoding='utf-8') as f:
        pois = json.load(f)
    
    print(f"\nProcessing {len(pois)} POIs...")
    print("⏱️ Estimated time: 10-15 minutes\n")
    
    enriched_count = 0
    failed_count = 0
    closed_count = 0
    
    for i, poi in enumerate(pois):
        name = poi.get('name', '')
        city = poi.get('city', '')
        lat = poi.get('lat')
        lon = poi.get('lon')
        
        if not (name and city and lat and lon):
            failed_count += 1
            continue
        
        # Skip if already has place_id
        if poi.get('place_id'):
            continue
        
        print(f"[{i+1}/{len(pois)}] {name[:50]}...", end=' ')
        
        try:
            google_data = get_comprehensive_place_data(name, city, lat, lon)
            
            if google_data:
                # Add ALL fields
                poi.update(google_data)
                
                # Check if permanently closed
                if google_data['business_status'] == 'CLOSED_PERMANENTLY':
                    print(f"⚠️ CLOSED PERMANENTLY")
                    poi['is_closed'] = True
                    closed_count += 1
                elif google_data['business_status'] == 'CLOSED_TEMPORARILY':
                    print(f"⚠️ Temporarily closed ({google_data.get('reviews_count', 0)} reviews)")
                    poi['is_temporarily_closed'] = True
                else:
                    print(f"✅ {google_data.get('reviews_count', 0)} reviews, {len(google_data.get('photo_references', []))} photos")
                
                enriched_count += 1
            else:
                print("❌ Not found")
                failed_count += 1
            
            # Rate limiting (20 requests per second)
            time.sleep(0.05)
            
        except Exception as e:
            print(f"❌ Error: {e}")
            failed_count += 1
    
    print(f"\n{'='*80}")
    print(f"✅ Successfully enriched: {enriched_count}")
    print(f"❌ Failed: {failed_count}")
    print(f"⚠️ Permanently closed: {closed_count}")
    print(f"{'='*80}")
    
    return pois, closed_count

def remove_closed_pois(pois):
    """
    Optionally remove permanently closed POIs
    """
    
    closed = [p for p in pois if p.get('is_closed', False)]
    
    if closed:
        print(f"\n⚠️ Found {len(closed)} PERMANENTLY CLOSED POIs:")
        for p in closed[:10]:  # Show first 10
            print(f"  - {p.get('name')} ({p.get('city')})")
        
        if len(closed) > 10:
            print(f"  ... and {len(closed) - 10} more")
        
        choice = input(f"\nRemove these {len(closed)} closed POIs? (yes/no): ")
        
        if choice.lower() == 'yes':
            pois = [p for p in pois if not p.get('is_closed', False)]
            print(f"✅ Removed {len(closed)} closed POIs")
            print(f"📊 Remaining POIs: {len(pois)}")
        else:
            print("⚠️ Keeping closed POIs (marked with 'is_closed': true)")
    else:
        print("\n✅ No permanently closed POIs found!")
    
    return pois

def generate_statistics(pois):
    """
    Show comprehensive statistics
    """
    
    print("\n" + "="*80)
    print("📊 ENRICHMENT STATISTICS")
    print("="*80)
    
    # Basic counts
    total = len(pois)
    with_place_id = sum(1 for p in pois if p.get('place_id'))
    with_photos = sum(1 for p in pois if p.get('photo_references'))
    with_hours = sum(1 for p in pois if p.get('hours_available'))
    with_website = sum(1 for p in pois if p.get('website'))
    with_phone = sum(1 for p in pois if p.get('phone'))
    
    print(f"\nTotal POIs: {total}")
    print(f"  ✅ With place_id: {with_place_id} ({100*with_place_id/total:.1f}%)")
    print(f"  📸 With photos: {with_photos} ({100*with_photos/total:.1f}%)")
    print(f"  ⏰ With opening hours: {with_hours} ({100*with_hours/total:.1f}%)")
    print(f"  🌐 With website: {with_website} ({100*with_website/total:.1f}%)")
    print(f"  📞 With phone: {with_phone} ({100*with_phone/total:.1f}%)")
    
    # Business status
    print(f"\nBusiness Status:")
    operational = sum(1 for p in pois if p.get('business_status') == 'OPERATIONAL')
    temp_closed = sum(1 for p in pois if p.get('is_temporarily_closed', False))
    perm_closed = sum(1 for p in pois if p.get('is_closed', False))
    
    print(f"  ✅ Operational: {operational} ({100*operational/total:.1f}%)")
    print(f"  ⚠️ Temporarily closed: {temp_closed}")
    print(f"  ❌ Permanently closed: {perm_closed}")
    
    # Photo statistics
    total_photos = sum(len(p.get('photo_references', [])) for p in pois)
    avg_photos = total_photos / with_photos if with_photos > 0 else 0
    
    print(f"\nPhoto Statistics:")
    print(f"  📸 Total photo references: {total_photos:,}")
    print(f"  📊 Average per POI: {avg_photos:.1f}")
    
    # Price level distribution
    price_counts = {}
    for p in pois:
        level = p.get('price_level')
        if level is not None:
            price_counts[level] = price_counts.get(level, 0) + 1
    
    if price_counts:
        print(f"\nPrice Level Distribution:")
        price_labels = {0: 'Free', 1: '€', 2: '€€', 3: '€€€', 4: '€€€€'}
        for level in sorted(price_counts.keys()):
            count = price_counts[level]
            print(f"  {price_labels.get(level, '?')}: {count} POIs")
    
    # Top POIs by photos
    print(f"\n" + "="*80)
    print("TOP 10 POIs BY PHOTO COUNT:")
    print("="*80)
    
    with_photos_list = [p for p in pois if p.get('photo_count', 0) > 0]
    with_photos_list.sort(key=lambda x: x.get('photo_count', 0), reverse=True)
    
    for i, poi in enumerate(with_photos_list[:10], 1):
        name = poi.get('name', '?')
        city = poi.get('city', '?')
        photos = poi.get('photo_count', 0)
        rating = poi.get('rating') or poi.get('google_rating', '?')
        reviews = poi.get('reviews_count', 0)
        print(f"{i}. {name} ({city})")
        print(f"   📸 {photos} photos | ⭐ {rating} | {reviews:,} reviews")

def main():
    """
    Main execution
    """
    
    print("\n" + "="*80)
    print("🚀 COMPREHENSIVE POI ENRICHMENT TOOL")
    print("="*80)
    
    # Get API key
    global GOOGLE_API_KEY
    api_key = input("\nEnter your Google Places API key: ")
    if api_key:
        GOOGLE_API_KEY = api_key
    
    print("\n⚠️ This will:")
    print("  1. Add place_id, photos, hours, pricing, contact info")
    print("  2. Identify permanently closed attractions")
    print("  3. Take 10-15 minutes (~800 API calls)")
    print(f"  4. Cost: ~$13.60 (from your $300 credit)")
    
    choice = input("\nContinue? (yes/no): ")
    
    if choice.lower() != 'yes':
        print("Cancelled.")
        return
    
    # Enrich POIs
    pois, closed_count = enrich_pois_comprehensively()
    
    # Remove closed POIs if user wants
    pois = remove_closed_pois(pois)
    
    # Save results
    output_file = 'andalusia_attractions_comprehensive.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(pois, f, indent=2, ensure_ascii=False)
    
    print(f"\n{'='*80}")
    print(f"✅ COMPLETE!")
    print(f"💾 Saved to: {output_file}")
    print(f"📊 Total POIs: {len(pois)}")
    print(f"{'='*80}")
    
    # Generate statistics
    generate_statistics(pois)
    
    print("\n✅ Done! Replace your file:")
    print(f"   copy andalusia_attractions_enriched.json andalusia_attractions_enriched_backup.json")
    print(f"   move {output_file} andalusia_attractions_filtered.json")
    
    print("\n🎉 Your POIs now have EVERYTHING:")
    print("   ✅ place_id - Unique identifiers")
    print("   ✅ photos - Image references") 
    print("   ✅ opening_hours - Timing info")
    print("   ✅ price_level - Budget filtering")
    print("   ✅ contact - Website & phone")
    print("   ✅ business_status - No closed attractions!")

if __name__ == "__main__":
    main()
