import logging
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    CallbackQueryHandler,
    ConversationHandler,
)
import bot_handlers
import database as db
from config import TELEGRAM_BOT_TOKEN
from scheduler import setup_scheduler
import asyncio

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    handlers=[
        logging.FileHandler('coinseer_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def main() -> None:
    """Start the bot."""
    # Initialize database
    db.init_db()

    # Validate bot token
    if not TELEGRAM_BOT_TOKEN:
        logger.critical("TELEGRAM_BOT_TOKEN not found in environment variables. Bot cannot start.")
        return

    # Create the Application
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Conversation Handler for Price Alerts
    alert_conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("alert", bot_handlers.alert_command_start),
            CallbackQueryHandler(bot_handlers.alert_coin_received, pattern="^alert_coin_")
        ],
        states={
            bot_handlers.COIN_FOR_ALERT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, bot_handlers.alert_coin_received),
                CallbackQueryHandler(bot_handlers.alert_coin_received, pattern="^alert_coin_")
            ],
            bot_handlers.PRICE_FOR_ALERT: [MessageHandler(filters.TEXT & ~filters.COMMAND, bot_handlers.alert_price_received)],
            bot_handlers.CONDITION_FOR_ALERT: [CallbackQueryHandler(bot_handlers.alert_condition_received, pattern="^alert_cond_")],
            bot_handlers.RECURRING_FOR_ALERT: [CallbackQueryHandler(bot_handlers.alert_recurring_received, pattern="^alert_recurring_")]
        },
        fallbacks=[CommandHandler("cancel", bot_handlers.alert_cancel)],
    )

    # Settings conversation handler
    settings_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("settings", bot_handlers.settings_command)],
        states={
            bot_handlers.FIAT_FOR_SETTINGS: [CallbackQueryHandler(bot_handlers.settings_fiat_received, pattern="^set_fiat_")]
        },
        fallbacks=[CommandHandler("cancel", bot_handlers.alert_cancel)]
    )

    # Register handlers
    application.add_handler(CommandHandler("start", bot_handlers.start_command))
    application.add_handler(CommandHandler("help", bot_handlers.help_command))
    application.add_handler(MessageHandler(filters.Regex(r'^/$'), bot_handlers.start_command))
    application.add_handler(CommandHandler("price", bot_handlers.price_command))
    application.add_handler(CommandHandler("chart", bot_handlers.chart_command))
    application.add_handler(CommandHandler("news", bot_handlers.news_command))
    application.add_handler(CommandHandler("fear_greed", bot_handlers.fear_greed_command))
    application.add_handler(CommandHandler("watchlist_add", bot_handlers.watchlist_add_command))
    application.add_handler(CommandHandler("watchlist_remove", bot_handlers.watchlist_remove_command))
    application.add_handler(CommandHandler("watchlist", bot_handlers.watchlist_command))
    application.add_handler(CommandHandler("portfolio_add", bot_handlers.portfolio_add_command))
    application.add_handler(CommandHandler("portfolio_remove", bot_handlers.portfolio_remove_command))
    application.add_handler(CommandHandler("portfolio", bot_handlers.portfolio_command))
    application.add_handler(CommandHandler("market", bot_handlers.market_command))
    application.add_handler(CommandHandler("topmovers", bot_handlers.topmovers_command))
    application.add_handler(CommandHandler("predict", bot_handlers.predict_command))
    application.add_handler(CommandHandler("my_alerts", bot_handlers.my_alerts_command))
    application.add_handler(CommandHandler("delete_alert", bot_handlers.delete_alert_command))
    application.add_handler(CommandHandler("volume_alert", bot_handlers.volume_alert_command))
    application.add_handler(CommandHandler("pnl", bot_handlers.pnl_command))
    application.add_handler(CommandHandler("learn", bot_handlers.learn_command))
    application.add_handler(CommandHandler("profile", bot_handlers.profile_command))
    application.add_handler(CommandHandler("feedback", bot_handlers.feedback_command))
    application.add_handler(alert_conv_handler)
    application.add_handler(settings_conv_handler)
    application.add_handler(CallbackQueryHandler(bot_handlers.button_callback_handler))

    # Start the scheduler
    scheduler = setup_scheduler()
    scheduler.start()
    logger.info("APScheduler started.")

    # Run the bot
    logger.info("Bot is starting...")
    try:
        application.run_polling(allowed_updates=Update.ALL_TYPES)
    except Exception as e:
        logger.critical(f"Bot crashed: {e}")
        raise

    # Cleanly shut down the scheduler
    scheduler.shutdown()
    logger.info("APScheduler shut down.")

if __name__ == "__main__":
    main()