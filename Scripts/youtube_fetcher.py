"""
YouTube Short Video Fetcher for Andalusia Travel App
Fetches 1-4 minute 4K videos for each destination in SPAIN (Andalusia)

FIXES:
- All queries include "Spain" or "Andalusia" to avoid Argentina/other locations
- Prioritizes 4K content
- Better filtering of irrelevant results
"""

import urllib.request
import urllib.parse
import json
import time

# YouTube Data API endpoint
YOUTUBE_API_BASE = "https://www.googleapis.com/youtube/v3/search"

# ============================================================================
# DESTINATIONS - All queries now include Spain/Andalusia + 4K
# ============================================================================

DESTINATIONS = {
    # Major Cities - Always include "Spain" and prefer "4K"
    "Seville": [
        "Seville Spain 4K drone",
        "Sevilla España 4K walking tour",
        "Seville Andalusia travel 4K"
    ],
    "Granada": [
        "Granada Spain 4K drone",
        "Alhambra Granada 4K tour",
        "Granada Andalusia 4K walking"
    ],
    "Córdoba": [
        "Córdoba Spain 4K drone",           # ✅ "Spain" to exclude Argentina
        "Mezquita Córdoba España 4K",
        "Cordoba Andalusia 4K tour"
    ],
    "Málaga": [
        "Málaga Spain 4K drone",
        "Malaga Costa del Sol 4K",
        "Málaga Andalusia walking tour 4K"
    ],
    "Ronda": [
        "Ronda Spain 4K drone",
        "Ronda Puente Nuevo 4K",
        "Ronda Andalusia drone 4K"
    ],
    "Cádiz": [
        "Cádiz Spain 4K drone",
        "Cadiz Andalusia 4K tour",
        "Cádiz España drone 4K"
    ],
    "Jerez": [
        "Jerez de la Frontera Spain 4K",
        "Jerez horses sherry Spain",
        "Jerez Andalusia 4K"
    ],
    
    # White Villages (Pueblos Blancos)
    "Arcos de la Frontera": [
        "Arcos de la Frontera Spain 4K drone",
        "Arcos de la Frontera Andalusia"
    ],
    "Zahara de la Sierra": [
        "Zahara de la Sierra Spain 4K drone",
        "Zahara de la Sierra Andalusia 4K"
    ],
    "Grazalema": [
        "Grazalema Spain 4K",
        "Grazalema Andalusia drone"
    ],
    "Setenil de las Bodegas": [
        "Setenil de las Bodegas Spain 4K",
        "Setenil cave houses Spain"
    ],
    "Frigiliana": [
        "Frigiliana Spain 4K drone",
        "Frigiliana Málaga 4K"
    ],
    "Mijas": [
        "Mijas pueblo Spain 4K",
        "Mijas Costa del Sol drone"
    ],
    "Olvera": [
        "Olvera Spain 4K drone",
        "Olvera Andalusia white village"
    ],
    
    # Major Attractions
    "Alhambra": [
        "Alhambra Granada 4K tour",
        "Alhambra palace Spain 4K drone",
        "Alhambra Nasrid palaces 4K"
    ],
    "Caminito del Rey": [
        "Caminito del Rey 4K drone",
        "Caminito del Rey Spain walk 4K",
        "El Chorro Málaga 4K"
    ],
    "Alcázar Seville": [
        "Real Alcázar Seville 4K",
        "Alcazar Sevilla Spain 4K tour",
        "Seville palace 4K drone"
    ],
    "Mezquita": [
        "Mezquita Córdoba Spain 4K",        # ✅ "Spain" is key here
        "Mosque Cathedral Cordoba 4K",
        "Mezquita interior 4K tour"
    ],
    
    # Nature
    "Sierra Nevada": [
        "Sierra Nevada Granada Spain 4K",   # ✅ "Granada Spain" to avoid USA
        "Sierra Nevada Andalusia 4K drone",
        "Sierra Nevada España skiing"
    ],
    "Doñana": [
        "Doñana National Park Spain 4K",
        "Doñana Andalusia wildlife",
        "Parque Nacional Doñana 4K"
    ],
    "El Torcal": [
        "El Torcal Antequera 4K",
        "Torcal de Antequera Spain drone",
        "El Torcal Málaga 4K"
    ],
    "Cabo de Gata": [
        "Cabo de Gata Almería 4K drone",
        "Cabo de Gata Spain beaches 4K"
    ],
    "Nerja": [
        "Nerja Spain 4K drone",
        "Nerja caves 4K tour",
        "Nerja Costa del Sol 4K"
    ],
}


