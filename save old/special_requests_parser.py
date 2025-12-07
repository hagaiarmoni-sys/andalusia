"""
Special Requests Parser - Natural Language Processing for Trip Planning
Handles: avoid cities, must-see cities, stay duration, preferences
"""

import re
from typing import Dict, List


def parse_special_requests(special_requests: str) -> Dict:
    """
    Parse natural language special requests into structured data
    
    Examples:
        "avoid Marbella, must see Seville, stay 2 days in Malaga"
        "skip Granada, want to visit Ronda, spend 3 nights in Cadiz"
        "don't go to Cordoba, definitely see Alhambra, prefer coastal routes"
    
    Returns:
        {
            'avoid_cities': ['Marbella', 'Cordoba'],
            'must_see_cities': ['Seville', 'Ronda'],
            'stay_duration': {'Malaga': 2, 'Cadiz': 3},
            'preferences': ['coastal routes'],
            'must_see_attractions': ['Alhambra']
        }
    """
    
    if not special_requests:
        return {
            'avoid_cities': [],
            'must_see_cities': [],
            'stay_duration': {},
            'preferences': [],
            'must_see_attractions': []
        }
    
    text = special_requests.lower().strip()
    
    # Known Andalusian cities (with accent variations)
    known_cities = {
        'malaga': 'Málaga', 'málaga': 'Málaga',
        'marbella': 'Marbella',
        'granada': 'Granada',
        'seville': 'Sevilla', 'sevilla': 'Sevilla',
        'cordoba': 'Córdoba', 'córdoba': 'Córdoba',
        'cadiz': 'Cádiz', 'cádiz': 'Cádiz',
        'almeria': 'Almería', 'almería': 'Almería',
        'jerez': 'Jerez de la Frontera',
        'ronda': 'Ronda',
        'tarifa': 'Tarifa',
        'nerja': 'Nerja',
        'antequera': 'Antequera',
        'ubeda': 'Úbeda', 'úbeda': 'Úbeda',
        'jaen': 'Jaén', 'jaén': 'Jaén',
        'huelva': 'Huelva',
        'estepona': 'Estepona',
        'mijas': 'Mijas',
        'fuengirola': 'Fuengirola',
        'gibraltar': 'Gibraltar',
        'motril': 'Motril',
        'vejer': 'Vejer de la Frontera',
        'arcos': 'Arcos de la Frontera'
    }
    
    # Known attractions
    known_attractions = {
        'alhambra': 'Alhambra',
        'mezquita': 'Mezquita-Catedral de Córdoba',
        'alcazar': 'Alcázar',
        'giralda': 'La Giralda',
        'cathedral': 'Cathedral',
        'alcazaba': 'Alcazaba'
    }
    
    result = {
        'avoid_cities': [],
        'must_see_cities': [],
        'stay_duration': {},
        'preferences': [],
        'must_see_attractions': []
    }
    
    # Split into sentences for better parsing
    sentences = re.split(r'[,;.]', text)
    
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        
        # ================================================================
        # PARSE AVOID CITIES
        # ================================================================
        avoid_patterns = [
            r'avoid\s+(\w+)',
            r'skip\s+(\w+)',
            r'not\s+(\w+)',
            r"don'?t\s+(?:want\s+to\s+)?(?:go\s+to\s+|visit\s+)?(\w+)",
            r'exclude\s+(\w+)',
            r'without\s+(\w+)',
            r'no\s+(\w+)'
        ]
        
        for pattern in avoid_patterns:
            matches = re.findall(pattern, sentence)
            for match in matches:
                city = match.lower()
                if city in known_cities:
                    normalized_city = known_cities[city]
                    if normalized_city not in result['avoid_cities']:
                        result['avoid_cities'].append(normalized_city)
        
        # ================================================================
        # PARSE MUST-SEE CITIES
        # ================================================================
        must_see_patterns = [
            r'must\s+(?:see|visit)\s+(\w+)',
            r'definitely\s+(?:see|visit|go\s+to)\s+(\w+)',
            r'want\s+to\s+(?:see|visit|go\s+to)\s+(\w+)',
            r'need\s+to\s+(?:see|visit)\s+(\w+)',
            r'important\s+to\s+(?:see|visit)\s+(\w+)',
            r'(?:have\s+to|must)\s+(?:go\s+to|visit)\s+(\w+)',
            r'include\s+(\w+)',
            r'priority\s+(\w+)'
        ]
        
        for pattern in must_see_patterns:
            matches = re.findall(pattern, sentence)
            for match in matches:
                city = match.lower()
                if city in known_cities:
                    normalized_city = known_cities[city]
                    if normalized_city not in result['must_see_cities']:
                        result['must_see_cities'].append(normalized_city)
        
        # ================================================================
        # PARSE STAY DURATION
        # ================================================================
        duration_patterns = [
            r'(\d+)\s+(?:days?|nights?)\s+(?:in|at)\s+(\w+)',
            r'(?:stay|spend)\s+(\d+)\s+(?:days?|nights?)\s+(?:in|at)\s+(\w+)',
            r'(\w+)\s+for\s+(\d+)\s+(?:days?|nights?)',
            r'be\s+in\s+(\w+)\s+for\s+(\d+)\s+(?:days?|nights?)'
        ]
        
        for pattern in duration_patterns:
            matches = re.findall(pattern, sentence)
            for match in matches:
                # Handle different match orders
                if len(match) == 2:
                    # Check if first element is digit or city
                    if match[0].isdigit():
                        days, city = int(match[0]), match[1].lower()
                    else:
                        city, days = match[0].lower(), int(match[1])
                    
                    if city in known_cities:
                        normalized_city = known_cities[city]
                        result['stay_duration'][normalized_city] = days
        
        # ================================================================
        # PARSE MUST-SEE ATTRACTIONS
        # ================================================================
        attraction_patterns = [
            r'(?:must\s+see|definitely\s+see|want\s+to\s+see|visit)\s+(?:the\s+)?(\w+)',
            r'(?:include|priority)\s+(?:the\s+)?(\w+)'
        ]
        
        for pattern in attraction_patterns:
            matches = re.findall(pattern, sentence)
            for match in matches:
                attraction = match.lower()
                if attraction in known_attractions:
                    normalized_attraction = known_attractions[attraction]
                    if normalized_attraction not in result['must_see_attractions']:
                        result['must_see_attractions'].append(normalized_attraction)
        
        # ================================================================
        # PARSE GENERAL PREFERENCES
        # ================================================================
        preference_keywords = {
            'coastal': 'coastal routes',
            'coast': 'coastal routes',
            'beach': 'beach towns',
            'mountain': 'mountain routes',
            'historical': 'historical sites',
            'modern': 'modern attractions',
            'quiet': 'quiet towns',
            'lively': 'lively cities',
            'foodie': 'food experiences',
            'wine': 'wine regions',
            'hiking': 'hiking trails',
            'photography': 'photography spots',
            'family': 'family-friendly',
            'romantic': 'romantic spots',
            'budget': 'budget-friendly',
            'luxury': 'luxury experiences'
        }
        
        for keyword, preference in preference_keywords.items():
            if keyword in sentence:
                if preference not in result['preferences']:
                    result['preferences'].append(preference)
    
    return result


