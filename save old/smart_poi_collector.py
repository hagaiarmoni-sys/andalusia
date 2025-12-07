#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Smart POI Collection System with Duplicate Detection
====================================================

✅ Merges with existing JSON file
✅ Detects duplicates by name + coordinates
✅ Only adds NEW POIs
✅ Preserves your existing data
✅ Interactive enrichment for new POIs only
"""

import requests
import json
import time
import webbrowser
import os
import math
from typing import List, Dict, Optional, Tuple
from urllib.parse import quote

# ============================================================================
# CONFIGURATION
# ============================================================================

OVERPASS_URL = "http://overpass-api.de/api/interpreter"
DUPLICATE_DISTANCE_THRESHOLD = 0.05  # km (50 meters)

# ============================================================================
# DUPLICATE DETECTION
# ============================================================================

def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance between two coordinates in kilometers using Haversine formula"""
    R = 6371  # Earth radius in km
    
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    
    a = (math.sin(dlat / 2) ** 2 + 
         math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return R * c


def normalize_name(name: str) -> str:
    """Normalize POI name for comparison"""
    import unicodedata
    
    # Remove accents
    name = unicodedata.normalize('NFKD', name)
    name = ''.join([c for c in name if not unicodedata.combining(c)])
    
    # Lowercase and remove common words
    name = name.lower()
    remove_words = ['the', 'de', 'del', 'la', 'el', 'los', 'las', 'of', 'cathedral', 'mosque', 'castle', 'palace']
    words = name.split()
    words = [w for w in words if w not in remove_words]
    
    return ' '.join(words)


def is_duplicate(new_poi: Dict, existing_pois: List[Dict]) -> Tuple[bool, Optional[Dict]]:
    """
    Check if POI already exists in the database
    
    Returns:
        (is_duplicate, matching_poi)
    """
    new_name = normalize_name(new_poi['name'])
    new_lat = new_poi['coordinates']['lat']
    new_lon = new_poi['coordinates']['lon']
    
    for existing in existing_pois:
        existing_name = normalize_name(existing['name'])
        
        # Check name similarity
        if new_name == existing_name or new_name in existing_name or existing_name in new_name:
            # Check if coordinates are close
            if 'coordinates' in existing:
                existing_lat = existing['coordinates'].get('lat')
                existing_lon = existing['coordinates'].get('lon')
                
                if existing_lat and existing_lon:
                    distance = calculate_distance(new_lat, new_lon, existing_lat, existing_lon)
                    
                    if distance < DUPLICATE_DISTANCE_THRESHOLD:
                        return True, existing
    
    return False, None


# ============================================================================
# OSM DATA COLLECTION
# ============================================================================

def get_osm_attractions(city_name: str, country: str = "España") -> List[Dict]:
    """Collect base POI data from OpenStreetMap"""
    
    query = f"""
    [out:json][timeout:30];
    area["name"="{city_name}"]["admin_level"~"[68]"]->.searchArea;
    (
      node["tourism"~"attraction|museum|artwork|viewpoint|gallery"](area.searchArea);
      way["tourism"~"attraction|museum|artwork|viewpoint|gallery"](area.searchArea);
      node["historic"~"castle|monument|memorial|archaeological_site|ruins"](area.searchArea);
      way["historic"~"castle|monument|memorial|archaeological_site|ruins"](area.searchArea);
      node["amenity"="place_of_worship"](area.searchArea);
      way["amenity"="place_of_worship"](area.searchArea);
      node["leisure"~"park|garden"](area.searchArea);
      way["leisure"~"park|garden"](area.searchArea);
    );
    out center 100;
    """
    
    print(f"🔍 Collecting from OSM: {city_name}...")
    
    try:
        response = requests.post(
            OVERPASS_URL,
            data={"data": query},
            timeout=60,
            headers={'User-Agent': 'TravelPlannerApp/1.0'}
        )
        
        if response.status_code != 200:
            print(f"  ❌ HTTP Error {response.status_code}")
            return []
        
        data = response.json()
        attractions = []
        
        for element in data.get("elements", []):
            # Get coordinates
            if element.get("type") == "node":
                lat = element.get("lat")
                lon = element.get("lon")
            else:
                center = element.get("center", {})
                lat = center.get("lat")
                lon = center.get("lon")
            
            if not lat or not lon:
                continue
            
            tags = element.get("tags", {})
            name = tags.get("name") or tags.get("name:en")
            
            if not name:
                continue
            
            attraction = {
                "name": name,
                "name_english": tags.get("name:en"),
                "city": city_name,
                "coordinates": {"lat": lat, "lon": lon},
                "category": categorize(tags),
                "subcategory": tags.get("tourism") or tags.get("historic"),
                "address": tags.get("addr:full") or tags.get("addr:street"),
                "website": tags.get("website"),
                "phone": tags.get("phone"),
                "entrance_fee": parse_fee(tags.get("fee")),
                "opening_hours": tags.get("opening_hours"),
                "wikipedia": tags.get("wikipedia"),
                "wikidata": tags.get("wikidata"),
                "tags": extract_tags(tags),
                "source": "OpenStreetMap",
                "osm_id": f"OSM_{element.get('id')}",
                # To be enriched from Google Maps
                "rating": None,
                "reviews_count": None,
                "description": None,
                "visit_duration_hours": None,
                "is_must_see": False,
                "google_maps_url": generate_google_maps_url(name, city_name)
            }
            
            attractions.append(attraction)
        
        print(f"  ✅ Found {len(attractions)} POIs from OSM")
        return attractions
        
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return []


def categorize(tags: Dict) -> str:
    """Categorize POI based on OSM tags"""
    if tags.get("historic") == "castle":
        return "Castle"
    elif tags.get("historic") in ["monument", "memorial"]:
        return "Monument"
    elif tags.get("historic") in ["archaeological_site", "ruins"]:
        return "Archaeological Site"
    elif tags.get("tourism") == "museum":
        return "Museum"
    elif tags.get("tourism") == "gallery":
        return "Art Gallery"
    elif tags.get("tourism") == "viewpoint":
        return "Viewpoint"
    elif tags.get("amenity") == "place_of_worship":
        religion = tags.get("religion", "").lower()
        if religion == "christian":
            return "Church"
        elif religion == "muslim":
            return "Mosque"
        elif religion == "jewish":
            return "Synagogue"
        return "Religious Site"
    elif tags.get("leisure") in ["park", "garden"]:
        return "Park/Garden"
    else:
        return "Attraction"


def parse_fee(fee: Optional[str]) -> str:
    """Parse entrance fee"""
    if not fee:
        return "Unknown"
    if fee.lower() in ["no", "free"]:
        return "Free"
    if fee.lower() == "yes":
        return "Paid (check locally)"
    return fee


def extract_tags(osm_tags: Dict) -> List[str]:
    """Extract relevant tags from OSM data"""
    tags = []
    
    if osm_tags.get("heritage") == "1" or "UNESCO" in osm_tags.get("name", ""):
        tags.append("UNESCO")
    
    arch_style = osm_tags.get("architecture") or osm_tags.get("architectural_style")
    if arch_style:
        tags.append(arch_style.title())
    
    if osm_tags.get("historic"):
        tags.append(osm_tags["historic"].replace("_", " ").title())
    
    return tags


def generate_google_maps_url(name: str, city: str) -> str:
    """Generate Google Maps search URL"""
    search_query = f"{name}, {city}"
    encoded = quote(search_query)
    return f"https://www.google.com/maps/search/?api=1&query={encoded}"


# ============================================================================
# FILE OPERATIONS
# ============================================================================

def load_existing_json(filename: str) -> List[Dict]:
    """Load existing POI data from JSON file"""
    if not os.path.exists(filename):
        print(f"ℹ️  No existing file found at {filename}")
        return []
    
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
            print(f"✅ Loaded {len(data)} existing POIs from {filename}")
            return data
    except Exception as e:
        print(f"❌ Error loading {filename}: {e}")
        return []


def save_to_json(data: List[Dict], filename: str):
    """Save POI data to JSON file"""
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"💾 Saved {len(data)} POIs to {filename}")


