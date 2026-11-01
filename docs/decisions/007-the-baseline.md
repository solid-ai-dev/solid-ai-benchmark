---
id: "007"
status: Accepted
date: 2026-09-12
category: design
supersedes: []
superseded_by: []
---

# ADR-007: The baseline

## Context

The benchmark compares a release of the templates with what came before it. The
v3.0 split moves templates, so a baseline taken after it could not show what
the move changed. A later question is how a template change is measured at all,
once a contrast pairing trials from different rounds gets no verdict
([ADR-015](015-contrasts-and-verdicts.md)).

## Decision

The baseline runs against the templates at `v2.90.0`, before the v3.0 split,
and a template change runs the baseline and the candidate head to head in the
candidate's round, with one contrast, `candidate − baseline`, and no `none`
arm.

## Rationale

- [ch. 4.2](../architecture/04-solution-strategy.md)'s comparison needs a
  baseline older than the move.
- A contrast pairing trials from different rounds gets no verdict, so round 3
  as the baseline could decide nothing.
- Two arms answer "is the trim free" at the least cost.

## Consequences

What the head-to-head rule changes for earlier rounds:

| Consequence | Effect |
| ----------- | ------ |
| Round 3 is a reference | It stays a reference without a verdict |

## History

Every change to this decision, oldest first:

| Date | Change | Why | Issue |
| ---- | ------ | --- | ----- |
| 2026-09-12 | The baseline runs against `v2.90.0`, before the v3.0 split moves any template | [ch. 4.2](../architecture/04-solution-strategy.md)'s comparison needs a baseline older than the move | solid-ai-templates#1705 |
| 2026-10-28 | A template change runs the baseline and the candidate head to head in the candidate's round, with one contrast, `candidate − baseline`, and no `none` arm; round 3 stays a reference without a verdict | A contrast pairing trials from different rounds gets no verdict, so round 3 as the baseline could decide nothing. Two arms answer "is the trim free" at the least cost | — |
