import streamlit as st
import pandas as pd
import json
import os
import io
from datetime import datetime
from urllib.parse import quote_plus

# ✅ CRITICAL: Use car-based generator
from itinerary_generator_car import generate_simple_trip
from document_generator import build_word_doc
from restaurant_service import get_restaurant_tips
from text_norm import canonicalize_city, norm_key  # ✅ NEW: Import text normalization

# Configuration
TRIPS_DIR = "trips"
os.makedirs(TRIPS_DIR, exist_ok=True)

POI_CATEGORIES = [
    "art", "museums", "history", "architecture", "parks", "nature",
    "gardens", "beaches", "viewpoints", "markets", "religious", "castles",
    "palaces", "neighborhoods", "food & tapas", "wine & bodegas",
    "music & flamenco"
]

def calculate_driving_time(distance_km):
    """Calculate driving time"""
    if distance_km < 30:
        return distance_km / 40 + 0.25
    elif distance_km < 100:
        return distance_km / 70 + 0.25
    else:
        return distance_km / 100 + 0.75

def load_prefs():
    default = {
        "default_trip_type": "Point-to-point",  # Can be Point-to-point, Circular, or Star/Hub
        "default_budget": "mid-range",
        "default_pace": "medium",
        "max_km_per_day": 200,
        "poi_categories": ["history", "architecture", "museums", "parks"],
        "hotel_platform": "Any",
        "max_price_per_night": 150,
        "min_poi_rating": 0.0,
        "max_same_category_per_day": 2
    }
    try:
        if os.path.exists("preferences.json"):
            with open("preferences.json", "r", encoding="utf-8") as f:
                saved = json.load(f) or {}
                default.update(saved)
    except Exception:
        pass
    return default

def build_hotel_links(hotel, city):
    name = hotel.get("name", "")
    booking = hotel.get("booking_url")
    airbnb = hotel.get("airbnb_url")
    
    if not booking:
        q = quote_plus(f"{name} {city}") if name else quote_plus(city)
        booking = f"https://www.booking.com/searchresults.html?ss={q}"
    if not airbnb:
        q = quote_plus(city)
        airbnb = f"https://www.airbnb.com/s/{q}/homes?query={q}"
    
    return f"[Booking]({booking})", f"[Airbnb]({airbnb})"

