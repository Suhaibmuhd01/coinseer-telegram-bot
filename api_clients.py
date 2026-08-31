"""Legacy api_clients compatibility bridge."""
from app.services.api_client import (
    api_client,
    get_coingecko_id,
    get_display_symbol,
    GasTrackerClient,
    GeminiAIEngine,
    ChartRenderer,
)

get_crypto_price = api_client.get_crypto_price
get_market_chart = api_client.get_market_chart
get_coin_details = api_client.get_coin_details
get_top_movers = api_client.get_top_movers
get_fear_greed_index = api_client.get_fear_greed_index
get_crypto_news = api_client.get_crypto_news

__all__ = [
    "api_client",
    "get_crypto_price",
    "get_market_chart",
    "get_coin_details",
    "get_top_movers",
    "get_fear_greed_index",
    "get_crypto_news",
    "get_coingecko_id",
    "get_display_symbol",
    "GasTrackerClient",
    "GeminiAIEngine",
    "ChartRenderer",
]