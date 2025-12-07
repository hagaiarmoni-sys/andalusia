"""
Enriched Routes Service - Leverages enriched routes data for intelligent en-route attractions
Provides context-aware route suggestions based on user preferences, season, and suitability
"""

import json
from typing import List, Dict, Optional, Tuple
from text_norm import norm_key  # ✅ FIXED: Use norm_key from your text_norm.py


class EnrichedRoutesService:
    """Service for working with enriched en-route attractions"""
    
    def __init__(self, routes_data: dict):
        """
        Initialize with enriched routes data
        
        Args:
            routes_data: Loaded JSON data from andalusia_routes_enriched.json
        """
        self.routes = routes_data.get('routes', [])
        self.metadata = routes_data.get('metadata', {})
    
    def get_routes_between_cities(
        self,
        from_city: str,
        to_city: str,
        filters: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Get en-route attractions between two cities
        
        Args:
            from_city: Starting city
            to_city: Destination city
            filters: Optional filters (priority, category, suitability, etc.)
        
        Returns:
            List of matching route attractions
        """
        matches = []
        
        # ✅ FIXED: Use norm_key for normalization
        from_norm = norm_key(from_city)
        to_norm = norm_key(to_city)
        
        for route in self.routes:
            between_cities = route.get('between_cities', [])
            
            # Check if route connects the two cities (in either direction)
            cities_norm = [norm_key(c) for c in between_cities]
            
            if from_norm in cities_norm and to_norm in cities_norm:
                # Apply filters if provided
                if filters and not self._matches_filters(route, filters):
                    continue
                
                matches.append(route)
        
        return matches
    
    def _matches_filters(self, route: Dict, filters: Dict) -> bool:
        """Check if route matches all provided filters"""
        
        # Priority filter
        if 'max_priority' in filters:
            if route.get('priority', 99) > filters['max_priority']:
                return False
        
        # Category filter
        if 'categories' in filters:
            if route.get('category') not in filters['categories']:
                return False
        
        # Suitability filters
        suitability = route.get('suitability', {})
        
        if filters.get('kids_friendly') and not suitability.get('kids_friendly'):
            return False
        
        if filters.get('seniors_friendly') and not suitability.get('seniors_friendly'):
            return False
        
        if filters.get('wheelchair_friendly') and not suitability.get('wheelchair_friendly'):
            return False
        
        # Max detour distance
        if 'max_detour_km' in filters:
            if route.get('detour_km', 999) > filters['max_detour_km']:
                return False
        
        # Max time impact
        if 'max_time_impact_minutes' in filters:
            drive_impact = route.get('drive_impact', {})
            total_time = (
                drive_impact.get('extra_drive_minutes', 0) +
                drive_impact.get('min_buffer_minutes', 0) +
                (route.get('recommended_stop_hours', 0) * 60)
            )
            
            if total_time > filters['max_time_impact_minutes']:
                return False
        
        # Season filter
        if 'current_month' in filters:
            seasonality = route.get('seasonality', {})
            avoid_months = seasonality.get('avoid_months', [])
            
            if filters['current_month'] in avoid_months:
                return False
        
        # Rainy day filter
        if filters.get('rainy_day') and not suitability.get('rainy_day_ok'):
            return False
        
        return True
    
    def get_recommended_stops(
        self,
        from_city: str,
        to_city: str,
        user_profile: Dict,
        max_stops: int = 3,
        current_month: Optional[str] = None
    ) -> List[Dict]:
        """
        Get recommended en-route stops based on user profile
        
        Args:
            from_city: Starting city
            to_city: Destination city
            user_profile: Dict with 'family_with_kids', 'budget', 'interests', etc.
            max_stops: Maximum number of stops to recommend
            current_month: Current travel month for seasonality
        
        Returns:
            List of recommended stops, scored and sorted
        """
        # Build filters from user profile
        filters = {}
        
        if user_profile.get('family_with_kids'):
            filters['kids_friendly'] = True
        
        if user_profile.get('seniors'):
            filters['seniors_friendly'] = True
        
        if user_profile.get('wheelchair_access'):
            filters['wheelchair_friendly'] = True
        
        if current_month:
            filters['current_month'] = current_month
        
        # Get all matching routes
        routes = self.get_routes_between_cities(from_city, to_city, filters)
        
        if not routes:
            return []
        
        # Score each route
        scored_routes = []
        
        for route in routes:
            score = self._calculate_route_score(route, user_profile)
            route_copy = route.copy()
            route_copy['recommendation_score'] = score
            scored_routes.append(route_copy)
        
        # Sort by score (highest first) and priority
        scored_routes.sort(
            key=lambda x: (x.get('recommendation_score', 0), -x.get('priority', 99)),
            reverse=True
        )
        
        return scored_routes[:max_stops]
    
    def _calculate_route_score(self, route: Dict, user_profile: Dict) -> float:
        """Calculate how well a route matches user preferences"""
        score = 0.0
        
        # Priority boost (must-see attractions)
        priority = route.get('priority', 3)
        if priority == 1:
            score += 30
        elif priority == 2:
            score += 15
        
        # Category match
        route_category = route.get('category', '').lower()
        user_interests = user_profile.get('interests', [])
        
        if route_category in [i.lower() for i in user_interests]:
            score += 20
        
        # Tags match
        route_tags = [t.lower() for t in route.get('tags', [])]
        
        for tag in route_tags:
            if any(tag in interest.lower() for interest in user_interests):
                score += 5
        
        # Budget consideration
        budget = user_profile.get('budget', 'mid-range').lower()
        booking = route.get('booking', {})
        
        if booking.get('required') and budget == 'budget':
            score -= 5  # Penalize expensive must-book attractions for budget travelers
        
        # Time efficiency (prefer shorter detours)
        detour_km = route.get('detour_km', 0)
        if detour_km <= 10:
            score += 10
        elif detour_km <= 20:
            score += 5
        
        # Photography spots
        suitability = route.get('suitability', {})
        if suitability.get('photography_spot') and 'photography' in user_interests:
            score += 10
        
        return score
    
    def get_route_details(self, attraction_id: str) -> Optional[Dict]:
        """Get detailed route information by attraction ID"""
        for route in self.routes:
            if route.get('attraction_id') == attraction_id:
                return route
        return None
    
    def get_time_impact(self, attraction_id: str) -> Dict:
        """
        Calculate total time impact of stopping at this attraction
        
        Returns:
            Dict with 'driving_minutes', 'buffer_minutes', 'visit_minutes', 'total_minutes'
        """
        route = self.get_route_details(attraction_id)
        
        if not route:
            return {}
        
        drive_impact = route.get('drive_impact', {})
        
        return {
            'driving_minutes': drive_impact.get('extra_drive_minutes', 0),
            'buffer_minutes': drive_impact.get('min_buffer_minutes', 0),
            'visit_minutes': route.get('recommended_stop_hours', 0) * 60,
            'total_minutes': (
                drive_impact.get('extra_drive_minutes', 0) +
                drive_impact.get('min_buffer_minutes', 0) +
                (route.get('recommended_stop_hours', 0) * 60)
            )
        }
    
    def check_booking_requirements(self, attraction_ids: List[str]) -> List[Dict]:
        """
        Check which attractions require advance booking
        
        Returns:
            List of dicts with booking information for attractions that need it
        """
        booking_needed = []
        
        for attr_id in attraction_ids:
            route = self.get_route_details(attr_id)
            
            if not route:
                continue
            
            booking = route.get('booking', {})
            
            if booking.get('required'):
                booking_needed.append({
                    'attraction_id': attr_id,
                    'attraction_name': route.get('attraction_name'),
                    'lead_time_days': booking.get('lead_time_days', 0),
                    'tip': booking.get('tip', 'Book in advance'),
                    'location': route.get('location')
                })
        
        # Sort by lead time (longest first)
        booking_needed.sort(key=lambda x: x['lead_time_days'], reverse=True)
        
        return booking_needed
    
    def get_seasonal_recommendations(
        self,
        from_city: str,
        to_city: str,
        month: str
    ) -> Dict:
        """
        Get season-specific route recommendations
        
        Returns:
            Dict with 'best', 'ok', 'avoid' lists of routes
        """
        routes = self.get_routes_between_cities(from_city, to_city)
        
        best = []
        ok = []
        avoid = []
        
        for route in routes:
            seasonality = route.get('seasonality', {})
            best_months = [m.lower() for m in seasonality.get('best_months', [])]
            avoid_months = [m.lower() for m in seasonality.get('avoid_months', [])]
            
            month_lower = month.lower()
            
            if 'all year' in best_months or month_lower in best_months:
                best.append(route)
            elif month_lower in avoid_months:
                avoid.append(route)
            else:
                ok.append(route)
        
        return {
            'best': best,
            'ok': ok,
            'avoid': avoid
        }
    
    def format_route_recommendation(self, route: Dict, include_warnings: bool = True) -> str:
        """
        Format a route recommendation for display
        
        Args:
            route: Route dict
            include_warnings: Whether to include warnings/tips
        
        Returns:
            Formatted string
        """
        name = route.get('attraction_name', 'Unknown')
        location = route.get('location', '')
        category = route.get('category', '')
        
        output = f"**{name}** ({location})\n"
        output += f"📍 Category: {category}\n"
        
        # Time impact
        detour_km = route.get('detour_km', 0)
        stop_hours = route.get('recommended_stop_hours', 0)
        
        output += f"🚗 Detour: +{detour_km}km | ⏱️ Stop: {stop_hours}h\n"
        
        # Priority indicator
        priority = route.get('priority', 3)
        if priority == 1:
            output += "⭐ **Must-see attraction**\n"
        elif priority == 2:
            output += "👍 Recommended\n"
        
        # Booking requirement
        booking = route.get('booking', {})
        if booking.get('required'):
            lead_time = booking.get('lead_time_days', 0)
            output += f"🎫 **Book {lead_time} days in advance**\n"
        
        # Suitability
        suitability = route.get('suitability', {})
        suitable_for = []
        
        if suitability.get('kids_friendly'):
            suitable_for.append('👶 Kids')
        if suitability.get('seniors_friendly'):
            suitable_for.append('👴 Seniors')
        if suitability.get('photography_spot'):
            suitable_for.append('📷 Photography')
        
        if suitable_for:
            output += f"✓ {', '.join(suitable_for)}\n"
        
        # Warnings/Tips
        if include_warnings:
            seasonality = route.get('seasonality', {})
            notes = seasonality.get('notes', '')
            
            if notes:
                output += f"💡 {notes}\n"
            
            tip = booking.get('tip', '')
            if tip:
                output += f"💡 {tip}\n"
        
        return output


def load_enriched_routes(filepath: str = 'andalusia_routes_enriched.json') -> Optional[EnrichedRoutesService]:
    """
    Load and initialize the enriched routes service
    
    Args:
        filepath: Path to enriched routes JSON
    
    Returns:
        EnrichedRoutesService instance or None if file not found
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return EnrichedRoutesService(data)
    
    except FileNotFoundError:
        return None
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON: {e}")
        return None
