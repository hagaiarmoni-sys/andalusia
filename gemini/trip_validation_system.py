"""
Trip Validation System
Prevents impossible or conflicting trip configurations
"""

import streamlit as st
from datetime import timedelta

# ═══════════════════════════════════════════════════════════
# CONSTRAINTS CONFIGURATION
# ═══════════════════════════════════════════════════════════

TRIP_CONSTRAINTS = {
    'min_days': 3,
    'max_days': 21,
    'max_circular_days': 14,
    'min_attractions_per_day': 2,
    'max_attractions_per_day': 6,
    'max_driving_per_day_km': 250,
}

# ═══════════════════════════════════════════════════════════
# VALIDATION FUNCTIONS
# ═══════════════════════════════════════════════════════════

def validate_trip_duration(days, trip_type='point_to_point'):
    """
    Validate trip duration is within acceptable range
    """
    errors = []
    warnings = []
    
    min_days = TRIP_CONSTRAINTS['min_days']
    max_days = TRIP_CONSTRAINTS['max_days']
    
    if days < min_days:
        errors.append(f"❌ Trip too short! Minimum {min_days} days required.")
    
    if trip_type == 'circular' and days > TRIP_CONSTRAINTS['max_circular_days']:
        warnings.append(f"⚠️ Circular trips work best with ≤{TRIP_CONSTRAINTS['max_circular_days']} days. Consider point-to-point instead.")
    
    if days > max_days:
        errors.append(f"❌ Trip too long! Maximum {max_days} days allowed.")
    
    return errors, warnings


def validate_city_conflicts(start_city, end_city, cities_to_include, cities_to_avoid):
    """
    Check for conflicts between selected cities and avoid list
    """
    errors = []
    warnings = []
    
    # Normalize city names for comparison
    def normalize(city):
        if not city:
            return ""
        return city.lower().strip()
    
    start_norm = normalize(start_city)
    end_norm = normalize(end_city)
    avoid_norm = [normalize(c) for c in cities_to_avoid]
    include_norm = [normalize(c) for c in cities_to_include]
    
    # Check 1: Start city in avoid list
    if start_norm in avoid_norm:
        errors.append(f"❌ Conflict: Start city '{start_city}' is in your AVOID list!")
    
    # Check 2: End city in avoid list
    if end_city and end_norm in avoid_norm:
        errors.append(f"❌ Conflict: End city '{end_city}' is in your AVOID list!")
    
    # Check 3: Required cities in avoid list
    for city in cities_to_include:
        if normalize(city) in avoid_norm:
            errors.append(f"❌ Conflict: You want to visit '{city}' but it's in your AVOID list!")
    
    # Check 4: Start and end are the same (for point-to-point)
    if start_city and end_city and start_norm == end_norm:
        warnings.append(f"⚠️ Start and end cities are the same. Consider using 'Circular' or 'Hub' trip type instead.")
    
    return errors, warnings


def validate_special_requests(special_requests, start_city, end_city, cities_to_include):
    """
    Parse special requests and check for conflicts
    """
    errors = []
    warnings = []
    
    if not special_requests:
        return errors, warnings
    
    text_lower = special_requests.lower()
    
    # Extract "avoid" mentions
    avoid_keywords = ['avoid', 'skip', 'no', "don't visit", 'exclude', 'not interested']
    cities_mentioned = [start_city] + ([end_city] if end_city else []) + cities_to_include
    
    for city in cities_mentioned:
        if not city:
            continue
        city_lower = city.lower()
        
        # Check if city is mentioned with avoid keywords
        for keyword in avoid_keywords:
            if keyword in text_lower and city_lower in text_lower:
                # Check proximity - is "avoid" near this city name?
                city_pos = text_lower.find(city_lower)
                keyword_pos = text_lower.find(keyword)
                
                if abs(city_pos - keyword_pos) < 30:  # Within 30 chars
                    if city == start_city:
                        errors.append(f"❌ Conflict: You want to AVOID '{city}' but it's your START city!")
                    elif city == end_city:
                        errors.append(f"❌ Conflict: You want to AVOID '{city}' but it's your END city!")
                    elif city in cities_to_include:
                        errors.append(f"❌ Conflict: You want to AVOID '{city}' but you also want to VISIT it!")
    
    return errors, warnings


