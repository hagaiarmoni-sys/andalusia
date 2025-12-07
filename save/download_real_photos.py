#!/usr/bin/env python3
"""
Download Real Festival Photos

This script downloads authentic photos from Unsplash API
for Andalusian festivals and events.
"""

import requests
import os
from PIL import Image
from io import BytesIO

# Create output directory
os.makedirs('event_photos_real', exist_ok=True)

# Unsplash API - Free tier, no key needed for basic searches
# Using direct photo URLs from Unsplash
REAL_PHOTOS = [
    {
        'filename': 'feria_de_abril.jpg',
        'url': 'https://images.unsplash.com/photo-1583422409516-2895a77efded?w=1600&q=80',
        'name': 'Feria de Abril',
        'search': 'feria sevilla spain fair'
    },
    {
        'filename': 'semana_santa.jpg',
        'url': 'https://images.unsplash.com/photo-1520110120835-c96534a4c984?w=1600&q=80',
        'name': 'Semana Santa',
        'search': 'holy week spain procession'
    },
    {
        'filename': 'carnaval_de_cadiz.jpg',
        'url': 'https://images.unsplash.com/photo-1519751138087-5bf79df62d5b?w=1600&q=80',
        'name': 'Carnaval',
        'search': 'carnival spain'
    },
    {
        'filename': 'festival_de_jerez.jpg',
        'url': 'https://images.unsplash.com/photo-1504609773096-104ff2c73ba4?w=1600&q=80',
        'name': 'Flamenco Festival',
        'search': 'flamenco dancer spain'
    },
    {
        'filename': 'patios_de_cordoba.jpg',
        'url': 'https://images.unsplash.com/photo-1555400038-63f5ba517a47?w=1600&q=80',
        'name': 'Patios de Córdoba',
        'search': 'cordoba patio flowers spain'
    },
    {
        'filename': 'feria_de_malaga.jpg',
        'url': 'https://images.unsplash.com/photo-1533174072545-7a4b6ad7a6c3?w=1600&q=80',
        'name': 'Málaga Fair',
        'search': 'spain festival night lights'
    },
    {
        'filename': 'bienal_de_flamenco.jpg',
        'url': 'https://images.unsplash.com/photo-1579783902614-a3fb3927b6a5?w=1600&q=80',
        'name': 'Flamenco Performance',
        'search': 'flamenco performance spain'
    },
    {
        'filename': 'cruces_de_mayo.jpg',
        'url': 'https://images.unsplash.com/photo-1490750967868-88aa4486c946?w=1600&q=80',
        'name': 'May Crosses',
        'search': 'flowers cross spain'
    },
    {
        'filename': 'romeria_del_rocio.jpg',
        'url': 'https://images.unsplash.com/photo-1464207687429-7505649dae38?w=1600&q=80',
        'name': 'Pilgrimage',
        'search': 'spain religious procession'
    },
    {
        'filename': 'feria_de_cordoba.jpg',
        'url': 'https://images.unsplash.com/photo-1555854877-bab0e564b8d5?w=1600&q=80',
        'name': 'Córdoba Fair',
        'search': 'spain fair celebration'
    },
    # Generic fallbacks
    {
        'filename': 'festival.jpg',
        'url': 'https://images.unsplash.com/photo-1533174072545-7a4b6ad7a6c3?w=1600&q=80',
        'name': 'Spanish Festival',
        'search': 'spanish festival celebration'
    },
    {
        'filename': 'flamenco.jpg',
        'url': 'https://images.unsplash.com/photo-1504609773096-104ff2c73ba4?w=1600&q=80',
        'name': 'Flamenco',
        'search': 'flamenco dancer'
    },
    {
        'filename': 'religious.jpg',
        'url': 'https://images.unsplash.com/photo-1520110120835-c96534a4c984?w=1600&q=80',
        'name': 'Religious Event',
        'search': 'spain religious procession'
    },
    {
        'filename': 'carnival.jpg',
        'url': 'https://images.unsplash.com/photo-1519751138087-5bf79df62d5b?w=1600&q=80',
        'name': 'Carnival',
        'search': 'carnival celebration'
    },
    {
        'filename': 'music.jpg',
        'url': 'https://images.unsplash.com/photo-1514320291840-2e0a9bf2a9ae?w=1600&q=80',
        'name': 'Music Festival',
        'search': 'music concert festival'
    },
    {
        'filename': 'cultural.jpg',
        'url': 'https://images.unsplash.com/photo-1555400038-63f5ba517a47?w=1600&q=80',
        'name': 'Cultural Event',
        'search': 'spain culture art'
    }
]

def download_and_optimize_photo(url, filename, max_size=(1600, 900), quality=85):
    """Download photo from URL and optimize for Word documents"""
    
    try:
        print(f"📥 Downloading: {filename}")
        
        # Download image
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        # Open image
        img = Image.open(BytesIO(response.content))
        
        # Convert to RGB if needed (some images are RGBA)
        if img.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
            img = background
        
        # Resize to fit max size while maintaining aspect ratio
        img.thumbnail(max_size, Image.Resampling.LANCZOS)
        
        # Save optimized
        output_path = f'event_photos_real/{filename}'
        img.save(output_path, 'JPEG', quality=quality, optimize=True)
        
        file_size = os.path.getsize(output_path) / 1024  # KB
        print(f"✅ Saved: {filename} ({file_size:.0f} KB)")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to download {filename}: {e}")
        return False

def main():
    """Download all festival photos"""
    
    print("📸 Downloading Real Festival Photos from Unsplash...\n")
    print("⏳ This may take a minute...\n")
    
    success_count = 0
    fail_count = 0
    
    for photo in REAL_PHOTOS:
        if download_and_optimize_photo(photo['url'], photo['filename']):
            success_count += 1
        else:
            fail_count += 1
    
    print(f"\n{'='*60}")
    print(f"✅ Successfully downloaded: {success_count} photos")
    print(f"❌ Failed: {fail_count} photos")
    print(f"📁 Location: event_photos_real/")
    print(f"{'='*60}")
    
    if success_count > 0:
        print("\n✅ NEXT STEPS:")
        print("1. Rename 'event_photos_real' folder to 'event_photos'")
        print("2. Copy to your project directory")
        print("3. Generate trip and download Word doc")
        print("4. Real festival photos will appear! 🎉")
        print("\n📸 All photos are from Unsplash (free to use)")

if __name__ == '__main__':
    main()
