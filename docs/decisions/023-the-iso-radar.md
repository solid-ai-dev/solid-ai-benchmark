---
id: "023"
status: Accepted
date: 2026-11-04
category: report
supersedes: []
superseded_by: []
---

# ADR-023: The report's radar reads ISO/IEC 25010:2023

## Context

The pilot's radars were built from what the benchmark happened to measure.
Round 5c's axes were reliability, security, data protection, design,
maintainability, tests and economy, each the share of its rows better than
`none` minus the share worse; round 5d's plotted how far each row moved
over a full scale of its own. Neither says what a backend's quality is, only
which rows moved, and a reader of two rounds could not lay their radars side
by side. The spike of 2026-11-02 (#118) proposed one radar on the
standard's own characteristics, scored as the share of targets met, and the
benchmark proper starts with round 6.

## Decision

From round 6 the report's radar has the eight characteristics of ISO/IEC
25010:2023 as its axes, in the standard's order, each scored as the share of
its targets met and read against `none`, with a marker only past the axis's
margin, a broken build counted against Reliability alone, and the cost shown
above the chart; round 5d's size-based radar stays with round 5d.

## Rationale

- The axes are the standard's, so a radar from any round, or any other
  system, reads the same way, and a thin axis shows as a gap to fill rather
  than being left off.
- A target met or not lands every axis on one scale, 0 to 100 %, which a
  reader takes in at a glance; the rows behind it stay in the appendix.
- A marker past a margin sized from the pilot's noise keeps a few points of
  drift from reading as a difference.
- A build that will not install or boot already fails the Reliability
  target; failing every other axis with it would count one fault eight
  times.

## Design

| # | Rule | In practice |
| - | ---- | ----------- |
| 1 | Eight axes, the standard's order | Functionality, Performance, Compatibility, Usability, Reliability, Security, Maintainability, Flexibility; Safety does not apply to this backend |
| 2 | A target is pass or fail | Each sub-characteristic lists its targets as `QT` rows in the requirements, fixed before round 6's first trial, and changed only by a new registration |
| 3 | A sub-score is the share of targets met | Over the targets measured; a sub-characteristic with no measured target reads not measured, never 0 %, and one with fewer than three is marked |
| 4 | An axis is the mean of its sub-scores | Each sub-characteristic weighs the same, however many targets it has |
| 5 | An arm is the mean over its trials | A median would hide a few broken builds |
| 6 | A broken build counts once | A build that does not install or boot fails Reliability's first target and is left out of every other axis |
| 7 | A marker only past the margin | ▲ where the whole interval of the difference against `none` lies past the axis's margin upward, ▽ downward, a dot otherwise; the margin is half the pooled within-arm standard deviation of the axis in round 5c, rounded up, never under 5 points |
| 8 | Shape as well as colour | Filled up, hollow down, a dot, so the chart reads in black and white |
| 9 | Cost shown, not scored | Dollars per run and the multiple of `none`, centred above each radar |
| 10 | No verdict on the chart | The report's text gives it; the radar describes and decides nothing |
| 11 | One table of sub-scores per axis | In the appendix: each sub-characteristic, each arm's share, the targets, and each arm against `none` with its interval |
| 12 | The pilot keeps its radars | A run holding a round-5 or round-5d arm draws the radar its registration states; every other run draws this one |

## Alternatives considered

| # | Alternative | Outcome |
| - | ----------- | ------- |
| A | The standard's characteristics, each the share of targets met | Chosen |
| B | Keep round 5d's radar by size | Why not: its axes are the benchmark's rows, not qualities, and a 1-point judge move and a 200 % cost move share one scale |
| C | Weight each target the same across an axis | Why not: a sub-characteristic with many probes would swamp one with a single target |
| D | Markers from the arm means alone, no margin | Why not: two means a few points apart would turn a marker on noise |
| E | A verdict word on the chart | Why not: the chart describes; the verdict rests on the deciding rows in the text |

## Consequences

| Consequence | Effect |
| ----------- | ------ |
| The requirements gain `QT` rows | One per target, numbered by the standard's characteristic, fixed before round 6's first trial |
| Thin axes show as gaps | Performance, Compatibility, Usability and Flexibility rest on one or two targets or none until the probes for them land (#119) |
| The margins are sized from round 5c | Recorded in the validation notes; Reliability's 7 points is one build of 15, as round 5d had it |
| Round 6's registration names the radar | Its targets, its margins, and how a run of round 6 is told apart from the pilot's, whose arm names it may reuse |
| Round 5d's report is unchanged | Its radar is registered; this one describes rounds from 6 |

## History

Every change to this decision, oldest first. An issue `solid-ai-templates#N`
is in `solid-ai-dev/solid-ai-templates`, where the benchmark lived until the
split; `#N` is in this repository; a dash means none.

| Date | Change | Why | Issue |
| ---- | ------ | --- | ----- |
| 2026-11-04 | From round 6 the radar reads ISO/IEC 25010:2023: eight axes, the share of targets met, markers past a margin, cost above | The pilot's radars read the benchmark's rows, not the software's qualities; the spike in #118 settled the chart | #121 |
| 2026-11-14 | Rule 10 and alternative E: from round 6 the verdict in the text reads the radar's markers, as ADR-024 decides | Round 5e read by the radar showed the verdict and the chart disagreeing | #165 |
