from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Callable

import pyupbit

import config
from core.strategy import get_signal


class BotState:
    def __init__(self):
        self.running = False
        self.ticker = config.DEFAULT_TICKER
        self.trade_amount = config.DEFAULT_TRADE_AMOUNT
        self.last_signal = "hold"
        self.indicators: dict = {}
        self.trades: list[dict] = []
        self.current_price: float = 0
        self.balance_krw: float = 0
        self.balance_coin: float = 0
        self.avg_buy_price: float = 0
        self.error: str | None = None
        self._upbit = None
        self._task: asyncio.Task | None = None

    @property
    def connected(self) -> bool:
        return self._upbit is not None

    def set_keys(self, access: str, secret: str):
        self._upbit = pyupbit.Upbit(access, secret)

    def profit_pct(self) -> float | None:
        if self.avg_buy_price and self.current_price and self.balance_coin > 0:
            return round((self.current_price - self.avg_buy_price) / self.avg_buy_price * 100, 2)
        return None

    def to_dict(self) -> dict:
        return {
            "running": self.running,
            "connected": self.connected,
            "ticker": self.ticker,
            "trade_amount": self.trade_amount,
            "current_price": self.current_price,
            "balance_krw": round(self.balance_krw, 0),
            "balance_coin": self.balance_coin,
            "avg_buy_price": self.avg_buy_price,
            "profit_pct": self.profit_pct(),
            "last_signal": self.last_signal,
            "indicators": self.indicators,
            "trades": self.trades[-50:],
            "error": self.error,
        }


state = BotState()


def _log_trade(t: str, price: float, amount: float, result):
    state.trades.append({
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "type": t,
        "price": price,
        "amount": amount,
        "result": str(result),
    })
    if len(state.trades) > config.MAX_TRADES:
        state.trades = state.trades[-config.MAX_TRADES:]


async def _refresh_balances():
    if not state._upbit:
        return
    coin = state.ticker.split("-")[1]
    balances = state._upbit.get_balances()
    if not isinstance(balances, list):
        state.error = f"잔고 조회 실패: {balances}"
        return
    for b in balances:
        cur = b["currency"]
        if cur == "KRW":
            state.balance_krw = float(b["balance"])
        elif cur == coin:
            state.balance_coin = float(b["balance"])
            state.avg_buy_price = float(b.get("avg_buy_price") or 0)


async def trading_loop(on_update: Callable):
    while state.running:
        try:
            price = pyupbit.get_current_price(state.ticker)
            if price:
                state.current_price = price

            df = pyupbit.get_ohlcv(state.ticker, interval=config.CANDLE_INTERVAL, count=40)
            signal, indicators = get_signal(
                df,
                ma_short=config.MA_SHORT,
                ma_long=config.MA_LONG,
                rsi_period=config.RSI_PERIOD,
                rsi_buy=config.RSI_BUY,
                rsi_sell=config.RSI_SELL,
            )
            state.last_signal = signal
            state.indicators = indicators

            await _refresh_balances()

            if state._upbit:
                if signal == "buy" and state.balance_krw >= state.trade_amount:
                    result = state._upbit.buy_market_order(state.ticker, state.trade_amount)
                    _log_trade("buy", price, state.trade_amount, result)
                elif signal == "sell" and state.balance_coin > 0:
                    result = state._upbit.sell_market_order(state.ticker, state.balance_coin)
                    _log_trade("sell", price, state.balance_coin * price, result)

            state.error = None
        except Exception as e:
            state.error = str(e)

        await on_update()
        await asyncio.sleep(config.LOOP_INTERVAL)


def start_bot(on_update: Callable):
    if state.running:
        return
    state.running = True
    loop = asyncio.get_event_loop()
    state._task = loop.create_task(trading_loop(on_update))


def stop_bot():
    state.running = False
    if state._task:
        state._task.cancel()
        state._task = None
