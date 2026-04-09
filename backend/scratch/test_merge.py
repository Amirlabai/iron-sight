import asyncio
import numpy as np
import json
import sys
import os

# Set PYTHONPATH
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mocking parts of the system for testing
class MockEngine:
    def __init__(self):
        self.origins = {"Lebanon": [33.8886, 35.8623]}
        self.strategic_depths = {"Lebanon": 0.5}
    
    def cluster(self, cities):
        # Cluster cities by some threshold; for test, just split by index to force 2 clusters
        return [
            {'centroid': cities[0]['coords'], 'cities': [cities[0]]},
            {'centroid': cities[1]['coords'], 'cities': [cities[1]]}
        ]
    
    async def get_origin(self, cities):
        # Simulate redundant origin name with whitespace
        return "Lebanon ", 0.5
    
    def get_convex_hull(self, coords):
        return coords # Mock hull
    
    def get_projected_origin(self, cities, org, depth=0.5):
        # User feedback: if recalculated projection falls in country, should point there
        # Mocking a slightly shifted entry point for the group
        coords = np.array([c['coords'] for c in cities])
        cnt = np.mean(coords, axis=0)
        return [cnt[0] + 0.5, cnt[1] + 0.5]

async def test_merging():
    from src.utils.cluster_utils import merge_event_group
    
    # User data scenario: 2 IDs consolidated, each from "Lebanon " (with space)
    event_data = {
        "ID1": {
            "data": {
                "category": "missiles",
                "all_cities": [{"name": "Metula", "coords": [33.28, 35.58]}],
                "trajectories": []
            }
        },
        "ID2": {
            "data": {
                "category": "missiles",
                "all_cities": [{"name": "Shlomi", "coords": [33.07, 35.14]}],
                "trajectories": []
            }
        }
    }
    
    engine = MockEngine()
    group_ids = ["ID1", "ID2"]
    
    print("--- TESTING CONSOLIDATION ---")
    result = await merge_event_group(group_ids, event_data, engine)
    
    print(f"Clusters Count: {len(result['clusters'])}")
    print(f"Trajectories Count: {len(result['trajectories'])}")
    
    if len(result['trajectories']) == 1:
        print("SUCCESS: Consolidated into 1 trajectory.")
        print(f"Target Center: {result['trajectories'][0]['target_coords']}")
        print(f"Recalculated Entry Point: {result['trajectories'][0]['origin_coords']}")
    else:
        print(f"FAILURE: Expected 1 trajectory, got {len(result['trajectories'])}")
        for t in result['trajectories']:
            print(f" - {t['origin']} to {t['target_coords']}")

if __name__ == "__main__":
    asyncio.run(test_merging())
