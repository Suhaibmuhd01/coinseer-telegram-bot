import logging
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

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
# For more detailed APScheduler logs (optional)
# logging.getLogger('apscheduler').setLevel(logging.DEBUG)
logger = logging.getLogger(__name__)

def main() -> None:
    """Start the bot."""
    # Initialize database
    db.init_db()

    # Create the Application and pass it your bot's token.
    if not TELEGRAM_BOT_TOKEN:
        logger.critical("TELEGRAM_BOT_TOKEN not found in environment variables. Bot cannot start.")
        return

    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # --- Conversation Handler for Price Alerts ---
    alert_conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("alert", bot_handlers.alert_command_start),
            CallbackQueryHandler(bot_handlers.alert_command_start, pattern="^alert_start$") # From inline button
        ],
        states={
            bot_handlers.COIN_FOR_ALERT: [MessageHandler(filters.TEXT & ~filters.COMMAND, bot_handlers.alert_coin_received)],
            bot_handlers.PRICE_FOR_ALERT: [MessageHandler(filters.TEXT & ~filters.COMMAND, bot_handlers.alert_price_received)],
            bot_handlers.CONDITION_FOR_ALERT: [CallbackQueryHandler(bot_handlers.alert_condition_received, pattern="^alert_cond_(above|below)$")],
        },
        fallbacks=[CommandHandler("cancel", bot_handlers.alert_cancel)],
    )

    # --- Register handlers ---
    application.add_handler(CommandHandler("start", bot_handlers.start_command))
    application.add_handler(CommandHandler("help", bot_handlers.help_command))
    application.add_handler(CommandHandler("price", bot_handlers.price_command))
    application.add_handler(CommandHandler("news", bot_handlers.news_command))
    application.add_handler(CommandHandler("fear_greed", bot_handlers.fear_greed_command))

    application.add_handler(CommandHandler("watchlist_add", bot_handlers.watchlist_add_command))
    application.add_handler(CommandHandler("watchlist_remove", bot_handlers.watchlist_remove_command))
    application.add_handler(CommandHandler("watchlist", bot_handlers.watchlist_command))

    application.add_handler(alert_conv_handler) # Add the conversation handler
    application.add_handler(CommandHandler("my_alerts", bot_handlers.my_alerts_command))

    # Handler for inline button presses not part of a conversation
    application.add_handler(CallbackQueryHandler(bot_handlers.button_callback_handler))

    # Start the scheduler
    scheduler = setup_scheduler()
    
    # edited section
    # 
    #
    
    """   scheduler.start()
    logger.info("APScheduler started.")

    # Run the bot until the user presses Ctrl-C
    logger.info("Bot is starting...")
    application.run_polling()

    # Cleanly shut down the scheduler when the application is stopped
    scheduler.shutdown()
    logger.info("APScheduler shut down.") """

if __name__ == "__main__":
    main()