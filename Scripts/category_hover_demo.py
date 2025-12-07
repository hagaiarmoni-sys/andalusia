# cmd   Command Prompt
# cd "C:\Users\hagai\PycharmProjects\pythonProject4\andalusia-app\static\videos"
# py -m http.server 8001

import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="Category Hover Demo", page_icon="🎬", layout="wide")

st.title("🎬 Trip Categories – Hover & Choose Demo")
st.write("Hover each thumbnail to see a short video, then flip the switch under the ones you like.")

# ---------- DEFINE CATEGORIES ----------
categories = [
    {"key": "museums", "label": "Museums & History",
     "image": "https://via.placeholder.com/160x90.png?text=Museums",
     "video": "http://localhost:8001/museum.mp4"},
    {"key": "architecture", "label": "Architecture & Monuments",
     "image": "https://via.placeholder.com/160x90.png?text=Arch",
     "video": "http://localhost:8001/architecture.mp4"},
    {"key": "old_towns", "label": "Old Towns & Streets",
     "image": "https://via.placeholder.com/160x90.png?text=Old+Town",
     "video": "http://localhost:8001/old_towns.mp4"},
    {"key": "nature", "label": "Nature & Mountains",
     "image": "https://via.placeholder.com/160x90.png?text=Nature",
     "video": "http://localhost:8001/tapas.mp4"},
    {"key": "beaches", "label": "Beaches & Coast",
     "image": "https://via.placeholder.com/160x90.png?text=Beaches",
     "video": "http://localhost:8001/beach.mp4"},
    {"key": "flamenco", "label": "Flamenco & Shows",
     "image": "https://via.placeholder.com/160x90.png?text=Shows",
     "video": "https://www.w3schools.com/html/mov_bbb.mp4"},
    {"key": "modern_art", "label": "Modern Art & Design",
     "image": "https://via.placeholder.com/160x90.png?text=Art",
     "video": "https://www.w3schools.com/html/mov_bbb.mp4"},
    {"key": "parks", "label": "Parks & Gardens",
     "image": "https://via.placeholder.com/160x90.png?text=Parks",
     "video": "https://www.w3schools.com/html/mov_bbb.mp4"},
    {"key": "religious", "label": "Religious Sites",
     "image": "https://via.placeholder.com/160x90.png?text=Religious",
     "video": "https://www.w3schools.com/html/mov_bbb.mp4"},
    {"key": "kids", "label": "Family & Kids",
     "image": "https://via.placeholder.com/160x90.png?text=Kids",
     "video": "https://www.w3schools.com/html/mov_bbb.mp4"},
    {"key": "adventure", "label": "Adventure & Hiking",
     "image": "https://via.placeholder.com/160x90.png?text=Adventure",
     "video": "https://www.w3schools.com/html/mov_bbb.mp4"},
    {"key": "nightlife", "label": "Nightlife & Bars",
     "image": "https://via.placeholder.com/160x90.png?text=Nightlife",
     "video": "https://www.w3schools.com/html/mov_bbb.mp4"},
]

st.markdown("### Hover over a category and choose")

CARDS_PER_ROW = 4
num_rows = (len(categories) + CARDS_PER_ROW - 1) // CARDS_PER_ROW

for row in range(num_rows):
    cols = st.columns(CARDS_PER_ROW)
    for col_idx in range(CARDS_PER_ROW):
        idx = row * CARDS_PER_ROW + col_idx
        if idx >= len(categories):
            break
        cat = categories[idx]
        with cols[col_idx]:
            # ---- VIDEO CARD (no label inside) ----
            card_html = f"""
            <!DOCTYPE html>
            <html>
            <head>
            <style>
            body {{
                margin: 0;
                padding: 0;
                text-align: center;
            }}
            .video-thumb {{
                width: 180px;
                height: 110px;
                border-radius: 12px;
                object-fit: cover;
                box-shadow: 0 0 4px rgba(0,0,0,0.25);
                cursor: pointer;
                transition: transform 0.2s ease, box-shadow 0.2s ease;
                transform-origin: center center;
            }}
            .video-thumb:hover {{
                transform: scale(1.7);
                box-shadow: 0 0 12px rgba(0,0,0,0.5);
            }}
            </style>
            </head>
            <body>
                <video class="video-thumb"
                       src="{cat['video']}"
                       poster="{cat['image']}"
                       muted
                       preload="none"
                       onmouseover="this.play();"
                       onmouseout="this.pause(); this.currentTime = 0;">
                </video>
            </body>
            </html>
            """
            # Small height so there is almost no extra space below the video
            components.html(card_html, height=125, scrolling=False)

            # ---- CENTERED TOGGLE DIRECTLY UNDER VIDEO ----
            left, center, right = st.columns([1, 3, 1])
            with center:
                st.toggle(cat["label"], key=f"like_{cat['key']}")

# Collect choices for your planner
liked_categories = [
    cat["key"]
    for cat in categories
    if st.session_state.get(f"like_{cat['key']}", False)
]

st.markdown("### Selected categories (debug)")
st.write(liked_categories)
