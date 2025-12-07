"""
Andalusia Travel Guide - Streamlit App
Main application file
"""
import streamlit as st
import json
import pandas as pd
from attraction_service import AttractionService
from route_service import RouteService
from filter_service import FilterService

# Page configuration
st.set_page_config(
    page_title="Andalusia Travel Guide",
    page_icon="🕌",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        color: #667eea;
        text-align: center;
        margin-bottom: 1rem;
    }
    .subtitle {
        text-align: center;
        color: #666;
        margin-bottom: 2rem;
    }
    .stat-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 10px;
        color: white;
        text-align: center;
    }
    .stat-value {
        font-size: 2.5rem;
        font-weight: bold;
    }
    .stat-label {
        font-size: 1rem;
        opacity: 0.9;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_data
def load_data():
    """Load data from JSON files"""
    with open('data/andalusia_attractions_clean.json', 'r', encoding='utf-8') as f:
        attractions_data = json.load(f)
    
    with open('data/andalusia_routes.json', 'r', encoding='utf-8') as f:
        routes_data = json.load(f)
    
    return attractions_data, routes_data


@st.cache_resource
def initialize_services():
    """Initialize all services"""
    attractions_data, routes_data = load_data()
    
    attraction_service = AttractionService(attractions_data)
    route_service = RouteService(routes_data, attraction_service)
    filter_service = FilterService(attraction_service)
    
    return attraction_service, route_service, filter_service


def display_attraction_card(row):
    """Display a single attraction card"""
    with st.container():
        st.markdown(f"### {row['name']}")
        
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            st.write(f"📍 **{row['city']}** | {row['category']}")
        with col2:
            st.write(f"⭐ **{row['rating']}**/10")
        with col3:
            st.write(f"⏱️ **{row['visit_duration_hours']}h**")
        
        st.write(row['description'])
        
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"💰 {row['entrance_fee']}")
        with col2:
            booking_emoji = "✅" if row['advance_booking'] else "❌"
            st.write(f"{booking_emoji} Booking: {'Required' if row['advance_booking'] else 'Not Required'}")
        
        # Tags
        tags_html = " ".join([f'<span style="background:#f0f0f0; padding:4px 10px; border-radius:15px; margin:2px; font-size:0.8rem;">{tag}</span>' for tag in row['tags']])
        st.markdown(tags_html, unsafe_allow_html=True)
        
        st.markdown("---")


def main():
    # Header
    st.markdown('<h1 class="main-header">🕌 Andalusia Travel Guide</h1>', unsafe_allow_html=True)
    st.markdown('<p class="subtitle">Discover the best attractions in Southern Spain</p>', unsafe_allow_html=True)
    
    # Initialize services
    try:
        attraction_service, route_service, filter_service = initialize_services()
    except FileNotFoundError:
        st.error("❌ Data files not found! Please ensure JSON files are in the 'data' folder.")
        st.stop()
    
    # Stats
    stats = attraction_service.get_stats()
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-value">{stats['total']}</div>
            <div class="stat-label">Attractions</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-value">{stats['cities']}</div>
            <div class="stat-label">Cities</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-value">{stats['free']}</div>
            <div class="stat-label">Free</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-value">{stats['avg_rating']}</div>
            <div class="stat-label">Avg Rating</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.header("🎯 Navigation")
        page = st.radio(
            "Choose a page:",
            ["🔍 Explore", "⭐ Top Rated", "🏛️ By City", "🎯 Advanced Filter", "🛣️ En-Route Planner"]
        )
    
    # Main content based on selected page
    if page == "🔍 Explore":
        show_explore_page(attraction_service)
    elif page == "⭐ Top Rated":
        show_top_rated_page(attraction_service)
    elif page == "🏛️ By City":
        show_by_city_page(attraction_service)
    elif page == "🎯 Advanced Filter":
        show_filter_page(attraction_service, filter_service)
    elif page == "🛣️ En-Route Planner":
        show_routes_page(route_service, attraction_service)


def show_explore_page(attraction_service):
    """Explore page with search"""
    st.header("🔍 Explore Attractions")
    
    search_query = st.text_input("Search by name, description, or tags...", placeholder="e.g., palace, mosque, beach")
    
    if search_query:
        results = attraction_service.search(search_query)
        st.write(f"Found **{len(results)}** attractions")
    else:
        results = attraction_service.get_all().head(20)
        st.write("Showing **top 20** attractions")
    
    if len(results) == 0:
        st.info("No attractions found. Try a different search term.")
    else:
        for _, row in results.iterrows():
            display_attraction_card(row)


