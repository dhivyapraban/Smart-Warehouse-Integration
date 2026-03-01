import os
from dotenv import load_dotenv

load_dotenv()

MOCK_MODE = os.getenv("MOCK_MODE", "True").lower() == "true"
ERP_URL = os.getenv("ERP_URL", "")
ERP_API_KEY = os.getenv("ERP_API_KEY", "")
ERP_API_SECRET = os.getenv("ERP_API_SECRET", "")

HEADERS = {
    "Authorization": f"token {ERP_API_KEY}:{ERP_API_SECRET}",
    "ngrok-skip-browser-warning": "true",
    "Content-Type": "application/json",
    "Accept": "application/json"
}
