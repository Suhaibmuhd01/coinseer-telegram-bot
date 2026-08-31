"""Legacy config compatibility bridge."""
from app.core.config import settings

TELEGRAM_BOT_TOKEN = settings.TELEGRAM_BOT_TOKEN
DATABASE_URL = settings.DATABASE_URL
REDIS_URL = settings.REDIS_URL
SUPPORTED_FIAT = settings.SUPPORTED_FIAT
DEFAULT_FIAT = settings.DEFAULT_FIAT
NEWS_API_KEY = settings.NEWS_API_KEY
COINGECKO_API_KEY = settings.COINGECKO_API_KEY