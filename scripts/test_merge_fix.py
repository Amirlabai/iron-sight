import asyncio
import sys
import os

# Add the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.utils.cluster_utils import merge_event_group
from src.data.data_manager import LamasDataManager
from src.core.engine import TrackingEngine

async def test_merge():
    # 1. Setup Mock Data
    dm = LamasDataManager()
    await dm.load()
    engine = TrackingEngine(dm)
    
    # Mock alerts
    # Alert 1: Tel Aviv
    alert1 = {
        "id": "123456789",
        "category": "missiles",
        "data": {
            "all_cities": [{"name": "תל אביב - יפו", "coords": [32.0853, 34.7818], "area": "תל אביב"}],
            "trajectories": [{"origin": "Gaza", "origin_coords": [31.5, 34.5], "target_coords": [32.0853, 34.7818]}],
            "clusters": [{"hull": [[32.0, 34.7], [32.1, 34.8]]}],
            "category": "missiles"
        }
    }
    
    # Alert 2: Ramat Gan (Adjacent)
    alert2 = {
        "id": "987654321",
        "category": "missiles",
        "data": {
            "all_cities": [{"name": "רמת גן", "coords": [32.0684, 34.8248], "area": "מרכז"}],
            "trajectories": [{"origin": "Gaza", "origin_coords": [31.5, 34.5], "target_coords": [32.0684, 34.8248]}],
            "clusters": [{"hull": [[32.0, 34.8], [32.1, 34.9]]}],
            "category": "missiles"
        }
    }
    
    active_events = {
        "123456789": alert1,
        "987654321": alert2
    }
    
    print("Testing Merge for missiles...")
    merged = await merge_event_group(["123456789", "987654321"], active_events, engine)
    
    print(f"Merged ID: {merged['id']}")
    print(f"City Count: {len(merged['all_cities'])}")
    print(f"Trajectory Count: {len(merged['trajectories'])}")
    print(f"Cluster Count: {len(merged['clusters'])}")
    
    if len(merged['trajectories']) == 1:
        print("SUCCESS: Trajectories unified.")
    else:
        print(f"FAILURE: Found {len(merged['trajectories'])} trajectories.")
        
    print("\nTrajectories Details:")
    for i, t in enumerate(merged['trajectories']):
        print(f"  {i}: {t['origin']} -> {t['target_coords']}")

if __name__ == "__main__":
    asyncio.run(test_merge())
