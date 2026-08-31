from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes
from app.core.security import sanitize_input, escape_markdown
from app.services.api_client import api_client


async def news_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = "cryptocurrency"
    if context.args:
        query = sanitize_input(" ".join(context.args), 64)

    status_msg = await update.message.reply_text(f"[INTEL] _Curating institutional intelligence for `{escape_markdown(query)}`..._", parse_mode=ParseMode.MARKDOWN)

    articles = await api_client.get_crypto_news(query=query, page_size=5)

    if not articles:
        await status_msg.edit_text("[ERROR] No recent intelligence reports found for this query.")
        return

    text = f"[NEWS] **Top Intelligence ({escape_markdown(query.title())})**\n\n"
    for i, a in enumerate(articles, start=1):
        title = escape_markdown(a.get("title", ""))
        url = a.get("url", "#")
        source = escape_markdown(a.get("source", "CryptoMedia"))
        text += f"{i}. [{title}]({url}) — _{source}_\n\n"

    await status_msg.edit_text(text, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)
