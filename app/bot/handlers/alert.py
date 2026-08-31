from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ContextTypes, ConversationHandler
from sqlalchemy import select, delete
from app.core.database import async_session_factory
from app.core.security import sanitize_input, escape_markdown
from app.models.alert import PriceAlert
from app.models.user import User, UserProfile
from app.services.api_client import api_client, get_coingecko_id, get_display_symbol
from app.bot.keyboards import get_alert_condition_keyboard, get_alert_recurring_keyboard

SET_COIN, SET_PRICE, SET_CONDITION, SET_RECURRING = range(4)


async def alert_command_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [
            InlineKeyboardButton("[BTC] Bitcoin", callback_data="alert_coin_bitcoin"),
            InlineKeyboardButton("[ETH] Ethereum", callback_data="alert_coin_ethereum"),
            InlineKeyboardButton("[SOL] Solana", callback_data="alert_coin_solana"),
        ],
        [InlineKeyboardButton("[FIND] Custom Coin / Token", callback_data="alert_coin_custom")],
        [InlineKeyboardButton("[x] Cancel", callback_data="alert_cancel")],
    ]
    await update.message.reply_text(
        "[ALERT] **Configure Target Price Alert**\n\nSelect or search a cryptocurrency asset:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN,
    )
    return SET_COIN


async def alert_coin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "alert_cancel":
        await query.edit_message_text("[CANCEL] Alert configuration aborted.")
        context.user_data.clear()
        return ConversationHandler.END

    if query.data == "alert_coin_custom":
        await query.edit_message_text("[INPUT] Reply with the token symbol or identifier (e.g. `AVAX`, `LINK`, `Cardano`):")
        return SET_COIN

    coin_id = query.data.replace("alert_coin_", "")
    context.user_data["alert_coin_id"] = coin_id
    display_sym = get_display_symbol(coin_id)
    context.user_data["alert_symbol"] = display_sym

    prices = await api_client.get_crypto_price([coin_id], vs_currency="usd")
    current_price = prices.get(coin_id, {}).get("usd", 0.0)

    await query.edit_message_text(
        f"[TARGET] Asset: **{display_sym}** (Live: `${current_price:,.2f}`)\n\n"
        f"Enter your target trigger price in USD (e.g. `{current_price * 1.05:,.2f}`):",
        parse_mode=ParseMode.MARKDOWN,
    )
    return SET_PRICE


async def alert_coin_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    raw_input = sanitize_input(update.message.text, 32)
    coin_id = get_coingecko_id(raw_input)
    display_sym = get_display_symbol(coin_id)

    prices = await api_client.get_crypto_price([coin_id], vs_currency="usd")
    if coin_id not in prices or "usd" not in prices[coin_id]:
        safe_sym = escape_markdown(raw_input)
        await update.message.reply_text(
            f"[ERROR] Asset `{safe_sym}` unrecognized. Please enter a valid symbol:",
            parse_mode=ParseMode.MARKDOWN,
        )
        return SET_COIN

    current_price = prices[coin_id]["usd"]
    context.user_data["alert_coin_id"] = coin_id
    context.user_data["alert_symbol"] = display_sym

    await update.message.reply_text(
        f"[TARGET] Asset: **{display_sym}** (Live: `${current_price:,.2f}`)\n\n"
        f"Enter your target trigger price in USD:",
        parse_mode=ParseMode.MARKDOWN,
    )
    return SET_PRICE


async def alert_price_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = sanitize_input(update.message.text, 32).replace("$", "").replace(",", "")
    try:
        target_price = float(text)
        if target_price <= 0:
            raise ValueError()
        context.user_data["alert_target_price"] = target_price
    except ValueError:
        await update.message.reply_text("[ERROR] Please enter a valid positive numeric price:")
        return SET_PRICE

    await update.message.reply_text(
        f"[THRESHOLD] Target price set to **${target_price:,.4f}**.\n\nSelect trigger condition:",
        reply_markup=get_alert_condition_keyboard(),
        parse_mode=ParseMode.MARKDOWN,
    )
    return SET_CONDITION


