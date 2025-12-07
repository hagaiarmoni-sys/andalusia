"""
GPS-Based Duplicate Cleaner - FINAL VERSION
============================================

Uses GPS coordinates as the PRIMARY duplicate detection method.
This is the most reliable way to find duplicates.

Logic:
1. POIs within 20 meters = Same place = DUPLICATE
2. Unless they have numbers in name (Cave 1 vs Cave 2)
3. Unless they're different types (Entrance vs Museum)
"""

import json
import math
import re
from collections import defaultdict


def haversine_meters(coord1, coord2):
    """Calculate distance between two GPS coordinates in meters"""
    lat1 = coord1.get('latitude', coord1.get('lat'))
    lon1 = coord1.get('longitude', coord1.get('lng', coord1.get('lon')))
    lat2 = coord2.get('latitude', coord2.get('lat'))
    lon2 = coord2.get('longitude', coord2.get('lng', coord2.get('lon')))
    
    if not all([lat1, lon1, lat2, lon2]):
        return float('inf')
    
    try:
        R = 6371000  # Earth radius in meters
        
        lat1_rad = math.radians(float(lat1))
        lat2_rad = math.radians(float(lat2))
        dlat = math.radians(float(lat2) - float(lat1))
        dlon = math.radians(float(lon2) - float(lon1))
        
        a = (math.sin(dlat/2)**2 + 
             math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        return R * c
    except:
        return float('inf')


def extract_numbers(name):
    """Extract all numbers from a name"""
    if not name:
        return []
    return re.findall(r'\d+', name)


def are_numbered_variations(name1, name2):
    """
    Check if two names are numbered variations of same thing.
    E.g., "Cave 1" and "Cave 2" or "Entrance A" and "Entrance B"
    """
    # Get numbers from both names
    nums1 = extract_numbers(name1)
    nums2 = extract_numbers(name2)
    
    # If both have numbers and they're different, likely variants
    if nums1 and nums2 and nums1 != nums2:
        # Remove numbers and compare base names
        base1 = re.sub(r'\d+', '', name1).strip()
        base2 = re.sub(r'\d+', '', name2).strip()
        
        # If base names are very similar, they're numbered variants
        if base1.lower() == base2.lower():
            return True
    
    return False


def are_different_types(name1, name2):
    """
    Check if POIs are different types (entrance vs museum, tower vs church)
    """
    type_keywords = {
        'entrance': ['entrada', 'entrance', 'gate', 'puerta'],
        'museum': ['museo', 'museum'],
        'tower': ['torre', 'tower'],
        'church': ['iglesia', 'church', 'cathedral', 'catedral'],
        'palace': ['palacio', 'palace', 'alcazar', 'alcázar'],
        'garden': ['jardin', 'jardín', 'garden'],
        'square': ['plaza', 'square'],
        'viewpoint': ['mirador', 'viewpoint'],
    }
    
    name1_lower = name1.lower()
    name2_lower = name2.lower()
    
    # Find types
    type1 = None
    type2 = None
    
    for type_name, keywords in type_keywords.items():
        for keyword in keywords:
            if keyword in name1_lower:
                type1 = type_name
            if keyword in name2_lower:
                type2 = type_name
    
    # If both have types and they're different, they're different things
    if type1 and type2 and type1 != type2:
        return True
    
    return False


def are_different_people_monuments(name1, name2):
    """
    Check if these are monuments/plaques to different people.
    E.g., "Placa a Robert Boyd" vs "Placa a John Bevan"
    """
    # Keywords indicating person-specific monuments
    person_keywords = ['placa a ', 'monumento a ', 'busto de ', 'estatua de ']
    
    name1_lower = name1.lower()
    name2_lower = name2.lower()
    
    # Check if both are person monuments
    is_person1 = any(kw in name1_lower for kw in person_keywords)
    is_person2 = any(kw in name2_lower for kw in person_keywords)
    
    if is_person1 and is_person2:
        # Extract the person name (everything after the keyword)
        for kw in person_keywords:
            if kw in name1_lower:
                person1 = name1_lower.split(kw)[1].strip()
            if kw in name2_lower:
                person2 = name2_lower.split(kw)[1].strip()
        
        # If person names are different, these are different monuments
        if person1 != person2:
            return True, f"Different people: '{person1}' vs '{person2}'"
    
    return False, None


def are_different_parts(name1, name2):
    """
    Check if these are different parts of same complex.
    E.g., "Patio de la Capilla" vs "Patio de la Cancela"
    """
    part_keywords = [
        'patio ', 'torre ', 'sala ', 'jardín ', 'jardin ', 'garden ',
        'puerta ', 'entrance ', 'entrada ', 'fuente ', 'fountain ',
        'panteón ', 'panteon ', 'capilla ', 'chapel '
    ]
    
    name1_lower = name1.lower()
    name2_lower = name2.lower()
    
    # Check if both have same part type
    for keyword in part_keywords:
        if keyword in name1_lower and keyword in name2_lower:
            # Extract the specific part name (what comes after the keyword)
            parts1 = name1_lower.split(keyword)
            parts2 = name2_lower.split(keyword)
            
            if len(parts1) > 1 and len(parts2) > 1:
                part1 = parts1[1].strip()
                part2 = parts2[1].strip()
                
                # If different specific parts, they're different
                if part1 and part2 and part1 != part2:
                    return True, f"Different {keyword.strip()}s: '{part1}' vs '{part2}'"
    
    # Check for torre vs patio, fuente vs patio (different types with same name)
    type_pairs = [
        ('torre ', 'patio '),
        ('fuente ', 'patio '),
        ('jardín ', 'mercado '),
        ('garden ', 'market '),
    ]
    
    for type1, type2 in type_pairs:
        if (type1 in name1_lower and type2 in name2_lower) or (type2 in name1_lower and type1 in name2_lower):
            return True, f"Different types: {type1.strip()} vs {type2.strip()}"
    
    return False, None


def should_keep_both(poi1, poi2, distance):
    """
    Decide if both POIs should be kept despite being close.
    Returns: (keep_both: bool, reason: str)
    """
    name1 = poi1.get('name', '')
    name2 = poi2.get('name', '')
    
    # Rule 1: Numbered variations (Cave 1 vs Cave 2)
    if are_numbered_variations(name1, name2):
        return True, f"Numbered variations: '{name1}' vs '{name2}'"
    
    # Rule 2: Different types (Entrance vs Museum)
    if are_different_types(name1, name2):
        return True, f"Different types: '{name1}' vs '{name2}'"
    
    # Rule 3: Different people monuments
    is_diff_people, reason = are_different_people_monuments(name1, name2)
    if is_diff_people:
        return True, reason
    
    # Rule 4: Different parts of same complex
    is_diff_parts, reason = are_different_parts(name1, name2)
    if is_diff_parts:
        return True, reason
    
    # Rule 5: Very far apart (>50m) despite being "close"
    if distance > 50:
        return True, f"Far apart ({distance:.0f}m)"
    
    return False, None


def normalize_name_simple(name):
    """Simple normalization for comparison"""
    if not name:
        return ""
    
    name = name.lower().strip()
    
    # Remove common articles
    for article in ['la ', 'el ', 'the ', 'los ', 'las ', 'de ', 'del ']:
        name = name.replace(article, ' ')
    
    # Remove punctuation
    name = name.rstrip('.,;:')
    
    return ' '.join(name.split())


def find_gps_duplicates(attractions):
    """Find duplicates using GPS proximity"""
    
    # Group by city
    by_city = defaultdict(list)
    for attr in attractions:
        city = attr.get('city', 'Unknown')
        if city:
            by_city[city].append(attr)
    
    duplicates = []
    
    print("\n🔍 Scanning for GPS-based duplicates...\n")
    
    for city, city_attrs in by_city.items():
        city_dupes = 0
        
        # Check each pair
        for i, poi1 in enumerate(city_attrs):
            for poi2 in city_attrs[i+1:]:
                
                coords1 = poi1.get('coordinates', {})
                coords2 = poi2.get('coordinates', {})
                
                distance = haversine_meters(coords1, coords2)
                
                # If within 20 meters, check if duplicate
                if distance <= 20:
                    
                    # Check if we should keep both anyway
                    keep_both, reason = should_keep_both(poi1, poi2, distance)
                    
                    if keep_both:
                        # Not a duplicate, skip
                        continue
                    
                    # Compare names to confirm
                    name1_norm = normalize_name_simple(poi1.get('name', ''))
                    name2_norm = normalize_name_simple(poi2.get('name', ''))
                    
                    # If names are completely different, might not be duplicate
                    if name1_norm and name2_norm:
                        # Check similarity
                        words1 = set(name1_norm.split())
                        words2 = set(name2_norm.split())
                        
                        if words1 and words2:
                            # Jaccard similarity
                            intersection = words1 & words2
                            union = words1 | words2
                            similarity = len(intersection) / len(union)
                            
                            # If less than 30% word overlap, probably different
                            if similarity < 0.3:
                                continue
                    
                    # It's a duplicate!
                    duplicates.append({
                        'city': city,
                        'poi1': poi1,
                        'poi2': poi2,
                        'distance_m': distance,
                        'name1': poi1.get('name'),
                        'name2': poi2.get('name')
                    })
                    
                    city_dupes += 1
        
        if city_dupes > 0:
            print(f"   {city}: Found {city_dupes} duplicate pairs")
    
    return duplicates


def choose_best_poi(dup):
    """Choose which POI to keep"""
    poi1 = dup['poi1']
    poi2 = dup['poi2']
    
    score1 = 0
    score2 = 0
    
    # 1. Prefer POI with rating
    rating1 = poi1.get('rating')
    rating2 = poi2.get('rating')
    
    if rating1 and not rating2:
        score1 += 3
    elif rating2 and not rating1:
        score2 += 3
    elif rating1 and rating2:
        if rating1 > rating2:
            score1 += 2
        elif rating2 > rating1:
            score2 += 2
    
    # 2. Prefer POI with description
    if poi1.get('description'):
        score1 += 2
    if poi2.get('description'):
        score2 += 2
    
    # 3. Prefer POI with more complete data
    fields1 = sum(1 for v in poi1.values() if v)
    fields2 = sum(1 for v in poi2.values() if v)
    
    if fields1 > fields2:
        score1 += 1
    elif fields2 > fields1:
        score2 += 1
    
    # 4. Prefer shorter, cleaner name (usually better)
    name1_len = len(poi1.get('name', ''))
    name2_len = len(poi2.get('name', ''))
    
    if name1_len > 0 and name2_len > 0:
        if name1_len < name2_len:
            score1 += 1
        elif name2_len < name1_len:
            score2 += 1
    
    return 'poi1' if score1 >= score2 else 'poi2'


def clean_gps_duplicates(input_file, output_file):
    """Clean duplicates using GPS"""
    
    print("=" * 80)
    print("GPS-BASED DUPLICATE CLEANER")
    print("=" * 80)
    
    # Load
    print(f"\n📂 Loading: {input_file}")
    with open(input_file, 'r', encoding='utf-8') as f:
        attractions = json.load(f)
    
    print(f"✅ Loaded {len(attractions)} attractions")
    
    # Find duplicates
    duplicates = find_gps_duplicates(attractions)
    
    if not duplicates:
        print("\n✅ No GPS-based duplicates found! Data is clean.")
        return
    
    print(f"\n⚠️  Found {len(duplicates)} duplicate pairs")
    
    # Show duplicates
    print("\n📋 Duplicate pairs:\n")
    for i, dup in enumerate(duplicates[:50], 1):  # Show first 50
        print(f"{i}. {dup['city']} ({dup['distance_m']:.1f}m apart):")
        print(f"   • {dup['name1']}")
        print(f"   • {dup['name2']}")
        
        # Show which will be kept
        keep = choose_best_poi(dup)
        keep_name = dup['name1'] if keep == 'poi1' else dup['name2']
        remove_name = dup['name2'] if keep == 'poi1' else dup['name1']
        print(f"   → Will keep: {keep_name}")
        print()
    
    if len(duplicates) > 50:
        print(f"   ... and {len(duplicates) - 50} more pairs\n")
    
    # Confirm
    response = input(f"\nRemove {len(duplicates)} duplicates? (y/n): ")
    
    if response.lower() != 'y':
        print("Cancelled.")
        return
    
    # Remove duplicates
    print("\n🧹 Removing duplicates...")
    
    ids_to_remove = set()
    
    for dup in duplicates:
        keep = choose_best_poi(dup)
        remove = dup['poi2'] if keep == 'poi1' else dup['poi1']
        
        # Create unique ID
        remove_id = (
            remove.get('name'),
            remove.get('city'),
            str(remove.get('coordinates'))
        )
        ids_to_remove.add(remove_id)
    
    # Filter
    cleaned = []
    for attr in attractions:
        attr_id = (
            attr.get('name'),
            attr.get('city'),
            str(attr.get('coordinates'))
        )
        if attr_id not in ids_to_remove:
            cleaned.append(attr)
    
    print(f"\n📊 Results:")
    print(f"   Original: {len(attractions)}")
    print(f"   Removed: {len(ids_to_remove)}")
    print(f"   Cleaned: {len(cleaned)}")
    
    # Save
    print(f"\n💾 Saving to: {output_file}")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(cleaned, f, indent=2, ensure_ascii=False)
    
    print("\n✅ Done!")
    print("\n" + "=" * 80)


if __name__ == "__main__":
    INPUT_FILE = "andalusia_attractions_filtered.json"
    OUTPUT_FILE = "andalusia_attractions_deduplicated.json"
    
    try:
        clean_gps_duplicates(INPUT_FILE, OUTPUT_FILE)
    except FileNotFoundError:
        print(f"❌ Error: Could not find '{INPUT_FILE}'")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
