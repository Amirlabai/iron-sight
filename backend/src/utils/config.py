import os
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

_BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
load_dotenv(os.path.join(_BACKEND_DIR, ".env"))
load_dotenv()

# --- Network Configuration ---
WS_PORT = int(os.environ.get("PORT", 8080))
POLL_INTERVAL = 3
TIMEZONE = ZoneInfo("Asia/Jerusalem")

# --- Tactical Logic Constants ---
MIN_IRAN_THRESHOLD = 35
MAX_IRAN_THRESHOLD = 50

# --- Hull Inflation Factors ---
DEFAULT_INFLATION_FACTOR = 1.0
DRONE_INFLATION_FACTOR = 1.5
MISSILE_INFLATION_FACTOR = 1.25

# --- Resource URLs ---
LAMAS_DATA_URL = "https://raw.githubusercontent.com/idodov/RedAlert/refs/heads/main/apps/red_alerts_israel/lamas_data.json"
LOCAL_DATA_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "lamas_data.json")
CITIES_DATA_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "cities.json")
POLYGONS_DATA_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "polygons.json")
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
ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("ALLOWED_ORIGINS", "*").split(",")
    if origin.strip()
]

# --- Relay Configuration ---
RELAY_URL = os.getenv("RELAY_URL")
RELAY_AUTH_KEY = os.getenv("RELAY_AUTH_KEY")

# --- Web Push (VAPID) ---
VAPID_PUBLIC_KEY = os.getenv("VAPID_PUBLIC_KEY")
VAPID_PRIVATE_KEY = os.getenv("VAPID_PRIVATE_KEY")
VAPID_CLAIMS_EMAIL = os.getenv("VAPID_CLAIMS_EMAIL", "mailto:ops@iron-sight.local")
COLLECTION_PUSH = "push_subscriptions"
