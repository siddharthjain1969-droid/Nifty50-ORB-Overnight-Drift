import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from fastapi import FastAPI, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from providers import FyersProvider, YFinanceProvider, HyperliquidProvider
from config import HOST, PORT

app = FastAPI(title="Trading Terminal")

fyers = FyersProvider()
yfinance = YFinanceProvider()
hyperliquid = HyperliquidProvider()

PROVIDER_MAP = {
    "india": fyers,
    "global": yfinance,
    "crypto": hyperliquid,
}


def detect_market(symbol: str) -> str:
    s = symbol.upper()
    if s.startswith("NSE:") or s.startswith("BSE:"):
        return "india"
    crypto_coins = {
        w["symbol"] for w in hyperliquid.get_watchlist()
    }
    if s in crypto_coins:
        return "crypto"
    return "global"


@app.get("/api/candles")
def get_candles(
    symbol: str,
    resolution: str = "15",
    market: str = "",
    days_back: int = 60,
):
    mkt = market or detect_market(symbol)
    provider = PROVIDER_MAP.get(mkt, yfinance)
    candles = provider.get_candles(symbol, resolution, days_back=days_back)
    return {"candles": candles, "market": mkt, "symbol": symbol}


@app.get("/api/quote")
def get_quote(symbol: str, market: str = ""):
    mkt = market or detect_market(symbol)
    provider = PROVIDER_MAP.get(mkt, yfinance)
    quote = provider.get_quote(symbol)
    return {"quote": quote, "market": mkt}


@app.get("/api/search")
def search_symbols(q: str = "", market: str = ""):
    results = []
    if market:
        provider = PROVIDER_MAP.get(market)
        if provider:
            results = provider.search(q)
    else:
        for p in [fyers, yfinance, hyperliquid]:
            results.extend(p.search(q))
    return {"results": results}


@app.get("/api/watchlist")
def get_watchlist(market: str = "india"):
    provider = PROVIDER_MAP.get(market)
    if provider:
        return {"symbols": provider.get_watchlist(), "market": market}
    return {"symbols": [], "market": market}


@app.get("/api/status")
def status():
    return {
        "fyers": fyers.available,
        "yfinance": True,
        "hyperliquid": True,
    }


static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/sw.js")
def service_worker():
    return FileResponse(
        os.path.join(static_dir, "sw.js"),
        media_type="application/javascript",
        headers={"Service-Worker-Allowed": "/"},
    )


@app.get("/")
def index():
    return FileResponse(os.path.join(static_dir, "index.html"))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host=HOST, port=PORT, reload=True)
