import logging
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from telegram.constants import ParseMode
import database as db
import api_clients
from config import DEFAULT_FIAT, NEWS_SOURCES, SUPPORTED_FIAT, CRYPTO_TIPS
from utils import (
    get_coingecko_id, get_display_symbol, format_currency, format_percentage, 
    sanitize_input, validate_amount, validate_price, format_time_ago
)
from datetime import datetime
import asyncio

logger = logging.getLogger(__name__)

# Conversation states
COIN_FOR_ALERT, PRICE_FOR_ALERT, CONDITION_FOR_ALERT, RECURRING_FOR_ALERT = range(4)
FIAT_FOR_SETTINGS = range(1)
EXPERIENCE_LEVEL = range(1)
FEEDBACK_MESSAGE, FEEDBACK_RATING = range(2)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await db.add_user_if_not_exists(user.id)
    
    # Check if user is new
    profile = await db.get_user_profile(user.id)
    is_new_user = profile and profile['total_alerts_created'] == 0
    
    if is_new_user:
        welcome_text = (
            f"🎉 Welcome to CoinSeer, {user.first_name}!\n\n"
            "I'm your advanced crypto companion, designed to help you:\n\n"
            "📈 **Track Real-time Prices** - Get instant price updates\n"
            "🔔 **Smart Alerts** - Price, volume, and trend notifications\n"
            "📊 **Portfolio Management** - Track your investments & PnL\n"
            "📰 **Latest News** - Stay updated with crypto developments\n"
            "🎓 **Learn & Grow** - Educational tips for all experience levels\n"
            "📋 **Advanced Analytics** - Market insights and trends\n\n"
            "Let's start with a quick setup! What's your crypto experience level?"
        )
        keyboard = [
            [InlineKeyboardButton("🌱 Beginner", callback_data="exp_beginner"),
             InlineKeyboardButton("📈 Intermediate", callback_data="exp_intermediate")],
            [InlineKeyboardButton("🚀 Advanced", callback_data="exp_advanced"),
             InlineKeyboardButton("⏭️ Skip Setup", callback_data="exp_skip")]
        ]
    else:
        welcome_text = (
            f"👋 Welcome back, {user.first_name}!\n\n"
            "🚀 **Quick Actions:**\n"
            "• Get prices, set alerts, check news\n"
            "• Manage your portfolio and watchlist\n"
            "• Access educational content\n\n"
            "Type `/help` to see all commands or use the buttons below:"
        )
        keyboard = [
            [InlineKeyboardButton("💰 BTC Price", callback_data="price_btc"),
             InlineKeyboardButton("📰 Crypto News", callback_data="news_crypto")],
            [InlineKeyboardButton("🔔 Set Alert", callback_data="alert_start"),
             InlineKeyboardButton("💼 Portfolio", callback_data="portfolio_view")],
            [InlineKeyboardButton("📊 Top Movers", callback_data="topmovers"),
             InlineKeyboardButton("🎓 Learn", callback_data="learn_tip")]
        ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
    
    if is_new_user:
        return EXPERIENCE_LEVEL

async def experience_level_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "exp_skip":
        await query.edit_message_text(
            "Setup skipped! You can always update your preferences in `/settings`.\n\n"
            "Type `/help` to explore all features. Happy trading! 🚀"
        )
        return ConversationHandler.END
    
    level_map = {
        "exp_beginner": "beginner",
        "exp_intermediate": "intermediate", 
        "exp_advanced": "advanced"
    }
    
    level = level_map.get(query.data, "beginner")
    user_id = query.from_user.id
    
    await db.update_user_experience_level(user_id, level)
    
    level_messages = {
        "beginner": (
            "🌱 **Beginner Level Set!**\n\n"
            "Perfect! I'll provide:\n"
            "• Simple explanations and educational tips\n"
            "• Basic price alerts and portfolio tracking\n"
            "• Beginner-friendly market insights\n\n"
            "💡 **First Tip**: Start by tracking a few major coins like BTC and ETH!\n\n"
            "Try: `/price BTC` or `/watchlist_add BTC`"
        ),
        "intermediate": (
            "📈 **Intermediate Level Set!**\n\n"
            "Great! You'll get:\n"
            "• Advanced alerts (volume spikes, trends)\n"
            "• Detailed market analysis\n"
            "• Portfolio PnL tracking\n\n"
            "💡 **Pro Tip**: Set up volume alerts to catch early market movements!\n\n"
            "Try: `/volume_alert BTC` or `/pnl`"
        ),
        "advanced": (
            "🚀 **Advanced Level Set!**\n\n"
            "Excellent! You'll access:\n"
            "• All premium features and analytics\n"
            "• Complex alert combinations\n"
            "• Professional market insights\n\n"
            "💡 **Expert Tip**: Use multiple alert types to create a comprehensive monitoring system!\n\n"
            "Try: `/topmovers` or `/market BTC`"
        )
    }
    
    await query.edit_message_text(
        level_messages[level],
        parse_mode=ParseMode.MARKDOWN
    )
    return ConversationHandler.END

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    profile = await db.get_user_profile(user_id)
    experience_level = profile['experience_level'] if profile else 'beginner'
    
    basic_commands = (
        "📋 **Essential Commands:**\n\n"
        "💰 `/price <coin>` - Get current price (e.g., `/price BTC`)\n"
        "📊 `/chart <coin> [days]` - Price chart (e.g., `/chart ETH 7`)\n"
        "📰 `/news [keyword]` - Latest crypto news\n"
        "🔔 `/alert` - Set price alerts\n"
        "📋 `/watchlist_add <coin>` - Add to watchlist\n"
        "💼 `/portfolio_add <coin> <amount>` - Add to portfolio\n"
        "⚙️ `/settings` - Configure preferences\n"
        "👤 `/profile` - View your profile\n"
        "🎓 `/learn` - Get crypto education tips\n"
    )
    
    intermediate_commands = (
        "\n📈 **Intermediate Features:**\n"
        "📊 `/volume_alert <coin>` - Volume spike alerts\n"
        "💹 `/pnl` - Portfolio profit/loss analysis\n"
        "🚀 `/topmovers` - Top gainers/losers\n"
        "📊 `/market <coin>` - Detailed market data\n"
        "😨 `/fear_greed` - Market sentiment index\n"
    )
    
    advanced_commands = (
        "\n🚀 **Advanced Features:**\n"
        "🔮 `/predict <coin>` - Price predictions (mock)\n"
        "📈 `/my_alerts` - Manage all alerts\n"
        "🗑️ `/delete_alert <id>` - Remove specific alert\n"
        "💬 `/feedback` - Send feedback to developers\n"
    )
    
    help_text = basic_commands
    if experience_level in ['intermediate', 'advanced']:
        help_text += intermediate_commands
    if experience_level == 'advanced':
        help_text += advanced_commands
    
    help_text += "\n💡 **Tip**: Use inline buttons for easier navigation!"
    
    keyboard = [
        [InlineKeyboardButton("🚀 Quick Start", callback_data="quick_start"),
         InlineKeyboardButton("⚙️ Settings", callback_data="settings_menu")],
        [InlineKeyboardButton("🎓 Learn More", callback_data="learn_tip"),
         InlineKeyboardButton("💬 Feedback", callback_data="feedback_start")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(help_text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)

async def price_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "Please specify a coin symbol or name.\n\n"
            "**Examples:**\n"
            "• `/price BTC`\n"
            "• `/price ethereum`\n"
            "• `/price SOL`"
        )
        return
    
    coin_symbol = sanitize_input(context.args[0])
    if not coin_symbol:
        await update.message.reply_text("Invalid coin symbol. Please try again.")
        return
    
    preferred_fiat = await db.get_user_preferred_fiat(update.effective_user.id)
    cg_coin_id = get_coingecko_id(coin_symbol)
    
    # Send loading message
    loading_msg = await update.message.reply_text(f"⏳ Fetching price for {coin_symbol.upper()}...")
    
    try:
        data = await api_clients.get_crypto_price(cg_coin_id, preferred_fiat)
        
        if data and preferred_fiat in data:
            price = data[preferred_fiat]
            market_cap = data.get(f"{preferred_fiat}_market_cap")
            volume = data.get(f"{preferred_fiat}_24h_vol")
            change_24h = data.get(f"{preferred_fiat}_24h_change")
            
            # Get additional data for advanced users
            profile = await db.get_user_profile(update.effective_user.id)
            experience_level = profile['experience_level'] if profile else 'beginner'
            
            message = (
                f"💰 **{coin_symbol.upper()} Price**\n\n"
                f"**Current Price:** {format_currency(price, preferred_fiat.upper())}\n"
                f"**24h Change:** {format_percentage(change_24h)}\n"
            )
            
            if experience_level in ['intermediate', 'advanced']:
                message += (
                    f"**Market Cap:** {format_currency(market_cap, preferred_fiat.upper(), 0)}\n"
                    f"**24h Volume:** {format_currency(volume, preferred_fiat.upper(), 0)}\n"
                )
            
            # Add quick action buttons
            keyboard = [
                [InlineKeyboardButton(f"📊 Chart", callback_data=f"chart_{coin_symbol}"),
                 InlineKeyboardButton(f"🔔 Set Alert", callback_data=f"alert_coin_{cg_coin_id}")],
                [InlineKeyboardButton(f"➕ Add to Watchlist", callback_data=f"watchlist_add_{cg_coin_id}"),
                 InlineKeyboardButton(f"📰 News", callback_data=f"news_{coin_symbol}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await loading_msg.edit_text(message, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
        else:
            await loading_msg.edit_text(
                f"❌ Couldn't fetch price for **{coin_symbol.upper()}**.\n\n"
                "**Suggestions:**\n"
                "• Check the spelling\n"
                "• Try the full name (e.g., 'bitcoin' instead of 'btc')\n"
                "• Use common symbols like BTC, ETH, SOL"
            )
    except Exception as e:
        logger.error(f"Error in price_command: {e}")
        await loading_msg.edit_text("❌ An error occurred while fetching the price. Please try again.")

async def chart_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "Please specify a coin symbol and optionally the number of days.\n\n"
            "**Examples:**\n"
            "• `/chart BTC` (7 days default)\n"
            "• `/chart ETH 30`\n"
            "• `/chart SOL 1`"
        )
        return
    
    coin_symbol = sanitize_input(context.args[0])
    days = 7  # default
    
    if len(context.args) > 1:
        try:
            days = int(context.args[1])
            if days < 1 or days > 365:
                await update.message.reply_text("Days must be between 1 and 365.")
                return
        except ValueError:
            await update.message.reply_text("Invalid number of days. Using default (7 days).")
    
    preferred_fiat = await db.get_user_preferred_fiat(update.effective_user.id)
    cg_coin_id = get_coingecko_id(coin_symbol)
    
    loading_msg = await update.message.reply_text(f"📊 Generating {days}-day chart for {coin_symbol.upper()}...")
    
    try:
        chart_data = await api_clients.get_market_chart(cg_coin_id, preferred_fiat, days)
        
        if not chart_data or not chart_data.get('prices'):
            await loading_msg.edit_text(f"❌ Couldn't fetch chart data for {coin_symbol.upper()}.")
            return
        
        prices = chart_data['prices']
        volumes = chart_data.get('total_volumes', [])
        
        # Create text-based chart
        display_points = min(10, len(prices))
        step = max(1, len(prices) // display_points)
        selected_prices = prices[::step][-display_points:]
        
        if not selected_prices:
            await loading_msg.edit_text("❌ No price data available for chart.")
            return
        
        max_price = max(price for _, price in selected_prices)
        min_price = min(price for _, price in selected_prices)
        price_range = max_price - min_price
        
        message = f"📊 **{coin_symbol.upper()} {days}-Day Chart ({preferred_fiat.upper()})**\n\n"
        
        for timestamp, price in selected_prices:
            date = datetime.fromtimestamp(timestamp/1000).strftime('%m/%d' if days <= 30 else '%m/%d')
            if price_range > 0:
                bars = int((price - min_price) / price_range * 10)
            else:
                bars = 5
            bar_chart = '█' * max(1, bars) + '░' * (10 - max(1, bars))
            message += f"`{date}` {bar_chart} {format_currency(price, preferred_fiat.upper())}\n"
        
        # Add summary statistics
        first_price = selected_prices[0][1]
        last_price = selected_prices[-1][1]
        change_percent = ((last_price - first_price) / first_price * 100) if first_price > 0 else 0
        
        message += f"\n📈 **Period Change:** {format_percentage(change_percent)}\n"
        message += f"📊 **High:** {format_currency(max_price, preferred_fiat.upper())}\n"
        message += f"📉 **Low:** {format_currency(min_price, preferred_fiat.upper())}"
        
        # Add action buttons
        keyboard = [
            [InlineKeyboardButton("1D", callback_data=f"chart_{coin_symbol}_1"),
             InlineKeyboardButton("7D", callback_data=f"chart_{coin_symbol}_7"),
             InlineKeyboardButton("30D", callback_data=f"chart_{coin_symbol}_30")],
            [InlineKeyboardButton("💰 Price", callback_data=f"price_{coin_symbol}"),
             InlineKeyboardButton("🔔 Alert", callback_data=f"alert_coin_{cg_coin_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await loading_msg.edit_text(message, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
        
    except Exception as e:
        logger.error(f"Error in chart_command: {e}")
        await loading_msg.edit_text("❌ An error occurred while generating the chart. Please try again.")

async def news_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = sanitize_input(" ".join(context.args)) if context.args else "cryptocurrency"
    
    loading_msg = await update.message.reply_text(f"📰 Fetching latest news for '{query}'...")
    
    try:
        articles = await api_clients.get_crypto_news(query=query, page_size=5)
        
        if articles:
            message = f"📰 **Top Crypto News: '{query.title()}'**\n\n"
            
            for i, article in enumerate(articles[:5], 1):
                title = article.get('title', 'No Title')[:80]
                url = article.get('url', '#')
                source_name = article.get('source', {}).get('name', 'Unknown')
                published_at = article.get('publishedAt', '')
                
                # Format time
                time_ago = format_time_ago(published_at) if published_at else 'Unknown time'
                
                message += f"**{i}.** [{title}...]({url})\n"
                message += f"   📅 {time_ago} • 📰 {source_name}\n\n"
            
            # Add action buttons
            keyboard = [
                [InlineKeyboardButton("🔄 Refresh", callback_data=f"news_{query}"),
                 InlineKeyboardButton("📈 Bitcoin News", callback_data="news_bitcoin")],
                [InlineKeyboardButton("⚡ Ethereum News", callback_data="news_ethereum"),
                 InlineKeyboardButton("🌐 General News", callback_data="news_crypto")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await loading_msg.edit_text(
                message, 
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN, 
                disable_web_page_preview=True
            )
        else:
            await loading_msg.edit_text(
                f"📰 No recent news found for '{query}'.\n\n"
                "**Try these keywords:**\n"
                "• bitcoin, ethereum, defi\n"
                "• regulation, adoption\n"
                "• Or use `/news` for general crypto news"
            )
    except Exception as e:
        logger.error(f"Error in news_command: {e}")
        await loading_msg.edit_text("❌ An error occurred while fetching news. Please try again.")

async def fear_greed_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    loading_msg = await update.message.reply_text("😨 Fetching Fear & Greed Index...")
    
    try:
        data = await api_clients.get_fear_greed_index()
        
        if data:
            value = int(data.get('value', 0))
            classification = data.get('value_classification', 'Unknown')
            timestamp = data.get('timestamp', '')
            
            # Create visual representation
            bar_length = 20
            filled_bars = int((value / 100) * bar_length)
            empty_bars = bar_length - filled_bars
            progress_bar = '█' * filled_bars + '░' * empty_bars
            
            # Determine emoji and color
            if value <= 25:
                emoji = "😱"
                description = "Extreme Fear - Potential buying opportunity"
            elif value <= 45:
                emoji = "😰"
                description = "Fear - Market is pessimistic"
            elif value <= 55:
                emoji = "😐"
                description = "Neutral - Market is balanced"
            elif value <= 75:
                emoji = "😊"
                description = "Greed - Market is optimistic"
            else:
                emoji = "🤑"
                description = "Extreme Greed - Potential selling opportunity"
            
            message = (
                f"📊 **Crypto Fear & Greed Index** {emoji}\n\n"
                f"**Current Value:** {value}/100\n"
                f"**Sentiment:** {classification}\n\n"
                f"`{progress_bar}` {value}%\n\n"
                f"💡 **Interpretation:** {description}\n\n"
                f"🕒 Last updated: {format_time_ago(timestamp)}"
            )
            
            keyboard = [
                [InlineKeyboardButton("🔄 Refresh", callback_data="fear_greed"),
                 InlineKeyboardButton("📊 Market Data", callback_data="market_overview")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await loading_msg.edit_text(message, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
        else:
            await loading_msg.edit_text("❌ Couldn't fetch Fear & Greed Index. Please try again later.")
    except Exception as e:
        logger.error(f"Error in fear_greed_command: {e}")
        await loading_msg.edit_text("❌ An error occurred while fetching the Fear & Greed Index.")

# Alert conversation handlers
async def alert_command_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await db.add_user_if_not_exists(update.effective_user.id)
    
    keyboard = [
        [InlineKeyboardButton("₿ Bitcoin", callback_data="alert_coin_bitcoin"),
         InlineKeyboardButton("⟠ Ethereum", callback_data="alert_coin_ethereum")],
        [InlineKeyboardButton("◎ Solana", callback_data="alert_coin_solana"),
         InlineKeyboardButton("🐕 Dogecoin", callback_data="alert_coin_dogecoin")],
        [InlineKeyboardButton("💎 Other Coin", callback_data="alert_coin_other")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🔔 **Set Up Price Alert**\n\n"
        "Which cryptocurrency would you like to monitor?",
        reply_markup=reply_markup
    )
    return COIN_FOR_ALERT

async def alert_coin_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        
        if query.data == 'alert_coin_other':
            await query.message.reply_text(
                "💎 **Custom Coin Alert**\n\n"
                "Please enter the coin symbol or name:\n"
                "Examples: `BTC`, `ethereum`, `SOL`, `DOGE`"
            )
            return COIN_FOR_ALERT
        
        # Extract coin ID from callback data
        cg_coin_id = query.data.replace('alert_coin_', '')
        coin_symbol_display = get_display_symbol(cg_coin_id)
    else:
        # Text input
        coin_input = sanitize_input(update.message.text)
        if not coin_input:
            await update.message.reply_text("Invalid input. Please enter a valid coin symbol.")
            return COIN_FOR_ALERT
            
        cg_coin_id = get_coingecko_id(coin_input)
        coin_symbol_display = coin_input.upper()
    
    # Validate coin by fetching current price
    preferred_fiat = await db.get_user_preferred_fiat(update.effective_user.id)
    current_price_data = await api_clients.get_crypto_price(cg_coin_id, preferred_fiat)
    
    if not current_price_data or preferred_fiat not in current_price_data:
        error_msg = (
            f"❌ Couldn't find '{coin_symbol_display}'.\n\n"
            "**Please try:**\n"
            "• Correct spelling (BTC, ETH, SOL)\n"
            "• Full name (bitcoin, ethereum)\n"
            "• Popular symbols from major exchanges"
        )
        await update.message.reply_text(error_msg)
        return COIN_FOR_ALERT
    
    # Store coin info and show current price
    context.user_data['alert_coin_id'] = cg_coin_id
    context.user_data['alert_coin_symbol_display'] = coin_symbol_display
    
    current_price = current_price_data[preferred_fiat]
    change_24h = current_price_data.get(f"{preferred_fiat}_24h_change", 0)
    
    message = (
        f"✅ **{coin_symbol_display} Selected**\n\n"
        f"**Current Price:** {format_currency(current_price, preferred_fiat.upper())}\n"
        f"**24h Change:** {format_percentage(change_24h)}\n\n"
        f"💰 **What's your target price in {preferred_fiat.upper()}?**\n"
        f"Example: `65000` or `0.50`"
    )
    
    await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
    return PRICE_FOR_ALERT

async def alert_price_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    price_input = sanitize_input(update.message.text)
    is_valid, target_price = validate_price(price_input)
    
    if not is_valid:
        await update.message.reply_text(
            "❌ Invalid price format.\n\n"
            "**Please enter a valid number:**\n"
            "• `65000` (for $65,000)\n"
            "• `0.50` (for $0.50)\n"
            "• `1.25` (for $1.25)"
        )
        return PRICE_FOR_ALERT
    
    context.user_data['alert_target_price'] = target_price
    
    # Get current price for comparison
    coin_id = context.user_data['alert_coin_id']
    preferred_fiat = await db.get_user_preferred_fiat(update.effective_user.id)
    current_price_data = await api_clients.get_crypto_price(coin_id, preferred_fiat)
    current_price = current_price_data[preferred_fiat] if current_price_data else 0
    
    # Suggest appropriate condition based on target vs current price
    if target_price > current_price:
        suggested_condition = "above"
        suggestion_text = f"💡 Suggested: Alert when price goes **above** {format_currency(target_price, preferred_fiat.upper())} (current: {format_currency(current_price, preferred_fiat.upper())})"
    else:
        suggested_condition = "below"
        suggestion_text = f"💡 Suggested: Alert when price goes **below** {format_currency(target_price, preferred_fiat.upper())} (current: {format_currency(current_price, preferred_fiat.upper())})"
    
    keyboard = [
        [InlineKeyboardButton(f"📈 Above {format_currency(target_price, preferred_fiat.upper())}", 
                             callback_data="alert_cond_above")],
        [InlineKeyboardButton(f"📉 Below {format_currency(target_price, preferred_fiat.upper())}", 
                             callback_data="alert_cond_below")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    message = (
        f"🎯 **Target Price Set:** {format_currency(target_price, preferred_fiat.upper())}\n\n"
        f"{suggestion_text}\n\n"
        "**When should I notify you?**"
    )
    
    await update.message.reply_text(message, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
    return CONDITION_FOR_ALERT

async def alert_condition_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    condition = query.data.split('_')[-1]  # 'above' or 'below'
    context.user_data['alert_condition'] = condition
    
    keyboard = [
        [InlineKeyboardButton("🔔 One-time Alert", callback_data="alert_recurring_false")],
        [InlineKeyboardButton("🔄 Recurring Alert", callback_data="alert_recurring_true")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    message = (
        f"🔔 **Alert Type Selection**\n\n"
        "**One-time Alert:** Notify once, then automatically disable\n"
        "**Recurring Alert:** Keep notifying every time the condition is met\n\n"
        "Which type would you prefer?"
    )
    
    await query.edit_message_text(message, reply_markup=reply_markup)
    return RECURRING_FOR_ALERT

async def alert_recurring_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    recurring = query.data.split('_')[-1] == 'true'
    user_id = query.from_user.id
    
    # Get stored data
    coin_id = context.user_data['alert_coin_id']
    coin_symbol_display = context.user_data['alert_coin_symbol_display']
    target_price = context.user_data['alert_target_price']
    condition = context.user_data['alert_condition']
    
    # Save alert to database
    success = await db.add_price_alert(user_id, coin_id, target_price, condition, recurring)
    
    if success:
        preferred_fiat = await db.get_user_preferred_fiat(user_id)
        alert_type = "Recurring" if recurring else "One-time"
        
        message = (
            f"✅ **Alert Created Successfully!**\n\n"
            f"**Coin:** {coin_symbol_display}\n"
            f"**Condition:** Price goes {condition} {format_currency(target_price, preferred_fiat.upper())}\n"
            f"**Type:** {alert_type}\n\n"
            f"🔔 You'll be notified when the condition is met!\n\n"
            f"Use `/my_alerts` to view all your alerts."
        )
        
        keyboard = [
            [InlineKeyboardButton("📋 My Alerts", callback_data="my_alerts"),
             InlineKeyboardButton("➕ Add Another", callback_data="alert_start")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(message, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
    else:
        await query.edit_message_text(
            "❌ **Failed to create alert.**\n\n"
            "Please try again or contact support if the problem persists."
        )
    
    # Clean up user data
    context.user_data.clear()
    return ConversationHandler.END

async def alert_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Alert setup cancelled.")
    context.user_data.clear()
    return ConversationHandler.END

async def my_alerts_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    alerts = await db.get_active_alerts()
    user_alerts = [alert for alert in alerts if alert['user_id'] == user_id]
    
    if not user_alerts:
        message = (
            "📋 **No Active Alerts**\n\n"
            "You don't have any price alerts set up yet.\n\n"
            "Use `/alert` to create your first alert!"
        )
        keyboard = [
            [InlineKeyboardButton("🔔 Create Alert", callback_data="alert_start")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(message, reply_markup=reply_markup)
        return
    
    message = f"📋 **Your Active Alerts ({len(user_alerts)})**\n\n"
    
    for i, alert in enumerate(user_alerts, 1):
        display_symbol = get_display_symbol(alert['coin_id'])
        alert_type = "🔄 Recurring" if alert['is_recurring'] else "🔔 One-time"
        
        message += (
            f"**{i}.** {display_symbol}\n"
            f"   Notify if price {alert['condition']} {format_currency(alert['target_price'], alert['preferred_fiat'].upper())}\n"
            f"   {alert_type} • ID: `{alert['alert_id']}`\n\n"
        )
    
    message += "💡 Use `/delete_alert <ID>` to remove an alert"
    
    keyboard = [
        [InlineKeyboardButton("➕ Add New Alert", callback_data="alert_start"),
         InlineKeyboardButton("🔄 Refresh", callback_data="my_alerts")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(message, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)

async def delete_alert_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "❌ Please specify an alert ID.\n\n"
            "**Usage:** `/delete_alert <ID>`\n"
            "**Example:** `/delete_alert 123`\n\n"
            "Use `/my_alerts` to see your alert IDs."
        )
        return
    
    try:
        alert_id = int(sanitize_input(context.args[0]))
        user_id = update.effective_user.id
        
        success = await db.delete_alert(user_id, alert_id)
        
        if success:
            await update.message.reply_text(
                f"✅ **Alert {alert_id} deleted successfully!**\n\n"
                "Use `/my_alerts` to view your remaining alerts."
            )
        else:
            await update.message.reply_text(
                f"❌ **Alert {alert_id} not found.**\n\n"
                "Please check the ID and try again.\n"
                "Use `/my_alerts` to see your active alerts."
            )
    except ValueError:
        await update.message.reply_text(
            "❌ Invalid alert ID format.\n\n"
            "Please provide a valid number.\n"
            "Use `/my_alerts` to see your alert IDs."
        )

# Volume alert command
async def volume_alert_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "📊 **Volume Spike Alerts**\n\n"
            "Get notified when trading volume increases significantly!\n\n"
            "**Usage:** `/volume_alert <coin> [multiplier]`\n"
            "**Examples:**\n"
            "• `/volume_alert BTC` (2x volume increase)\n"
            "• `/volume_alert ETH 3` (3x volume increase)"
        )
        return
    
    coin_symbol = sanitize_input(context.args[0])
    multiplier = 2.0  # default
    
    if len(context.args) > 1:
        try:
            multiplier = float(context.args[1])
            if multiplier < 1.5 or multiplier > 10:
                await update.message.reply_text("Multiplier must be between 1.5 and 10.")
                return
        except ValueError:
            await update.message.reply_text("Invalid multiplier. Using default (2x).")
    
    cg_coin_id = get_coingecko_id(coin_symbol)
    user_id = update.effective_user.id
    
    # Validate coin
    preferred_fiat = await db.get_user_preferred_fiat(user_id)
    price_data = await api_clients.get_crypto_price(cg_coin_id, preferred_fiat)
    
    if not price_data:
        await update.message.reply_text(f"❌ Couldn't find '{coin_symbol}'. Please check the symbol.")
        return
    
    success = await db.add_volume_alert(user_id, cg_coin_id, multiplier)
    
    if success:
        display_symbol = get_display_symbol(cg_coin_id)
        await update.message.reply_text(
            f"✅ **Volume Alert Created!**\n\n"
            f"**Coin:** {display_symbol}\n"
            f"**Trigger:** {multiplier}x volume increase\n\n"
            f"🔔 You'll be notified when 24h volume increases by {multiplier}x or more!"
        )
    else:
        await update.message.reply_text("❌ Failed to create volume alert. Please try again.")

# Watchlist commands
async def watchlist_add_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await db.add_user_if_not_exists(user_id)
    
    if not context.args:
        await update.message.reply_text(
            "📋 **Add to Watchlist**\n\n"
            "**Usage:** `/watchlist_add <coin>`\n"
            "**Examples:**\n"
            "• `/watchlist_add BTC`\n"
            "• `/watchlist_add ethereum`\n"
            "• `/watchlist_add SOL`"
        )
        return
    
    coin_symbol = sanitize_input(context.args[0])
    cg_coin_id = get_coingecko_id(coin_symbol)
    
    # Validate coin
    preferred_fiat = await db.get_user_preferred_fiat(user_id)
    price_data = await api_clients.get_crypto_price(cg_coin_id, preferred_fiat)
    
    if not price_data:
        await update.message.reply_text(f"❌ Couldn't find '{coin_symbol}'. Please check the symbol.")
        return
    
    response_message = await db.add_to_watchlist(user_id, cg_coin_id)
    
    # Add quick action buttons
    keyboard = [
        [InlineKeyboardButton("📋 View Watchlist", callback_data="watchlist_view"),
         InlineKeyboardButton("💰 Get Price", callback_data=f"price_{coin_symbol}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(response_message, reply_markup=reply_markup)

async def watchlist_remove_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not context.args:
        await update.message.reply_text(
            "📋 **Remove from Watchlist**\n\n"
            "**Usage:** `/watchlist_remove <coin>`\n"
            "**Example:** `/watchlist_remove BTC`"
        )
        return
    
    coin_symbol = sanitize_input(context.args[0])
    cg_coin_id = get_coingecko_id(coin_symbol)
    
    response_message = await db.remove_from_watchlist(user_id, cg_coin_id)
    await update.message.reply_text(response_message)

async def watchlist_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    watchlist_coins = await db.get_watchlist(user_id)
    
    if not watchlist_coins:
        message = (
            "📋 **Your Watchlist is Empty**\n\n"
            "Add coins to track their prices easily!\n\n"
            "**Usage:** `/watchlist_add <coin>`\n"
            "**Example:** `/watchlist_add BTC`"
        )
        keyboard = [
            [InlineKeyboardButton("➕ Add BTC", callback_data="watchlist_add_bitcoin"),
             InlineKeyboardButton("➕ Add ETH", callback_data="watchlist_add_ethereum")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(message, reply_markup=reply_markup)
        return
    
    preferred_fiat = await db.get_user_preferred_fiat(user_id)
    loading_msg = await update.message.reply_text("📋 Loading watchlist prices...")
    
    try:
        # Fetch prices for all coins at once
        price_data = await api_clients.get_crypto_price(','.join(watchlist_coins), preferred_fiat)
        
        message = f"📋 **Your Watchlist ({len(watchlist_coins)} coins)**\n\n"
        
        for coin_id in watchlist_coins:
            display_symbol = get_display_symbol(coin_id)
            
            if price_data and coin_id in price_data and preferred_fiat in price_data[coin_id]:
                coin_data = price_data[coin_id]
                price = coin_data[preferred_fiat]
                change_24h = coin_data.get(f"{preferred_fiat}_24h_change", 0)
                
                change_emoji = "📈" if change_24h >= 0 else "📉"
                message += f"**{display_symbol}:** {format_currency(price, preferred_fiat.upper())} {change_emoji} {format_percentage(change_24h)}\n"
            else:
                message += f"**{display_symbol}:** ❌ Error fetching price\n"
        
        keyboard = [
            [InlineKeyboardButton("🔄 Refresh", callback_data="watchlist_view"),
             InlineKeyboardButton("➕ Add Coin", callback_data="watchlist_add_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await loading_msg.edit_text(message, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
        
    except Exception as e:
        logger.error(f"Error in watchlist_command: {e}")
        await loading_msg.edit_text("❌ Error loading watchlist. Please try again.")

# Portfolio commands
async def portfolio_add_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await db.add_user_if_not_exists(user_id)
    
    if len(context.args) < 2:
        await update.message.reply_text(
            "💼 **Add to Portfolio**\n\n"
            "**Usage:** `/portfolio_add <coin> <amount>`\n"
            "**Examples:**\n"
            "• `/portfolio_add BTC 0.5`\n"
            "• `/portfolio_add ETH 2.5`\n"
            "• `/portfolio_add SOL 100`"
        )
        return
    
    coin_symbol = sanitize_input(context.args[0])
    amount_str = sanitize_input(context.args[1])
    
    is_valid, amount = validate_amount(amount_str)
    if not is_valid:
        await update.message.reply_text(
            "❌ Invalid amount format.\n\n"
            "Please enter a positive number.\n"
            "**Examples:** `0.5`, `2.5`, `100`"
        )
        return
    
    cg_coin_id = get_coingecko_id(coin_symbol)
    
    # Validate coin and get current price
    preferred_fiat = await db.get_user_preferred_fiat(user_id)
    price_data = await api_clients.get_crypto_price(cg_coin_id, preferred_fiat)
    
    if not price_data or preferred_fiat not in price_data:
        await update.message.reply_text(f"❌ Couldn't find '{coin_symbol}'. Please check the symbol.")
        return
    
    current_price = price_data[preferred_fiat]
    
    # Add to portfolio
    response_message = await db.add_to_portfolio(user_id, cg_coin_id, amount)
    
    # Add transaction record for PnL tracking
    await db.add_portfolio_transaction(user_id, cg_coin_id, 'buy', amount, current_price)
    
    display_symbol = get_display_symbol(cg_coin_id)
    total_value = amount * current_price
    
    message = (
        f"✅ **Added to Portfolio**\n\n"
        f"**Coin:** {display_symbol}\n"
        f"**Amount:** {amount:,.4f}\n"
        f"**Current Price:** {format_currency(current_price, preferred_fiat.upper())}\n"
        f"**Total Value:** {format_currency(total_value, preferred_fiat.upper())}\n\n"
        f"{response_message}"
    )
    
    keyboard = [
        [InlineKeyboardButton("💼 View Portfolio", callback_data="portfolio_view"),
         InlineKeyboardButton("📊 PnL Analysis", callback_data="pnl_view")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(message, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)

async def portfolio_remove_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not context.args:
        await update.message.reply_text(
            "💼 **Remove from Portfolio**\n\n"
            "**Usage:** `/portfolio_remove <coin>`\n"
            "**Example:** `/portfolio_remove BTC`"
        )
        return
    
    coin_symbol = sanitize_input(context.args[0])
    cg_coin_id = get_coingecko_id(coin_symbol)
    
    response_message = await db.remove_from_portfolio(user_id, cg_coin_id)
    await update.message.reply_text(response_message)

async def portfolio_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    portfolio = await db.get_portfolio(user_id)
    
    if not portfolio:
        message = (
            "💼 **Your Portfolio is Empty**\n\n"
            "Start tracking your crypto investments!\n\n"
            "**Usage:** `/portfolio_add <coin> <amount>`\n"
            "**Example:** `/portfolio_add BTC 0.5`"
        )
        keyboard = [
            [InlineKeyboardButton("➕ Add BTC", callback_data="portfolio_add_btc"),
             InlineKeyboardButton("➕ Add ETH", callback_data="portfolio_add_eth")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(message, reply_markup=reply_markup)
        return
    
    preferred_fiat = await db.get_user_preferred_fiat(user_id)
    loading_msg = await update.message.reply_text("💼 Calculating portfolio value...")
    
    try:
        # Get current prices for all portfolio coins
        coin_ids = [coin_id for coin_id, _ in portfolio]
        price_data = await api_clients.get_crypto_price(','.join(coin_ids), preferred_fiat)
        
        message = f"💼 **Your Portfolio ({len(portfolio)} coins)**\n\n"
        total_value = 0
        
        for coin_id, amount in portfolio:
            display_symbol = get_display_symbol(coin_id)
            
            if price_data and coin_id in price_data and preferred_fiat in price_data[coin_id]:
                coin_data = price_data[coin_id]
                price = coin_data[preferred_fiat]
                value = price * amount
                total_value += value
                change_24h = coin_data.get(f"{preferred_fiat}_24h_change", 0)
                
                message += (
                    f"**{display_symbol}**\n"
                    f"  Amount: {amount:,.4f}\n"
                    f"  Price: {format_currency(price, preferred_fiat.upper())} {format_percentage(change_24h)}\n"
                    f"  Value: {format_currency(value, preferred_fiat.upper())}\n\n"
                )
            else:
                message += f"**{display_symbol}:** {amount:,.4f} units (❌ Price error)\n\n"
        
        message += f"💰 **Total Portfolio Value:** {format_currency(total_value, preferred_fiat.upper())}"
        
        keyboard = [
            [InlineKeyboardButton("🔄 Refresh", callback_data="portfolio_view"),
             InlineKeyboardButton("📊 PnL Analysis", callback_data="pnl_view")],
            [InlineKeyboardButton("➕ Add Coin", callback_data="portfolio_add_menu"),
             InlineKeyboardButton("📈 Performance", callback_data="portfolio_performance")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await loading_msg.edit_text(message, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
        
    except Exception as e:
        logger.error(f"Error in portfolio_command: {e}")
        await loading_msg.edit_text("❌ Error loading portfolio. Please try again.")

# PnL command
async def pnl_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    transactions = await db.get_portfolio_transactions(user_id)
    
    if not transactions:
        await update.message.reply_text(
            "📊 **No Transaction History**\n\n"
            "Add coins to your portfolio to track PnL!\n\n"
            "Use `/portfolio_add <coin> <amount>` to get started."
        )
        return
    
    loading_msg = await update.message.reply_text("📊 Calculating profit/loss...")
    
    try:
        preferred_fiat = await db.get_user_preferred_fiat(user_id)
        
        # Group transactions by coin
        coin_data = {}
        for tx in transactions:
            coin_id = tx['coin_id']
            if coin_id not in coin_data:
                coin_data[coin_id] = {'buy_amount': 0, 'buy_value': 0, 'sell_amount': 0, 'sell_value': 0}
            
            if tx['transaction_type'] == 'buy':
                coin_data[coin_id]['buy_amount'] += tx['amount']
                coin_data[coin_id]['buy_value'] += tx['amount'] * tx['price_per_unit']
            else:  # sell
                coin_data[coin_id]['sell_amount'] += tx['amount']
                coin_data[coin_id]['sell_value'] += tx['amount'] * tx['price_per_unit']
        
        # Get current prices
        coin_ids = list(coin_data.keys())
        price_data = await api_clients.get_crypto_price(','.join(coin_ids), preferred_fiat)
        
        message = "📊 **Profit/Loss Analysis**\n\n"
        total_invested = 0
        total_current_value = 0
        
        for coin_id, data in coin_data.items():
            display_symbol = get_display_symbol(coin_id)
            current_amount = data['buy_amount'] - data['sell_amount']
            
            if current_amount > 0:  # Still holding
                avg_buy_price = data['buy_value'] / data['buy_amount'] if data['buy_amount'] > 0 else 0
                
                if price_data and coin_id in price_data:
                    current_price = price_data[coin_id][preferred_fiat]
                    current_value = current_amount * current_price
                    invested_value = current_amount * avg_buy_price
                    
                    pnl = current_value - invested_value
                    pnl_percent = (pnl / invested_value * 100) if invested_value > 0 else 0
                    
                    total_invested += invested_value
                    total_current_value += current_value
                    
                    pnl_emoji = "📈" if pnl >= 0 else "📉"
                    message += (
                        f"**{display_symbol}**\n"
                        f"  Holding: {current_amount:,.4f}\n"
                        f"  Avg Buy: {format_currency(avg_buy_price, preferred_fiat.upper())}\n"
                        f"  Current: {format_currency(current_price, preferred_fiat.upper())}\n"
                        f"  PnL: {format_currency(pnl, preferred_fiat.upper())} ({pnl_percent:+.1f}%) {pnl_emoji}\n\n"
                    )
        
        # Total PnL
        total_pnl = total_current_value - total_invested
        total_pnl_percent = (total_pnl / total_invested * 100) if total_invested > 0 else 0
        total_emoji = "📈" if total_pnl >= 0 else "📉"
        
        message += (
            f"💰 **Total Invested:** {format_currency(total_invested, preferred_fiat.upper())}\n"
            f"💎 **Current Value:** {format_currency(total_current_value, preferred_fiat.upper())}\n"
            f"📊 **Total PnL:** {format_currency(total_pnl, preferred_fiat.upper())} ({total_pnl_percent:+.1f}%) {total_emoji}"
        )
        
        keyboard = [
            [InlineKeyboardButton("🔄 Refresh", callback_data="pnl_view"),
             InlineKeyboardButton("💼 Portfolio", callback_data="portfolio_view")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await loading_msg.edit_text(message, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
        
    except Exception as e:
        logger.error(f"Error in pnl_command: {e}")
        await loading_msg.edit_text("❌ Error calculating PnL. Please try again.")

# Market and analysis commands
async def market_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "📊 **Market Data**\n\n"
            "**Usage:** `/market <coin>`\n"
            "**Examples:**\n"
            "• `/market BTC`\n"
            "• `/market ethereum`\n"
            "• `/market SOL`"
        )
        return
    
    coin_symbol = sanitize_input(context.args[0])
    cg_coin_id = get_coingecko_id(coin_symbol)
    preferred_fiat = await db.get_user_preferred_fiat(update.effective_user.id)
    
    loading_msg = await update.message.reply_text(f"📊 Fetching market data for {coin_symbol.upper()}...")
    
    try:
        data = await api_clients.get_coin_details(cg_coin_id)
        
        if not data or 'market_data' not in data:
            await loading_msg.edit_text(f"❌ Couldn't fetch market data for {coin_symbol.upper()}.")
            return
        
        market_data = data['market_data']
        display_symbol = get_display_symbol(cg_coin_id)
        
        price = market_data['current_price'][preferred_fiat]
        market_cap = market_data['market_cap'][preferred_fiat]
        volume = market_data['total_volume'][preferred_fiat]
        circulating_supply = market_data.get('circulating_supply', 0)
        total_supply = market_data.get('total_supply', 0)
        max_supply = market_data.get('max_supply', 0)
        
        # Price changes
        change_24h = market_data.get('price_change_percentage_24h', 0)
        change_7d = market_data.get('price_change_percentage_7d', 0)
        change_30d = market_data.get('price_change_percentage_30d', 0)
        
        # All-time high/low
        ath = market_data.get('ath', {}).get(preferred_fiat, 0)
        atl = market_data.get('atl', {}).get(preferred_fiat, 0)
        
        message = (
            f"📊 **{display_symbol} Market Analysis**\n\n"
            f"💰 **Price:** {format_currency(price, preferred_fiat.upper())}\n"
            f"📈 **24h:** {format_percentage(change_24h)}\n"
            f"📊 **7d:** {format_percentage(change_7d)}\n"
            f"📅 **30d:** {format_percentage(change_30d)}\n\n"
            f"📈 **Market Cap:** {format_currency(market_cap, preferred_fiat.upper(), 0)}\n"
            f"📉 **24h Volume:** {format_currency(volume, preferred_fiat.upper(), 0)}\n\n"
            f"🔄 **Circulating:** {circulating_supply:,.0f}\n"
        )
        
        if total_supply > 0:
            message += f"🌐 **Total Supply:** {total_supply:,.0f}\n"
        if max_supply > 0:
            message += f"🔝 **Max Supply:** {max_supply:,.0f}\n"
        
        message += f"\n🚀 **ATH:** {format_currency(ath, preferred_fiat.upper())}\n"
        message += f"📉 **ATL:** {format_currency(atl, preferred_fiat.upper())}"
        
        keyboard = [
            [InlineKeyboardButton("📊 Chart", callback_data=f"chart_{coin_symbol}"),
             InlineKeyboardButton("🔔 Alert", callback_data=f"alert_coin_{cg_coin_id}")],
            [InlineKeyboardButton("📰 News", callback_data=f"news_{coin_symbol}"),
             InlineKeyboardButton("➕ Watchlist", callback_data=f"watchlist_add_{cg_coin_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await loading_msg.edit_text(message, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
        
    except Exception as e:
        logger.error(f"Error in market_command: {e}")
        await loading_msg.edit_text("❌ Error fetching market data. Please try again.")

async def topmovers_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    preferred_fiat = await db.get_user_preferred_fiat(update.effective_user.id)
    loading_msg = await update.message.reply_text(f"🚀 Fetching top movers in {preferred_fiat.upper()}...")
    
    try:
        movers = await api_clients.get_top_movers(preferred_fiat, limit=10)
        
        if not movers:
            await loading_msg.edit_text("❌ Couldn't fetch top movers. Please try again.")
            return
        
        # Separate gainers and losers
        gainers = [coin for coin in movers if coin.get('price_change_percentage_24h', 0) > 0][:5]
        losers = [coin for coin in movers if coin.get('price_change_percentage_24h', 0) < 0][-5:]
        
        message = f"🚀 **Top Movers (24h, {preferred_fiat.upper()})**\n\n"
        
        if gainers:
            message += "📈 **Top Gainers:**\n"
            for i, coin in enumerate(gainers, 1):
                symbol = get_display_symbol(coin['id'])
                price = coin['current_price']
                change_24h = coin['price_change_percentage_24h']
                message += f"{i}. **{symbol}**: {format_currency(price, preferred_fiat.upper())} {format_percentage(change_24h)}\n"
        
        if losers:
            message += "\n📉 **Top Losers:**\n"
            for i, coin in enumerate(losers, 1):
                symbol = get_display_symbol(coin['id'])
                price = coin['current_price']
                change_24h = coin['price_change_percentage_24h']
                message += f"{i}. **{symbol}**: {format_currency(price, preferred_fiat.upper())} {format_percentage(change_24h)}\n"
        
        keyboard = [
            [InlineKeyboardButton("🔄 Refresh", callback_data="topmovers"),
             InlineKeyboardButton("😨 Fear & Greed", callback_data="fear_greed")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await loading_msg.edit_text(message, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
        
    except Exception as e:
        logger.error(f"Error in topmovers_command: {e}")
        await loading_msg.edit_text("❌ Error fetching top movers. Please try again.")

async def predict_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "🔮 **Price Prediction (Mock)**\n\n"
            "**Usage:** `/predict <coin>`\n"
            "**Examples:**\n"
            "• `/predict BTC`\n"
            "• `/predict ETH`\n\n"
            "⚠️ **Disclaimer:** These are mock predictions for demonstration only!"
        )
        return
    
    coin_symbol = sanitize_input(context.args[0])
    preferred_fiat = await db.get_user_preferred_fiat(update.effective_user.id)
    cg_coin_id = get_coingecko_id(coin_symbol)
    
    loading_msg = await update.message.reply_text(f"🔮 Analyzing {coin_symbol.upper()} trends...")
    
    try:
        price_data = await api_clients.get_crypto_price(cg_coin_id, preferred_fiat)
        
        if not price_data or preferred_fiat not in price_data:
            await loading_msg.edit_text(f"❌ Couldn't fetch data for {coin_symbol.upper()}.")
            return
        
        current_price = price_data[preferred_fiat]
        change_24h = price_data.get(f"{preferred_fiat}_24h_change", 0)
        
        # Mock prediction algorithm (for demonstration)
        import hashlib
        seed = int(hashlib.md5(coin_symbol.encode()).hexdigest()[:8], 16)
        random.seed(seed)
        
        # Generate mock predictions
        predictions = {
            "1h": random.uniform(-2, 2),
            "24h": random.uniform(-8, 8),
            "7d": random.uniform(-15, 15),
            "30d": random.uniform(-25, 25)
        }
        
        display_symbol = get_display_symbol(cg_coin_id)
        
        message = (
            f"🔮 **Mock Price Prediction: {display_symbol}**\n\n"
            f"**Current Price:** {format_currency(current_price, preferred_fiat.upper())}\n"
            f"**24h Change:** {format_percentage(change_24h)}\n\n"
            f"**Predictions:**\n"
        )
        
        for timeframe, change in predictions.items():
            predicted_price = current_price * (1 + change / 100)
            emoji = "📈" if change > 0 else "📉" if change < 0 else "➡️"
            message += f"{emoji} **{timeframe}:** {format_currency(predicted_price, preferred_fiat.upper())} ({change:+.1f}%)\n"
        
        message += (
            f"\n⚠️ **Disclaimer:** These are mock predictions for demonstration purposes only. "
            f"Real trading decisions should be based on thorough research and analysis."
        )
        
        keyboard = [
            [InlineKeyboardButton("📊 Real Data", callback_data=f"market_{coin_symbol}"),
             InlineKeyboardButton("📈 Chart", callback_data=f"chart_{coin_symbol}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await loading_msg.edit_text(message, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
        
    except Exception as e:
        logger.error(f"Error in predict_command: {e}")
        await loading_msg.edit_text("❌ Error generating prediction. Please try again.")

# Educational and user experience commands
async def learn_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    profile = await db.get_user_profile(user_id)
    experience_level = profile['experience_level'] if profile else 'beginner'
    
    # Select appropriate tip based on experience level
    if experience_level == 'beginner':
        tips = CRYPTO_TIPS[:5]  # Basic tips
    elif experience_level == 'intermediate':
        tips = CRYPTO_TIPS[3:8]  # Intermediate tips
    else:
        tips = CRYPTO_TIPS[5:]  # Advanced tips
    
    tip = random.choice(tips)
    
    keyboard = [
        [InlineKeyboardButton("💡 Another Tip", callback_data="learn_tip"),
         InlineKeyboardButton("📊 Market Basics", callback_data="learn_market")],
        [InlineKeyboardButton("🔔 Alert Guide", callback_data="learn_alerts"),
         InlineKeyboardButton("💼 Portfolio Tips", callback_data="learn_portfolio")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    message = f"🎓 **Crypto Education**\n\n{tip}\n\n💡 Keep learning to improve your crypto knowledge!"
    
    await update.message.reply_text(message, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)

async def profile_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    
    profile = await db.get_user_profile(user_id)
    preferred_fiat = await db.get_user_preferred_fiat(user_id)
    
    if not profile:
        await update.message.reply_text("❌ Profile not found. Please use /start to initialize.")
        return
    
    # Get user statistics
    alerts = await db.get_active_alerts()
    user_alerts = len([a for a in alerts if a['user_id'] == user_id])
    
    watchlist = await db.get_watchlist(user_id)
    portfolio = await db.get_portfolio(user_id)
    
    experience_emoji = {
        'beginner': '🌱',
        'intermediate': '📈',
        'advanced': '🚀'
    }
    
    message = (
        f"👤 **Your CoinSeer Profile**\n\n"
        f"**Name:** {user.first_name}\n"
        f"**Experience:** {experience_emoji.get(profile['experience_level'], '🌱')} {profile['experience_level'].title()}\n"
        f"**Preferred Currency:** {preferred_fiat.upper()}\n"
        f"**Member Since:** {format_time_ago(profile['join_date'])}\n\n"
        f"📊 **Statistics:**\n"
        f"🔔 Active Alerts: {user_alerts}\n"
        f"📋 Watchlist Coins: {len(watchlist)}\n"
        f"💼 Portfolio Coins: {len(portfolio)}\n"
        f"🎯 Total Alerts Created: {profile['total_alerts_created']}\n"
    )
    
    keyboard = [
        [InlineKeyboardButton("⚙️ Settings", callback_data="settings_menu"),
         InlineKeyboardButton("🎓 Change Level", callback_data="change_experience")],
        [InlineKeyboardButton("📊 My Stats", callback_data="user_stats"),
         InlineKeyboardButton("💬 Feedback", callback_data="feedback_start")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(message, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)

# Settings conversation handler
async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("💰 USD", callback_data="set_fiat_usd"),
         InlineKeyboardButton("💶 EUR", callback_data="set_fiat_eur"),
         InlineKeyboardButton("💷 GBP", callback_data="set_fiat_gbp")],
        [InlineKeyboardButton("💴 JPY", callback_data="set_fiat_jpy"),
         InlineKeyboardButton("💵 AUD", callback_data="set_fiat_aud")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    current_fiat = await db.get_user_preferred_fiat(update.effective_user.id)
    
    message = (
        f"⚙️ **Settings**\n\n"
        f"**Current Currency:** {current_fiat.upper()}\n\n"
        "Select your preferred currency for prices and alerts:"
    )
    
    await update.message.reply_text(message, reply_markup=reply_markup)
    return FIAT_FOR_SETTINGS

async def settings_fiat_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    fiat = query.data.split('_')[-1]
    user_id = query.from_user.id
    
    success = await db.set_user_preferred_fiat(user_id, fiat)
    
    if success:
        message = (
            f"✅ **Currency Updated!**\n\n"
            f"Your preferred currency is now **{fiat.upper()}**.\n\n"
            "All prices and alerts will use this currency."
        )
    else:
        message = f"❌ Invalid currency. Supported currencies: {', '.join(SUPPORTED_FIAT)}"
    
    await query.edit_message_text(message, parse_mode=ParseMode.MARKDOWN)
    return ConversationHandler.END

# Feedback system
async def feedback_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = (
        "💬 **Send Feedback**\n\n"
        "Help us improve CoinSeer! Please share:\n"
        "• Feature requests\n"
        "• Bug reports\n"
        "• General suggestions\n\n"
        "Type your feedback message:"
    )
    
    await update.message.reply_text(message)
    return FEEDBACK_MESSAGE

async def feedback_message_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    feedback_text = sanitize_input(update.message.text)
    
    if not feedback_text or len(feedback_text) < 10:
        await update.message.reply_text(
            "❌ Please provide more detailed feedback (at least 10 characters)."
        )
        return FEEDBACK_MESSAGE
    
    context.user_data['feedback_message'] = feedback_text
    
    keyboard = [
        [InlineKeyboardButton("⭐", callback_data="rating_1"),
         InlineKeyboardButton("⭐⭐", callback_data="rating_2"),
         InlineKeyboardButton("⭐⭐⭐", callback_data="rating_3")],
        [InlineKeyboardButton("⭐⭐⭐⭐", callback_data="rating_4"),
         InlineKeyboardButton("⭐⭐⭐⭐⭐", callback_data="rating_5")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "⭐ **Rate Your Experience**\n\n"
        "How would you rate CoinSeer overall?",
        reply_markup=reply_markup
    )
    return FEEDBACK_RATING

async def feedback_rating_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    rating = int(query.data.split('_')[1])
    feedback_message = context.user_data.get('feedback_message', '')
    user_id = query.from_user.id
    
    success = await db.add_feedback(user_id, feedback_message, rating)
    
    if success:
        message = (
            f"✅ **Thank You for Your Feedback!**\n\n"
            f"**Rating:** {'⭐' * rating}\n"
            f"**Message:** {feedback_message[:100]}...\n\n"
            "Your feedback helps us improve CoinSeer for everyone! 🚀"
        )
    else:
        message = "❌ Failed to save feedback. Please try again."
    
    await query.edit_message_text(message, parse_mode=ParseMode.MARKDOWN)
    context.user_data.clear()
    return ConversationHandler.END

# Callback query handler for inline buttons
async def button_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    try:
        # Route callback data to appropriate handlers
        if data == "price_btc":
            context.args = ["BTC"]
            await price_command(query, context)
        elif data == "news_crypto":
            context.args = []
            await news_command(query, context)
        elif data.startswith("news_"):
            keyword = data.split("_", 1)[1]
            context.args = [keyword]
            await news_command(query, context)
        elif data == "portfolio_view":
            await portfolio_command(query, context)
        elif data == "watchlist_view":
            await watchlist_command(query, context)
        elif data == "my_alerts":
            await my_alerts_command(query, context)
        elif data == "topmovers":
            await topmovers_command(query, context)
        elif data == "fear_greed":
            await fear_greed_command(query, context)
        elif data == "pnl_view":
            await pnl_command(query, context)
        elif data == "learn_tip":
            await learn_command(query, context)
        elif data.startswith("price_"):
            coin = data.split("_", 1)[1]
            context.args = [coin]
            await price_command(query, context)
        elif data.startswith("chart_"):
            parts = data.split("_")
            coin = parts[1]
            days = int(parts[2]) if len(parts) > 2 else 7
            context.args = [coin, str(days)]
            await chart_command(query, context)
        elif data.startswith("market_"):
            coin = data.split("_", 1)[1]
            context.args = [coin]
            await market_command(query, context)
        elif data == "alert_start":
            await alert_command_start(query, context)
        elif data.startswith("alert_coin_") and data != "alert_coin_other":
            # Handle coin selection for alerts
            context.user_data['callback_query'] = query
            await alert_coin_received(query, context)
        elif data.startswith("watchlist_add_"):
            coin_id = data.split("_", 2)[2]
            symbol = get_display_symbol(coin_id)
            context.args = [symbol]
            await watchlist_add_command(query, context)
        elif data.startswith("set_fiat_"):
            context.user_data['callback_query'] = query
            await settings_fiat_received(query, context)
        elif data.startswith("exp_"):
            await experience_level_handler(query, context)
        elif data == "settings_menu":
            await settings_command(query, context)
        elif data == "feedback_start":
            await feedback_command(query, context)
        elif data.startswith("rating_"):
            context.user_data['callback_query'] = query
            await feedback_rating_received(query, context)
        else:
            # Generic fallback
            await query.edit_message_text(f"🔄 Processing: {data}")
            
    except Exception as e:
        logger.error(f"Error in button_callback_handler for {data}: {e}")
        try:
            await query.edit_message_text("❌ An error occurred. Please try again.")
        except:
            pass