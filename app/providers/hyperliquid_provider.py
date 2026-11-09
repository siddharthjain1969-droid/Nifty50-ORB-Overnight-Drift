import httpx
import time
from config import HYPERLIQUID_API

INTERVAL_MAP = {
    "1": "1m", "3": "3m", "5": "5m", "15": "15m", "30": "30m",
    "60": "1h", "120": "2h", "240": "4h",
    "D": "1d", "W": "1w", "M": "1M",
}

CRYPTO_WATCHLIST = [
    {"symbol": "BTC", "name": "Bitcoin", "exchange": "HL"},
    {"symbol": "ETH", "name": "Ethereum", "exchange": "HL"},
    {"symbol": "SOL", "name": "Solana", "exchange": "HL"},
    {"symbol": "DOGE", "name": "Dogecoin", "exchange": "HL"},
    {"symbol": "AVAX", "name": "Avalanche", "exchange": "HL"},
    {"symbol": "LINK", "name": "Chainlink", "exchange": "HL"},
    {"symbol": "ARB", "name": "Arbitrum", "exchange": "HL"},
    {"symbol": "SUI", "name": "Sui", "exchange": "HL"},
    {"symbol": "OP", "name": "Optimism", "exchange": "HL"},
    {"symbol": "APT", "name": "Aptos", "exchange": "HL"},
    {"symbol": "WIF", "name": "dogwifhat", "exchange": "HL"},
    {"symbol": "PEPE", "name": "Pepe", "exchange": "HL"},
]


class HyperliquidProvider:
    def __init__(self):
        self._mids_cache = {}
        self._mids_ts = 0

    def get_candles(self, symbol: str, resolution: str, days_back: int = 60):
        interval = INTERVAL_MAP.get(resolution, "15m")
        now_ms = int(time.time() * 1000)
        start_ms = now_ms - days_back * 86400 * 1000
        try:
            resp = httpx.post(
                HYPERLIQUID_API,
                json={
                    "type": "candleSnapshot",
                    "req": {
                        "coin": symbol,
                        "interval": interval,
                        "startTime": start_ms,
                        "endTime": now_ms,
                    },
                },
                timeout=15,
            )
            data = resp.json()
            if not isinstance(data, list):
                return []
            candles = []
            for c in data:
                candles.append({
                    "time": int(c["t"]) // 1000,
                    "open": float(c["o"]),
                    "high": float(c["h"]),
                    "low": float(c["l"]),
                    "close": float(c["c"]),
                    "volume": float(c["v"]),
                })
            return candles
        except Exception as e:
            print(f"Hyperliquid candle error: {e}")
            return []

    def _refresh_mids(self):
        now = time.time()
        if now - self._mids_ts < 5:
            return
        try:
            resp = httpx.post(HYPERLIQUID_API, json={"type": "allMids"}, timeout=10)
            self._mids_cache = resp.json()
            self._mids_ts = now
        except Exception as e:
            print(f"Hyperliquid mids error: {e}")

    def get_quote(self, symbol: str):
        self._refresh_mids()
        mid = self._mids_cache.get(symbol)
        if mid is None:
            return None
        price = float(mid)
        return {
            "symbol": symbol,
            "ltp": price,
            "open": 0,
            "high": 0,
            "low": 0,
            "close": 0,
            "change": 0,
            "change_pct": 0,
            "volume": 0,
        }

    def search(self, query: str):
        results = []
        q = query.upper()
        for item in CRYPTO_WATCHLIST:
            if q in item["symbol"].upper() or q in item["name"].upper():
                results.append(item)
        return results

    def get_watchlist(self):
        return CRYPTO_WATCHLIST
