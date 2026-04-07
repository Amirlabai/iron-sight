import numpy as np
import sys
import os

# Mocking parts of the system to test cluster_utils
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from src.utils.cluster_utils import _compute_adjacency_matrix, _get_connected_components

def test_shared_city_merging():
    # Alerts sharing a city should merge
    items = [
        {
            "id": "A",
            "category": "missiles",
            "cities": [{"name": "Tel Aviv"}, {"name": "Haifa"}],
            "center": [32.0853, 34.7818]
        },
        {
            "id": "B",
            "category": "missiles",
            "cities": [{"name": "Haifa"}, {"name": "Nazareth"}],
            "center": [32.7940, 34.9896]
        }
    ]
    
    # Run adjacency matrix builder
    adj = _compute_adjacency_matrix(items, threshold_km=1) # Low threshold to ensure only shared city trigger
    components = _get_connected_components(adj)
    
    print(f"Components found: {components}")
    if len(components) == 1:
        print("SUCCESS: A and B merged due to shared city 'Haifa'.")
    else:
        print("FAILURE: A and B did not merge.")

if __name__ == "__main__":
    test_shared_city_merging()