def show_trip_planner_full(attractions, hotels, restaurants=None):
    """Main trip planner UI with city name normalization"""
    
    if restaurants is None:
        restaurants = []
    
    # ✅ NEW: Build set of known cities from attractions data
    known_cities = {(item.get("city") or "").strip() for item in attractions}
    known_cities.discard("")  # Remove empty strings
    
    st.title("✈️ Plan a New Trip")
    
    prefs_state = load_prefs()
    
    if 'form_submitted' not in st.session_state:
        st.session_state.form_submitted = False
    
    if 'form_data' not in st.session_state:
        st.session_state.form_data = {
            'start_end_text': "",
            'special_requests': "",
            'trip_days': 7,
            'trip_type': prefs_state["default_trip_type"],
            'max_km': int(prefs_state["max_km_per_day"]),
            'budget': prefs_state["default_budget"],
            'pace': prefs_state["default_pace"],
            'platform_pref': prefs_state["hotel_platform"],
            'max_price_per_night': int(prefs_state.get("max_price_per_night", 150)),
            'cats': [c for c in prefs_state["poi_categories"] if c in POI_CATEGORIES],
            'max_same_category': int(prefs_state.get("max_same_category_per_day", 2))
        }
    
    with st.form("trip_form"):
        start_end_text = st.text_input("Start & End Location", 
                                      value=st.session_state.form_data['start_end_text'],
                                      placeholder="e.g., Malaga to Seville",
                                      help="You can use city names with or without accents (Malaga = Málaga)")
        
        colA, colB, colC = st.columns(3)
        with colA:
            trip_type_options = ["Point-to-point", "Circular", "Star/Hub"]
            current_trip_type = st.session_state.form_data.get('trip_type', 'Point-to-point')
            if current_trip_type not in trip_type_options:
                current_trip_type = 'Point-to-point'
            trip_type = st.selectbox("Trip Type", trip_type_options, 
                                   index=trip_type_options.index(current_trip_type),
                                   help="Point-to-point: A→B | Circular: Loop | Star/Hub: Day trips ⭐")
        with colB:
            days = st.slider("Duration (days)", 3, 14, st.session_state.form_data['trip_days'])
        with colC:
            max_km = st.number_input("Max driving km/day", min_value=50, max_value=500, 
                                   value=st.session_state.form_data['max_km'], step=10)
        
        special = st.text_area("Special Requests", 
                              value=st.session_state.form_data['special_requests'],
                              placeholder="e.g., avoid Marbella, must see Seville, stay 2 days in Granada",
                              help="Natural language: 'avoid [city]', 'must see [city]', 'stay X days in [city]'")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            budget_options = ["budget", "mid-range", "luxury"]
            budget = st.selectbox("Budget", budget_options, 
                                index=budget_options.index(st.session_state.form_data['budget']))
        with col2:
            pace_options = ["easy", "medium", "fast"]
            pace = st.selectbox("Travel pace", pace_options, 
                              index=pace_options.index(st.session_state.form_data['pace']))
        with col3:
            platform_options = ["Any", "Booking", "Airbnb"]
            platform_pref = st.selectbox("Hotel platform", platform_options, 
                                       index=platform_options.index(st.session_state.form_data['platform_pref']))
        with col4:
            max_price_per_night = st.number_input("Max hotel (€/night)", min_value=0, step=10, 
                                                value=st.session_state.form_data['max_price_per_night'], 
                                                help="0 = no cap")
        
        cats = st.multiselect("POI categories", POI_CATEGORIES, 
                            default=st.session_state.form_data['cats'])
        
        max_same_category = st.slider("🎨 Max same category per day (Diversity)", 
                                     min_value=1, max_value=4, 
                                     value=st.session_state.form_data['max_same_category'])
        
        submitted = st.form_submit_button("✨ Generate Trip")
        
        if submitted:
            # ✅ NEW: Normalize city names in the start_end_text
            normalized_text = normalize_start_end_text(start_end_text, known_cities)
            
            st.session_state.form_data = {
                'start_end_text': normalized_text,  # ✅ Use normalized version
                'special_requests': special,
                'trip_days': days,
                'trip_type': trip_type,
                'max_km': max_km,
                'budget': budget,
                'pace': pace,
                'platform_pref': platform_pref,
                'max_price_per_night': int(max_price_per_night),
                'cats': cats,
                'max_same_category': max_same_category
            }
            
            # ✅ NEW: Show normalization feedback
            if normalized_text != start_end_text:
                st.success(f"✓ Matched: '{start_end_text}' → '{normalized_text}'")
            
            st.session_state.form_submitted = True
    
    if st.session_state.form_submitted and st.session_state.form_data['start_end_text']:
        form_vals = st.session_state.form_data
        
        prefs = {
            "trip_type": form_vals['trip_type'],  # ✅ CRITICAL FIX: Add trip_type!
            "budget": form_vals['budget'],
            "pace": form_vals['pace'],
            "notes": form_vals['special_requests'],
            "max_km_per_day": form_vals['max_km'],
            "poi_categories": form_vals['cats'],
            "hotel_platform": form_vals['platform_pref'],
            "max_price_per_night": form_vals['max_price_per_night'],
            "min_poi_rating": float(prefs_state.get("min_poi_rating", 0.0)),
            "max_same_category_per_day": form_vals['max_same_category'],
        }
        
        with st.spinner("Generating your itinerary..."):
            # ✅ Call generate_simple_trip from itinerary_generator module
            result = generate_simple_trip(
                form_vals['start_end_text'], 
                form_vals['trip_days'], 
                prefs, 
                form_vals['trip_type'], 
                attractions, 
                hotels,
                restaurants  # ✅ Added restaurants
            )
        
        if not result or not result.get("itinerary"):
            st.error("Could not generate itinerary.")
            st.session_state.form_submitted = False
            return
        
        st.session_state.current_trip_result = result
        st.session_state.current_trip_prefs = prefs
        st.session_state.current_trip_days = form_vals['trip_days']
    
    if 'current_trip_result' in st.session_state:
        display_itinerary(
            st.session_state.current_trip_result, 
            st.session_state.current_trip_prefs, 
            st.session_state.current_trip_days, 
            attractions, 
            hotels,
            restaurants
        )

