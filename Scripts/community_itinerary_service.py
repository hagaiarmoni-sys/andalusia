"""
Community Itinerary Service - Leverages enriched community itineraries data
Provides smart recommendations and templates based on proven travel patterns
"""

import json
from typing import List, Dict, Optional, Tuple
from text_norm import norm_key  # ✅ FIXED: Use norm_key from your text_norm.py


class CommunityItineraryService:
    """Service for working with enriched community itineraries"""
    
    def __init__(self, itineraries_data: dict):
        """
        Initialize with community itineraries data
        
        Args:
            itineraries_data: Loaded JSON data from andalusia_community_itineraries_enriched.json
        """
        self.itineraries = itineraries_data.get('itineraries', [])
        self.metadata = itineraries_data.get('planning_metadata', {})
    
    def find_matching_itineraries(
        self,
        duration_days: int,
        user_profile: Dict,
        cities: Optional[List[str]] = None,
        tolerance_days: int = 2
    ) -> List[Dict]:
        """
        Find community itineraries that match user's profile and requirements
        
        Args:
            duration_days: Desired trip duration
            user_profile: Dict with keys like 'first_time', 'family_with_kids', 'budget', 'pace'
            cities: Optional list of cities user wants to visit
            tolerance_days: Allow itineraries within ±tolerance_days
        
        Returns:
            List of matching itineraries, sorted by match score
        """
        matches = []
        
        for itinerary in self.itineraries:
            score = self._calculate_match_score(
                itinerary,
                duration_days,
                user_profile,
                cities,
                tolerance_days
            )
            
            if score > 0:
                itinerary_copy = itinerary.copy()
                itinerary_copy['match_score'] = score
                matches.append(itinerary_copy)
        
        # Sort by match score (highest first)
        matches.sort(key=lambda x: x['match_score'], reverse=True)
        
        return matches
    
    def _calculate_match_score(
        self,
        itinerary: Dict,
        duration_days: int,
        user_profile: Dict,
        cities: Optional[List[str]],
        tolerance_days: int
    ) -> float:
        """Calculate how well an itinerary matches user requirements"""
        score = 0.0
        
        # Duration match (highest weight)
        itin_days = itinerary.get('duration_days', 0)
        days_diff = abs(itin_days - duration_days)
        
        if days_diff == 0:
            score += 50  # Perfect match
        elif days_diff <= tolerance_days:
            score += 30 - (days_diff * 5)  # Partial match
        else:
            return 0  # Too different
        
        # Profile fit (second highest weight)
        profile_fit = itinerary.get('profile_fit', {})
        
        for key, value in user_profile.items():
            if key in profile_fit and profile_fit[key] == value:
                if value:  # True match
                    score += 10
        
        # Budget match
        itin_budget = itinerary.get('budget_level', '').lower()
        user_budget = user_profile.get('budget', '').lower()
        
        if itin_budget == user_budget:
            score += 15
        
        # Pace match
        pace_profile = itinerary.get('pace_profile', {})
        user_pace = user_profile.get('pace', 'medium').lower()
        
        pace_map = {
            'easy': ['easy', 'relaxed', 'slow'],
            'medium': ['medium', 'standard', 'balanced'],
            'fast': ['fast', 'active', 'intensive']
        }
        
        itin_intensity = pace_profile.get('walking_intensity', '').lower()
        
        for pace_key, pace_terms in pace_map.items():
            if user_pace in pace_terms and any(term in itin_intensity for term in pace_terms):
                score += 10
                break
        
        # City overlap (if specified)
        if cities:
            itin_cities = [c.lower() for c in itinerary.get('cities_visited', [])]
            user_cities_lower = [c.lower() for c in cities]
            
            overlap = len(set(itin_cities) & set(user_cities_lower))
            score += overlap * 5
        
        # Transport type match
        required_transport = itinerary.get('required_transport_type', {})
        car_required = required_transport.get('car_required', False)
        user_wants_car = user_profile.get('car_required', True)
        
        if car_required == user_wants_car:
            score += 8
        
        # Rating boost (social proof)
        social_proof = itinerary.get('social_proof', {})
        rating = social_proof.get('rating', 0)
        
        if rating >= 4.5:
            score += 5
        elif rating >= 4.0:
            score += 3
        
        return score
    
    def get_template_metrics(self, itinerary_id: str) -> Optional[Dict]:
        """Get metrics from a community itinerary to use as template"""
        for itinerary in self.itineraries:
            if itinerary.get('id') == itinerary_id:
                return itinerary.get('metrics', {})
        return None
    
    def get_route_suggestions(self, from_city: str, to_city: str) -> List[Dict]:
        """
        Get route suggestions between two cities from community itineraries
        
        Returns:
            List of possible detours with enriched route data
        """
        suggestions = []
        
        for itinerary in self.itineraries:
            route_ids = itinerary.get('route_ids_between_cities', [])
            
            for route in route_ids:
                route_from = route.get('from', '').lower()
                route_to = route.get('to', '').lower()
                
                # ✅ FIXED: Use norm_key for comparison
                if (norm_key(route_from) == norm_key(from_city) and
                    norm_key(route_to) == norm_key(to_city)):
                    
                    detours = route.get('possible_detours', [])
                    if detours:
                        suggestions.append({
                            'from': route.get('from'),
                            'to': route.get('to'),
                            'detour_ids': detours,
                            'source_itinerary': itinerary.get('name'),
                            'itinerary_rating': itinerary.get('social_proof', {}).get('rating', 0)
                        })
        
        return suggestions
    
    def get_daily_plan_pois(self, itinerary_id: str) -> Dict[int, List[str]]:
        """
        Get POI IDs by day from a community itinerary
        
        Returns:
            Dict mapping day_number to list of poi_ids
        """
        for itinerary in self.itineraries:
            if itinerary.get('id') == itinerary_id:
                daily_plan = itinerary.get('daily_plan', [])
                
                result = {}
                for day in daily_plan:
                    day_num = day.get('day_number')
                    poi_ids = day.get('poi_ids_for_day', [])
                    if day_num and poi_ids:
                        result[day_num] = poi_ids
                
                return result
        
        return {}
    
    def get_booking_priorities(self) -> List[str]:
        """Get booking priorities from planning metadata"""
        return self.metadata.get('booking_priorities', [])
    
    def get_seasonal_tips(self, season: str) -> Dict:
        """Get seasonal tips for trip planning"""
        seasonal_tips = self.metadata.get('seasonal_tips', {})
        
        season_map = {
            'spring': 'Spring',
            'summer': 'Summer',
            'autumn': 'Autumn',
            'fall': 'Autumn',
            'winter': 'Winter'
        }
        
        season_key = season_map.get(season.lower(), season.capitalize())
        return seasonal_tips.get(season_key, {})
    
    def get_transport_tips(self, transport_type: str = 'rental_car') -> Dict:
        """Get transport tips from planning metadata"""
        transport_tips = self.metadata.get('transport_tips', {})
        return transport_tips.get(transport_type, {})
    
    def get_must_try_foods(self, city: str) -> List[str]:
        """Get must-try foods for a specific city"""
        must_try = self.metadata.get('must_try_foods', {})
        
        # Normalize city name
        city_lower = city.lower()
        
        # ✅ FIXED: Use norm_key for comparison
        for key, foods in must_try.items():
            if norm_key(key) == norm_key(city):
                return foods
        
        # Return regional defaults if city not found
        return must_try.get('Regional', [])
    
    def get_cultural_etiquette(self, category: str = 'general') -> List[str]:
        """Get cultural etiquette tips"""
        etiquette = self.metadata.get('cultural_etiquette', {})
        return etiquette.get(category, [])
    
    def get_money_saving_tips(self) -> List[str]:
        """Get money saving tips"""
        return self.metadata.get('money_saving_tips', [])
    
    def format_itinerary_comparison(self, user_metrics: Dict, similar_itinerary: Dict) -> str:
        """
        Format a comparison between user's trip and a similar community itinerary
        
        Args:
            user_metrics: User's trip metrics (total_km, avg_km_per_day, etc.)
            similar_itinerary: Community itinerary dict
        
        Returns:
            Formatted comparison string
        """
        itin_name = similar_itinerary.get('name', 'Unknown')
        itin_metrics = similar_itinerary.get('metrics', {})
        
        comparison = f"**Your trip is similar to: {itin_name}**\n\n"
        
        # Compare key metrics
        user_total_km = user_metrics.get('total_km', 0)
        itin_total_km = itin_metrics.get('total_km', 0)
        
        if user_total_km and itin_total_km:
            diff_km = user_total_km - itin_total_km
            comparison += f"- **Driving:** Your trip has {abs(diff_km):.0f}km {'more' if diff_km > 0 else 'less'} driving\n"
        
        user_avg_km = user_metrics.get('avg_km_per_day', 0)
        itin_avg_km = itin_metrics.get('avg_km_per_day', 0)
        
        if user_avg_km and itin_avg_km:
            comparison += f"- **Daily pace:** {user_avg_km:.0f}km/day vs {itin_avg_km:.0f}km/day in template\n"
        
        # User tips from community
        user_tips = similar_itinerary.get('user_tips', [])
        if user_tips:
            comparison += f"\n**Tips from travelers:**\n"
            for tip in user_tips[:3]:  # Show top 3 tips
                comparison += f"- {tip}\n"
        
        return comparison


def load_community_itineraries(filepath: str = 'andalusia_community_itineraries_enriched.json') -> Optional[CommunityItineraryService]:
    """
    Load and initialize the community itinerary service
    
    Args:
        filepath: Path to enriched community itineraries JSON
    
    Returns:
        CommunityItineraryService instance or None if file not found
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return CommunityItineraryService(data)
    
    except FileNotFoundError:
        return None
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON: {e}")
        return None