def merge_new_pois(existing: List[Dict], new_pois: List[Dict]) -> Tuple[List[Dict], List[Dict], List[Dict]]:
    """
    Merge new POIs with existing data, avoiding duplicates
    
    Returns:
        (merged_list, added_pois, duplicate_pois)
    """
    added = []
    duplicates = []
    
    for new_poi in new_pois:
        is_dup, matching = is_duplicate(new_poi, existing)
        
        if is_dup:
            duplicates.append({
                'new': new_poi,
                'existing': matching
            })
        else:
            existing.append(new_poi)
            added.append(new_poi)
    
    return existing, added, duplicates


# ============================================================================
# INTERACTIVE ENRICHMENT
# ============================================================================

def enrich_poi_interactive(poi: Dict) -> Dict:
    """Interactive tool to enrich POI with Google Maps data"""
    
    print("\n" + "="*70)
    print(f"📍 {poi['name']}")
    print(f"🏙️  {poi['city']} • {poi['category']}")
    print(f"🗺️  {poi['google_maps_url']}")
    print("="*70)
    
    # Option to open in browser
    open_browser = input("\n🌐 Open in Google Maps? (y/n/skip): ").strip().lower()
    
    if open_browser == 'skip':
        poi['enrichment_status'] = 'skipped'
        return poi
    
    if open_browser == 'y':
        webbrowser.open(poi['google_maps_url'])
        time.sleep(1)
    
    print("\n📝 Enter data from Google Maps (press Enter to skip field):\n")
    
    # Rating
    rating = input("⭐ Rating (e.g., 4.7): ").strip()
    if rating:
        try:
            poi['rating'] = float(rating)
        except:
            pass
    
    # Reviews
    reviews = input("📊 Reviews (e.g., 12543): ").strip()
    if reviews:
        try:
            poi['reviews_count'] = int(reviews.replace(',', ''))
        except:
            pass
    
    # Description
    desc = input("📄 Description: ").strip()
    if desc:
        poi['description'] = desc
    
    # Entrance fee (override if better info)
    fee = input(f"💶 Fee (current: {poi.get('entrance_fee', 'Unknown')}): ").strip()
    if fee:
        poi['entrance_fee'] = fee
    
    # Duration
    duration = input("⏱️  Duration (hours, e.g., 2): ").strip()
    if duration:
        try:
            poi['visit_duration_hours'] = float(duration)
        except:
            pass
    
    # Must-see
    must_see = input("⭐ Must-see? (y/n): ").strip().lower()
    poi['is_must_see'] = (must_see == 'y')
    
    poi['enrichment_status'] = 'complete'
    print("✅ Updated!")
    
    return poi


