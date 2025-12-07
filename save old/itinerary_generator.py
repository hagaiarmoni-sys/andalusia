"""
Car-Based Itinerary Generator for Andalusia Road Trip App
Optimized for travelers with rental cars - focuses on base cities and day trips
"""

import streamlit as st
import math
import unicodedata
from collections import Counter
from urllib.parse import quote_plus


def normalize_city_name(city_name):
    """Normalize city name by removing accents and converting to lowercase"""
    if not city_name:
        return ""
    
    city_name = str(city_name)
    nfd = unicodedata.normalize('NFD', city_name)
    without_accents = ''.join(char for char in nfd if unicodedata.category(char) != 'Mn')
    return without_accents.lower().strip()


def cities_match(city1, city2):
    """Check if two city names match (ignoring accents and case)"""
    if not city1 or not city2:
        return False
    
    norm1 = normalize_city_name(city1)
    norm2 = normalize_city_name(city2)
    
    if norm1 == norm2:
        return True
    
    city_aliases = {
        'seville': {'seville', 'sevilla'},
        'cordoba': {'cordoba', 'córdoba', 'cordova'},
        'malaga': {'malaga', 'málaga'},
        'cadiz': {'cadiz', 'cádiz'},
        'jerez': {'jerez', 'jerez de la frontera'},
        'granada': {'granada'},
        'almeria': {'almeria', 'almería'},
    }
    
    for canonical, aliases in city_aliases.items():
        if norm1 in aliases and norm2 in aliases:
            return True
    
    if len(norm1) > 3 and len(norm2) > 3:
        if norm1 in norm2 or norm2 in norm1:
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


def haversine_km(a, b, road_factor=1.3):
    """Calculate driving distance between two coordinates"""
    if not a or not b:
        return float("inf")
    
    if isinstance(a, tuple) and len(a) == 2:
        lat1, lon1 = a
    else:
        return float("inf")
    
    if isinstance(b, tuple) and len(b) == 2:
        lat2, lon2 = b
    else:
        return float("inf")
    
    if lat1 is None or lon1 is None or lat2 is None or lon2 is None:
        return float("inf")
    
    try:
        lat1, lon1, lat2, lon2 = float(lat1), float(lon1), float(lat2), float(lon2)
        
        if not (-90 <= lat1 <= 90 and -90 <= lat2 <= 90):
            return float("inf")
        if not (-180 <= lon1 <= 180 and -180 <= lon2 <= 180):
            return float("inf")
        
        R = 6371.0
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        sa = math.sin(dlat / 2) ** 2
        sb = math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
        straight_line = 2 * R * math.atan2(math.sqrt(sa + sb), math.sqrt(1 - (sa + sb)))
        
        return straight_line * road_factor
    except (ValueError, TypeError):
        return float("inf")


def calculate_driving_time(distance_km):
    """
    Calculate driving time with realistic speed estimates
    
    Speed assumptions:
    - < 30km: Local roads, city traffic (40 km/h)
    - 30-100km: Mix of highway and local (70 km/h)
    - > 100km: Mostly highway (100 km/h)
    
    Adds buffers for parking and rest stops
    """
    if distance_km < 30:
        speed_kmh = 40
        parking_buffer = 0.25  # 15 minutes
        rest_buffer = 0
    elif distance_km < 100:
        speed_kmh = 70
        parking_buffer = 0.25
        rest_buffer = 0
    else:
        speed_kmh = 100
        parking_buffer = 0.25
        rest_buffer = 0.5  # 30 min rest stop for long drives
    
    base_time = distance_km / speed_kmh
    return base_time + parking_buffer + rest_buffer


