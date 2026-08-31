from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes
from sqlalchemy import select, delete
from app.core.database import async_session_factory
from app.core.security import sanitize_input
from app.models.watchlist import Watchlist
from app.models.user import User
from app.services.api_client import api_client, get_coingecko_id, get_display_symbol


async def watchlist_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    async with async_session_factory() as session:
        res_user = await session.execute(select(User.preferred_fiat).where(User.user_id == user_id))
        fiat = res_user.scalar_one_or_none() or "usd"

        result = await session.execute(select(Watchlist).where(Watchlist.user_id == user_id))
        items = result.scalars().all()

    if not items:
        await update.message.reply_text(
            "[WATCHLIST] **Your Watchlist is empty.**\n\nAdd assets with `/watchlist_add <symbol>` (e.g. `/watchlist_add SOL`).",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    coin_ids = [w.coin_id for w in items]
    price_data = await api_client.get_crypto_price(coin_ids, vs_currency=fiat)

    msg = f"[WATCHLIST] **Monitored Assets ({fiat.upper()}):**\n\n"
    for item in items:
        c_data = price_data.get(item.coin_id, {})
        price = c_data.get(fiat)
        change_24h = c_data.get(f"{fiat}_24h_change", 0.0)

        if price is not None:
            glyph = "▲" if change_24h >= 0 else "▼"
            msg += f"• **{item.symbol}**: `${price:,.4f}` ({glyph} `{change_24h:+.2f}%`)\n"
        else:
            msg += f"• **{item.symbol}**: Querying price stream...\n"

    msg += "\n[INFO] _Use `/watchlist_add` or `/watchlist_remove` to manage._"
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)


async def watchlist_add_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not context.args:
        await update.message.reply_text("Usage: `/watchlist_add <symbol>` (e.g. `/watchlist_add ETH`)", parse_mode=ParseMode.MARKDOWN)
        return

    raw_symbol = sanitize_input(context.args[0], 32)
    coin_id = get_coingecko_id(raw_symbol)
    display_sym = get_display_symbol(coin_id)

    async with async_session_factory() as session:
        res = await session.execute(
            select(Watchlist).where(Watchlist.user_id == user_id, Watchlist.coin_id == coin_id)
        )
        existing = res.scalar_one_or_none()
        if existing:
            await update.message.reply_text(f"[INFO] **{display_sym}** is already present in your watchlist.", parse_mode=ParseMode.MARKDOWN)
            return

        item = Watchlist(user_id=user_id, coin_id=coin_id, symbol=display_sym)
        session.add(item)
        await session.commit()

    await update.message.reply_text(f"[OK] **{display_sym}** added to your watchlist. View via `/watchlist`.", parse_mode=ParseMode.MARKDOWN)


async def watchlist_remove_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not context.args:
        await update.message.reply_text("Usage: `/watchlist_remove <symbol>` (e.g. `/watchlist_remove ETH`)", parse_mode=ParseMode.MARKDOWN)
        return

    raw_symbol = sanitize_input(context.args[0], 32)
    coin_id = get_coingecko_id(raw_symbol)
    display_sym = get_display_symbol(coin_id)

    async with async_session_factory() as session:
        result = await session.execute(
            delete(Watchlist).where(Watchlist.user_id == user_id, Watchlist.coin_id == coin_id)
        )
        await session.commit()
        if result.rowcount > 0:
            await update.message.reply_text(f"[OK] **{display_sym}** removed from watchlist.", parse_mode=ParseMode.MARKDOWN)
        else:
            await update.message.reply_text(f"[ERROR] **{display_sym}** was not found in your watchlist.", parse_mode=ParseMode.MARKDOWN)
