import json

# Read your existing file
with open('data/andalusia_attractions_full.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Handle both possible structures
if isinstance(data, list):
    # If it's just a list of attractions
    attractions = data
    full_data = {'metadata': {'version': '3.0', 'total_attractions': len(data)}, 'attractions': data}
elif 'attractions' in data:
    # If it already has the right structure
    attractions = data['attractions']
    full_data = data
else:
    print("❌ Unexpected JSON structure!")
    exit()

# Add IDs to each attraction
for attraction in attractions:
    if 'id' not in attraction:
        # Generate ID from name
        name = attraction['name']
        attraction_id = name.lower()
        # Remove accents
        replacements = {'á': 'a', 'é': 'e', 'í': 'i', 'ó': 'o', 'ú': 'u', 'ñ': 'n', 'ü': 'u'}
        for old, new in replacements.items():
            attraction_id = attraction_id.replace(old, new)
        # Replace non-alphanumeric with underscore
        attraction_id = ''.join(c if c.isalnum() or c == ' ' else '_' for c in attraction_id)
        # Replace spaces with underscore and clean up
        attraction_id = '_'.join(attraction_id.split())
        attraction_id = attraction_id.strip('_')
        
        attraction['id'] = attraction_id

# Update metadata
if 'metadata' in full_data:
    full_data['metadata']['total_attractions'] = len(attractions)

# Save with new name
with open('data/andalusia_attractions_clean.json', 'w', encoding='utf-8') as f:
    json.dump(full_data, f, indent=2, ensure_ascii=False)

print(f"✅ Done! Created andalusia_attractions_clean.json with {len(attractions)} attractions")
print("Each attraction now has an 'id' field")