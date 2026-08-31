from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes
from sqlalchemy import select
from app.core.database import async_session_factory
from app.core.logging import logger
from app.core.security import escape_markdown, sanitize_input
from app.models.user import User, UserProfile
from app.bot.keyboards import get_main_menu_keyboard, get_experience_level_keyboard


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_info = update.effective_user
    if not user_info:
        return

    first_name_safe = escape_markdown(sanitize_input(user_info.first_name or "Trader", 32))

    is_new = False
    try:
        async with async_session_factory() as session:
            result = await session.execute(select(User).where(User.user_id == user_info.id))
            user_record = result.scalar_one_or_none()

            if not user_record:
                is_new = True
                user_record = User(
                    user_id=user_info.id,
                    username=sanitize_input(user_info.username, 64) if user_info.username else None,
                    first_name=sanitize_input(user_info.first_name, 128) if user_info.first_name else None,
                    preferred_fiat="usd",
                )
                profile = UserProfile(user_id=user_info.id, experience_level="beginner")
                session.add(user_record)
                session.add(profile)
                await session.commit()
                logger.info("new_user_registered", user_id=user_info.id)
    except Exception as e:
        logger.warning("database_user_sync_failed_continuing", error=str(e))
        is_new = False

    if is_new:
        welcome_text = (
            f"[SYSTEM] **Welcome to CoinSeer Enterprise, {first_name_safe}**\n\n"
            "Institutional Web3 crypto intelligence terminal and automated risk monitoring ecosystem.\n\n"
            "**Core Capabilities:**\n"
            "• [FEED] **Real-time Cross-Chain Prices & High-Res Technical Charts**\n"
            "• [AI] **Gemini-Powered Market Sentiment Briefings** (`/ai_brief`)\n"
            "• [GAS] **Multi-Chain Gas & Fee Optimization Matrix** (`/gas`)\n"
            "• [ALERT] **Low-Latency Distributed Price Alerts** (`/alert`)\n"
            "• [VAULT] **Multi-Asset Portfolio & PnL Analytics** (`/portfolio`)\n"
            "• [ORDER] **Real-Time Whale & Derivatives Liquidation Feeds**\n\n"
            "Select your crypto operational experience level below to initialize:"
        )
        await update.message.reply_text(
            welcome_text,
            reply_markup=get_experience_level_keyboard(),
            parse_mode=ParseMode.MARKDOWN,
        )
    else:
        welcome_text = (
            f"[ONLINE] **CoinSeer Intelligence Terminal — Welcome, {first_name_safe}**\n\n"
            "System operational. Select an intelligence module below or launch the Web3 Mini-App:"
        )
        await update.message.reply_text(
            welcome_text,
            reply_markup=get_main_menu_keyboard(),
            parse_mode=ParseMode.MARKDOWN,
        )


async def experience_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data
    user_id = query.from_user.id

    if data == "exp_skip":
        await query.edit_message_text(
            "[CONFIG] Setup complete. Preferences can be updated anytime in `/settings`.",
            reply_markup=get_main_menu_keyboard(),
        )
        return

    level_map = {
        "exp_beginner": "beginner",
        "exp_intermediate": "intermediate",
        "exp_advanced": "advanced",
    }
    selected_level = level_map.get(data, "beginner")

    try:
        async with async_session_factory() as session:
            result = await session.execute(select(UserProfile).where(UserProfile.user_id == user_id))
            profile = result.scalar_one_or_none()
            if profile:
                profile.experience_level = selected_level
                await session.commit()
    except Exception as e:
        logger.warning("experience_level_update_failed", error=str(e))

    level_display = selected_level.capitalize()
    await query.edit_message_text(
        f"[PROFILE] Profile calibrated to **{level_display}**.\n\n"
        "Terminal ready. Choose a tool below or launch the Mini-App:",
        reply_markup=get_main_menu_keyboard(),
        parse_mode=ParseMode.MARKDOWN,
    )


async def webapp_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Launch the Telegram WebApp Mini-App."""
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
    from app.core.config import settings

    webapp_url = (
        settings.TELEGRAM_WEBAPP_URL
        or (
            f"{settings.TELEGRAM_WEBHOOK_URL.replace('/webhook', '')}/webapp"
            if settings.TELEGRAM_WEBHOOK_URL
            else "https://suhaibmuhd01.github.io/coinseer-telegram-bot/"
        )
    )

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "Launch Web3 Mini-App",
                web_app=WebAppInfo(url=webapp_url)
            )
        ]
    ])

    await update.message.reply_text(
        "**CoinSeer Web3 Technical Mini-App**\n\n"
        "Tap the button below to launch the live TradingView technical charts, gas monitor, and asset dashboard:",
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN,
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "[MANUAL] **CoinSeer Terminal Command Reference**\n\n"
        "**Market Intelligence:**\n"
        "• `/price <coin>` — Live quote, 24h change, market cap\n"
        "• `/chart <coin> [days]` — 7 to 30 day rendered technical chart\n"
        "• `/market <coin>` — Token fundamentals, circulating supply, FDV\n"
        "• `/topmovers` — Top 24h gainers and momentum leaders\n"
        "• `/fear_greed` / `/fng` — Crypto sentiment index and regime\n"
        "• `/news [query]` — Institutional news & intelligence feed\n\n"
        "**Next-Gen Web3 & AI:**\n"
        "• `/ai_brief` — Gemini LLM 3-bullet crypto briefing\n"
        "• `/gas` — Cross-chain gas fees (ETH, Base, Arbitrum, BSC, SOL)\n\n"
        "**Portfolio & Vaults:**\n"
        "• `/portfolio` — Net worth, PnL, allocation pie chart\n"
        "• `/portfolio_add <coin> <amount> [buy_price]` — Add asset\n"
        "• `/portfolio_remove <coin>` — Remove asset from vault\n"
        "• `/watchlist` — Multi-asset monitoring status\n"
        "• `/watchlist_add <coin>` — Add token to watchlist\n"
        "• `/watchlist_remove <coin>` — Remove token from watchlist\n\n"
        "**Distributed Alerts:**\n"
        "• `/alert` — Configure target price threshold alert\n"
        "• `/my_alerts` — List and audit active triggers\n"
        "• `/delete_alert <id>` — Decommission an alert trigger\n\n"
        "**System:**\n"
        "• `/settings` — Configure base currency (USD, EUR, GBP, etc.)\n"
        "• `/webapp` — Launch interactive native Telegram Mini-App\n"
    )
    await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)
