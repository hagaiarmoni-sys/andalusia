"""
Document Helpers for Andalusia Travel App
Helper functions, constants, and utilities for document generation

Split from document_generator.py for better maintainability
"""

from docx.shared import Inches, Pt, RGBColor
from docx.oxml.shared import OxmlElement
from docx.oxml.ns import qn
from urllib.parse import quote_plus
from datetime import datetime, timedelta
import unicodedata
import os

# ============================================================================
# PATH CONFIGURATION - PORTABLE (works on any computer/cloud deployment)
# ============================================================================

# Get the directory where this file is located
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Define paths relative to base directory
DATA_DIR = os.path.join(BASE_DIR, 'data')
PHOTOS_DIR = os.path.join(DATA_DIR, 'photos')
EVENT_PHOTOS_DIR = os.path.join(BASE_DIR, 'event_photos')


# ============================================================================
# AFFILIATE CONFIGURATION
# ============================================================================

# Booking.com affiliate ID (sign up at: https://partner.booking.com)
# Replace with your actual affiliate ID to earn commissions!
BOOKING_AFFILIATE_ID = "YOUR_AFFILIATE_ID"  # ⚠️ UPDATE THIS!


def get_hotel_booking_link(city_name, hotel_name=None, checkin_date=None, checkout_date=None):
    """
    Generate Booking.com affiliate link for hotel search
    
    Args:
        city_name: City to search in
        hotel_name: Optional specific hotel name
        checkin_date: Check-in date (datetime or YYYY-MM-DD string)
        checkout_date: Check-out date (datetime or YYYY-MM-DD string)
    
    Returns:
        Affiliate link URL for Booking.com
    """
    base_url = "https://www.booking.com/searchresults.html"
    
    # Build search string: hotel name + city for best results
    if hotel_name:
        search_string = f"{hotel_name} {city_name}"
    else:
        search_string = city_name
    
    # URL encode search string
    search_encoded = quote_plus(search_string)
    
    # Build parameters
    params = f"ss={search_encoded}"
    
    # Add affiliate ID if configured
    if BOOKING_AFFILIATE_ID and BOOKING_AFFILIATE_ID != "YOUR_AFFILIATE_ID":
        params += f"&aid={BOOKING_AFFILIATE_ID}"
    
    # Add dates if provided
    if checkin_date:
        if isinstance(checkin_date, datetime):
            checkin_str = checkin_date.strftime('%Y-%m-%d')
        else:
            checkin_str = str(checkin_date)
        params += f"&checkin={checkin_str}"
    
    if checkout_date:
        if isinstance(checkout_date, datetime):
            checkout_str = checkout_date.strftime('%Y-%m-%d')
        else:
            checkout_str = str(checkout_date)
        params += f"&checkout={checkout_str}"
    
    return f"{base_url}?{params}"


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def normalize_city_name(city_name):
    """Normalize city name for matching (removes accents, lowercase)"""
    if not city_name:
        return ""
    city_name = str(city_name)
    nfd = unicodedata.normalize('NFD', city_name)
    without_accents = ''.join(char for char in nfd if unicodedata.category(char) != 'Mn')
    return without_accents.lower().strip()


def generate_daily_map_url(previous_city, current_city, attractions, restaurants, is_circular=False, return_to_city=None):
    """
    Generate Google Maps directions URL with all POIs for the day
    
    Args:
        previous_city: Name of previous city (str or None)
        current_city: Name of current city (str)
        attractions: List of attraction dicts with 'name' and 'coordinates'
        restaurants: List of restaurant dicts (lunch, dinner)
        is_circular: Boolean indicating if this is a circular trip
        return_to_city: City to return to (for circular trips on last day)
    
    Returns:
        Google Maps URL string
    """
    waypoints = []
    
    # Start from previous city if this is a driving day
    if previous_city and previous_city != current_city:
        waypoints.append(previous_city)
    
    # Add all attractions
    for attr in attractions:
        name = attr.get('name', '')
        coords = attr.get('coordinates', {})
        lat = coords.get('latitude') or coords.get('lat')
        lon = coords.get('longitude') or coords.get('lon') or coords.get('lng')
        
        if lat and lon:
            waypoints.append(f"{lat},{lon}")
        elif name:
            waypoints.append(name)
    
    # Add restaurants
    for restaurant in restaurants:
        if not restaurant:
            continue
        
        address = restaurant.get('address', '')
        
        if address:
            waypoints.append(address)
        else:
            # Fallback: construct from name and city
            name = restaurant.get('name', '')
            city = restaurant.get('city', '')
            if name and city:
                waypoints.append(f"{name}, {city}, Spain")
            elif name:
                waypoints.append(name)
    
    # ✅ FIX: For circular trips, add return to start city
    if is_circular and return_to_city:
        waypoints.append(return_to_city)
    
    if not waypoints:
        return None
    
    # Build Google Maps URL
    if len(waypoints) == 1:
        # Single destination
        return f"https://www.google.com/maps/dir/?api=1&destination={quote_plus(str(waypoints[0]))}"
    else:
        # Multiple waypoints
        origin = quote_plus(str(waypoints[0]))
        destination = quote_plus(str(waypoints[-1]))
        
        if len(waypoints) > 2:
            # Add intermediate waypoints
            middle_points = waypoints[1:-1]
            waypoints_param = "|".join([quote_plus(str(wp)) for wp in middle_points])
            return f"https://www.google.com/maps/dir/?api=1&origin={origin}&destination={destination}&waypoints={waypoints_param}"
        else:
            return f"https://www.google.com/maps/dir/?api=1&origin={origin}&destination={destination}"


