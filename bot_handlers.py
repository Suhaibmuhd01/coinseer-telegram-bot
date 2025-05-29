import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from telegram.constants import ParseMode
import database as db
import api_clients
from config import DEFAULT_FIAT, NEWS_SOURCES

logger = logging.getLogger(__name__)

# Conversation states for adding alerts
COIN_FOR_ALERT, PRICE_FOR_ALERT, CONDITION_FOR_ALERT = range(3)

# --- Helper function to get coin ID (map common symbols to coingecko IDs) ---
def get_coingecko_id(symbol: str) -> str:
    mapping = {
        "btc": "bitcoin",
        "eth": "ethereum",
        "doge": "dogecoin",
        "sol": "solana",
        "xrp": "ripple",
       
    }
    return mapping.get(symbol.lower(), symbol.lower()) # Default to symbol if not found

# --- Command Handlers ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await db.add_user_if_not_exists(user.id) # Ensure user is in DB
    welcome_text = (
        f"👋 Hello {user.first_name}! I'm CoinSeer, your crypto companion.\n\n"
        "I can help you with:\n"
        "📈 Real-time crypto prices\n"
        "📰 Latest crypto news\n"
        "🔔 Price alerts\n"
        "📊 Market overview & more!\n\n"
        "Type `/help` to see all available commands."
    )
    keyboard = [
        [InlineKeyboardButton("🚀 Get BTC Price", callback_data="price_btc")],
        [InlineKeyboardButton("📰 Latest Crypto News", callback_data="news_crypto")],
        [InlineKeyboardButton("🔔 Set Price Alert", callback_data="alert_start")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(welcome_text, reply_markup=reply_markup)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "ℹ️ **Available Commands:**\n\n"
        "**/price <coin_symbol>** - Get current price (e.g., `/price BTC`)\n"
        "/chart <coin_symbol> - Get 7-day price chart (e.g., `/chart ETH`)\n"
        "/news [keyword] - Latest crypto news. Optional keyword (e.g., `/news bitcoin` or `/news` for general)\n"
        "/alert - Start setting up a new price alert.\n"
        "/my_alerts - View your active price alerts.\n"
        "/watchlist_add <coin_symbol> - Add a coin to your watchlist.\n"
        "/watchlist_remove <coin_symbol> - Remove a coin from your watchlist.\n"
        "/watchlist - View prices for coins in your watchlist.\n"
        "/fear_greed - Show the current Crypto Fear & Greed Index.\n"

        "**/help** - Show this help message."
    )
    await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)

async def price_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Please specify a coin symbol (e.g., `/price BTC`).")
        return

    coin_symbol = context.args[0].upper()
    cg_coin_id = get_coingecko_id(coin_symbol)

    await update.message.reply_text(f"⏳ Fetching price for {coin_symbol}...")

    data = await api_clients.get_crypto_price(cg_coin_id, DEFAULT_FIAT)

    if data and DEFAULT_FIAT in data:
        price = data[DEFAULT_FIAT]
        market_cap = data.get(f"{DEFAULT_FIAT}_market_cap", "N/A")
        volume = data.get(f"{DEFAULT_FIAT}_24h_vol", "N/A")
        change_24h = data.get(f"{DEFAULT_FIAT}_24h_change", "N/A")

        message = (
            f"🪙 **{coin_symbol.upper()} Price ({DEFAULT_FIAT.upper()})**\n"
            f"💰 Price: ${price:,.2f}\n"
            f"📊 24h Change: {change_24h:.2f}%\n"
            f"📈 Market Cap: ${market_cap:,.0f}\n"
            f"📉 24h Volume: ${volume:,.0f}"
        )
        await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text(f"Sorry, I couldn't fetch the price for {coin_symbol}. "
                                        f"Ensure the symbol is correct or try its full name (e.g., bitcoin).")

async def news_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = " ".join(context.args) if context.args else "cryptocurrency"
    await update.message.reply_text(f"📰 Fetching latest news for '{query}'...")

    articles = await api_clients.get_crypto_news(query=query, sources=NEWS_SOURCES, page_size=5)
    if articles:
        message = f"**Top 5 Crypto News for '{query.title()}'**:\n\n"
        for i, article in enumerate(articles):
            title = article.get('title', 'No Title')
            url = article.get('url', '#')
            source_name = article.get('source', {}).get('name', 'Unknown Source')
            message += f"{i+1}. [{title}]({url}) - _{source_name}_\n\n"
        await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)
    else:
        await update.message.reply_text(f"Sorry, I couldn't find any recent news for '{query}'.")

