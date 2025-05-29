# CoinSeer - Your Crypto Tracking Telegram Bot 🤖📈

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

CoinSeer is a real-time Telegram bot designed to be your all-in-one companion for tracking cryptocurrency prices, staying updated with the latest crypto news, setting price alerts, and gaining market insights directly within your Telegram chat.

## ✨ Features

* **Real-time Crypto Prices**: Get current prices, 24h change, market cap, and volume for a wide range of cryptocurrencies (e.g., `/price BTC`).
* **Latest Crypto News**: Fetches top news articles from reputable sources. Filter by keyword or get general crypto news (e.g., `/news bitcoin`).
* **Customizable Price Alerts**: Set up notifications for when a coin reaches a specific target price (e.g., `/alert ETH > 3500`).
* **Personalized Watchlist**: Add coins to your watchlist (`/watchlist_add SOL`) and quickly check their prices (`/watchlist`).
* **Market Overview**:
    * Current **Fear & Greed Index** (`/fear_greed`).
    * *(Future)* Top market movers, global stats.
* **Interactive Interface**: Uses inline buttons and a clear command structure for easy interaction.
* **User-Friendly**: Simple commands and helpful guidance.

## 🛠️ Tech Stack

* **Python 3.8+**
* **`python-telegram-bot`**: For interacting with the Telegram Bot API.
* **`CoinGeckoAPI` (`pycoingecko`)**: For fetching cryptocurrency market data.
* **`NewsAPI` (via `aiohttp`/`requests`)**: For fetching crypto news articles.
* **`APScheduler`**: For scheduling background tasks like price alert checks.
* **`SQLite`**: For local database storage (user preferences, alerts).
* **`python-dotenv`**: For managing environment variables.

## ⚙️ Prerequisites

* Python 3.8 or higher.
* A Telegram account.
* API Keys for:
    * Telegram Bot (from BotFather)
    * [CoinGecko API](https://www.coingecko.com/en/api/pricing) (a free Demo API key is sufficient for personal use)
    * [NewsAPI.org](https://newsapi.org/) (a free developer plan is available)

## 🚀 Setup & Installation

1.  **Clone the Repository:**
    ```bash
    git clone [https://github.com/suhaibmuhd01/coinseer-telegram-bot.git](https://github.com/suhaibmuhd01/coinseer-telegram-bot.git)
    cd coinseer-telegram-bot
    ```

2.  **Create and Activate a Virtual Environment:**
    * **Windows:**
        ```bash
        python -m venv venv
        venv\Scripts\activate
        ```
    * **macOS/Linux:**
        ```bash
        python3 -m venv venv
        source venv/bin/activate
        ```

3.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Set up Environment Variables:**
    Create a file named `.env` in the root project directory (`coinseer-telegram-bot/`).
    Add your API keys and bot token to this file:

    ```env
    TELEGRAM_BOT_TOKEN=YOUR_TELEGRAM_BOT_TOKEN_HERE
    NEWS_API_KEY=YOUR_NEWS_API_KEY_HERE
    # COINGECKO_API_KEY=YOUR_COINGECKO_API_KEY_IF_NEEDED_FOR_PRO_PLAN
    ```
    * Replace placeholders with your actual keys.
    * The `COINGECKO_API_KEY` is generally not strictly required for basic use of the `pycoingecko` library with the public API but is good practice to include if you have a Demo key or plan to use a paid tier.

5.  **Initialize the Database (First time only):**
    The bot will attempt to initialize the database on its first run. Alternatively, you can initialize it manually (ensure your virtual environment is active):
    ```bash
    python database.py
    ```

## ▶️ Running the Bot

Once the setup is complete and your virtual environment is active:

```bash
python main.py