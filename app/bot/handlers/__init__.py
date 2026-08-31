from telegram import BotCommand
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ConversationHandler,
    MessageHandler,
    filters,
)
from app.bot.handlers.start import start_command, help_command, experience_callback_handler, webapp_command
from app.bot.handlers.price import price_command, chart_command
from app.bot.handlers.alert import (
    alert_command_start,
    alert_coin_callback,
    alert_coin_text_input,
    alert_price_input,
    alert_condition_callback,
    alert_recurring_callback,
    alert_cancel,
    my_alerts_command,
    delete_alert_command,
    SET_COIN,
    SET_PRICE,
    SET_CONDITION,
    SET_RECURRING,
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
from app.bot.handlers.settings import settings_command, settings_fiat_callback
from app.bot.handlers.news import news_command
from app.bot.handlers.market import fear_greed_command, topmovers_command, market_command


async def register_bot_commands(app: Application) -> None:
    """Register command auto-complete suggestions menu with Telegram."""
    commands = [
        BotCommand("start", "Launch CoinSeer terminal & main menu"),
        BotCommand("help", "Command reference & user manual"),
        BotCommand("webapp", "Launch interactive Web3 Mini-App"),
        BotCommand("price", "Live crypto quote (e.g. /price BTC)"),
        BotCommand("chart", "Technical candlestick chart (e.g. /chart ETH)"),
        BotCommand("gas", "Decentralized multi-chain gas tracker"),
        BotCommand("ai_brief", "Gemini AI market sentiment briefing"),
        BotCommand("alert", "Set real-time price threshold alerts"),
        BotCommand("my_alerts", "View and audit active price triggers"),
        BotCommand("portfolio", "View multi-asset portfolio & net worth"),
        BotCommand("portfolio_add", "Log holding (e.g. /portfolio_add SOL 10 140)"),
        BotCommand("portfolio_remove", "Remove asset from portfolio vault"),
        BotCommand("watchlist", "Monitor custom crypto watchlist"),
        BotCommand("watchlist_add", "Add token to watchlist"),
        BotCommand("watchlist_remove", "Remove token from watchlist"),
        BotCommand("topmovers", "Top 24h market gainers & losers"),
        BotCommand("fng", "Fear & Greed crypto market index"),
        BotCommand("market", "Token fundamentals & circulating supply"),
        BotCommand("news", "Latest breaking crypto intelligence"),
        BotCommand("settings", "Configure currency preference (USD/EUR/etc)"),
    ]
    try:
        await app.bot.set_my_commands(commands)
    except Exception:
        pass


async def global_callback_router(update, context):
    """Route general menu buttons."""
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "price_btc":
        context.args = ["BTC"]
        await price_command(query, context)
    elif data == "ai_brief_trigger":
        await ai_brief_command(query, context)
    elif data == "gas_tracker":
        await gas_command(query, context)
    elif data == "portfolio_view":
        await portfolio_command(query, context)
    elif data == "watchlist_view":
        await watchlist_command(query, context)
    elif data == "news_crypto":
        await news_command(query, context)
    elif data == "fear_greed_view":
        await fear_greed_command(query, context)
    elif data == "alert_start":
        await alert_command_start(query, context)


def register_handlers(app: Application) -> None:
    """Register all modular handlers with the python-telegram-bot application."""

    # Alert Setup Conversation Handler
    alert_conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("alert", alert_command_start),
            CallbackQueryHandler(alert_command_start, pattern="^alert_start$"),
        ],
        states={
            SET_COIN: [
                CallbackQueryHandler(alert_coin_callback, pattern="^alert_coin_|^alert_cancel$"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, alert_coin_text_input),
            ],
            SET_PRICE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, alert_price_input),
            ],
            SET_CONDITION: [
                CallbackQueryHandler(alert_condition_callback, pattern="^alert_cond_|^alert_cancel$"),
            ],
            SET_RECURRING: [
                CallbackQueryHandler(alert_recurring_callback, pattern="^alert_recurring_"),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", alert_cancel),
            CallbackQueryHandler(alert_cancel, pattern="^alert_cancel$"),
        ],
        per_chat=True,
    )

    app.add_handler(alert_conv_handler)

    # Command Handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("webapp", webapp_command))
    app.add_handler(CommandHandler("price", price_command))
    app.add_handler(CommandHandler("chart", chart_command))
    app.add_handler(CommandHandler("watchlist", watchlist_command))
    app.add_handler(CommandHandler("watchlist_add", watchlist_add_command))
    app.add_handler(CommandHandler("watchlist_remove", watchlist_remove_command))
    app.add_handler(CommandHandler("portfolio", portfolio_command))
    app.add_handler(CommandHandler("portfolio_add", portfolio_add_command))
    app.add_handler(CommandHandler("portfolio_remove", portfolio_remove_command))
    app.add_handler(CommandHandler("pnl", portfolio_command))
    app.add_handler(CommandHandler("my_alerts", my_alerts_command))
    app.add_handler(CommandHandler("delete_alert", delete_alert_command))
    app.add_handler(CommandHandler("ai_brief", ai_brief_command))
    app.add_handler(CommandHandler("gas", gas_command))
    app.add_handler(CommandHandler("news", news_command))
    app.add_handler(CommandHandler("fear_greed", fear_greed_command))
    app.add_handler(CommandHandler("fng", fear_greed_command))
    app.add_handler(CommandHandler("topmovers", topmovers_command))
    app.add_handler(CommandHandler("market", market_command))
    app.add_handler(CommandHandler("settings", settings_command))

    # Callback Query Handlers
    app.add_handler(CallbackQueryHandler(experience_callback_handler, pattern="^exp_"))
    app.add_handler(CallbackQueryHandler(settings_fiat_callback, pattern="^set_fiat_"))
    app.add_handler(CallbackQueryHandler(global_callback_router))

