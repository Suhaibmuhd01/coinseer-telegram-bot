from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes
from app.services.api_client import GasTrackerClient


async def gas_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text("[GAS] _Querying decentralized RPC oracles across EVM chains & Solana..._", parse_mode=ParseMode.MARKDOWN)

    gas_data = await GasTrackerClient.get_multichain_gas()

    text = "[GAS] **Multi-Chain Fee & Congestion Matrix**\n\n"
    for chain, metrics in gas_data.items():
        unit = metrics.get("unit", "Gwei")
        safe = metrics.get("safe_low")
        std = metrics.get("standard")
        fast = metrics.get("fast")
        status = metrics.get("status", "[NORMAL]")

        text += (
            f"**[{chain.upper()}]** | {status}\n"
            f"• Standard: `{std} {unit}` | Fast: `{fast} {unit}` | Safe-Low: `{safe} {unit}`\n\n"
        )

    text += "[INFO] _Execution Tip: Submit transactions during low congestion periods to minimize slippage & MEV priority fees._"
    await msg.edit_text(text, parse_mode=ParseMode.MARKDOWN)