def show_top_rated_page(attraction_service):
    """Top rated attractions page"""
    st.header("⭐ Top Rated Attractions")
    
    limit = st.slider("Number of attractions to show", 5, 30, 20)
    
    top = attraction_service.get_top_rated(limit)
    
    for _, row in top.iterrows():
        display_attraction_card(row)


def show_by_city_page(attraction_service):
    """Browse by city page"""
    st.header("🏛️ Browse by City")
    
    cities = attraction_service.get_cities()
    selected_city = st.selectbox("Select a city", ["All Cities"] + cities)
    
    if selected_city == "All Cities":
        st.info("Please select a city to view attractions")
    else:
        attractions = attraction_service.get_by_city(selected_city)
        st.write(f"**{len(attractions)}** attractions in {selected_city}")
        
        # Sort option
        sort_by = st.selectbox("Sort by", ["Rating (High to Low)", "Rating (Low to High)", "Duration", "Name"])
        
        if sort_by == "Rating (High to Low)":
            attractions = attractions.sort_values('rating', ascending=False)
        elif sort_by == "Rating (Low to High)":
            attractions = attractions.sort_values('rating', ascending=True)
        elif sort_by == "Duration":
            attractions = attractions.sort_values('visit_duration_hours')
        elif sort_by == "Name":
            attractions = attractions.sort_values('name')
        
        for _, row in attractions.iterrows():
            display_attraction_card(row)


def show_filter_page(attraction_service, filter_service):
    """Advanced filter page"""
    st.header("🎯 Advanced Filter")
    
    col1, col2 = st.columns(2)
    
    with col1:
        cities = attraction_service.get_cities()
        selected_cities = st.multiselect("Cities", cities)
        
        categories = attraction_service.get_categories()
        selected_category = st.selectbox("Category", ["All"] + categories)
        
        min_rating = st.slider("Minimum Rating", 0.0, 10.0, 8.0, 0.5)
    
    with col2:
        duration_range = st.slider("Visit Duration (hours)", 0.0, 10.0, (0.0, 10.0), 0.5)
        
        free_only = st.checkbox("Free attractions only")
        
        booking_filter = st.radio("Booking", ["All", "Required", "Not Required"])
    
    # Apply filters button
    if st.button("🔍 Apply Filters", type="primary"):
        criteria = {
            'min_rating': min_rating,
            'duration_range': duration_range,
            'free_only': free_only
        }
        
        if selected_cities:
            criteria['cities'] = selected_cities
        
        if selected_category != "All":
            criteria['category'] = selected_category
        
        if booking_filter == "Required":
            criteria['booking_required'] = True
        elif booking_filter == "Not Required":
            criteria['booking_required'] = False
        
        results = filter_service.filter(criteria)
        
        st.write(f"Found **{len(results)}** attractions")
        
        if len(results) == 0:
            st.info("No attractions match your criteria. Try adjusting the filters.")
        else:
            for _, row in results.iterrows():
                display_attraction_card(row)


def show_routes_page(route_service, attraction_service):
    """En-route planner page"""
    st.header("🛣️ En-Route Attractions")
    
    cities = attraction_service.get_cities()
    
    col1, col2 = st.columns(2)
    with col1:
        from_city = st.selectbox("From", [""] + cities, key="from")
    with col2:
        to_city = st.selectbox("To", [""] + cities, key="to")
    
    if from_city and to_city:
        if from_city == to_city:
            st.warning("Please select different cities")
        else:
            routes = route_service.get_recommendations(from_city, to_city)
            
            if len(routes) == 0:
                st.info(f"No en-route attractions found between {from_city} and {to_city}")
            else:
                st.success(f"Found **{len(routes)}** en-route attractions")
                
                for route in routes:
                    attraction = route['attraction_details']
                    
                    st.markdown(f"### {attraction['name']}")
                    
                    col1, col2, col3 = st.columns([2, 1, 1])
                    with col1:
                        st.write(f"📍 **{route['location']}**")
                    with col2:
                        st.write(f"⭐ **{attraction['rating']}**/10")
                    with col3:
                        st.write(f"🛣️ Detour: **{route['detour_km']} km**")
                    
                    st.write(attraction['description'])
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.write(f"⏱️ Stop time: {route['recommended_stop_hours']}h")
                    with col2:
                        st.write(f"💰 {attraction['entrance_fee']}")
                    with col3:
                        booking_emoji = "✅" if attraction['advance_booking'] else "❌"
                        st.write(f"{booking_emoji} Booking: {'Required' if attraction['advance_booking'] else 'Not needed'}")
                    
                    st.markdown("---")
    else:
        st.info("Please select both cities to find en-route attractions")


if __name__ == "__main__":
    main()