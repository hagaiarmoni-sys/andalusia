# itinerary_builder.py
from typing import List, Dict, Any
import pandas as pd
from sklearn.cluster import KMeans
import numpy as np

def haversine_km(a, b, road_factor=1.3):
    if not a or not b: return 0.0
    R = 6371.0
    dlat = np.radians(b[0] - a[0])
    dlon = np.radians(b[1] - a[1])
    sa = np.sin(dlat / 2) ** 2
    sb = np.cos(np.radians(a[0])) * np.cos(np.radians(b[0])) * np.sin(dlon / 2) ** 2
    dist = 2 * R * np.arctan2(np.sqrt(sa + sb), np.sqrt(1 - (sa + sb)))
    return dist * road_factor

class ItineraryBuilder:
    def __init__(self, attraction_service, route_service):
        self.attractions = attraction_service
        self.routes = route_service

    def create_multi_city_itinerary(self, cities_ordered, total_days, options):
        options = options or {}
        hours_per_day = float(options.get("hours_per_day", 8.0))
        min_rating = float(options.get("min_rating", 0.0))
        allowed_cats = {c.lower() for c in options.get("poi_categories", [])}
        max_same_cat = int(options.get("max_same_category_per_day", 99))
        max_daily_budget = float(options.get("max_daily_budget", 50.0))
        stay_duration = options.get("stay_duration", {})

        cities = [c for c in cities_ordered if c]
        if not cities: raise ValueError("No cities")

        city_poi_counts = {}
        for city in cities:
            df = self.attractions.get_by_city(city)
            if df is None or df.empty:
                city_poi_counts[city] = 0
                continue
            df = df[df["rating"] >= min_rating]
            if allowed_cats: df = df[df["category"].str.lower().isin(allowed_cats)]
            city_poi_counts[city] = len(df)

        total_pois = sum(city_poi_counts.values())
        itinerary = []
        current_day = 1

        city_days = {}
        if stay_duration:
            for city in cities:
                city_days[city] = stay_duration.get(city, 1)
            total_assigned = sum(city_days.values())
            if total_assigned > total_days:
                raise ValueError("Stay durations exceed total days")
            remaining = total_days - total_assigned
        else:
            remaining = total_days

        if remaining > 0:
            if total_pois > 0:
                for city in cities:
                    prop = city_poi_counts.get(city, 0) / total_pois
                    extra = max(0, int(round(prop * remaining)))
                    city_days[city] = city_days.get(city, 0) + extra
            else:
                per_city = remaining // len(cities)
                for city in cities:
                    city_days[city] = city_days.get(city, 0) + per_city
                leftovers = remaining - sum(city_days.values())
                for i in range(leftovers):
                    city_days[cities[i % len(cities)]] += 1

        for i, city in enumerate(cities):
            days_for_city = city_days.get(city, 1)
            planned_days = self._build_city_days(city, days_for_city, hours_per_day, min_rating, allowed_cats, max_same_cat, max_daily_budget)
            travel_km = 0.0
            if i < len(cities) - 1:
                travel_km = self._estimate_travel_km(city, cities[i + 1])
            for d in planned_days:
                d["day"] = current_day
                d["travel_km"] = travel_km if d is planned_days[-1] else 0.0
                itinerary.append(d)
                current_day += 1
            while len(planned_days) < days_for_city:
                itinerary.append({"day": current_day, "city": city, "attractions": [], "total_hours": 0, "travel_km": 0.0})
                current_day += 1

        last_city = cities[-1]
        while len(itinerary) < total_days:
            itinerary.append({"day": len(itinerary) + 1, "city": last_city, "attractions": [], "total_hours": 0, "travel_km": 0.0})

        return {"itinerary": itinerary, "cities": cities}

    def _build_city_days(self, city, days, hours_per_day, min_rating, allowed_cats, max_same_cat, max_daily_budget):
        df = self.attractions.get_by_city(city)
        if df is None or df.empty: return []
        df = df[df["rating"] >= min_rating]
        if allowed_cats: df = df[df["category"].str.lower().isin(allowed_cats)]
        df = df[df["entrance_fee_value"].apply(lambda x: float(x or 0) <= max_daily_budget)]
        if df.empty: return []

        if "is_must_see_attraction" in df.columns:
            df["priority"] = df["is_must_see_attraction"].apply(lambda x: 3 if x else 0)
        else:
            df["priority"] = 0
        df = df.sort_values(["priority", "rating", "visit_duration_hours"], ascending=[False, False, True])
        rows = df.to_dict("records")

        planned_days = []
        used = set()
        for _ in range(days):
            day_pois, time_used = self._pack_day(rows, hours_per_day, max_same_cat, max_daily_budget, used)
            planned_days.append({"city": city, "attractions": day_pois, "total_hours": round(time_used, 2)})
        return planned_days

    def _pack_day(self, rows, hours_per_day, max_same_cat, max_daily_budget, used):
        day_pois = []
        cat_counts = {}
        time_left = hours_per_day
        total_cost = 0.0
        for rec in sorted(rows, key=lambda x: (x.get("priority", 0), x.get("rating", 0)), reverse=True):
            key = (rec.get("name"), rec.get("city"))
            if key in used: continue
            dur = float(rec.get("visit_duration_hours") or 0.0)
            fee = float(rec.get("entrance_fee_value") or 0.0)
            if dur <= 0 or dur > time_left or total_cost + fee > max_daily_budget: continue
            cat = (rec.get("category") or "").lower()
            if max_same_cat and cat_counts.get(cat, 0) >= max_same_cat: continue
            day_pois.append(rec)
            used.add(key)
            cat_counts[cat] = cat_counts.get(cat, 0) + 1
            time_left -= dur
            total_cost += fee
            if len(day_pois) >= 12: break
        return day_pois, hours_per_day - time_left

    def _estimate_travel_km(self, a, b):
        df_a = self.attractions.get_by_city(a)
        df_b = self.attractions.get_by_city(b)
        if df_a is None or df_a.empty or df_b is None or df_b.empty: return 0.0
        ca = (df_a["lat"].mean(), df_a["lon"].mean())
        cb = (df_b["lat"].mean(), df_b["lon"].mean())
        return haversine_km(ca, cb)