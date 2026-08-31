import asyncio
import os
from contextlib import asynccontextmanager
from typing import Optional
from fastapi import FastAPI, Request, Header, HTTPException, status, Query, Response
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from telegram import Update
from telegram.ext import Application
import sentry_sdk

from app.core.config import settings
from app.core.logging import setup_logging, logger
from app.core.security import (
    secure_compare,
    SecurityHeadersMiddleware,
    RateLimitMiddleware,
)
from app.core.database import init_db, engine
from app.core.redis import get_redis_client, close_redis, RedisCache
from app.bot.handlers import register_handlers
from app.services.api_client import api_client, GasTrackerClient
from app.services.whale_listener import start_liquidation_and_whale_stream, WHALE_ALERT_CHANNEL
from app.core.database import async_session_factory
from sqlalchemy import select
from app.models.user import User

# Sentry APM integration
if settings.SENTRY_DSN:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.ENVIRONMENT,
        traces_sample_rate=1.0,
    )

# Prometheus Metrics
WEBHOOK_REQUESTS_TOTAL = Counter("telegram_webhook_requests_total", "Total Telegram webhook updates received", ["status"])
API_REQUEST_DURATION = Histogram("http_request_duration_seconds", "HTTP request latency in seconds", ["endpoint"])

# Global Telegram Application instance
telegram_app: Optional[Application] = None
background_tasks = set()


async def whale_alert_broadcaster(tg_app: Application):
    """Subscribes to Redis PubSub and broadcasts high-priority whale alerts to users."""
    client = await get_redis_client()
    pubsub = client.pubsub()
    await pubsub.subscribe(WHALE_ALERT_CHANNEL)
    logger.info("whale_broadcaster_subscribed_to_redis")

    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                try:
                    import json
                    payload = json.loads(message["data"])
                    alert_text = payload.get("description")
                    if alert_text:
                        async with async_session_factory() as session:
                            res = await session.execute(
                                select(User.user_id).where(User.whale_alerts_enabled == True)  # noqa: E712
                            )
                            user_ids = res.scalars().all()

                        for uid in user_ids:
                            try:
                                await tg_app.bot.send_message(
                                    chat_id=uid,
                                    text=alert_text,
                                    parse_mode="Markdown",
                                )
                            except Exception:
                                pass
                except Exception as broadcast_err:
                    logger.debug("whale_broadcast_error", error=str(broadcast_err))
    except asyncio.CancelledError:
        await pubsub.unsubscribe(WHALE_ALERT_CHANNEL)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Startup ---
    setup_logging()
    logger.info("starting_coinseer_enterprise", env=settings.ENVIRONMENT)

    # 1. Initialize Database
    await init_db()

    # 2. Initialize Redis
    await get_redis_client()

    # 3. Initialize Telegram Bot Application
    global telegram_app
    if settings.TELEGRAM_BOT_TOKEN:
        telegram_app = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()
        register_handlers(telegram_app)
        await telegram_app.initialize()
        await telegram_app.start()

        from app.bot.handlers import register_bot_commands
        await register_bot_commands(telegram_app)

        # Configure Webhook if URL is set
        if settings.TELEGRAM_WEBHOOK_URL:
            webhook_url = settings.TELEGRAM_WEBHOOK_URL
            secret_token = settings.TELEGRAM_WEBHOOK_SECRET
            await telegram_app.bot.set_webhook(
                url=webhook_url,
                secret_token=secret_token,
                allowed_updates=Update.ALL_TYPES,
                drop_pending_updates=True,
            )
            logger.info("telegram_webhook_set", url=webhook_url)

        # Start WebSocket Whale and Liquidation Listener in background
        task_whale_stream = asyncio.create_task(start_liquidation_and_whale_stream())
        task_broadcaster = asyncio.create_task(whale_alert_broadcaster(telegram_app))
        background_tasks.add(task_whale_stream)
        background_tasks.add(task_broadcaster)
    else:
        logger.warning("no_telegram_token_provided_bot_handlers_offline")

    yield

    # --- Shutdown ---
    logger.info("shutting_down_coinseer_services")
    for t in background_tasks:
        t.cancel()

    if telegram_app:
        await telegram_app.stop()
        await telegram_app.shutdown()

    await close_redis()
    await engine.dispose()
    logger.info("services_shutdown_complete")


app = FastAPI(
    title="CoinSeer Enterprise Platform API",
    description="Asynchronous high-throughput Web3 crypto intelligence and Telegram bot ecosystem.",
    version="2.0.0",
    lifespan=lifespan,
)

# Attach Security Middlewares
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RateLimitMiddleware)

templates = Jinja2Templates(directory="app/templates")


# ==========================================
# Routes & Endpoints
# ==========================================

@app.post("/webhook")
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: Optional[str] = Header(None),
):
    """Secure Telegram Webhook endpoint with constant-time cryptographic token verification."""
    if not telegram_app:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Bot is not initialized")

    # Cryptographic secret verification (Constant time comparison)
    if settings.TELEGRAM_WEBHOOK_SECRET:
        if not secure_compare(x_telegram_bot_api_secret_token, settings.TELEGRAM_WEBHOOK_SECRET):
            WEBHOOK_REQUESTS_TOTAL.labels(status="unauthorized").inc()
            logger.warning("unauthorized_webhook_request")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid secret token")

    try:
        payload = await request.json()
        update = Update.de_json(payload, telegram_app.bot)
        await telegram_app.process_update(update)
        WEBHOOK_REQUESTS_TOTAL.labels(status="success").inc()
        return {"status": "ok"}
    except Exception as e:
        WEBHOOK_REQUESTS_TOTAL.labels(status="error").inc()
        logger.error("webhook_processing_failed", error=str(e))
        return {"status": "error", "message": str(e)}


@app.get("/health")
async def health_check():
    """Health check endpoint probing database and Redis pools."""
    db_status = "healthy"
    redis_status = "healthy"

    # Test Database
    try:
        async with engine.connect() as conn:
            from sqlalchemy import text
            await conn.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    # Test Redis
    try:
        client = await get_redis_client()
        await client.ping()
    except Exception as e:
        redis_status = f"unhealthy: {str(e)}"

    is_ok = db_status == "healthy" and redis_status == "healthy"
    status_code = status.HTTP_200_OK if is_ok else status.HTTP_503_SERVICE_UNAVAILABLE

    return JSONResponse(
        status_code=status_code,
        content={
            "status": "healthy" if is_ok else "degraded",
            "database": db_status,
            "redis": redis_status,
            "version": "2.0.0",
        },
    )


@app.get("/metrics")
async def prometheus_metrics():
    """Prometheus telemetry scrape endpoint."""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/webapp", response_class=HTMLResponse)
async def serve_mini_app(request: Request):
    """Serve native Telegram WebApp Mini-App frontend."""
    return templates.TemplateResponse("webapp.html", {"request": request})


@app.get("/api/v1/market/prices")
async def get_market_prices(coins: str = Query("bitcoin,ethereum,solana,binancecoin")):
    """REST API endpoint for live market prices used by Mini-App."""
    coin_list = [c.strip() for c in coins.split(",") if c.strip()]
    data = await api_client.get_crypto_price(coin_list, vs_currency="usd")
    return data


@app.get("/api/v1/gas")
async def get_gas_metrics():
    """REST API endpoint for cross-chain gas metrics."""
    return await GasTrackerClient.get_multichain_gas()
