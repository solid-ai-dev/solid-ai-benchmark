---
id: "024"
status: Accepted
date: 2026-11-14
category: report
supersedes: []
superseded_by: []
---

# ADR-024: From round 6, verdicts and the screen read the ISO radar

## Context

ADR-023 gave round 6 the ISO radar but kept the verdict on round 5d's
deciding rows: the hidden tests, both probe sets and the judge's five
primaries. Round 5e read by the ISO radar showed the two parting ways. The
radar marked no axis better for `lazyskills`, whose verdict still read
better, and three axes better for `hybrid`, whose verdict rested on the
security checks alone. A reader sees the chart first, so a verdict that
says something else reads as a contradiction. The same rows also drive
round 5d's screen of round 6's arms (13d.9).

## Decision

From round 6 an arm's verdict against `none` is read from the ISO radar's
axes, and round 6's arms are screened on those axes; the pilot rounds keep
the rules they registered, and a pilot round read by the ISO radar is a
draft that says it is post hoc.

## Rationale

- The chart and the verdict read the same markers, so they cannot disagree.
- The axes are the software's qualities, not the benchmark's rows; a
  verdict on them says what a reader asks.
- Each axis already has a margin sized from the pilot's noise (ADR-023,
  rule 7), so a verdict on the axes moves only past that margin.

## Design

| # | Rule | In practice |
| - | ---- | ----------- |
| 1 | Worse on any axis worse | One ▽ makes the verdict **Worse**, whatever the rest gained |
| 2 | Better on an axis better, none worse | At least one ▲ and no ▽ is **Yes** |
| 3 | No clear gain otherwise | Every axis read within its margin is **No** |
| 4 | An axis not measured is not read | Compatibility, with no target yet, neither helps nor hurts; with no axis read at all the verdict is not measured |
| 5 | Cost is shown, not counted | It stays above each radar, as ADR-023 has it |
| 6 | The screen reads the axes | Out on an axis worse; the rest ranked by axes better, then by mean cost; the top four go on, as 13d.9 had it for its rows |
| 7 | An unmeasured axis never holds the screen | An axis no target reaches would hold it for good; a run short of its K still holds it |
| 8 | The summary's table is the radar's | The record's first table lists the ISO axes, each arm's share and marker, not the pilot's clusters |
| 9 | A pilot round is read post hoc | `report.py --iso` writes a draft only, never under `docs/audits/`, opens with a note that the rules came after the results, and keeps its aggregate as `aggregate-iso.json` beside the registered one |

## Alternatives considered

| # | Alternative | Outcome |
| - | ----------- | ------- |
| A | Verdict and screen on the ISO axes | Chosen |
| B | Keep the deciding rows, as ADR-023 had it | Why not: the radar and the verdict disagree on the same page |
| C | Show both, the rows' verdict beside the axes | Why not: two verdicts per arm leave the reader to pick one |
| D | Count the axes better minus worse | Why not: one axis worse would be outweighed by two better, and a loss on one quality is not bought back by another |

## Consequences

| Consequence | Effect |
| ----------- | ------ |
| ADR-023's rule 10 changes | The radar still carries no verdict word, but from round 6 the verdict in the text reads its markers |
| Round 6's arms are chosen post hoc | Round 5e read by the ISO radar ranks `hybrid`, `inline`, `lazyref` and `hand` first, against `reference`, `skills`, `lazyskills` and `lazyref` by 13d.9. The axes were chosen after round 5e's results were seen, so the pick is a selection, not a finding: round 6 runs the four fresh and paired |
| Round 5e's report stands | Its verdicts and its screen under 13d.9 are its registered reading; the post-hoc ISO page describes it and decides nothing |
| Thin axes weigh as much as full ones | Performance and Flexibility rest on one or two targets each until the probes for them land (#119); a move on one counts as a move on Security |

## History

Every change to this decision, oldest first. `#N` is in this repository.

| Date | Change | Why | Issue |
| ---- | ------ | --- | ----- |
| 2026-11-14 | From round 6 verdicts and the screen read the ISO radar's axes | Round 5e read by the ISO radar showed the radar and the verdict disagreeing; the owner chose the axes | #165 |
