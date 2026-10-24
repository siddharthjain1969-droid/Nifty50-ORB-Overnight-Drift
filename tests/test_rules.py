"""The system's fill and timing rules, checked on small made-up price paths."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
import orb_overnight as orb


def flat_sessions(days=2, price=100.0):
    """`days` complete sessions of unchanging prices; tests then edit individual minutes."""
    n = days * orb.SESSION
    index = pd.DatetimeIndex([d + pd.Timedelta(hours=9, minutes=15 + k)
                              for d in pd.date_range('2024-01-01', periods=days) for k in range(orb.SESSION)])
    o, h, l = np.full(n, price), np.full(n, price), np.full(n, price)
    return orb.Sessions(index, pd.DatetimeIndex(index.normalize().unique()), o, h, l,
                        np.repeat(np.arange(days), orb.SESSION), np.full(days, price),
                        np.r_[np.arange(1, days) * orb.SESSION, -1])


def test_gap_below_stop_fills_at_the_open():
    s = flat_sessions()
    s.open[375] = 80.0  # next session opens below a stop at 90
    assert orb._first_exit(s, 100, 405, stop=90.0, target=120.0) == (375, 80.0, 'stop')


def test_gap_above_target_is_capped_at_the_target():
    s = flat_sessions()
    s.open[375] = 150.0
    assert orb._first_exit(s, 100, 405, stop=90.0, target=120.0) == (375, 120.0, 'target')


def test_stop_wins_when_one_minute_touches_both():
    s = flat_sessions()
    s.low[200], s.high[200] = 85.0, 125.0
    assert orb._first_exit(s, 100, 405, stop=90.0, target=120.0) == (200, 90.0, 'stop')


def test_scheduled_exit_uses_the_deadline_open_only():
    s = flat_sessions()
    s.open[405], s.low[405] = 101.0, 50.0  # the deadline minute's low must be ignored
    assert orb._first_exit(s, 100, 405, stop=90.0, target=120.0) == (405, 101.0, 'scheduled')


def test_overnight_trade_exits_at_0945_and_same_day_twin_at_1525():
    s = flat_sessions()
    entries, atrs = np.array([60]), np.array([5.0])
    held = orb.simulate(s, entries, atrs)
    same_day = orb.simulate(s, entries, atrs, overnight=False)
    assert held.exit_time[0] == pd.Timestamp('2024-01-02 09:45')
    assert same_day.exit_time[0] == pd.Timestamp('2024-01-01 15:25')
    assert held.net_points[0] == -2 * orb.COST_PER_SIDE


def test_one_position_at_a_time_and_no_reentry_in_the_exit_minute():
    s = flat_sessions()
    s.low[70] = 0.0  # stops out the first trade in minute 70
    entries = np.array([60, 70, 80, 90])
    t = orb.simulate(s, entries, np.full(4, 5.0), overnight=False)
    assert list(t.entry_index) == [60, 80]


def test_at_most_two_entries_a_day():
    s = flat_sessions()
    s.low[65] = s.low[85] = 0.0  # each of the first two trades is stopped out quickly
    t = orb.simulate(s, np.array([60, 70, 90]), np.full(3, 5.0), overnight=False)
    assert list(t.entry_index) == [60, 70]


def test_atr_is_seeded_with_the_mean_of_the_first_14_true_ranges():
    bars = pd.DataFrame({'High': np.arange(60) + 2.0, 'Low': np.arange(60) + 0.0, 'Close': np.arange(60) + 1.0})
    atr = orb.wilder_atr(bars, warmup=0)
    assert np.isnan(atr[13]) and atr[14] == 2.0 and atr[59] == 2.0
