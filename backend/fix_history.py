import json
import os
from main import TrackingEngine, LamasDataManager

async def migrate_history():
    history_path = 'c:/Users/amirl/OneDrive/Documents/GitHub/redalert-source/backend/history.json'
    if not os.path.exists(history_path):
        print("History file not found.")
        return

    # Initialize Tactical Engine
    dm = LamasDataManager()
    await dm.load()
    engine = TrackingEngine(dm)

    with open(history_path, 'r', encoding='utf-8') as f:
        history = json.load(f)

    print(f"Migrating {len(history)} records to Dynamic Strategic Depth...")

    for event in history:
        for traj in event.get('trajectories', []):
            origin_name = traj.get('origin')
            # Extract cities from the cluster to re-calculate the PCA vector
            # (Note: In a real app we'd store the vector, but here we rebuild from centroid/cities if available)
            # Actually, TrackingEngine.get_capped_origin_coords needs the cluster cities list.
            
            # Find the cluster that matches this trajectory's target_coords (centroid)
            target_centroid = traj.get('target_coords')
            matching_cluster = next((c for c in event.get('clusters', []) if c['centroid'] == target_centroid), None)
            
            if matching_cluster and origin_name:
                # Re-calculate using the new Dynamic Depth logic
                new_origin_coords = engine.get_capped_origin_coords(matching_cluster['cities'], origin_name)
                traj['origin_coords'] = new_origin_coords
                print(f"Updated {origin_name} projection to {new_origin_coords}")

    with open(history_path, 'w', encoding='utf-8') as f:
        json.dump(history, f, indent=2, ensure_ascii=False)

    print("Archive Migration Complete. High-Resolution Dynamic Depth is now locked into history.")

if __name__ == "__main__":
    import asyncio
    asyncio.run(migrate_history())
