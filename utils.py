import logging

logger = logging.getLogger(__name__)

# Expanded coin ID mapping
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
    "hmtr": "hamster-kombat",
    "ton": "the-open-network",
    "atom": "cosmos",
    "near": "near",
    "algo": "algorand",
}

SYMBOL_DISPLAY_MAP = {v: k.upper() for k, v in COIN_ID_MAP.items()}

def get_coingecko_id(user_input_symbol: str) -> str:
    """Map user input symbol to CoinGecko API ID."""
    symbol_lower = user_input_symbol.lower()
    return COIN_ID_MAP.get(symbol_lower, symbol_lower)

def get_display_symbol(coingecko_id: str) -> str:
    """Get display symbol from CoinGecko ID."""
    return SYMBOL_DISPLAY_MAP.get(coingecko_id, coingecko_id.capitalize())

def format_currency(value: float, currency_symbol: str = "$", precision: int = 2) -> str:
    """Format a float as a currency string."""
    if value is None:
        return f"{currency_symbol}N/A"
    return f"{currency_symbol}{value:,.{precision}f}"

def format_percentage(value: float, precision: int = 2) -> str:
    """Format a float as a percentage string."""
    if value is None:
        return "N/A%"
    return f"{value:.{precision}f}%"

def sanitize_input(text: str) -> str:
    """Sanitize user input to prevent injection."""
    return ''.join(c for c in text if c.isalnum() or c in ' .-').strip()

if __name__ == '__main__':
    print(f"CoinGecko ID for 'BTC': {get_coingecko_id('BTC')}")
    print(f"Display symbol for 'bitcoin': {get_display_symbol('bitcoin')}")
    print(f"Formatted currency: {format_currency(12345.6789)}")
    print(f"Formatted percentage: {format_percentage(23.456)}")