def batch_enrich(pois: List[Dict], auto_save_file: str) -> List[Dict]:
    """Batch enrichment with auto-save"""
    
    total = len(pois)
    print(f"\n🎯 Starting enrichment for {total} new POIs")
    print("Commands: 'skip' to skip, 'save' to save and exit\n")
    
    for i, poi in enumerate(pois):
        print(f"\n📊 Progress: {i+1}/{total}")
        
        pois[i] = enrich_poi_interactive(poi)
        
        # Auto-save every 5 POIs
        if (i + 1) % 5 == 0:
            save_to_json(pois, auto_save_file)
            print("💾 Auto-saved")
    
    return pois


# ============================================================================
# STATISTICS & REPORTING
# ============================================================================

def print_merge_report(added: List[Dict], duplicates: List[Dict]):
    """Print detailed merge report"""
    
    print("\n" + "="*70)
    print("📊 MERGE REPORT")
    print("="*70)
    print(f"✅ New POIs added:      {len(added)}")
    print(f"⚠️  Duplicates skipped:  {len(duplicates)}")
    
    if duplicates:
        print("\n🔍 Duplicate POIs found:")
        for dup in duplicates[:10]:  # Show first 10
            new_name = dup['new']['name']
            exist_name = dup['existing']['name']
            print(f"  • '{new_name}' matches existing '{exist_name}'")
        
        if len(duplicates) > 10:
            print(f"  ... and {len(duplicates) - 10} more")
    
    print("="*70)


