import json

# Load restaurant data
with open('restaurants_andalusia.json', 'r', encoding='utf-8') as f:
    restaurants = json.load(f)

print(f"Total restaurants: {len(restaurants)}")
print("\n" + "="*80)
print("CHECKING 'topic' FIELD FOR NUMBERS:")
print("="*80)

with_numbers = []
without_numbers = []

for r in restaurants:
    topic = r.get('topic', '')
    if topic:
        # Check if topic starts with a number
        parts = topic.split()
        if parts and parts[0].isdigit():
            with_numbers.append({
                'name': r.get('name'),
                'topic': topic,
                'reviews': int(parts[0]),
                'rating': r.get('rating')
            })
        else:
            without_numbers.append({
                'name': r.get('name'),
                'topic': topic,
                'rating': r.get('rating')
            })

print(f"\n✅ Restaurants WITH review count in topic: {len(with_numbers)}")
print(f"❌ Restaurants WITHOUT review count in topic: {len(without_numbers)}")

if with_numbers:
    print("\n" + "="*80)
    print("EXAMPLES WITH REVIEW COUNTS:")
    print("="*80)
    for r in with_numbers[:10]:
        print(f"{r['name']}: {r['reviews']} reviews (topic: '{r['topic']}')")

if without_numbers:
    print("\n" + "="*80)
    print("EXAMPLES WITHOUT REVIEW COUNTS:")
    print("="*80)
    for r in without_numbers[:10]:
        print(f"{r['name']}: (topic: '{r['topic']}')")

# Find the specific restaurants you mentioned
print("\n" + "="*80)
print("CHECKING SPECIFIC RESTAURANTS:")
print("="*80)

targets = ["Andino Gastrobar", "La Cordobesa", "Papas Elvira"]

for target in targets:
    found = [r for r in restaurants if target.lower() in r.get('name', '').lower()]
    if found:
        r = found[0]
        topic = r.get('topic', '')
        parts = topic.split() if topic else []
        has_number = parts and parts[0].isdigit()
        
        print(f"\n✅ {r.get('name')}:")
        print(f"   topic: '{topic}'")
        print(f"   Has review count? {'YES - ' + parts[0] + ' reviews' if has_number else 'NO'}")
        print(f"   rating: {r.get('rating')}")
