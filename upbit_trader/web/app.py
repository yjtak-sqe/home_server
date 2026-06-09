from __future__ import annotations

import json
import os
import sys
from contextlib import asynccontextmanager

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel  # noqa: F401 (StartBody)

import config
from core import bot

HERE = os.path.dirname(os.path.abspath(__file__))
_clients: set[WebSocket] = set()


async def _broadcast():
    data = json.dumps(bot.state.to_dict())
    dead = set()
    for ws in _clients:
        try:
            await ws.send_text(data)
        except Exception:
            dead.add(ws)
    _clients.difference_update(dead)


@asynccontextmanager
async def _lifespan(app):
    access = os.environ.get("UPBIT_ACCESS_KEY", "").strip()
    secret = os.environ.get("UPBIT_SECRET_KEY", "").strip()
    if access and secret:
        bot.state.set_keys(access, secret)
        await bot._refresh_balances()
    yield
    bot.stop_bot()


app = FastAPI(title=config.APP_NAME, version=config.APP_VERSION, lifespan=_lifespan)
app.mount("/static", StaticFiles(directory=os.path.join(HERE, "static")), name="static")


@app.get("/", response_class=HTMLResponse)
def index():
    with open(os.path.join(HERE, "templates", "index.html"), encoding="utf-8") as f:
        html = f.read()
    return HTMLResponse(html.replace("{{APP_NAME}}", config.APP_NAME).replace("{{APP_VERSION}}", config.APP_VERSION))


@app.get("/api/state")
def get_state():
    return bot.state.to_dict()


class StartBody(BaseModel):
    ticker: str = config.DEFAULT_TICKER
    trade_amount: float = config.DEFAULT_TRADE_AMOUNT
    use_golden_cross: bool = True
    use_rsi_buy: bool = True
    use_rsi_sell: bool = True
    rsi_buy_threshold: float = config.RSI_BUY
    rsi_sell_threshold: float = config.RSI_SELL


@app.post("/api/start")
async def start(body: StartBody):
    if not bot.state.connected:
        raise HTTPException(400, "먼저 API 키를 연결해 주세요.")
    if body.trade_amount < 5000:
        raise HTTPException(400, "최소 거래금액은 5,000원입니다.")
    bot.state.ticker = body.ticker
    bot.state.trade_amount = body.trade_amount
    bot.state.use_golden_cross = body.use_golden_cross
    bot.state.use_rsi_buy = body.use_rsi_buy
    bot.state.use_rsi_sell = body.use_rsi_sell
    bot.state.rsi_buy_threshold = body.rsi_buy_threshold
    bot.state.rsi_sell_threshold = body.rsi_sell_threshold
    bot.start_bot(_broadcast)
    await _broadcast()
    return {"ok": True}


@app.post("/api/stop")
async def stop():
    bot.stop_bot()
    await _broadcast()
    return {"ok": True}


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    _clients.add(ws)
    try:
        await ws.send_text(json.dumps(bot.state.to_dict()))
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        _clients.discard(ws)
