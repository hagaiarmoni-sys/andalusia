import re

# Read the file as text
with open("andalusia_attractions_full.json", "r", encoding="utf-8") as f:
    content = f.read()

# Replace all NaN with null
content = re.sub(r'\bNaN\b', 'null', content)

# Save back
with open("andalusia_pois_complete.json", "w", encoding="utf-8") as f:
    f.write(content)

print("✅ Fixed NaN values in JSON file")