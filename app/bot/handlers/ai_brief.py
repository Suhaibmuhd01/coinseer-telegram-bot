from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes
from app.services.api_client import api_client, GeminiAIEngine


async def ai_brief_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text("[AI] _Synthesizing on-chain telemetry and market data with Gemini 1.5 Flash..._", parse_mode=ParseMode.MARKDOWN)

    # 1. Fetch live BTC price
    btc_data = await api_client.get_crypto_price(["bitcoin"], vs_currency="usd")
    btc_price = btc_data.get("bitcoin", {}).get("usd", 68000.0)

    # 2. Fetch Fear & Greed Index
    fng = await api_client.get_fear_greed_index()
    fng_val = fng.get("value_classification", "Neutral") if fng else "Neutral"
    fng_num = fng.get("value", "50") if fng else "50"

    # 3. Fetch Top Headlines
    news = await api_client.get_crypto_news(query="cryptocurrency", page_size=5)
    headlines = [a.get("title", "") for a in news if a.get("title")]

    # 4. Generate AI briefing
    briefing = await GeminiAIEngine.generate_market_briefing(
        news_headlines=headlines,
        btc_price=btc_price,
        fng_value=f"{fng_val} ({fng_num}/100)",
    )

    await msg.edit_text(briefing, parse_mode=ParseMode.MARKDOWN)
