"""
Surgical Duplicate Remover - Removes only specific known duplicates
This is the final, precise solution
"""
import json

def remove_specific_duplicates(data):
    """
    Remove specific duplicates by exact name matching
    """
    
    print(f"Starting with {len(data)} POIs")
    print()
    
    # Define exact duplicates to remove (by name)
    duplicates_to_remove = [
        # Seville Cathedral duplicate
        "Catedral de Sevilla",
        
        # Córdoba Mosque-Cathedral duplicate  
        "Mezquita-Catedral de Córdoba",
        
        # Any other specific duplicates you know about
        # Add them here in the format: "Exact Name",
    ]
    
    removed = []
    cleaned = []
    
    for poi in data:
        name = poi.get('name', '')
        
        if name in duplicates_to_remove:
            removed.append(poi)
            print(f"❌ REMOVED: {name} (Rating: {poi.get('rating')}, City: {poi.get('city')})")
        else:
            cleaned.append(poi)
    
    print()
    print("=" * 70)
    print(f"✅ Removed {len(removed)} specific duplicates")
    print(f"📊 Final count: {len(cleaned)} unique POIs")
    
    return cleaned

def main():
    input_file = "data/andalusia_attractions_filtered.json"
    output_file = "data/andalusia_attractions_filtered.json"
    backup_file = "data/andalusia_attractions_BEFORE_SURGICAL.json"
    
    print(f"📂 Loading: {input_file}")
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Backup
    print(f"💾 Backup: {backup_file}")
    with open(backup_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    # Remove specific duplicates
    cleaned = remove_specific_duplicates(data)
    
    # Save
    print(f"\n💾 Saving: {output_file}")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(cleaned, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Done! Saved {len(cleaned)} POIs")
    
    # Verify
    print("\n" + "=" * 70)
    print("FINAL VERIFICATION:")
    print("=" * 70)
    
    # Check Seville Cathedrals
    seville_cats = [p for p in cleaned 
                    if 'cathedral' in p.get('name', '').lower()
                    and ('seville' in p.get('name', '').lower() 
                         or 'sevilla' in p.get('name', '').lower()
                         or p.get('city', '') == 'Seville')]
    
    print(f"\n📍 Seville Cathedral entries: {len(seville_cats)}")
    for cat in seville_cats:
        print(f"   - {cat.get('name')} (Rating: {cat.get('rating')})")
    
    # Check Córdoba
    cordoba = [p for p in cleaned 
               if 'mosque' in p.get('name', '').lower() 
               and 'cathedral' in p.get('name', '').lower()]
    
    print(f"\n📍 Córdoba Mosque-Cathedral entries: {len(cordoba)}")
    for cat in cordoba:
        print(f"   - {cat.get('name')} (Rating: {cat.get('rating')})")
    
    if len(seville_cats) == 1 and len(cordoba) == 1:
        print("\n🎉 PERFECT! Only one of each remains!")
    else:
        print(f"\⚠️ Status: {len(seville_cats)} Seville, {len(cordoba)} Córdoba")

if __name__ == "__main__":
    main()
