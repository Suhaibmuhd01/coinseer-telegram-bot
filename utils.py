"""Utility functions for symbol mappings, formatting, and sanitization."""
from typing import Optional
from app.core.security import sanitize_input
from app.services.api_client import (
    COIN_ID_MAP,
    SYMBOL_DISPLAY_MAP,
    get_coingecko_id,
    get_display_symbol,
)


def format_currency(value: Optional[float], currency_symbol: str = "$", precision: int = 2) -> str:
    if value is None:
        return f"{currency_symbol}N/A"
    symbols = {"USD": "$", "EUR": "€", "GBP": "£", "JPY": "¥", "AUD": "A$"}
    symbol = symbols.get(currency_symbol.upper(), currency_symbol)

    if value >= 1_000_000_000:
        return f"{symbol}{value/1_000_000_000:.1f}B"
    elif value >= 1_000_000:
        return f"{symbol}{value/1_000_000:.1f}M"
    elif value >= 1_000:
        return f"{symbol}{value/1_000:.1f}K"
    else:
        return f"{symbol}{value:,.{precision}f}"


def format_percentage(value: Optional[float], precision: int = 2) -> str:
    if value is None:
        return "N/A%"
    if value > 0:
        return f"+{value:.{precision}f}% ▲"
    elif value < 0:
        return f"{value:.{precision}f}% ▼"
    else:
        return f"{value:.{precision}f}%"


__all__ = [
    "COIN_ID_MAP",
    "SYMBOL_DISPLAY_MAP",
    "get_coingecko_id",
    "get_display_symbol",
    "format_currency",
    "format_percentage",
    "sanitize_input",
]