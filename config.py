"""
Конфигурационный файл бота.
"""

import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "https://your-app.onrender.com")
MONGODB_URI = os.getenv("MONGODB_URI") or None
