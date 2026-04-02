import os
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

load_dotenv()

# --- Network Configuration ---
WS_PORT = int(os.environ.get("PORT", 8080))
POLL_INTERVAL = 3
TIMEZONE = ZoneInfo("Asia/Jerusalem")

# --- Tactical Logic Constants ---
MIN_IRAN_THRESHOLD = 10
MAX_IRAN_THRESHOLD = 50

# --- Resource URLs ---
LAMAS_DATA_URL = "https://raw.githubusercontent.com/idodov/RedAlert/refs/heads/main/apps/red_alerts_israel/lamas_data.json"
LOCAL_DATA_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "lamas_data.json")
OREF_API_URL = "https://www.oref.org.il/WarningMessages/alert/alerts.json"

# --- Database Configuration ---
MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("DB_NAME", "iron_sight_db")

# --- Collections ---
COLLECTION_SALVO = os.getenv("COLLECTION_NAME", "salvo_history")
COLLECTION_DRONE = "drone_history"
COLLECTION_INFILTRATION = "infiltration_history"
COLLECTION_SEISMIC = "seismic_history"
COLLECTION_LOGS = "event_logs"

# --- Security ---
MISSION_KEY = os.getenv("MISSION_KEY")
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")

# --- Relay Configuration ---
RELAY_URL = os.getenv("RELAY_URL")
RELAY_AUTH_KEY = os.getenv("RELAY_AUTH_KEY")
