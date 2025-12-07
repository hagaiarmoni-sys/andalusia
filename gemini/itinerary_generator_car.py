"""
Car-Based Itinerary Generator for Andalusia Travel App
WITH OPTIMIZED ROUTE ALGORITHM (No Backtracking!)
"""

import streamlit as st
import math
import unicodedata
from collections import Counter
from urllib.parse import quote_plus
from text_norm import canonicalize_city, norm_key
from must_see_landmarks import is_must_see, get_must_see_count, get_missing_must_sees
from weighted_poi_scoring import calculate_weighted_score, score_and_sort_pois

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
    """Check if two city names match (handling accents and aliases)"""
    if not city1 or not city2:
        return False
    
    norm1 = normalize_city_name(city1)
    norm2 = normalize_city_name(city2)
    
    if norm1 == norm2:
        return True
    
    city_aliases = {
        'seville': {'seville', 'sevilla'},
        'cordoba': {'cordoba', 'córdoba'},
        'malaga': {'malaga', 'málaga'},
        'cadiz': {'cadiz', 'cádiz'},
        'jerez': {'jerez', 'jerez de la frontera'},
        'granada': {'granada'},
        'ronda': {'ronda'},
        'tarifa': {'tarifa'},
        'almeria': {'almeria', 'almería'},
        'antequera': {'antequera'},
        'marbella': {'marbella'},
        'nerja': {'nerja'}
    }
    
    for canonical, aliases in city_aliases.items():
        if norm1 in aliases and norm2 in aliases:
            return True
            
    if len(norm1) > 3 and len(norm2) > 3 and (norm1 in norm2 or norm2 in norm1):
        return True
    
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
    """Calculate driving distance between two coordinates"""
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
    
    return distance if distance < 10000 else None


def calculate_driving_time(distance_km):
    """Calculate driving time in hours based on distance"""
    if distance_km < 30:
        return distance_km / 40 + 0.25
    elif distance_km < 100:
        return distance_km / 70 + 0.25
    else:
        return distance_km / 100 + 0.5

def google_maps_link(cities):
    """Generate Google Maps link for multi-city route"""
    if not cities or len(cities) < 2:
        return ""
    
    origin = cities[0]
    destination = cities[-1]
    waypoints = cities[1:-1] if len(cities) > 2 else []
    
    base_url = "https://www.google.com/maps/dir/"
    
    parts = [quote_plus(str(origin))]
    for wp in waypoints:
        parts.append(quote_plus(str(wp)))
    parts.append(quote_plus(str(destination)))
    
    return base_url + "/".join(parts)


def filter_duplicate_pois(pois):
    """Remove duplicate POIs using place_id (most reliable) with name-based fallback"""
    if not pois:
        return []
    
    seen_place_ids = set()
    seen_normalized_names = set()
    unique = []
    
    for poi in pois:
        place_id = poi.get('place_id')
        
        if place_id:
            if place_id not in seen_place_ids:
                seen_place_ids.add(place_id)
                unique.append(poi)
            continue
        
        name = poi.get('name', '').lower().strip()
        if not name:
            continue
            
        name = ''.join(c for c in unicodedata.normalize('NFD', name) if unicodedata.category(c) != 'Mn')
        normalized = ''.join(c for c in name if c.isalnum())
        
        if normalized and normalized not in seen_normalized_names:
            seen_normalized_names.add(normalized)
            unique.append(poi)
    
    return unique

