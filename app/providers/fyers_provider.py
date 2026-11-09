import time
from datetime import datetime, timedelta
from config import FYERS_CLIENT_ID, FYERS_ACCESS_TOKEN

try:
    from fyers_apiv3 import fyersModel
except ImportError:
    fyersModel = None

RESOLUTION_MAP = {
    "1": "1", "3": "3", "5": "5", "10": "10", "15": "15", "30": "30",
    "60": "60", "120": "120", "240": "240",
    "D": "1D", "W": "1W", "M": "1M",
}

INDIAN_WATCHLIST = [
    {"symbol": "NSE:NIFTY50-INDEX", "name": "NIFTY 50", "exchange": "NSE"},
    {"symbol": "NSE:NIFTYBANK-INDEX", "name": "BANK NIFTY", "exchange": "NSE"},
    {"symbol": "NSE:RELIANCE-EQ", "name": "Reliance", "exchange": "NSE"},
    {"symbol": "NSE:TCS-EQ", "name": "TCS", "exchange": "NSE"},
    {"symbol": "NSE:HDFCBANK-EQ", "name": "HDFC Bank", "exchange": "NSE"},
    {"symbol": "NSE:INFY-EQ", "name": "Infosys", "exchange": "NSE"},
    {"symbol": "NSE:ICICIBANK-EQ", "name": "ICICI Bank", "exchange": "NSE"},
    {"symbol": "NSE:SBIN-EQ", "name": "SBI", "exchange": "NSE"},
    {"symbol": "NSE:BHARTIARTL-EQ", "name": "Bharti Airtel", "exchange": "NSE"},
    {"symbol": "NSE:ITC-EQ", "name": "ITC", "exchange": "NSE"},
    {"symbol": "NSE:TATAMOTORS-EQ", "name": "Tata Motors", "exchange": "NSE"},
    {"symbol": "NSE:LT-EQ", "name": "L&T", "exchange": "NSE"},
    {"symbol": "NSE:WIPRO-EQ", "name": "Wipro", "exchange": "NSE"},
    {"symbol": "NSE:AXISBANK-EQ", "name": "Axis Bank", "exchange": "NSE"},
    {"symbol": "NSE:KOTAKBANK-EQ", "name": "Kotak Bank", "exchange": "NSE"},
]


class FyersProvider:
    def __init__(self):
        self.fyers = None
        if fyersModel and FYERS_CLIENT_ID and FYERS_ACCESS_TOKEN:
            self.fyers = fyersModel.FyersModel(
                client_id=FYERS_CLIENT_ID,
                token=FYERS_ACCESS_TOKEN,
                is_async=False,
                log_path="",
            )

    @property
    def available(self):
        return self.fyers is not None

    def get_candles(self, symbol: str, resolution: str, days_back: int = 60):
        if not self.available:
            return []
        res = RESOLUTION_MAP.get(resolution, resolution)
        now = int(time.time())
        start = now - days_back * 86400
        data = {
            "symbol": symbol,
            "resolution": res,
            "date_format": "1",
            "range_from": str(start),
            "range_to": str(now),
            "cont_flag": "1",
        }
        try:
            resp = self.fyers.history(data=data)
            if resp and resp.get("s") == "ok":
                candles = resp.get("candles", [])
                return [
                    {
                        "time": int(c[0]),
                        "open": c[1],
                        "high": c[2],
                        "low": c[3],
                        "close": c[4],
                        "volume": c[5],
                    }
                    for c in candles
                ]
        except Exception as e:
            print(f"Fyers candle error: {e}")
        return []

    def get_quote(self, symbol: str):
        if not self.available:
            return None
        try:
            data = {"symbols": symbol}
            resp = self.fyers.quotes(data=data)
            if resp and resp.get("s") == "ok" and resp.get("d"):
                q = resp["d"][0]["v"]
                return {
                    "symbol": symbol,
                    "ltp": q.get("lp", 0),
                    "open": q.get("open_price", 0),
                    "high": q.get("high_price", 0),
                    "low": q.get("low_price", 0),
                    "close": q.get("prev_close_price", 0),
                    "change": q.get("ch", 0),
                    "change_pct": q.get("chp", 0),
                    "volume": q.get("volume", 0),
                }
        except Exception as e:
            print(f"Fyers quote error: {e}")
        return None

    def search(self, query: str):
        results = []
        q = query.upper()
        for item in INDIAN_WATCHLIST:
            if q in item["symbol"].upper() or q in item["name"].upper():
                results.append(item)
        return results

    def get_watchlist(self):
        return INDIAN_WATCHLIST
