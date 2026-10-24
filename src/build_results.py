"""Rebuild every table in results/ from one-minute Nifty 50 index data.

    python src/build_results.py --source NIFTY_1MIN.csv --repairs REPAIR_REPORT.csv

The data itself is not part of this repository. The source CSV needs DATE, TIME, Open, High, Low,
Close columns; the repair report lists DATE values of sessions to exclude.
"""
import argparse
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

import orb_overnight as orb

RESULTS = Path(__file__).resolve().parents[1] / 'results'
PERIODS = [('IS', '2017-06-01', '2023-01-01'), ('OOS', '2023-01-01', '2027-01-01')]
COMPONENTS = ['entry_day', 'overnight_gap', 'opening_fill_adjustment', 'next_morning', 'costs']
NIGHT_COLUMNS = ['gap_points', 'gap_bps', 'clock0945_net', 'clock0945_net_bps', 'clock0916_net']


def segment(minutes, entries, atrs, start, end):
    """Sessions and entry signals for one sample. Indicators carry in; positions start flat."""
    sub = minutes.loc[(minutes.index >= start) & (minutes.index < end)].copy()
    sub.attrs = minutes.attrs.copy()
    offset = int((minutes.index < start).sum())
    keep = (entries >= offset) & (entries < offset + len(sub))
    return orb.Sessions.from_minutes(sub), entries[keep] - offset, atrs[keep]


def dissect(minutes, entries, atrs):
    """The system, its same-day twin and the timed night controls, sample by sample."""
    trades, daily, models, night_tables, tests, trade_net = [], [], [], [], {}, {}
    for period, start, end in PERIODS:
        s, ev, at = segment(minutes, entries, atrs, start, end)
        system = orb.attribute(s, orb.simulate(s, ev, at))
        same_day = orb.simulate(s, ev, at, overnight=False)
        assert (same_day.entry_index.to_numpy() == system.entry_index.to_numpy()).all()

        n = orb.nights(s, system)
        variants = {'System (exit 09:45 next day)': system, 'Same signals, exit 15:25 same day': same_day}
        for label, rows in [('Every night', n), ('Only system nights', n[n.selected])]:
            for clock, minute in [('09:45', 30), ('09:16', 1)]:
                variants[f'{label}, 15:25 to {clock}'] = orb.timed_trades(s, rows, minute)

        day = orb.daily_components(s, system)
        day.insert(0, 'date', s.days)
        day.insert(1, 'period', period)
        for name, t in variants.items():
            day[name] = orb.daily_pnl(s, t)
            models.append(dict(period=period, model=name, **orb.metrics(day[name], t.net_points)))
            trade_net.setdefault(name, []).append(t.net_points.to_numpy())
        assert np.allclose(day[COMPONENTS].sum(axis=1), day['System (exit 09:45 next day)'])

        system.insert(0, 'trade_id', [f'{period}-{i + 1:04d}' for i in range(len(system))])
        system.insert(1, 'period', period)
        trades.append(system)
        daily.append(day)
        night_tables.append(n.assign(period=period))
        tests[period] = orb.selection_tests(n, NIGHT_COLUMNS)
    daily = pd.concat(daily, ignore_index=True)
    for name, nets in trade_net.items():
        models.append(dict(period='ALL', model=name, **orb.metrics(daily[name], np.concatenate(nets))))
    trades = pd.concat(trades, ignore_index=True)
    return trades, daily, pd.DataFrame(models), pd.concat(night_tables, ignore_index=True), tests