async def fear_greed_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⏳ Fetching Fear & Greed Index...")
    data = await api_clients.get_fear_greed_index()
    if data:
        value = data.get('value')
        classification = data.get('value_classification')
        timestamp = data.get('timestamp') # You might want to format this
        message = (
            f"**Crypto Fear & Greed Index**\n\n"
            f"Current Value: **{value}**\n"
            f"Sentiment: **{classification}**\n"
            f"_(Updated: {timestamp})_"
        )
        await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text("Sorry, I couldn't fetch the Fear & Greed Index right now.")


# --- Alert Conversation Handlers ---
async def alert_command_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Starts the conversation to add a price alert."""
    await db.add_user_if_not_exists(update.effective_user.id)
    await update.message.reply_text("Okay, let's set up a price alert!\n"
                                    "Which coin do you want to monitor? (e.g., BTC, ETH, Sol, Not, XRP, bitcoin)")
    return COIN_FOR_ALERT

async def alert_coin_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Stores the coin and asks for the target price."""
    coin_input = update.message.text.strip()
    cg_coin_id = get_coingecko_id(coin_input) # Convert to coingecko ID

    # Validate coin (optional - check if coin exists via API)
    current_price_data = await api_clients.get_crypto_price(cg_coin_id, DEFAULT_FIAT)
    if not current_price_data:
        await update.message.reply_text(f"Hmm, I couldn't find information for '{coin_input}'. "
                                        "Please enter a valid coin symbol or name.")
        return COIN_FOR_ALERT # Ask again

    context.user_data['alert_coin_id'] = cg_coin_id
    context.user_data['alert_coin_symbol_display'] = coin_input.upper() # For display
    current_price_usd = current_price_data.get(DEFAULT_FIAT, "N/A")

    await update.message.reply_text(f"Got it: {coin_input.upper()} (current price: ${current_price_usd}).\n"
                                    f"What's the target price in {DEFAULT_FIAT.upper()}? (e.g., 65000)")
    return PRICE_FOR_ALERT

async def alert_price_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Stores the price and asks for the condition (above/below)."""
    try:
        target_price = float(update.message.text.strip())
        if target_price <= 0:
            raise ValueError("Price must be positive.")
        context.user_data['alert_target_price'] = target_price
    except ValueError:
        await update.message.reply_text("That doesn't look like a valid price. Please enter a number (e.g., 65000).")
        return PRICE_FOR_ALERT # Ask again

    keyboard = [
        [InlineKeyboardButton("Notify if price goes ABOVE target", callback_data="alert_cond_above")],
        [InlineKeyboardButton("Notify if price goes BELOW target", callback_data="alert_cond_below")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("When should I notify you?", reply_markup=reply_markup)
    return CONDITION_FOR_ALERT

async def alert_condition_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Stores the condition and saves the alert."""
    query = update.callback_query
    await query.answer() # Acknowledge callback

    condition = query.data.split('_')[-1] # 'above' or 'below'
    user_id = query.from_user.id
    coin_id = context.user_data['alert_coin_id']
    coin_symbol_display = context.user_data['alert_coin_symbol_display']
    target_price = context.user_data['alert_target_price']

    success = await db.add_price_alert(user_id, coin_id, target_price, condition)

    if success:
        await query.edit_message_text(
            text=f"✅ Alert set! I'll notify you if {coin_symbol_display} goes {condition} ${target_price:,.2f}."
        )
    else:
        await query.edit_message_text(text="😔 Sorry, I couldn't save the alert. Please try again.")

    context.user_data.clear() # Clean up user_data
    return ConversationHandler.END

