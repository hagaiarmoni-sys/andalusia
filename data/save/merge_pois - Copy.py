
import json
from datetime import datetime

# ============================================================================
# CONFIGURATION
# ============================================================================

OSM_FILE = "andalusia_attractions_full.json"
TOP_50_FILE = "top_50_attractions.json"
OUTPUT_FILE = "andalusia_attractions_enriched.json"
BACKUP_FILE = f"backup_before_merge_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

# ============================================================================
# LOAD DATA
# ============================================================================

print("=" * 70)
print("MERGING TOP 50 ATTRACTIONS WITH OSM DATA")
print("=" * 70)

# Load OSM data
print(f"\n📖 Loading OSM data from {OSM_FILE}...")
with open(OSM_FILE, "r", encoding="utf-8") as f:
    osm_data = json.load(f)
    
    if isinstance(osm_data, dict) and 'attractions' in osm_data:
        osm_pois = osm_data['attractions']
    else:
        osm_pois = osm_data

print(f"   ✅ Loaded {len(osm_pois)} OSM POIs")

# Create backup
print(f"\n📦 Creating backup: {BACKUP_FILE}")
with open(BACKUP_FILE, "w", encoding="utf-8") as f:
    json.dump(osm_pois, f, indent=2, ensure_ascii=False)

# Load top 50
print(f"\n📖 Loading top 50 attractions from {TOP_50_FILE}...")
with open(TOP_50_FILE, "r", encoding="utf-8") as f:
    top_50 = json.load(f)

print(f"   ✅ Loaded {len(top_50)} curated attractions")

# ============================================================================
# MATCHING FUNCTION
# ============================================================================

def normalize_name(name):
    """Normalize name for fuzzy matching"""
    if not name:
        return ""
    
    # Remove accents and convert to lowercase
    import unicodedata
    nfd = unicodedata.normalize('NFD', name)
    without_accents = ''.join(char for char in nfd if unicodedata.category(char) != 'Mn')
    
    # Remove common words and punctuation
    remove_words = ['de', 'del', 'la', 'el', 'los', 'las']
    words = without_accents.lower().split()
    words = [w for w in words if w not in remove_words]
    
    return ' '.join(words).strip()

def names_match(name1, name2, threshold=0.7):
    """Check if two names are similar enough"""
    norm1 = normalize_name(name1)
    norm2 = normalize_name(name2)
    
    # Exact match after normalization
    if norm1 == norm2:
        return True
    
    # One is substring of other
    if norm1 in norm2 or norm2 in norm1:
        return True
    
    # Calculate similarity (simple word overlap)
    words1 = set(norm1.split())
    words2 = set(norm2.split())
    
    if not words1 or not words2:
        return False
    
    overlap = len(words1 & words2)
    min_words = min(len(words1), len(words2))
    
    similarity = overlap / min_words if min_words > 0 else 0
    
    return similarity >= threshold

def cities_match(city1, city2):
    """Check if cities match"""
    return normalize_name(city1) == normalize_name(city2)

def distance_km(coord1, coord2):
    """Calculate distance between two coordinates"""
    import math
    
    lat1, lon1 = coord1
    lat2, lon2 = coord2
    
    R = 6371.0  # Earth radius in km
    
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return R * c

# ============================================================================
# MERGE LOGIC
# ============================================================================

print("\n" + "=" * 70)
print("MATCHING AND MERGING")
print("=" * 70)

matched_count = 0
unmatched_top50 = []

for top_poi in top_50:
    top_name = top_poi.get('name', '')
    top_city = top_poi.get('city', '')
    top_coords = (top_poi['coordinates']['lat'], top_poi['coordinates']['lon'])
    
    # Try to find matching OSM POI
    best_match = None
    best_score = 0
    
    for osm_poi in osm_pois:
        osm_name = osm_poi.get('name', '')
        osm_city = osm_poi.get('city', '')
        
        # Skip if cities don't match
        if not cities_match(top_city, osm_city):
            continue
        
        # Check name similarity
        if names_match(top_name, osm_name):
            # Calculate distance if coordinates exist
            if osm_poi.get('coordinates'):
                osm_coords = (
                    osm_poi['coordinates'].get('lat'),
                    osm_poi['coordinates'].get('lon')
                )
                
                if osm_coords[0] and osm_coords[1]:
                    dist = distance_km(top_coords, osm_coords)
                    
                    # Must be within 500m to be same place
                    if dist < 0.5:
                        score = 1.0 / (1.0 + dist)  # Closer = higher score
                        
                        if score > best_score:
                            best_score = score
                            best_match = osm_poi
    
    # Merge if match found
    if best_match:
        # Update OSM POI with curated data
        best_match['rating'] = top_poi['rating']
        best_match['visit_duration_hours'] = top_poi['visit_duration_hours']
        best_match['entrance_fee'] = top_poi['entrance_fee']
        best_match['is_top_attraction'] = True
        best_match['curated_description'] = top_poi['description']
        best_match['enriched_at'] = datetime.now().isoformat()
        
        # Keep OSM description if curated one is empty
        if not best_match.get('description'):
            best_match['description'] = top_poi['description']
        
        matched_count += 1
        print(f"✅ Matched: {top_name} ({top_city})")
    else:
        # No match found - add as new POI
        osm_pois.append(top_poi)
        unmatched_top50.append(top_name)
        print(f"➕ Added new: {top_name} ({top_city})")

# ============================================================================
# SAVE RESULTS
# ============================================================================

print("\n" + "=" * 70)
print("SAVING ENRICHED DATA")
print("=" * 70)

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(osm_pois, f, indent=2, ensure_ascii=False)

print(f"\n✅ Saved {len(osm_pois)} POIs to {OUTPUT_FILE}")

# ============================================================================
# STATISTICS
# ============================================================================

enriched_count = sum(1 for p in osm_pois if p.get('rating'))
top_attractions = sum(1 for p in osm_pois if p.get('is_top_attraction'))

print("\n" + "=" * 70)
print("SUMMARY STATISTICS")
print("=" * 70)
print(f"Total POIs in output............ {len(osm_pois)}")
print(f"POIs with ratings............... {enriched_count} ({enriched_count/len(osm_pois)*100:.1f}%)")
print(f"Top attractions................. {top_attractions}")
print(f"Matched from top 50............. {matched_count}/{len(top_50)}")
print(f"Added as new POIs............... {len(unmatched_top50)}")

if unmatched_top50:
    print(f"\n⚠️  These top 50 attractions were not found in OSM data:")
    for name in unmatched_top50[:10]:
        print(f"   - {name}")
    if len(unmatched_top50) > 10:
        print(f"   ... and {len(unmatched_top50) - 10} more")

print("\n" + "=" * 70)
print("✅ MERGE COMPLETE!")
print("=" * 70)
print(f"\nNext steps:")
print(f"1. Review {OUTPUT_FILE}")
print(f"2. Update app.py to use {OUTPUT_FILE}")
print(f"3. Set min_poi_rating preference to 0.0")
print(f"4. Test trip generation!")