def add_hyperlink(paragraph, url, text):
    """
    Add a working hyperlink to a Word document paragraph
    
    Args:
        paragraph: The paragraph to add the hyperlink to
        url: The URL string
        text: The display text
    
    Returns:
        The hyperlink element
    """
    # Get the paragraph's parent part
    part = paragraph.part
    
    # Create a relationship to the URL
    r_id = part.relate_to(
        url, 
        'http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink', 
        is_external=True
    )
    
    # Create the w:hyperlink element
    hyperlink = OxmlElement('w:hyperlink')
    hyperlink.set(qn('r:id'), r_id)
    
    # Create a new run element
    new_run = OxmlElement('w:r')
    
    # Create run properties
    rPr = OxmlElement('w:rPr')
    
    # Add color
    color = OxmlElement('w:color')
    color.set(qn('w:val'), '2980B9')  # Blue color
    rPr.append(color)
    
    # Add underline
    u = OxmlElement('w:u')
    u.set(qn('w:val'), 'single')
    rPr.append(u)
    
    new_run.append(rPr)
    
    # Add the text
    text_elem = OxmlElement('w:t')
    text_elem.text = text
    new_run.append(text_elem)
    
    hyperlink.append(new_run)
    
    # Add to paragraph
    paragraph._p.append(hyperlink)
    
    return hyperlink


def get_city_prefix(city_norm):
    """Get descriptive prefix for each city"""
    prefixes = {
        'malaga': '🌊 Málaga is the vibrant gateway to the Costa del Sol, birthplace of Picasso, and a perfect blend of beaches, culture, and tapas bars.',
        'sevilla': '💃 Sevilla is the heart of Andalusia, famous for flamenco, the stunning Alcázar palace, and the world\'s largest Gothic cathedral.',
        'seville': '💃 Seville is the heart of Andalusia, famous for flamenco, the stunning Alcázar palace, and the world\'s largest Gothic cathedral.',
        'granada': '🏰 Granada is home to the breathtaking Alhambra palace, nestled at the foot of the Sierra Nevada mountains.',
        'cordoba': '🕌 Córdoba boasts the magnificent Mezquita, a stunning mosque-cathedral that showcases the city\'s Moorish heritage.',
        'cadiz': '🌅 Cádiz is one of Europe\'s oldest cities, surrounded by the Atlantic Ocean with beautiful beaches and historic old town.',
        'ronda': '🌉 Ronda sits dramatically atop a gorge with the iconic Puente Nuevo bridge connecting the old and new towns.',
        'marbella': '⛱️ Marbella is a glamorous resort town on the Costa del Sol, known for luxury yachts, beaches, and upscale dining.',
        'nerja': '🏖️ Nerja is a charming coastal town famous for the Balcón de Europa viewpoint and spectacular caves.',
        'almeria': '🏜️ Almería features unique desert landscapes, historic Alcazaba fortress, and pristine Mediterranean beaches.',
        'jerez': '🍷 Jerez de la Frontera is the home of sherry wine, flamenco culture, and the Royal Andalusian School of Equestrian Art.',
        'tarifa': '🌊 Tarifa is the southernmost point of Europe, famous for windsurfing, kitesurfing, and views of Africa across the strait.',
        'gibraltar': '🗿 Gibraltar is a British territory with the famous Rock, Barbary macaques, and stunning views of two continents.',
        'antequera': '🏛️ Antequera is known for its impressive dolmens, historic churches, and the stunning El Torcal natural park.'
    }
    return prefixes.get(city_norm, f'{city_norm.title()} is a beautiful Andalusian city worth exploring.')


