# Register a hypothesis

The owner has read round 4's report and wants to know whether a short root
file with task skills delivers what the hybrid file does, before any of
round 5 runs.

Target:

- The question, its one primary measure, its threshold and the result that
  refutes it, committed in the round's registration before any trial runs
  ([ch. 8.1](../../architecture/08-crosscutting-concepts.md))

Assumptions:

- The round's arms are new, so the harness owes work before the first trial
- The minutes come from writing [round 5's registration](../../rounds/round-5.md)
- All times are estimates

## Steps

| # | Who | Step | Time | Notes |
| - | --- | ---- | ---- | ----- |
| 1 | Owner | Reads the last report and the assessment, and names what they could not show | 30 min | Round 4: both hypotheses supported on a few rows, escalation owed |
| 2 | Owner | Writes the question and what varies, one knob inside a block | 20 min | Round 5: the arm varies, each block moves one setting from block A |
| 3 | Owner | Picks each hypothesis's contrast, primary rows and the supported and refuted readings, from the registered margins | 30 min | No new threshold. A new one needs its own reason |
| 4 | Owner | Lists the secondary measures, reported without a verdict | 10 min | Every meter of [ch. 8.6](../../architecture/08-crosscutting-concepts.md), worst trial beside mean, cost |
| 5 | Owner | Lists the harness work owed before the first trial, each with a self test | 15 min | [Round 5's registration, 13.4](../../rounds/round-5.md) |
| 6 | Owner | Opens a pull request adding `docs/rounds/round-N.md`, and merges it | 10 min | Before any trial of the round |
| | | Total | about 2 hours | |

## Findings

| # | Finding | Status |
| - | ------- | ------ |
| 1 | Nothing in the code checked that a round's hypothesis was committed before its first trial. The report now refuses a round whose registration landed on `main` after its first trial started, or differs from `main`'s copy | Settled in [ch. 8.1.1](../../architecture/08-crosscutting-concepts.md) |
| 2 | A hypothesis decides a record in another repository, such as ADR-058 in `solid-ai-templates`. The registration names it, and the record cites the report | Settled in [round 5's registration](../../rounds/round-5.md) |
| 3 | A hypothesis on agreement across trials has one value per arm, so no interval. Its result is descriptive | Settled in [round 4's registration, 12.1](../../rounds/round-4.md) |
| 4 | Once a round's trial has run, its section may not change | Settled in [round 5's registration, 13.4](../../rounds/round-5.md) |
