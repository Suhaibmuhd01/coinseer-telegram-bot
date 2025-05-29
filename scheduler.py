import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram import Bot
from telegram.constants import ParseMode
import database as db
import api_clients
from config import TELEGRAM_BOT_TOKEN, DEFAULT_FIAT

logger = logging.getLogger(__name__)
bot = Bot(token=TELEGRAM_BOT_TOKEN) # Initialize bot instance for sending messages

async def check_price_alerts():
    """Checks all active price alerts and notifies users if conditions are met."""
    logger.info("Scheduler: Running check_price_alerts job.")
    active_alerts = await db.get_active_alerts()
    if not active_alerts:
        # logger.info("Scheduler: No active alerts to check.")
        return

    # To avoid hitting API rate limits too quickly, batch coin checks
    coin_ids_to_check = list(set([alert['coin_id'] for alert in active_alerts]))
    if not coin_ids_to_check:
        return

    try:
        # For CoinGecko, you can batch multiple coin IDs and fiat currencies
        # price_data_batch = cg.get_price(ids=coin_ids_to_check, vs_currencies=DEFAULT_FIAT)
        # Simpler: one by one to manage logging and individual errors better for now
        for alert in active_alerts:
            coin_id = alert['coin_id']
            user_id = alert['user_id']
            target_price = alert['target_price']
            condition = alert['condition'] # 'above' or 'below'
            alert_id = alert['alert_id']
           # preferred_fiat = alert.get('preferred_fiat', DEFAULT_FIAT) # Get user's preferred fiat
           preferred_fiat = alert['preferred_fiat'] if 'preferred_fiat' in alert.keys() else DEFAULT_FIAT

             current_price_data = await api_clients.get_crypto_price(coin_id, preferred_fiat)

            if current_price_data and preferred_fiat in current_price_data:
                current_price = current_price_data[preferred_fiat]
                logger.debug(f"Alert Check: Coin: {coin_id}, Target: {target_price}, Current: {current_price}, Condition: {condition}")

                triggered = False
                if condition == 'above' and current_price > target_price:
                    triggered = True
                elif condition == 'below' and current_price < target_price:
                    triggered = True

                if triggered:
                    try:
                        message = (
                            f"🔔 **Price Alert Triggered!** 🔔\n\n"
                            f"Coin: **{coin_id.upper()}**\n"
                            f"Condition: Price {condition} ${target_price:,.2f} {preferred_fiat.upper()}\n"
                            f"Current Price: **${current_price:,.2f} {preferred_fiat.upper()}**"
                        )
                        await bot.send_message(chat_id=user_id, text=message, parse_mode=ParseMode.MARKDOWN)
                        await db.deactivate_alert(alert_id) # Deactivate alert after triggering
                        logger.info(f"Alert triggered and sent to user {user_id} for coin {coin_id}. Alert ID: {alert_id} deactivated.")
                    except Exception as e: # Catch errors from sending message or deactivating
                        logger.error(f"Error sending alert notification or deactivating for user {user_id}, alert {alert_id}: {e}")
            else:
                logger.warning(f"Could not fetch price for {coin_id} during alert check for user {user_id}.")
    except Exception as e:
        logger.error(f"Error during batch price check for alerts: {e}")


def setup_scheduler():
    scheduler = AsyncIOScheduler(timezone="UTC") # Or your preferred timezone
    # Check alerts every 1 minute. Adjust as needed based on API limits and desired responsiveness.
    # More frequent checks = more API calls.
    scheduler.add_job(check_price_alerts, 'interval', minutes=1, id="price_alert_checker")
    # You can add more jobs here (e.g., daily news summary)
    # scheduler.add_job(send_daily_news_summary, 'cron', hour=8, minute=0)
    logger.info("Scheduler setup complete. Jobs will run based on their schedule.")
    return scheduler