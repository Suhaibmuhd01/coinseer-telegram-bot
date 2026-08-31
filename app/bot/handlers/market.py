from datetime import datetime
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes
from app.core.security import sanitize_input, escape_markdown
from app.services.api_client import api_client, get_coingecko_id, get_display_symbol


async def fear_greed_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    fng = await api_client.get_fear_greed_index()
    if not fng:
        await update.message.reply_text("[ERROR] Fear & Greed Index data temporarily unavailable.")
        return

    val = fng.get("value", "50")
    sentiment = fng.get("value_classification", "Neutral")
    ts = fng.get("timestamp")
    date_str = datetime.fromtimestamp(int(ts)).strftime("%Y-%m-%d") if ts else "Today"

    tag = "[EXTREME GREED]" if int(val) >= 75 else ("[GREED]" if int(val) >= 55 else ("[NEUTRAL]" if int(val) >= 45 else ("[FEAR]" if int(val) >= 25 else "[EXTREME FEAR]")))

    msg = (
        f"[INDEX] **Crypto Market Sentiment & Fear/Greed Index**\n\n"
        f"• **Score**: **{val} / 100**\n"
        f"• **Regime**: **{sentiment}** {tag}\n"
        f"• **Timestamp**: `{date_str}`\n\n"
        f"[INFO] _Historical context: Extreme fear indicates oversold conditions; extreme greed warns of overheated leverage._"
    )
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)


async def topmovers_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    status_msg = await update.message.reply_text("[RANK] _Querying top 24h momentum leaders..._")
    movers = await api_client.get_top_movers(vs_currency="usd", limit=5)

    if not movers:
        await status_msg.edit_text("[ERROR] Momentum rankings temporarily unavailable.")
        return

    text = "[RANK] **Top 24h Market Gainers (Momentum)**\n\n"
    for m in movers:
        sym = escape_markdown(m.get("symbol", "").upper())
        price = m.get("current_price", 0.0)
        chg = m.get("price_change_percentage_24h", 0.0)
        text += f"• **{sym}**: `${price:,.4f}` (▲ `+{chg:.2f}%`)\n"

    await status_msg.edit_text(text, parse_mode=ParseMode.MARKDOWN)


async def market_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: `/market <symbol>` (e.g. `/market SOL`)", parse_mode=ParseMode.MARKDOWN)
        return

    raw_coin = sanitize_input(context.args[0], 32)
    coin_id = get_coingecko_id(raw_coin)
    display_sym = get_display_symbol(coin_id)

    status_msg = await update.message.reply_text(f"[INTEL] _Loading market fundamentals for {display_sym}..._")
    details = await api_client.get_coin_details(coin_id)

    if not details or "market_data" not in details:
        await status_msg.edit_text(f"[ERROR] Market data unavailable for `{escape_markdown(raw_coin)}`.")
        return

    mdata = details["market_data"]
    price = mdata.get("current_price", {}).get("usd", 0.0)
    mcap = mdata.get("market_cap", {}).get("usd", 0.0)
    vol = mdata.get("total_volume", {}).get("usd", 0.0)
    circ_supply = mdata.get("circulating_supply", 0.0)
    total_supply = mdata.get("total_supply", 0.0)
    ath = mdata.get("ath", {}).get("usd", 0.0)
    ath_change = mdata.get("ath_change_percentage", {}).get("usd", 0.0)

    name_safe = escape_markdown(details.get("name", display_sym))

    text = (
        f"[MARKET] **{name_safe} ({display_sym}) Fundamentals**\n\n"
        f"• **Current Price**: **${price:,.4f} USD**\n"
        f"• **Market Cap**: ${mcap:,.0f}\n"
        f"• **24h Volume**: ${vol:,.0f}\n"
        f"• **Circulating Supply**: {circ_supply:,.0f} {display_sym}\n"
        f"• **Total / Max Supply**: {total_supply:,.0f} {display_sym}\n"
        f"• **All-Time High (ATH)**: ${ath:,.2f} (`{ath_change:+.1f}%` from ATH)\n"
    )
    await status_msg.edit_text(text, parse_mode=ParseMode.MARKDOWN)
