# pages/trip_planner_page.py
import streamlit as st
import os, json, math
from datetime import datetime
from urllib.parse import quote_plus
from special_requests_parser import parse_special_requests, validate_requests

TRIPS_DIR = "trips"
os.makedirs(TRIPS_DIR, exist_ok=True)

# ------------------------------------------------------------------
# Helper utils
# ------------------------------------------------------------------
def normalize_city(name): return ''.join(c for c in name.lower() if c.isalnum())

def parse_start_end(text, trip_type):
    if not text: return None, None
    parts = [p.strip() for p in text.split(" to ") if p.strip()]
    if len(parts) == 2: return parts[0], parts[1]
    return text.strip(), text.strip() if trip_type == "Circular" else None

def haversine_km(a, b):
    if not a or not b: return float('inf')
    R = 6371.0
    dlat = math.radians(b[0] - a[0])
    dlon = math.radians(b[1] - a[1])
    sa = math.sin(dlat/2)**2
    sb = math.cos(math.radians(a[0]))*math.cos(math.radians(b[0]))*math.sin(dlon/2)**2
    return 2*R*math.atan2(math.sqrt(sa+sb), math.sqrt(1-(sa+sb))) * 1.3

def get_centroids(attractions, hotels):
    buckets = {}
    for item in (attractions or []) + (hotels or []):
        city = item.get("city")
        lat = item.get("lat") or item.get("coordinates", {}).get("lat")
        lon = item.get("lon") or item.get("coordinates", {}).get("lon")
        if city and lat and lon:
            b = buckets.setdefault(city, {"n":0, "lat":0.0, "lon":0.0})
            b["n"] += 1
            b["lat"] += float(lat)
            b["lon"] += float(lon)
    return {c:(b["lat"]/b["n"], b["lon"]/b["n"]) for c,b in buckets.items() if b["n"]>0}

def insert_enroute_cities(ordered, days, parsed, centroids, prefs, service):
    known = set(ordered)
    avoid = {normalize_city(c) for c in parsed.get("avoid_cities",[])}
    stay = parsed.get("stay_durations", {})
    cur = sum(stay.get(c,1) for c in ordered)
    if cur >= days: return ordered, stay

    candidates = [c for c in centroids.keys() if normalize_city(c) not in avoid and c not in known]
    poi_cnt = {c:len(service.get_by_city(c)) for c in candidates if len(service.get_by_city(c))>0}

    while cur < days and poi_cnt:
        best_city, best_pos, best_score = None, None, -1
        for cand in poi_cnt:
            for i in range(1, len(ordered)):
                prev, nxt = ordered[i-1], ordered[i]
                d = (haversine_km(centroids.get(prev), centroids.get(cand)) +
                     haversine_km(centroids.get(cand), centroids.get(nxt)) -
                     haversine_km(centroids.get(prev), centroids.get(nxt)))
                if d > 120: continue
                score = poi_cnt[cand] / (1 + d/10)
                if score > best_score:
                    best_score, best_city, best_pos = score, cand, i
        if not best_city: break
        ordered.insert(best_pos, best_city)
        stay[best_city] = 1
        cur += 1
        del poi_cnt[best_city]
    return ordered, stay

