# Measure a template change

A fork's maintainer has trimmed the templates' chain to cut tokens and
wants to know whether the trim is free. Target: a reading of every quality
metric as held, with tokens down, or a named metric that is not.

Assumptions: the fork is a git clone named with `--templates`. The trim is
batched per file, since each iteration costs a full set of trials. Times
and costs are estimated from [Run a round](../run/run-a-round.md).

| # | Step | Minutes | Cost | Notes |
| - | ---- | ------- | ---- | ----- |
| 1 | Registers the comparison: the upstream chain as baseline, the fork's as candidate | 30 | | Design [ch. 4.2](../../architecture/04-solution-strategy.md) |
| 2 | Generates the candidate's arms from the fork's chain | 40 | | [Generate the arms](../prepare/generate-the-arms.md) |
| 3 | Runs, scores, judges and archives, same K, model and spec | 9 to 14 hours | about $325 | |
| 4 | Reads each quality metric: free only if every one held and tokens fell | 15 | | "No improvement shown" is not enough |
| | Total | about 1.5 working days | | |

## Findings

| # | Finding | Status |
| - | ------- | ------ |
| 1 | Design [ch. 4.2](../../architecture/04-solution-strategy.md) names round 3 as the baseline, but [ch. 8.7.1](../../architecture/08-crosscutting-concepts.md) gives a contrast pairing trials from different rounds no verdict. A candidate therefore needs its baseline arms in the same round, which doubles the trials | Open, #18 |
| 2 | At K = 3 a metric's interval is often too wide to read held, and the trim is then unproven, not safe | Settled in [ch. 4.2](../../architecture/04-solution-strategy.md) |
| 3 | A trim that turns any primary dimension worse is rejected | Settled in [ch. 4.2](../../architecture/04-solution-strategy.md) |
| 4 | Tuning against one app overfits to it. `ledger` stays sealed for the final claim | Settled in [ch. 4.2](../../architecture/04-solution-strategy.md) |
