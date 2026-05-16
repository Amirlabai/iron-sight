import asyncio
from src.db.mongo_manager import MongoManager

async def check():
    db = MongoManager()
    print("Categories in DB:")
    for coll_name in db.collections:
        count = await db.collections[coll_name].count_documents({})
        print(f"Collection {coll_name}: {count} docs")
        if count > 0:
            sample = await db.collections[coll_name].find_one()
            print(f"  Sample ID: {sample.get('id')}")
            print(f"  Sample Category: {sample.get('category')}")
            print(f"  Has trajectories: {'trajectories' in sample}")
            print(f"  Has clusters: {'clusters' in sample}")
            if 'clusters' in sample and sample['clusters']:
                print(f"  Sample Cluster Origin: {sample['clusters'][0].get('origin')}")

if __name__ == "__main__":
    asyncio.run(check())