def fetch_short_videos(api_key: str, query: str, max_results: int = 3) -> list:
    """
    Fetch short videos (1-4 minutes) from YouTube
    
    videoDuration options:
    - 'short': < 4 minutes
    - 'medium': 4-20 minutes  
    - 'long': > 20 minutes
    """
    params = {
        'part': 'snippet',
        'q': query,
        'type': 'video',
        'videoDuration': 'short',  # Under 4 minutes
        'order': 'relevance',      # Changed from viewCount for better relevance
        'maxResults': max_results,
        'key': api_key,
        'regionCode': 'ES',        # Spain region
        'relevanceLanguage': 'en', # English preferred
        'videoDefinition': 'high', # HD/4K only
    }
    
    url = f"{YOUTUBE_API_BASE}?{urllib.parse.urlencode(params)}"
    
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            data = json.loads(response.read().decode())
            
        videos = []
        for item in data.get('items', []):
            video_id = item['id']['videoId']
            title = item['snippet']['title']
            channel = item['snippet']['channelTitle']
            
            # ✅ FILTER: Skip videos that are clearly wrong location
            title_lower = title.lower()
            channel_lower = channel.lower()
            
            # Skip Argentina, USA, or other wrong locations
            skip_keywords = [
                'argentina', 'buenos aires', 'mendoza',  # Argentina
                'california', 'nevada usa', 'las vegas', # USA
                'mexico', 'colombia', 'chile',           # Other Spanish-speaking
                'laliga', 'fc barcelona', 'real madrid', 'sevilla fc',  # Sports
                'highlights', 'resumen', 'gol', 'match', 'partido',
                'basketball', 'padel', 'futbol', 'football',
                'noticias', 'news', 'polemic',
            ]
            
            if any(kw in title_lower or kw in channel_lower for kw in skip_keywords):
                continue
            
            # ✅ BOOST: Prefer videos with these keywords
            boost_keywords = ['spain', 'españa', 'andalusia', 'andalucia', '4k', 'drone', 
                            'walking tour', 'travel', 'visit']
            has_boost = any(kw in title_lower for kw in boost_keywords)
            
            video_data = {
                'title': title,
                'video_id': video_id,
                'channel': channel,
                'thumbnail_url': item['snippet']['thumbnails']['high']['url'],
                'watch_url': f"https://www.youtube.com/watch?v={video_id}",
                'embed_url': f"https://www.youtube.com/embed/{video_id}",
                'short_embed': f"https://youtu.be/{video_id}",
                'has_boost': has_boost,
            }
            
            # Add boosted videos first
            if has_boost:
                videos.insert(0, video_data)
            else:
                videos.append(video_data)
        
        return videos
        
    except urllib.error.HTTPError as e:
        print(f"HTTP Error for '{query}': {e.code} - {e.reason}")
        return []
    except Exception as e:
        print(f"Error fetching videos for '{query}': {e}")
        return []


def fetch_all_destinations(api_key: str) -> dict:
    """Fetch videos for all destinations with rate limiting"""
    results = {}
    total = len(DESTINATIONS)
    
    for idx, (destination, queries) in enumerate(DESTINATIONS.items(), 1):
        print(f"[{idx}/{total}] Fetching videos for: {destination}")
        destination_videos = []
        
        for query in queries:
            videos = fetch_short_videos(api_key, query, max_results=3)
            destination_videos.extend(videos)
            
            # Rate limiting - don't hit API too fast
            time.sleep(0.2)
        
        # Remove duplicates by video_id, keep boosted ones first
        seen = set()
        unique_videos = []
        
        # First pass: boosted videos
        for v in destination_videos:
            if v['video_id'] not in seen and v.get('has_boost'):
                seen.add(v['video_id'])
                # Remove the boost flag before saving
                v.pop('has_boost', None)
                unique_videos.append(v)
        
        # Second pass: non-boosted videos
        for v in destination_videos:
            if v['video_id'] not in seen:
                seen.add(v['video_id'])
                v.pop('has_boost', None)
                unique_videos.append(v)
        
        # Keep top 3 unique videos
        results[destination] = unique_videos[:3]
        
        if unique_videos:
            print(f"   ✅ Found {len(unique_videos)} videos")
        else:
            print(f"   ⚠️ No suitable videos found")
    
    return results


