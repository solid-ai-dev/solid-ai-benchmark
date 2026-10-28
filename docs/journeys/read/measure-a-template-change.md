# Measure a template change

A fork's maintainer has trimmed the templates' chain to cut tokens and
wants to know whether the trim is free.

Target:

- Every quality meter read as held, with tokens down, or a named meter
  that is not ([ch. 4.2](../../architecture/04-solution-strategy.md))

Assumptions:

- The fork is a git clone named with `--templates`
- The trim is batched per file, since each iteration costs a full set of
  trials
- Times and costs come from [Run a round](../run/run-a-round.md). All are
  estimates

## Steps

| # | Who | Step | Time | Notes |
| - | --- | ---- | ---- | ----- |
| 1 | Maintainer | Registers the round: the upstream chain's arm as baseline, the fork's as candidate, both run in it, and the contrast `candidate − baseline` | 30 min | [Ch. 4.2](../../architecture/04-solution-strategy.md) |
| 2 | Maintainer | Generates the baseline's arm from the upstream chain and the candidate's from the fork's | 40 min | [Generate the arms](../prepare/generate-the-arms.md) |
| 3 | Maintainer | Runs, scores, judges and archives, same K, model and spec | 9 to 14 hours | About $325 |
| 4 | Maintainer | Reads each quality meter: free only if every one held and tokens fell | 15 min | Undecided is not enough |
| | | Total | about 1.5 working days | |

## Findings

| # | Finding | Status |
| - | ------- | ------ |
| 1 | Design [ch. 4.2](../../architecture/04-solution-strategy.md) names round 3 as the baseline, but [ch. 8.7.1](../../architecture/08-crosscutting-concepts.md) gives a contrast pairing trials from different rounds no verdict. The baseline and the candidate now run head to head in the candidate's round, with no `none` arm | Settled in [ch. 4.2](../../architecture/04-solution-strategy.md) |
| 2 | At K = 3 a metric's interval is often too wide to read held, and the trim is then unproven, not safe | Settled in [ch. 4.2](../../architecture/04-solution-strategy.md) |
| 3 | A trim that turns any primary dimension worse is rejected | Settled in [ch. 4.2](../../architecture/04-solution-strategy.md) |
| 4 | Tuning against one app overfits to it. `ledger` stays sealed for the final claim | Settled in [ch. 4.2](../../architecture/04-solution-strategy.md) |
