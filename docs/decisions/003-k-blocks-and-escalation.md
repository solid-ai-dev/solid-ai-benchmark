---
id: "003"
status: Accepted
date: 2026-09-12
category: measurement
supersedes: []
superseded_by: []
---

# ADR-003: K, blocks and escalation

## Context

K is the number of blocks a round runs, so the number of trials per arm. Each
block runs every arm once, and a contrast's interval is computed on its K
paired differences. Too few blocks and the interval decides nothing; adding
blocks until an effect turns significant is sampling to significance.

## Decision

A round fixes K before its first trial, at K = 15 with no escalation from
round 5, while a round registered at K = 3 escalates at most once, to K = 5, on
an effect in either direction.

## Rationale

- Three is the smallest set an interval can be computed on, and the bound on
  escalation stops sampling to significance.
- An escalation owed only to a favourable effect would lean toward "better".
- Run on round 3's per-trial noise, the report's rules decide almost nothing at
  K = 3: H1 is supported in 29 % of rounds when true, and a chance "worse"
  turns up in 36 %. At K = 15 those are 73 % and 12 %.
- On round 4's noise, blocks B and C would contradict block A by chance at any
  affordable K, so round 5 runs block A alone.

## Design

The rules a round's K follows:

| # | Rule | In practice |
| - | ---- | ----------- |
| 1 | K is registered | Fixed by the round's registration before its first trial |
| 2 | Escalation | Only a round registered at K = 3: one step to K = 5, owed by an effect in either direction on any contrast; a row with no interval triggers nothing |
| 3 | Block order | Each block starts one arm later than the last |
| 4 | One lettered block | Round 5 runs block A alone; blocks B and C wait for a later round |

## Consequences

What the history of this decision left behind:

| Consequence | Effect |
| ----------- | ------ |
| Round 3 stays at K = 3 | Its K = 5 escalation is recorded as unrunnable, since its run root no longer exists |

## History

Every change to this decision, oldest first:

| Date | Change | Why | Issue |
| ---- | ------ | --- | ----- |
| 2026-09-12 | K = 3, one bounded escalation to 5 | The smallest set an interval can be computed on; the bound stops sampling to significance | solid-ai-templates#1705 |
| 2026-09-15 | The escalation reads the effect in either direction, on any contrast; a row with no interval triggers nothing | An escalation owed only to a favourable effect would lean toward "better" | — |
| 2026-10-15 | Round 3's K = 5 escalation is recorded as unrunnable, and its report stays at K = 3 | The escalation adds blocks 4 and 5 to round 3's root, which no longer exists; re-running the whole round would not reproduce the three blocks its report read | solid-ai-templates#1767 |
| 2026-10-27 | Round 5 runs block A alone, at K = 15 with no escalation, each block starting one arm later; adherence is held within 8 pp, and H2 reads the mean over pairs of trials. Blocks B and C wait for a later round | The report's rules, run on round 3's per-trial noise, decide almost nothing at K = 3: H1 is supported in 29 % of rounds when true, and a chance "worse" turns up in 36 %. At K = 15 those are 73 % and 12 %. On round 4's noise, B and C would contradict block A by chance at any affordable K | — |
