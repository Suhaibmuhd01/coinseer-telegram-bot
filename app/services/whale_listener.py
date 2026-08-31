import asyncio
import json
import websockets
from app.core.config import settings
from app.core.logging import logger
from app.core.redis import RedisCache

BINANCE_FUTURES_WS = "wss://fstream.binance.com/ws/!forceOrder@arr"
WHALE_ALERT_CHANNEL = "coinseer:whale_alerts"


async def start_liquidation_and_whale_stream():
    """Real-time background WebSocket stream listener for market liquidations & whale movements."""
    logger.info("starting_liquidation_and_whale_listener")
    retry_delay = 5

    while True:
        try:
            async with websockets.connect(BINANCE_FUTURES_WS, ping_interval=20, ping_timeout=10) as ws:
                logger.info("connected_to_binance_liquidation_stream")
                retry_delay = 5

                async for raw_message in ws:
                    try:
                        data = json.loads(raw_message)
                        order = data.get("o", {})
                        symbol = order.get("s", "UNKNOWN")
                        side = order.get("S", "UNKNOWN")  # BUY or SELL
                        original_qty = float(order.get("q", 0))
                        price = float(order.get("p", 0))
                        total_value = original_qty * price

                        # Filter for high-impact liquidations (> $100k USD)
                        if total_value >= 100_000.0:
                            liquidation_type = "[SHORT SQUEEZE] (Shorts Liquidated)" if side == "BUY" else "[LONG CASCADE] (Longs Liquidated)"
                            alert_payload = {
                                "type": "liquidation",
                                "symbol": symbol,
                                "side": side,
                                "amount_usd": total_value,
                                "price": price,
                                "description": (
                                    f"[LIQUIDATION] **DERIVATIVES CASCADE DETECTED**\n\n"
                                    f"• **Asset**: #{symbol}\n"
                                    f"• **Event**: {liquidation_type}\n"
                                    f"• **Aggregate Value**: **${total_value:,.2f} USD**\n"
                                    f"• **Bankruptcy Price**: ${price:,.4f}\n"
                                    f"• **Source**: Live Derivatives Engine Feed"
                                ),
                            }
                            # Broadcast to Redis PubSub
                            await RedisCache.publish(WHALE_ALERT_CHANNEL, alert_payload)
                    except Exception as parse_err:
                        logger.debug("liquidation_message_parse_error", error=str(parse_err))

        except (websockets.ConnectionClosed, Exception) as conn_err:
            logger.warning("liquidation_stream_disconnected", error=str(conn_err), reconnect_in=retry_delay)
            await asyncio.sleep(retry_delay)
            retry_delay = min(retry_delay * 2, 60)
