import json
import os

from PIL import Image, ImageDraw, ImageFont, ImageOps
import imageio.v2 as imageio


# === CONFIG ===

# JSON with POIs (run this script from project root: andalusia-app/)
JSON_PATH = os.path.join("data", "andalusia_attractions_filtered.json")

# Output video path
OUTPUT_VIDEO = os.path.join("data", "andalusia_attractions_slideshow.mp4")

# Basemap image for the mini-map (you created this already)
MAP_IMAGE_PATH = os.path.join("data", "maps", "andalusia_mini_map.png")

# Video parameters
FPS = 20
SECONDS_PER_POI = 4
VIDEO_WIDTH = 1280
VIDEO_HEIGHT = 720
FOOTER_HEIGHT = 140  # a bit taller for mini-map

# Limit number of POIs in the video (None = all)
MAX_POIS = 40  # change to None if you want all POIs with photos


# === HELPERS ===

def load_attractions(json_path):
    """
    Load attractions from JSON and resolve their local_photo_path
    relative to the data/photos directory. Also attach lat/lon.
    """
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    json_abs = os.path.abspath(json_path)
    data_dir = os.path.dirname(json_abs)  # .../andalusia-app/data
    photos_dir = os.path.join(data_dir, "photos")

    attractions = []

    for a in data:
        local_path = a.get("local_photo_path")
        if not local_path:
            continue

        # Normalize slashes
        local_path = local_path.replace("\\", os.sep).replace("/", os.sep)

        # If path is not absolute, make it relative to data/photos
        if not os.path.isabs(local_path):
            if local_path.lower().startswith("photos" + os.sep):
                resolved = os.path.join(data_dir, local_path)
            else:
                resolved = os.path.join(photos_dir, local_path)
        else:
            resolved = local_path

        # lat / lon from either top-level or coordinates{}
        lat = a.get("lat")
        lon = a.get("lon")
        coords = a.get("coordinates") or {}
        if lat is None:
            lat = coords.get("lat")
        if lon is None:
            lon = coords.get("lon")

        attractions.append({
            "name": a.get("name", "Unknown POI"),
            "city": a.get("city", "Unknown city"),
            "photo_path": resolved,
            "lat": lat,
            "lon": lon,
        })

    return attractions


def measure_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont):
    """
    Measure text size in a Pillow-version-safe way.
    Uses textbbox if available, falls back to font.getsize().
    """
    try:
        bbox = draw.textbbox((0, 0), text, font=font)
        width = bbox[2] - bbox[0]
        height = bbox[3] - bbox[1]
        return width, height
    except AttributeError:
        return font.getsize(text)


def prepare_map_bounds(attractions):
    """
    Compute min/max lat/lon for all attractions that have coordinates.
    This defines the bounding box for the mini-map.
    """
    points = [
        (a["lat"], a["lon"])
        for a in attractions
        if a["lat"] is not None and a["lon"] is not None
    ]
    if not points:
        return None

    lats = [p[0] for p in points]
    lons = [p[1] for p in points]
    return min(lats), max(lats), min(lons), max(lons)


def project_to_map(lat, lon, lat_min, lat_max, lon_min, lon_max,
                   map_x0, map_y0, map_width, map_height):
    """
    Simple lat/lon -> (x, y) projection into the mini-map rectangle.
    """
    if lat_min == lat_max:
        y = map_y0 + map_height / 2.0
    else:
        # invert lat so north is at top
        y_norm = (lat - lat_min) / (lat_max - lat_min)
        y = map_y0 + (1.0 - y_norm) * map_height

    if lon_min == lon_max:
        x = map_x0 + map_width / 2.0
    else:
        x_norm = (lon - lon_min) / (lon_max - lon_min)
        x = map_x0 + x_norm * map_width

    return x, y


def draw_mini_map(base_image, draw, basemap,
                  attractions, upto_index,
                  footer_y0, footer_y1,
                  lat_min, lat_max, lon_min, lon_max,
                  width):
    """
    Draw a mini-map in the footer on the right-hand side.
    Uses a static basemap image as background.
    upto_index = draw route up to this attraction index (inclusive).
    """
    map_margin = 16
    map_width = 260
    map_height = (footer_y1 - footer_y0) - 2 * map_margin
    map_x0 = width - map_width - map_margin
    map_y0 = footer_y0 + map_margin
    map_x1 = map_x0 + map_width
    map_y1 = map_y0 + map_height

    # 1) Paste resized basemap
    if basemap is not None:
        bm = basemap.resize((map_width, map_height), Image.LANCZOS)
        base_image.paste(bm, (map_x0, map_y0))
    else:
        # fallback plain background
        draw.rectangle([map_x0, map_y0, map_x1, map_y1], fill=(30, 30, 30))

    # 2) Route + points on top
    sequence = []
    for i in range(min(upto_index + 1, len(attractions))):
        lat = attractions[i]["lat"]
        lon = attractions[i]["lon"]
        if lat is None or lon is None:
            continue
        x, y = project_to_map(
            lat, lon,
            lat_min, lat_max, lon_min, lon_max,
            map_x0, map_y0, map_width, map_height
        )
        sequence.append((x, y))

    if not sequence:
        return

    # Route line
    if len(sequence) > 1:
        draw.line(sequence, fill=(120, 200, 255), width=3)

    # Dots for visited points, except current
    for (x, y) in sequence[:-1]:
        r = 4
        draw.ellipse([x - r, y - r, x + r, y + r], fill=(230, 230, 230))

    # Current POI (bigger orange)
    cur_x, cur_y = sequence[-1]
    r = 7
    draw.ellipse(
        [cur_x - r, cur_y - r, cur_x + r, cur_y + r],
        fill=(255, 140, 0)
    )


