import json
import math
import re
import unicodedata
from itertools import combinations
from collections import defaultdict

# ==== CONFIGURABLE THRESHOLDS ====
MAX_DISTANCE_KM = 5.0      # how close two POIs must be
MIN_JACCARD     = 0.60     # token overlap threshold
MIN_SEQ_RATIO   = 0.90     # SequenceMatcher similarity threshold
MIN_SUBSTR_LEN  = 10       # minimum length for substring match


# ==== TEXT / NAME NORMALIZATION ====

STOPWORDS = {
    "natural", "park", "parque", "national",
    "de", "del", "la", "el", "los", "las",
    "the", "of", "y", "and",
    # generic attraction words (you can tweak)
    "jardines", "jardin", "plaza", "museo", "museum",
    "iglesia", "catedral", "cathedral", "real",
    "palacio", "alcázar", "alcazar", "castillo", "castle"
}


def strip_accents(text: str) -> str:
    """Remove accents/diacritics."""
    return "".join(
        c for c in unicodedata.normalize("NFD", text)
        if unicodedata.category(c) != "Mn"
    )


def norm_city(city: str) -> str:
    if not city:
        return ""
    return strip_accents(city.lower().strip())


def base_tokens(text: str):
    """Lowercase, strip accents & punctuation, split, drop stopwords."""
    text = strip_accents(text.lower())
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    tokens = [t for t in text.split() if t and t not in STOPWORDS]
    return tokens


def name_tokens(item: dict):
    """Tokens for the name, with the *city name* also removed (to avoid false matches)."""
    tokens = base_tokens(item.get("name", ""))
    city_norm = norm_city(item.get("city", ""))
    return [t for t in tokens if t != city_norm]


def jaccard(a, b) -> float:
    sa, sb = set(a), set(b)
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


# ==== GEO UTILS ====

def haversine(lat1, lon1, lat2, lon2) -> float:
    """Distance in km between two lat/lon points."""
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)

    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dl / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


# ==== DUPLICATE LOGIC ====

def is_potential_duplicate(a: dict, b: dict) -> bool:
    """Heuristic: same city, close coordinates, and very similar names."""
    # 1) same city
    if norm_city(a.get("city")) != norm_city(b.get("city")):
        return False

    # 2) coordinates must exist and be close
    lat1, lon1 = a.get("lat"), a.get("lon")
    lat2, lon2 = b.get("lat"), b.get("lon")
    if None in (lat1, lon1, lat2, lon2):
        return False

    dist = haversine(lat1, lon1, lat2, lon2)
    if dist > MAX_DISTANCE_KM:
        return False

    # 3) name similarity
    tokens1 = name_tokens(a)
    tokens2 = name_tokens(b)
    shared_tokens = set(tokens1) & set(tokens2)
    jac = jaccard(tokens1, tokens2)

    base1 = strip_accents(a.get("name", "").lower())
    base2 = strip_accents(b.get("name", "").lower())

    # SequenceMatcher (lazy import to avoid overhead if you want)
    import difflib
    seq_ratio = difflib.SequenceMatcher(a=base1, b=base2).ratio()

    # substring case (e.g. "The Statue of John Lennon" vs "The Statue of John Lenon")
    substr = (
        (len(base1) >= MIN_SUBSTR_LEN and base1 in base2) or
        (len(base2) >= MIN_SUBSTR_LEN and base2 in base1)
    )

    # At least one shared "meaningful" token and strong similarity
    if (jac >= MIN_JACCARD or seq_ratio >= MIN_SEQ_RATIO or substr) and shared_tokens:
        return True

    return False