async def alert_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancels the alert setup conversation."""
    await update.message.reply_text("Alert setup cancelled.")
    context.user_data.clear()
    return ConversationHandler.END

async def my_alerts_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    alerts = await db.get_active_alerts() # This gets all alerts, filter by user_id
    user_alerts = [alert for alert in alerts if alert['user_id'] == user_id]

    if not user_alerts:
        await update.message.reply_text("You have no active price alerts. Use `/alert` to set one.")
        return

    message = "🔔 **Your Active Price Alerts:**\n\n"
    for alert in user_alerts:
        # Map coingecko_id back to a display symbol if possible, or use the stored one
        # This requires more sophisticated coin_id management
        display_coin = alert['coin_id'].capitalize() # Simple capitalization for now
        message += (f"🔸 **{display_coin}**: Notify if price goes {alert['condition']} "
                    f"${alert['target_price']:,.2f} {alert['preferred_fiat'].upper()}\n"
                    f"   (Alert ID: {alert['alert_id']} - Use `/delete_alert {alert['alert_id']}` to remove)\n\n") # Add delete functionality later

    await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
    # Consider adding inline buttons to delete alerts directly from the message

# --- Watchlist Handlers ---
async def watchlist_add_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await db.add_user_if_not_exists(user_id)

    if not context.args:
        await update.message.reply_text("Please specify a coin symbol to add (e.g., `/watchlist_add BTC`).")
        return

    coin_symbol = context.args[0]
    cg_coin_id = get_coingecko_id(coin_symbol)

    # Optional: Validate coin by trying to fetch its price
    price_data = await api_clients.get_crypto_price(cg_coin_id, DEFAULT_FIAT)
    if not price_data:
        await update.message.reply_text(f"Sorry, I couldn't find info for '{coin_symbol}'. Is it a valid symbol/name?")
        return

    response_message = await db.add_to_watchlist(user_id, cg_coin_id) # Store the coingecko ID
    await update.message.reply_text(response_message)


async def watchlist_remove_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not context.args:
        await update.message.reply_text("Please specify a coin symbol to remove (e.g., `/watchlist_remove BTC`).")
        return

    coin_symbol = context.args[0]
    cg_coin_id = get_coingecko_id(coin_symbol)

    response_message = await db.remove_from_watchlist(user_id, cg_coin_id)
    await update.message.reply_text(response_message)


async def watchlist_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    watchlist_coins = await db.get_watchlist(user_id)

    if not watchlist_coins:
        await update.message.reply_text("Your watchlist is empty. Use `/watchlist_add <symbol>` to add coins.")
        return

    await update.message.reply_text("⏳ Fetching prices for your watchlist...")
    message_parts = ["**Your Watchlist Prices:**\n"]

    for coin_id in watchlist_coins:
        # Fetch price (assuming coin_id stored is the coingecko ID)
        data = await api_clients.get_crypto_price(coin_id, DEFAULT_FIAT)
        display_symbol = coin_id.capitalize() # needs better mapping back from ID to symbol

        if data and DEFAULT_FIAT in data:
            price = data[DEFAULT_FIAT]
            change_24h = data.get(f"{DEFAULT_FIAT}_24h_change", "N/A")
            change_emoji = "📈" if (change_24h or 0) >= 0 else "📉"
            message_parts.append(
                f"🔸 **{display_symbol}**: ${price:,.2f} ({change_emoji} {change_24h:.2f}%)"
            )
        else:
            message_parts.append(f"🔸 **{display_symbol}**: Error fetching price.")

    await update.message.reply_text("\n".join(message_parts), parse_mode=ParseMode.MARKDOWN)


# --- Callback Query Handlers (for inline buttons) ---
async def button_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer() # Acknowledge button press

    data = query.data
    # Example: route based on callback data
    if data == "price_btc":
        context.args = ["BTC"] # Simulate arguments for price_command
        await price_command(query, context) # Use query as update for sending reply
    elif data == "news_crypto":
        await news_command(query, context)
    elif data == "alert_start":
        # Need to use query.message to reply, as query itself doesn't have .message.reply_text
        await query.message.reply_text("Okay, let's set up a price alert!\n"
                                       "Which coin do you want to monitor? (e.g., BTC, ETH, SOL, XRP, CORE)")
        return COIN_FOR_ALERT # This won't work directly here, i need to integrate with conv handler entry
    # ... more handlers for other buttons

    # Fallback if not handled by conversation handler for alerts
    if data.startswith("alert_cond_"):
        # This is part of the alert conversation, should be handled by `alert_condition_received`
        # If we reach here, it means the conversation state might have been lost or not entered correctly.
        # This is a simplified button handler; complex flows often use ConversationHandler.
        await query.edit_message_text(text=f"Processing: {data}. (Note: Alert setup should be in a conversation)")