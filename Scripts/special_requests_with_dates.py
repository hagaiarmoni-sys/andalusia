# Enhanced Special Requests Parser with Date Support

import re
from datetime import datetime
from typing import Dict, List, Optional

def parse_special_requests_with_dates(request_text: str) -> Dict:
    """
    Enhanced parser that handles:
    - "Must visit Seville"
    - "Stay 2 nights in Granada" 
    - "Must see Seville on 09-Feb-2026" ← NEW!
    - "Be in Granada for Festival on April 15"
    
    Returns:
        {
            'must_see_cities': ['Seville', 'Granada'],
            'avoid_cities': ['Málaga'],
            'stay_duration': {'Granada': 2},
            'date_constraints': [  ← NEW!
                {
                    'city': 'Seville',
                    'date': '2026-02-09',
                    'reason': 'user request'
                }
            ]
        }
    """
    
    result = {
        'must_see_cities': [],
        'avoid_cities': [],
        'stay_duration': {},
        'date_constraints': []  # NEW!
    }
    
    if not request_text:
        return result
    
    text_lower = request_text.lower()
    
    # ============================================================
    # DATE PATTERNS - NEW!
    # ============================================================
    
    # Pattern 1: "must see/visit CITY on DATE"
    # Examples: "must see Seville on 09-Feb-2026", "visit Granada on April 15"
    date_patterns = [
        r'(?:must see|visit|be in)\s+([A-Za-zá-úÁ-Ú\s]+?)\s+on\s+(\d{1,2}[-/]\w+[-/]\d{4}|\w+\s+\d{1,2})',
        r'([A-Za-zá-úÁ-Ú\s]+?)\s+on\s+(\d{1,2}[-/]\w+[-/]\d{4}|\w+\s+\d{1,2})',
    ]
    
    for pattern in date_patterns:
        matches = re.finditer(pattern, text_lower, re.IGNORECASE)
        for match in matches:
            city = match.group(1).strip().title()
            date_str = match.group(2).strip()
            
            # Try to parse the date
            parsed_date = parse_flexible_date(date_str)
            
            if parsed_date:
                result['date_constraints'].append({
                    'city': city,
                    'date': parsed_date,
                    'reason': 'user request'
                })
                
                # Also add to must_see_cities
                if city not in result['must_see_cities']:
                    result['must_see_cities'].append(city)
    
    # ============================================================
    # EXISTING PATTERNS (keep all existing logic)
    # ============================================================
    
    # Must-see cities
    must_see_patterns = [
        r'must (?:see|visit)\s+([A-Za-zá-úÁ-Ú\s,]+)',
        r'don\'t miss\s+([A-Za-zá-úÁ-Ú\s,]+)',
        r'essential:\s*([A-Za-zá-úÁ-Ú\s,]+)'
    ]
    
    for pattern in must_see_patterns:
        matches = re.finditer(pattern, text_lower)
        for match in matches:
            cities_text = match.group(1)
            cities = [c.strip().title() for c in re.split(r'[,and]', cities_text) if c.strip()]
            for city in cities:
                if city not in result['must_see_cities']:
                    result['must_see_cities'].append(city)
    
    # Avoid cities
    avoid_patterns = [
        r'(?:avoid|skip)\s+([A-Za-zá-úÁ-Ú\s,]+)',
        r'no\s+([A-Za-zá-úÁ-Ú\s]+)',
    ]
    
    for pattern in avoid_patterns:
        matches = re.finditer(pattern, text_lower)
        for match in matches:
            cities_text = match.group(1)
            cities = [c.strip().title() for c in re.split(r'[,and]', cities_text) if c.strip()]
            result['avoid_cities'].extend(cities)
    
    # Stay duration
    duration_patterns = [
        r'(\d+)\s+(?:nights?|days?)\s+in\s+([A-Za-zá-úÁ-Ú\s]+)',
        r'stay\s+(\d+)\s+(?:nights?|days?)\s+in\s+([A-Za-zá-úÁ-Ú\s]+)',
    ]
    
    for pattern in duration_patterns:
        matches = re.finditer(pattern, text_lower)
        for match in matches:
            duration = int(match.group(1))
            city = match.group(2).strip().title()
            result['stay_duration'][city] = duration
    
    return result


def parse_flexible_date(date_str: str) -> Optional[str]:
    """
    Parse various date formats:
    - "09-Feb-2026"
    - "09/02/2026"
    - "February 9, 2026"
    - "April 15"
    - "15-04-2026"
    
    Returns: "YYYY-MM-DD" format or None
    """
    
    date_str = date_str.strip()
    
    # Try different formats
    formats = [
        '%d-%b-%Y',      # 09-Feb-2026
        '%d/%m/%Y',      # 09/02/2026
        '%d-%m-%Y',      # 09-02-2026
        '%B %d, %Y',     # February 9, 2026
        '%b %d, %Y',     # Feb 9, 2026
        '%B %d',         # February 9 (assumes current/next year)
        '%b %d',         # Feb 9
    ]
    
    for fmt in formats:
        try:
            date_obj = datetime.strptime(date_str, fmt)
            
            # If no year specified, assume next occurrence
            if '%Y' not in fmt:
                today = datetime.now()
                date_obj = date_obj.replace(year=today.year)
                
                # If date already passed, use next year
                if date_obj < today:
                    date_obj = date_obj.replace(year=today.year + 1)
            
            return date_obj.strftime('%Y-%m-%d')
        except:
            continue
    
    return None


# ============================================================
# EXAMPLE USAGE
# ============================================================

if __name__ == "__main__":
    
    test_requests = [
        "Must see Seville on 09-Feb-2026 for the carnival",
        "Visit Granada on April 15 for the festival",
        "Must visit Córdoba, stay 2 nights in Seville, avoid Málaga",
        "Be in Cádiz on February 20",
        "Must see Granada, Seville on 20-04-2026, and Córdoba"
    ]
    
    print("=" * 80)
    print("TESTING DATE-AWARE SPECIAL REQUESTS PARSER")
    print("=" * 80)
    
    for request in test_requests:
        print(f"\nInput: {request}")
        result = parse_special_requests_with_dates(request)
        print(f"Result:")
        print(f"  Must-see cities: {result['must_see_cities']}")
        print(f"  Date constraints: {result['date_constraints']}")
        print(f"  Stay duration: {result['stay_duration']}")
        print(f"  Avoid: {result['avoid_cities']}")