def exit_clocks(minutes, entries, atrs):
    """The same system with the next-morning exit moved from 09:15 to 10:00, on one continuous run."""
    s = orb.Sessions.from_minutes(minutes)
    n = len(s.days)
    middle = s.days[n // 2]
    halves = {'Full sample': np.ones(n, bool), 'First half': s.days < middle, 'Second half': s.days >= middle}
    daily = pd.DataFrame({'date': s.days, 'half': np.where(s.days < middle, 'First half', 'Second half')})
    rows, parts, logs = [], [], {}
    for clock, minute in orb.EXIT_CLOCKS.items():
        t = orb.attribute(s, orb.simulate(s, entries, atrs, exit_minute=minute))
        daily[clock] = orb.daily_pnl(s, t)
        logs[clock] = t
        for name, mask in halves.items():
            closed = mask[s.day[t.exit_index]]
            rows.append(dict(clock=clock, segment=name, **orb.metrics(daily.loc[mask, clock], t.net_points[closed])))
        parts.append(dict(clock=clock, trades=len(t), entry_day=t.entry_day.sum(),
                          captured_gap=(t.overnight_gap + t.opening_fill_adjustment).sum(),
                          after_open=t.next_morning.sum(), costs=t.costs.sum(), net_points=t.net_points.sum()))
    table = pd.DataFrame(rows)
    base = {name: daily.loc[mask, '09:45'].sum() for name, mask in halves.items()}
    table['vs_0945_lakh'] = [(daily.loc[halves[r.segment], r.clock].sum() - base[r.segment]) * orb.QUANTITY / 1e5
                             for r in table.itertuples()]

    # Paired block bootstrap of each clock's daily difference from 09:45.
    rng = np.random.default_rng(211026)
    starts = rng.integers(n, size=(5000, math.ceil(n / 10)))
    ix = ((starts[:, :, None] + np.arange(10)) % n).reshape(5000, -1)[:, :n]
    shared = set(logs['09:45'].entry_time)
    boot = []
    for clock in orb.EXIT_CLOCKS:
        delta = (daily[clock] - daily['09:45']).to_numpy()
        dist = delta[ix].mean(axis=1)
        boot.append(dict(clock=clock, mean_daily_points=delta.mean(),
                         ci95_daily_points=np.percentile(dist, [2.5, 97.5]).tolist(),
                         ci95_total_lakh=(np.percentile(dist, [2.5, 97.5]) * n * orb.QUANTITY / 1e5).tolist(),
                         same_entries_as_0945=bool(set(logs[clock].entry_time) == shared)))
    return table, pd.DataFrame(parts), daily, dict(draws=5000, block=10, seed=211026, middle=str(middle.date()),
                                                    clocks=boot)


def index_split(minutes):
    """Nifty's own return split into overnight (close to next open) and daytime (open to close)."""
    s = orb.Sessions.from_minutes(minutes)
    first = np.arange(len(s.days)) * orb.SESSION
    day = 1e4 * np.log(s.close / s.open[first])
    night = np.full(len(s.days), np.nan)
    ok = s.next_open >= 0
    night[np.flatnonzero(ok) + 1] = 1e4 * np.log(s.open[s.next_open[ok]] / s.close[ok])
    return pd.DataFrame(dict(date=s.days, overnight_bps=night, daytime_bps=day))


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--source', required=True)
    parser.add_argument('--repairs', required=True)
    args = parser.parse_args()
    RESULTS.mkdir(exist_ok=True)

    minutes = orb.load_sessions(args.source, args.repairs)
    entries, atrs = orb.breakout_entries(minutes)
    trades, daily, models, night_table, tests = dissect(minutes, entries, atrs)

    attribution = trades.groupby('period')[COMPONENTS + ['net_points']].sum()
    attribution.loc['ALL'] = attribution.sum()
    yearly = daily.assign(year=daily.date.dt.year).drop(columns='date').groupby(['period', 'year']).sum()

    clocks, clock_parts, clock_daily, clock_boot = exit_clocks(minutes, entries, atrs)

    out = {
        'trades.csv': trades.drop(columns=['entry_index', 'exit_index']),
        'daily.csv': daily,
        'models.csv': models,
        'attribution.csv': attribution.reset_index(),
        'yearly.csv': yearly.reset_index(),
        'nights.csv': night_table.drop(columns='day_index'),
        'exit_clocks.csv': clocks,
        'exit_clock_attribution.csv': clock_parts,
        'exit_clock_daily.csv': clock_daily,
        'index_overnight_daytime.csv': index_split(minutes),
    }
    for name, frame in out.items():
        frame.to_csv(RESULTS / name, index=False)
    for name, obj in [('selection_tests.json', tests), ('exit_clock_bootstrap.json', clock_boot)]:
        (RESULTS / name).write_text(json.dumps(obj, indent=2, default=float), encoding='utf-8')
    print(models[['period', 'model', 'trades', 'net_lakh', 'sharpe']].to_string(index=False))


if __name__ == '__main__':
    main()
