import asyncio
from typing import Dict, Any, List
from sqlalchemy import select
from telegram import Bot
from telegram.constants import ParseMode
from app.core.config import settings
from app.core.database import async_session_factory
from app.core.logging import logger
from app.models.alert import PriceAlert, VolumeAlert
from app.services.api_client import api_client, get_display_symbol

previous_volumes: Dict[str, float] = {}


async def evaluate_price_alerts_task(ctx: Dict[Any, Any] = None):
    """Asynchronously evaluate price alerts against real-time cached price pools."""
    if not settings.TELEGRAM_BOT_TOKEN:
        logger.warning("scheduler_skipped_no_telegram_token")
        return

    bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)

    async with async_session_factory() as session:
        result = await session.execute(
            select(PriceAlert).where(PriceAlert.is_active == True)  # noqa: E712
        )
        alerts: List[PriceAlert] = list(result.scalars().all())

        if not alerts:
            return

        unique_coins = list(set(a.coin_id for a in alerts))
        price_data = await api_client.get_crypto_price(unique_coins, vs_currency="usd")

        for alert in alerts:
            coin_id = alert.coin_id
            if coin_id not in price_data:
                continue

            current_price = price_data[coin_id].get("usd")
            if current_price is None:
                continue

            triggered = False
            if alert.condition == "above" and current_price >= alert.target_price:
                triggered = True
            elif alert.condition == "below" and current_price <= alert.target_price:
                triggered = True

            if triggered:
                display_sym = get_display_symbol(coin_id)
                recurring_note = "[RECURRING] Monitoring continues." if alert.is_recurring else "[COMPLETED] Trigger deactivated."
                msg = (
                    f"[ALERT] **PRICE THRESHOLD TRIGGERED**\n\n"
                    f"• **Asset**: {display_sym} ({coin_id.upper()})\n"
                    f"• **Condition**: Price went **{alert.condition.upper()}** ${alert.target_price:,.4f}\n"
                    f"• **Trigger Price**: **${current_price:,.4f} USD**\n\n"
                    f"• **Status**: {recurring_note}"
                )
                try:
                    await bot.send_message(
                        chat_id=alert.user_id,
                        text=msg,
                        parse_mode=ParseMode.MARKDOWN,
                    )
                    if not alert.is_recurring:
                        alert.is_active = False
                    await session.commit()
                    logger.info("price_alert_sent", user_id=alert.user_id, coin=coin_id)
                except Exception as send_err:
                    logger.error("alert_send_failed", user_id=alert.user_id, error=str(send_err))


async def evaluate_volume_alerts_task(ctx: Dict[Any, Any] = None):
    """Check for volume spikes."""
    global previous_volumes
    if not settings.TELEGRAM_BOT_TOKEN:
        return

    bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)

    async with async_session_factory() as session:
        result = await session.execute(
            select(VolumeAlert).where(VolumeAlert.is_active == True)  # noqa: E712
        )
        volume_alerts: List[VolumeAlert] = list(result.scalars().all())
        if not volume_alerts:
            return

        unique_coins = list(set(v.coin_id for v in volume_alerts))
        price_data = await api_client.get_crypto_price(unique_coins, vs_currency="usd")

        for alert in volume_alerts:
            coin_id = alert.coin_id
            if coin_id not in price_data:
                continue

            current_vol = price_data[coin_id].get("usd_24h_vol", 0.0)
            prev_vol = previous_volumes.get(coin_id, 0.0)

            if prev_vol > 0 and current_vol > 0:
                multiplier = current_vol / prev_vol
                if multiplier >= alert.threshold_multiplier:
                    display_sym = get_display_symbol(coin_id)
                    msg = (
                        f"[SURGE] **VOLUME SPIKE DETECTED**\n\n"
                        f"• **Asset**: {display_sym}\n"
                        f"• **Surge Rate**: **{multiplier:.1f}x** increase!\n"
                        f"• **Current 24h Volume**: ${current_vol:,.0f} USD\n"
                    )
                    try:
                        await bot.send_message(
                            chat_id=alert.user_id,
                            text=msg,
                            parse_mode=ParseMode.MARKDOWN,
                        )
                        logger.info("volume_alert_sent", user_id=alert.user_id, coin=coin_id)
                    except Exception as e:
                        logger.error("volume_alert_send_failed", error=str(e))

            previous_volumes[coin_id] = current_vol


async def warm_cache_task(ctx: Dict[Any, Any] = None):
    """Pre-warm Redis cache with top 20 crypto assets."""
    top_coins = ["bitcoin", "ethereum", "solana", "binancecoin", "ripple", "cardano", "dogecoin", "avalanche-2", "polkadot", "chainlink"]
    await api_client.get_crypto_price(top_coins, vs_currency="usd")
    await api_client.get_fear_greed_index()
    logger.debug("cache_warmed_successfully")


class WorkerSettings:
    """ARQ Worker configuration."""
    functions = [evaluate_price_alerts_task, evaluate_volume_alerts_task, warm_cache_task]
    cron_jobs = [
        {"coroutine": evaluate_price_alerts_task, "minute": None},
        {"coroutine": evaluate_volume_alerts_task, "minute": {0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55}},
        {"coroutine": warm_cache_task, "minute": {0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24, 26, 28, 30, 32, 34, 36, 38, 40, 42, 44, 46, 48, 50, 52, 54, 56, 58}},
    ]
    redis_settings = settings.REDIS_URL
