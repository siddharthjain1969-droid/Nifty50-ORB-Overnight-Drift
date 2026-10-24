# System rules

Long only on the Nifty 50 index. All times are Indian Standard Time; each timestamp labels the **open** of a one-minute candle. In the original research the system's ID was S20991.

## Data

- One-minute Nifty 50 index candles (`NSE:NIFTY50-INDEX`) from the FYERS broker's historical data API, 17 July 2017 to 3 September 2026. Not included in this repository.
- A session is used only if it has exactly 375 candles from 09:15 to 15:29, with valid prices and no repairs. 31 sessions fail this and are excluded. Indicators carry across the remaining sessions.
- In-sample: 17 July 2017 – 30 December 2022 (1,323 sessions). Out-of-sample: 2 January 2023 – 3 September 2026 (905 sessions). Both start with no position; indicators carry across the boundary.

## Opening range

- **Range high** = the highest High of the 09:15–09:44 one-minute candles of the same day.
- It becomes known only at 09:45 and is never used before then.

## Signal candles and ATR

- Signals use completed **15-minute** candles aligned to 09:15. The candle labelled 09:45 covers 09:45–09:59 and completes at 10:00.
- **ATR(14)** on those candles: true range = max(High − Low, |High − previous Close|, |Low − previous Close|); the first candle has no previous close. ATR starts as the plain average of the first 14 true ranges, then ATR = previous ATR × 13/14 + true range / 14. The first 50 candles are treated as warm-up and never trade.

## Entry

On each completed 15-minute candle, buy when **all** of these hold:

1. The candle's close is **above** today's range high.
2. The previous 15-minute close was **at or below** the same range high, so this is a fresh crossing, not just a candle sitting above the range. The previous candle may be from the prior session.
3. ATR is valid and the candle completes between 09:45 and 14:30.
4. No position is open, fewer than two entries have been made today, and the entry minute is not the minute a previous trade exited.

The fill is the **open of the next one-minute candle**. The earliest possible entry is 10:00. There is no trend, volume, weekday or other filter.

## Stop and target

- Risk R = max(10 points, **4 × ATR** of the signal candle).
- Stop = entry − R. Target = entry + **2R**. Both are fixed for the life of the trade: no trailing stop, no break-even move.

## Exit

The position stays open through the rest of the entry day and into the next session. Every minute from entry onward is checked in this order:

1. If the minute **opens at or below the stop**, exit at that open. A gap down can lose more than R.
2. Else, if it **opens at or above the target**, exit at the target. A gap up beyond the target earns only the target.
3. Else, if this is the **scheduled exit minute (09:45 next session)**, exit at its open.
4. Else, if the minute's Low touches the stop, exit at the stop. If the same minute also touches the target, the stop wins.
5. Else, if the minute's High touches the target, exit at the target.

**Data-boundary exit:** if the next session is missing from the data, or more than four calendar days away, the position is closed at 15:25 on the entry day. This depends on the historical dataset, not on a rule a live trader could follow.

## Size, costs and accounting

- Fixed **260 units** (4 lots × 65) on every trade, with no compounding. Starting capital is ₹10,00,000.
- Cost: **3 index points per side**, so 6 points (₹1,560) per round trip, charged on each leg's own day.
- Daily P&L marks open positions at that session's last close. Maximum drawdown is measured on these daily values, so intraday drawdowns can be larger.
- Sharpe ratio = mean daily P&L ÷ its standard deviation × √252, counting days with no position.

## Variants used in the study

These are diagnostic changes to the rules above, not separate systems:

- **Same-day exit:** identical, except the scheduled exit is 15:25 on the entry day.
- **Alternative exit clocks:** identical, except the scheduled exit is 09:15, 09:16, 09:17, 09:20, 09:22, 09:25, 09:30 or 10:00 next session. Exploratory.
- **Night controls:** buy at the 15:25 open, sell at the 09:45 (or 09:16) open next session, no stop or target, 6 points cost. Run on every eligible night, or only on nights when the system holds a position just before 15:25.
