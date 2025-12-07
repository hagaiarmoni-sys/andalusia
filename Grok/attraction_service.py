"""
AttractionService - Enhanced with coordinate consistency and indexing
"""
import pandas as pd
from typing import List, Dict, Optional

class AttractionService:
    def __init__(self, attractions_data):
        """
        Initialize with attractions data
        
        Args:
            attractions_data: Can be list or dict with 'attractions' key
        """
        if isinstance(attractions_data, list):
            self.df = pd.DataFrame(attractions_data)
            self.metadata = {}
        elif isinstance(attractions_data, dict):
            if 'attractions' in attractions_data:
                self.df = pd.DataFrame(attractions_data['attractions'])
            else:
                self.df = pd.DataFrame(attractions_data)
            self.metadata = attractions_data.get('metadata', {})
        else:
            self.df = pd.DataFrame(attractions_data)
            self.metadata = {}
        
        # Standardize coordinates
        if 'coordinates' in self.df.columns:
            self.df['lat'] = self.df['coordinates'].apply(lambda x: float(x.get('lat', 0)) if isinstance(x, dict) else 0)
            self.df['lon'] = self.df['coordinates'].apply(lambda x: float(x.get('lon', 0)) if isinstance(x, dict) else 0)
        else:
            self.df['lat'] = self.df.get('latitude', 0)
            self.df['lon'] = self.df.get('longitude', 0)
        
        # Ensure required columns
        if 'tags' not in self.df.columns:
            self.df['tags'] = [[] for _ in range(len(self.df))]
        
        if 'rating' not in self.df.columns:
            self.df['rating'] = 0.0
        
        if 'visit_duration_hours' not in self.df.columns:
            self.df['visit_duration_hours'] = 2.0
        
        if 'entrance_fee' not in self.df.columns:
            self.df['entrance_fee'] = 'Free'
            self.df['entrance_fee_value'] = 0.0
        else:
            self.df['entrance_fee_value'] = self.df['entrance_fee'].apply(
                lambda x: float(x) if isinstance(x, (int, float)) else 0.0
            )
        
        if 'category' not in self.df.columns:
            self.df['category'] = 'Other'
        
        # Clean data
        self.df['rating'] = pd.to_numeric(self.df['rating'], errors='coerce').fillna(0.0)
        self.df['visit_duration_hours'] = pd.to_numeric(self.df['visit_duration_hours'], errors='coerce').fillna(2.0)
        self.df['lat'] = pd.to_numeric(self.df['lat'], errors='coerce').fillna(0.0)
        self.df['lon'] = pd.to_numeric(self.df['lon'], errors='coerce').fillna(0.0)
    
    def get_all(self) -> pd.DataFrame:
        """Get all attractions"""
        return self.df.copy()
    
    def get_by_city(self, city: str) -> pd.DataFrame:
        """Get attractions by city"""
        try:
            return self.df[self.df['city'].str.lower() == city.lower()].copy()
        except:
            return pd.DataFrame()
    
    def get_by_category(self, category: str) -> pd.DataFrame:
        """Get attractions by category"""
        return self.df[self.df['category'].str.lower() == category.lower()].copy()
    
    def get_by_id(self, attraction_id: str) -> Optional[Dict]:
        """Get single attraction by ID or name"""
        if 'id' in self.df.columns:
            result = self.df[self.df['id'] == attraction_id]
        else:
            result = self.df[self.df['name'] == attraction_id]
        
        if len(result) == 0:
            return None
        return result.iloc[0].to_dict()
    
    def get_by_rating(self, min_rating: float) -> pd.DataFrame:
        """Get attractions with rating >= min_rating"""
        return self.df[self.df['rating'] >= min_rating].copy()
    
    def get_by_tag(self, tag: str) -> pd.DataFrame:
        """Get attractions by tag"""
        tag_lower = tag.lower()
        mask = self.df['tags'].apply(
            lambda tags: any(tag_lower in (t or '').lower() for t in (tags or []))
        )
        return self.df[mask].copy()
    
    def get_top_rated(self, n: int = 10) -> pd.DataFrame:
        """Get top N rated attractions"""
        return self.df.nlargest(n, 'rating').copy()
    
    def get_cities(self) -> List[str]:
        """Get list of all cities"""
        return sorted(self.df['city'].dropna().unique().tolist())
    
    def get_categories(self) -> List[str]:
        """Get list of all categories"""
        return sorted(self.df['category'].dropna().unique().tolist())
    
    def search(self, query: str) -> pd.DataFrame:
        """Search attractions by name or description"""
        query_lower = query.lower()
        mask = (
            self.df['name'].str.lower().str.contains(query_lower, na=False) |
            self.df.get('description', pd.Series([''] * len(self.df))).str.lower().str.contains(query_lower, na=False)
        )
        return self.df[mask].copy()
    
    def get_stats(self) -> Dict:
        """Get statistics about attractions"""
        return {
            'total': len(self.df),
            'cities': len(self.df['city'].dropna().unique()),
            'categories': len(self.df['category'].dropna().unique()),
            'avg_rating': round(self.df['rating'].mean(), 2),
            'avg_duration': round(self.df['visit_duration_hours'].mean(), 2)
        }