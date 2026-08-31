from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes
from sqlalchemy import select
from app.core.config import settings
from app.core.database import async_session_factory
from app.models.user import User
from app.bot.keyboards import get_fiat_selection_keyboard


async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    current_fiat = "usd"

    async with async_session_factory() as session:
        res = await session.execute(select(User.preferred_fiat).where(User.user_id == user_id))
        fiat = res.scalar_one_or_none()
        if fiat:
            current_fiat = fiat

    await update.message.reply_text(
        f"[SETTINGS] **CoinSeer Preferences**\n\n"
        f"• **Base Valuation Currency**: `[{current_fiat.upper()}]`\n\n"
        f"Select your preferred benchmark currency below:",
        reply_markup=get_fiat_selection_keyboard(settings.SUPPORTED_FIAT),
        parse_mode=ParseMode.MARKDOWN,
    )


async def settings_fiat_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    fiat = query.data.replace("set_fiat_", "").lower()
    user_id = query.from_user.id

    async with async_session_factory() as session:
        res = await session.execute(select(User).where(User.user_id == user_id))
        user = res.scalar_one_or_none()
        if user:
            user.preferred_fiat = fiat
            await session.commit()

    await query.edit_message_text(
        f"[OK] Base valuation currency updated to **[{fiat.upper()}]**.\n"
        "All quotes, portfolio analytics, and alerts will now calculate in this benchmark.",
        parse_mode=ParseMode.MARKDOWN,
    )
