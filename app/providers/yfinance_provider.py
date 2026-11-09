from datetime import datetime, timedelta

try:
    import yfinance as yf
except ImportError:
    yf = None

PERIOD_MAP = {
    "1": ("5d", "1m"),
    "5": ("30d", "5m"),
    "15": ("60d", "15m"),
    "30": ("60d", "30m"),
    "60": ("730d", "1h"),
    "240": ("730d", "1h"),
    "D": ("3650d", "1d"),
    "W": ("3650d", "1wk"),
    "M": ("3650d", "1mo"),
}

GLOBAL_WATCHLIST = [
    {"symbol": "^GSPC", "name": "S&P 500", "exchange": "US"},
    {"symbol": "^DJI", "name": "Dow Jones", "exchange": "US"},
    {"symbol": "^IXIC", "name": "NASDAQ", "exchange": "US"},
    {"symbol": "AAPL", "name": "Apple", "exchange": "NASDAQ"},
    {"symbol": "MSFT", "name": "Microsoft", "exchange": "NASDAQ"},
    {"symbol": "GOOGL", "name": "Alphabet", "exchange": "NASDAQ"},
    {"symbol": "AMZN", "name": "Amazon", "exchange": "NASDAQ"},
    {"symbol": "NVDA", "name": "NVIDIA", "exchange": "NASDAQ"},
    {"symbol": "TSLA", "name": "Tesla", "exchange": "NASDAQ"},
    {"symbol": "META", "name": "Meta", "exchange": "NASDAQ"},
    {"symbol": "^FTSE", "name": "FTSE 100", "exchange": "LON"},
    {"symbol": "^N225", "name": "Nikkei 225", "exchange": "TYO"},
]


class YFinanceProvider:
    def get_candles(self, symbol: str, resolution: str, **_):
        if not yf:
            return []
        period, interval = PERIOD_MAP.get(resolution, ("60d", "15m"))
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(period=period, interval=interval)
            if df.empty:
                return []
            candles = []
            for ts, row in df.iterrows():
                t = int(ts.timestamp())
                candles.append({
                    "time": t,
                    "open": round(row["Open"], 2),
                    "high": round(row["High"], 2),
                    "low": round(row["Low"], 2),
                    "close": round(row["Close"], 2),
                    "volume": int(row.get("Volume", 0)),
                })
            return candles
        except Exception as e:
            print(f"yfinance candle error: {e}")
            return []

    def get_quote(self, symbol: str):
        if not yf:
            return None
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.fast_info
            ltp = info.last_price
            prev = info.previous_close
            change = ltp - prev if prev else 0
            change_pct = (change / prev * 100) if prev else 0
            return {
                "symbol": symbol,
                "ltp": round(ltp, 2),
                "open": round(info.open, 2) if info.open else 0,
                "high": round(info.day_high, 2) if info.day_high else 0,
                "low": round(info.day_low, 2) if info.day_low else 0,
                "close": round(prev, 2) if prev else 0,
                "change": round(change, 2),
                "change_pct": round(change_pct, 2),
                "volume": int(info.last_volume) if info.last_volume else 0,
            }
        except Exception as e:
            print(f"yfinance quote error: {e}")
            return None

    def search(self, query: str):
        results = []
        q = query.upper()
        for item in GLOBAL_WATCHLIST:
            if q in item["symbol"].upper() or q in item["name"].upper():
                results.append(item)
        return results

    def get_watchlist(self):
        return GLOBAL_WATCHLIST
