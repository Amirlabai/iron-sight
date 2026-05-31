import os
import asyncio
import math
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from main import TrackingEngine, LamasDataManager

async def mine_tactical_data():
    load_dotenv()
    uri = os.getenv("MONGO_URI")
    db_name = os.getenv("DB_NAME")
    coll_name = os.getenv("COLLECTION_NAME")
    
    client = AsyncIOMotorClient(uri)
    db = client[db_name]
    coll = db[coll_name]
    
    dm = LamasDataManager()
    engine = TrackingEngine(dm)
    
    print("\n" + "="*60)
    print(" IRON SIGHT - TACTICAL INTELLIGENCE DATA MINER")
    print("="*60)
    
    cursor = coll.find({
        "verified": True,
        "trajectories.0": {"$exists": True},
    })
    calibrations = await cursor.to_list(length=500)
    
    if not calibrations:
        print("[!] NO VERIFIED SALVOS FOUND IN DATABASE.")
        print("    Calibrate salvos in history-fixer (COMMIT & VERIFY) first.")
        return

    results = {}
    
    for salvo in calibrations:
        traj = (salvo.get("trajectories") or [{}])[0]
        origin = salvo.get("manual_origin") or traj.get("origin")
        if not origin:
            continue
        if origin not in results:
            results[origin] = []
            
        cluster = salvo.get("clusters", [{}])[0]
        cities = cluster.get("cities", [])
        
        # Calculate raw regression vector
        v_lat, v_lon = engine.calculate_regression_vector(cities)
        mag = math.sqrt(v_lat**2 + v_lon**2)
        
        # Calculate angle (0 = North, 90 = East, 180 = South, 270 = West)
        angle = math.degrees(math.atan2(v_lon, v_lat))
        if angle < 0: angle += 360
            
        results[origin].append({
            "id": salvo.get("id"),
            "mag": mag,
            "angle": angle
        })

    print(f"[*] ANALYZING {len(calibrations)} MANUAL CALIBRATIONS...\n")
    
    for origin, entries in results.items():
        avg_mag = sum(e["mag"] for e in entries) / len(entries)
        avg_angle = sum(e["angle"] for e in entries) / len(entries)
        
        print(f"THEATER: {origin.upper()}")
        print(f"  - Count: {len(entries)}")
        print(f"  - Avg Magnitude: {avg_mag:.4f}")
        print(f"  - Avg Launch Angle: {avg_angle:.2f}°")
        print(f"  - Detailed Map Vectors:")
        for e in entries:
            status = "SIM_DATA" if e["mag"] > 0 else "SINGLE_HIT_STATIC"
            print(f"    [ID: {e['id']}] Angle: {e['angle']:>6.2f}° | Mag: {e['mag']:.4f} | Status: {status}")
        print("-" * 30)

    print("\n[*] DATA MINING COMPLETE.")
    print("    Use these angles and magnitudes to tune TrackingEngine detection thresholds.")

if __name__ == "__main__":
    asyncio.run(mine_tactical_data())
