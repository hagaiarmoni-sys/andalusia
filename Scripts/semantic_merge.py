"""
Semantic merge layer for itinerary export.

Goal: Collapse *logical* duplicates (bilingual names, sub-POIs in same complex)
that should appear once in the DOC/PDF, without destroying the underlying
rich dataset.

Usage:
    from semantic_merge import merge_city_pois, merge_all

    cleaned = merge_all(pois)  # list[dict] of POIs across cities
    # or per-city inside your generator
    pois_city = [p for p in pois if p.get("city") == city]
    pois_city = merge_city_pois(pois_city, city)

No third‑party deps. Works with your current schema:
    {
      "name": str,
      "city": str,
      "category": str,
      "coordinates": {"lat": float, "lon": float},
      "description": str, ...
    }
"""
from __future__ import annotations
import unicodedata, re, math
from typing import Dict, Iterable, List, Tuple

# --------------------------- Normalization helpers ---------------------------

def strip_accents(s: str) -> str:
    s = unicodedata.normalize("NFD", s or "")
    return "".join(ch for ch in s if unicodedata.category(ch) != "Mn")

def norm_key(s: str) -> str:
    s = strip_accents(s).lower()
    s = re.sub(r"[\W_]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()

def name_tokens(s: str) -> set:
    return set(norm_key(s).split())

# ------------------------------- Geo helpers --------------------------------

def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    from math import radians, sin, cos, atan2, sqrt
    phi1, phi2 = radians(lat1), radians(lat2)
    dphi = radians(lat2 - lat1)
    dlmb = radians(lon2 - lon1)
    a = sin(dphi/2)**2 + cos(phi1)*cos(phi2)*sin(dlmb/2)**2
    c = 2*atan2(sqrt(a), sqrt(1-a))
    return R * c

def meters_between(a: dict, b: dict) -> float | None:
    ca, cb = a.get("coordinates") or {}, b.get("coordinates") or {}
    if ca.get("lat") is None or ca.get("lon") is None: return None
    if cb.get("lat") is None or cb.get("lon") is None: return None
    return haversine_km(ca["lat"], ca["lon"], cb["lat"], cb["lon"]) * 1000.0

# -------------------------- Semantic grouping config -------------------------
# Terms inside the same list represent one logical complex.
# Matching is done on normalized names (accents removed, lowercased).

SEMANTIC_GROUPS: Dict[str, List[List[str]]] = {
    # Córdoba
    "cordoba": [
        ["mosque cathedral", "mezquita", "mezquita catedral", "mezquita cathedral"],
        ["puente romano", "roman bridge"],
    ],
    # Seville
    "seville": [
        ["seville cathedral", "catedral de sevilla", "la giralda", "giralda"],
        ["real alcazar", "alcazar of seville", "alcazar"],
        ["plaza de espana", "plaza de españa"],
        ["metropol parasol", "las setas"],
        ["torre del oro", "golden tower"],
    ],
    # Granada
    "granada": [
        ["alhambra", "palacios nazaries", "palacios nazaríes", "generalife"],
        ["mirador de san nicolas", "san nicolas viewpoint"],
        ["granada cathedral", "catedral de granada"],
    ],
    # Ronda
    "ronda": [
        ["puente nuevo", "new bridge of ronda"],
    ],
    # Cádiz
    "cadiz": [
        ["cadiz cathedral", "catedral de cadiz"],
        ["torre tavira"],
    ],
    # Jerez, Carmona can be extended as needed
}

# Optional fallbacks for city aliases
CITY_ALIASES = {
    "sevilla": "seville",
    "cordoba": "cordoba",  # already ASCII form
    "cádiz": "cadiz",
}

# ------------------------------ Merge predicate ------------------------------

def _is_alias_match(name: str, alias_terms: List[str]) -> bool:
    nk = norm_key(name)
    for term in alias_terms:
        if term in nk:
            return True
    return False

# Conservative similarity: token overlap (Jaccard) to catch small variants.

def token_jaccard(a: str, b: str) -> float:
    ta, tb = name_tokens(a), name_tokens(b)
    if not ta or not tb:
        return 0.0
    inter = len(ta & tb)
    if inter == 0:
        return 0.0
    return inter / len(ta | tb)

# ------------------------------ Merge utilities ------------------------------

def _score_richness(p: dict) -> int:
    score = 0
    for k, v in p.items():
        if v in (None, "", []):
            continue
        if k in ("description", "opening_hours", "website", "wikidata", "wikipedia", "rating"):
            score += 3
        elif k in ("tags", "category", "coordinates"):
            score += 2
        else:
            score += 1
    return score

def _merge_pair(a: dict, b: dict) -> dict:
    base, other = (a, b) if _score_richness(a) >= _score_richness(b) else (b, a)
    merged = dict(base)
    # Merge tags
    ta = set(a.get("tags") or [])
    tb = set(b.get("tags") or [])
    if ta or tb:
        merged["tags"] = sorted(ta | tb)
    # Fill missing scalars
    for k, v in other.items():
        if k not in merged or merged[k] in (None, "", []):
            merged[k] = v
    return merged

# ------------------------------ Public API ----------------------------------

def merge_city_pois(pois: List[dict], city: str,
                    distance_merge_m: int = 120,
                    token_sim_threshold: float = 0.85,
                    apply_semantic_groups: bool = True) -> List[dict]:
    """
    Returns a list where logical duplicates within a city are collapsed.

    Strategy (ordered):
      1) Apply city-specific SEMANTIC_GROUPS (alias lists) if enabled.
      2) Within each alias group, merge all matches into one richest record.
      3) For remaining items, merge rows that are within `distance_merge_m` OR
         have high token Jaccard similarity (>= token_sim_threshold).
    """
    if not pois:
        return []

    city_key = CITY_ALIASES.get(norm_key(city), norm_key(city))
    alias_groups = SEMANTIC_GROUPS.get(city_key, []) if apply_semantic_groups else []

    used = set()
    result: List[dict] = []

    # 1) Semantic alias collapsing
    for alias in alias_groups:
        matches_idx = [i for i, p in enumerate(pois) if _is_alias_match(p.get("name", ""), alias)]
        if not matches_idx:
            continue
        # Merge all matched entries
        merged = None
        for idx in matches_idx:
            used.add(idx)
            merged = _merge_pair(merged, pois[idx]) if merged is not None else pois[idx]
        result.append(merged)

    # 2) Geospatial / token-sim collapsing for the rest
    def can_merge(p: dict, q: dict) -> bool:
        # Distance rule
        m = meters_between(p, q)
        if m is not None and m <= distance_merge_m:
            return True
        # Token-level similarity rule (e.g., bilingual variants)
        if token_jaccard(p.get("name", ""), q.get("name", "")) >= token_sim_threshold:
            return True
        return False

    remaining = [p for i, p in enumerate(pois) if i not in used]

    clusters: List[dict] = []
    for rec in remaining:
        merged_into_existing = False
        for j in range(len(clusters)):
            if can_merge(rec, clusters[j]):
                clusters[j] = _merge_pair(clusters[j], rec)
                merged_into_existing = True
                break
        if not merged_into_existing:
            clusters.append(rec)

    result.extend(clusters)
    return result


def merge_all(pois: List[dict], **kwargs) -> List[dict]:
    """Apply merge_city_pois for each city and return a single list."""
    # group by city label
    by_city: Dict[str, List[dict]] = {}
    for p in pois:
        city = (p.get("city") or "").strip()
        by_city.setdefault(city, []).append(p)

    merged_all: List[dict] = []
    for city, plist in by_city.items():
        merged_all.extend(merge_city_pois(plist, city, **kwargs))
    return merged_all

# ------------------------------- Quick test ----------------------------------
if __name__ == "__main__":
    sample = [
        {"name": "Seville Cathedral", "city": "Seville", "coordinates": {"lat": 37.386, "lon": -5.992}},
        {"name": "La Giralda", "city": "Seville", "coordinates": {"lat": 37.3863, "lon": -5.9922}},
        {"name": "Catedral de Sevilla", "city": "Seville", "coordinates": {"lat": 37.3861, "lon": -5.9919}},
        {"name": "Plaza de España", "city": "Seville", "coordinates": {"lat": 37.377, "lon": -5.987}},
        {"name": "Plaza de Espana", "city": "Seville", "coordinates": {"lat": 37.3771, "lon": -5.9871}},
        {"name": "Mosque–Cathedral of Córdoba", "city": "Córdoba", "coordinates": {"lat": 37.8792, "lon": -4.7794}},
        {"name": "Mezquita de los Andaluces", "city": "Córdoba", "coordinates": {"lat": 37.88023, "lon": -4.7805642}},
        {"name": "Puente Romano", "city": "Córdoba", "coordinates": {"lat": 37.878, "lon": -4.778}},
        {"name": "Roman Bridge of Córdoba", "city": "Córdoba", "coordinates": {"lat": 37.8781, "lon": -4.7781}},
    ]
    merged = merge_all(sample)
    print(f"Input: {len(sample)} → Output: {len(merged)}")
    for p in merged:
        print(" -", p["city"], "::", p["name"])
