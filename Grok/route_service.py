import pandas as pd
import numpy as np
from attraction_service import AttractionService

class RouteService:
    def __init__(self, routes_data: dict, attraction_service: AttractionService):
        """
        Initialize RouteService with routes data and attraction service.
        
        Args:
            routes_data (dict): Dictionary containing routes data (e.g., from JSON)
            attraction_service (AttractionService): Service for attraction data
        """
        if not routes_data or 'routes' not in routes_data:
            self.df = pd.DataFrame(columns=['start', 'end', 'distance_km', 'detour_km'])
        else:
            # Load routes data into DataFrame
            self.df = pd.DataFrame(routes_data['routes'])
            # Ensure required columns exist, fill with defaults if missing
            for col in ['start', 'end', 'distance_km', 'detour_km']:
                if col not in self.df.columns:
                    self.df[col] = None
            # Convert distance and detour to numeric, handle missing values
            self.df['distance_km'] = pd.to_numeric(self.df['distance_km'], errors='coerce').fillna(0.0)
            self.df['detour_km'] = pd.to_numeric(self.df['detour_km'], errors='coerce').fillna(0.0)
        
        self.attraction_service = attraction_service

    def get_between_cities(self, city_a: str, city_b: str) -> pd.DataFrame:
        """Get routes between two cities"""
        # Filter routes where city_a is start and city_b is end, or vice versa
        mask = (
            ((self.df['start'].str.lower() == city_a.lower()) & (self.df['end'].str.lower() == city_b.lower())) |
            ((self.df['start'].str.lower() == city_b.lower()) & (self.df['end'].str.lower() == city_a.lower()))
        )
        return self.df[mask].copy()

    def get_recommendations(self, city_a: str, city_b: str, max_detour: float = 50.0, 
                          preferences: dict = None) -> list:
        """
        Get recommended stops between two cities.
        
        Args:
            city_a (str): Starting city
            city_b (str): Destination city
            max_detour (float): Maximum detour distance in km
            preferences (dict): User preferences (e.g., min_stop_time, prefer_quick_stops, avoid_cities)
        
        Returns:
            list: List of recommendation dictionaries
        """
        if not city_a or not city_b or city_a.lower() == city_b.lower():
            return []

        min_stop_time = preferences.get('min_stop_time', 1) if preferences else 1
        prefer_quick_stops = preferences.get('prefer_quick_stops', False) if preferences else False
        avoid_cities = preferences.get('avoid_cities', []) if preferences else []
        
        routes = self.get_between_cities(city_a, city_b)
        
        if routes.empty:
            return []

        routes = routes[
            (routes['detour_km'] <= max_detour) &
            (routes['distance_km'] > 0)
        ].copy()

        if routes.empty:
            return []

        # Get attractions near the route midpoints, filtering out avoided cities
        recommendations = []
        for _, route in routes.iterrows():
            midpoint = self._estimate_midpoint(route['start'], route['end'])
            attractions = self.attraction_service.get_nearby_attractions(midpoint, max_distance_km=20.0)
            
            for attr in attractions:
                city = attr.get('city', '').lower()
                if avoid_cities and any(normalize_city_name(avoid) == city for avoid in avoid_cities):
                    continue  # Skip attractions in avoided cities
                
                detour_km = route['detour_km']  # Simplified detour estimate
                stop_hours = attr.get('visit_duration_hours', min_stop_time)
                if prefer_quick_stops and stop_hours > 2:
                    continue
                
                recommendations.append({
                    'attraction_details': attr,
                    'detour_km': detour_km,
                    'recommended_stop_hours': stop_hours
                })

        # Sort by detour distance and filter top recommendations
        recommendations.sort(key=lambda x: x['detour_km'])
        return recommendations[:3]  # Return top 3 recommendations

    def _estimate_midpoint(self, city_a: str, city_b: str) -> tuple:
        """Estimate midpoint coordinates between two cities (simplified)"""
        attractions_a = self.attraction_service.get_attractions_by_city(city_a)
        attractions_b = self.attraction_service.get_attractions_by_city(city_b)
        
        if not attractions_a or not attractions_b:
            return (0.0, 0.0)
        
        lat_a = np.mean([a['coordinates']['lat'] for a in attractions_a if 'coordinates' in a])
        lon_a = np.mean([a['coordinates']['lon'] for a in attractions_a if 'coordinates' in a])
        lat_b = np.mean([a['coordinates']['lat'] for a in attractions_b if 'coordinates' in a])
        lon_b = np.mean([a['coordinates']['lon'] for a in attractions_b if 'coordinates' in a])
        
        return ((lat_a + lat_b) / 2, (lon_a + lon_b) / 2)

# Note: Ensure normalize_city_name is available (defined in trip_planner_page.py or imported)