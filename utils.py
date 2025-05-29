from utils import get_display_symbol

import logging

logger = logging.getLogger(__name__)
display_symbol = get_display_symbol(coin_id)
# --- Coin Symbol/ID Mapping ---
# This mapping helps translate user input (like 'BTC') to the ID
# that CoinGecko API expects (like 'bitcoin').
# You should expand this list as needed.
COIN_ID_MAP = {
    "btc": "bitcoin",
    "eth": "ethereum",
    "ltc": "litecoin",
    "xrp": "ripple",
    "bch": "bitcoin-cash",
    "ada": "cardano",
    "dot": "polkadot",
    "not": "notcoin",
    "doge": "dogecoin",
    "shib": "shiba-inu",
    "sol": "solana",
    "link": "chainlink",
    "matic": "matic-network",
    "usdt": "tether",
    "usdc": "usd-coin",
    "bnb": "binancecoin",
    "avax": "avalanche-2",
    "trx": "tron",
    "xlm": "stellar",
    "uni": "uniswap",
    "hmtr": "Hamster",
}

# Reverse mapping to get common symbol from ID (useful for display)
# This can be auto-generated from COIN_ID_MAP if IDs are unique display symbols
# For simplicity, we'll keep it separate. we might need a more complex solution
# if multiple IDs could map back to a similar user-facing symbol or if CoinGecko IDs
# are not always the desired display symbol.;
SYMBOL_DISPLAY_MAP = {v: k.upper() for k, v in COIN_ID_MAP.items()}


def get_coingecko_id(user_input_symbol: str) -> str:
    """
    Tries to find the CoinGecko API compatible coin ID for a given user symbol.
    Defaults to the lowercased symbol if not found in the map.
    """
    symbol_lower = user_input_symbol.lower()
    return COIN_ID_MAP.get(symbol_lower, symbol_lower)

def get_display_symbol(coingecko_id: str) -> str:
    """
    Tries to get a common display symbol (e.g., BTC) from a CoinGecko ID.
    Defaults to the capitalized ID if not found.
    """
    return SYMBOL_DISPLAY_MAP.get(coingecko_id, coingecko_id.capitalize())


# --- Formatting Helpers (Optional examples) ---
def format_currency(value: float, currency_symbol: str = "$", precision: int = 2) -> str:
    """Formats a float as a currency string."""
    if value is None:
        return f"{currency_symbol}N/A"
    return f"{currency_symbol}{value:,.{precision}f}"

def format_percentage(value: float, precision: int = 2) -> str:
    """Formats a float as a percentage string."""
    if value is None:
        return "N/A%"
    return f"{value:.{precision}f}%"

# You can add more utility functions here as your bot grows.
# For example:
# - Functions to create standard Telegram inline keyboard layouts
# - Date/time formatting utilities
# - Input validation helpers

if __name__ == '__main__':
    # Test the functions
    print(f"CoinGecko ID for 'BTC': {get_coingecko_id('BTC')}")
    print(f"CoinGecko ID for 'Ethereum': {get_coingecko_id('Ethereum')}")
    print(f"CoinGecko ID for 'nonexistent': {get_coingecko_id('nonexistentcoin')}")

    print(f"Display symbol for 'bitcoin': {get_display_symbol('bitcoin')}")
    print(f"Display symbol for 'matic-network': {get_display_symbol('matic-network')}")

    print(f"Formatted currency: {format_currency(12345.6789)}")
    print(f"Formatted percentage: {format_percentage(23.456)}")