import asyncio
from unittest.mock import AsyncMock, MagicMock

class MockMongoManager:
    def __init__(self):
        self.collections = {
            "missiles": MagicMock(),
            "hostileAircraftIntrusion": MagicMock(),
            "terroristInfiltration": MagicMock(),
            "earthQuake": MagicMock(),
        }

    async def get_history(self, alert_type, limit=50):
        # Return different IDs to test interleaving
        if alert_type == "missiles":
            return [{"id": "100", "category": "missiles"}, {"id": "096", "category": "missiles"}]
        elif alert_type == "hostileAircraftIntrusion":
            return [{"id": "099", "category": "hostileAircraftIntrusion"}, {"id": "097", "category": "hostileAircraftIntrusion"}]
        elif alert_type == "terroristInfiltration":
            return [{"id": "098", "category": "terroristInfiltration"}]
        elif alert_type == "earthQuake":
            return [{"id": "095", "category": "earthQuake"}]
        return []

    async def get_consolidated_history(self, limit=50):
        import asyncio
        tasks = [self.get_history(alert_type, limit=limit) for alert_type in self.collections]
        results = await asyncio.gather(*tasks)
        unified = []
        for res in results: unified.extend(res)
        unified.sort(key=lambda x: str(x.get("id", "")), reverse=True)
        return unified[:limit]

async def test_consolidation():
    db = MockMongoManager()
    history = await db.get_consolidated_history(limit=50)
    ids = [item['id'] for item in history]
    print(f"Consolidated History IDs: {ids}")
    # Expected: 100 (missile), 099 (drone), 098 (infiltration), 097 (drone), 096 (missile), 095 (earthquake)
    expected = ["100", "099", "098", "097", "096", "095"]
    assert ids == expected, f"Sort mismatch: got {ids}, expected {expected}"
    print("Verification [History Consolidation]: SUCCESS")

if __name__ == "__main__":
    asyncio.run(test_consolidation())
