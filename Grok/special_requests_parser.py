# special_requests_parser.py
import re

def parse_special_requests(text):
    text = text.strip().lower()
    result = {"must_see_cities": [], "avoid_cities": [], "stay_durations": {}}
    if not text: return result

    must_see = re.findall(r"must see ([^\,]+)", text)
    result["must_see_cities"] = [c.strip().title() for c in must_see]

    avoid = re.findall(r"avoid ([^\,]+)", text)
    result["avoid_cities"] = [c.strip().title() for c in avoid]

    stays = re.findall(r"spend (\d+) days? in ([^\,]+)", text)
    for days, city in stays:
        result["stay_durations"][city.strip().title()] = int(days)

    return result

def validate_requests(parsed):
    if not isinstance(parsed, dict): return False
    if "stay_durations" in parsed:
        for k, v in parsed["stay_durations"].items():
            if not isinstance(v, int) or v < 1: return False
    return True