# ✅ NEW: Helper function to normalize start/end text
def normalize_start_end_text(text, known_cities):
    """
    Normalize city names in 'Start to End' text
    Examples:
        'Malaga to Seville' → 'Málaga to Seville'
        'malaga' → 'Málaga'
        'cordoba to cadiz' → 'Córdoba to Cádiz'
    """
    if not text:
        return text
    
    # Handle both " to " and "-" separators (case-insensitive)
    import re
    match = re.search(r'\s+to\s+', text, re.IGNORECASE)
    
    if match:
        # Split using the matched separator
        parts = re.split(r'\s+to\s+', text, maxsplit=1, flags=re.IGNORECASE)
        if len(parts) == 2:
            start_normalized = canonicalize_city(parts[0].strip(), known_cities)
            end_normalized = canonicalize_city(parts[1].strip(), known_cities)
            
            if start_normalized and end_normalized:
                return f"{start_normalized} to {end_normalized}"
            elif start_normalized:
                return f"{start_normalized} to {parts[1].strip()}"
            elif end_normalized:
                return f"{parts[0].strip()} to {end_normalized}"
    
    # Single city (circular trip)
    normalized = canonicalize_city(text.strip(), known_cities)
    if normalized:
        return normalized
    
    # Return original if no match
    return text

