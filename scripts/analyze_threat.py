import requests
import json
import sys
import argparse
from typing import List

# Configuration
API_URL = "http://localhost:8080/api/analyze"

SCENARIOS = {
    "gaza": ["שדרות", "נתיב העשרה", "אשקלון"],
    "lebanon": ["קריית שמונה", "מטולה", "צפת"],
    "iran": ["נתניה", "תל אביב - מרכז", "ירושלים"],
    "yemen": ["אילת", "אילות"]
}

def analyze(cities: List[str]):
    print(f"[*] INITIALIZING TACTICAL ANALYSIS FOR {len(cities)} TARGETS...")
    
    payload = {"cities": cities}
    try:
        response = requests.post(API_URL, json=payload)
        if response.status_code != 200:
            print(f"[!] ERROR: Backend returned {response.status_code}")
            print(response.json())
            return

        data = response.json()
        
        print("\n" + "="*60)
        print(f"  IRON SIGHT TACTICAL REPORT: {data.get('title')}")
        print("="*60)
        
        # Origin Analysis
        trajectories = data.get("trajectories", [])
        for traj in trajectories:
            origin = traj.get("origin")
            print(f"[+] DETECTED ORIGIN: {origin}")
            print(f"    Launch Vector: {traj.get('origin_coords')} -> {traj.get('target_coords')}")

        # Cluster Breakdown
        clusters = data.get("clusters", [])
        print(f"\n[+] CLUSTER DENSITY: {len(clusters)} distinct salvo zones")
        for i, cl in enumerate(clusters):
            city_list = ", ".join([c['name'] for c in cl['cities']])
            print(f"    Zone {i+1} [{cl['origin']}]: {city_list}")

        # Strategic Metadata
        print(f"\n[+] STRATEGIC FOCUS: {data.get('center')}")
        print(f"    Zoom Calibration: {data.get('zoom_level')}")
        print("="*60 + "\n")

    except requests.exceptions.ConnectionError:
        print("[!] ERROR: Could not connect to backend. Is it running on port 8080?")
    except Exception as e:
        print(f"[!] UNEXPECTED ERROR: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Iron Sight Tactical Analysis CLI")
    parser.add_argument("cities", nargs="*", help="List of city names to analyze")
    parser.add_argument("--scenario", choices=SCENARIOS.keys(), help="Run a pre-defined tactical scenario")
    
    args = parser.parse_args()
    
    target_cities = []
    if args.scenario:
        target_cities = SCENARIOS[args.scenario]
    elif args.cities:
        # Check if first arg is a comma-separated list
        if len(args.cities) == 1 and "," in args.cities[0]:
            target_cities = [c.strip() for c in args.cities[0].split(",")]
        else:
            target_cities = args.cities
    else:
        print("[!] No cities provided. Use --scenario or pass city names.")
        sys.exit(1)
        
    analyze(target_cities)