def get_city_tips(city_norm):
    """Get specific travel tips for each city"""
    tips = {
        'malaga': [
            'Visit the Alcazaba fortress early morning to avoid crowds and heat',
            'The Picasso Museum offers free entry in the last 2 hours on Sundays',
            'Walk along the Muelle Uno waterfront for dining and sea views',
            'Try espeto de sardinas (grilled sardines) at beach chiringuitos'
        ],
        'sevilla': [
            'Book Alcázar tickets online in advance - they sell out days ahead',
            'Visit the Cathedral early morning or late afternoon to avoid tour groups',
            'Explore Triana neighborhood across the river for authentic flamenco bars',
            'Free entry to Cathedral on Mondays for residents (show ID)'
        ],
        'seville': [
            'Book Alcázar tickets online in advance - they sell out days ahead',
            'Visit the Cathedral early morning or late afternoon to avoid tour groups',
            'Explore Triana neighborhood across the river for authentic flamenco bars',
            'Free entry to Cathedral on Mondays for residents (show ID)'
        ],
        'granada': [
            'Book Alhambra tickets 2-3 MONTHS in advance - they sell out!',
            'Free tapas with every drink - it\'s a Granada tradition!',
            'Sunset at Mirador San Nicolás = best Alhambra views',
            'The Albaicín neighborhood is a UNESCO World Heritage site - explore on foot',
            'Take the free Alhambra bus from Plaza Nueva'
        ],
        'cordoba': [
            'Visit Mezquita at 8:30am for free entry (until 9:30am)',
            'The flower patios are most beautiful in May (festival!)',
            'Cross the Roman Bridge at sunset for amazing photos',
            'The Jewish Quarter has the best tapas and crafts'
        ],
        'cadiz': [
            'Carnival (February) is Spain\'s biggest - book months ahead!',
            'Playa La Caleta is the most scenic beach near old town',
            'Watch sunset from the seafront promenade (Malecón)',
            'Try fresh seafood at the Central Market'
        ],
        'ronda': [
            'Walk across Puente Nuevo at sunset for best photos',
            'Visit the Arab Baths - some of the best preserved in Spain',
            'The bullfighting ring is one of Spain\'s oldest and most beautiful',
            'Book a winery tour in the nearby Serranía de Ronda'
        ],
        'jerez': [
            'Sherry bodega tours usually include tastings - book ahead',
            'Royal Andalusian School of Equestrian Art shows on Tuesdays and Thursdays',
            'Visit the historic center early morning when it\'s cool',
            'Try fino sherry with jamón - the perfect pairing!'
        ],
        'marbella': [
            'Old Town (Casco Antiguo) is charming and car-free',
            'Puerto Banús for celebrity-watching and luxury shopping',
            'Beach clubs charge for sunbeds but include service',
            'Golden Mile has the best restaurants and nightlife'
        ],
        'nerja': [
            'Balcón de Europa viewpoint is stunning at sunset',
            'Book Nerja Caves tickets online to avoid queues',
            'Burriana Beach has the best chiringuitos (beach bars)',
            'Take a boat trip to see the caves from the sea'
        ],
        'tarifa': [
            'Best windsurfing/kitesurfing from April to October',
            'Take the ferry to Tangier, Morocco for a day trip',
            'Old town is tiny but charming - explore on foot',
            'Bolonia Beach has Roman ruins and massive dunes'
        ]
    }
    return tips.get(city_norm, [])


