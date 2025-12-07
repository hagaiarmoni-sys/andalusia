"""
Google Maps URL Generator for Andalusia Travel App
Generates Google Maps directions URLs with multiple waypoints
"""

from urllib.parse import quote_plus


def generate_daily_map_url(previous_city, current_city, attractions, restaurants):
    """
    Generate Google Maps directions URL with all POIs for the day
    
    Args:
        previous_city: Name of previous city (str or None)
        current_city: Name of current city (str)
        attractions: List of attraction dicts with 'name' and 'coordinates'
        restaurants: List of restaurant dicts (lunch, dinner)
    
    Returns:
        Google Maps URL string
    """
    waypoints = []
    
    # Start from previous city if this is a driving day
    if previous_city and previous_city != current_city:
        waypoints.append(previous_city)
    
    # Add all attractions
    for attr in attractions:
        name = attr.get('name', '')
        coords = attr.get('coordinates', {})
        lat = coords.get('latitude') or coords.get('lat')
        lon = coords.get('longitude') or coords.get('lon') or coords.get('lng')
        
        if lat and lon:
            waypoints.append(f"{lat},{lon}")
        elif name:
            waypoints.append(name)
    
    # Add restaurants
    # ✅ OPTION 3: Use full address from database (includes city = no ambiguity!)
    for restaurant in restaurants:
        if not restaurant:
            continue
        
        address = restaurant.get('address', '')
        
        # Use the full address from your database
        # Your addresses are clean and include city, e.g.:
        # "La Cordobesa, Málaga, Andalusia, Spain"
        # "Calle José Denis Belgrano 25, 29008 Málaga, Spain"
        if address:
            waypoints.append(address)
        else:
            # Fallback: construct from name and city
            name = restaurant.get('name', '')
            city = restaurant.get('city', '')
            if name and city:
                waypoints.append(f"{name}, {city}, Spain")
            elif name:
                waypoints.append(name)
    
    if not waypoints:
        return None
    
    # Build Google Maps URL
    if len(waypoints) == 1:
        # Single destination
        return f"https://www.google.com/maps/dir/?api=1&destination={quote_plus(str(waypoints[0]))}"
    else:
        # Multiple waypoints
        origin = quote_plus(str(waypoints[0]))
        destination = quote_plus(str(waypoints[-1]))
        
        if len(waypoints) > 2:
            # Add intermediate waypoints
            middle_points = waypoints[1:-1]
            waypoints_param = "|".join([quote_plus(str(wp)) for wp in middle_points])
            return f"https://www.google.com/maps/dir/?api=1&origin={origin}&destination={destination}&waypoints={waypoints_param}"
        else:
            return f"https://www.google.com/maps/dir/?api=1&origin={origin}&destination={destination}"
