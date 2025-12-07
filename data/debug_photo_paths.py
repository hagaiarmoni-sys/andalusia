"""
Debug: Check if photos can be found for POIs in your itinerary
"""

import json
import os

# POIs from your Word doc
test_pois = [
    "Alcazaba (Málaga)",
    "Malaga Cathedral", 
    "Museo Picasso Malaga",
    "Castillo de Gibralfaro",
    "Museo del Automóvil y la Moda de Málaga"
]

print("="*80)
print("🔍 PHOTO PATH DEBUGGING")
print("="*80)

# Load POI file
poi_file = r'C:\Users\hagai\PycharmProjects\pythonProject4\andalusia-app\data\andalusia_attractions_filtered.json'
with open(poi_file, 'r', encoding='utf-8') as f:
    all_pois = json.load(f)

print(f"\nLoaded {len(all_pois)} POIs from database")

# Check photos directory
photos_dir = r'C:\Users\hagai\PycharmProjects\pythonProject4\andalusia-app\data\photos'
if os.path.exists(photos_dir):
    photo_files = [f for f in os.listdir(photos_dir) if f.endswith('.jpg')]
    print(f"✅ Photos directory exists: {len(photo_files)} photos")
else:
    print(f"❌ Photos directory NOT FOUND: {photos_dir}")

print("\n" + "="*80)
print("CHECKING SAMPLE POIs FROM YOUR DOCUMENT:")
print("="*80)

for test_name in test_pois:
    print(f"\n📍 {test_name}")
    
    # Find POI in database
    found = False
    for poi in all_pois:
        if test_name.lower() in poi.get('name', '').lower():
            found = True
            
            print(f"   ✅ Found in database: {poi.get('name')}")
            print(f"   place_id: {poi.get('place_id', 'NONE')}")
            print(f"   photo_references: {len(poi.get('photo_references', []))} refs")
            
            # Check if photo file exists
            place_id = poi.get('place_id')
            if place_id:
                # Try different path constructions
                filename = f"{place_id[:30]}.jpg"
                
                # Option 1: data/photos/
                path1 = os.path.join(r'C:\Users\hagai\PycharmProjects\pythonProject4\andalusia-app\data\photos', filename)
                # Option 2: photos/
                path2 = os.path.join(r'C:\Users\hagai\PycharmProjects\pythonProject4\andalusia-app\photos', filename)
                
                print(f"   Expected filename: {filename}")
                print(f"   Path 1 exists: {os.path.exists(path1)} ({path1})")
                print(f"   Path 2 exists: {os.path.exists(path2)} ({path2})")
                
                if os.path.exists(path1):
                    print(f"   ✅ PHOTO FOUND!")
                else:
                    print(f"   ❌ PHOTO NOT FOUND")
            else:
                print(f"   ❌ No place_id (can't find photo)")
            
            break
    
    if not found:
        print(f"   ❌ NOT FOUND in database")

print("\n" + "="*80)
print("DIAGNOSIS:")
print("="*80)

# Check document_generator location
doc_gen_locations = [
    r'C:\Users\hagai\PycharmProjects\pythonProject4\andalusia-app\document_generator.py',
    r'C:\Users\hagai\PycharmProjects\pythonProject4\andalusia-app\data\document_generator.py'
]

print("\nLooking for document_generator.py:")
for loc in doc_gen_locations:
    if os.path.exists(loc):
        print(f"   ✅ Found: {loc}")
        
        # Check if it has the photo code
        with open(loc, 'r', encoding='utf-8') as f:
            content = f.read()
            if 'place_id' in content and 'photo' in content.lower():
                print(f"      ✅ Contains photo code")
            else:
                print(f"      ❌ Does NOT contain photo code!")
    else:
        print(f"   ❌ Not found: {loc}")

print("\n" + "="*80)
