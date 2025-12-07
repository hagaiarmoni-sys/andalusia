"""
Download ALL POI Photos Once - Save Locally
After this, Word documents can use local photos (no API calls needed!)
"""

import json
import requests
import os
from pathlib import Path
import time

GOOGLE_API_KEY = "YOUR_API_KEY_HERE"

def download_all_poi_photos():
    """
    Download all POI photos and save them locally
    Creates: /photos/ folder with images
    """
    
    print("="*80)
    print("📸 POI PHOTO DOWNLOADER")
    print("="*80)
    print("This will:")
    print("  1. Download photos for all 793 POIs")
    print("  2. Save them locally in /photos/ folder")
    print("  3. Update JSON with local photo paths")
    print("  4. Word docs will use local photos (no API needed!)")
    print("="*80)
    
    # Load POI data
    with open('andalusia_attractions_comprehensive.json', 'r', encoding='utf-8') as f:
        pois = json.load(f)
    
    # Create photos directory
    photos_dir = Path('photos')
    photos_dir.mkdir(exist_ok=True)
    
    print(f"\nProcessing {len(pois)} POIs...")
    
    downloaded_count = 0
    failed_count = 0
    no_photos_count = 0
    
    for i, poi in enumerate(pois):
        poi_name = poi.get('name', 'unknown')
        photo_refs = poi.get('photo_references', [])
        
        if not photo_refs:
            no_photos_count += 1
            continue
        
        # Create safe filename from POI name
        safe_name = "".join(c for c in poi_name if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_name = safe_name.replace(' ', '_')[:50]  # Max 50 chars
        
        # Use place_id if available (most unique)
        if poi.get('place_id'):
            safe_name = poi['place_id'][:30]
        
        print(f"[{i+1}/{len(pois)}] {poi_name[:50]}...", end=' ')
        
        # Download first photo (most representative)
        photo_ref = photo_refs[0]
        photo_filename = f"{safe_name}.jpg"
        photo_path = photos_dir / photo_filename
        
        # Skip if already downloaded
        if photo_path.exists():
            poi['local_photo_path'] = str(photo_path)
            print(f"✅ Already exists")
            downloaded_count += 1
            continue
        
        try:
            # Download photo from Google
            photo_url = "https://maps.googleapis.com/maps/api/place/photo"
            params = {
                'maxwidth': 800,  # Good quality
                'photo_reference': photo_ref,
                'key': GOOGLE_API_KEY
            }
            
            response = requests.get(photo_url, params=params, timeout=10)
            
            if response.status_code == 200:
                # Save photo locally
                with open(photo_path, 'wb') as f:
                    f.write(response.content)
                
                # Add local path to POI data
                poi['local_photo_path'] = str(photo_path)
                
                file_size = len(response.content) / 1024  # KB
                print(f"✅ {file_size:.1f} KB")
                downloaded_count += 1
            else:
                print(f"❌ HTTP {response.status_code}")
                failed_count += 1
            
            # Rate limiting (10 photos per second)
            time.sleep(0.1)
            
        except Exception as e:
            print(f"❌ Error: {e}")
            failed_count += 1
    
    # Save updated POI data with local photo paths
    output_file = 'andalusia_attractions_with_photos.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(pois, f, indent=2, ensure_ascii=False)
    
    print(f"\n{'='*80}")
    print(f"✅ Downloaded: {downloaded_count}")
    print(f"❌ Failed: {failed_count}")
    print(f"⚠️ No photos available: {no_photos_count}")
    print(f"💾 Saved POI data to: {output_file}")
    print(f"📸 Photos saved to: {photos_dir}/")
    print(f"{'='*80}")
    
    # Calculate statistics
    total_size = sum(f.stat().st_size for f in photos_dir.glob('*.jpg')) / (1024 * 1024)  # MB
    print(f"\n📊 Total photo storage: {total_size:.1f} MB")
    print(f"📊 Average photo size: {total_size / downloaded_count:.2f} MB" if downloaded_count > 0 else "")
    
    print("\n✅ Done! Now update your app:")
    print("   1. Replace: andalusia_attractions_comprehensive.json")
    print("      with:    andalusia_attractions_with_photos.json")
    print("   2. Update document_generator.py to use local_photo_path")
    print("   3. No more API calls needed for photos!")

def main():
    """
    Main execution
    """
    
    print("\n" + "="*80)
    print("🚀 ONE-TIME PHOTO DOWNLOAD")
    print("="*80)
    
    # Get API key
    global GOOGLE_API_KEY
    api_key = input("\nEnter your Google Places API key: ")
    if api_key:
        GOOGLE_API_KEY = api_key
    
    print("\n💰 Cost estimate:")
    print("   ~725 photos × 1 download = 725 photo requests")
    print("   Cost: $0 (Photo API is FREE!)")
    print("\n⏱️ Time estimate: 2-3 minutes")
    print("💾 Storage needed: ~50-100 MB")
    
    choice = input("\nContinue? (yes/no): ")
    
    if choice.lower() != 'yes':
        print("Cancelled.")
        return
    
    download_all_poi_photos()

if __name__ == "__main__":
    main()
