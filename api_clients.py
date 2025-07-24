import logging
import asyncio
import aiohttp
import time
from pycoingecko import CoinGeckoAPI
from config import NEWS_API_KEY, DEFAULT_FIAT, SUPPORTED_FIAT
from utils import get_coingecko_id

logger = logging.getLogger(__name__)
cg = CoinGeckoAPI()

# Rate limiting
last_api_call = {}
API_RATE_LIMIT = 1.0  # seconds between calls

async def rate_limit_check(api_name: str):
    """Simple rate limiting to avoid API abuse."""
    current_time = time.time()
    if api_name in last_api_call:
        time_diff = current_time - last_api_call[api_name]
        if time_diff < API_RATE_LIMIT:
            await asyncio.sleep(API_RATE_LIMIT - time_diff)
    last_api_call[api_name] = time.time()

async def get_crypto_price(coin_id: str, vs_currency: str = DEFAULT_FIAT):
    """Fetch crypto price from CoinGecko with retry logic."""
    await rate_limit_check("coingecko_price")
    cg_coin_id = get_coingecko_id(coin_id)
    
    # Handle multiple coins
    if ',' in coin_id:
        coin_ids = [get_coingecko_id(c.strip()) for c in coin_id.split(',')]
        cg_coin_id = ','.join(coin_ids)
    
    for attempt in range(3):
        try:
            price_data = cg.get_price(
                ids=cg_coin_id,
                vs_currencies=vs_currency,
                include_market_cap='true',
                include_24hr_vol='true',
                include_24hr_change='true'
            )
            if price_data:
                if ',' in cg_coin_id:
                    return price_data
                elif cg_coin_id in price_data:
                    return price_data[cg_coin_id]
            return None
        except Exception as e:
            logger.warning(f"CoinGecko API error for {cg_coin_id}, attempt {attempt+1}: {e}")
            if attempt < 2:
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
            else:
                logger.error(f"Failed to fetch price for {cg_coin_id}: {e}")
                return None

async def get_coin_details(coin_id: str):
    """Fetch detailed coin information from CoinGecko."""
    await rate_limit_check("coingecko_details")
    cg_coin_id = get_coingecko_id(coin_id)
    try:
        data = cg.get_coin_by_id(
            id=cg_coin_id,
            localization='false',
            tickers='false',
            market_data='true',
            community_data='false',
            developer_data='false',
            sparkline='false'
        )
        return data
    except Exception as e:
        logger.error(f"CoinGecko get_coin_details error for {cg_coin_id}: {e}")
        return None

async def get_market_chart(coin_id: str, vs_currency: str = DEFAULT_FIAT, days: int = 7):
    """Fetch market chart data for a coin."""
    await rate_limit_check("coingecko_chart")
    cg_coin_id = get_coingecko_id(coin_id)
    try:
        chart_data = cg.get_coin_market_chart_by_id(
            id=cg_coin_id,
            vs_currency=vs_currency,
            days=days,
            interval='daily' if days > 1 else 'hourly'
        )
        return chart_data
    except Exception as e:
        logger.error(f"CoinGecko get_market_chart error for {cg_coin_id}: {e}")
        return None

async def get_top_movers(vs_currency: str = DEFAULT_FIAT, limit: int = 5):
    """Fetch top gainers and losers."""
    await rate_limit_check("coingecko_movers")
    try:
        data = cg.get_coins_markets(
            vs_currency=vs_currency,
            order='market_cap_desc',
            per_page=limit,
            page=1
            price_change_percentage='24h'
        )
        if data:
            # Sort by 24h change and return top gainers and losers
            sorted_data = sorted(data, key=lambda x: x.get('price_change_percentage_24h', 0), reverse=True)
            return sorted_data[:limit]
        return []
    except Exception as e:
        logger.error(f"CoinGecko get_top_movers error: {e}")
        return []