def generate_json_database(api_key: str, output_file: str = "youtube_videos_db.json"):
    """Generate a JSON database of videos for all destinations"""
    print("=" * 60)
    print("YOUTUBE VIDEO FETCHER - Andalusia Spain (4K preferred)")
    print("=" * 60)
    print()
    
    all_videos = fetch_all_destinations(api_key)
    
    output = {
        "metadata": {
            "description": "Short YouTube videos (under 4 min, 4K preferred) for Andalusia SPAIN destinations",
            "video_duration": "short (< 4 minutes)",
            "video_quality": "HD/4K preferred",
            "region": "Andalusia, Spain",
            "generated_by": "youtube_fetcher.py",
            "note": "Filtered to exclude Argentina, USA, and sports content"
        },
        "destinations": all_videos
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    total_videos = sum(len(v) for v in all_videos.values())
    print()
    print("=" * 60)
    print(f"✅ Saved {total_videos} videos for {len(all_videos)} destinations")
    print(f"📄 Output file: {output_file}")
    print("=" * 60)
    
    return output_file


# ============================================================================
# MANUAL SEARCH URLs (without API key)
# ============================================================================

def get_manual_search_urls() -> dict:
    """
    Generate YouTube search URLs for manual curation
    Use these to find videos manually without API key
    """
    search_urls = {}
    
    base_url = "https://www.youtube.com/results?"
    
    for destination, queries in DESTINATIONS.items():
        urls = []
        for query in queries:
            # sp=EgIYAQ%3D%3D = "Under 4 minutes" filter
            # sp=EgJAAQ%3D%3D = "4K" filter
            # Combined would need different approach
            params = {
                'search_query': query,
                'sp': 'EgIYAQ%3D%3D'  # Under 4 minutes filter
            }
            url = base_url + urllib.parse.urlencode(params)
            urls.append({
                'query': query,
                'search_url': url
            })
        search_urls[destination] = urls
    
    return search_urls


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    import sys
    
    # Check for API key as argument or environment variable
    API_KEY = None
    
    if len(sys.argv) > 1:
        API_KEY = sys.argv[1]
    else:
        import os
        API_KEY = os.environ.get('YOUTUBE_API_KEY')
    
    if API_KEY:
        print(f"Using API key: {API_KEY[:10]}...")
        generate_json_database(API_KEY, "data/youtube_videos_db.json")
    else:
        print("=" * 60)
        print("YOUTUBE VIDEO FETCHER - Manual Mode")
        print("=" * 60)
        print()
        print("No API key provided. Generating manual search URLs...")
        print()
        print("To use with API key, run:")
        print("  python youtube_fetcher.py YOUR_API_KEY")
        print()
        print("Or set environment variable:")
        print("  export YOUTUBE_API_KEY=your_key")
        print("  python youtube_fetcher.py")
        print()
        
        search_urls = get_manual_search_urls()
        
        # Save search URLs
        with open("youtube_search_urls.json", 'w', encoding='utf-8') as f:
            json.dump(search_urls, f, indent=2, ensure_ascii=False)
        
        print("Sample search URLs (filtered for videos under 4 minutes):")
        print("-" * 60)
        
        for dest in ["Córdoba", "Seville", "Alhambra", "Sierra Nevada"]:
            if dest in search_urls:
                print(f"\n📍 {dest}:")
                for item in search_urls[dest][:2]:
                    print(f"   🔍 {item['query']}")
        
        print()
        print(f"📄 Full list saved to: youtube_search_urls.json")
