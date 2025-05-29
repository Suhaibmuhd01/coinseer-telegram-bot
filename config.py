import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
# COINGECKO_API_KEY = os.getenv("COINGECKO_API_KEY") # Not strictly needed for many basic calls
NEWS_API_KEY = os.getenv("NEWS_API_KEY")

# Database
DB_NAME = "coinseer_bot.db"

# Other constants
SUPPORTED_FIAT = ["usd", "eur", "gbp"]
DEFAULT_FIAT = "usd"
NEWS_SOURCES = "coindesk,cointelegraph,decrypt" # Example for NewsAPI