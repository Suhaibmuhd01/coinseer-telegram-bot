import aiohttp
import logging
from pycoingecko import CoinGeckoAPI
from config import NEWS_API_KEY, DEFAULT_FIAT ;import asyncio
loop = asyncio.get_running_loop()
result = await loop.run_in_executor(None, cg.get_price, ...)

logger = logging.getLogger(__name__)
cg = CoinGeckoAPI() # No API key needed for basic public access

# --- CoinGecko Client ---
async def get_crypto_price(coin_id: str, vs_currency: str = DEFAULT_FIAT):
    """Fetches crypto price from CoinGecko."""
    try:
        # In pycoingecko, coin_id is usually the full name like 'bitcoin', 'ethereum' and rest
        # and vs_currency is 'usd', 'eur' etc.
        # i need a mapping if users type 'BTC'
        coin_map = {"btc": "bitcoin", "eth": "ethereum", "doge": "dogecoin", "sol": "solana"} # Extend this map
        cg_coin_id = coin_map.get(coin_id.lower(), coin_id.lower())

        price_data = cg.get_price(ids=cg_coin_id, vs_currencies=vs_currency,
                                  include_market_cap='true', include_24hr_vol='true',
                                  include_24hr_change='true')
        if price_data and cg_coin_id in price_data:
            return price_data[cg_coin_id]
        return None
    except Exception as e:
        logger.error(f"CoinGecko API error for {coin_id}: {e}")
        return None

async def get_coin_details(coin_id: str):
    """Fetches detailed coin information from CoinGecko."""
    coin_map = {"btc": "bitcoin", "eth": "ethereum", "doge": "dogecoin"}
    cg_coin_id = coin_map.get(coin_id.lower(), coin_id.lower())
    try:
        # This call is quite large, select only what you need if possible
        # For this example, we'll assume it fetches what we need
        # data = cg.get_coin_by_id(id=cg_coin_id, localization='false', tickers='false', community_data='false', developer_data='false', sparkline='false')
        # For simplicity, let's just reuse get_crypto_price and add more details if needed
        return await get_crypto_price(cg_coin_id) # Placeholder
    except Exception as e:
        logger.error(f"CoinGecko get_coin_details error for {coin_id}: {e}")
        return None

async def get_market_chart(coin_id: str, vs_currency: str = DEFAULT_FIAT, days: int = 7):
    """Fetches market chart data for a coin."""
    coin_map = {"btc": "bitcoin", "eth": "ethereum", "doge": "dogecoin"}
    cg_coin_id = coin_map.get(coin_id.lower(), coin_id.lower())
    try:
        chart_data = cg.get_coin_market_chart_by_id(id=cg_coin_id, vs_currency=vs_currency, days=days)
        return chart_data # Contains 'prices', 'market_caps', 'total_volumes'
    except Exception as e:
        logger.error(f"CoinGecko get_market_chart error for {coin_id}: {e}")
        return None


# --- NewsAPI Client ---
async def get_crypto_news(query: str = "cryptocurrency", sources: str = None, page_size: int = 5):
    """Fetches crypto news from NewsAPI."""
    if not NEWS_API_KEY:
        logger.warning("NEWS_API_KEY not configured. News feature will be disabled.")
        return []

    url = "https://newsapi.org/v2/everything"
    params = {
        "q": query,
        "apiKey": NEWS_API_KEY,
        "pageSize": page_size,
        "sortBy": "publishedAt", # relevance, popularity
        "language": "en"
    }
    if sources:
        params["sources"] = sources # e.g., 'crypto-coins-news,bloomberg,reuters'

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, params=params) as response:
                response.raise_for_status() # Raise an exception for HTTP errors
                data = await response.json()
                return data.get("articles", [])
        except aiohttp.ClientError as e:
            logger.error(f"NewsAPI request error: {e}")
            return []
        except Exception as e:
            logger.error(f"Error processing NewsAPI response: {e}")
            return []

# --- Fear & Greed Index (Example from alternative.me) ---
async def get_fear_greed_index():
    """Fetches the Fear & Greed Index from alternative.me API."""
    url = "https://api.alternative.me/fng/?limit=1" # Gets the latest
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url) as response:
                response.raise_for_status()
                data = await response.json()
                if data and "data" in data and len(data["data"]) > 0:
                    return data["data"][0] # Returns {'value': '...', 'value_classification': '...', ...}
                return None
        except aiohttp.ClientError as e:
            logger.error(f"Fear & Greed API request error: {e}")
            return None
        except Exception as e:
            logger.error(f"Error processing Fear & Greed API response: {e}")
            return None