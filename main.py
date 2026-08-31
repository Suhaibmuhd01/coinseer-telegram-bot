import argparse
import asyncio
import uvicorn
from telegram import Update
from telegram.ext import Application
from app.core.config import settings
from app.core.logging import setup_logging, logger
from app.core.database import init_db, engine
from app.core.redis import get_redis_client, close_redis
from app.bot.handlers import register_handlers


def run_polling():
    """Run bot in local polling mode (convenient for local development without webhook tunnels)."""
    setup_logging()
    logger.info("starting_coinseer_in_polling_mode")

    if not settings.TELEGRAM_BOT_TOKEN:
        logger.critical("TELEGRAM_BOT_TOKEN is not set in environment or .env file.")
        return

    async def post_init(app: Application) -> None:
        # 1. Initialize Database
        try:
            await init_db()
        except Exception as e:
            logger.warning("database_unavailable_stateful_features_limited", error=str(e))

        # 2. Initialize Redis
        try:
            await get_redis_client()
        except Exception as e:
            logger.warning("redis_unavailable_caching_and_rate_limiting_fallback", error=str(e))

        # 3. Register Telegram Slash Command Suggestions
        from app.bot.handlers import register_bot_commands
        await register_bot_commands(app)
        logger.info("telegram_slash_commands_registered")

    async def post_shutdown(app: Application) -> None:
        logger.info("stopping_bot_polling")
        await close_redis()
        await engine.dispose()

    # Build & start Telegram Bot using standard PTB run_polling
    application = (
        Application.builder()
        .token(settings.TELEGRAM_BOT_TOKEN)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )
    register_handlers(application)

    logger.info("bot_polling_started_successfully")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


def main():
    parser = argparse.ArgumentParser(description="CoinSeer Enterprise Terminal Launcher")
    parser.add_argument(
        "--mode",
        choices=["webhook", "polling"],
        default="webhook",
        help="Run mode: 'webhook' for FastAPI server, 'polling' for standalone local polling",
    )
    args = parser.parse_args()

    if args.mode == "polling":
        run_polling()
    else:
        uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)


if __name__ == "__main__":
    main()