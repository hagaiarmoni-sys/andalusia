"""
Document Helpers for Andalusia Travel App
Utility functions for document generation
"""

import unicodedata


def normalize_city_name(city_name):
    """Normalize city name for matching"""
    if not city_name:
        return ""
    import unicodedata
    city_name = str(city_name)
    nfd = unicodedata.normalize('NFD', city_name)
    without_accents = ''.join(char for char in nfd if unicodedata.category(char) != 'Mn')
    return without_accents.lower().strip()


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
    from docx.oxml.shared import OxmlElement
    from docx.oxml.ns import qn
    from docx.shared import RGBColor, Pt
    
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
    """Get city description"""
    descriptions = {
        'malaga': 'Coastal gem with museums, beaches, and vibrant culture',
        'granada': 'Home to the magnificent Alhambra palace',
        'cordoba': 'Historic city famous for the stunning Mezquita',
        'seville': 'Andalusia\'s capital, heart of flamenco and tapas',
        'cadiz': 'Ancient port city with beautiful beaches',
        'ronda': 'Dramatic clifftop town with iconic bridge',
        'jerez': 'Home of sherry wine and Andalusian horses',
        'tarifa': 'Southernmost point of Europe, windsurfing paradise'
    }
    return descriptions.get(city_norm, '')


def get_city_tips(city_norm):
    """Get city-specific tips"""
    tips = {
        'granada': [
            'Book Alhambra tickets 2-3 months in advance!',
            'Free tapas with every drink - bar hop in Albaicín',
            'Visit Mirador San Nicolás at sunset for stunning views'
        ],
        'seville': [
            'Alcázar is less crowded early morning',
            'Best tapas in Triana neighborhood',
            'Flamenco shows in Barrio Santa Cruz'
        ],
        'cordoba': [
            'Visit Mezquita early (8:30am) to avoid crowds',
            'Wander the flower-filled patios in spring',
            'Cross the Roman Bridge at sunset'
        ]
    }
    return tips.get(city_norm, [])


def get_poi_tip(poi_name):
    """Get POI-specific tip"""
    tips = {
        'alhambra': 'Book tickets online months in advance - they sell out!',
        'mezquita': 'Visit during morning prayer time (free entry 8:30-9:30am)',
        'alcazar': 'Book early morning slot to avoid crowds',
        'cathedral': 'Climb the tower for panoramic views'
    }
    
    name_lower = poi_name.lower()
    for key, tip in tips.items():
        if key in name_lower:
            return tip
    return None


def get_poi_description_fallback(name, category):
    """Generate fallback description if missing"""
    if not name:
        return "Interesting local attraction worth visiting"
    
    if category:
        return f"Notable {category.lower()} attraction in the area"
    
    return "Popular local point of interest"
