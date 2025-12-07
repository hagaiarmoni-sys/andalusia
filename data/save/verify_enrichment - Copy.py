# verify_enrichment.py
import json

print("=" * 70)
print("ENRICHMENT VERIFICATION")
print("=" * 70)

# Load enriched data
with open("andalusia_attractions_enriched.json", "r", encoding="utf-8") as f:
    pois = json.load(f)

# Statistics
total = len(pois)
with_ratings = sum(1 for p in pois if p.get('rating'))
top_attractions = sum(1 for p in pois if p.get('is_top_attraction'))
with_duration = sum(1 for p in pois if p.get('visit_duration_hours'))
with_fee = sum(1 for p in pois if p.get('entrance_fee'))
with_null_names = sum(1 for p in pois if not p.get('name'))

print(f"\nTotal POIs........................ {total:,}")
print(f"With ratings...................... {with_ratings} ({with_ratings/total*100:.1f}%)")
print(f"Top attractions (curated)......... {top_attractions}")
print(f"With visit duration............... {with_duration} ({with_duration/total*100:.1f}%)")
print(f"With entrance fee................. {with_fee} ({with_fee/total*100:.1f}%)")
print(f"With null/missing names........... {with_null_names}")

# Show top rated attractions
print("\n" + "=" * 70)
print("TOP 10 RATED ATTRACTIONS")
print("=" * 70)

rated_pois = [p for p in pois if p.get('rating')]
rated_pois.sort(key=lambda x: x.get('rating', 0), reverse=True)

for i, poi in enumerate(rated_pois[:10], 1):
    # Safe handling of None values
    name = poi.get('name') or 'Unknown'
    city = poi.get('city') or 'Unknown'
    rating = poi.get('rating', 0)
    
    # Truncate after ensuring it's a string
    name = str(name)[:40]
    city = str(city)[:15]
    
    print(f"{i:2}. {name:40} | {city:15} | Rating: {rating}")

# Show cities with most top attractions
print("\n" + "=" * 70)
print("TOP ATTRACTIONS BY CITY")
print("=" * 70)

cities = {}
for poi in pois:
    if poi.get('is_top_attraction'):
        city = poi.get('city') or 'Unknown'
        cities[city] = cities.get(city, 0) + 1

for city, count in sorted(cities.items(), key=lambda x: x[1], reverse=True):
    print(f"{city:20} {count:3} top attractions")

# Check for issues
print("\n" + "=" * 70)
print("DATA QUALITY CHECKS")
print("=" * 70)

issues = []

# Check for null names
null_names = [p for p in pois if not p.get('name')]
if null_names:
    issues.append(f"WARNING: {len(null_names)} POIs with null/missing names")

# Check for missing coordinates
no_coords = []
for p in pois:
    coords = p.get('coordinates')
    if not coords or not coords.get('lat'):
        no_coords.append(p)

if no_coords:
    issues.append(f"WARNING: {len(no_coords)} POIs missing coordinates")

# Check for attractions without cities
no_city = [p for p in pois if not p.get('city')]
if no_city:
    issues.append(f"WARNING: {len(no_city)} POIs missing city")

if issues:
    for issue in issues:
        print(issue)
else:
    print("OK - No data quality issues found!")

print("\n" + "=" * 70)
print("RECOMMENDATIONS")
print("=" * 70)

if with_null_names > 0:
    print(f"1. Clean up {with_null_names} POIs with null names")
    print("   Run: python clean_null_names.py")
else:
    print("1. All POIs have valid names - Good!")

if with_ratings < 100:
    print(f"2. Only {with_ratings} POIs have ratings ({with_ratings/total*100:.1f}%)")
    print(f"   This is expected - top {top_attractions} attractions are curated")
    print(f"   OSM data doesn't include ratings")
else:
    print(f"2. {with_ratings} POIs have ratings - Excellent!")

print(f"3. Update app.py to use 'andalusia_attractions_enriched.json'")
print(f"4. Set min_poi_rating preference to 0.0 (to include OSM POIs without ratings)")

print("\n" + "=" * 70)
print("Enrichment verification complete!")
print("=" * 70)