def find_duplicate_groups(records):
    """Return list of groups; each group is a list of record indices that might be duplicates."""
    n = len(records)
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x, y):
        rx, ry = find(x), find(y)
        if rx != ry:
            parent[ry] = rx

    # Build union-find from all candidate pairs
    for i, j in combinations(range(n), 2):
        if is_potential_duplicate(records[i], records[j]):
            union(i, j)

    clusters = defaultdict(list)
    for idx in range(n):
        root = find(idx)
        clusters[root].append(idx)

    # Only keep "true" groups of size > 1
    groups = [sorted(idx_list) for idx_list in clusters.values() if len(idx_list) > 1]
    return sorted(groups, key=lambda g: (records[g[0]].get("city", ""), len(g)), reverse=False)


def print_duplicate_report(records, groups):
    print(f"Found {len(groups)} potential duplicate groups.")
    for gi, group in enumerate(groups):
        print("\n" + "=" * 60)
        print(f"Group {gi}  (size {len(group)})")
        city = records[group[0]].get("city", "")
        print(f"City: {city}")
        print("-" * 60)
        for idx in group:
            r = records[idx]
            print(f"Index {idx:3d} | {r.get('name')}  | rating={r.get('rating')} | source={r.get('source')}")
        print("-" * 60)
        print("# Decide: merge? keep separate? fix name/typo?  <-- YOUR DECISION")


# ==== OPTIONAL: MERGE LOGIC (SIMPLE SKELETON) ====

def choose_preferred_record(records, indices):
    """
    Very naive: pick the record with the most non-empty fields and/or with wikidata/wikipedia.
    You can customize this.
    """
    def score(idx):
        r = records[idx]
        score = 0
        # reward having wikidata / wikipedia
        if r.get("wikidata"): score += 3
        if r.get("wikipedia"): score += 2
        # reward non-empty fields
        for k, v in r.items():
            if v not in (None, "", [], {}):
                score += 0.2
        return score

    return max(indices, key=score)


def merge_group(records, indices):
    """
    Example of auto-merge into a *single* record.
    You may or may not want to use this – review before trusting.
    """
    base_idx = choose_preferred_record(records, indices)
    base = dict(records[base_idx])  # shallow copy

    # Merge tags
    all_tags = set(base.get("tags") or [])
    for idx in indices:
        if idx == base_idx:
            continue
        r = records[idx]
        for t in r.get("tags") or []:
            all_tags.add(t)
    if all_tags:
        base["tags"] = sorted(all_tags)

    # Take max rating, max reviews_count if present
    ratings = [r.get("rating") for r in (records[i] for i in indices) if r.get("rating") is not None]
    if ratings:
        base["rating"] = max(ratings)

    # Combine sources into list
    sources = []
    for idx in indices:
        s = records[idx].get("source")
        if isinstance(s, list):
            sources.extend(s)
        elif isinstance(s, str):
            sources.append(s)
    if sources:
        base["source"] = sorted(set(sources))

    # You can add more merge rules (website, entrance_fee, etc.) here.

    return base


def merge_all_duplicates(records, groups):
    """
    Returns a *new* list of records where each group is collapsed into a single merged record.
    Non-duplicate records are copied as-is.
    """
    to_merge = set(i for g in groups for i in g)
    new_records = []
    used = set()

    for g in groups:
        # Only merge each group once
        if any(idx in used for idx in g):
            continue
        merged = merge_group(records, g)
        new_records.append(merged)
        used.update(g)

    # Add all records that were not in any duplicate group
    for i, r in enumerate(records):
        if i not in to_merge:
            new_records.append(r)

    return new_records


# ==== MAIN (example usage) ====

if __name__ == "__main__":
    INPUT_FILE = "andalusia_attractions_filtered.json"
    OUTPUT_FILE = "andalusia_attractions_deduped.json"

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        attractions = json.load(f)

    groups = find_duplicate_groups(attractions)
    print_duplicate_report(attractions, groups)

    # If (and only if) you are happy with auto-merging logic:
    # merged = merge_all_duplicates(attractions, groups)
    # print(f"\nOriginal count: {len(attractions)}, after merge: {len(merged)}")
    # with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    #     json.dump(merged, f, ensure_ascii=False, indent=2)
    # print(f"Saved merged file to {OUTPUT_FILE}")
