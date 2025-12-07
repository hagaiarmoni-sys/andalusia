"""
Check Missing Coordinates
=========================

Quick script to see how many POIs are missing GPS coordinates.
"""

import json


def check_missing_coordinates(filename):
    """Check how many POIs are missing coordinates"""
    
    print("=" * 80)
    print(f"CHECKING: {filename}")
    print("=" * 80)
    
    # Load
    with open(filename, 'r', encoding='utf-8') as f:
        attractions = json.load(f)
    
    print(f"\n✅ Total attractions: {len(attractions)}")
    
    # Check coordinates
    missing = []
    invalid = []
    valid = []
    
    for poi in attractions:
        coords = poi.get('coordinates', {})
        
        if not coords:
            missing.append(poi)
            continue
        
        lat = coords.get('latitude', coords.get('lat'))
        lon = coords.get('longitude', coords.get('lng', coords.get('lon')))
        
        if not lat or not lon:
            missing.append(poi)
            continue
        
        try:
            lat_f = float(lat)
            lon_f = float(lon)
            
            # Andalusia bounds: 35-39°N, 8-1°W
            if 35.0 <= lat_f <= 39.0 and -8.0 <= lon_f <= -1.0:
                valid.append(poi)
            else:
                invalid.append(poi)
        except:
            invalid.append(poi)
    
    # Results
    print("\n📊 RESULTS:")
    print(f"   ✅ Valid coordinates: {len(valid)} ({len(valid)/len(attractions)*100:.1f}%)")
    print(f"   ❌ Missing coordinates: {len(missing)} ({len(missing)/len(attractions)*100:.1f}%)")
    print(f"   ⚠️  Invalid coordinates: {len(invalid)} ({len(invalid)/len(attractions)*100:.1f}%)")
    
    # Group by city
    if missing:
        print("\n📍 Missing coordinates by city:")
        by_city = {}
        for poi in missing:
            city = poi.get('city', 'Unknown')
            if city not in by_city:
                by_city[city] = []
            by_city[city].append(poi)
        
        # Sort by count
        sorted_cities = sorted(by_city.items(), key=lambda x: len(x[1]), reverse=True)
        
        for city, pois in sorted_cities[:10]:
            print(f"   • {city}: {len(pois)} POIs")
        
        if len(sorted_cities) > 10:
            remaining = sum(len(pois) for city, pois in sorted_cities[10:])
            print(f"   • Other cities: {remaining} POIs")
        
        # Show samples
        print("\n📋 Sample POIs missing coordinates:")
        for poi in missing[:15]:
            print(f"   • {poi.get('name')} in {poi.get('city')}")
        
        if len(missing) > 15:
            print(f"   ... and {len(missing) - 15} more")
    
    if invalid:
        print("\n⚠️  Sample invalid coordinates:")
        for poi in invalid[:10]:
            coords = poi.get('coordinates', {})
            print(f"   • {poi.get('name')}: {coords}")
    
    print("\n" + "=" * 80)
    
    return len(missing), len(invalid)


if __name__ == "__main__":
    import sys
    
    filename = sys.argv[1] if len(sys.argv) > 1 else "andalusia_attractions_filtered.json"
    
    try:
        check_missing_coordinates(filename)
    except FileNotFoundError:
        print(f"❌ Error: Could not find '{filename}'")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()