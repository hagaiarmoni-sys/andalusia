"""
Quick analysis of your enriched POI data
"""

import json

# Load the enriched data
with open('andalusia_attractions_enriched.json', 'r', encoding='utf-8') as f:
    pois = json.load(f)

print("="*80)
print("📊 POI ENRICHMENT RESULTS")
print("="*80)

# Total count
print(f"\nTotal POIs: {len(pois)}")

# With review counts
with_reviews = sum(1 for p in pois if (p.get('reviews_count') or 0) > 0)
print(f"POIs with review counts: {with_reviews} ({100*with_reviews/len(pois):.1f}%)")

# High quality (4.5+, 500+)
high_quality = sum(1 for p in pois if (p.get('reviews_count') or 0) >= 500 and (p.get('rating') or 0) >= 4.5)
print(f"High-quality POIs (4.5+, 500+ reviews): {high_quality} ({100*high_quality/len(pois):.1f}%)")

# With place_id
with_place_id = sum(1 for p in pois if p.get('place_id'))
print(f"POIs with place_id: {with_place_id} ({100*with_place_id/len(pois):.1f}%)")

# By city
print("\n" + "="*80)
print("POIs BY CITY:")
print("="*80)
city_counts = {}
for p in pois:
    city = p.get('city', 'Unknown')
    city_counts[city] = city_counts.get(city, 0) + 1

for city, count in sorted(city_counts.items(), key=lambda x: x[1], reverse=True)[:15]:
    print(f"  {city}: {count}")

# Top rated POIs with lots of reviews
print("\n" + "="*80)
print("TOP 10 HIGHEST-RATED POIs (with 1000+ reviews):")
print("="*80)

top_rated = [p for p in pois if (p.get('reviews_count') or 0) >= 1000]
top_rated.sort(key=lambda x: (x.get('rating') or 0), reverse=True)

for i, poi in enumerate(top_rated[:10], 1):
    name = poi.get('name', '?')
    city = poi.get('city', '?')
    rating = poi.get('rating') or poi.get('google_rating', '?')
    reviews = poi.get('reviews_count', '?')
    print(f"{i}. {name} ({city}) - ⭐ {rating} ({reviews:,} reviews)")

# New discoveries
print("\n" + "="*80)
print("NEW DISCOVERIES (from Google Places):")
print("="*80)

new_pois = [p for p in pois if p.get('source') == 'Google Places Discovery']
print(f"Total new POIs: {len(new_pois)}")

if new_pois:
    print("\nSample new discoveries:")
    for i, poi in enumerate(new_pois[:10], 1):
        name = poi.get('name', '?')
        city = poi.get('city', '?')
        rating = poi.get('rating', '?')
        reviews = poi.get('reviews_count', '?')
        print(f"{i}. {name} ({city}) - ⭐ {rating} ({reviews:,} reviews)")

print("\n" + "="*80)
print("✅ Analysis Complete!")
print("="*80)
