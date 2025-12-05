import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID", "0"))
ADMIN_IDS = [int(x.strip()) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]
CARD_NUMBER = os.getenv("CARD_NUMBER", "8600 0000 0000 0000")

# Narxlar (so'm)
REGULAR_POST_PRICE = int(os.getenv("REGULAR_POST_PRICE", "30000"))  # Oddiy e'lon narxi
AUCTION_POST_PRICE = int(os.getenv("AUCTION_POST_PRICE", "40000"))  # Auksiyon e'lon narxi
