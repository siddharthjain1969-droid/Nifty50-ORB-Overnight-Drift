"""Draw every README chart from the tables in results/, in a light and a dark version.

    python src/make_figures.py
"""
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RESULTS, FIGURES = ROOT / 'results', ROOT / 'figures'
LAKH = 260 / 1e5            # index points to INR lakh at 260 units
SYSTEM = 'System (exit 09:45 next day)'

THEMES = {
    'light': dict(surface='#fcfcfb', ink='#0b0b0b', ink2='#52514e', muted='#898781', grid='#e1e0d9',
                  axis='#c3c2b7', shade='#f0efec', main='#2a78d6', other='#eb6834', loss='#e34948'),
    'dark': dict(surface='#1a1a19', ink='#f0efec', ink2='#c3c2b7', muted='#898781', grid='#2c2c2a',
                 axis='#383835', shade='#262624', main='#3987e5', other='#d95926', loss='#e66767'),
}


def canvas(t, title, subtitle, size=(9, 4.6)):
    plt.rcParams.update({'font.family': ['Segoe UI', 'DejaVu Sans'], 'font.size': 10.5})
    fig, ax = plt.subplots(figsize=size, dpi=160)
    fig.patch.set_facecolor(t['surface'])
    ax.set_facecolor(t['surface'])
    for side in ['top', 'right', 'left']:
        ax.spines[side].set_visible(False)
    ax.spines['bottom'].set_color(t['axis'])
    ax.grid(axis='y', color=t['grid'], linewidth=0.8)
    ax.set_axisbelow(True)
    ax.tick_params(colors=t['muted'], length=0)
    fig.text(0.06, 0.95, title, fontsize=14, fontweight='bold', color=t['ink'], va='top')
    fig.text(0.06, 0.885, subtitle, fontsize=10.5, color=t['ink2'], va='top')
    fig.subplots_adjust(left=0.08, right=0.96, top=0.79, bottom=0.12)
    return fig, ax


def label_end(ax, x, y, text, color, t, dy=0):
    ax.annotate(text, (x, y), xytext=(8, dy), textcoords='offset points', va='center',
                fontsize=10, color=t['ink'], fontweight='bold')
    ax.plot([x], [y], 'o', ms=5, color=color)


def year_axis(ax, dates, room_days):
    ax.set_xlim(dates.iloc[0], dates.iloc[-1] + pd.Timedelta(days=room_days))
    ax.set_xticks([pd.Timestamp(f'{y}-01-01') for y in range(2018, dates.iloc[-1].year + 1, 2)],
                  [str(y) for y in range(2018, dates.iloc[-1].year + 1, 2)])


def mark_oos(ax, dates, t):
    start = dates[dates >= '2023-01-01'].iloc[0]
    ax.axvspan(start, dates.iloc[-1], color=t['shade'], zorder=0, lw=0)
    ax.text(start, 1.0, '  Out-of-sample  2023 onward', transform=ax.get_xaxis_transform(),
            va='top', fontsize=9, color=t['muted'])


def save(fig, name, mode):
    fig.savefig(FIGURES / f'{name}-{mode}.png', facecolor=fig.get_facecolor())
    plt.close(fig)


def equity(daily, t, mode):
    d = pd.to_datetime(daily.date)
    eq = 10 + daily[SYSTEM].cumsum() * LAKH
    fig, ax = canvas(t, 'The system: INR 10 lakh to 54.5 lakh, 2017-2026',
                     'Daily account value, INR lakh, fixed 260 units, after 6 points cost per trade')
    mark_oos(ax, d, t)
    ax.plot(d, eq, color=t['main'], lw=2)
    label_end(ax, d.iloc[-1], eq.iloc[-1], f'{eq.iloc[-1]:.1f}', t['main'], t)
    year_axis(ax, d, 250)
    save(fig, '1-system-equity', mode)


def attribution(attr, t, mode):
    row = attr.set_index('period').loc['ALL'] * LAKH
    parts = [('Entry day', row.entry_day), ('Overnight gap', row.overnight_gap),
             ('Target cap at the open', row.opening_fill_adjustment), ('Next morning', row.next_morning),
             ('Costs', row.costs)]
    fig, ax = canvas(t, 'Almost all of the profit arrives in the overnight gap',
                     'Where the system\'s INR 44.5 lakh net profit came from, INR lakh, 2017-2026', size=(9, 4.8))
    ax.grid(axis='y', visible=False)
    ax.grid(axis='x', color=t['grid'], linewidth=0.8)
    level = 0.0
    for i, (name, value) in enumerate(parts):
        ax.barh(i, value, left=level, height=0.55, color=t['main'] if value > 0 else t['loss'])
        x = level + value if value > 0 else level
        ax.text(x + 1, i, f'{value:+.1f}', va='center', fontsize=10, color=t['ink'], fontweight='bold')
        level += value
    ax.set_xlim(0, max(np.cumsum([p[1] for p in parts])) * 1.12)
    ax.barh(len(parts), level, height=0.55, color=t['ink2'])
    ax.text(level + 1, len(parts), f'{level:.1f} net', va='center', fontsize=10, color=t['ink'], fontweight='bold')
    ax.set_yticks(range(len(parts) + 1), [p[0] for p in parts] + ['Net profit'])
    ax.tick_params(axis='y', colors=t['ink2'])
    ax.invert_yaxis()
    ax.axvline(0, color=t['axis'], lw=1)
    ax.spines['bottom'].set_visible(False)
    fig.subplots_adjust(left=0.22)
    save(fig, '2-profit-attribution', mode)


