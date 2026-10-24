"""ORB with an overnight hold on the Nifty 50 index, and the controls used to take it apart.

All prices and P&L are in index points. Timestamps label the open of each one-minute candle (IST).
Only complete regular sessions are used: 375 one-minute candles from 09:15 to 15:29.
"""
from dataclasses import dataclass
import math

import numpy as np
import pandas as pd

SESSION = 375          # one-minute candles per session
CUTOFF = 370           # 15:25, the last minute a same-day position may be held to
RANGE_MINUTES = 30     # opening range is 09:15-09:44
BAR_MINUTES = 15       # signal candles
ATR_LENGTH, ATR_WARMUP = 14, 50
STOP_ATR, TARGET_R, MIN_RISK = 4.0, 2.0, 10.0
MAX_ENTRIES_PER_DAY = 2
COST_PER_SIDE = 3.0
QUANTITY = 260         # 4 lots x 65 units, fixed
EXIT_CLOCKS = {'09:15': 0, '09:16': 1, '09:17': 2, '09:20': 5, '09:22': 7,
               '09:25': 10, '09:30': 15, '09:45': 30, '10:00': 45}
DESIGNED_EXIT = 30     # the system exits at 09:45 next session


# ----------------------------------------------------------------------------- data

def load_sessions(source_csv, repairs_csv):
    """Read one-minute Nifty candles and keep only complete, valid, unrepaired sessions.

    Returns a frame indexed by candle open time. `attrs['source_days']` lists every day present
    in the source, so that a removed session is never silently held across.
    """
    raw = pd.read_csv(source_csv)
    raw.index = pd.to_datetime(raw.DATE + ' ' + raw.TIME)
    raw = raw.sort_index()
    repaired = set(pd.to_datetime(pd.read_csv(repairs_csv).DATE).dt.normalize())
    kept = []
    for day, g in raw.groupby(raw.index.normalize()):
        expected = pd.date_range(day + pd.Timedelta(hours=9, minutes=15), periods=SESSION, freq='min')
        v = g[['Open', 'High', 'Low', 'Close']]
        valid = (g.index.equals(expected) and day not in repaired
                 and np.isfinite(v.to_numpy()).all() and (v > 0).all().all()
                 and not ((g.High < v.max(axis=1)) | (g.Low > v.min(axis=1))).any())
        if valid:
            kept.append(day)
    minutes = raw.loc[raw.index.normalize().isin(kept), ['Open', 'High', 'Low', 'Close']].copy()
    minutes.attrs['source_days'] = pd.DatetimeIndex(raw.index.normalize().unique())
    return minutes


def wilder_atr(bars, length=ATR_LENGTH, warmup=ATR_WARMUP):
    """ATR seeded with the mean of the first `length` true ranges; the first `warmup` bars are masked."""
    c, h, l = bars.Close, bars.High, bars.Low
    tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1).to_numpy()
    tr[0] = np.nan  # the first bar has no previous close
    atr = np.full(len(tr), np.nan)
    start = int(np.flatnonzero(np.isfinite(tr))[0])
    atr[start + length - 1] = tr[start:start + length].mean()
    for k in range(start + length, len(tr)):
        atr[k] = atr[k - 1] * (length - 1) / length + tr[k] / length
    atr[:warmup] = np.nan
    return pd.Series(atr, index=bars.index)