def validate_date_range(start_date, end_date):
    """
    Validate date range is reasonable
    """
    errors = []
    warnings = []
    
    if end_date <= start_date:
        errors.append(f"❌ End date must be AFTER start date!")
        return errors, warnings
    
    days = (end_date - start_date).days + 1
    
    # Check against constraints
    err, warn = validate_trip_duration(days)
    errors.extend(err)
    warnings.extend(warn)
    
    # Check if trip is too far in the future
    from datetime import datetime
    months_ahead = (start_date.year - datetime.now().year) * 12 + (start_date.month - datetime.now().month)
    
    if months_ahead > 24:
        warnings.append(f"⚠️ Trip is {months_ahead} months away. Plans may need adjustment closer to the date.")
    
    return errors, warnings


def validate_pace_and_days(pace, days):
    """
    Check if pace is appropriate for trip length
    """
    warnings = []
    
    if pace == 'relaxed' and days < 5:
        warnings.append(f"⚠️ 'Relaxed' pace works best with 5+ days. Consider 'Medium' pace for {days}-day trip.")
    
    if pace == 'fast' and days > 10:
        warnings.append(f"⚠️ 'Fast' pace can be exhausting for {days}-day trip. Consider 'Medium' or 'Relaxed' pace.")
    
    return warnings


def validate_all_parameters(params):
    """
    Master validation function - checks everything
    
    params = {
        'start_date': date,
        'end_date': date,
        'start_city': str,
        'end_city': str,
        'trip_type': str,
        'cities_to_include': list,
        'cities_to_avoid': list,
        'special_requests': str,
        'pace': str
    }
    
    Returns: (all_errors, all_warnings, is_valid)
    """
    all_errors = []
    all_warnings = []
    
    # Extract parameters
    start_date = params.get('start_date')
    end_date = params.get('end_date')
    start_city = params.get('start_city', '')
    end_city = params.get('end_city', '')
    trip_type = params.get('trip_type', 'point_to_point')
    cities_to_include = params.get('cities_to_include', [])
    cities_to_avoid = params.get('cities_to_avoid', [])
    special_requests = params.get('special_requests', '')
    pace = params.get('pace', 'medium')
    
    # Calculate days
    if start_date and end_date:
        days = (end_date - start_date).days + 1
    else:
        days = 7  # default
    
    # Run all validations
    errors, warnings = validate_date_range(start_date, end_date)
    all_errors.extend(errors)
    all_warnings.extend(warnings)
    
    errors, warnings = validate_city_conflicts(start_city, end_city, cities_to_include, cities_to_avoid)
    all_errors.extend(errors)
    all_warnings.extend(warnings)
    
    errors, warnings = validate_special_requests(special_requests, start_city, end_city, cities_to_include)
    all_errors.extend(errors)
    all_warnings.extend(warnings)
    
    warnings = validate_pace_and_days(pace, days)
    all_warnings.extend(warnings)
    
    is_valid = len(all_errors) == 0
    
    return all_errors, all_warnings, is_valid


def display_validation_results(errors, warnings):
    """
    Display validation errors and warnings in Streamlit UI
    """
    if errors:
        st.error("### 🚫 Cannot Generate Trip - Please Fix These Issues:")
        for error in errors:
            st.error(error)
        return False
    
    if warnings:
        st.warning("### ⚠️ Suggestions:")
        for warning in warnings:
            st.warning(warning)
    
    return True


# ═══════════════════════════════════════════════════════════
# EXAMPLE USAGE IN YOUR APP
# ═══════════════════════════════════════════════════════════

"""
# In your main app file, BEFORE generating itinerary:

# Collect all parameters
params = {
    'start_date': start_date,
    'end_date': end_date,
    'start_city': start_city,
    'end_city': end_city,
    'trip_type': trip_type,
    'cities_to_include': cities_to_include,
    'cities_to_avoid': cities_to_avoid,
    'special_requests': special_requests,
    'pace': pace
}

# Validate everything
errors, warnings, is_valid = validate_all_parameters(params)

# Display results
can_proceed = display_validation_results(errors, warnings)

# Only generate if valid
if can_proceed and st.button("Generate Itinerary"):
    # Generate trip...
    pass
else:
    if not can_proceed:
        st.stop()  # Don't show generate button
"""
