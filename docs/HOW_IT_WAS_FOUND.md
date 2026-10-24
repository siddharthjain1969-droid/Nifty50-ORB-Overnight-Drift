# How the system was found

The rules were not designed by hand. They came out of a broad search. This page sets out exactly what was done, and how to read the multiple-testing statistics that a search like this produces.

## The research approach

This research follows a deliberate two-step pattern.

**Step 1: fit to understand.** Many different ideas are fitted to a fixed window of data. The goal is not a curve-fitted system to trade. It is to learn what works on this market and what does not: which signal families survive costs, which holding periods matter, where the returns appear. A large search is the instrument for that learning, not a lottery ticket.

**Step 2: test to explain.** Whatever survives step 1 is then tested hard, and the question changes from "does it work?" to "*why* does it work?" Only when a survivor's returns can be traced to a cause does the research move forward.

So the number of configurations tried is not a measure of how desperate the search was. It is a measure of how much of the market's behaviour was mapped before a conclusion was drawn. For this system, step 2 found the cause: the overnight drift.

## The search

- **23,040 configurations** were tested on the same execution engine: ten signal families (EMA crosses, pullbacks, Donchian channels, Bollinger bands, RSI, stochastics, opening ranges, failed breakouts, momentum), three candle sizes, four parameter sets, three filters, long-only or long-and-short, four stop sizes, two targets and four exit styles.
- Only the in-sample period (July 2017 – December 2022) was used to choose.
- A configuration qualified only if it had: profit factor of at least 1.10; at least 0.15 entries per session; a profit in at least four of six half-year folds from 2020 to 2022; a positive combined result across those folds; and a positive stability score (median half-year Sharpe minus 0.25 × its spread).
- The best qualifier from each family was ranked, and the **top five were frozen** (18 September 2026) before any of them was run on 2023 onward.

## The choice

This ORB ranked **fourth of the five** on the in-sample rule. It was chosen *after* all five had been run on the out-of-sample period, and that period had also been examined in earlier rounds of research. So the 2023–2026 results are a **reused out-of-sample period**, not an untouched test. They should be read as strong supporting evidence, not as independent proof.

## Correcting for the search: the deflated Sharpe ratio

Testing thousands of variations guarantees that some look good by luck. The deflated Sharpe ratio (Bailey & López de Prado) asks how likely the observed Sharpe is to reflect real skill, given how many trials were run.

| Measure | Value | Bar |
|---|---:|---:|
| In-sample DSR, 23,040 trials | **≈ 40%** (39.8%) | 95% |
| Range across defensible trial counts | 30.6% – 58.6% | 95% |
| Out-of-sample DSR across the five-candidate shortlist | 88.4% | 95% |

**None of the 23,040 configurations clears 95%.** At the observed Sharpe, about 12 years of in-sample data would be needed to reach that bar; 5.3 years were available.

An earlier calculation reported a DSR of about 10⁻¹³⁰. That figure was an error. Its "luck" benchmark (an expected best Sharpe of 12.3) was far above the best Sharpe any trial actually achieved (2.0). The spread of results had been inflated by high-turnover configurations that lose money to costs reliably, which is not chance. Re-estimated against a null that matches the observed trials to within 6%, the figure is the ≈ 40% above. The largest remaining uncertainty is how correlated the 23,040 trials are. Treating them as roughly 52 independent tests would raise the DSR to about 93%.

## Why the search does not make this luck

The deflated Sharpe ratio answers one narrow question: *if none of the 23,040 ideas had any real edge, how often would the best of them look this good?* It counts trials. It knows nothing about **why** the winner made money. On that question alone it scores this system ≈ 40%.

A lucky configuration has no reason to make its money in one specific, explainable place. This one does, and the evidence for that comes from outside the search:

1. **One identifiable source.** Splitting every trade shows the overnight gap (+₹69.9 lakh) is larger than the entire net profit (+₹44.5 lakh). The entry day barely covers costs.
2. **Change the cause and the result goes with it.** With the same entries, stops and targets, closing at 15:25 instead of holding overnight turns a ₹44.5 lakh profit into a ₹3.9 lakh loss. Re-tuning the breakout's own settings (85 variations) did not improve it. The parameters are not where the edge lives.
3. **The cause exists without the system.** The Nifty 50 itself, with no signals at all, rose about tenfold through its overnight moves from 2017 to 2026 and lost three-quarters through its trading-hours moves.
4. **The cause was not invented here.** The overnight drift has been documented in US stocks, ETFs and index futures since at least 2008, in work published in the Journal of Financial Economics and the Review of Financial Studies. It was not fitted to this dataset.
5. **The selection is better than chance.** Out of sample, none of 5,000 random sets of nights (matched by year and weekday) had gaps as large as the nights the system chose.

Points 1, 2 and 5 come from tests that involve no further searching. They explain the existing results rather than select new ones. Points 3 and 4 are independent of this system altogether. A deflated Sharpe ratio cannot take any of this into account, so the ≈ 40% should be read as **the risk from the search taken by itself**, not as the probability that the system is real.

**What remains open** is whether the effect persists. A real mechanism can weaken, and the breakout's ability to pick the better nights is an empirical regularity, not a law. That is a question about the future that no historical statistic can settle. It is the reason for the futures validation still pending.

The recent record is a live example. From October 2024 the Nifty fell and moved sideways, and the market-wide overnight drift almost disappeared (+1.8 bp a night, against +13.4 bp before). The system's profit fell with it, to its lowest two-year stretch. But the part of the mechanism the system controls held up: its chosen nights still gapped up +29.6 points on average, while the other nights gapped down −16.6. The drawdown stayed within the 2020 record, and the account made a new high in August 2026. When the drift weakens, the system earns less. That is what a drift-harvesting system should do, and it is the opposite of what a lucky fit would show.
