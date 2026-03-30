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

    for event in history:
        new_highlights = []
        highlight_names = set()
        
        for traj in event.get('trajectories', []):
            # Re-classify and Re-project every track based on V3.8 Theater Heuristics
            target_centroid = traj.get('target_coords')
            matching_cluster = next((c for c in event.get('clusters', []) if (c['centroid'][0] == target_centroid[0] and c['centroid'][1] == target_centroid[1])), None)
            
            if matching_cluster:
                # 1. Re-detect origin (e.g., Iran -> North Iran if applicable)
                new_org_name = engine.get_origin(matching_cluster['cities'])
                traj['origin'] = new_org_name
                
                # 2. Re-project trajectory depth (e.g., North Iran 16.0)
                new_origin_coords = engine.get_capped_origin_coords(matching_cluster['cities'], new_org_name)
                traj['origin_coords'] = new_origin_coords
                
                # 3. Strategic Highlight Alias (Always keep the whole country red)
                highlight_name = "Iran" if new_org_name == "North Iran" else new_org_name
                if highlight_name not in highlight_names:
                    fixed_pin = engine.origins.get(highlight_name, [0, 0])
                    new_highlights.append({"name": highlight_name, "coords": fixed_pin})
                    highlight_names.add(highlight_name)
                
                print(f"Archive Re-Classification: {new_org_name} detected at {new_origin_coords}")
        
        event['highlight_origins'] = new_highlights

    with open(history_path, 'w', encoding='utf-8') as f:
        json.dump(history, f, indent=2, ensure_ascii=False)

    print("Archive Migration Complete. V3.8 Theater Intelligence is now synchronized.")

if __name__ == "__main__":
    import asyncio
    asyncio.run(migrate_history())
