"""
RouteService - Handles route planning and en-route attractions
"""
import pandas as pd
from typing import List, Dict, Optional


def parse_avoid_locations(special_requests):
    """Extract cities to avoid from special requests"""
    if not special_requests:
        return []
    
    avoid_keywords = ['avoid', 'skip', 'exclude', 'not', "don't", 'without', 'except']
    avoid_cities = []
    
    text = special_requests.lower().strip()
    
    # Check if user wants to avoid something
    has_avoid_keyword = any(keyword in text for keyword in avoid_keywords)
    
    if has_avoid_keyword:
        # Andalusian cities (add variations with/without accents)
        known_cities = [
            'marbella', 'malaga', 'málaga', 'granada', 'seville', 'sevilla',
            'cordoba', 'córdoba', 'cadiz', 'cádiz', 'almeria', 'almería',
            'jerez', 'ronda', 'tarifa', 'nerja', 'antequera', 'ubeda', 'úbeda',
            'jaen', 'jaén', 'huelva', 'estepona', 'mijas', 'fuengirola',
            'gibraltar', 'motril', 'alhama', 'vejer', 'arcos'
        ]
        
        for city in known_cities:
            if city in text:
                # Normalize to title case
                avoid_cities.append(city.title())
    
    return avoid_cities


class RouteService:
    def __init__(self, routes_data: Dict, attraction_service):
        """Initialize with routes data and attraction service"""
        self.df = pd.DataFrame(routes_data['routes'])
        self.metadata = routes_data['metadata']
        self.attraction_service = attraction_service
    
    def get_all(self) -> pd.DataFrame:
        """Get all routes"""
        return self.df.copy()
    
    def get_between_cities(self, city_a: str, city_b: str) -> pd.DataFrame:
        """Get routes between two cities"""
        mask = self.df['between_cities'].apply(
            lambda cities: city_a in cities and city_b in cities
        )
        return self.df[mask].copy()
    
    def get_from_city(self, city: str) -> pd.DataFrame:
        """Get all routes from a city"""
        mask = self.df['between_cities'].apply(lambda cities: city in cities)
        return self.df[mask].copy()
    
    def get_route_with_details(self, attraction_id: str) -> Optional[Dict]:
        """Get route with full attraction details"""
        route = self.df[self.df['attraction_id'] == attraction_id]
        if len(route) == 0:
            return None
        
        route_dict = route.iloc[0].to_dict()
        attraction = self.attraction_service.get_by_id(attraction_id)
        
        return {
            **route_dict,
            'attraction_details': attraction
        }
    
    def get_all_with_details(self) -> List[Dict]:
        """Get all routes with full attraction details"""
        results = []
        for _, route in self.df.iterrows():
            attraction = self.attraction_service.get_by_id(route['attraction_id'])
            results.append({
                **route.to_dict(),
                'attraction_details': attraction
            })
        return results
    
    def get_by_max_detour(self, max_km: float) -> pd.DataFrame:
        """Get routes by maximum detour distance"""
        return self.df[self.df['detour_km'] <= max_km].copy()
    
    def get_by_min_stop_time(self, min_hours: float) -> pd.DataFrame:
        """Get routes by minimum recommended stop time"""
        return self.df[self.df['recommended_stop_hours'] >= min_hours].copy()
    
    def sort_by_detour(self, ascending: bool = True) -> pd.DataFrame:
        """Sort routes by detour distance"""
        return self.df.sort_values('detour_km', ascending=ascending).copy()
    
    def get_optimal_routes(self, max_detour_km: float = 20, 
                          min_stop_hours: float = 1.5) -> pd.DataFrame:
        """Get optimal routes (short detour, worth the stop)"""
        return self.df[
            (self.df['detour_km'] <= max_detour_km) &
            (self.df['recommended_stop_hours'] >= min_stop_hours)
        ].copy()
    
    def calculate_total_detour(self, route_ids: List[str]) -> Dict:
        """Calculate total detour for multiple routes"""
        routes = self.df[self.df['attraction_id'].isin(route_ids)]
        
        return {
            'total_km': routes['detour_km'].sum(),
            'total_hours': routes['recommended_stop_hours'].sum(),
            'routes': routes.to_dict('records')
        }
    
    def get_recommendations(self, city_a: str, city_b: str, 
                           preferences: Optional[Dict] = None,
                           avoid_cities: Optional[List[str]] = None) -> List[Dict]:
        """Get route recommendations for a journey, excluding avoided cities"""
        if preferences is None:
            preferences = {}
        
        if avoid_cities is None:
            avoid_cities = []
        
        max_detour = preferences.get('max_detour', 30)
        min_stop_time = preferences.get('min_stop_time', 1)
        prefer_quick_stops = preferences.get('prefer_quick_stops', False)
        
        # Get routes between cities
        routes = self.get_between_cities(city_a, city_b)
        
        # Filter by preferences
        routes = routes[
            (routes['detour_km'] <= max_detour) &
            (routes['recommended_stop_hours'] >= min_stop_time)
        ]
        
        # Sort by preference
        if prefer_quick_stops:
            routes = routes.sort_values('recommended_stop_hours')
        else:
            routes = routes.sort_values('detour_km')
        
        # Add full attraction details and filter avoided cities
        results = []
        for _, route in routes.iterrows():
            attraction = self.attraction_service.get_by_id(route['attraction_id'])
            
            # Skip if attraction is in an avoided city
            if attraction and avoid_cities:
                attr_city = attraction.get('city', '').lower()
                if any(avoid.lower() in attr_city for avoid in avoid_cities):
                    continue
            
            results.append({
                **route.to_dict(),
                'attraction_details': attraction
            })
        
        return results
    
    def filter_cities_by_avoidance(self, cities: List[str], avoid_cities: List[str]) -> List[str]:
        """Filter out cities that should be avoided"""
        if not avoid_cities:
            return cities
        
        filtered = []
        for city in cities:
            city_lower = city.lower()
            # Check if any avoided city is in this city name
            should_skip = any(avoid.lower() in city_lower for avoid in avoid_cities)
            if not should_skip:
                filtered.append(city)
        
        return filtered
    
    def get_stats(self) -> Dict:
        """Get statistics about routes"""
        return {
            'total': len(self.df),
            'avg_detour': round(self.df['detour_km'].mean(), 1),
            'avg_stop_time': round(self.df['recommended_stop_hours'].mean(), 1),
            'shortest_detour': self.df['detour_km'].min(),
            'longest_detour': self.df['detour_km'].max()
        }