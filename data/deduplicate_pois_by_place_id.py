"""
Deduplicate POI JSON file using place_id
This permanently removes duplicates from your data
"""

import json

def deduplicate_poi_file(input_file, output_file):
    """
    Remove duplicate POIs using place_id as unique identifier
    """
    
    print("="*80)
    print("🔧 POI DEDUPLICATION TOOL (by place_id)")
    print("="*80)
    
    # Load POI file
    with open(input_file, 'r', encoding='utf-8') as f:
        pois = json.load(f)
    
    print(f"\n📊 Original POIs: {len(pois)}")
    
    # Track statistics
    seen_place_ids = set()
    seen_names_without_id = set()
    unique_pois = []
    duplicates_by_place_id = []
    duplicates_by_name = []
    no_place_id = []
    
    for poi in pois:
        place_id = poi.get('place_id')
        name = poi.get('name', '').lower().strip()
        
        if place_id:
            # Has place_id - use it as unique identifier
            if place_id not in seen_place_ids:
                seen_place_ids.add(place_id)
                unique_pois.append(poi)
            else:
                duplicates_by_place_id.append(poi)
                print(f"   ❌ Duplicate (place_id): {poi.get('name')}")
        else:
            # No place_id - fallback to name-based deduplication
            no_place_id.append(poi)
            
            # Normalize name (remove accents, special chars)
            import unicodedata
            normalized = ''.join(
                c for c in unicodedata.normalize('NFD', name)
                if unicodedata.category(c) != 'Mn'
            )
            normalized = ''.join(c for c in normalized if c.isalnum())
            
            if normalized not in seen_names_without_id:
                seen_names_without_id.add(normalized)
                unique_pois.append(poi)
            else:
                duplicates_by_name.append(poi)
                print(f"   ⚠️ Duplicate (no place_id): {poi.get('name')}")
    
    # Save deduplicated file
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(unique_pois, f, indent=2, ensure_ascii=False)
    
    print(f"\n{'='*80}")
    print("RESULTS:")
    print("="*80)
    print(f"✅ Unique POIs: {len(unique_pois)}")
    print(f"❌ Duplicates (by place_id): {len(duplicates_by_place_id)}")
    print(f"⚠️ Duplicates (by name, no place_id): {len(duplicates_by_name)}")
    print(f"📝 POIs without place_id: {len(no_place_id)}")
    print(f"\n📊 Removed: {len(pois) - len(unique_pois)} duplicates")
    print(f"💾 Saved to: {output_file}")
    
    # Show sample duplicates
    if duplicates_by_place_id:
        print(f"\n{'='*80}")
        print("SAMPLE DUPLICATES REMOVED:")
        print("="*80)
        for dup in duplicates_by_place_id[:10]:
            print(f"  • {dup.get('name')} ({dup.get('city')})")
            print(f"    place_id: {dup.get('place_id')}")
    
    return unique_pois, len(pois) - len(unique_pois)

if __name__ == "__main__":
    input_file = r'C:\Users\hagai\PycharmProjects\pythonProject4\andalusia-app\data\andalusia_attractions_filtered.json'
    output_file = r'C:\Users\hagai\PycharmProjects\pythonProject4\andalusia-app\data\andalusia_attractions_deduplicated.json'
    
    print("\n⚠️ This will create a deduplicated version of your POI file")
    print(f"Input:  {input_file}")
    print(f"Output: {output_file}")
    
    choice = input("\nContinue? (yes/no): ")
    
    if choice.lower() == 'yes':
        unique_pois, removed = deduplicate_poi_file(input_file, output_file)
        
        print(f"\n{'='*80}")
        print("NEXT STEPS:")
        print("="*80)
        print("1. Review the deduplicated file")
        print("2. If it looks good, replace the original:")
        print(f"   copy {input_file} {input_file}.backup")
        print(f"   move {output_file} {input_file}")
        print("\n✅ Done!")
    else:
        print("Cancelled.")
