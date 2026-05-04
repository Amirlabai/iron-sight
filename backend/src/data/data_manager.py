import json
import os
import aiohttp
import logging
from src.utils.config import LAMAS_DATA_URL, LOCAL_DATA_FILE
from src.utils.text_utils import standardize_name

logger = logging.getLogger("IronSightBackend")

class LamasDataManager:
    def __init__(self):
        self.city_map = {}
        self.city_to_id = {} # Standardized name -> City ID
        self.areas = {}

    async def load(self):
        """Load geographical data from local cache or remote repository."""
        from src.utils.config import CITIES_DATA_FILE
        data_path = LOCAL_DATA_FILE
        # Ensure directory exists
        os.makedirs(os.path.dirname(data_path), exist_ok=True)
        
        if os.path.exists(data_path):
            with open(data_path, 'r', encoding='utf-8-sig') as f:
                data = json.load(f)
        else:
            logger.info("Initializing remote city data download...")
            async with aiohttp.ClientSession() as session:
                async with session.get(LAMAS_DATA_URL) as resp:
                    if resp.status != 200:
                        raise Exception(f"DATA_FETCH_FAILURE: Status {resp.status}")
                    text = await resp.text()
                    text = text.lstrip('\ufeff').strip()
                    data = json.loads(text)
            with open(data_path, 'w', encoding='utf-8-sig') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

        self.areas = data.get('areas', {})
        for area, cities in self.areas.items():
            for city, details in cities.items():
                std = standardize_name(city)
                self.city_map[std] = {
                    "lat": float(details.get("lat", 0)),
                    "lon": float(details.get("long", 0)),
                    "area": area,
                    "name": city
                }

        # Load IDs from cities.json
        if os.path.exists(CITIES_DATA_FILE):
            try:
                with open(CITIES_DATA_FILE, 'r', encoding='utf-8') as f:
                    cities_data = json.load(f)
                    for city_obj in cities_data:
                        std = standardize_name(city_obj.get("name"))
                        if std:
                            self.city_to_id[std] = city_obj.get("id")
                logger.info(f"CITY_IDS_LOADED: {len(self.city_to_id)} mappings.")
            except Exception as e:
                logger.error(f"CITY_IDS_LOAD_FAILURE: {e}")

        logger.info(f"TACTICAL_DATA_LOADED: {len(self.city_map)} cities mapped.")
