"""
Monetization Manager
Centralizes affiliate link generation for Hotels, Tours, and Car Rentals.
"""
from urllib.parse import quote_plus

# 💰 CONFIGURATION: Replace with your actual Affiliate IDs
BOOKING_AID = "YOUR_BOOKING_AID" 
VIATOR_UID = "YOUR_VIATOR_UID"
RENTALCARS_ID = "YOUR_RENTALCARS_ID"

def get_hotel_affiliate_link(hotel_name, city, checkin=None, checkout=None):
    """Generate Booking.com affiliate link with dates."""
    base = "https://www.booking.com/searchresults.html"
    query = quote_plus(f"{hotel_name} {city}")
    params = f"?ss={query}&aid={BOOKING_AID}"
    
    if checkin and checkout:
        try:
            # Handle both datetime objects and strings
            c_in = checkin.strftime('%Y-%m-%d') if hasattr(checkin, 'strftime') else str(checkin)
            c_out = checkout.strftime('%Y-%m-%d') if hasattr(checkout, 'strftime') else str(checkout)
            params += f"&checkin={c_in}&checkout={c_out}"
        except:
            pass # Fallback to no dates if error
            
    return base + params

def get_tour_affiliate_link(city):
    """Generate Viator search link."""
    base = "https://www.viator.com/searchResults/all"
    query = quote_plus(f"things to do in {city}")
    return f"{base}?text={query}&pid={VIATOR_UID}"