import os
from dotenv import load_dotenv

load_dotenv()

FYERS_CLIENT_ID = os.getenv("FYERS_CLIENT_ID", "")
FYERS_ACCESS_TOKEN = os.getenv("FYERS_ACCESS_TOKEN", "")
HYPERLIQUID_API = "https://api.hyperliquid.xyz/info"
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8080"))
