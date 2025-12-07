"""
Car-Based Itinerary Generator for Andalusia Travel App
WITH OPTIMIZED ROUTE ALGORITHM (No Backtracking!)
"""

import streamlit as st
import math
import unicodedata
from collections import Counter
from urllib.parse import quote_plus
from text_norm import canonicalize_city, norm_key  # ✅ NEW: Import text normalization
from semantic_merge import merge_city_pois  # ✅ Import semantic deduplication


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def normalize_city_name(city_name):
    """Normalize city name by removing accents and converting to lowercase"""
    if not city_name:
        return ""
    
    city_name = str(city_name)
    nfd = unicodedata.normalize('NFD', city_name)
    without_accents = ''.join(char for char in nfd if unicodedata.category(char) != 'Mn')
    return without_accents.lower().strip()


def cities_match(city1, city2):
    """
    Check if two city names match (handling accents and aliases)
    FIXED: Removed dangerous partial matching that caused false positives
    """
    if not city1 or not city2:
        return False
    
    norm1 = normalize_city_name(city1)
    norm2 = normalize_city_name(city2)
    
    # Extract just the city name (remove postal codes, country, etc.)
    # "Ronda, 18006 Granada, Spain" → "ronda"
    norm1 = norm1.split(',')[0].strip()
    norm2 = norm2.split(',')[0].strip()
    
    # Exact match
    if norm1 == norm2:
        return True
    
    # City aliases (known variations)
    city_aliases = {
        'seville': {'seville', 'sevilla'},
        'cordoba': {'cordoba', 'cordoba', 'cordoba'},
        'malaga': {'malaga', 'malaga'},
        'cadiz': {'cadiz', 'cadiz'},
        'jerez': {'jerez', 'jerez de la frontera'},
        'granada': {'granada'},
        'ronda': {'ronda'},
        'tarifa': {'tarifa'},
        'almeria': {'almeria', 'almeria'},
        'antequera': {'antequera'},
        'marbella': {'marbella'},
        'nerja': {'nerja'},
        'san pedro': {'san pedro', 'san pedro alcantara'},
        'estepona': {'estepona'}
    }
    
    for canonical, aliases in city_aliases.items():
        if norm1 in aliases and norm2 in aliases:
            return True
    
    # ❌ REMOVED: Dangerous partial matching
    # OLD CODE: if len(norm1) > 3 and len(norm2) > 3 and (norm1 in norm2 or norm2 in norm1):
    # This caused false positives like matching "Ronda" with "Granada"
    
    return False


def parse_start_end(text, trip_type):
    """Parse start and end cities from text input"""
    if not text:
        return None, None
    
    parts = [p.strip() for p in text.split(" to ") if p.strip()]
    
    if len(parts) == 2:
        return parts[0], parts[1]
    
    if trip_type == "Circular":
        return text.strip(), text.strip()
    
    return text.strip(), None


