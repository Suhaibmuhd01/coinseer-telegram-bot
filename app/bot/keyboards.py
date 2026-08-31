from typing import List
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from app.core.config import settings


def get_main_menu_keyboard(webapp_url: str = None) -> InlineKeyboardMarkup:
    """Build dynamic main menu keyboard with institutional badges & Mini-App button."""
    target_webapp_url = webapp_url or (
        f"{settings.TELEGRAM_WEBHOOK_URL.replace('/webhook', '')}/webapp"
        if settings.TELEGRAM_WEBHOOK_URL
        else "https://coinseer.app/webapp"
    )

    keyboard = [
        [
            InlineKeyboardButton(" Launch Web3 Mini-App", web_app=WebAppInfo(url=target_webapp_url)),
        ],
        [
            InlineKeyboardButton("[QUOTE] BTC / USD", callback_data="price_btc"),
            InlineKeyboardButton("[AI] Market Brief", callback_data="ai_brief_trigger"),
        ],
        [
            InlineKeyboardButton("[GAS] Fee Tracker", callback_data="gas_tracker"),
            InlineKeyboardButton("[ALERT] Set Trigger", callback_data="alert_start"),
        ],
        [
            InlineKeyboardButton("[VAULT] Portfolio", callback_data="portfolio_view"),
            InlineKeyboardButton("[TRACK] Watchlist", callback_data="watchlist_view"),
        ],
        [
            InlineKeyboardButton("[NEWS] Intel Feed", callback_data="news_crypto"),
            InlineKeyboardButton("[INDEX] Fear & Greed", callback_data="fear_greed_view"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_experience_level_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton("[LVL 1] Beginner", callback_data="exp_beginner"),
            InlineKeyboardButton("[LVL 2] Intermediate", callback_data="exp_intermediate"),
        ],
        [
            InlineKeyboardButton("[LVL 3] Web3 Native / Pro", callback_data="exp_advanced"),
            InlineKeyboardButton("[SKIP] Default Config", callback_data="exp_skip"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_fiat_selection_keyboard(supported_fiats: List[str]) -> InlineKeyboardMarkup:
    buttons = []
    row = []
    for fiat in supported_fiats:
        row.append(InlineKeyboardButton(f"[{fiat.upper()}]", callback_data=f"set_fiat_{fiat}"))
        if len(row) == 3:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    return InlineKeyboardMarkup(buttons)


def get_alert_condition_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton("▲ Price Crosses Above", callback_data="alert_cond_above"),
            InlineKeyboardButton("▼ Price Crosses Below", callback_data="alert_cond_below"),
        ],
        [
            InlineKeyboardButton("[x] Cancel", callback_data="alert_cancel"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_alert_recurring_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton("[1x] One-Time Trigger", callback_data="alert_recurring_false"),
            InlineKeyboardButton("[INF] Recurring Monitor", callback_data="alert_recurring_true"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)
