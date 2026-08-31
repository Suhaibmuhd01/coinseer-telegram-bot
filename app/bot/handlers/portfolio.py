from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes
from sqlalchemy import select, delete
from app.core.database import async_session_factory
from app.core.security import sanitize_input
from app.models.portfolio import PortfolioHolding, PortfolioTransaction
from app.models.user import User
from app.services.api_client import (
    api_client,
    get_coingecko_id,
    get_display_symbol,
    ChartRenderer,
)


async def portfolio_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    async with async_session_factory() as session:
        res_user = await session.execute(select(User.preferred_fiat).where(User.user_id == user_id))
        fiat = res_user.scalar_one_or_none() or "usd"

        res_holdings = await session.execute(
            select(PortfolioHolding).where(PortfolioHolding.user_id == user_id)
        )
        holdings = res_holdings.scalars().all()

    if not holdings:
        await update.message.reply_text(
            "[VAULT] **Your Portfolio is currently empty.**\n\n"
            "Log assets with `/portfolio_add <symbol> <amount> [avg_buy_price]`\n"
            "Example: `/portfolio_add SOL 25.5 140`",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    coin_ids = [h.coin_id for h in holdings]
    price_data = await api_client.get_crypto_price(coin_ids, vs_currency=fiat)

    total_net_worth = 0.0
    labels = []
    values = []
    breakdown_lines = []

    for h in holdings:
        c_data = price_data.get(h.coin_id, {})
        current_price = c_data.get(fiat, 0.0)
        holding_value = h.amount * current_price
        total_net_worth += holding_value

        labels.append(h.symbol)
        values.append(round(holding_value, 2))

        pnl_str = ""
        if h.average_buy_price and h.average_buy_price > 0:
            cost_basis = h.amount * h.average_buy_price
            profit = holding_value - cost_basis
            profit_pct = (profit / cost_basis) * 100
            pnl_glyph = "▲" if profit >= 0 else "▼"
            pnl_str = f" | PnL: {pnl_glyph} `${profit:+,.2f}` (`{profit_pct:+.1f}%`)"

        breakdown_lines.append(
            f"• **{h.symbol}**: `{h.amount:.4f}` units = **${holding_value:,.2f}**{pnl_str}"
        )

    msg = (
        f"[VAULT] **Institutional Portfolio Valuation ({fiat.upper()})**\n\n"
        f"• **Total Aggregate Net Worth**: **${total_net_worth:,.2f} USD**\n\n"
        f"**Asset Allocations:**\n" + "\n".join(breakdown_lines) + "\n\n"
        f"[INFO] _Use `/portfolio_add` or `/portfolio_remove` to balance._"
    )

    if sum(values) > 0:
        chart_url = ChartRenderer.render_portfolio_pie_chart(labels, values)
        try:
            await update.message.reply_photo(photo=chart_url, caption=msg, parse_mode=ParseMode.MARKDOWN)
            return
        except Exception:
            pass

    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)


async def portfolio_add_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not context.args or len(context.args) < 2:
        await update.message.reply_text(
            "Usage: `/portfolio_add <symbol> <amount> [avg_buy_price]`\n"
            "Example: `/portfolio_add ETH 2.5 3100`",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    raw_symbol = sanitize_input(context.args[0], 32)
    try:
        amount = float(sanitize_input(context.args[1], 32).replace(",", ""))
        if amount <= 0:
            raise ValueError()
    except ValueError:
        await update.message.reply_text("[ERROR] Amount must be a positive numeric value.")
        return

    avg_buy_price = 0.0
    if len(context.args) > 2:
        try:
            avg_buy_price = float(sanitize_input(context.args[2], 32).replace("$", "").replace(",", ""))
        except ValueError:
            pass

    coin_id = get_coingecko_id(raw_symbol)
    display_sym = get_display_symbol(coin_id)

    async with async_session_factory() as session:
        res = await session.execute(
            select(PortfolioHolding).where(
                PortfolioHolding.user_id == user_id, PortfolioHolding.coin_id == coin_id
            )
        )
        existing = res.scalar_one_or_none()

        if existing:
            existing.amount = amount
            if avg_buy_price > 0:
                existing.average_buy_price = avg_buy_price
        else:
            new_holding = PortfolioHolding(
                user_id=user_id,
                coin_id=coin_id,
                symbol=display_sym,
                amount=amount,
                average_buy_price=avg_buy_price,
            )
            session.add(new_holding)

        tx = PortfolioTransaction(
            user_id=user_id,
            coin_id=coin_id,
            symbol=display_sym,
            transaction_type="buy",
            amount=amount,
            price_per_unit=avg_buy_price,
            fiat="usd",
        )
        session.add(tx)
        await session.commit()

    await update.message.reply_text(
        f"[OK] Position saved: **{amount} {display_sym}**. Audit via `/portfolio`.",
        parse_mode=ParseMode.MARKDOWN,
    )


async def portfolio_remove_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not context.args:
        await update.message.reply_text("Usage: `/portfolio_remove <symbol>`", parse_mode=ParseMode.MARKDOWN)
        return

    raw_symbol = sanitize_input(context.args[0], 32)
    coin_id = get_coingecko_id(raw_symbol)
    display_sym = get_display_symbol(coin_id)

    async with async_session_factory() as session:
        result = await session.execute(
            delete(PortfolioHolding).where(
                PortfolioHolding.user_id == user_id, PortfolioHolding.coin_id == coin_id
            )
        )
        await session.commit()
        if result.rowcount > 0:
            await update.message.reply_text(f"[OK] **{display_sym}** decommissioned from vault.", parse_mode=ParseMode.MARKDOWN)
        else:
            await update.message.reply_text(f"[ERROR] **{display_sym}** was not found in your holdings.", parse_mode=ParseMode.MARKDOWN)
