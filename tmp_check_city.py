import json
import re
import os

def standardize_name(name):
    if not name: return ""
    name = re.sub(r'[\-\,\(\)\s]+', '', name)
    return name.strip()

data_path = r'c:\Users\amirl\OneDrive\Documents\GitHub\iron-sight\backend\lamas_data.json'
with open(data_path, 'r', encoding='utf-8-sig') as f:
    data = json.load(f)

city_map = {}
areas = data.get('areas', {})
for area, cities in areas.items():
    for city, details in cities.items():
        std = standardize_name(city)
        city_map[std] = city

target = "משגב עם"
std_target = standardize_name(target)
print(f"Target: {target} -> Standardized: {std_target}")
if std_target in city_map:
    print(f"Found: {city_map[std_target]}")
else:
    print("Not found in city_map")
    # Search for similar names
    matches = [c for c in city_map.values() if "משגב" in c]
    print(f"Partial matches for 'משגב': {matches}")
