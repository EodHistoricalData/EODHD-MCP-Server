import os
from dotenv import load_dotenv

load_dotenv()
EODHD_API_BASE = "https://eodhd.com/api"
EODHD_API_KEY = os.environ.get("EODHD_API_KEY", "demo")
