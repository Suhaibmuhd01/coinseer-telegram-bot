import logging
import re

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
    "polygon": "matic-network",
    "usdt": "tether",
    "usdc": "usd-coin",
    "bnb": "binancecoin",
    "avax": "avalanche-2",
    "avalanche": "avalanche-2",
    "trx": "tron",
    "xlm": "stellar",
    "uni": "uniswap",
    "hmtr": "hamster-kombat",
    "ton": "the-open-network",
    "atom": "cosmos",
    "near": "near",
    "algo": "algorand",
    "ftm": "fantom",
    "fantom": "fantom",
    "icp": "internet-computer",
    "hbar": "hedera-hashgraph",
    "vet": "vechain",
    "fil": "filecoin",
    "theta": "theta-token",
    "axs": "axie-infinity",
    "sand": "the-sandbox",
    "mana": "decentraland",
    "grt": "the-graph",
    "mkr": "maker",
    "comp": "compound-governance-token",
    "aave": "aave",
    "snx": "synthetix-network-token",
    "crv": "curve-dao-token",
    "1inch": "1inch",
    "sushi": "sushi",
    "yfi": "yearn-finance",
    "bat": "basic-attention-token",
    "zrx": "0x",
    "omg": "omisego",
    "knc": "kyber-network-crystal",
    "lrc": "loopring",
    "ren": "republic-protocol",
    "storj": "storj",
    "band": "band-protocol",
    "bal": "balancer",
    "uma": "uma",
    "rlc": "iexec-rlc"
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
    
    # Handle different currency symbols
    if currency_symbol.upper() in ["USD", "EUR", "GBP", "JPY", "AUD"]:
        symbols = {"USD": "$", "EUR": "€", "GBP": "£", "JPY": "¥", "AUD": "A$"}
        symbol = symbols.get(currency_symbol.upper(), currency_symbol)
    else:
        symbol = currency_symbol
    
    # Format large numbers with appropriate suffixes
    if value >= 1_000_000_000:
        return f"{symbol}{value/1_000_000_000:.1f}B"
    elif value >= 1_000_000:
        return f"{symbol}{value/1_000_000:.1f}M"
    elif value >= 1_000:
        return f"{symbol}{value/1_000:.1f}K"
    else:
        return f"{symbol}{value:,.{precision}f}"
    return f"{currency_symbol}{value:,.{precision}f}"

def format_percentage(value: float, precision: int = 2) -> str:
    """Format a float as a percentage string."""
    if value is None:
        return "N/A%"
    
    # Add color indicators for positive/negative changes
    if value > 0:
        return f"+{value:.{precision}f}% 📈"
    elif value < 0:
        return f"{value:.{precision}f}% 📉"
    else:
        return f"{value:.{precision}f}%"

def sanitize_input(text: str) -> str:
    """Sanitize user input to prevent injection."""
    if not text:
        return ""
    # Allow alphanumeric, spaces, dots, hyphens, and underscores
    sanitized = re.sub(r'[^a-zA-Z0-9\s.\-_]', '', text.strip())
    return sanitized[:100]  # Limit length

def validate_amount(amount_str: str) -> tuple[bool, float]:
    """Validate and parse amount input."""
    try:
        amount = float(amount_str)
        if amount <= 0:
            return False, 0.0
        if amount > 1_000_000_000:  # Reasonable upper limit
            return False, 0.0
        return True, amount
    except (ValueError, TypeError):
        return False, 0.0

def validate_price(price_str: str) -> tuple[bool, float]:
    """Validate and parse price input."""
    try:
        price = float(price_str)
        if price <= 0:
            return False, 0.0
        if price > 10_000_000:  # Reasonable upper limit
            return False, 0.0
        return True, price
    except (ValueError, TypeError):
        return False, 0.0

def format_time_ago(timestamp):
    """Format timestamp as time ago string."""
    from datetime import datetime, timezone
    try:
        if isinstance(timestamp, str):
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        else:
            dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
        
        now = datetime.now(timezone.utc)
        diff = now - dt
        
        if diff.days > 0:
            return f"{diff.days}d ago"
        elif diff.seconds > 3600:
            return f"{diff.seconds // 3600}h ago"
        elif diff.seconds > 60:
            return f"{diff.seconds // 60}m ago"
        else:
            return "Just now"
    except Exception:
        return "Unknown"

if __name__ == '__main__':
    print(f"CoinGecko ID for 'BTC': {get_coingecko_id('BTC')}")
    print(f"Display symbol for 'bitcoin': {get_display_symbol('bitcoin')}")
    print(f"Formatted currency: {format_currency(12345.6789)}")
    print(f"Formatted percentage: {format_percentage(23.456)}")
    print(f"Sanitized input: {sanitize_input('BTC@#$%^&*()123')}")
    print(f"Validate amount: {validate_amount('0.5')}")
    print(f"Validate price: {validate_price('65000')}")