async def get_crypto_news(query: str = "cryptocurrency", sources: str = None, page_size: int = 5):
    """Fetch crypto news from NewsAPI."""
    if not NEWS_API_KEY:
        logger.warning("NEWS_API_KEY not configured. News feature disabled.")
        return []

    url = "https://newsapi.org/v2/everything"
    params = {
        "q": query,
        "apiKey": NEWS_API_KEY,
        "pageSize": page_size,
        "sortBy": "publishedAt",
        "language": "en",
        "domains": "coindesk.com,cointelegraph.com,decrypt.co,bitcoinmagazine.com,theblock.co"
    }

    async with aiohttp.ClientSession() as session:
        for attempt in range(3):
            try:
                async with session.get(url, params=params) as response:
                    response.raise_for_status()
                    data = await response.json()
                    articles = data.get("articles", [])
                    # Filter out articles with missing content
                    filtered_articles = [
                        article for article in articles 
                        if article.get('title') and article.get('url') and 
                        article.get('title') != '[Removed]'
                    ]
                    return filtered_articles
            except aiohttp.ClientError as e:
                logger.warning(f"NewsAPI request error, attempt {attempt+1}: {e}")
                if attempt < 2:
                    await asyncio.sleep(2 ** attempt)
                else:
                    logger.error(f"Failed to fetch news: {e}")
                    return []
            except Exception as e:
                logger.error(f"Unexpected error fetching news: {e}")
                return []

async def get_fear_greed_index():
    """Fetch Fear & Greed Index."""
    url = "https://api.alternative.me/fng/?limit=1"
    async with aiohttp.ClientSession() as session:
        for attempt in range(3):
            try:
                async with session.get(url) as response:
                    response.raise_for_status()
                    data = await response.json()
                    if data and "data" in data and len(data["data"]) > 0:
                        return data["data"][0]
                    return None
            except aiohttp.ClientError as e:
                logger.warning(f"Fear & Greed API request error, attempt {attempt+1}: {e}")
                if attempt < 2:
                    await asyncio.sleep(2 ** attempt)
                else:
                    logger.error(f"Failed to fetch Fear & Greed Index: {e}")
                    return None

async def get_trending_coins():
    """Fetch trending coins from CoinGecko."""
    await rate_limit_check("coingecko_trending")
    try:
        data = cg.get_search_trending()
        return data.get('coins', [])
    except Exception as e:
        logger.error(f"CoinGecko trending coins error: {e}")
        return []

async def get_global_market_data():
    """Fetch global cryptocurrency market data."""
    await rate_limit_check("coingecko_global")
    try:
        data = cg.get_global()
        return data.get('data', {})
    except Exception as e:
        logger.error(f"CoinGecko global market data error: {e}")
        return {}


import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from telegram.constants import ParseMode
import database as db
import api_clients
from config import DEFAULT_FIAT, NEWS_SOURCES, SUPPORTED_FIAT
from utils import get_coingecko_id, get_display_symbol, format_currency, format_percentage, sanitize_input
from datetime import datetime
import asyncio

logger = logging.getLogger(__name__)

# Conversation states for alerts and settings
COIN_FOR_ALERT, PRICE_FOR_ALERT, CONDITION_FOR_ALERT, RECURRING_FOR_ALERT = range(4)
FIAT_FOR_SETTINGS = range(1)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await db.add_user_if_not_exists(user.id)
    welcome_text = (
        f"👋 Hello {user.first_name}! I'm CoinSeer, your crypto companion.\n\n"
        "I can help you with:\n"
        "📈 Real-time crypto prices\n"
        "📊 Price charts and market data\n"
        "🔔 Price alerts\n"
        "📰 Latest crypto news\n"
        "💼 Portfolio management\n"
        "📋 Watchlist tracking\n"
        "🌍 Fear & Greed Index\n\n"
        "Type `/` or `/help` to see all commands."
    )
    keyboard = [
        [InlineKeyboardButton("🚀 Get BTC Price", callback_data="price_btc"),
         InlineKeyboardButton("📰 Latest News", callback_data="news_crypto")],
        [InlineKeyboardButton("🔔 Set Price Alert", callback_data="alert_start"),
         InlineKeyboardButton("💼 View Portfolio", callback_data="portfolio_view")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(welcome_text, reply_markup=reply_markup)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "ℹ️ **CoinSeer Commands:**\n\n"
        "**/price <symbol>** - Get current price (e.g., `/price BTC`)\n"
        "**/chart <symbol> [days]** - View price chart (e.g., `/chart ETH 7`)\n"
        "**/news [keyword]** - Latest crypto news (e.g., `/news bitcoin`)\n"
        "**/alert** - Set a price alert\n"
        "**/my_alerts** - View active alerts\n"
        "**/delete_alert <id>** - Delete an alert\n"
        "**/watchlist_add <symbol>** - Add coin to watchlist\n"
        "**/watchlist_remove <symbol>** - Remove coin from watchlist\n"
        "**/watchlist** - View watchlist prices\n"
        "**/portfolio_add <symbol> <amount>** - Add to portfolio\n"
        "**/portfolio_remove <symbol>** - Remove from portfolio\n"
        "**/portfolio** - View portfolio value\n"
        "**/market <symbol>** - Get market data\n"
        "**/topmovers** - See top gainers/losers\n"
        "**/predict <symbol>** - Get mock price prediction\n"
        "**/settings** - Configure preferences\n"
        "**/fear_greed** - Crypto Fear & Greed Index\n"
        "**/help** - Show this message"
    )
    await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)