def haversine_km(coord1, coord2, road_factor=1.3):
    """
    Calculate driving distance between two coordinates
    
    Args:
        coord1: Tuple (lat, lon) or coordinate dict
        coord2: Tuple (lat, lon) or coordinate dict
        road_factor: Multiplier for road distance vs straight line
    
    Returns:
        Distance in kilometers
    """
    # Handle different input formats
    if isinstance(coord1, tuple) and isinstance(coord2, tuple):
        lat1, lon1 = coord1
        lat2, lon2 = coord2
    elif isinstance(coord1, dict) and isinstance(coord2, dict):
        lat1 = coord1.get('latitude', coord1.get('lat', 0))
        lon1 = coord1.get('longitude', coord1.get('lng', coord1.get('lon', 0)))
        lat2 = coord2.get('latitude', coord2.get('lat', 0))
        lon2 = coord2.get('longitude', coord2.get('lng', coord2.get('lon', 0)))
    else:
        return None
    
    if not all([lat1, lon1, lat2, lon2]):
        return None
    
    R = 6371  # Earth radius in km
    
    lat1_rad = math.radians(float(lat1))
    lat2_rad = math.radians(float(lat2))
    dlat = math.radians(float(lat2) - float(lat1))
    dlon = math.radians(float(lon2) - float(lon1))
    
    a = (math.sin(dlat / 2) ** 2 + 
         math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    distance = R * c * road_factor
    
    return distance if distance < 10000 else None  # Sanity check


def google_maps_link(cities):
    """Generate Google Maps link for multi-city route"""
    if not cities or len(cities) < 2:
        return ""
    
    origin = cities[0]
    destination = cities[-1]
    waypoints = cities[1:-1] if len(cities) > 2 else []
    
    base_url = "https://www.google.com/maps/dir/"
    
    # Build URL
    parts = [quote_plus(str(origin))]
    for wp in waypoints:
        parts.append(quote_plus(str(wp)))
    parts.append(quote_plus(str(destination)))
    
    return base_url + "/".join(parts)


def filter_duplicate_pois(pois):
    """Remove duplicate POIs based on name similarity"""
    if not pois:
        return []
    
    seen_normalized = set()
    unique = []
    
    # Translation map for common city name variations
    name_translations = {
        'sevilla': 'seville',
        'córdoba': 'cordoba',
        'málaga': 'malaga',
        'cádiz': 'cadiz'
    }
    
    for poi in pois:
        name = poi.get('name', '').lower().strip()
        
        if not name:
            continue
        
        # Normalize name (remove common building type words)
        normalized = name
        
        # Remove common words
        words_to_remove = [
            'cathedral', 'catedral', 'mosque', 'mezquita',
            'church', 'iglesia', 'palace', 'palacio',
            'museum', 'museo', 'of', 'de', 'del', 'la', 'el',
            'the', '-', 'and', 'y'
        ]
        
        for word in words_to_remove:
            normalized = normalized.replace(word, '')
        
        # Remove extra spaces
        normalized = ' '.join(normalized.split())
        
        # Apply translations
        for spanish, english in name_translations.items():
            normalized = normalized.replace(spanish, english)
        
        # Remove all spaces for final comparison
        normalized = normalized.replace(' ', '')
        
        if normalized and normalized not in seen_normalized:
            seen_normalized.add(normalized)
            unique.append(poi)
    
    return unique


def compute_poi_quota(pace, total_pois):
    """Calculate how many POIs to select based on pace"""
    if pace == "relaxed":
        quota = min(5, total_pois)
    elif pace == "fast":
        quota = min(8, total_pois)
    else:  # medium
        quota = min(6, total_pois)
    
    return max(3, min(quota, total_pois))


def apply_diversity(pois, quota, max_same_category):
    """
    Select POIs with category diversity
    Ensures no more than max_same_category of the same type
    """
    if not pois:
        return []
    
    # Sort by rating (handle None values)
    sorted_pois = sorted(pois, key=lambda x: x.get('rating') or 0, reverse=True)
    
    selected = []
    category_count = Counter()
    
    for poi in sorted_pois:
        if len(selected) >= quota:
            break
        
        category = poi.get('category', 'Other')
        
        if category_count[category] < max_same_category:
            selected.append(poi)
            category_count[category] += 1
    
    # If we haven't reached quota, add remaining POIs
    if len(selected) < quota:
        for poi in sorted_pois:
            if poi not in selected and len(selected) < quota:
                selected.append(poi)
    
    return selected


def get_poi_centroid(pois):
    """
    Calculate the geographic center point (centroid) of a list of POIs
    
    Args:
        pois: List of POI dictionaries with coordinates
    
    Returns:
        Tuple (lat, lon) representing the centroid, or None if no valid coordinates
    """
    if not pois:
        return None
    
    valid_coords = []
    for poi in pois:
        coords = poi.get('coordinates', {})
        lat = coords.get('latitude') or coords.get('lat')
        lon = coords.get('longitude') or coords.get('lng') or coords.get('lon')
        
        if lat and lon:
            try:
                valid_coords.append((float(lat), float(lon)))
            except (ValueError, TypeError):
                continue
    
    if not valid_coords:
        return None
    
    avg_lat = sum(c[0] for c in valid_coords) / len(valid_coords)
    avg_lon = sum(c[1] for c in valid_coords) / len(valid_coords)
    
    return (avg_lat, avg_lon)


def filter_nearby_restaurants(restaurants, centroid, max_distance_km=2.5):
    """
    Filter restaurants to only those within a reasonable distance from POI centroid
    This ensures lunch/dinner locations don't require long detours
    
    Args:
        restaurants: List of restaurant dictionaries
        centroid: Tuple (lat, lon) representing the center of POIs
        max_distance_km: Maximum distance in km (default 2.5 km)
    
    Returns:
        List of restaurants within max_distance_km of the centroid
    """
    if not centroid or not restaurants:
        return restaurants
    
    nearby = []
    for restaurant in restaurants:
        coords = restaurant.get('coordinates', {})
        r_lat = coords.get('latitude') or coords.get('lat')
        r_lon = coords.get('longitude') or coords.get('lng') or coords.get('lon')
        
        if r_lat and r_lon:
            try:
                r_coords = (float(r_lat), float(r_lon))
                distance = haversine_km(centroid, r_coords)
                
                if distance is not None and distance <= max_distance_km:
                    # Add distance info for debugging/sorting
                    restaurant['_distance_from_pois'] = distance
                    nearby.append(restaurant)
            except (ValueError, TypeError):
                continue
    
    return nearby


def optimize_poi_order(pois):
    """
    Optimize POI visiting order using nearest-neighbor algorithm
    Returns POIs in geographic order to minimize walking/driving distance
    
    Args:
        pois: List of POI dictionaries with coordinates
    
    Returns:
        List of POIs in optimized visiting order
    """
    if not pois or len(pois) <= 1:
        return pois
    
    # Extract coordinates
    poi_coords = []
    for poi in pois:
        coords = poi.get('coordinates', {})
        lat = coords.get('latitude') or coords.get('lat')
        lon = coords.get('longitude') or coords.get('lng') or coords.get('lon')
        
        if lat and lon:
            try:
                poi_coords.append((float(lat), float(lon), poi))
            except (ValueError, TypeError):
                poi_coords.append((None, None, poi))
        else:
            poi_coords.append((None, None, poi))
    
    # Separate POIs with and without coordinates
    with_coords = [(lat, lon, poi) for lat, lon, poi in poi_coords if lat is not None and lon is not None]
    without_coords = [poi for lat, lon, poi in poi_coords if lat is None or lon is None]
    
    if len(with_coords) <= 1:
        # Not enough POIs with coordinates to optimize
        return pois
    
    # Nearest-neighbor algorithm
    ordered = []
    remaining = with_coords.copy()
    
    # Start with the first POI (highest rated, from apply_diversity)
    current = remaining.pop(0)
    ordered.append(current[2])  # Append the POI (third element of tuple)
    current_coords = (current[0], current[1])
    
    # Greedily select nearest unvisited POI
    while remaining:
        nearest_dist = float('inf')
        nearest_idx = 0
        
        for i, (lat, lon, poi) in enumerate(remaining):
            dist = haversine_km(current_coords, (lat, lon))
            
            if dist is not None and dist < nearest_dist:
                nearest_dist = dist
                nearest_idx = i
        
        # Add nearest POI to ordered list
        nearest = remaining.pop(nearest_idx)
        ordered.append(nearest[2])
        current_coords = (nearest[0], nearest[1])
    
    # Add POIs without coordinates at the end
    ordered.extend(without_coords)
    
    return ordered


# ============================================================================
# OPTIMIZED ROUTE ALGORITHM
# ============================================================================

def optimize_route_andalusia(start_city, end_city, available_cities, centroids, city_name_map, days, parsed_requests, prefs):
    """
    OPTIMIZED ROUTE BUILDER - Supports point-to-point AND circular trips
    
    ✅ FIXED: Handles circular trips (Málaga → Málaga) correctly
    
    Algorithm:
    1. Detect if trip is circular (start == end)
    2. For circular: use 200km fictitious radius, create loop pattern
    3. For point-to-point: use original detour-based logic
    4. Filter cities and build optimal route
    """
    
    # Major cities importance scores
    MAJOR_CITIES = {
        'granada': 100, 'cordoba': 90, 'córdoba': 90,
        'seville': 95, 'sevilla': 95, 'cadiz': 85, 'cádiz': 85,
        'malaga': 80, 'málaga': 80, 'ronda': 70,
        'jerez': 65, 'tarifa': 55, 'marbella': 50,
        'antequera': 45, 'nerja': 40
    }
    
    # Parse user requests
    stay_duration = {}
    for city, duration in parsed_requests.get('stay_duration', {}).items():
        stay_duration[normalize_city_name(city)] = duration
    
    must_see_norms = [normalize_city_name(c) for c in parsed_requests.get('must_see_cities', [])]
    avoid_norms = [normalize_city_name(c) for c in parsed_requests.get('avoid_cities', [])]
    
    # Get coordinates
    start_name = city_name_map.get(start_city, start_city)
    end_name = city_name_map.get(end_city, end_city) if end_city else start_name
    start_coord = centroids.get(start_name)
    
    if not start_coord:
        st.warning(f"⚠️ Missing coordinates for {start_name}")
        return [], []
    
    # ✅ FIX: Handle circular and star/hub trips
    is_circular = (start_city == end_city)
    is_star_hub = prefs.get('trip_type') == 'star' or prefs.get('trip_type') == 'hub'
    
    if is_circular or is_star_hub:
        # For circular and star/hub trips, use a large fictional direct distance
        # This prevents division by zero and allows nearby cities
        # Star/hub trips are limited to 100km radius for day trips
        direct_distance = 200.0  # 200km fictitious radius
        end_coord = start_coord
        if is_star_hub:
            st.info(f"⭐ Planning star/hub trip from {start_name} (sleep in same place every night)")
        else:
            st.info(f"🔄 Planning circular trip from {start_name}")
    else:
        # Normal point-to-point trip
        end_coord = centroids.get(end_name)
        
        if not end_coord:
            st.warning(f"⚠️ Missing coordinates for {end_name}")
            return [], []
        
        direct_distance = haversine_km(start_coord, end_coord)
    
    # Step 1: Filter and score all candidate cities
    candidates = []
    
    for city_norm, pois in available_cities.items():
        # 🚨 NUCLEAR OPTION: Explicitly exclude Fuengirola and other small cities
        # This overrides all other logic to guarantee exclusion
        excluded_cities = ['fuengirola', 'frigiliana', 'mijas']  # Add more as needed
        if any(excluded in city_norm.lower() for excluded in excluded_cities):
            print(f"⛔ HARDCODED EXCLUSION: {city_name_map.get(city_norm, city_norm)} (only {len(pois)} POIs)")
            continue
        
        # Skip if should avoid or is start city
        if city_norm in avoid_norms or city_norm == start_city:
            continue
        
        # For non-circular trips, also skip end city from candidates
        if not is_circular and city_norm == end_city:
            continue
        
        # ✅ CRITICAL FIX: Require 8+ POIs for ALL trip types
        # This excludes Fuengirola (6 POIs) and other small towns
        min_pois = 8
        if len(pois) < min_pois:
            continue
        
        city_name = city_name_map.get(city_norm)
        city_coord = centroids.get(city_name)
        
        if not city_coord:
            continue
        
        # Calculate distances
        dist_start_to_city = haversine_km(start_coord, city_coord)
        dist_city_to_end = haversine_km(city_coord, end_coord)
        total_via_city = dist_start_to_city + dist_city_to_end
        
        # ✅ FIX: Different filtering logic for circular vs point-to-point vs star/hub
        if is_star_hub:
            # For star/hub trips, limit to day-trip distance (max 100km one-way)
            # This allows ~2h round trip drive
            if dist_start_to_city > 100:
                continue
            detour_ratio = 1.0  # Don't filter based on detour
        elif is_circular:
            # For circular trips, include cities within reasonable distance from base
            if dist_start_to_city > 150:  # Max 150km from base city
                continue
            detour_ratio = 1.0  # Don't filter based on detour
        else:
            # Normal detour calculation for point-to-point
            detour_ratio = total_via_city / direct_distance if direct_distance > 0 else 999
            
            # Exclude cities that add >200% to the journey
            if detour_ratio > 3.0 and city_norm not in must_see_norms:
                continue
        
        # Score this city
        poi_score = len(pois) * 2
        importance_score = MAJOR_CITIES.get(city_norm, 20)
        must_see_bonus = 200 if city_norm in must_see_norms else 0
        
        total_score = poi_score + importance_score + must_see_bonus
        
        candidates.append({
            'norm': city_norm,
            'name': city_name,
            'coord': city_coord,
            'score': total_score,
            'pois': len(pois),
            'detour': detour_ratio,
            'dist_from_start': dist_start_to_city
        })
    
    # Sort by score (highest first)
    candidates.sort(key=lambda x: x['score'], reverse=True)
    
    # Step 2: Calculate how many cities to visit
    pace = prefs.get('pace', 'medium')
    
    # ✅ FIX: For circular trips, cities = days (1 city per day)
    # For point-to-point, select cities based on DISTANCE not just days!
    if is_circular or is_star_hub:
        # Circular trip: Don't add start city at end
        # For 7 days: max_cities = 7, route = [start, 6 other cities] = 7 total
        # Last day in final city, evening return to start
        max_cities = min(days, len(candidates) + 1)
    else:
        # ✅ CRITICAL FIX: Point-to-point trips should select cities based on DISTANCE
        # Not on number of days! Málaga → Seville (200km) shouldn't visit 9 cities!
        
        # Calculate how many cities make sense for this distance
        if direct_distance < 150:
            # Short trips (< 150km): 2-3 cities total
            max_cities = min(3, len(candidates) + 1)
        elif direct_distance < 300:
            # Medium trips (150-300km): 3-5 cities total  
            max_cities = min(5, len(candidates) + 1)
        elif direct_distance < 500:
            # Long trips (300-500km): 4-6 cities total
            max_cities = min(6, len(candidates) + 1)
        else:
            # Very long trips (> 500km): 5-7 cities total
            max_cities = min(7, len(candidates) + 1)
        
        # But never exceed the number of days
        max_cities = min(max_cities, days)
    
    # Step 3: Build route greedily
    route = [start_city]
    current_pos = start_coord
    visited = {start_city}
    intermediate_stops = set()
    
    # Select cities to visit
    for _ in range(max_cities - 1):
        if not candidates:
            break
        
        best_city = None
        best_score = -999999
        
        for candidate in candidates:
            if candidate['norm'] in visited:
                continue
            
            dist_current_to_candidate = haversine_km(current_pos, candidate['coord'])
            dist_candidate_to_target = haversine_km(candidate['coord'], end_coord)
            
            # ✅ FIX: Different scoring for circular vs point-to-point
            if is_circular or is_star_hub:
                # For circular trips: create a nice geographic loop
                cities_visited = len(route)
                
                # Distance penalty (don't go too far)
                distance_penalty = dist_current_to_candidate * 2
                
                # Loop bonus: move away from start first, then back
                if cities_visited < max_cities / 2:
                    # First half: prefer cities moving away
                    loop_bonus = candidate['dist_from_start'] * 5
                else:
                    # Second half: prefer cities heading back
                    loop_bonus = (150 - candidate['dist_from_start']) * 5
                
                combined_score = candidate['score'] - distance_penalty + loop_bonus
            else:
                # Normal point-to-point scoring
                progress_to_target = dist_current_to_candidate + dist_candidate_to_target
                distance_penalty = dist_current_to_candidate * 2
                combined_score = candidate['score'] - distance_penalty - (progress_to_target * 0.5)
            
            if combined_score > best_score:
                best_score = combined_score
                best_city = candidate
        
        if best_city:
            route.append(best_city['norm'])
            visited.add(best_city['norm'])
            current_pos = best_city['coord']
            candidates = [c for c in candidates if c['norm'] != best_city['norm']]
    
    # ✅ FIX: Complete the route appropriately
    if is_circular or is_star_hub:
        # For circular and star/hub trips, DON'T add start city again
        # The last day will be in a different city, with evening return to start
        # This is handled in the itinerary display, not in the route
        pass  # No need to append start_city again
    else:
        # For point-to-point, ensure we end at destination
        if route[-1] != end_city:
            route.append(end_city)
    
    return route, intermediate_stops


def generate_simple_trip(start_end_text, days, prefs, trip_type, attractions, hotels, restaurants=None):
    """
    Generate car-based trip itinerary with optimized routing
    
    Args:
        restaurants: Optional list of restaurant data
    
    Returns:
        dict with: itinerary, ordered_cities, hop_kms, maps_link
    """
    
    # ✅ NEW: Build set of known cities from attractions
    known_cities = {(attr.get('city') or '').strip() for attr in attractions}
    known_cities.discard('')
    
    # ✅ NEW: Parse and canonicalize start/end cities
    start_city, end_city = parse_start_end(start_end_text, trip_type)
    
    if not start_city:
        st.error("❌ Please specify a start city")
        return None
    
    # ✅ NEW: Canonicalize city names to match dataset
    start_city_canonical = canonicalize_city(start_city, known_cities)
    
    # Detect trip type for later use
    trip_type_lower = trip_type.lower()
    is_circular = trip_type_lower == 'circular'
    is_star_hub = 'star' in trip_type_lower or 'hub' in trip_type_lower
    
    # For circular and star/hub trips, end city is same as start
    if is_circular or is_star_hub:
        if not end_city or end_city == start_city:
            end_city = start_city
            end_city_canonical = start_city_canonical
        else:
            end_city_canonical = canonicalize_city(end_city, known_cities)
    else:
        end_city_canonical = canonicalize_city(end_city, known_cities) if end_city else None
    
    # ✅ NEW: Better error handling
    if not start_city_canonical:
        cities_list = ', '.join(sorted(known_cities)[:10])
        st.error(f"❌ Start city '{start_city}' not found in data")
        st.info(f"💡 Available cities: {cities_list}")
        return None
    
    if end_city and not end_city_canonical:
        st.error(f"❌ End city '{end_city}' not found in data")
        return None
    
    # ✅ NEW: Use canonical names going forward
    start_city = start_city_canonical
    end_city = end_city_canonical
    
    # Build city coordinates map (centroids)
    centroids = {}
    for attr in attractions:
        city = attr.get('city')
        coords = attr.get('coordinates', {})
        lat = coords.get('latitude') or coords.get('lat')
        lon = coords.get('longitude') or coords.get('lng') or coords.get('lon')
        
        if city and lat and lon:
            if city not in centroids:
                centroids[city] = (float(lat), float(lon))
    
    # Group attractions by city (normalized)
    by_city_normalized = {}
    city_name_map = {}  # normalized -> original
    
    for attr in attractions:
        city = attr.get('city')
        if not city:
            continue
        
        city_norm = normalize_city_name(city)
        
        if city_norm not in city_name_map:
            city_name_map[city_norm] = city
        
        if city_norm not in by_city_normalized:
            by_city_normalized[city_norm] = []
        
        by_city_normalized[city_norm].append(attr)
    
    # Build route using optimized algorithm
    st.info(f"🚗 Planning road trip: {start_city} → {end_city or 'various cities'}")
    
    # Normalize for internal routing
    start_city_norm = normalize_city_name(start_city)
    end_city_norm = normalize_city_name(end_city) if end_city else None
    
    parsed_requests = {
        'stay_duration': {},
        'must_see_cities': [],
        'avoid_cities': []
    }
    
    route, intermediate_stops = optimize_route_andalusia(
        start_city_norm,
        end_city_norm,
        by_city_normalized,
        centroids,
        city_name_map,
        days,
        parsed_requests,
        prefs  # Add prefs parameter
    )
    
    if not route:
        st.error("❌ Could not generate route")
        return None
    
    # Convert to original city names
    ordered_cities = [city_name_map.get(c, c) for c in route]
    
    st.success(f"🗺️ Route: {' → '.join(ordered_cities)}")
    
    # Build day-by-day itinerary
    # Skip intermediate stops when counting days - they're just overnight stops, not full days
    itinerary = []
    pace = prefs.get("pace", "medium")
    max_same_cat = prefs.get("max_same_category_per_day", 2)
    day_counter = 1
    
    for i, city_norm in enumerate(route):
        city_original = city_name_map.get(city_norm, city_norm)
        
        # ✅ CRITICAL FIX: Stop if we've reached the requested number of days
        if day_counter > days:
            print(f"⚠️ Reached {days}-day limit, stopping itinerary generation")
            break
        
        # FIXED: Don't skip intermediate stops - they need a day too!
        # Original logic commented out to ensure correct day count
        #         # Skip intermediate stops - they don't get their own day in the itinerary
        #         # They're just overnight stops and are reflected in the route/distances
        #         if city_norm in intermediate_stops:
        #             continue
        
        city_attrs = by_city_normalized.get(city_norm, [])
        
        # ✅ SMART SEMANTIC MERGE: Only deduplicate large cities
        # Small cities need all their POIs to have enough variety
        if len(city_attrs) > 20:
            # Large cities (Granada, Seville, Málaga) - use deduplication to remove bilingual duplicates
            original_count = len(city_attrs)
            city_attrs = merge_city_pois(city_attrs, city_original)
            print(f"ℹ️ {city_original}: {original_count} → {len(city_attrs)} POIs (after semantic deduplication)")
        else:
            # Small cities - keep all POIs for maximum variety
            print(f"ℹ️ {city_original}: {len(city_attrs)} POIs (semantic merge skipped - small city)")
        
        # ✅ NEW: Filter by minimum rating preference
        min_rating = prefs.get('min_poi_rating', 0.0)
        if min_rating > 0:
            original_count = len(city_attrs)
            city_attrs = [poi for poi in city_attrs if (poi.get('rating') or 0) >= min_rating]
            if original_count != len(city_attrs):
                print(f"   📊 Filtered by rating ≥{min_rating}: {original_count} → {len(city_attrs)} POIs")
        
        # Select POIs for this day
        quota = compute_poi_quota(pace, len(city_attrs))
        selected = apply_diversity(city_attrs, quota, max_same_cat)
        
        # ✅ NEW: Optimize POI order geographically (nearest-neighbor)
        selected = optimize_poi_order(selected)
        
        # ✅ NEW: Calculate centroid of POIs for restaurant proximity filtering
        poi_centroid = get_poi_centroid(selected)
        
        # Get hotels for this city
        city_hotels = []
        for h in hotels:
            h_city = h.get("city", "")
            if cities_match(h_city, city_original):
                city_hotels.append(h)
        
        # Sort by rating (handle None values)
        top_hotels = sorted(city_hotels, key=lambda x: x.get("guest_rating") or 0, reverse=True)[:3]
        
        # Get restaurants for this city (if restaurants data is provided)
        city_restaurants = []
        if restaurants:
            for r in restaurants:
                r_city = r.get("city", "")
                if cities_match(r_city, city_original):
                    city_restaurants.append(r)
            
            # ✅ NEW: Filter restaurants by proximity to POI cluster (within 2.5 km)
            if poi_centroid and city_restaurants:
                nearby_restaurants = filter_nearby_restaurants(city_restaurants, poi_centroid, max_distance_km=2.5)
                
                # If we have nearby restaurants, use those; otherwise fall back to all city restaurants
                if nearby_restaurants:
                    city_restaurants = nearby_restaurants
                    # Sort by rating first, then by distance as tiebreaker
                    top_restaurants = sorted(
                        city_restaurants, 
                        key=lambda x: (-(x.get("rating") or 0), x.get('_distance_from_pois', 999)),
                        reverse=False
                    )
                else:
                    # No nearby restaurants found, use all city restaurants sorted by rating
                    top_restaurants = sorted(city_restaurants, key=lambda x: x.get("rating") or 0, reverse=True)
            else:
                # No centroid or no restaurants, fall back to rating sort
                top_restaurants = sorted(city_restaurants, key=lambda x: x.get("rating") or 0, reverse=True)
        else:
            top_restaurants = []
        
        # Select lunch and dinner restaurants
        lunch_restaurant = top_restaurants[0] if len(top_restaurants) > 0 else None
        dinner_restaurant = top_restaurants[1] if len(top_restaurants) > 1 else None
        
        # ✅ FIX: For circular and star/hub trips, handle hotels/dinner specially
        is_last_day = (i == len(route) - 1)
        
        # For star/hub trips, EVERY night is in the start city
        # For circular trips, only LAST night is in the start city
        if is_star_hub or (is_circular and is_last_day):
            # Last day of circular trip: lunch in current city, but hotel/dinner in start city
            start_city_original = city_name_map.get(route[0], route[0])
            
            # Get hotels from start city
            start_hotels = [h for h in hotels if normalize_city_name(h.get('city', '')) == normalize_city_name(start_city_original)]
            start_hotels_sorted = sorted(start_hotels, key=lambda x: x.get("guest_rating") or x.get("star_rating") or 0, reverse=True)[:3]
            
            # Get dinner restaurant from start city
            # Rotate through different restaurants for variety
            start_restaurants = [r for r in restaurants if normalize_city_name(r.get('city', '')) == normalize_city_name(start_city_original)] if restaurants else []
            start_restaurants_sorted = sorted(start_restaurants, key=lambda x: x.get("rating") or 0, reverse=True)
            
            # Use day_counter to rotate through restaurants (avoid same one every night)
            restaurant_index = (day_counter - 1) % len(start_restaurants_sorted) if start_restaurants_sorted else 0
            start_dinner = start_restaurants_sorted[restaurant_index] if start_restaurants_sorted else None
            
            itinerary.append({
                "day": day_counter,
                "city": city_original,
                "cities": [{"city": city_original, "attractions": selected}],
                "overnight_city": start_city_original,  # ✅ Return to start city
                "hotels": start_hotels_sorted,  # ✅ Hotels in start city
                "lunch_restaurant": lunch_restaurant,  # Lunch in current city
                "dinner_restaurant": start_dinner  # ✅ Dinner in start city
            })
        else:
            # Normal day or point-to-point trip
            itinerary.append({
                "day": day_counter,
                "city": city_original,
                "cities": [{"city": city_original, "attractions": selected}],
                "overnight_city": city_original,
                "hotels": top_hotels,
                "lunch_restaurant": lunch_restaurant,
                "dinner_restaurant": dinner_restaurant
            })
        day_counter += 1
    
    # Calculate distances between cities
    hop_kms = []
    for i in range(len(ordered_cities) - 1):
        c1 = centroids.get(ordered_cities[i])
        c2 = centroids.get(ordered_cities[i + 1])
        
        if c1 and c2:
            dist = haversine_km(c1, c2)
            hop_kms.append(round(dist) if dist and not math.isinf(dist) else None)
        else:
            hop_kms.append(None)
    
    # ✅ NEW: Add driving_km and driving_hours to each day
    # The driving happens when leaving a city to go to the next one
    for i, day_entry in enumerate(itinerary):
        if i < len(hop_kms):
            driving_km = hop_kms[i] or 0
            # Calculate driving time: assume average speed of 80 km/h
            driving_hours = round(driving_km / 80, 2) if driving_km > 0 else 0
            
            day_entry["driving_km"] = driving_km
            day_entry["driving_hours"] = driving_hours
        else:
            # Last day - no driving to next city
            day_entry["driving_km"] = 0
            day_entry["driving_hours"] = 0
    
    # Generate Google Maps link
    maps_link = google_maps_link(ordered_cities)
    
    return {
        "itinerary": itinerary,
        "ordered_cities": ordered_cities,
        "hop_kms": hop_kms,
        "maps_link": maps_link
    }