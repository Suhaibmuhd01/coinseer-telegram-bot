import os
import sys
import asyncio

# Ensure project root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import select
from app.core.database import async_session_factory, init_db
from app.models.user import User
from app.models.alert import PriceAlert
from app.models.watchlist import Watchlist
from app.models.portfolio import PortfolioHolding


def print_table(headers, rows):
    if not rows:
        return
    col_widths = [max(len(str(item)) for item in col) for col in zip(*([headers] + rows))]
    fmt = " | ".join(f"{{:<{w}}}" for w in col_widths)
    separator = "-+-".join("-" * w for w in col_widths)
    print(fmt.format(*headers))
    print(separator)
    for row in rows:
        print(fmt.format(*row))


async def inspect_database():
    await init_db()
    print("=" * 70)
    print("      COINSEER ENTERPRISE DATABASE INSPECTION CONSOLE")
    print("=" * 70)

    async with async_session_factory() as session:
        # 1. Registered Users
        res_users = await session.execute(select(User))
        users = res_users.scalars().all()
        print(f"\n[1] REGISTERED USERS ({len(users)} Total):")
        if users:
            user_data = [
                [
                    str(u.id),
                    str(u.user_id),
                    u.username or "N/A",
                    u.first_name or "N/A",
                    u.experience_level or "N/A",
                    u.preferred_fiat.upper(),
                    "YES" if u.whale_alerts_enabled else "NO",
                    u.created_at.strftime("%Y-%m-%d %H:%M") if u.created_at else "N/A",
                ]
                for u in users
            ]
            print_table(["ID", "TG User ID", "Username", "First Name", "Level", "Fiat", "Whale Alerts", "Registered At"], user_data)
        else:
            print("  (No users registered yet. Start the bot and send /start in Telegram!)")

        # 2. Active Price Alerts
        res_alerts = await session.execute(select(PriceAlert))
        alerts = res_alerts.scalars().all()
        print(f"\n[2] ACTIVE PRICE ALERTS ({len(alerts)} Total):")
        if alerts:
            alert_data = [
                [
                    str(a.id),
                    str(a.user_id),
                    a.coin_id.upper(),
                    f"${a.target_price:,.2f}",
                    a.condition,
                    "YES" if a.is_active else "NO",
                    "YES" if a.is_recurring else "NO",
                ]
                for a in alerts
            ]
            print_table(["Alert ID", "TG User ID", "Coin", "Target Price", "Condition", "Active", "Recurring"], alert_data)
        else:
            print("  (No price alerts recorded.)")

        # 3. User Watchlists
        res_watch = await session.execute(select(Watchlist))
        watchlists = res_watch.scalars().all()
        print(f"\n[3] MONITORED WATCHLISTS ({len(watchlists)} Total):")
        if watchlists:
            watch_data = [
                [str(w.id), str(w.user_id), w.coin_id.upper(), w.coin_name, w.created_at.strftime("%Y-%m-%d %H:%M") if w.created_at else "N/A"]
                for w in watchlists
            ]
            print_table(["ID", "TG User ID", "Coin Symbol", "Coin Name", "Added At"], watch_data)
        else:
            print("  (No watchlist items recorded.)")

        # 4. User Portfolios
        res_port = await session.execute(select(PortfolioHolding))
        portfolios = res_port.scalars().all()
        print(f"\n[4] VAULT PORTFOLIOS ({len(portfolios)} Total):")
        if portfolios:
            port_data = [
                [str(p.id), str(p.user_id), p.symbol.upper(), str(p.amount), f"${(p.average_buy_price or 0.0):,.2f}", p.created_at.strftime("%Y-%m-%d %H:%M") if p.created_at else "N/A"]
                for p in portfolios
            ]
            print_table(["ID", "TG User ID", "Coin Symbol", "Amount", "Avg Buy Price", "Created At"], port_data)
        else:
            print("  (No portfolio holdings recorded.)")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    asyncio.run(inspect_database())