def compute_city_centroids(attractions, hotels):
    """Compute geographic center point for each city"""
    buckets = {}
    
    def add_point(city, coord):
        if not city or not coord:
            return
        lat = coord.get("lat") or coord.get("latitude")
        lon = coord.get("lon") or coord.get("lng") or coord.get("longitude")
        if lat is None or lon is None:
            return
        b = buckets.setdefault(city, {"n": 0, "lat": 0.0, "lon": 0.0})
        b["n"] += 1
        b["lat"] += float(lat)
        b["lon"] += float(lon)
    
    for a in attractions or []:
        add_point(a.get("city"), a.get("coordinates"))
    for h in hotels or []:
        coord = h.get("coordinates") or {"lat": h.get("lat"), "lon": h.get("lon")}
        add_point(h.get("city"), coord)
    
    centroids = {}
    for city, agg in buckets.items():
        if agg["n"] > 0:
            centroids[city] = (agg["lat"] / agg["n"], agg["lon"] / agg["n"])
    return centroids


def google_maps_link(cities):
    """Generate Google Maps directions link"""
    if not cities:
        return ""
    base = "https://www.google.com/maps/dir/"
    return base + "/".join(quote_plus(c) for c in cities)


def is_valid_attraction(attraction):
    """Filter out invalid attractions"""
    name = attraction.get("name", "").lower()
    
    bad_keywords = [
        'crematorio', 'cementerio', 'cemetery', 'funeral', 
        'crematorium', 'graveyard', 'morgue',
    ]
    
    if any(bad in name for bad in bad_keywords):
        return False
    
    if not name or name in ['unknown', 'none', '', 'n/a', 'null']:
        return False
    
    return True


def get_poi_coordinates(poi):
    """Extract coordinates from POI"""
    coords = poi.get('coordinates', {})
    
    if isinstance(coords, dict):
        lat = coords.get('lat') or coords.get('latitude')
        lon = coords.get('lon') or coords.get('lng') or coords.get('longitude')
        
        if lat is not None and lon is not None:
            try:
                lat_f = float(lat)
                lon_f = float(lon)
                
                if not (-90 <= lat_f <= 90):
                    return None
                if not (-180 <= lon_f <= 180):
                    return None
                
                # Check for swapped coordinates
                if lat_f < 0 or lon_f > 0:
                    if -90 <= lon_f <= 90 and -180 <= lat_f <= 180:
                        return (lon_f, lat_f)
                
                return (lat_f, lon_f)
            except (ValueError, TypeError):
                return None
    
    return None


def select_base_cities(start_city, end_city, days, city_scores, centroids, max_km_per_day=300):
    """
    Select 2-4 strategic base cities for the road trip
    
    Strategy:
    - Short trips (3-5 days): 2 bases
    - Medium trips (6-8 days): 3 bases
    - Long trips (9+ days): 3-4 bases
    
    Ensures bases are not too close (waste) or too far (exhausting drive)
    """
    
    # Determine number of bases
    if days <= 5:
        num_bases = 2
    elif days <= 8:
        num_bases = 3
    else:
        num_bases = 4
    
    bases = []
    
    # Always start with start_city
    start_city_norm = normalize_city_name(start_city)
    if start_city_norm:
        bases.append(start_city_norm)
    
    # Always end with end_city if different
    end_city_norm = normalize_city_name(end_city)
    force_end_city = end_city_norm and end_city_norm != start_city_norm
    
    # Fill intermediate bases
    remaining_bases = num_bases - len(bases) - (1 if force_end_city else 0)
    
    # Get candidates sorted by score
    candidates = [(norm, score) for norm, score in city_scores 
                  if norm != start_city_norm and norm != end_city_norm]
    candidates.sort(key=lambda x: x[1], reverse=True)
    
    for city_norm, _ in candidates:
        if remaining_bases <= 0:
            break
        
        # Check if this city is well-positioned
        if bases:
            last_base = bases[-1]
            last_centroid = centroids.get(last_base)
            current_centroid = centroids.get(city_norm)
            
            if last_centroid and current_centroid:
                distance = haversine_km(last_centroid, current_centroid)
                
                # Should be at least 80km apart (meaningful move)
                # But not more than max_km_per_day
                if distance < 80:
                    continue
                if distance > max_km_per_day:
                    continue
        
        bases.append(city_norm)
        remaining_bases -= 1
    
    # Add end city
    if force_end_city:
        bases.append(end_city_norm)
    
    return bases


