import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
NEWS_API_KEY = os.getenv("NEWS_API_KEY")

# Database
DB_NAME = "coinseer_bot.db"

# Other constants
SUPPORTED_FIAT = ["usd", "eur", "gbp", "jpy", "aud"]
DEFAULT_FIAT = "usd"
NEWS_SOURCES = "coindesk,cointelegraph,decrypt,bitcoin-magazine,the-block,coinbase-blog"

# Educational content
CRYPTO_TIPS = [
    "💡 **DCA (Dollar Cost Averaging)**: Invest a fixed amount regularly regardless of price to reduce volatility impact.",
    "💡 **HODL**: Hold On for Dear Life - a strategy of holding crypto long-term despite market fluctuations.",
    "💡 **Market Cap**: Total value of all coins in circulation. Higher market cap usually means more stability.",
    "💡 **Volume**: Amount of crypto traded in 24h. High volume indicates strong interest and liquidity.",
    "💡 **Support/Resistance**: Price levels where buying (support) or selling (resistance) pressure is strong.",
    "💡 **Whale**: Large crypto holders who can influence market prices with their trades.",
    "💡 **FOMO**: Fear of Missing Out - emotional trading that often leads to buying high and selling low.",
    "💡 **FUD**: Fear, Uncertainty, and Doubt - negative sentiment that can drive prices down.",
    "💡 **Staking**: Earning rewards by holding and 'staking' certain cryptocurrencies to support network operations.",
    "💡 **Cold Storage**: Keeping crypto offline in hardware wallets for maximum security."
]

# Alert thresholds
VOLUME_SPIKE_THRESHOLD = 2.0  # 200% increase
PRICE_CHANGE_THRESHOLD = 10.0  # 10% change