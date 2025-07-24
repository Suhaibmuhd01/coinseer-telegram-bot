import logging
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram import Bot
from telegram.constants import ParseMode
import database as db
import api_clients
from config import TELEGRAM_BOT_TOKEN, DEFAULT_FIAT, VOLUME_SPIKE_THRESHOLD
from utils import get_display_symbol, format_currency, format_percentage

logger = logging.getLogger(__name__)

# Initialize bot only if token exists
bot = None
if TELEGRAM_BOT_TOKEN:
    bot = Bot(token=TELEGRAM_BOT_TOKEN)

# Store previous volume data for comparison
previous_volumes = {}

async def check_price_alerts():
    """Checks all active price alerts and notifies users if conditions are met."""
    if not bot:
        logger.error("Bot not initialized - cannot check price alerts")
        return
        
    logger.debug("Scheduler: Running check_price_alerts job.")
    active_alerts = await db.get_active_alerts()
    if not active_alerts:
        logger.debug("No active price alerts to check.")
        return

    # Group alerts by coin to minimize API calls
    coin_ids_to_check = list(set(alert['coin_id'] for alert in active_alerts))
    
    try:
        # Fetch prices for all coins at once
        price_data = await api_clients.get_crypto_price(','.join(coin_ids_to_check), DEFAULT_FIAT)
        
        if not price_data:
            logger.warning("No price data received from API during alert check.")
            return
            
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

            coin_data = price_data[coin_id]
            if preferred_fiat not in coin_data:
                logger.warning(f"Preferred fiat {preferred_fiat} not available for {coin_id}")
                continue
                
            current_price = coin_data[preferred_fiat]
            logger.debug(f"Alert Check: Coin: {coin_id}, Target: {target_price}, Current: {current_price}, Condition: {condition}")

            triggered = False
            if condition == 'above' and current_price > target_price:
                triggered = True
            elif condition == 'below' and current_price < target_price:
                triggered = True

            if triggered:
                try:
                    display_symbol = get_display_symbol(coin_id)
                    change_24h = coin_data.get(f"{preferred_fiat}_24h_change", 0)
                    message = (
                        f"🔔 **Price Alert Triggered!** 🔔\n\n"
                        f"Coin: **{display_symbol}**\n"
                        f"Condition: Price {condition} {format_currency(target_price, preferred_fiat.upper())}\n"
                        f"Current Price: **{format_currency(current_price, preferred_fiat.upper())}**\n"
                        f"24h Change: {format_percentage(change_24h)}\n\n"
                        f"{'🔄 This is a recurring alert.' if is_recurring else '✅ Alert completed.'}"
                    )
                    await bot.send_message(chat_id=user_id, text=message, parse_mode=ParseMode.MARKDOWN)
                    
                    if not is_recurring:
                        await db.deactivate_alert(alert_id)
                        logger.info(f"One-time alert {alert_id} triggered for user {user_id}, coin {coin_id}. Alert deactivated.")
                    else:
                        logger.info(f"Recurring alert {alert_id} triggered for user {user_id}, coin {coin_id}. Alert remains active.")
                        
                except Exception as e:
                    logger.error(f"Error sending alert notification for user {user_id}, alert {alert_id}: {e}")
                    
    except Exception as e:
        logger.error(f"Error during batch price check for alerts: {e}")

async def check_volume_alerts():
    """Check for volume spike alerts."""
    if not bot:
        logger.error("Bot not initialized - cannot check volume alerts")
        return
        
    logger.debug("Scheduler: Running check_volume_alerts job.")
    active_alerts = await db.get_active_volume_alerts()
    if not active_alerts:
        return

    coin_ids_to_check = list(set(alert['coin_id'] for alert in active_alerts))
    
    try:
        price_data = await api_clients.get_crypto_price(','.join(coin_ids_to_check), DEFAULT_FIAT)
        
        if not price_data:
            return
            
        for alert in active_alerts:
            coin_id = alert['coin_id']
            user_id = alert['user_id']
            threshold_multiplier = alert['threshold_multiplier']
            preferred_fiat = alert['preferred_fiat']

            if coin_id not in price_data:
                continue

            coin_data = price_data[coin_id]
            current_volume = coin_data.get(f"{preferred_fiat}_24h_vol", 0)
            
            if coin_id in previous_volumes:
                previous_volume = previous_volumes[coin_id]
                if previous_volume > 0:
                    volume_increase = current_volume / previous_volume
                    if volume_increase >= threshold_multiplier:
                        try:
                            display_symbol = get_display_symbol(coin_id)
                            message = (
                                f"📊 **Volume Alert Triggered!** 📊\n\n"
                                f"Coin: **{display_symbol}**\n"
                                f"Volume increased by **{volume_increase:.1f}x**\n"
                                f"Current 24h Volume: {format_currency(current_volume, preferred_fiat.upper(), 0)}\n"
                                f"Previous Volume: {format_currency(previous_volume, preferred_fiat.upper(), 0)}"
                            )
                            await bot.send_message(chat_id=user_id, text=message, parse_mode=ParseMode.MARKDOWN)
                        except Exception as e:
                            logger.error(f"Error sending volume alert for user {user_id}: {e}")
            
            previous_volumes[coin_id] = current_volume
            
    except Exception as e:
        logger.error(f"Error during volume alert check: {e}")

def setup_scheduler():
    """Setup the APScheduler with all jobs."""
    scheduler = AsyncIOScheduler(timezone="UTC")
    
    # Price alerts - check every minute
    scheduler.add_job(
        check_price_alerts, 
        'interval', 
        minutes=1, 
        id="price_alert_checker",
        max_instances=1,
        coalesce=True
    )
    
    # Volume alerts - check every 5 minutes
    scheduler.add_job(
        check_volume_alerts,
        'interval',
        minutes=5,
        id="volume_alert_checker",
        max_instances=1,
        coalesce=True
    )
    
    logger.info("Scheduler setup complete. Price alerts: every 1 min, Volume alerts: every 5 min.")
    return scheduler