async def alert_condition_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "alert_cancel":
        await query.edit_message_text("[CANCEL] Alert setup aborted.")
        context.user_data.clear()
        return ConversationHandler.END

    condition = "above" if "above" in query.data else "below"
    context.user_data["alert_condition"] = condition

    await query.edit_message_text(
        f"[CONDITION] Trigger when **price crosses {condition.upper()} target**.\n\nSelect frequency mode:",
        reply_markup=get_alert_recurring_keyboard(),
        parse_mode=ParseMode.MARKDOWN,
    )
    return SET_RECURRING


async def alert_recurring_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    is_recurring = "true" in query.data
    user_id = query.from_user.id

    coin_id = context.user_data.get("alert_coin_id", "bitcoin")
    symbol = context.user_data.get("alert_symbol", "BTC")
    target_price = context.user_data.get("alert_target_price", 0.0)
    condition = context.user_data.get("alert_condition", "above")

    async with async_session_factory() as session:
        alert = PriceAlert(
            user_id=user_id,
            coin_id=coin_id,
            symbol=symbol,
            target_price=target_price,
            condition=condition,
            fiat="usd",
            is_recurring=is_recurring,
            is_active=True,
        )
        session.add(alert)

        # Update stats
        res = await session.execute(select(UserProfile).where(UserProfile.user_id == user_id))
        profile = res.scalar_one_or_none()
        if profile:
            profile.total_alerts_created += 1

        await session.commit()

    mode_tag = "[RECURRING]" if is_recurring else "[ONE-TIME]"
    await query.edit_message_text(
        f"[OK] **Alert Trigger Successfully Deployed**\n\n"
        f"• **Asset**: {symbol}\n"
        f"• **Condition**: Price goes **{condition.upper()}** ${target_price:,.4f}\n"
        f"• **Mode**: {mode_tag}\n\n"
        f"System is actively monitoring. You will receive an instant push notification upon trigger.",
        parse_mode=ParseMode.MARKDOWN,
    )
    context.user_data.clear()
    return ConversationHandler.END


async def alert_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("[CANCEL] Alert setup cancelled.")
    context.user_data.clear()
    return ConversationHandler.END


async def my_alerts_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    async with async_session_factory() as session:
        result = await session.execute(
            select(PriceAlert).where(PriceAlert.user_id == user_id, PriceAlert.is_active == True)  # noqa: E712
        )
        alerts = result.scalars().all()

    if not alerts:
        await update.message.reply_text(
            "[STATUS] No active price alerts found. Use `/alert` to configure a trigger.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    msg = "[AUDIT] **Active Price Alert Triggers:**\n\n"
    for a in alerts:
        rec_tag = "[REC]" if a.is_recurring else "[1X]"
        msg += f"• `ID #{a.alert_id}`: **{a.symbol}** {a.condition.upper()} `${a.target_price:,.4f}` {rec_tag}\n"

    msg += "\n[INFO] _To decommission an alert, execute `/delete_alert <ID>`._"
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)


async def delete_alert_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not context.args:
        await update.message.reply_text("Usage: `/delete_alert <alert_id>` (e.g. `/delete_alert 3`)", parse_mode=ParseMode.MARKDOWN)
        return

    try:
        alert_id = int(sanitize_input(context.args[0], 16))
    except ValueError:
        await update.message.reply_text("[ERROR] Invalid alert ID. Numeric format required.")
        return

    async with async_session_factory() as session:
        result = await session.execute(
            delete(PriceAlert).where(PriceAlert.alert_id == alert_id, PriceAlert.user_id == user_id)
        )
        await session.commit()
        if result.rowcount > 0:
            await update.message.reply_text(f"[OK] Alert `#{alert_id}` decommissioned.", parse_mode=ParseMode.MARKDOWN)
        else:
            await update.message.reply_text(f"[ERROR] Alert `#{alert_id}` not found or already deleted.", parse_mode=ParseMode.MARKDOWN)