def allocate_nights_to_bases(bases, total_days):
    """
    Allocate nights to each base city
    
    Strategy:
    - First and last bases: 2-3 nights (arrival/departure logistics)
    - Middle bases: Divide remaining nights evenly
    """
    if not bases:
        return {}
    
    if len(bases) == 1:
        return {bases[0]: total_days}
    
    allocation = {}
    
    # First base: 2-3 nights depending on total days
    first_nights = 3 if total_days >= 7 else 2
    allocation[bases[0]] = first_nights
    
    remaining_days = total_days - first_nights
    
    # Last base: 2 nights
    if len(bases) > 1:
        last_nights = min(2, remaining_days)
        allocation[bases[-1]] = last_nights
        remaining_days -= last_nights
    
    # Middle bases: divide evenly
    if len(bases) > 2:
        middle_bases = bases[1:-1]
        nights_per_middle = max(2, remaining_days // len(middle_bases))
        
        for base in middle_bases:
            allocation[base] = nights_per_middle
            remaining_days -= nights_per_middle
    
    # Distribute any remaining days to middle/last bases
    if remaining_days > 0:
        for i in range(len(bases) - 1, 0, -1):
            if remaining_days > 0:
                allocation[bases[i]] += 1
                remaining_days -= 1
    
    return allocation


def get_attractions_within_radius(base_city_norm, all_attractions, centroids, max_radius_km=80):
    """
    Get all attractions within driving radius of base city
    
    For car travel, we can reach attractions up to 80km away (1-1.5h drive)
    """
    base_centroid = centroids.get(base_city_norm)
    if not base_centroid:
        return []
    
    nearby_attractions = []
    
    for attr in all_attractions:
        coords = get_poi_coordinates(attr)
        if not coords:
            continue
        
        distance = haversine_km(base_centroid, coords)
        if distance and distance <= max_radius_km:
            attr_copy = attr.copy()
            attr_copy['distance_from_base'] = round(distance, 1)
            attr_copy['driving_time_hours'] = round(calculate_driving_time(distance), 1)
            nearby_attractions.append(attr_copy)
    
    return nearby_attractions


def cluster_attractions_by_area(attractions, centroids, base_centroid):
    """
    Cluster attractions into day trip areas
    
    Groups attractions that are:
    - In the same direction from base
    - Close to each other (within 20km)
    - Can be visited in one day
    """
    if not attractions:
        return []
    
    # Sort by distance from base
    attractions_sorted = sorted(attractions, key=lambda x: x.get('distance_from_base', 999))
    
    clusters = []
    current_cluster = []
    
    for attr in attractions_sorted:
        if not current_cluster:
            current_cluster.append(attr)
            continue
        
        # Check if this attraction is close to cluster
        cluster_coords = [get_poi_coordinates(a) for a in current_cluster]
        attr_coords = get_poi_coordinates(attr)
        
        if attr_coords:
            # Find closest attraction in cluster
            min_distance = float('inf')
            for c_coords in cluster_coords:
                if c_coords:
                    dist = haversine_km(attr_coords, c_coords)
                    if dist < min_distance:
                        min_distance = dist
            
            # If within 20km of cluster, add to it
            if min_distance < 20:
                current_cluster.append(attr)
            else:
                # Start new cluster
                if len(current_cluster) >= 2:  # Only keep clusters with 2+ attractions
                    clusters.append(current_cluster)
                current_cluster = [attr]
    
    # Add last cluster
    if len(current_cluster) >= 2:
        clusters.append(current_cluster)
    
    return clusters


def apply_diversity(all_pois, quota, max_same=2):
    """Apply category diversity"""
    if not all_pois or quota <= 0:
        return []
    
    remaining = all_pois.copy()
    remaining.sort(key=lambda x: (
        x.get('priority', 0),
        x.get('rating') or 0
    ), reverse=True)
    
    selected = []
    cat_counts = {}
    
    for poi in remaining:
        if len(selected) >= quota:
            break
        
        cat = (poi.get("category") or "unknown").lower().strip()
        current_count = cat_counts.get(cat, 0)
        
        if current_count < max_same:
            selected.append(poi)
            cat_counts[cat] = current_count + 1
    
    return selected


def generate_simple_trip(start_end_text, days, prefs, trip_type, attractions, hotels, special_requests="", restaurants=None):
    """
    🚗 Generate CAR-BASED road trip itinerary
    
    Strategy:
    1. Select 2-4 strategic base cities
    2. Allocate nights to each base
    3. For each base: plan day trips to nearby attractions
    4. Optimize driving routes for each day
    """
    
    from special_requests_parser import parse_special_requests, validate_requests
    from restaurant_service import add_restaurants_to_itinerary
    
    if restaurants is None:
        restaurants = []
    
    print(f"\n=== 🚗 CAR-BASED ROAD TRIP PLANNER ===")
    print(f"Attractions: {len(attractions)}")
    print(f"Hotels: {len(hotels)}")
    print(f"Restaurants: {len(restaurants)}")
    print(f"Days: {days}")
    print("=" * 50 + "\n")
    
    start_city, end_city = parse_start_end(start_end_text, trip_type)
    min_rating = prefs.get("min_poi_rating", 0.0)
    
    # Parse special requests
    parsed_requests = parse_special_requests(special_requests)
    validation = validate_requests(parsed_requests)
    
    if parsed_requests['avoid_cities']:
        st.warning(f"🚫 **Avoiding:** {', '.join(parsed_requests['avoid_cities'])}")
    
    if parsed_requests['must_see_cities']:
        st.success(f"✅ **Must see:** {', '.join(parsed_requests['must_see_cities'])}")
    
    if not validation['valid']:
        for conflict in validation['conflicts']:
            st.error(f"⚠️ {conflict}")
        st.stop()
    
    for warning in validation['warnings']:
        st.warning(warning)
    
    st.info(f"🚗 Planning road trip: {start_city} → {end_city} ({days} days)")
    
    # Filter attractions
    filtered = []
    for a in attractions:
        rating = a.get("rating")
        name = a.get("name")
        city = a.get("city", "")
        
        if not name or not is_valid_attraction(a):
            continue
        
        if parsed_requests['avoid_cities']:
            should_skip = any(
                normalize_city_name(avoid) == normalize_city_name(city)
                for avoid in parsed_requests['avoid_cities']
            )
            if should_skip:
                continue
        
        if rating is None or rating == 0 or rating >= min_rating:
            is_must_see_city = any(
                normalize_city_name(must_see) == normalize_city_name(city)
                for must_see in parsed_requests['must_see_cities']
            )
            
            is_must_see_attraction = any(
                must_see.lower() in name.lower()
                for must_see in parsed_requests['must_see_attractions']
            )
            
            a['is_must_see_city'] = is_must_see_city
            a['is_must_see_attraction'] = is_must_see_attraction
            a['priority'] = (is_must_see_city * 2) + (is_must_see_attraction * 3)
            
            filtered.append(a)
    
    filtered.sort(key=lambda x: x.get('priority', 0), reverse=True)
    
    centroids = compute_city_centroids(filtered, hotels)
    
    # Group by city
    by_city_normalized = {}
    city_name_map = {}
    
    for a in filtered:
        city_original = a.get("city", "")
        if not city_original:
            continue
        city_norm = normalize_city_name(city_original)
        
        by_city_normalized.setdefault(city_norm, []).append(a)
        if city_norm not in city_name_map:
            city_name_map[city_norm] = city_original
    
    print("\n=== POI Count per City ===")
    for city_norm, attrs in by_city_normalized.items():
        city_original = city_name_map.get(city_norm, city_norm)
        print(f"{city_original}: {len(attrs)} POIs")
    print("=" * 50 + "\n")
    
    # Score cities for base selection
    city_scores = []
    for city_norm, attrs in by_city_normalized.items():
        must_see_count = sum(1 for a in attrs if a.get('is_must_see_city'))
        total_priority = sum(a.get('priority', 0) for a in attrs)
        score = (must_see_count * 100) + total_priority + len(attrs)
        city_scores.append((city_norm, score))
    
    city_scores.sort(key=lambda x: x[1], reverse=True)
    
    # 🚗 STEP 1: Select base cities
    base_cities_norm = select_base_cities(
        start_city, 
        end_city, 
        days, 
        city_scores, 
        centroids,
        max_km_per_day=prefs.get("max_km_per_day", 300)
    )
    
    base_cities = [city_name_map.get(c, c) for c in base_cities_norm]
    
    print(f"\n🏨 Selected Base Cities: {' → '.join(base_cities)}")
    
    # 🚗 STEP 2: Allocate nights
    night_allocation = allocate_nights_to_bases(base_cities_norm, days)
    
    for base_norm, nights in night_allocation.items():
        base_name = city_name_map.get(base_norm, base_norm)
        print(f"  {base_name}: {nights} nights")
    print("=" * 50 + "\n")
    
    st.success(f"🏨 Base Cities ({len(base_cities)}): {' → '.join(base_cities)}")
    
    # 🚗 STEP 3: Build daily itinerary
    itinerary = []
    day_counter = 1
    pace = prefs.get("pace", "medium")
    max_same_cat = prefs.get("max_same_category_per_day", 2)
    
    # POI quota for car travel (fewer POIs, more spread out)
    POI_QUOTA_CAR = {
        "easy": 3,      # Leisurely pace
        "medium": 4,    # Balanced
        "fast": 5,      # Ambitious
    }
    poi_quota = POI_QUOTA_CAR.get(pace, 4)
    
    for idx, base_norm in enumerate(base_cities_norm):
        base_name = city_name_map.get(base_norm, base_norm)
        nights = night_allocation.get(base_norm, 1)
        base_centroid = centroids.get(base_name)
        
        print(f"\n🏨 Planning {nights} days in {base_name}...")
        
        # Get attractions within 80km radius
        nearby_attractions = get_attractions_within_radius(
            base_norm,
            filtered,
            centroids,
            max_radius_km=80
        )
        
        print(f"  Found {len(nearby_attractions)} attractions within 80km")
        
        # Day 1 at base: Explore the base city itself
        if day_counter <= days:
            base_city_attrs = [a for a in nearby_attractions if a.get('distance_from_base', 999) < 10]
            
            selected = apply_diversity(base_city_attrs, poi_quota, max_same_cat)
            
            if len(selected) < 3:
                selected = sorted(base_city_attrs, key=lambda x: x.get('rating') or 0, reverse=True)[:poi_quota]
            
            # Get hotels
            city_hotels = []
            for h in hotels:
                if cities_match(h.get("city", ""), base_name):
                    city_hotels.append(h)
            
            if not city_hotels:
                city_hotels = [{
                    "name": f"Hotels in {base_name}",
                    "city": base_name,
                    "booking_url": f"https://www.booking.com/searchresults.html?ss={quote_plus(base_name)}",
                    "airbnb_url": f"https://www.airbnb.com/s/{quote_plus(base_name)}/homes"
                }]
            
            top_hotels = sorted(city_hotels, key=lambda x: x.get("guest_rating") or x.get("star_rating") or 0, reverse=True)[:3]
            
            # Calculate if it's a driving day
            is_driving_day = idx > 0
            driving_km = 0
            driving_hours = 0
            
            if is_driving_day:
                prev_base_norm = base_cities_norm[idx - 1]
                prev_base_name = city_name_map.get(prev_base_norm, prev_base_norm)
                prev_centroid = centroids.get(prev_base_name)
                
                if prev_centroid and base_centroid:
                    driving_km = round(haversine_km(prev_centroid, base_centroid))
                    driving_hours = round(calculate_driving_time(driving_km), 1)
            
            itinerary.append({
                "day": day_counter,
                "type": "base_city" if not is_driving_day else "driving_day",
                "base": base_name,
                "city": base_name,
                "cities": [{"city": base_name, "attractions": selected}],
                "overnight_city": base_name,
                "hotels": top_hotels,
                "is_must_see": any(normalize_city_name(m) == base_norm for m in parsed_requests['must_see_cities']),
                "driving_km": driving_km if is_driving_day else 0,
                "driving_hours": driving_hours if is_driving_day else 0,
                "walking_distance_km": None
            })
            
            print(f"  Day {day_counter}: Explore {base_name} city")
            day_counter += 1
        
        
        # ✨ Remaining days: Day trips with MULTI-CITY support
        for day_at_base in range(1, nights):
            if day_counter > days:
                break
            
            # Get attractions 10-80km away (day trip range)
            day_trip_attrs = [a for a in nearby_attractions if 10 <= a.get('distance_from_base', 999) <= 80]
            
            if not day_trip_attrs:
                # No day trips available, stay in base city
                base_city_attrs = [a for a in nearby_attractions if a.get('distance_from_base', 999) < 10]
                selected = apply_diversity(base_city_attrs, poi_quota, max_same_cat)
                
                itinerary.append({
                    "day": day_counter,
                    "type": "base_city",
                    "base": base_name,
                    "city": base_name,
                    "cities": [{"city": base_name, "attractions": selected}],
                    "overnight_city": base_name,
                    "hotels": top_hotels,
                    "driving_km": 0,
                    "driving_hours": 0,
                    "walking_distance_km": None
                })
                
                print(f"  Day {day_counter}: Continue exploring {base_name}")
            else:
                # ✨ NEW: Smart multi-city day trip planning
                from collections import defaultdict
                city_groups = defaultdict(list)
                for attr in day_trip_attrs:
                    city = attr.get('city', '')
                    if city:
                        city_groups[city].append(attr)
                
                # Check if any single city has enough POIs
                single_city_ok = None
                for city, attrs in city_groups.items():
                    if len(attrs) >= poi_quota:
                        single_city_ok = (city, attrs)
                        break
                
                if single_city_ok:
                    # Single city is sufficient
                    city, attrs = single_city_ok
                    selected = apply_diversity(attrs, poi_quota, max_same_cat)
                    avg_distance = sum(a.get('distance_from_base', 0) for a in selected) / len(selected)
                    driving_km = round(avg_distance * 2)
                    driving_hours = round(calculate_driving_time(driving_km), 1)
                    
                    itinerary.append({
                        "day": day_counter,
                        "type": "day_trip",
                        "base": base_name,
                        "city": city,
                        "cities": [{"city": city, "attractions": selected}],
                        "overnight_city": base_name,
                        "hotels": top_hotels,
                        "driving_km": driving_km,
                        "driving_hours": driving_hours,
                        "walking_distance_km": None
                    })
                    
                    print(f"  Day {day_counter}: Day trip to {city} ({len(selected)} POIs)")
                
                else:
                    # ✨ COMBINE 2 CITIES!
                    sorted_cities = sorted(city_groups.items(), key=lambda x: len(x[1]), reverse=True)
                    
                    if len(sorted_cities) >= 2:
                        city1, attrs1 = sorted_cities[0]
                        city2, attrs2 = sorted_cities[1]
                        
                        # Split POI quota between cities
                        total = len(attrs1) + len(attrs2)
                        quota1 = max(2, round(poi_quota * len(attrs1) / total))
                        quota2 = poi_quota - quota1
                        
                        selected1 = apply_diversity(attrs1, min(quota1, len(attrs1)), max_same_cat)
                        selected2 = apply_diversity(attrs2, min(quota2, len(attrs2)), max_same_cat)
                        
                        # Calculate distance
                        avg1 = sum(a.get('distance_from_base', 0) for a in selected1) / max(len(selected1), 1)
                        avg2 = sum(a.get('distance_from_base', 0) for a in selected2) / max(len(selected2), 1)
                        driving_km = round((avg1 + avg2 + abs(avg1 - avg2)) * 1.5)
                        driving_hours = round(calculate_driving_time(driving_km), 1)
                        
                        itinerary.append({
                            "day": day_counter,
                            "type": "multi_city_day_trip",
                            "base": base_name,
                            "city": f"{city1} & {city2}",  # ✅ Header will show both cities!
                            "cities": [
                                {"city": city1, "attractions": selected1},
                                {"city": city2, "attractions": selected2}
                            ],
                            "overnight_city": base_name,
                            "hotels": top_hotels,
                            "driving_km": driving_km,
                            "driving_hours": driving_hours,
                            "walking_distance_km": None
                        })
                        
                        print(f"  Day {day_counter}: Multi-city - {city1} ({len(selected1)}) & {city2} ({len(selected2)})")
                    
                    elif sorted_cities:
                        # Only 1 city - use what we have
                        city, attrs = sorted_cities[0]
                        selected = apply_diversity(attrs, min(poi_quota, len(attrs)), max_same_cat)
                        avg_distance = sum(a.get('distance_from_base', 0) for a in selected) / max(len(selected), 1)
                        driving_km = round(avg_distance * 2)
                        driving_hours = round(calculate_driving_time(driving_km), 1)
                        
                        itinerary.append({
                            "day": day_counter,
                            "type": "day_trip",
                            "base": base_name,
                            "city": city,
                            "cities": [{"city": city, "attractions": selected}],
                            "overnight_city": base_name,
                            "hotels": top_hotels,
                            "driving_km": driving_km,
                            "driving_hours": driving_hours,
                            "walking_distance_km": None
                        })
                    
                    else:
                        # Fallback to base city
                        base_city_attrs = [a for a in nearby_attractions if a.get('distance_from_base', 999) < 10]
                        selected_fallback = apply_diversity(base_city_attrs, poi_quota, max_same_cat)
                        
                        itinerary.append({
                            "day": day_counter,
                            "type": "base_city",
                            "base": base_name,
                            "city": base_name,
                            "cities": [{"city": base_name, "attractions": selected_fallback}],
                            "overnight_city": base_name,
                            "hotels": top_hotels,
                            "driving_km": 0,
                            "driving_hours": 0,
                            "walking_distance_km": None
                        })
            
            day_counter += 1
    
    # Calculate route
    ordered_cities = base_cities
    hop_kms = []
    
    for i in range(len(base_cities) - 1):
        c1 = centroids.get(base_cities[i])
        c2 = centroids.get(base_cities[i+1])
        if c1 and c2:
            dist = haversine_km(c1, c2)
            hop_kms.append(round(dist) if dist and not math.isinf(dist) else None)
        else:
            hop_kms.append(None)
    
    maps_link = google_maps_link(ordered_cities)
    
    # Add restaurants
    itinerary_with_restaurants = add_restaurants_to_itinerary(
        itinerary,
        restaurants,
        budget=prefs.get('budget', 'mid-range'),
        preferences=prefs
    )
    
    return {
        "itinerary": itinerary_with_restaurants,
        "ordered_cities": ordered_cities,
        "hop_kms": hop_kms,
        "maps_link": maps_link,
        "parsed_requests": parsed_requests,
        "base_cities": base_cities,
        "is_car_mode": True
    }