def display_itinerary(result, prefs, days, attractions, hotels, restaurants):
    """Display generated itinerary"""
    itinerary = result.get("itinerary", [])
    hop_kms = result.get("hop_kms", [])  # FIXED: was "hop_km_list"
    maps_link = result.get("maps_link", "")
    ordered_cities = result.get("ordered_cities", [])
    is_car_mode = result.get("is_car_mode", True)
    
    st.success(f"✅ Generated {days}-day {'road trip' if is_car_mode else 'itinerary'}!")
    
    if not itinerary:
        st.warning("No itinerary data to display")
        return
    
    # Show route overview
    if ordered_cities:
        st.markdown("### 📍 Route")
        route_str = " → ".join(ordered_cities)
        st.info(f"**{route_str}**")
    
    # Show special requests acknowledgment
    parsed_req = result.get("parsed_requests", {})
    if parsed_req:
        st.markdown("### ✓ Special Requests Applied")
        col1, col2, col3 = st.columns(3)
        if parsed_req.get("must_see_cities"):
            with col1:
                st.success(f"Must see: {', '.join(parsed_req['must_see_cities'])}")
        if parsed_req.get("avoid_cities"):
            with col2:
                st.warning(f"Avoiding: {', '.join(parsed_req['avoid_cities'])}")
        if parsed_req.get("stay_requests"):
            with col3:
                stays = [f"{s['city']} ({s['days']}d)" for s in parsed_req['stay_requests']]
                st.info(f"Extended stays: {', '.join(stays)}")
    
    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_km = sum(d.get("driving_km", 0) for d in itinerary)
        st.metric("🚗 Total Driving", f"{total_km} km")
    
    with col2:
        total_hours = sum(d.get("driving_hours", 0) for d in itinerary)
        st.metric("⏱️ Drive Time", f"{total_hours:.1f}h")
    
    with col3:
        total_pois = sum(len(cs.get("attractions", [])) for d in itinerary for cs in d.get("cities", []))
        st.metric("📍 Total POIs", total_pois)
    
    with col4:
        avg_pois = total_pois / len(itinerary) if itinerary else 0
        st.metric("📊 Avg POIs/day", f"{avg_pois:.1f}")
    
    # Day-by-day itinerary
    st.markdown("---")
    st.markdown("### 📅 Daily Itinerary")
    
    for day_data in itinerary:
        day_num = day_data.get("day", 0)
        day_type = day_data.get("type", "base_city")
        overnight = day_data.get("overnight_city", day_data.get("city", "Unknown"))
        
        # Day header
        if day_type == "driving_day":
            st.markdown(f"## Day {day_num} 🚗 Driving Day → {overnight}")
        elif day_type == "day_trip":
            base = day_data.get("base", "?")
            st.markdown(f"## Day {day_num} 🏖️ Day Trip from {base}")
        else:
            st.markdown(f"## Day {day_num} 📍 {overnight}")
        
        # Driving info
        driving_km = day_data.get("driving_km", 0)
        driving_hours = day_data.get("driving_hours", 0)
        if driving_km > 0:
            col1, col2 = st.columns(2)
            with col1:
                st.info(f"🚗 **Driving:** {driving_km} km (~{driving_hours:.1f}h)")
            with col2:
                if day_type == "day_trip":
                    st.info("🏨 **Overnight:** Same base city")
                else:
                    st.info(f"🏨 **Overnight:** {overnight}")
        
        # Cities visited
        cities_list = day_data.get("cities", [])
        for city_stop in cities_list:
            city_name = city_stop.get("city", "Unknown")
            
            # POIs
            pois = city_stop.get("attractions", [])
            if pois:
                st.markdown(f"### 📍 {city_name} ({len(pois)} attractions)")
                
                for idx, poi in enumerate(pois, 1):
                    with st.expander(f"**{idx}. {poi.get('name', 'Unknown')}**", expanded=False):
                        col1, col2 = st.columns([2, 1])
                        
                        with col1:
                            desc = poi.get("description", "No description")
                            st.write(desc)
                            
                            if poi.get("insider_tip"):
                                st.info(f"💡 **Tip:** {poi['insider_tip']}")
                        
                        with col2:
                            if poi.get("rating"):
                                st.metric("⭐ Rating", f"{poi['rating']}/10")
                            if poi.get("duration"):
                                st.metric("⏱️ Duration", poi["duration"])
                            if poi.get("price"):
                                st.metric("💶 Price", poi["price"])
                            
                            category = poi.get("category", "")
                            if category:
                                st.caption(f"🏷️ {category}")
        
        # Restaurants
        lunch = day_data.get("lunch_restaurant")
        dinner = day_data.get("dinner_restaurant")
        
        if lunch or dinner:
            st.markdown("### 🍽️ Dining")
            rest_col1, rest_col2 = st.columns(2)
            
            with rest_col1:
                if lunch:
                    st.markdown(f"**🥗 Lunch:** {lunch.get('name', 'N/A')}")
                    if lunch.get("cuisine"):
                        st.caption(f"Cuisine: {lunch['cuisine']}")
                    if lunch.get("address"):
                        st.caption(f"📍 {lunch['address']}")
            
            with rest_col2:
                if dinner:
                    st.markdown(f"**🍷 Dinner:** {dinner.get('name', 'N/A')}")
                    if dinner.get("cuisine"):
                        st.caption(f"Cuisine: {dinner['cuisine']}")
                    if dinner.get("address"):
                        st.caption(f"📍 {dinner['address']}")
        
        # Hotels
        hotels_list = day_data.get("hotels", [])
        if hotels_list:
            st.markdown("### 🏨 Accommodation")
            for hotel in hotels_list:
                booking_link, airbnb_link = build_hotel_links(hotel, overnight)
                
                h_col1, h_col2, h_col3 = st.columns([2, 1, 1])
                with h_col1:
                    st.markdown(f"**{hotel.get('name', 'Unknown')}**")
                    if hotel.get("address"):
                        st.caption(f"📍 {hotel['address']}")
                with h_col2:
                    st.markdown(booking_link)
                with h_col3:
                    st.markdown(airbnb_link)
        
        st.markdown("---")
    
    # Maps link
    if maps_link:
        st.markdown("### 🗺️ Route Map")
        st.markdown(f"[Open in Google Maps]({maps_link})")
    
    # AI insights
    if is_car_mode:
        generate_ai_insights(itinerary, ordered_cities, is_car_mode=True)
    
    # Export options
    st.markdown("---")
    st.markdown("### 💾 Export Options")
    
    col1, col2, col3 = st.columns(3)
    
    # Excel export
    with col1:
        try:
            excel_file = build_excel(itinerary, hop_kms, maps_link, ordered_cities, days, prefs, is_car_mode)
            st.download_button(
                label="📊 Download Excel",
                data=excel_file,
                file_name=f"andalusia_trip_{datetime.now().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
        except Exception as e:
            st.error(f"❌ Error generating Excel: {str(e)}")
    
    # Word export
    with col2:
        try:
            parsed_req = result.get("parsed_requests", {})
            word_doc = build_word_doc(itinerary, hop_kms, maps_link, ordered_cities, days, prefs, parsed_req, is_car_mode)
            st.download_button(
                label="📝 Download Word Doc",
                data=word_doc,
                file_name=f"andalusia_trip_{datetime.now().strftime('%Y%m%d')}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True
            )
        except Exception as e:
            st.error(f"❌ Error generating document: {str(e)}")
    
    # JSON export
    with col3:
        json_data = json.dumps(result, ensure_ascii=False, indent=2)
        st.download_button(
            label="💾 Download JSON",
            data=json_data,
            file_name=f"andalusia_trip_{datetime.now().strftime('%Y%m%d')}.json",
            mime="application/json",
            use_container_width=True
        )


def generate_ai_insights(itinerary, ordered_cities, is_car_mode=False):
    """Generate AI travel insights with car-specific tips"""
    
    try:
        from dotenv import load_dotenv
        load_dotenv()
        api_key = os.getenv("GEMINI_API_KEY")
        
        if not api_key:
            st.info("💡 **Pro tip:** Set GEMINI_API_KEY in .env file for AI-powered travel insights!")
            
            if is_car_mode:
                st.markdown("""
                **Car Road Trip Tips:**
                - Book car rental in advance for better rates
                - Full insurance coverage recommended
                - Download offline maps before departure
                - Keep highway toll change handy (€20-30 total)
                - Gas stations frequent, credit cards widely accepted
                """)
            else:
                st.markdown("""
                **Manual Travel Tips:**
                - Book major attractions in advance
                - Lunch: 2-4pm, Dinner: after 9pm
                - Many museums closed Mondays
                """)
            return
        
        try:
            from google import genai
            
            client = genai.Client(api_key=api_key)
            
            cities_str = ", ".join(ordered_cities)
            attractions_list = []
            for day in itinerary:
                for city_stop in day.get("cities", []):
                    for attr in city_stop.get("attractions", []):
                        attractions_list.append(attr.get("name", ""))
            
            attractions_str = ", ".join(attractions_list[:10])
            
            if is_car_mode:
                prompt = f"""Travel expert for Andalusia road trip by car.
Road Trip: {len(itinerary)} days
Base Cities: {cities_str}
Key Attractions: {attractions_str}

Provide road trip advice:
1) Brief 2-sentence overview of this road trip route
2) 3 car-specific tips (parking, tolls, scenic routes)
3) 1 must-try roadside food/restaurant stop
4) Best times to drive to avoid traffic

Keep it practical and car-focused."""
            else:
                prompt = f"""Travel expert for Andalusia, Spain.
Trip: {len(itinerary)} days
Route: {cities_str}
Key Attractions: {attractions_str}

Provide concise travel advice:
1) Brief 2-sentence overview
2) 3 insider tips
3) 1 must-try dish
4) Best times to visit attractions

Keep it practical."""
            
            with st.spinner("✨ Generating AI insights..."):
                response = client.models.generate_content(
                    model="gemini-2.0-flash-exp",
                    contents=prompt
                )
                
                if hasattr(response, 'text'):
                    insights = response.text
                elif hasattr(response, 'candidates') and len(response.candidates) > 0:
                    insights = response.candidates[0].content.parts[0].text
                else:
                    insights = str(response)
                
                st.markdown("### 🎯 AI Travel Recommendations")
                st.markdown(insights)
                st.caption("_Generated by Gemini AI_")
        
        except ImportError:
            st.info("💡 Install `google-genai` for AI insights")
        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
                st.warning("⏳ AI insights temporarily unavailable (rate limit reached). Your itinerary is complete!")
            elif "API" in error_msg or "key" in error_msg.lower():
                st.info("💡 AI insights require API configuration")
            else:
                st.caption(f"💡 AI insights unavailable: {error_msg}")
    
    except Exception as e:
        # Outer exception - don't show error, AI insights are optional
        pass


def build_excel(itinerary, hop_kms, maps_link, ordered_cities, days, prefs, is_car_mode=False):
    """Build Excel export with car-specific columns"""
    import pandas as pd
    import io
    
    rows = []
    for i, d in enumerate(itinerary):
        day_type = d.get("type", "base_city")
        overnight = d.get("overnight_city", d.get("city", "?"))
        city_visited = d.get("city", "?")
        base = d.get("base", city_visited)
        
        cities_list = d.get("cities", [])
        all_pois = []
        for city_stop in cities_list:
            all_pois.extend(city_stop.get("attractions", []))
        
        poi_names = ", ".join(a.get("name") or "Unknown" for a in all_pois if a.get("name"))
        hotel_names = ", ".join(h.get("name") or "?" for h in d.get("hotels", []) if h.get("name"))
        
        lunch_restaurant = d.get("lunch_restaurant")
        lunch_name = lunch_restaurant.get("name", "") if lunch_restaurant else ""

        dinner_restaurant = d.get("dinner_restaurant")
        dinner_name = dinner_restaurant.get("name", "") if dinner_restaurant else ""
        
        driving_km = d.get("driving_km", 0)
        driving_hours = d.get("driving_hours", 0)
        
        row_data = {
            "Day": d["day"],
            "City": city_visited,
            "POIs": poi_names,
            "Hotels": hotel_names,
            "Lunch": lunch_name,
            "Dinner": dinner_name
        }
        
        if is_car_mode:
            row_data["Type"] = day_type.replace("_", " ").title()
            row_data["Base"] = base
            row_data["Driving (km)"] = driving_km
            row_data["Drive Time (h)"] = driving_hours
        
        rows.append(row_data)
    
    df = pd.DataFrame(rows)
    
    # Reorder columns for car mode
    if is_car_mode:
        col_order = ["Day", "Type", "Base", "City", "Driving (km)", "Drive Time (h)", "POIs", "Hotels", "Lunch", "Dinner"]
        df = df[[c for c in col_order if c in df.columns]]
    
    bio = io.BytesIO()
    with pd.ExcelWriter(bio, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="Itinerary")
        
        # Summary sheet
        summary_data = {
            "Trip Type": ["Road Trip (Car)" if is_car_mode else "Walking/Transit"],
            "Start": [ordered_cities[0] if ordered_cities else "?"],
            "End": [ordered_cities[-1] if len(ordered_cities) > 1 else ordered_cities[0]],
            "Days": [days],
            "Base Cities": [len(ordered_cities) if is_car_mode else "N/A"],
            "Total Driving (km)": [sum(d.get('driving_km', 0) for d in itinerary)] if is_car_mode else ["N/A"],
            "Budget": [prefs.get("budget", "?")],
            "Pace": [prefs.get("pace", "?")]
        }
        summary_df = pd.DataFrame(summary_data)
        summary_df.to_excel(writer, index=False, sheet_name="Summary")
    
    bio.seek(0)
    return bio

def save_trip(result, prefs, ordered_cities, days):
    """Save trip to file"""
    from datetime import datetime
    
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    fname = f"{TRIPS_DIR}/roadtrip_{ts}.json"
    
    parsed_requests = result.get("parsed_requests", {})
    
    payload = {
        "created_at": ts,
        "trip_type": "car_road_trip",
        "start_end_text": " to ".join(ordered_cities[:2]) if len(ordered_cities) >= 2 else ordered_cities[0],
        "days": days,
        "preferences": prefs,
        "ordered_cities": ordered_cities,
        "base_cities": result.get("base_cities", ordered_cities),
        "special_requests": prefs.get("notes", ""),
        "parsed_requests": parsed_requests,
        "result": result
    }
    
    with open(fname, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    
    st.success(f"✅ Saved road trip: {fname}")