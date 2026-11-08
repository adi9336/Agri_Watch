"""
Agri_watch - One-time District Centroid Geocoder
Builds data/district_coords.json (district|state -> lat/lon) from every district
in the market directory and price snapshot, using OpenStreetMap Nominatim.
Resumable: districts already in the output file are skipped.

Usage:
    python scripts/build_district_coords.py
"""

import os
import sys
import csv
import json
import time
import urllib.parse
import urllib.request

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(CURRENT_DIR)
DATA_DIR = os.path.join(PARENT_DIR, "data")
OUT_PATH = os.path.join(DATA_DIR, "district_coords.json")
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "AgriWatch/1.0 (https://github.com/adi9336/Agri_Watch)"


def district_key(district: str, state: str) -> str:
    return f"{district.strip().lower()}|{state.strip().lower()}"


def collect_districts() -> set:
    pairs = set()
    with open(os.path.join(DATA_DIR, "market_directory.json"), encoding="utf-8") as f:
        for v in json.load(f).values():
            pairs.add((v["district"].strip(), v["state"].strip()))
    snapshot = os.path.join(DATA_DIR, "mandi_prices_snapshot.csv")
    if os.path.exists(snapshot):
        with open(snapshot, encoding="utf-8", errors="ignore") as f:
            for r in csv.DictReader(f):
                pairs.add((r["district"].strip(), r["state"].strip()))
    return {p for p in pairs if p[0] and p[1]}


def geocode(query: str):
    url = f"{NOMINATIM_URL}?{urllib.parse.urlencode({'q': query, 'format': 'json', 'limit': 1, 'countrycodes': 'in'})}"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=20) as resp:
        results = json.loads(resp.read().decode("utf-8"))
    if results:
        return round(float(results[0]["lat"]), 4), round(float(results[0]["lon"]), 4)
    return None


def main():
    coords = {}
    if os.path.exists(OUT_PATH):
        with open(OUT_PATH, encoding="utf-8") as f:
            coords = json.load(f)

    pending = sorted(p for p in collect_districts() if district_key(*p) not in coords)
    print(f"[*] {len(coords)} cached, {len(pending)} districts to geocode")

    for i, (district, state) in enumerate(pending, 1):
        point = None
        for query in (f"{district} district, {state}, India", f"{district}, {state}, India"):
            try:
                point = geocode(query)
            except Exception as e:
                print(f"[!] {query}: {e}")
            time.sleep(1.1)  # Nominatim usage policy: max 1 request/second
            if point:
                break
        if point:
            coords[district_key(district, state)] = {"lat": point[0], "lon": point[1]}
        print(f"[{i}/{len(pending)}] {district}, {state} -> {point}", flush=True)
        if i % 25 == 0:
            with open(OUT_PATH, "w", encoding="utf-8") as f:
                json.dump(coords, f, ensure_ascii=False, indent=0, sort_keys=True)

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(coords, f, ensure_ascii=False, indent=0, sort_keys=True)
    print(f"[+] Saved {len(coords)} district centroids to {OUT_PATH}")


if __name__ == "__main__":
    main()