def create_slideshow_frames(
    attractions,
    fps,
    seconds_per_poi,
    width,
    height,
    footer_height
):
    frames = []

    # Fonts
    try:
        font_city = ImageFont.truetype("DejaVuSans-Bold.ttf", 34)
        font_poi = ImageFont.truetype("DejaVuSans.ttf", 28)
    except Exception:
        font_city = ImageFont.load_default()
        font_poi = ImageFont.load_default()

    # Bounds for mini-map
    bounds = prepare_map_bounds(attractions)
    if bounds is None:
        lat_min = lat_max = lon_min = lon_max = None
    else:
        lat_min, lat_max, lon_min, lon_max = bounds

    # Load basemap once (if available)
    basemap = None
    if os.path.exists(MAP_IMAGE_PATH):
        try:
            basemap = Image.open(MAP_IMAGE_PATH).convert("RGB")
        except Exception as e:
            print(f"[WARN] Could not open basemap image: {e}")
            basemap = None
    else:
        print(f"[WARN] Basemap image not found at {MAP_IMAGE_PATH}")

    for idx, attr in enumerate(attractions, start=0):
        city = attr["city"]
        name = attr["name"]
        img_path = attr["photo_path"]

        if not os.path.exists(img_path):
            print(f"[WARN] Skipping (missing file): {img_path}")
            continue

        try:
            base = Image.open(img_path).convert("RGB")
        except Exception as e:
            print(f"[WARN] Could not open {img_path}: {e}")
            continue

        # Fit/crop photo into 16:9
        base = ImageOps.fit(base, (width, height), method=Image.LANCZOS)
        draw = ImageDraw.Draw(base)

        # Footer bar
        footer_y0 = height - footer_height
        footer_y1 = height
        draw.rectangle([0, footer_y0, width, footer_y1], fill=(0, 0, 0))

        # Text: City (bold) + POI name on left side
        city_text = city
        poi_text = name

        city_w, city_h = measure_text(draw, city_text, font_city)
        city_x = 40
        city_y = footer_y0 + 16

        draw.text(
            (city_x, city_y),
            city_text,
            font=font_city,
            fill=(255, 255, 255)
        )

        poi_w, poi_h = measure_text(draw, poi_text, font_poi)
        poi_x = 40
        poi_y = city_y + city_h + 6

        # Truncate POI text if too long (leave space for mini-map)
        max_poi_width = width // 2 - 60
        if poi_w > max_poi_width:
            while poi_w > max_poi_width and len(poi_text) > 4:
                poi_text = poi_text[:-4] + "..."
                poi_w, poi_h = measure_text(draw, poi_text, font_poi)

        draw.text(
            (poi_x, poi_y),
            poi_text,
            font=font_poi,
            fill=(230, 230, 230)
        )

        # Mini-map on the right side, if we have bounds
        if lat_min is not None and lat_max is not None:
            draw_mini_map(
                base,
                draw,
                basemap,
                attractions,
                upto_index=idx,
                footer_y0=footer_y0,
                footer_y1=footer_y1,
                lat_min=lat_min,
                lat_max=lat_max,
                lon_min=lon_min,
                lon_max=lon_max,
                width=width
            )

        # Duplicate frame for duration
        frame_count = int(fps * seconds_per_poi)
        for _ in range(frame_count):
            frames.append(base.copy())

        print(f"Added slide {idx + 1}: {city} – {name}")

    return frames


# === MAIN ===

def main():
    if not os.path.exists(JSON_PATH):
        print(f"JSON not found: {JSON_PATH}")
        return

    attractions = load_attractions(JSON_PATH)

    if not attractions:
        print("No attractions with photo paths found, aborting.")
        return

    if MAX_POIS is not None:
        attractions = attractions[:MAX_POIS]

    print(f"Using {len(attractions)} attractions for the slideshow...")

    frames = create_slideshow_frames(
        attractions,
        fps=FPS,
        seconds_per_poi=SECONDS_PER_POI,
        width=VIDEO_WIDTH,
        height=VIDEO_HEIGHT,
        footer_height=FOOTER_HEIGHT,
    )

    if not frames:
        print("No frames generated, aborting.")
        return

    print(f"Writing video to {OUTPUT_VIDEO} ...")
    imageio.mimsave(OUTPUT_VIDEO, frames, fps=FPS)
    print("Done!")


if __name__ == "__main__":
    main()
