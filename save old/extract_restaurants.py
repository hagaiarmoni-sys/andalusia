import json

# Load your attractions
with open("data/andalusia_attractions_enriched.json", "r", encoding="utf-8") as f:
    all_data = json.load(f)

# Separate into attractions and restaurants
tourist_attractions = []
restaurants = []
hotels_venues = []
shops = []
bars = []

ATTRACTION_CATEGORIES = {
    'Museum', 'Historical', 'Religious', 'Architecture', 
    'Attraction', 'Park/Garden', 'Nature', 'Archaeological',
    'Viewpoints', 'Gardens', 'Neighborhoods', 'Entertainment',
    'Viewpoint', 'Palace', 'Cave', 'Market'
}

def extract_cuisine(item):
    """Extract cuisine from tags"""
    tags = item.get('tags', [])
    
    # If tags is a list, look for cuisine-related keywords
    if isinstance(tags, list):
        cuisine_keywords = ['spanish', 'tapas', 'mediterranean', 'andalusian', 
                          'seafood', 'traditional', 'regional']
        for tag in tags:
            if isinstance(tag, str):
                tag_lower = tag.lower()
                if any(keyword in tag_lower for keyword in cuisine_keywords):
                    return tag.title()
        return 'Spanish'
    
    # If tags is a dict
    elif isinstance(tags, dict):
        return tags.get('cuisine', 'Spanish')
    
    return 'Spanish'

def estimate_price_range(item):
    """Estimate price range from rating or other data"""
    rating = item.get('rating', 0)
    name = (item.get('name') or '').lower()
    
    # If name suggests fine dining
    if any(word in name for word in ['michelin', 'gourmet', 'starred', 'palace', 'royal']):
        return '$$$$'
    
    # If high rating, probably mid-to-high range
    if rating and rating >= 8.5:
        return '$$$'
    elif rating and rating >= 7.0:
        return '$$'
    else:
        return '$$'  # Default mid-range

for item in all_data:
    category = item.get('category', '')
    name = item.get('name')
    
    # Skip items without names
    if not name or name == 'None':
        continue
    
    if category in ATTRACTION_CATEGORIES:
        tourist_attractions.append(item)
    
    elif category == 'Restaurant':
        # Convert to restaurant format
        restaurant = {
            'name': name,
            'city': item.get('city'),
            'cuisine': extract_cuisine(item),
            'rating': item.get('rating'),
            'price_range': estimate_price_range(item),
            'description': item.get('description', f"Local restaurant in {item.get('city', 'Andalusia')}"),
            'address': item.get('address', ''),
            'coordinates': item.get('coordinates'),
            'tags': item.get('tags', [])
        }
        restaurants.append(restaurant)
    
    elif category == 'Bar/Nightlife':
        bars.append(item)
    
    elif category == 'Hotel':
        hotels_venues.append(item)
    
    elif category == 'Shopping':
        shops.append(item)

print(f"\n{'='*60}")
print(f"{'DATA SEPARATION RESULTS':^60}")
print(f"{'='*60}")
print(f"✅ Tourist Attractions: {len(tourist_attractions):>6,}")
print(f"🍽️  Restaurants:         {len(restaurants):>6,}")
print(f"🍺 Bars/Nightlife:      {len(bars):>6,}")
print(f"🏨 Hotels (venues):     {len(hotels_venues):>6,}")
print(f"🛍️  Shopping:            {len(shops):>6,}")
print(f"{'-'*60}")
print(f"📊 Total original:      {len(all_data):>6,}")
print(f"{'='*60}\n")

# Save tourist attractions (cleaned)
with open("data/andalusia_attractions_filtered.json", "w", encoding="utf-8") as f:
    json.dump(tourist_attractions, f, ensure_ascii=False, indent=2)
print(f"✅ Saved {len(tourist_attractions):,} attractions to: data/andalusia_attractions_filtered.json")

# Save restaurants (for lunch/dinner recommendations)
with open("data/restaurants.json", "w", encoding="utf-8") as f:
    json.dump(restaurants, f, ensure_ascii=False, indent=2)
print(f"✅ Saved {len(restaurants):,} restaurants to: data/restaurants.json")

# Optional: Save bars separately (could be used for nightlife recommendations)
with open("data/bars.json", "w", encoding="utf-8") as f:
    json.dump(bars, f, ensure_ascii=False, indent=2)
print(f"✅ Saved {len(bars):,} bars to: data/bars.json")

# Show restaurants per city
print(f"\n{'='*60}")
print(f"{'RESTAURANTS PER CITY':^60}")
print(f"{'='*60}")

city_counts = {}
city_ratings = {}

for r in restaurants:
    city = r.get('city', 'Unknown')
    rating = r.get('rating')
    
    city_counts[city] = city_counts.get(city, 0) + 1
    
    if rating:
        if city not in city_ratings:
            city_ratings[city] = []
        city_ratings[city].append(rating)

# Show top 15 cities with restaurants
sorted_cities = sorted(city_counts.items(), key=lambda x: x[1], reverse=True)[:15]

for city, count in sorted_cities:
    avg_rating = ''
    if city in city_ratings and city_ratings[city]:
        avg = sum(city_ratings[city]) / len(city_ratings[city])
        avg_rating = f"(avg ⭐ {avg:.1f})"
    
    print(f"  {city:<25} {count:>4,} restaurants {avg_rating}")

print(f"{'='*60}\n")

# Show sample restaurants from Seville
print(f"{'='*60}")
print(f"{'SAMPLE: TOP RESTAURANTS IN SEVILLE':^60}")
print(f"{'='*60}")

seville_restaurants = [r for r in restaurants if r.get('city') == 'Seville']
seville_restaurants.sort(key=lambda x: x.get('rating') or 0, reverse=True)

for i, r in enumerate(seville_restaurants[:10], 1):
    rating = r.get('rating')
    rating_str = f"⭐ {rating}" if rating else "No rating"
    cuisine = r.get('cuisine', 'Spanish')
    price = r.get('price_range', '$$')
    
    print(f"{i:2}. {r['name']:<40} {rating_str:<10} {price:<5} {cuisine}")

print(f"{'='*60}\n")

print("🎉 Extraction complete! Your files are ready to use.")
print("\n📋 Next steps:")
print("  1. Update app.py to load filtered attractions file first")
print("  2. Restart your Streamlit app")
print("  3. Generate a new trip - you'll see:")
print("     • Clean tourist attractions (no shops/restaurants)")
print("     • Real restaurant recommendations for lunch/dinner")