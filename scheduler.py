import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram import Bot
from telegram.constants import ParseMode
import database as db
import api_clients
from config import TELEGRAM_BOT_TOKEN, DEFAULT_FIAT
from utils import get_display_symbol

logger = logging.getLogger(__name__)
bot = Bot(token=TELEGRAM_BOT_TOKEN)

async def check_price_alerts():
    """Checks all active price alerts and notifies users if conditions are met."""
    logger.info("Scheduler: Running check_price_alerts job.")
    active_alerts = await db.get_active_alerts()
    if not active_alerts:
        return

    coin_ids_to_check = list(set([alert['coin_id'] for alert in active_alerts]))
    try:
        price_data = await api_clients.get_crypto_price(','.join(coin_ids_to_check), DEFAULT_FIAT)
        for alert in active_alerts:
            coin_id = alert['coin_id']
            user_id = alert['user_id']
            target_price = alert['target_price']
            condition = alert['condition']
            alert_id = alert['alert_id']
            is_recurring = alert['is_recurring']
            preferred_fiat = alert['preferred_fiat']

            if not price_data or coin_id not in price_data:
                logger.warning(f"Could not fetch price for {coin_id} during alert check for user {user_id}.")
                continue

            current_price = price_data[coin_id][preferred_fiat]
            logger.debug(f"Alert Check: Coin: {coin_id}, Target: {target_price}, Current: {current_price}, Condition: {condition}")

            triggered = False
            if condition == 'above' and current_price > target_price:
                triggered = True
            elif condition == 'below' and current_price < target_price:
                triggered = True

            if triggered:
                try:
                    display_symbol = get_display_symbol(coin_id)
                    message = (
                        f"🔔 **Price Alert Triggered!** 🔔\n\n"
                        f"Coin: **{display_symbol}**\n"
                        f"Condition: Price {condition} {preferred_fiat.upper()} {target_price:,.2f}\n"
                        f"Current Price: **{preferred_fiat.upper()} {current_price:,.2f}**"
                    )
                    await bot.send_message(chat_id=user_id, text=message, parse_mode=ParseMode.MARKDOWN)
                    if not is_recurring:
                        await db.deactivate_alert(alert_id)
                        logger.info(f"Alert triggered and sent to user {user_id} for coin {coin_id}. Alert ID: {alert_id} deactivated.")
                    else:
                        logger.info(f"Recurring alert triggered and sent to user {user_id} for coin {coin_id}. Alert ID: {alert_id} remains active.")
                except Exception as e:
                    logger.error(f"Error sending alert notification for user {user_id}, alert {alert_id}: {e}")
    except Exception as e:
        logger.error(f"Error during batch price check for alerts: {e}")

def setup_scheduler():
    scheduler = AsyncIOScheduler(timezone="UTC")
    scheduler.add_job(check_price_alerts, 'interval', minutes=1, id="price_alert_checker")
    logger.info("Scheduler setup complete. Jobs will run every minute.")
    return scheduler