def validate_requests(parsed_requests: Dict) -> Dict:
    """
    Validate and resolve conflicts in special requests
    
    Returns:
        {
            'valid': bool,
            'conflicts': List[str],
            'warnings': List[str]
        }
    """
    
    conflicts = []
    warnings = []
    
    # Check for cities in both avoid and must-see
    avoid_set = set(parsed_requests['avoid_cities'])
    must_see_set = set(parsed_requests['must_see_cities'])
    
    conflicting = avoid_set.intersection(must_see_set)
    if conflicting:
        conflicts.append(f"Conflicting cities: {', '.join(conflicting)} (in both avoid and must-see)")
    
    # Check for unrealistic stay durations
    for city, days in parsed_requests['stay_duration'].items():
        if days > 7:
            warnings.append(f"{city}: {days} days is quite long - consider splitting time")
        elif days < 1:
            warnings.append(f"{city}: Stay duration must be at least 1 day")
    
    # Check if must-see cities have sufficient time
    total_must_see = len(parsed_requests['must_see_cities'])
    total_stay_days = sum(parsed_requests['stay_duration'].values())
    
    if total_must_see > 0 and total_stay_days > 0:
        if total_must_see > total_stay_days:
            warnings.append(f"You want to see {total_must_see} cities but only specified {total_stay_days} days total")
    
    return {
        'valid': len(conflicts) == 0,
        'conflicts': conflicts,
        'warnings': warnings
    }