def print_final_stats(pois: List[Dict]):
    """Print final statistics"""
    
    total = len(pois)
    enriched = sum(1 for p in pois if p.get('rating'))
    
    # By city
    cities = {}
    for poi in pois:
        city = poi.get('city', 'Unknown')
        cities[city] = cities.get(city, 0) + 1
    
    # By category
    categories = {}
    for poi in pois:
        cat = poi.get('category', 'Unknown')
        categories[cat] = categories.get(cat, 0) + 1
    
    print("\n" + "="*70)
    print("📊 FINAL DATABASE STATISTICS")
    print("="*70)
    print(f"Total POIs:        {total}")
    print(f"With ratings:      {enriched} ({enriched/total*100:.1f}%)")
    
    print("\n🏙️  By City:")
    for city, count in sorted(cities.items(), key=lambda x: -x[1])[:5]:
        print(f"  {city}: {count}")
    
    print("\n🏛️  By Category:")
    for cat, count in sorted(categories.items(), key=lambda x: -x[1])[:5]:
        print(f"  {cat}: {count}")
    
    print("="*70)


# ============================================================================
# MAIN PROGRAM
# ============================================================================

def main():
    """Main program"""
    
    print("="*70)
    print("🗺️  SMART POI COLLECTION WITH DUPLICATE DETECTION")
    print("="*70)
    
    # Get existing file path
    print("\n📂 Step 1: Load existing POI database")
    existing_file = input("Enter path to existing JSON file (or press Enter for none): ").strip()
    
    existing_pois = []
    if existing_file:
        existing_pois = load_existing_json(existing_file)
    
    # Get cities to collect
    print("\n📍 Step 2: Enter cities to collect POIs from")
    print("(Enter one per line, empty line to finish)")
    
    cities = []
    while True:
        city = input(f"  City {len(cities)+1}: ").strip()
        if not city:
            break
        cities.append(city)
    
    if not cities:
        print("❌ No cities entered. Exiting.")
        return
    
    # Collect from OSM
    print("\n🔍 Step 3: Collecting from OpenStreetMap...")
    new_pois = []
    for city in cities:
        pois = get_osm_attractions(city)
        new_pois.extend(pois)
        time.sleep(2)  # Rate limiting
    
    print(f"\n✅ Collected {len(new_pois)} POIs from OSM")
    
    # Merge with existing
    print("\n🔄 Step 4: Checking for duplicates...")
    merged, added, duplicates = merge_new_pois(existing_pois, new_pois)
    
    print_merge_report(added, duplicates)
    
    if not added:
        print("\n✅ No new POIs to add. Database is up to date!")
        return
    
    # Enrich new POIs
    print("\n📝 Step 5: Enrich new POIs with Google Maps data")
    enrich = input(f"\nEnrich {len(added)} new POIs now? (y/n): ").strip().lower()
    
    if enrich == 'y':
        enriched_added = batch_enrich(added, "pois_temp.json")
        
        # Update in merged list
        for i, poi in enumerate(merged):
            for enriched in enriched_added:
                if poi.get('osm_id') == enriched.get('osm_id'):
                    merged[i] = enriched
                    break
    
    # Save final result
    output_file = existing_file if existing_file else "pois_merged.json"
    save_to_json(merged, output_file)
    
    print_final_stats(merged)
    
    print("\n🎉 COMPLETE!")
    print(f"✅ Final database saved to: {output_file}")
    print(f"✅ Total POIs: {len(merged)}")
    print(f"✅ New POIs added: {len(added)}")


if __name__ == "__main__":
    main()
