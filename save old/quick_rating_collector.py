#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Quick Rating Collector for POIs
================================

FAST MODE: Only collect ratings (5-10 seconds per POI)
- Opens Google Maps
- You copy just the rating number
- Skips descriptions, fees, etc.
- Auto-saves every 5 POIs

Goal: Get ratings for all 4,086 POIs quickly, then filter for 8.5+ later
"""

import json
import webbrowser
import time
from typing import List, Dict
from urllib.parse import quote

# ============================================================================
# QUICK RATING COLLECTION
# ============================================================================

def generate_google_maps_url(name: str, city: str = "", lat: float = None, lon: float = None) -> str:
    """Generate Google Maps search URL"""
    if lat and lon:
        # Search near coordinates for better accuracy
        search_query = f"{name}, {city}"
        encoded = quote(search_query)
        return f"https://www.google.com/maps/search/{encoded}/@{lat},{lon},15z"
    else:
        search_query = f"{name}, {city}, Andalusia, Spain"
        encoded = quote(search_query)
        return f"https://www.google.com/maps/search/?api=1&query={encoded}"


def quick_rating_collect(poi: Dict) -> Dict:
    """
    Quick collection: ONLY rating
    Takes 5-10 seconds per POI
    """
    
    name = poi.get('name', 'Unknown')
    city = poi.get('city', 'Unknown')
    coords = poi.get('coordinates', {})
    lat = coords.get('lat')
    lon = coords.get('lon')
    
    # Generate URL
    gmaps_url = generate_google_maps_url(name, city, lat, lon)
    
    print("\n" + "="*70)
    print(f"📍 {name}")
    print(f"🏙️  {city}")
    print(f"🗺️  {gmaps_url}")
    print("="*70)
    
    # Option to open
    open_browser = input("\n🌐 Open? (y/enter): ").strip().lower()
    if open_browser in ['y', '']:
        webbrowser.open(gmaps_url)
        time.sleep(0.5)
    
    # ONLY ask for rating
    print("\n⚡ QUICK MODE: Just enter the rating and move on!\n")
    
    rating_input = input("⭐ Rating (e.g. 4.7, or 's' to skip): ").strip().lower()
    
    if rating_input == 's':
        poi['rating'] = None
        poi['rating_status'] = 'skipped'
    elif rating_input:
        try:
            poi['rating'] = float(rating_input)
            poi['rating_status'] = 'collected'
        except:
            print("  ⚠️  Invalid, setting to None")
            poi['rating'] = None
            poi['rating_status'] = 'error'
    else:
        poi['rating'] = None
        poi['rating_status'] = 'skipped'
    
    return poi


def batch_rating_collect(pois: List[Dict], start_index: int = 0, output_file: str = "pois_with_ratings.json") -> List[Dict]:
    """
    Batch collect ratings with auto-save
    
    Returns: (pois, last_index)
    """
    
    total = len(pois)
    
    print("\n" + "="*70)
    print("⚡ QUICK RATING COLLECTION MODE")
    print("="*70)
    print(f"Total POIs: {total}")
    print(f"Starting at: #{start_index + 1}")
    print(f"\nGoal: Add ratings to filter for 8.5+ must-sees later")
    print(f"\nSpeed: 5-10 seconds per POI")
    print(f"Total time: ~{total * 10 / 3600:.1f} hours (spread over days)")
    print("\nCommands:")
    print("  - Just enter rating (e.g., 4.7)")
    print("  - 's' to skip")
    print("  - 'save' to save and exit")
    print("  - 'quit' to exit without saving")
    print("="*70)
    
    for i in range(start_index, total):
        poi = pois[i]
        
        # Skip if already has rating
        if poi.get('rating') is not None and poi.get('rating_status') == 'collected':
            print(f"\n⏭️  Skipping #{i+1} - already has rating {poi['rating']}")
            continue
        
        print(f"\n\n📊 Progress: {i+1}/{total} ({(i+1)/total*100:.1f}%)")
        
        # Quick rating collection
        pois[i] = quick_rating_collect(poi)
        
        # Check for commands
        if poi.get('rating_status') == 'save_requested':
            print(f"\n💾 Saving progress at #{i+1}...")
            save_to_json(pois, output_file)
            return pois, i
        
        # Auto-save every 5 POIs
        if (i + 1) % 5 == 0:
            save_to_json(pois, output_file)
            print(f"\n💾 Auto-saved at #{i+1}")
    
    print("\n🎉 All POIs processed!")
    save_to_json(pois, output_file)
    return pois, total


def save_to_json(data: List[Dict], filename: str):
    """Save to JSON"""
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"✅ Saved to {filename}")


def load_from_json(filename: str) -> List[Dict]:
    """Load from JSON"""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"❌ File not found: {filename}")
        return []


def print_statistics(pois: List[Dict]):
    """Print collection statistics"""
    
    total = len(pois)
    collected = sum(1 for p in pois if p.get('rating_status') == 'collected')
    skipped = sum(1 for p in pois if p.get('rating_status') == 'skipped')
    pending = total - collected - skipped
    
    print("\n" + "="*70)
    print("📊 COLLECTION STATISTICS")
    print("="*70)
    print(f"Total POIs:        {total}")
    print(f"✅ Collected:      {collected} ({collected/total*100:.1f}%)")
    print(f"⏭️  Skipped:        {skipped} ({skipped/total*100:.1f}%)")
    print(f"⏳ Pending:        {pending} ({pending/total*100:.1f}%)")
    
    if collected > 0:
        # Rating distribution
        rated_pois = [p for p in pois if p.get('rating') is not None]
        if rated_pois:
            ratings = [p['rating'] for p in rated_pois]
            avg_rating = sum(ratings) / len(ratings)
            
            # Count high-rated (8.5+)
            high_rated = sum(1 for r in ratings if r >= 8.5)
            
            print(f"\n⭐ RATING ANALYSIS:")
            print(f"Average rating:    {avg_rating:.2f}")
            print(f"Highest rating:    {max(ratings):.1f}")
            print(f"Lowest rating:     {min(ratings):.1f}")
            print(f"🎯 8.5+ rated:     {high_rated} ({high_rated/len(ratings)*100:.1f}%)")
            print(f"\nEstimated must-sees: ~{high_rated} POIs")
    
    print("="*70)


def filter_must_see(pois: List[Dict], min_rating: float = 8.5) -> List[Dict]:
    """Filter POIs with rating >= threshold"""
    
    must_see = [p for p in pois if p.get('rating') and p['rating'] >= min_rating]
    
    print(f"\n🎯 MUST-SEE POIs (rating ≥ {min_rating}):")
    print(f"Found {len(must_see)} POIs\n")
    
    # Sort by rating
    must_see_sorted = sorted(must_see, key=lambda x: x.get('rating', 0), reverse=True)
    
    # Show top 20
    print("Top 20:")
    for i, poi in enumerate(must_see_sorted[:20], 1):
        name = poi.get('name', 'Unknown')
        city = poi.get('city', 'Unknown')
        rating = poi.get('rating', 0)
        print(f"  {i:2}. {name:40} ({city:15}) ⭐ {rating}")
    
    return must_see


# ============================================================================
# MAIN PROGRAM
# ============================================================================

def main():
    """Main program"""
    
    print("="*70)
    print("⚡ QUICK RATING COLLECTOR")
    print("="*70)
    print("\nGoal: Collect ratings for all POIs")
    print("Then: Filter 8.5+ for must-see enrichment")
    print("="*70)
    
    # Load existing POI database
    print("\n📂 Step 1: Load POI database")
    input_file = input("Enter path to POI JSON file: ").strip()
    
    if not input_file:
        print("❌ No file specified. Exiting.")
        return
    
    pois = load_from_json(input_file)
    
    if not pois:
        print("❌ Could not load POIs. Exiting.")
        return
    
    print(f"✅ Loaded {len(pois)} POIs")
    
    # Check for existing progress
    output_file = "pois_with_ratings_progress.json"
    
    # Show current stats
    print_statistics(pois)
    
    # Find last collected index
    start_idx = 0
    for i, poi in enumerate(pois):
        if poi.get('rating_status') == 'collected':
            start_idx = i + 1
    
    if start_idx > 0:
        print(f"\n📌 Resuming from #{start_idx + 1}")
    
    # Start collection
    ready = input("\n▶️  Ready to start? (y/n): ").strip().lower()
    
    if ready == 'y':
        pois, last_idx = batch_rating_collect(pois, start_idx, output_file)
        
        print_statistics(pois)
        
        # Filter must-see
        must_see = filter_must_see(pois, min_rating=8.5)
        
        # Save must-see list
        if must_see:
            save_to_json(must_see, "must_see_pois_85plus.json")
            print(f"\n✅ Must-see list saved to: must_see_pois_85plus.json")
        
        print(f"\n🎉 Complete! All data saved to: {output_file}")
    else:
        print("\n👋 Exiting without changes")


if __name__ == "__main__":
    main()
