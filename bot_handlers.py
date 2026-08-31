"""Legacy bot_handlers compatibility bridge."""
from app.bot.handlers import register_handlers
from app.bot.handlers.start import start_command, help_command
from app.bot.handlers.price import price_command, chart_command
from app.bot.handlers.alert import (
    alert_command_start,
    my_alerts_command,
    delete_alert_command,
)
from app.bot.handlers.watchlist import (
    watchlist_command,
    watchlist_add_command,
    watchlist_remove_command,
)
from app.bot.handlers.portfolio import (
    portfolio_command,
    portfolio_add_command,
    portfolio_remove_command,
)
from app.bot.handlers.ai_brief import ai_brief_command
from app.bot.handlers.gas import gas_command
from app.bot.handlers.settings import settings_command
from app.bot.handlers.news import news_command
from app.bot.handlers.market import fear_greed_command, topmovers_command, market_command

__all__ = [
    "register_handlers",
    "start_command",
    "help_command",
    "price_command",
    "chart_command",
    "alert_command_start",
    "my_alerts_command",
    "delete_alert_command",
    "watchlist_command",
    "watchlist_add_command",
    "watchlist_remove_command",
    "portfolio_command",
    "portfolio_add_command",
    "portfolio_remove_command",
    "ai_brief_command",
    "gas_command",
    "settings_command",
    "news_command",
    "fear_greed_command",
    "topmovers_command",
    "market_command",
]