def compute_poi_quota(pace, total_pois, has_blockbuster=False):
    """Calculate how many POIs to select based on pace"""
    if has_blockbuster:
        if pace == "relaxed": quota = min(3, total_pois)
        elif pace == "fast": quota = min(4, total_pois)
        else: quota = min(3, total_pois)
    else:
        if pace == "relaxed": quota = min(5, total_pois)
        elif pace == "fast": quota = min(7, total_pois)
        else: quota = min(6, total_pois)

    if total_pois < 15:
        quota = max(quota, min(total_pois // 2 + 1, total_pois))

    return max(3, min(quota, total_pois))


def has_blockbuster_attraction(pois):
    """Check if POI list contains a blockbuster attraction"""
    for poi in pois:
        duration = poi.get('visit_duration_hours', 0)
        try:
            duration = float(duration)
            if duration >= 3.0:
                return True
        except (ValueError, TypeError):
            continue
    return False


def apply_diversity(pois, quota, max_same_category):
    """Select POIs with category diversity using weighted scoring"""
    if not pois:
        return []
    
    for poi in pois:
        city_name = poi.get('city_label', poi.get('city', ''))
        poi['weighted_score'] = calculate_weighted_score(poi, city_name)
    
    sorted_pois = sorted(pois, key=lambda x: x.get('weighted_score', 0), reverse=True)
    
    selected = []
    category_count = Counter()
    total_duration = 0
    max_duration_minutes = 8 * 60
    
    for poi in sorted_pois:
        if len(selected) >= quota:
            break
        
        duration = poi.get('duration_minutes', 60)
        if total_duration + duration > max_duration_minutes:
            continue
        
        category = poi.get('category', 'Other')
        
        if category_count[category] < max_same_category:
            selected.append(poi)
            category_count[category] += 1
            total_duration += duration
    
    if len(selected) < quota:
        for poi in sorted_pois:
            if poi not in selected and len(selected) < quota:
                duration = poi.get('duration_minutes', 60)
                if total_duration + duration <= max_duration_minutes:
                    selected.append(poi)
                    total_duration += duration
    
    return selected


# ============================================================================
# OPTIMIZED ROUTE ALGORITHM
# ============================================================================

def optimize_route_andalusia(start_city, end_city, available_cities, centroids, city_name_map, days, parsed_requests, prefs):
    """
    OPTIMIZED ROUTE BUILDER - NO BACKTRACKING
    """
    
    MAJOR_CITIES = {
        'granada': 100, 'cordoba': 90, 'córdoba': 90,
        'seville': 95, 'sevilla': 95, 'cadiz': 85, 'cádiz': 85,
        'malaga': 80, 'málaga': 80, 'ronda': 70,
        'jerez': 65, 'tarifa': 55, 'marbella': 50,
        'antequera': 45, 'nerja': 40
    }
    
    must_see_norms = [normalize_city_name(c) for c in parsed_requests.get('must_see_cities', [])]
    avoid_norms = [normalize_city_name(c) for c in parsed_requests.get('avoid_cities', [])]
    
    start_name = city_name_map.get(start_city, start_city)
    end_name = city_name_map.get(end_city, end_city)
    start_coord = centroids.get(start_name)
    end_coord = centroids.get(end_name)
    
    # ✅ FIX: Return tuple on failure to match unpacking expectations
    if not start_coord or not end_coord:
        st.warning(f"⚠️ Missing coordinates for {start_name} or {end_name}")
        return [], set() 
    
    direct_distance = haversine_km(start_coord, end_coord)
    is_circular = (end_city == start_city)
    
    candidates = []
    
    for city_norm, pois in available_cities.items():
        if city_norm in avoid_norms or city_norm == start_city or city_norm == end_city:
            continue
        
        city_name = city_name_map.get(city_norm)
        
        if city_norm in MAJOR_CITIES:
            min_required_pois = 8
        else:
            min_required_pois = 12
        
        if len(pois) < min_required_pois:
            continue
        
        city_coord = centroids.get(city_name)
        
        if not city_coord:
            continue
        
        dist_start_to_city = haversine_km(start_coord, city_coord)
        dist_city_to_end = haversine_km(city_coord, end_coord)
        total_via_city = dist_start_to_city + dist_city_to_end
        
        if is_circular:
            detour_ratio = 0
        else:
            detour_ratio = total_via_city / direct_distance if direct_distance > 0 else 999
        
        if detour_ratio > 3.0 and city_norm not in must_see_norms:
            continue
        
        score = len(pois) * 3
        
        if city_norm in MAJOR_CITIES:
            score += MAJOR_CITIES[city_norm]
        
        if city_norm in must_see_norms:
            score += 200
        
        if detour_ratio < 1.2:
            score += 50
        
        candidates.append({
            'city_norm': city_norm,
            'city_name': city_name,
            'coord': city_coord,
            'score': score,
            'detour': detour_ratio
        })
    
    candidates.sort(key=lambda x: -x['score'])
    
    max_intermediate = days - 2 if end_city != start_city else days - 1
    
    route = [start_city]
    available = candidates[:]
    current_coord = start_coord
    dist_to_end = direct_distance
    
    for step in range(max_intermediate):
        if not available:
            break
        
        best = None
        best_score = -float('inf')
        
        for candidate in available:
            dist_to_candidate = haversine_km(current_coord, candidate['coord'])
            dist_candidate_to_end = haversine_km(candidate['coord'], end_coord)
            
            MAX_SINGLE_DRIVE = prefs.get("max_km_per_day", 250)
            if dist_to_candidate > MAX_SINGLE_DRIVE and candidate['city_norm'] not in must_see_norms:
                continue
            
            if candidate['city_norm'] in MAJOR_CITIES and candidate['score'] > 100:
                tolerance = 150
            elif candidate['city_norm'] in MAJOR_CITIES:
                tolerance = 100
            else:
                tolerance = 50
            
            if not is_circular:
                if dist_candidate_to_end > dist_to_end + tolerance and candidate['city_norm'] not in must_see_norms:
                    continue
            
            nearby_score = max(0, 200 - dist_to_candidate)
            
            if is_circular and step > max_intermediate / 2:
                dist_back_to_start = haversine_km(candidate['coord'], start_coord)
                progress = max(-50, (200 - dist_back_to_start))
            else:
                progress = max(-50, (dist_to_end - dist_candidate_to_end) * 1.5)
            
            quality = candidate['score']
            combined = (nearby_score * 0.2) + (progress * 0.3) + (quality * 0.5)
            
            if combined > best_score:
                best_score = combined
                best = candidate
        
        if best:
            route.append(best['city_norm'])
            current_coord = best['coord']
            dist_to_end = haversine_km(current_coord, end_coord)
            available.remove(best)
        else:
            if available:
                best_fallback = max(available, key=lambda x: x['score'])
                route.append(best_fallback['city_norm'])
                current_coord = best_fallback['coord']
                dist_to_end = haversine_km(current_coord, end_coord)
                available.remove(best_fallback)
            else:
                break
    
    if end_city and end_city != start_city:
        route.append(end_city)
    elif is_circular:
        route.append(start_city)
    
    # 2-opt optimization
    def optimize_route_2opt(route, centroids, city_name_map):
        if len(route) <= 3:
            return route
        
        improved = True
        iterations = 0
        max_iterations = 10
        
        while improved and iterations < max_iterations:
            improved = False
            iterations += 1
            
            for i in range(1, len(route) - 2):
                for j in range(i + 1, len(route) - 1):
                    c1_name = city_name_map.get(route[i-1], route[i-1])
                    c2_name = city_name_map.get(route[i], route[i])
                    c3_name = city_name_map.get(route[j], route[j])
                    c4_name = city_name_map.get(route[j+1], route[j+1])
                    
                    c1_coord = centroids.get(c1_name)
                    c2_coord = centroids.get(c2_name)
                    c3_coord = centroids.get(c3_name)
                    c4_coord = centroids.get(c4_name)
                    
                    if not all([c1_coord, c2_coord, c3_coord, c4_coord]):
                        continue
                    
                    current_dist = (haversine_km(c1_coord, c2_coord) + 
                                   haversine_km(c3_coord, c4_coord))
                    
                    new_dist = (haversine_km(c1_coord, c3_coord) + 
                               haversine_km(c2_coord, c4_coord))
                    
                    if new_dist < current_dist - 1:
                        route[i:j+1] = reversed(route[i:j+1])
                        improved = True
                        break
                if improved:
                    break
        return route
    
    route = optimize_route_2opt(route, centroids, city_name_map)
    
    # ✅ FIX: Return explicit tuple (route, empty_set)
    return route, set()


# ============================================================================
# STAR/HUB TRIP GENERATOR
# ============================================================================

def generate_star_hub_trip(base_city, days, prefs, attractions, hotels, restaurants=None):
    st.info(f"⭐ Planning {days}-day Star/Hub trip from {base_city}")
    
    base_city_norm = normalize_city_name(base_city)
    base_attractions = [a for a in attractions if normalize_city_name(a.get('city', '')) == base_city_norm]
    
    if not base_attractions:
        st.error(f"❌ No attractions found in {base_city}")
        return None
    
    centroids = {}
    for attr in attractions:
        city = attr.get('city')
        coords = attr.get('coordinates', {})
        lat = coords.get('latitude') or coords.get('lat')
        lon = coords.get('longitude') or coords.get('lng') or coords.get('lon')
        if city and lat and lon:
            if city not in centroids:
                centroids[city] = (float(lat), float(lon))
    
    base_coord = centroids.get(base_city)
    if not base_coord:
        return None
    
    MAX_DAY_TRIP_KM = 150
    nearby_cities = []
    city_attractions_map = {}
    
    for attr in attractions:
        city = attr.get('city')
        if not city or normalize_city_name(city) == base_city_norm:
            continue
        
        city_coord = centroids.get(city)
        if not city_coord:
            continue
        
        distance = haversine_km(base_coord, city_coord)
        
        if distance <= MAX_DAY_TRIP_KM:
            city_norm = normalize_city_name(city)
            if city_norm not in city_attractions_map:
                city_attractions_map[city_norm] = {
                    'city': city,
                    'distance': distance,
                    'attractions': []
                }
            city_attractions_map[city_norm]['attractions'].append(attr)
    
    for city_norm, data in city_attractions_map.items():
        if len(data['attractions']) >= 3:
            nearby_cities.append(data)
    
    nearby_cities.sort(key=lambda x: -len(x['attractions']) + x['distance']/10)
    
    itinerary = []
    pace = prefs.get("pace", "medium")
    max_same_cat = prefs.get("max_same_category_per_day", 2)
    
    days_in_base = 1
    days_for_trips = days - 1
    day_counter = 1
    
    for i in range(days_in_base):
        city_attractions = [a for a in base_attractions]
        city_attractions = filter_duplicate_pois(city_attractions)
        has_blockbuster = has_blockbuster_attraction(city_attractions)
        quota = compute_poi_quota(pace, len(city_attractions), has_blockbuster)
        selected_pois = apply_diversity(city_attractions, quota, max_same_cat)
        base_attractions = [a for a in base_attractions if a not in selected_pois]
        
        itinerary.append({
            'day': day_counter,
            'city': base_city,
            'driving_km': 0,
            'driving_hours': 0,
            'cities': [{'city': base_city, 'attractions': selected_pois}]
        })
        day_counter += 1
    
    for i in range(min(days_for_trips, len(nearby_cities))):
        day_trip = nearby_cities[i]
        trip_city = day_trip['city']
        trip_distance = day_trip['distance']
        trip_attractions = day_trip['attractions']
        trip_attractions = filter_duplicate_pois(trip_attractions)
        quota = compute_poi_quota(pace, len(trip_attractions))
        selected_pois = apply_diversity(trip_attractions, quota, max_same_cat)
        total_km = round(trip_distance * 2, 1)
        driving_hours = round(calculate_driving_time(trip_distance) * 2, 1)
        
        itinerary.append({
            'day': day_counter,
            'city': trip_city,
            'is_day_trip': True,
            'base': base_city,
            'driving_km': total_km,
            'driving_hours': driving_hours,
            'cities': [{'city': trip_city, 'attractions': selected_pois}]
        })
        day_counter += 1
    
    base_city_hotels = [h for h in hotels if normalize_city_name(h.get('city', '')) == base_city_norm]
    top_hotels = sorted(base_hotels, key=lambda x: x.get('rating', 0), reverse=True)[:3]
    
    if restaurants:
        try:
            from restaurant_service import add_restaurants_to_itinerary
            itinerary = add_restaurants_to_itinerary(itinerary, restaurants, prefs.get('budget', 'mid-range'), prefs)
        except Exception as e:
            print(f"⚠️ Could not add restaurants: {e}")
    
    visited_cities = [base_city]
    for day_data in itinerary:
        if day_data.get('is_day_trip'):
            city = day_data['city']
            if city not in visited_cities:
                visited_cities.append(city)
    
    total_driving_km = round(sum(day['driving_km'] for day in itinerary), 1)
    day_trip_cities = [d['city'] for d in itinerary if d.get('is_day_trip')]
    maps_link = google_maps_link([base_city] + day_trip_cities)
    
    return {
        'itinerary': itinerary,
        'ordered_cities': visited_cities,
        'hop_kms': [0] * (len(visited_cities) - 1),
        'total_km': total_driving_km,
        'maps_link': maps_link,
        'start_end_text': base_city,
        'days': days,
        'preferences': prefs,
        'trip_type': 'Star/Hub',
        'base_city': base_city,
        'base_hotels': top_hotels
    }


# ============================================================================
# MAIN TRIP GENERATION FUNCTION
# ============================================================================

def generate_simple_trip(start_end_text, days, prefs, trip_type, attractions, hotels, restaurants=None):
    is_star_hub = trip_type and ('star' in trip_type.lower() or 'hub' in trip_type.lower())
    
    if is_star_hub:
        base_city = start_end_text.strip()
        known_cities = {(attr.get('city') or '').strip() for attr in attractions}
        known_cities.discard('')
        base_city_canonical = canonicalize_city(base_city, known_cities)
        
        if not base_city_canonical:
            st.error(f"❌ Base city '{base_city}' not found in data")
            return None
        
        return generate_star_hub_trip(base_city_canonical, days, prefs, attractions, hotels, restaurants)
    
    known_cities = {(attr.get('city') or '').strip() for attr in attractions}
    known_cities.discard('')
    
    start_city, end_city = parse_start_end(start_end_text, trip_type)
    if not start_city:
        st.error("❌ Please specify a start city")
        return None
    
    start_city_canonical = canonicalize_city(start_city, known_cities)
    end_city_canonical = canonicalize_city(end_city, known_cities) if end_city else None
    
    if not start_city_canonical:
        st.error(f"❌ Start city '{start_city}' not found in data")
        return None
    
    start_city = start_city_canonical
    end_city = end_city_canonical
    
    min_rating = prefs.get('min_poi_rating', 0.0)
    
    # ✅ FIX: Handle NoneType comparison crash
    if min_rating > 0:
        attractions = [a for a in attractions if float(a.get('rating') or 0) >= min_rating]
    
    # Internal Category Filter
    pref_cats = prefs.get('poi_categories', [])
    if pref_cats:
        filtered_attrs = []
        for a in attractions:
            a_cat = str(a.get('category', '')).lower()
            a_name = str(a.get('name', '')).lower()
            match = False
            for p_cat in pref_cats:
                p_cat = p_cat.lower()
                if p_cat in a_cat: match = True
                if p_cat == "history" and any(x in a_cat for x in ['castle', 'ruin', 'historic', 'monument']): match = True
                if p_cat == "nature" and any(x in a_cat for x in ['park', 'garden', 'mountain', 'hike']): match = True
                if p_cat == "art" and any(x in a_cat for x in ['museum', 'gallery']): match = True
            
            if match:
                filtered_attrs.append(a)
        
        if len(filtered_attrs) > 100:
            attractions = filtered_attrs
    
    centroids = {}
    for attr in attractions:
        city = attr.get('city')
        coords = attr.get('coordinates', {})
        lat = coords.get('latitude') or coords.get('lat')
        lon = coords.get('longitude') or coords.get('lng') or coords.get('lon')
        if city and lat and lon:
            if city not in centroids:
                centroids[city] = (float(lat), float(lon))
    
    by_city_normalized = {}
    city_name_map = {}
    
    for attr in attractions:
        city = attr.get('city')
        if not city: continue
        city_norm = normalize_city_name(city)
        if city_norm not in city_name_map: city_name_map[city_norm] = city
        if city_norm not in by_city_normalized: by_city_normalized[city_norm] = []
        by_city_normalized[city_norm].append(attr)
    
    start_city_norm = normalize_city_name(start_city)
    end_city_norm = normalize_city_name(end_city) if end_city else None
    
    parsed_requests = {'stay_duration': {}, 'must_see_cities': [], 'avoid_cities': []}
    
    # ✅ FIX: Unpack tuple correctly
    route, intermediate_stops = optimize_route_andalusia(
        start_city_norm,
        end_city_norm,
        by_city_normalized,
        centroids,
        city_name_map,
        days,
        parsed_requests,
        prefs
    )
    
    if not route:
        st.error("❌ Could not generate route")
        return None
    
    ordered_cities = [city_name_map.get(c, c) for c in route]
    
    itinerary = []
    pace = prefs.get("pace", "medium")
    max_same_cat = prefs.get("max_same_category_per_day", 2)
    day_counter = 1
    
    is_circular_trip = (len(route) >= 2 and route[0] == route[-1])
    start_city_for_hotels = city_name_map.get(route[0], route[0]) if is_circular_trip else None
    
    for i, city_norm in enumerate(route):
        city_original = city_name_map.get(city_norm, city_norm)
        
        if is_circular_trip and i == len(route) - 1:
            continue
        
        city_attrs = by_city_normalized.get(city_norm, [])
        has_blockbuster = has_blockbuster_attraction(city_attrs)
        quota = compute_poi_quota(pace, len(city_attrs), has_blockbuster)
        selected = apply_diversity(city_attrs, quota, max_same_cat)
        
        if is_circular_trip and i == len(route) - 2:
            overnight_city = start_city_for_hotels
        else:
            overnight_city = city_original
        
        city_hotels = []
        for h in hotels:
            h_city = h.get("city", "")
            if cities_match(h_city, overnight_city):
                city_hotels.append(h)
        
        top_hotels = sorted(city_hotels, key=lambda x: x.get("guest_rating") or x.get("rating", 0) or 0, reverse=True)[:3]
        
        city_restaurants = []
        if restaurants:
            for r in restaurants:
                r_city = r.get("city", "")
                if cities_match(r_city, city_original):
                    city_restaurants.append(r)
            top_restaurants = sorted(city_restaurants, key=lambda x: x.get("rating") or 0, reverse=True)
        else:
            top_restaurants = []
        
        lunch_restaurant = top_restaurants[0] if len(top_restaurants) > 0 else None
        dinner_restaurant = top_restaurants[1] if len(top_restaurants) > 1 else None
        
        itinerary.append({
            "day": day_counter,
            "city": city_original,
            "cities": [{"city": city_original, "attractions": selected}],
            "overnight_city": overnight_city,
            "hotels": top_hotels,
            "lunch_restaurant": lunch_restaurant,
            "dinner_restaurant": dinner_restaurant
        })
        day_counter += 1
    
    hop_kms = []
    total_km = 0
    
    for i in range(len(ordered_cities) - 1):
        city1 = ordered_cities[i]
        city2 = ordered_cities[i + 1]
        c1 = centroids.get(city1)
        c2 = centroids.get(city2)
        
        if c1 and c2:
            dist = haversine_km(c1, c2)
            if dist:
                hop_kms.append(round(dist))
                total_km += dist
            else:
                hop_kms.append(None)
        else:
            hop_kms.append(None)
    
    maps_link = google_maps_link(ordered_cities)
    
    return {
        "itinerary": itinerary,
        "ordered_cities": ordered_cities,
        "hop_kms": hop_kms,
        "total_km": round(total_km, 1),
        "maps_link": maps_link
    }