async def price_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Please specify a coin symbol (e.g., `/price BTC`).")
        return
    coin_symbol = sanitize_input(context.args[0])
    preferred_fiat = await db.get_user_preferred_fiat(update.effective_user.id)
    cg_coin_id = get_coingecko_id(coin_symbol)
    await update.message.reply_text(f"⏳ Fetching price for {coin_symbol.upper()}...")
    data = await api_clients.get_crypto_price(cg_coin_id, preferred_fiat)
    if data and preferred_fiat in data:
        price = data[preferred_fiat]
        market_cap = data.get(f"{preferred_fiat}_market_cap", None)
        volume = data.get(f"{preferred_fiat}_24h_vol", None)
        change_24h = data.get(f"{preferred_fiat}_24h_change", None)
        message = (
            f"🪙 **{coin_symbol.upper()} Price ({preferred_fiat.upper()})**\n"
            f"💰 Price: {format_currency(price, preferred_fiat.upper())}\n"
            f"📊 24h Change: {format_percentage(change_24h)}\n"
            f"📈 Market Cap: {format_currency(market_cap, preferred_fiat.upper(), 0)}\n"
            f"📉 24h Volume: {format_currency(volume, preferred_fiat.upper(), 0)}"
        )
        await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text(f"Sorry, couldn't fetch price for {coin_symbol.upper()}. Try the full name (e.g., bitcoin).")

async def chart_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Please specify a coin symbol (e.g., `/chart BTC 7`).")
        return
    coin_symbol = sanitize_input(context.args[0])
    days = int(context.args[1]) if len(context.args) > 1 else 7
    if days < 1 or days > 365:
        await update.message.reply_text("Days must be between 1 and 365.")
        return
    preferred_fiat = await db.get_user_preferred_fiat(update.effective_user.id)
    cg_coin_id = get_coingecko_id(coin_symbol)
    await update.message.reply_text(f"⏳ Fetching {days}-day chart for {coin_symbol.upper()}...")
    chart_data = await api_clients.get_market_chart(cg_coin_id, preferred_fiat, days)
    if not chart_data or not chart_data.get('prices'):
        await update.message.reply_text(f"Couldn't fetch chart data for {coin_symbol.upper()}.")
        return
    prices = chart_data['prices'][-10:]  # Last 10 points for brevity
    max_price = max(price for _, price in prices)
    min_price = min(price for _, price in prices)
    message = f"📊 **{coin_symbol.upper()} {days}-day Price Chart ({preferred_fiat.upper()})**\n\n"
    for timestamp, price in prices:
        date = datetime.fromtimestamp(timestamp/1000).strftime('%Y-%m-%d')
        bars = int((price - min_price) / (max_price - min_price + 0.001) * 10) if max_price != min_price else 5
        message += f"{date}: {format_currency(price, preferred_fiat.upper())} {'█' * bars}\n"
    await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)

