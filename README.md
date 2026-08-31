# CoinSeer Enterprise Crypto Intelligence Ecosystem

CoinSeer is an industrial-grade, highly available, distributed crypto intelligence and market analytics Telegram platform engineered with **Python 3.12**, **FastAPI**, **python-telegram-bot v21+**, **SQLAlchemy 2.0 (AsyncPG)**, **Redis**, and **ARQ**.

---

## 1. System Architecture

```mermaid
graph TD
    User([Telegram User]) <-->|HTTPS / Webhook or Polling| BotAPI[FastAPI + PTB Bot Engine]
    BotAPI <-->|Connection Pool| PG[(PostgreSQL 16)]
    BotAPI <-->|Cache & Pub/Sub| Redis[(Redis 7)]
    
    subgraph Market Intelligence Layer
        BotAPI -->|Market Feed & Circuit Breakers| CG[CoinGecko / DeFiLlama API]
        BotAPI -->|Multi-Chain Gas RPCs| RPC[Ethereum / Arbitrum / Base / Solana]
        BotAPI -->|AI Briefings| Gemini[Google Gemini 1.5 Flash]
        BotAPI -->|Asset Allocation Charts| QC[QuickChart Engine]
    end

    subgraph Real-Time Derivatives Stream
        WhaleWS[Whale / Liquidation Listener] -->|Binance Futures WS| Redis
        Redis -->|Pub/Sub Alert Channel| BotAPI
    end

    subgraph Distributed Background Workers
        Worker[ARQ Task Scheduler] <-->|Queue / Polling| Redis
        Worker <-->|Price Alert Triggers & Volume Scans| PG
    end
```

---

## 2. Key Features

- **Decentralized Multi-Chain Gas Oracle (`/gas`)**: Real-time Gwei metrics and congestion levels for Ethereum, Arbitrum, Base, BSC, and Solana via public RPCs.
- **Institutional Market Intelligence (`/price`, `/chart`, `/market`, `/topmovers`)**: Live quotes, TradingView mini-charts, volume breakdowns, and Fear & Greed index.
- **AI-Powered Market Briefings (`/ai_brief`)**: Generative market sentiment and macro summaries powered by Google Gemini 1.5 Flash.
- **Real-Time Whale & Liquidation Streams**: WebSocket feed monitoring Binance Futures liquidation cascades ($\ge \$100\text{k}$) with instant alerts.
- **Institutional Portfolio Management (`/portfolio`, `/pnl`)**: Track multi-asset positions, entry costs, live net worth, and generate QuickChart portfolio pie charts.
- **Interactive Telegram Mini-App (`/webapp`)**: Dark-mode glassmorphic interface with embedded technical TradingView charts.
- **Zero-Trust Enterprise Security**: Constant-time webhook verification (`hmac.compare_digest`), Telegram Markdown escaping, global sliding-window rate limiting, and security headers.

---

## 3. Quick Start & Local Testing

### Prerequisites
- **Python 3.12+**
- (Optional for full containerization) **Podman** or **Docker**

### Step 1: Clone and Configure Environment
```powershell
# 1. Clone repository
git clone https://github.com/Suhaibmuhd01/coinseer-telegram-bot.git
cd CoinSeer

# 2. Copy and configure .env
cp .env.example .env
```

Open `.env` and configure your credentials:
```env
TELEGRAM_BOT_TOKEN="your_bot_token_from_botfather"
GEMINI_API_KEY="your_gemini_api_key"
DATABASE_URL="postgresql+asyncpg://coinseer_user:coinseer_secret_pass@localhost:5432/coinseer_db"
REDIS_URL="redis://localhost:6379/0"
```

---

### Step 2: Option A — Run via Podman (Recommended for Production)

```powershell
# 1. Start Podman Machine (if not already running)
podman machine start

# 2. Build and launch all services in detached mode
podman compose up --build -d

# 3. Check container status
podman compose ps

# 4. View live logs
podman compose logs -f
```

---

### Step 3: Option B — Run Locally via Python Virtual Environment

```powershell
# 1. Activate virtual environment
.\venv\Scripts\Activate.ps1

# 2. Install dependencies
pip install -r requirements.txt

# 3. Launch Bot in Local Polling Mode (Zero tunnel setup needed)
python main.py --mode polling
```

---

## 4. Bot Command Reference

| Command | Description | Example |
| :--- | :--- | :--- |
| `/start` | Launch bot onboarding and configure experience profile | `/start` |
| `/help` | Display terminal command menu | `/help` |
| `/price <coin>` | Live institutional price quote and 24h stats | `/price BTC` |
| `/chart <coin>` | Technical candlestick price trend chart | `/chart ETH` |
| `/gas` | Decentralized multi-chain gas fee tracker | `/gas` |
| `/ai_brief` | Google Gemini 1.5 Flash market sentiment brief | `/ai_brief` |
| `/alert` | Set price trigger alerts | `/alert` |
| `/portfolio` | View holdings, asset allocation, and net worth | `/portfolio` |
| `/portfolio_add` | Log an asset position into your vault | `/portfolio_add SOL 10 140` |
| `/market <coin>` | Deep asset fundamentals and market metrics | `/market SOL` |
| `/topmovers` | Top 24h gainers and losers across crypto markets | `/topmovers` |
| `/fng` | Fear and Greed market sentiment index | `/fng` |
| `/news` | Latest crypto headlines and regulatory developments | `/news` |
| `/webapp` | Open the interactive CoinSeer Mini-App | `/webapp` |

---

## 5. Testing & Verification

Run automated test compilation:
```powershell
# Verify syntax across all modules
.\venv\Scripts\python.exe -m compileall -q app main.py

# Verify end-to-end imports
.\venv\Scripts\python.exe -c "import app.main, app.core.config, app.core.database, app.core.redis, app.core.security, app.services.api_client, app.services.scheduler, app.services.whale_listener; print('ALL CHECKS PASSED')"
```

---

## 6. License
MIT License. Engineered for institutional reliability.