def get_poi_tip(poi_name):
    """
    Get specific tips for popular POIs
    Based on actual attractions
    """
    poi_name_lower = poi_name.lower()
    
    # Major landmarks with specific tips
    if 'alhambra' in poi_name_lower:
        return 'MUST BOOK IN ADVANCE! Tickets sell out 2-3 months ahead. Book Nasrid Palaces time slot carefully - you cannot enter before your slot. Allow 3-4 hours for full visit.'
    elif 'mezquita' in poi_name_lower:
        return 'Free entry 8:30-9:30am (Mon-Sat). The forest of columns is breathtaking - allow 1-2 hours. Don\'t miss the hidden cathedral in the center!'
    elif 'alcazar' in poi_name_lower and 'seville' in poi_name_lower:
        return 'Book tickets online to skip the queue. The gardens are as impressive as the palace. Allow 2-3 hours for full visit.'
    elif 'alcazar' in poi_name_lower:
        return 'Book tickets online to skip the queue. Allow 2-3 hours to explore fully.'
    elif 'cathedral' in poi_name_lower and 'seville' in poi_name_lower:
        return 'World\'s largest Gothic cathedral! Climb the Giralda tower for panoramic views. Free entry Mondays (for residents).'
    elif 'giralda' in poi_name_lower:
        return 'The bell tower has 35 ramps (not stairs!) - horses used to climb it! Best views of Seville from the top.'
    elif 'puente nuevo' in poi_name_lower or 'new bridge' in poi_name_lower:
        return 'Best photos from the viewing platforms below the bridge. Sunset is magical. There\'s a small museum inside the bridge.'
    elif 'caminito del rey' in poi_name_lower:
        return 'MUST BOOK IN ADVANCE! Wear comfortable shoes. The walkway is one-way and takes 3-4 hours. Stunning but not for those afraid of heights!'
    elif 'picasso' in poi_name_lower:
        return 'Free entry last 2 hours on Sundays. Allow 1.5-2 hours for the full collection.'
    elif 'alcazaba' in poi_name_lower:
        return 'Visit early morning to avoid heat. Great views from the top - bring water and sun protection.'
    elif 'plaza' in poi_name_lower or 'square' in poi_name_lower:
        return 'Best visited during golden hour (sunset) for photos. Enjoy a coffee at a terrace café to soak in the atmosphere.'
    elif 'mirador' in poi_name_lower or 'viewpoint' in poi_name_lower:
        return 'Visit at sunset for magical views and photo opportunities. Can get crowded - arrive 30 minutes early.'
    elif 'beach' in poi_name_lower or 'playa' in poi_name_lower:
        return 'Pack sunscreen, water, and arrive early for best spots. Beach restaurants (chiringuitos) serve fresh seafood.'
    elif 'market' in poi_name_lower or 'mercado' in poi_name_lower:
        return 'Visit in the morning when produce is freshest. Great place to sample local foods and buy souvenirs.'
    elif 'garden' in poi_name_lower or 'jardin' in poi_name_lower:
        return 'Best visited in spring for flowers or early morning for peaceful atmosphere. Bring camera!'
    elif 'museum' in poi_name_lower or 'museo' in poi_name_lower:
        return 'Check for free entry days. Audio guides often available. Photography rules vary - check before snapping.'
    else:
        return None


def get_poi_description_fallback(poi_name, category):
    """
    Generate fallback descriptions for POIs without descriptions
    Based on category and name
    """
    if not category:
        category = "attraction"
    
    cat_lower = category.lower().strip()
    
    # Category-based templates
    category_descriptions = {
        'museum': f"A museum showcasing art, culture, and history. {poi_name} offers interesting exhibitions and collections worth exploring.",
        'museums': f"A museum showcasing art, culture, and history. {poi_name} offers interesting exhibitions and collections worth exploring.",
        'art': f"An art gallery featuring works from various artists and periods. {poi_name} is a must-visit for art enthusiasts.",
        'history': f"A historic site that tells the story of the region's past. {poi_name} provides fascinating insights into local heritage.",
        'architecture': f"An architectural landmark showcasing beautiful design and construction. {poi_name} is a stunning example of the region's architectural heritage.",
        'parks': f"A green space perfect for relaxation and outdoor activities. {poi_name} offers a peaceful escape from the city bustle.",
        'nature': f"A natural attraction featuring beautiful landscapes and scenery. {poi_name} is ideal for nature lovers and photographers.",
        'gardens': f"Beautiful gardens featuring diverse plants and landscaping. {poi_name} is perfect for a leisurely stroll.",
        'beaches': f"A coastal area with sand and sea. {poi_name} is great for swimming, sunbathing, and water activities.",
        'viewpoints': f"A scenic viewpoint offering panoramic vistas. {poi_name} provides stunning photo opportunities, especially at sunset.",
        'markets': f"A local market where you can find fresh produce, crafts, and local specialties. {poi_name} offers an authentic taste of local life.",
        'religious': f"A religious building of cultural and historical significance. {poi_name} features beautiful architecture and spiritual atmosphere.",
        'castles': f"A historic fortress showcasing medieval architecture and military history. {poi_name} offers great views and fascinating stories.",
        'palaces': f"A grand palace featuring opulent rooms and beautiful gardens. {poi_name} showcases the luxury and artistry of past eras.",
        'neighborhoods': f"A charming neighborhood with local character and atmosphere. {poi_name} is perfect for exploring on foot and discovering hidden gems.",
        'food & tapas': f"A culinary destination known for local food and flavors. {poi_name} is ideal for tasting authentic Andalusian cuisine.",
        'wine & bodegas': f"A winery or bodega offering wine tasting and tours. {poi_name} showcases the region's winemaking traditions.",
        'music & flamenco': f"A venue celebrating music and dance culture. {poi_name} offers authentic performances and cultural experiences.",
    }
    
    # Try to get category-specific description
    description = category_descriptions.get(cat_lower)
    
    # If no match, create generic description
    if not description:
        description = f"A notable {category} attraction in the area. {poi_name} is worth visiting to experience local culture and sights."
    
    return description


