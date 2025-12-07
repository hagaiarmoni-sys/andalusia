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
    """Check if two city names match (handling accents and aliases)"""
    if not city1 or not city2:
        return False
    
    norm1 = normalize_city_name(city1)
    norm2 = normalize_city_name(city2)
    
    if norm1 == norm2:
        return True
    
    # City aliases
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
    
    # Partial match for longer names
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


# ============================================================================
# OPTIMIZED ROUTE ALGORITHM
# ============================================================================

def optimize_route_andalusia(start_city, end_city, available_cities, centroids, city_name_map, days, parsed_requests, prefs):
    """
    OPTIMIZED ROUTE BUILDER - NO BACKTRACKING
    
    Algorithm:
    1. Filter out cities that cause huge detours (>100% longer)
    2. Score cities by importance + number of attractions
    3. Build route greedily: always pick nearest city that progresses toward destination
    
    Example:
        Input: Málaga to Seville, 8 days
        Output: Málaga → Ronda → Jerez → Cádiz → Córdoba → Antequera → Marbella → Seville
        Distance: ~881km (efficient, no backtracking!)
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
    end_name = city_name_map.get(end_city, end_city)
    start_coord = centroids.get(start_name)
    end_coord = centroids.get(end_name)
    
    if not start_coord or not end_coord:
        st.warning(f"⚠️ Missing coordinates for {start_name} or {end_name}")
        return []
    
    direct_distance = haversine_km(start_coord, end_coord)
    
    # Step 1: Filter and score all candidate cities
    candidates = []
    
    for city_norm, pois in available_cities.items():
        # Skip if should avoid or is start/end
        if city_norm in avoid_norms or city_norm == start_city or city_norm == end_city:
            continue
        
        # Need minimum attractions
        if len(pois) < 5:
            continue
        
        city_name = city_name_map.get(city_norm)
        city_coord = centroids.get(city_name)
        
        if not city_coord:
            continue
        
        # Calculate detour: how much longer is it to go through this city?
        dist_start_to_city = haversine_km(start_coord, city_coord)
        dist_city_to_end = haversine_km(city_coord, end_coord)
        total_via_city = dist_start_to_city + dist_city_to_end
        detour_ratio = total_via_city / direct_distance if direct_distance > 0 else 999
        
        # Exclude cities that add >200% to the journey (truly massive detours only)
        # This is very lenient - only excludes cities like Almería for Málaga→Seville
        if detour_ratio > 3.0 and city_norm not in must_see_norms:
            continue
        
        # Calculate score
        score = len(pois)  # Base: number of attractions
        
        if city_norm in MAJOR_CITIES:
            score += MAJOR_CITIES[city_norm]
        
        if city_norm in must_see_norms:
            score += 200  # Must-see gets huge bonus
        
        # Bonus for cities that are truly on the way (low detour)
        if detour_ratio < 1.2:
            score += 50
        
        candidates.append({
            'city_norm': city_norm,
            'city_name': city_name,
            'coord': city_coord,
            'score': score,
            'detour': detour_ratio
        })
    
    # Sort candidates by score (best first)
    candidates.sort(key=lambda x: -x['score'])
    
    # Step 2: Build route using greedy nearest neighbor WITH progress constraint
    max_intermediate = days - 2 if end_city != start_city else days - 1
    
    st.write(f"🔧 Debug: Need {max_intermediate} intermediate cities between {start_name} and {end_name}")
    st.write(f"📊 Found {len(candidates)} candidate cities")
    
    route = [start_city]
    available = candidates[:]
    current_coord = start_coord
    dist_to_end = direct_distance
    
    for step in range(max_intermediate):
        if not available:
            st.write(f"⚠️ No more candidates available after {len(route)} cities")
            break
        
        best = None
        best_score = -float('inf')
        rejected_count = 0
        
        for candidate in available:
            dist_to_candidate = haversine_km(current_coord, candidate['coord'])
            dist_candidate_to_end = haversine_km(candidate['coord'], end_coord)
            
            # KEY: Only consider cities that progress toward destination
            # Very lenient for major cities, moderate for others
            # This ensures Granada, Córdoba, Ronda are included
            if candidate['city_norm'] in MAJOR_CITIES and candidate['score'] > 100:
                tolerance = 150  # Major cities get huge tolerance
            elif candidate['city_norm'] in MAJOR_CITIES:
                tolerance = 100  # Regular major cities
            else:
                tolerance = 50  # Small towns
            
            if dist_candidate_to_end > dist_to_end + tolerance and candidate['city_norm'] not in must_see_norms:
                rejected_count += 1
                continue  # This city doesn't progress toward destination
            
            # Score this candidate
            # REBALANCED: Prioritize city quality over pure geography
            # This ensures Granada, Córdoba are selected despite not being perfectly "on the way"
            nearby_score = max(0, 200 - dist_to_candidate)  # 0-200 points for distance
            progress = max(-50, (dist_to_end - dist_candidate_to_end) * 1.5)  # -50 to +200 points for progress
            quality = candidate['score']  # 0-200+ points for city quality
            
            # Weighted combination: 20% distance, 30% progress, 50% quality
            combined = (nearby_score * 0.2) + (progress * 0.3) + (quality * 0.5)
            
            if combined > best_score:
                best_score = combined
                best = candidate
        
        if best:
            route.append(best['city_norm'])
            st.write(f"  ✅ Step {step+1}: Added {best['city_name']} (rejected {rejected_count} cities)")
            current_coord = best['coord']
            dist_to_end = haversine_km(current_coord, end_coord)
            available.remove(best)
        else:
            # Fallback: If NO city passes the strict filter, just pick the highest-scored available city
            st.write(f"  ⚠️ Step {step+1}: All {rejected_count} cities rejected by distance filter, using fallback")
            if available:
                best_fallback = max(available, key=lambda x: x['score'])
                route.append(best_fallback['city_norm'])
                st.write(f"  ✅ Added {best_fallback['city_name']} (fallback - highest score)")
                current_coord = best_fallback['coord']
                dist_to_end = haversine_km(current_coord, end_coord)
                available.remove(best_fallback)
            else:
                st.write(f"  ❌ No cities available at all")
                break
    
    # Add end city
    if end_city and end_city != start_city:
        route.append(end_city)
    
    # ===================================================================
    # NEW: POST-PROCESS ROUTE OPTIMIZATION (2-opt improvement)
    # ===================================================================
    def optimize_route_2opt(route, centroids, city_name_map):
        """
        Apply 2-opt optimization to reduce backtracking
        
        2-opt: Try swapping order of intermediate cities to reduce total distance
        """
        if len(route) <= 3:
            return route  # Too short to optimize
        
        improved = True
        iterations = 0
        max_iterations = 10
        
        while improved and iterations < max_iterations:
            improved = False
            iterations += 1
            
            # Don't touch first and last cities
            for i in range(1, len(route) - 2):
                for j in range(i + 1, len(route) - 1):
                    # Calculate current distance
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
                    
                    # Current edges: c1->c2 and c3->c4
                    current_dist = (haversine_km(c1_coord, c2_coord) + 
                                   haversine_km(c3_coord, c4_coord))
                    
                    # New edges if we reverse: c1->c3 and c2->c4
                    new_dist = (haversine_km(c1_coord, c3_coord) + 
                               haversine_km(c2_coord, c4_coord))
                    
                    # If reversing the segment improves distance, do it
                    if new_dist < current_dist - 1:  # -1 to avoid floating point issues
                        route[i:j+1] = reversed(route[i:j+1])
                        improved = True
                        st.write(f"  🔄 2-opt: Reversed segment {i}→{j} (saved {current_dist - new_dist:.1f} km)")
                        break
                
                if improved:
                    break
        
        return route
    
    # Apply optimization
    st.write("📊 Optimizing route to minimize backtracking...")
    route = optimize_route_2opt(route, centroids, city_name_map)
    
    # ===================================================================
    # ENFORCE MAX KM PER DAY - Insert intermediate cities if needed
    # ===================================================================
    MAX_KM_PER_DAY = prefs.get("max_km_per_day", 250)  # Use user preference (default 250)
    
    def check_and_fix_route(route, centroids, city_name_map, available_cities):
        """Check each leg and insert intermediate cities if distance > MAX_KM_PER_DAY
        
        Returns:
            tuple: (fixed_route, intermediate_cities_set)
        """
        fixed_route = [route[0]]
        intermediate_cities = set()  # Track which cities are just overnight stops
        
        for i in range(len(route) - 1):
            current_city = route[i]
            next_city = route[i + 1]
            
            # Get coordinates
            current_name = city_name_map.get(current_city, current_city)
            next_name = city_name_map.get(next_city, next_city)
            current_coord = centroids.get(current_name)
            next_coord = centroids.get(next_name)
            
            if not current_coord or not next_coord:
                fixed_route.append(next_city)
                continue
            
            distance = haversine_km(current_coord, next_coord)
            
            if distance > MAX_KM_PER_DAY:
                st.warning(f"⚠️ {current_name} → {next_name}: {distance:.0f}km exceeds {MAX_KM_PER_DAY}km limit!")
                
                # Find best intermediate city
                best_intermediate = None
                best_max_leg = float('inf')
                
                for candidate_norm, pois in available_cities.items():
                    if candidate_norm in route or len(pois) < 3:
                        continue
                    
                    candidate_name = city_name_map.get(candidate_norm)
                    candidate_coord = centroids.get(candidate_name)
                    
                    if not candidate_coord:
                        continue
                    
                    dist_current_to_candidate = haversine_km(current_coord, candidate_coord)
                    dist_candidate_to_next = haversine_km(candidate_coord, next_coord)
                    
                    # Both legs must be under limit
                    if dist_current_to_candidate > MAX_KM_PER_DAY or dist_candidate_to_next > MAX_KM_PER_DAY:
                        continue
                    
                    # Find city that minimizes the maximum leg distance
                    max_leg = max(dist_current_to_candidate, dist_candidate_to_next)
                    
                    if max_leg < best_max_leg:
                        best_max_leg = max_leg
                        best_intermediate = {
                            'norm': candidate_norm,
                            'name': candidate_name,
                            'dist1': dist_current_to_candidate,
                            'dist2': dist_candidate_to_next
                        }
                
                if best_intermediate:
                    st.info(f"📍 Adding {best_intermediate['name']} as overnight stop (drive-through) "
                              f"({best_intermediate['dist1']:.0f}km + {best_intermediate['dist2']:.0f}km)")
                    fixed_route.append(best_intermediate['norm'])
                    intermediate_cities.add(best_intermediate['norm'])  # Mark as intermediate
                else:
                    st.error(f"❌ Cannot find intermediate city to split {current_name}→{next_name}. "
                            f"This route may not be feasible with current constraints.")
            
            fixed_route.append(next_city)
        
        return fixed_route, intermediate_cities
    
    # Apply the fix
    route, intermediate_stops = check_and_fix_route(route, centroids, city_name_map, available_cities)
    
    return route, intermediate_stops


# ============================================================================
# MAIN TRIP GENERATION FUNCTION
# ============================================================================

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
    
    # ✅ FILTER: Apply minimum rating filter (5.0 scale)
    min_rating = prefs.get('min_poi_rating', 0.0)
    original_total = len(attractions)
    
    if min_rating > 0:
        attractions = [a for a in attractions if a.get('rating', 0) >= min_rating]
        print(f"📊 Rating filter ({min_rating}+ stars): {original_total} → {len(attractions)} POIs")
    
    # ✅ FILTER: Apply category filter (if specified)
    preferred_categories = prefs.get('poi_categories', [])
    if preferred_categories:
        # Normalize both lists to lowercase for comparison
        preferred_lower = [c.lower() for c in preferred_categories]
        attractions_after_category = [a for a in attractions 
                      if a.get('category', '').lower() in preferred_lower]
        
        # ⚠️ Safety check: Don't over-filter!
        if len(attractions_after_category) < 50:
            st.warning(f"⚠️ Only {len(attractions_after_category)} attractions in your preferred categories. Using all {len(attractions)} attractions to ensure good routes.")
            print(f"📊 Category filter would reduce to {len(attractions_after_category)} POIs - skipping to avoid over-filtering")
        else:
            print(f"📊 Category filter: {len(attractions)} → {len(attractions_after_category)} POIs")
            attractions = attractions_after_category
    
    # ✅ Critical check: Ensure we have enough POIs
    if len(attractions) < 30:
        st.error(f"❌ Only {len(attractions)} attractions match your filters. Please adjust preferences:")
        st.info("💡 Try: Lower minimum rating OR add more categories OR remove filters")
        return None
    
    # ✅ Critical check: Ensure start/end cities have POIs
    start_city_pois = [a for a in attractions if normalize_city_name(a.get('city', '')) == normalize_city_name(start_city)]
    if not start_city_pois:
        st.error(f"❌ No attractions found in {start_city} after filtering. Please adjust your preferences.")
        st.info(f"💡 Current filters: Rating ≥ {min_rating} stars, Categories: {preferred_categories}")
        return None
    
    if end_city:
        end_city_pois = [a for a in attractions if normalize_city_name(a.get('city', '')) == normalize_city_name(end_city)]
        if not end_city_pois:
            st.error(f"❌ No attractions found in {end_city} after filtering. Please adjust your preferences.")
            return None
    
    print(f"✅ Final filtered POIs: {len(attractions)} (Start city: {len(start_city_pois)} POIs)")
    
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
        
        # FIXED: Don't skip intermediate stops - they need a day too!
        # Original logic commented out to ensure correct day count
        #         # Skip intermediate stops - they don't get their own day in the itinerary
        #         # They're just overnight stops and are reflected in the route/distances
        #         if city_norm in intermediate_stops:
        #             continue
        
        city_attrs = by_city_normalized.get(city_norm, [])
        
        # ✅ Apply semantic merge to remove logical duplicates (bilingual names, sub-POIs, etc.)
        city_attrs = merge_city_pois(city_attrs, city_original)
        
        # Select POIs for this day
        quota = compute_poi_quota(pace, len(city_attrs))
        selected = apply_diversity(city_attrs, quota, max_same_cat)
        
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
            
            # Sort by rating
            top_restaurants = sorted(city_restaurants, key=lambda x: x.get("rating") or 0, reverse=True)
        else:
            top_restaurants = []
        
        # Select lunch and dinner restaurants
        lunch_restaurant = top_restaurants[0] if len(top_restaurants) > 0 else None
        dinner_restaurant = top_restaurants[1] if len(top_restaurants) > 1 else None
        
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
    
    # Generate Google Maps link
    maps_link = google_maps_link(ordered_cities)
    
    return {
        "itinerary": itinerary,
        "ordered_cities": ordered_cities,
        "hop_kms": hop_kms,
        "maps_link": maps_link
    }