def two_lines(d, a, b, labels, title, subtitle, name, t, mode, oos=True, percent=False):
    fig, ax = canvas(t, title, subtitle)
    if percent:
        ax.yaxis.set_major_formatter(lambda v, _: f'{v:+.0f}%' if v else '0')
    if oos:
        mark_oos(ax, d, t)
    ax.axhline(0, color=t['axis'], lw=1)
    ax.plot(d, a, color=t['main'], lw=2)
    ax.plot(d, b, color=t['other'], lw=2)
    gap = 0.04 * (max(a.max(), b.max()) - min(a.min(), b.min(), 0))
    ya, yb = a.iloc[-1], b.iloc[-1]
    if abs(ya - yb) < gap:
        ya, yb = (ya + gap / 2, yb - gap / 2) if ya >= yb else (ya - gap / 2, yb + gap / 2)
    label_end(ax, d.iloc[-1], a.iloc[-1], labels[0], t['main'], t, dy=(ya - a.iloc[-1]) / gap * 8)
    label_end(ax, d.iloc[-1], b.iloc[-1], labels[1], t['other'], t, dy=(yb - b.iloc[-1]) / gap * 8)
    year_axis(ax, d, 900)
    save(fig, name, mode)


def exit_clocks(clocks, t, mode):
    order = ['09:15', '09:16', '09:17', '09:20', '09:22', '09:25', '09:30', '09:45', '10:00']
    minutes = np.array([int(c[:2]) * 60 + int(c[3:]) - 555 for c in order])
    fig, ax = canvas(t, 'From 09:25 on, every later exit gives back more of the gain',
                     'Net profit by next-morning exit time, INR lakh, each half of 2017-2026 (1,114 sessions each)')
    for segment, color in [('First half', t['main']), ('Second half', t['other'])]:
        rows = clocks[clocks.segment == segment].set_index('clock').loc[order]
        ax.plot(minutes, rows.net_lakh, color=color, lw=2, marker='o', ms=6, mec=t['surface'], mew=2)
        ax.annotate(f'{segment}, 2017-22' if segment == 'First half' else f'{segment}, 2022-26',
                    (minutes[-1], rows.net_lakh.iloc[-1]), xytext=(8, 0), textcoords='offset points',
                    va='center', fontsize=10, color=t['ink'], fontweight='bold')
    for clock, note in [('09:15', 'opening print\n(reference only)'), ('09:25', '09:25\nexploratory'),
                        ('09:45', '09:45\nas designed')]:
        x = minutes[order.index(clock)]
        ax.axvline(x, color=t['grid'], lw=1, zorder=0)
        ax.text(x, 1.0, note, transform=ax.get_xaxis_transform(), ha='center', va='bottom',
                fontsize=9, color=t['ink2'])
    shown = ['09:15', '09:20', '09:25', '09:30', '09:45', '10:00']
    ax.set_xticks([minutes[order.index(c)] for c in shown], shown)
    ax.set_xlim(-2, 66)
    fig.subplots_adjust(top=0.72)
    save(fig, '5-exit-clocks', mode)


def main():
    FIGURES.mkdir(exist_ok=True)
    daily = pd.read_csv(RESULTS / 'daily.csv')
    attr = pd.read_csv(RESULTS / 'attribution.csv')
    clocks = pd.read_csv(RESULTS / 'exit_clocks.csv')
    index = pd.read_csv(RESULTS / 'index_overnight_daytime.csv')
    d = pd.to_datetime(daily.date)
    idx_d = pd.to_datetime(index.date)
    for mode, t in THEMES.items():
        equity(daily, t, mode)
        attribution(attr, t, mode)
        two_lines(d, daily[SYSTEM].cumsum() * LAKH, daily['Same signals, exit 15:25 same day'].cumsum() * LAKH,
                  ['Held overnight', 'Closed at 15:25'],
                  'Take away the night and the edge disappears',
                  'Same entries, stops and targets; cumulative net profit, INR lakh',
                  '3-overnight-vs-same-day', t, mode)
        two_lines(d, daily['Only system nights, 15:25 to 09:45'].cumsum() * LAKH,
                  daily['Every night, 15:25 to 09:45'].cumsum() * LAKH,
                  ['Only the system\'s nights', 'Every night'],
                  'The breakout picks the nights worth holding',
                  'Buy at 15:25, sell at 09:45, no stop or target; cumulative net profit, INR lakh',
                  '4-which-nights', t, mode)
        exit_clocks(clocks, t, mode)
        two_lines(idx_d, (np.exp(index.overnight_bps.fillna(0).cumsum() / 1e4) - 1) * 100,
                  (np.exp(index.daytime_bps.cumsum() / 1e4) - 1) * 100,
                  ['Overnight only', 'Trading hours only'],
                  'Nifty 50 rose overnight and fell during trading hours',
                  'Growth of the index counting only close-to-open moves vs only open-to-close moves, %',
                  '6-nifty-overnight-vs-daytime', t, mode, oos=False, percent=True)


if __name__ == '__main__':
    main()