# ============================================================================
# FOOD DATA (used by document generator)
# ============================================================================

ANDALUSIAN_DISHES = [
    ('🥘 Gazpacho', 'Cold tomato soup, perfect for hot days - originated right here in Andalusia'),
    ('🍲 Salmorejo', 'Thick, creamy cold soup from Córdoba, topped with egg and jamón'),
    ('🥓 Jamón Ibérico', 'Premium cured ham from acorn-fed pigs - the best in Spain!'),
    ('🐟 Pescaíto Frito', 'Fried fish platter, a coastal specialty in Málaga and Cádiz'),
    ('🍖 Rabo de Toro', 'Oxtail stew, traditional in Córdoba (especially after bullfights)'),
    ('🥚 Tortilla Española', 'Classic Spanish potato omelet - simple but delicious'),
    ('🐟 Espeto de Sardinas', 'Grilled sardines on a stick, Málaga beach specialty'),
    ('🥖 Flamenquín', 'Rolled pork filled with ham and cheese, breaded and fried'),
    ('🥪 Pringá', 'Slow-cooked meat sandwich, popular in Seville'),
    ('🍩 Churros con Chocolate', 'Fried dough with thick hot chocolate for dipping'),
    ('🍷 Sherry Wine', 'From Jerez - try fino, manzanilla, or sweet Pedro Ximénez'),
    ('🥣 Ajo Blanco', 'Cold white soup with almonds and grapes, from Málaga')
]


# ============================================================================
# DRIVING TIPS DATA (used by document generator)
# ============================================================================

DRIVING_BASICS = [
    '🚗  Drive on the RIGHT side of the road',
    '🚦  Speed limits: 120 km/h (highways), 90 km/h (rural), 50 km/h (cities)',
    '🚫  Right-of-way: Traffic from right has priority',
    '📱  Using phones while driving is ILLEGAL (€200 fine!)',
    '🍺  Blood alcohol limit: 0.5g/l (0.25g/l for new drivers)',
    '👶  Children under 135cm MUST use car seats',
    '🔺  Required: 2 warning triangles, reflective vest, spare tire',
    '💡  Headlights required in tunnels and at night'
]

TOLL_TIPS = [
    '🛣️  Autopistas (AP-) are TOLL roads, Autovías (A-) are FREE',
    '💳  Most toll booths accept credit cards (Visa/Mastercard)',
    '🧾  Typical tolls: Málaga↔Seville ~€15-20',
    '⛽  Gas stations (gasolineras) are frequent on highways',
    '💳  Most accept credit cards, some require chip & PIN',
    '⛽  Fuel types: Gasolina 95 (regular), Gasolina 98 (premium), Diesel',
    '📱  Apps: Google Maps or Waze for cheapest fuel nearby'
]

PARKING_COLORS = {
    'blue': ('🔵 BLUE ZONE', 'Paid parking - usually €1-2/hour, max 2 hours'),
    'green': ('🟢 GREEN ZONE', 'Residents only OR paid (check signs carefully!)'),
    'yellow': ('🟡 YELLOW LINE', 'No parking at any time'),
    'white': ('⚪ WHITE LINE', 'Free parking (rare in city centers)')
}

EMERGENCY_NUMBERS = [
    ('🚨 Emergency (all)', '112'),
    ('🚔 Police (Policía Nacional)', '091'),
    ('🚔 Local Police (Policía Local)', '092'),
    ('🚒 Fire (Bomberos)', '080'),
    ('🚑 Medical Emergency', '061'),
    ('🚗 Roadside Assistance', '+34 900 123 505')
]
