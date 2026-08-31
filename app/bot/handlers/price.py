from datetime import datetime
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes
from sqlalchemy import select
from app.core.database import async_session_factory
from app.core.security import sanitize_input, escape_markdown
from app.models.user import User
from app.services.api_client import (
    api_client,
    get_coingecko_id,
    get_display_symbol,
    ChartRenderer,
)


def format_currency_value(value: float, fiat: str = "USD") -> str:
    if value is None:
        return "N/A"
    symbols = {"USD": "$", "EUR": "€", "GBP": "£", "JPY": "¥", "AUD": "A$"}
    sym = symbols.get(fiat.upper(), f"{fiat.upper()} ")
    if value >= 1_000_000_000:
        return f"{sym}{value/1_000_000_000:.2f}B"
    elif value >= 1_000_000:
        return f"{sym}{value/1_000_000:.2f}M"
    elif value >= 1:
        return f"{sym}{value:,.2f}"
    else:
        return f"{sym}{value:,.4f}"


async def price_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    target_coin = "btc"
    if context.args:
        target_coin = sanitize_input(context.args[0], 32)

    coin_id = get_coingecko_id(target_coin)
    display_sym = get_display_symbol(coin_id)

    preferred_fiat = "usd"
    async with async_session_factory() as session:
        res = await session.execute(select(User.preferred_fiat).where(User.user_id == user_id))
        fiat = res.scalar_one_or_none()
        if fiat:
            preferred_fiat = fiat

    data = await api_client.get_crypto_price([coin_id], vs_currency=preferred_fiat)
    coin_data = data.get(coin_id, {})
    price = coin_data.get(preferred_fiat)

    if price is None:
        safe_sym = escape_markdown(target_coin.upper())
        await update.message.reply_text(
            f"[ERROR] Unable to retrieve real-time data for `{safe_sym}`. Please verify symbol or name.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    change_24h = coin_data.get(f"{preferred_fiat}_24h_change", 0.0)
    market_cap = coin_data.get(f"{preferred_fiat}_market_cap", 0.0)
    vol_24h = coin_data.get(f"{preferred_fiat}_24h_vol", 0.0)
    change_symbol = "▲" if change_24h >= 0 else "▼"

    message = (
        f"[QUOTE] **{display_sym} ({coin_id.upper()}) Market Snapshot**\n\n"
        f"• **Current Price**: **{format_currency_value(price, preferred_fiat)}**\n"
        f"• **24h Change**: {change_symbol} `{change_24h:+.2f}%`\n"
        f"• **24h Trading Volume**: {format_currency_value(vol_24h, preferred_fiat)}\n"
        f"• **Market Capitalization**: {format_currency_value(market_cap, preferred_fiat)}\n\n"
        f"[INFO] _Use `/chart {display_sym}` for historical technical charts._"
    )

    await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)


async def chart_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    target_coin = "btc"
    days = 7

    if context.args:
        target_coin = sanitize_input(context.args[0], 32)
        if len(context.args) > 1:
            try:
                days = max(1, min(int(sanitize_input(context.args[1], 8)), 90))
            except ValueError:
                pass

    coin_id = get_coingecko_id(target_coin)
    display_sym = get_display_symbol(coin_id)

    preferred_fiat = "usd"
    async with async_session_factory() as session:
        res = await session.execute(select(User.preferred_fiat).where(User.user_id == user_id))
        fiat = res.scalar_one_or_none()
        if fiat:
            preferred_fiat = fiat

    status_msg = await update.message.reply_text(f"[RENDER] Generating {days}-day technical chart for **{display_sym}**...")

    chart_data = await api_client.get_market_chart(coin_id, vs_currency=preferred_fiat, days=days)
    if not chart_data or "prices" not in chart_data or not chart_data["prices"]:
        await status_msg.edit_text(f"[ERROR] Historical chart data unavailable for **{display_sym}**.")
        return

    raw_prices = chart_data["prices"]
    step = max(1, len(raw_prices) // 20)
    sampled = raw_prices[::step]

    dates = [datetime.fromtimestamp(ts / 1000).strftime("%m-%d") for ts, _ in sampled]
    prices = [p for _, p in sampled]

    chart_url = ChartRenderer.render_price_trend_chart(display_sym, dates, prices, preferred_fiat)

    caption = (
        f"[CHART] **{display_sym} {days}-Day Technical Trend**\n"
        f"• **Open**: {format_currency_value(prices[0], preferred_fiat)}\n"
        f"• **Latest**: {format_currency_value(prices[-1], preferred_fiat)}\n"
        f"• **High**: {format_currency_value(max(prices), preferred_fiat)}\n"
        f"• **Low**: {format_currency_value(min(prices), preferred_fiat)}"
    )

    try:
        await update.message.reply_photo(photo=chart_url, caption=caption, parse_mode=ParseMode.MARKDOWN)
        await status_msg.delete()
    except Exception:
        await status_msg.edit_text(caption, parse_mode=ParseMode.MARKDOWN)