async def news_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = sanitize_input(" ".join(context.args)) if context.args else "cryptocurrency"
    await update.message.reply_text(f"📰 Fetching news for '{query}'...")
    articles = await api_clients.get_crypto_news(query=query, sources=NEWS_SOURCES, page_size=5)
    if articles:
        message = f"**Top 5 Crypto News for '{query.title()}'**:\n\n"
        for i, article in enumerate(articles):
            title = article.get('title', 'No Title')
            url = article.get('url', '#')
            source_name = article.get('source', {}).get('name', 'Unknown')
            message += f"{i+1}. [{title}]({url}) - _{source_name}_\n\n"
        await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)
    else:
        await update.message.reply_text(f"No recent news found for '{query}'. Try a different keyword.")

async def fear_greed_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⏳ Fetching Fear & Greed Index...")
    data = await api_clients.get_fear_greed_index()
    if data:
        value = data.get('value')
        classification = data.get('value_classification')
        timestamp = data.get('timestamp')
        message = (
            f"**Crypto Fear & Greed Index**\n\n"
            f"Value: **{value}/100**\n"
            f"Sentiment: **{classification}**\n"
            f"Updated: _{timestamp}_"
        )
        await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text("Couldn't fetch Fear & Greed Index. Please try again.")

async def alert_command_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await db.add_user_if_not_exists(update.effective_user.id)
    keyboard = [
        [InlineKeyboardButton(f"Coin: {sym}", callback_data=f"alert_coin_{get_coingecko_id(sym)}") for sym in ["BTC", "ETH", "SOL"]],
        [InlineKeyboardButton("Other coin", callback_data="alert_coin_other")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Which coin do you want to monitor?", reply_markup=reply_markup)
    return COIN_FOR_ALERT

async def alert_coin_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if 'callback_query' in update:
        query = update.callback_query
        await query.answer()
        data = query.data
        if data == 'alert_coin_other':
            await query.message.reply_text("Please enter the coin symbol or name (e.g., BTC, Ethereum).")
            return COIN_FOR_ALERT
        cg_coin_id = data.split('_')[-1]
        coin_symbol_display = get_display_symbol(cg_coin_id)
    else:
        coin_input = sanitize_input(update.message.text)
        cg_coin_id = get_coingecko_id(coin_input)
        coin_symbol_display = coin_input.upper()

    preferred_fiat = await db.get_user_preferred_fiat(update.effective_user.id)
    current_price_data = await api_clients.get_crypto_price(cg_coin_id, preferred_fiat)
    if not current_price_data:
        await update.message.reply_text(f"Couldn't find '{coin_symbol_display}'. Try a valid symbol or name.")
        return COIN_FOR_ALERT

    context.user_data['alert_coin_id'] = cg_coin_id
    context.user_data['alert_coin_symbol_display'] = coin_symbol_display
    current_price = current_price_data.get(preferred_fiat, "N/A")
    await update.message.reply_text(
        f"Got it: {coin_symbol_display} (current: {format_currency(current_price, preferred_fiat.upper())}).\n"
        f"What's the target price in {preferred_fiat.upper()}? (e.g., 65000)"
    )
    return PRICE_FOR_ALERT

async def alert_price_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        target_price = float(sanitize_input(update.message.text))
        if target_price <= 0:
            raise ValueError("Price must be positive.")
        context.user_data['alert_target_price'] = target_price
    except ValueError:
        await update.message.reply_text("Please enter a valid number (e.g., 65000).")
        return PRICE_FOR_ALERT

    keyboard = [
        [InlineKeyboardButton("Above target", callback_data="alert_cond_above"),
         InlineKeyboardButton("Below target", callback_data="alert_cond_below")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Notify when price goes:", reply_markup=reply_markup)
    return CONDITION_FOR_ALERT

async def alert_condition_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    condition = query.data.split('_')[-1]
    context.user_data['alert_condition'] = condition
    keyboard = [
        [InlineKeyboardButton("One-time alert", callback_data="alert_recurring_false"),
         InlineKeyboardButton("Recurring alert", callback_data="alert_recurring_true")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.reply_text("Should this alert repeat after triggering?", reply_markup=reply_markup)
    return RECURRING_FOR_ALERT

async def alert_recurring_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    recurring = query.data.split('_')[-1] == 'true'
    user_id = query.from_user.id
    coin_id = context.user_data['alert_coin_id']
    coin_symbol_display = context.user_data['alert_coin_symbol_display']
    target_price = context.user_data['alert_target_price']
    condition = context.user_data['alert_condition']
    success = await db.add_price_alert(user_id, coin_id, target_price, condition, recurring)
    if success:
        await query.edit_message_text(
            f"✅ Alert set for {coin_symbol_display} when price goes {condition} {format_currency(target_price, (await db.get_user_preferred_fiat(user_id)).upper())}! "
            f"{'Recurring' if recurring else 'One-time'} alert."
        )
    else:
        await query.edit_message_text("😔 Couldn't save the alert. Try again.")
    context.user_data.clear()
    return ConversationHandler.END

async def alert_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Alert setup cancelled.")
    context.user_data.clear()
    return ConversationHandler.END

async def my_alerts_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    alerts = await db.get_active_alerts()
    user_alerts = [alert for alert in alerts if alert['user_id'] == user_id]
    if not user_alerts:
        await update.message.reply_text("No active alerts. Use `/alert` to set one.")
        return
    message = "🔔 **Your Active Alerts:**\n\n"
    for alert in user_alerts:
        display_symbol = get_display_symbol(alert['coin_id'])
        message += (
            f"🔸 **{display_symbol}**: Notify if price {alert['condition']} "
            f"{format_currency(alert['target_price'], alert['preferred_fiat'].upper())} "
            f"({'recurring' if alert['is_recurring'] else 'one-time'})\n"
            f"   (ID: {alert['alert_id']} - `/delete_alert {alert['alert_id']}`)\n\n"
        )
    await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)

async def delete_alert_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Please specify an alert ID (e.g., `/delete_alert 1`). See `/my_alerts`.")
        return
    try:
        alert_id = int(sanitize_input(context.args[0]))
        user_id = update.effective_user.id
        if await db.delete_alert(user_id, alert_id):
            await update.message.reply_text(f"Alert ID {alert_id} deleted.")
        else:
            await update.message.reply_text(f"Alert ID {alert_id} not found or not yours.")
    except ValueError:
        await update.message.reply_text("Please provide a valid alert ID number.")

async def watchlist_add_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await db.add_user_if_not_exists(user_id)
    if not context.args:
        await update.message.reply_text("Please specify a coin symbol (e.g., `/watchlist_add BTC`).")
        return
    coin_symbol = sanitize_input(context.args[0])
    cg_coin_id = get_coingecko_id(coin_symbol)
    price_data = await api_clients.get_crypto_price(cg_coin_id, await db.get_user_preferred_fiat(user_id))
    if not price_data:
        await update.message.reply_text(f"Couldn't find '{coin_symbol}'. Try a valid symbol or name.")
        return
    response_message = await db.add_to_watchlist(user_id, cg_coin_id)
    await update.message.reply_text(response_message)

async def watchlist_remove_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not context.args:
        await update.message.reply_text("Please specify a coin symbol (e.g., `/watchlist_remove BTC`).")
        return
    coin_symbol = sanitize_input(context.args[0])
    cg_coin_id = get_coingecko_id(coin_symbol)
    response_message = await db.remove_from_watchlist(user_id, cg_coin_id)
    await update.message.reply_text(response_message)

async def watchlist_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    watchlist_coins = await db.get_watchlist(user_id)
    if not watchlist_coins:
        await update.message.reply_text("Your watchlist is empty. Use `/watchlist_add <symbol>`.")
        return
    preferred_fiat = await db.get_user_preferred_fiat(user_id)
    await update.message.reply_text("⏳ Fetching watchlist prices...")
    message_parts = ["**Your Watchlist Prices:**\n"]
    price_data = await api_clients.get_crypto_price(','.join(watchlist_coins), preferred_fiat)
    for coin_id in watchlist_coins:
        display_symbol = get_display_symbol(coin_id)
        if price_data and coin_id in price_data and preferred_fiat in price_data[coin_id]:
            price = price_data[coin_id][preferred_fiat]
            change_24h = price_data[coin_id].get(f"{preferred_fiat}_24h_change", None)
            change_emoji = "📈" if (change_24h or 0) >= 0 else "📉"
            message_parts.append(
                f"🔸 **{display_symbol}**: {format_currency(price, preferred_fiat.upper())} ({change_emoji} {format_percentage(change_24h)})"
            )
        else:
            message_parts.append(f"🔸 **{display_symbol}**: Error fetching price.")
    await update.message.reply_text("\n".join(message_parts), parse_mode=ParseMode.MARKDOWN)

async def portfolio_add_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await db.add_user_if_not_exists(user_id)
    if len(context.args) < 2:
        await update.message.reply_text("Please specify coin and amount (e.g., `/portfolio_add BTC 0.5`).")
        return
    coin_symbol = sanitize_input(context.args[0])
    try:
        amount = float(sanitize_input(context.args[1]))
    except ValueError:
        await update.message.reply_text("Please provide a valid amount (e.g., 0.5).")
        return
    cg_coin_id = get_coingecko_id(coin_symbol)
    price_data = await api_clients.get_crypto_price(cg_coin_id, await db.get_user_preferred_fiat(user_id))
    if not price_data:
        await update.message.reply_text(f"Couldn't find '{coin_symbol}'. Try a valid symbol or name.")
        return
    response_message = await db.add_to_portfolio(user_id, cg_coin_id, amount)
    await update.message.reply_text(response_message)

async def portfolio_remove_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not context.args:
        await update.message.reply_text("Please specify a coin symbol (e.g., `/portfolio_remove BTC`).")
        return
    coin_symbol = sanitize_input(context.args[0])
    cg_coin_id = get_coingecko_id(coin_symbol)
    response_message = await db.remove_from_portfolio(user_id, cg_coin_id)
    await update.message.reply_text(response_message)

async def portfolio_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    portfolio = await db.get_portfolio(user_id)
    if not portfolio:
        await update.message.reply_text("Your portfolio is empty. Use `/portfolio_add <symbol> <amount>`.")
        return
    preferred_fiat = await db.get_user_preferred_fiat(user_id)
    await update.message.reply_text("⏳ Fetching portfolio values...")
    message_parts = ["**Your Portfolio:**\n"]
    total_value = 0
    coin_ids = [coin_id for coin_id, _ in portfolio]
    price_data = await api_clients.get_crypto_price(','.join(coin_ids), preferred_fiat)
    for coin_id, amount in portfolio:
        display_symbol = get_display_symbol(coin_id)
        if price_data and coin_id in price_data and preferred_fiat in price_data[coin_id]:
            price = price_data[coin_id][preferred_fiat]
            value = price * amount
            total_value += value
            message_parts.append(
                f"🔸 **{display_symbol}**: {amount:.4f} units, Value: {format_currency(value, preferred_fiat.upper())}"
            )
        else:
            message_parts.append(f"🔸 **{display_symbol}**: {amount:.4f} units, Value: Error")
    message_parts.append(f"\n**Total Value**: {format_currency(total_value, preferred_fiat.upper())}")
    await update.message.reply_text("\n".join(message_parts), parse_mode=ParseMode.MARKDOWN)

async def market_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Please specify a coin symbol (e.g., `/market BTC`).")
        return
    coin_symbol = sanitize_input(context.args[0])
    preferred_fiat = await db.get_user_preferred_fiat(update.effective_user.id)
    cg_coin_id = get_coingecko_id(coin_symbol)
    await update.message.reply_text(f"⏳ Fetching market data for {coin_symbol.upper()}...")
    data = await api_clients.get_coin_details(cg_coin_id)
    if data:
        price = data['market_data']['current_price'][preferred_fiat]
        market_cap = data['market_data']['market_cap'][preferred_fiat]
        volume = data['market_data']['total_volume'][preferred_fiat]
        circulating_supply = data['market_data'].get('circulating_supply', 'N/A')
        total_supply = data['market_data'].get('total_supply', 'N/A')
        message = (
            f"📊 **{coin_symbol.upper()} Market Data ({preferred_fiat.upper()})**\n"
            f"💰 Price: {format_currency(price, preferred_fiat.upper())}\n"
            f"📈 Market Cap: {format_currency(market_cap, preferred_fiat.upper(), 0)}\n"
            f"📉 24h Volume: {format_currency(volume, preferred_fiat.upper(), 0)}\n"
            f"🔄 Circulating Supply: {circulating_supply:,}\n"
            f"🌐 Total Supply: {total_supply:,}"
        )
        await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text(f"Couldn't fetch market data for {coin_symbol.upper()}.")

async def topmovers_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    preferred_fiat = await db.get_user_preferred_fiat(update.effective_user.id)
    await update.message.reply_text(f"⏳ Fetching top movers in {preferred_fiat.upper()}...")
    movers = await api_clients.get_top_movers(preferred_fiat, limit=5)
    if not movers:
        await update.message.reply_text("Couldn't fetch top movers. Try again later.")
        return
    message = f"📈 **Top 5 Movers (24h, {preferred_fiat.upper()})**\n\n"
    for coin in movers:
        symbol = get_display_symbol(coin['id'])
        price = coin['current_price']
        change_24h = coin['price_change_percentage_24h']
        change_emoji = "📈" if change_24h >= 0 else "📉"
        message += (
            f"🔸 **{symbol}**: {format_currency(price, preferred_fiat.upper())} "
            f"({change_emoji} {format_percentage(change_24h)})\n"
        )
    await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)

async def predict_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Please specify a coin symbol (e.g., `/predict BTC`).")
        return
    coin_symbol = sanitize_input(context.args[0])
    preferred_fiat = await db.get_user_preferred_fiat(update.effective_user.id)
    cg_coin_id = get_coingecko_id(coin_symbol)
    price_data = await api_clients.get_crypto_price(cg_coin_id, preferred_fiat)
    if not price_data:
        await update.message.reply_text(f"Couldn't fetch data for {coin_symbol.upper()}.")
        return
    current_price = price_data[preferred_fiat]
    # Mock prediction (real predictions need ML models)
    mock_change = (current_price * 0.05) * (-1 if hash(coin_symbol) % 2 else 1)
    predicted_price = current_price + mock_change
    message = (
        f"🔮 **Mock Price Prediction for {coin_symbol.upper()} ({preferred_fiat.upper()})**\n"
        f"Current Price: {format_currency(current_price, preferred_fiat.upper())}\n"
        f"Predicted 24h Price: {format_currency(predicted_price, preferred_fiat.upper())} "
        f"({format_percentage((predicted_price - current_price) / current_price * 100)})\n"
        f"_Note: This is a mock prediction for demonstration._"
    )
    await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)

async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton(fiat.upper(), callback_data=f"set_fiat_{fiat}") for fiat in SUPPORTED_FIAT[:3]],
        [InlineKeyboardButton(fiat.upper(), callback_data=f"set_fiat_{fiat}") for fiat in SUPPORTED_FIAT[3:]]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Select your preferred currency:", reply_markup=reply_markup)
    return FIAT_FOR_SETTINGS

async def settings_fiat_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    fiat = query.data.split('_')[-1]
    user_id = query.from_user.id
    if await db.set_user_preferred_fiat(user_id, fiat):
        await query.edit_message_text(f"Preferred currency set to {fiat.upper()}.")
    else:
        await query.edit_message_text(f"Invalid currency. Supported: {', '.join(SUPPORTED_FIAT)}.")
    return ConversationHandler.END

async def button_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    if data == "price_btc":
        context.args = ["BTC"]
        await price_command(query, context)
    elif data == "news_crypto":
        await news_command(query, context)
    elif data == "portfolio_view":
        await portfolio_command(query, context)
    elif data.startswith("alert_coin_"):
        context.user_data['callback_query'] = query
        await alert_coin_received(query, context)
    elif data.startswith("set_fiat_"):
        context.user_data['callback_query'] = query
        await settings_fiat_received(query, context)