def breakout_entries(minutes):
    """Minute index of every long entry signal, and the signal candle's ATR.

    A completed 15-minute close above today's opening-range high, with the previous close at or
    below it, signals a buy at the next minute's open. Signals are allowed from 09:30 to 14:30.
    """
    m = minutes.assign(minute_index=np.arange(len(minutes)))
    m.attrs = {}  # pandas cannot resample with an index stored in attrs
    bars = m.resample(f'{BAR_MINUTES}min', origin='start_day', offset='9h15min').agg(
        {'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'minute_index': 'last'}).dropna()
    bars['atr'] = wilder_atr(bars)
    clock = m.index.hour * 60 + m.index.minute
    opening = m.loc[clock < 555 + RANGE_MINUTES]
    range_high = opening.groupby(opening.index.normalize()).High.max()
    bars['range_high'] = bars.index.normalize().map(range_high)

    completes = bars.index.hour * 60 + bars.index.minute + BAR_MINUTES
    crossed = (bars.Close > bars.range_high) & (bars.Close.shift() <= bars.range_high)
    # The range is known from 09:45; the last signal candle completes at 14:30.
    allowed = (completes >= 555 + RANGE_MINUTES) & (completes <= 870) & bars.atr.notna()
    hit = bars[crossed & allowed]
    return hit.minute_index.to_numpy(np.int64) + 1, hit.atr.to_numpy()


@dataclass
class Sessions:
    """Flat arrays over the minutes of a run, plus per-day lookups."""
    index: pd.DatetimeIndex
    days: pd.DatetimeIndex
    open: np.ndarray
    high: np.ndarray
    low: np.ndarray
    day: np.ndarray        # session number of each minute
    close: np.ndarray      # final close of each session
    next_open: np.ndarray  # minute index of the next session's 09:15, or -1 if it may not be held into

    @classmethod
    def from_minutes(cls, minutes):
        days = pd.DatetimeIndex(minutes.index.normalize().unique())
        n = len(days)
        source_days = pd.DatetimeIndex(minutes.attrs.get('source_days', days))
        next_open = np.full(n, -1, np.int64)
        for d in range(n - 1):
            pos = source_days.get_indexer([days[d]])[0]
            # Never hold across a removed session, a long calendar gap or the end of the run.
            adjacent = pos + 1 < len(source_days) and source_days[pos + 1] == days[d + 1]
            if adjacent and (days[d + 1] - days[d]).days <= 4:
                next_open[d] = (d + 1) * SESSION
        return cls(minutes.index, days, minutes.Open.to_numpy(), minutes.High.to_numpy(),
                   minutes.Low.to_numpy(), np.repeat(np.arange(n), SESSION),
                   minutes.Close.to_numpy()[np.arange(n) * SESSION + SESSION - 1], next_open)


# ----------------------------------------------------------------------------- simulation

def _first_exit(s, start, deadline, stop, target):
    """Walk minute by minute. Gaps through the stop fill at the open; gaps through the target are capped
    at the target; the scheduled deadline fills at its open; if one minute touches both, stop wins."""
    for k in range(start, deadline + 1):
        if s.open[k] <= stop:
            return k, s.open[k], 'stop'
        if s.open[k] >= target:
            return k, target, 'target'
        if k == deadline:
            return k, s.open[k], 'scheduled'
        if s.low[k] <= stop:
            return k, stop, 'stop'
        if s.high[k] >= target:
            return k, target, 'target'
    raise AssertionError('deadline not reached')


def simulate(s, entries, atrs, exit_minute=DESIGNED_EXIT, overnight=True):
    """Run the system. `exit_minute` is minutes after the next session's 09:15 for the scheduled exit;
    `overnight=False` closes every position at 15:25 the same day instead."""
    counts = np.zeros(len(s.days), int)
    occupied = -1
    rows = []
    for e, atr in zip(entries, atrs):
        if e >= len(s.open) or e <= occupied:   # one position; no re-entry in the exit minute
            continue
        d = s.day[e]
        cutoff = d * SESSION + CUTOFF
        if counts[d] >= MAX_ENTRIES_PER_DAY or e >= cutoff:
            continue
        entry = s.open[e]
        risk = max(MIN_RISK, STOP_ATR * atr)
        stop, target = entry - risk, entry + TARGET_R * risk
        held = overnight and s.next_open[d] >= 0
        deadline = s.next_open[d] + exit_minute if held else cutoff
        j, exit_price, reason = _first_exit(s, e, deadline, stop, target)
        rows.append(dict(entry_index=e, exit_index=j, entry=entry, exit=exit_price, stop=stop,
                         target=target, reason=reason, net_points=exit_price - entry - 2 * COST_PER_SIDE))
        counts[d] += 1
        occupied = j
    trades = pd.DataFrame(rows)
    trades['entry_time'] = s.index[trades.entry_index]
    trades['exit_time'] = s.index[trades.exit_index]
    return trades


def daily_pnl(s, trades):
    """Daily net P&L in points: open positions marked at each session's final close, cost on each leg's day."""
    daily = np.zeros(len(s.days))
    for t in trades.itertuples():
        d, xd = s.day[t.entry_index], s.day[t.exit_index]
        mark = t.entry
        for dd in range(d, xd + 1):
            price = t.exit if dd == xd else s.close[dd]
            daily[dd] += price - mark
            mark = price
        daily[d] -= COST_PER_SIDE
        daily[xd] -= COST_PER_SIDE
    return daily


def attribute(s, trades):
    """Split every trade into entry-day move, overnight gap, opening target cap, next-morning move and costs."""
    parts = []
    for t in trades.itertuples():
        d, xd = s.day[t.entry_index], s.day[t.exit_index]
        gap = adjust = morning = 0.0
        if xd == d:
            entry_day = t.exit - t.entry
        else:
            first = xd * SESSION
            entry_day = s.close[d] - t.entry
            gap = s.open[first] - s.close[d]
            capped_at_open = t.exit_index == first and (s.open[first] <= t.stop or s.open[first] >= t.target)
            if capped_at_open:
                adjust = t.exit - s.open[first]
            else:
                morning = t.exit - s.open[first]
        parts.append(dict(overnight=xd > d, entry_day=entry_day, overnight_gap=gap,
                          opening_fill_adjustment=adjust, next_morning=morning, costs=-2 * COST_PER_SIDE))
    out = pd.concat([trades.reset_index(drop=True), pd.DataFrame(parts)], axis=1)
    total = out[['entry_day', 'overnight_gap', 'opening_fill_adjustment', 'next_morning', 'costs']].sum(axis=1)
    assert np.allclose(total, out.net_points, atol=1e-8)
    return out


def daily_components(s, attributed):
    """The attribution components booked on the day each one happens."""
    cols = ['entry_day', 'overnight_gap', 'opening_fill_adjustment', 'next_morning', 'costs']
    out = pd.DataFrame(0.0, index=range(len(s.days)), columns=cols)
    for t in attributed.itertuples():
        d, xd = s.day[t.entry_index], s.day[t.exit_index]
        out.loc[d, 'entry_day'] += t.entry_day
        out.loc[xd, ['overnight_gap', 'opening_fill_adjustment', 'next_morning']] += (
            t.overnight_gap, t.opening_fill_adjustment, t.next_morning)
        out.loc[d, 'costs'] -= COST_PER_SIDE
        out.loc[xd, 'costs'] -= COST_PER_SIDE
    return out


# ----------------------------------------------------------------------------- night controls

def nights(s, system_trades):
    """Every night that may be held, with the plain overnight returns of buying at 15:25.

    `selected` marks nights on which the system holds a position just before 15:25. It uses only
    entries and stop/target events up to 15:24, never anything that happens afterwards.
    """
    rows = []
    for d in range(len(s.days) - 1):
        if s.next_open[d] != (d + 1) * SESSION:
            continue
        cutoff, first = d * SESSION + CUTOFF, (d + 1) * SESSION
        active = ((system_trades.entry_index < cutoff) & (system_trades.exit_index >= cutoff)).any()
        buy, close, open_ = s.open[cutoff], s.close[d], s.open[first]
        sell_0945, sell_0916 = s.open[first + 30], s.open[first + 1]
        rows.append(dict(date=s.days[d], next_date=s.days[d + 1], day_index=d, selected=bool(active),
                         year=s.days[d].year, weekday=s.days[d].weekday(),
                         gap_points=open_ - close, gap_bps=(open_ / close - 1) * 1e4,
                         clock0945_net=sell_0945 - buy - 6, clock0916_net=sell_0916 - buy - 6,
                         clock0945_net_bps=(sell_0945 - buy - 6) / buy * 1e4,
                         clock0916_net_bps=(sell_0916 - buy - 6) / buy * 1e4))
    return pd.DataFrame(rows)


def timed_trades(s, night_rows, exit_minute):
    """Buy at 15:25 and sell at a fixed next-morning minute: no signal, no stop, no target."""
    e = night_rows.day_index.to_numpy() * SESSION + CUTOFF
    j = (night_rows.day_index.to_numpy() + 1) * SESSION + exit_minute
    entry, exit_ = s.open[e], s.open[j]
    return pd.DataFrame(dict(entry_index=e, exit_index=j, entry=entry, exit=exit_,
                             net_points=exit_ - entry - 2 * COST_PER_SIDE))


# ----------------------------------------------------------------------------- statistics

def metrics(daily, trade_net):
    """Account figures for fixed 260-unit size. Sharpe uses daily marked P&L including flat days."""
    daily, net = np.asarray(daily, float), np.asarray(trade_net, float)
    equity = np.r_[0, np.cumsum(daily)]
    return dict(trades=len(net), net_points=daily.sum(), net_lakh=daily.sum() * QUANTITY / 1e5,
                sharpe=daily.mean() / daily.std(ddof=1) * math.sqrt(252),
                max_dd_lakh=(np.maximum.accumulate(equity) - equity).max() * QUANTITY / 1e5,
                mean_trade_points=net.mean(), win_rate=(net > 0).mean(),
                profit_factor=net[net > 0].sum() / -net[net < 0].sum())


def block_indices(rng, n, block=10):
    """One circular block-bootstrap resample of positions 0..n-1."""
    starts = rng.integers(n, size=math.ceil(n / block))
    return ((starts[:, None] + np.arange(block)) % n).ravel()[:n]


def selection_tests(night_rows, columns, draws=5000, seed=211026):
    """Do the system's nights beat the other nights?

    Bootstrap: 10-night circular blocks, interval for (selected mean - other mean).
    Shuffle test: pick the same number of nights at random within each year-and-weekday group
    and count how often a random pick does at least as well as the real one.
    """
    rng = np.random.default_rng(seed)
    n = len(night_rows)
    picked = night_rows.selected.to_numpy(bool)
    values = night_rows[columns].to_numpy(float)
    diffs = []
    for _ in range(draws):
        ix = block_indices(rng, n)
        p, v = picked[ix], values[ix]
        diffs.append(v[p].mean(axis=0) - v[~p].mean(axis=0))
    ci = np.percentile(diffs, [2.5, 97.5], axis=0)
    groups = [np.asarray(g, int) for g in night_rows.groupby(['year', 'weekday']).indices.values()]
    shuffled = np.empty((draws, len(columns)))
    for b in range(draws):
        chosen = []
        for ix in groups:
            k = int(picked[ix].sum())
            if k:
                chosen.extend(rng.choice(ix, k, replace=False))
        shuffled[b] = values[chosen].mean(axis=0)
    observed = values[picked].mean(axis=0)
    out = {}
    for i, col in enumerate(columns):
        v = values[:, i]
        out[col] = dict(selected_mean=v[picked].mean(), other_mean=v[~picked].mean(),
                        difference=v[picked].mean() - v[~picked].mean(), ci95=ci[:, i].tolist(),
                        random_pick_mean=shuffled[:, i].mean(),
                        random_pick_ci95=np.percentile(shuffled[:, i], [2.5, 97.5]).tolist(),
                        shuffles_at_least_as_good=int((shuffled[:, i] >= observed[i]).sum()),
                        shuffle_p=(1 + (shuffled[:, i] >= observed[i]).sum()) / (draws + 1))
    return dict(nights=n, selected=int(picked.sum()), draws=draws, block=10, seed=seed, tests=out)