# ------------------------------------------------------------------
# Main generator
# ------------------------------------------------------------------
def generate_simple_trip(start_end_text, days, prefs, trip_type,
                         attractions, hotels, route_service, special_requests):
    start, end = parse_start_end(start_end_text, trip_type)
    if not start:
        st.error("Enter a start city.")
        return

    from attraction_service import AttractionService
    service = AttractionService(attractions)
    centroids = get_centroids(attractions, hotels)

    parsed = parse_special_requests(special_requests or "")
    if not validate_requests(parsed):
        st.error("Invalid special request.")
        return

    ordered = [start]
    if end and end != start: ordered.append(end)
    for city in parsed.get("must_see_cities", []):
        if city not in ordered: ordered.insert(-1, city)

    ordered, stay_durations = insert_enroute_cities(
        ordered, days, parsed, centroids, prefs, service)

    hop_kms = [round(haversine_km(centroids.get(ordered[i]), centroids.get(ordered[i+1])))
               for i in range(len(ordered)-1)]
    total_km = sum(hop_kms)

    # ---- itinerary -------------------------------------------------
    from itinerary_builder import ItineraryBuilder
    builder = ItineraryBuilder(service, route_service)
    options = {
        "hours_per_day": 8.0,
        "min_rating": prefs.get("min_poi_rating", 0.0),
        "poi_categories": prefs.get("poi_categories", []),
        "max_same_category_per_day": prefs.get("max_same_category_per_day", 2),
        "max_daily_budget": prefs.get("max_daily_budget", 50.0),
        "stay_duration": stay_durations
    }
    itinerary = builder.create_multi_city_itinerary(ordered, days, options)["itinerary"]

    # ---- hotels ----------------------------------------------------
    hotel_by_city = {}
    for h in hotels:
        c = h.get("city")
        if c: hotel_by_city.setdefault(c, []).append(h)

    for day in itinerary:
        city = day.get("city")
        lst = hotel_by_city.get(city, [])
        def score(h):
            r = h.get("guest_rating") or h.get("star_rating") or 0.0
            p = h.get("avg_price_per_night_couple")
            p = float(p) if p and str(p).replace('.','').isdigit() else 999.0
            return (float(r), -p)
        lst.sort(key=score, reverse=True)
        day["hotels"] = lst[:3]

    # ---- display ---------------------------------------------------
    st.markdown(f"**Route:** {' → '.join(ordered)}  ·  [Google Maps](https://www.google.com/maps/dir/{'/'.join(quote_plus(c) for c in ordered)})")
    st.caption(f"Total ≈ {int(total_km)} km")

    for day in itinerary:
        with st.expander(f"Day {day['day']}: {day.get('city','?')}", expanded=day['day']==1):
            ats = day.get("attractions", [])
            if ats:
                st.markdown("### Attractions")
                for a in ats:
                    name = a.get("name","?")
                    info = [f"{a.get('rating',0)}", f"{a.get('visit_duration_hours',0)}h"]
                    if a.get("entrance_fee"): info.append(a["entrance_fee"])
                    st.write(f"**{name}** — {a.get('description','')}")
                    if info: st.caption(" · ".join(info))
            htls = day.get("hotels",[])
            if htls:
                st.markdown("### Hotels")
                for h in htls:
                    r = h.get("guest_rating") or h.get("star_rating")
                    p = h.get("avg_price_per_night_couple")
                    txt = f"- **{h.get('name','?')}**"
                    if p: txt += f" — €{p}/night"
                    if r: txt += f" {r}/10"
                    st.write(txt)

    # ---- save ------------------------------------------------------
    if st.button("Save Trip"):
        fn = f"{TRIPS_DIR}/trip_{datetime.now():%Y%m%d_%H%M%S}_{normalize_city(ordered[0])}_to_{normalize_city(ordered[-1])}_{days}d.json"
        data = {"ordered_cities": ordered, "itinerary": itinerary, "hop_kms": hop_kms}
        with open(fn, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        st.success("Trip saved!")

# ------------------------------------------------------------------
# Page entry point
# ------------------------------------------------------------------
def show_trip_planner_full(attractions, hotels, route_service):
    st.title("Plan Your Andalusia Trip")

    # Load saved preferences (or defaults)
    prefs_file = "preferences.json"
    if os.path.exists(prefs_file):
        with open(prefs_file, "r", encoding="utf-8") as f:
            prefs = json.load(f)
    else:
        prefs = {
            "poi_categories": ["history","architecture","museums","parks"],
            "min_poi_rating": 0.0,
            "max_same_category_per_day": 2,
            "max_daily_budget": 50.0
        }

    with st.form("trip_form"):
        col1, col2, col3 = st.columns(3)
        with col1: start_end = st.text_input("From → To", "Seville to Málaga")
        with col2: days = st.number_input("Days", 1, 30, 8)
        with col3: trip_type = st.selectbox("Trip type", ["Point-to-point","Circular"])
        special = st.text_area("Special requests",
                               placeholder="spend 2 days in Granada, avoid Marbella")
        go = st.form_submit_button("Plan Trip")

    if go:
        generate_simple_trip(start_end, days, prefs, trip_type,
                             attractions, hotels, route_service, special)