import os
import csv
import json
from pymongo import MongoClient
from dotenv import load_dotenv

# Load credentials from backend/.env
ENV_PATH = os.path.join(os.path.dirname(__file__), "..", "backend", ".env")
load_dotenv(ENV_PATH)

MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("DB_NAME", "iron_sight")
COLLECTION_LOGS = "event_logs"

def export_to_csv():
    if not MONGO_URI:
        print("ERROR: MONGO_URI not found in backend/.env")
        return

    try:
        client = MongoClient(MONGO_URI)
        db = client[DB_NAME]
        collection = db[COLLECTION_LOGS]

        # Fetch all documents
        cursor = collection.find().sort("start_time", -1)
        logs = list(cursor)

        if not logs:
            print("No logs found in the collection.")
            return

        # Prepare CSV fields
        # Note: We'll include the top-level fields and stringify the nested ones.
        field_names = [
            "event_id", "category", "is_simulation", "start_time", 
            "last_update_time", "end_time", "termination_reason", 
            "city_count", "city_list", "updates_count", "timeline"
        ]

        output_file = os.path.join(os.path.dirname(__file__), "..", "logs_export.csv")

        with open(output_file, mode='w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=field_names)
            writer.writeheader()

            for log in logs:
                # Remove MongoDB _id
                log.pop("_id", None)

                # Format nested fields
                if 'city_list' in log and isinstance(log['city_list'], list):
                    log['city_list'] = "; ".join(log['city_list'])
                
                if 'timeline' in log:
                    # Serializing timeline for full data integrity
                    log['timeline'] = json.dumps(log['timeline'])

                # Filter keys to match field_names
                row = {key: log.get(key, "") for key in field_names}
                writer.writerow(row)

        print(f"SUCCESS: Logs exported to {output_file}")
        print(f"Total records: {len(logs)}")

    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    export_to_csv()