def apply_special_requests(attractions: List[Dict], parsed_requests: Dict) -> List[Dict]:
    """
    Filter attractions based on parsed special requests
    """
    
    filtered = []
    
    for attr in attractions:
        attr_city = attr.get('city', '')
        attr_name = attr.get('name', '')
        
        # Skip avoided cities
        if parsed_requests['avoid_cities']:
            should_skip = any(
                avoid.lower() in attr_city.lower() 
                for avoid in parsed_requests['avoid_cities']
            )
            if should_skip:
                continue
        
        # Prioritize must-see cities
        is_must_see_city = any(
            must_see.lower() in attr_city.lower() 
            for must_see in parsed_requests['must_see_cities']
        )
        
        # Prioritize must-see attractions
        is_must_see_attraction = any(
            must_see.lower() in attr_name.lower() 
            for must_see in parsed_requests['must_see_attractions']
        )
        
        # Add priority flags
        attr['is_must_see_city'] = is_must_see_city
        attr['is_must_see_attraction'] = is_must_see_attraction
        attr['priority'] = (is_must_see_city * 2) + (is_must_see_attraction * 3)
        
        filtered.append(attr)
    
    # Sort by priority (highest first)
    filtered.sort(key=lambda x: x.get('priority', 0), reverse=True)
    
    return filtered


def generate_itinerary_with_constraints(
    attractions: List[Dict],
    parsed_requests: Dict,
    total_days: int,
    start_city: str,
    end_city: str
) -> List[Dict]:
    """
    Generate day-by-day itinerary respecting all constraints
    """
    
    itinerary = []
    remaining_days = total_days
    visited_cities = set()
    
    # Start with must-see cities with specified durations
    for city, days in parsed_requests['stay_duration'].items():
        if remaining_days <= 0:
            break
        
        city_attractions = [
            a for a in attractions 
            if a.get('city', '').lower() == city.lower()
        ][:days * 2]  # 2 attractions per day
        
        for day in range(min(days, remaining_days)):
            day_attractions = city_attractions[day*2:(day+1)*2]
            itinerary.append({
                'day': len(itinerary) + 1,
                'city': city,
                'attractions': day_attractions,
                'is_must_see': True
            })
        
        visited_cities.add(city.lower())
        remaining_days -= days
    
    # Add other must-see cities (1 day each if not specified)
    for city in parsed_requests['must_see_cities']:
        if city.lower() in visited_cities or remaining_days <= 0:
            continue
        
        city_attractions = [
            a for a in attractions 
            if a.get('city', '').lower() == city.lower()
        ][:2]
        
        itinerary.append({
            'day': len(itinerary) + 1,
            'city': city,
            'attractions': city_attractions,
            'is_must_see': True
        })
        
        visited_cities.add(city.lower())
        remaining_days -= 1
    
    # Fill remaining days with other high-priority attractions
    for attr in attractions:
        if remaining_days <= 0:
            break
        
        attr_city = attr.get('city', '')
        if attr_city.lower() in visited_cities:
            continue
        
        itinerary.append({
            'day': len(itinerary) + 1,
            'city': attr_city,
            'attractions': [attr],
            'is_must_see': False
        })
        
        visited_cities.add(attr_city.lower())
        remaining_days -= 1
    
    return itinerary[:total_days]