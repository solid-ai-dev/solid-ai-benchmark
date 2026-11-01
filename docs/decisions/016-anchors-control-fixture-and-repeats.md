---
id: "016"
status: Accepted
date: 2026-09-19
category: judge
supersedes: []
superseded_by: []
---

# ADR-016: Anchors, the control fixture and repeated judgings

## Context

The judge scores each tree 1 to 5 per rubric row. In rounds 1 and 2 its rows
had no anchors. A row that cannot fall on a damaged tree, or a score that
changes when the same tree is judged again, cannot carry a verdict.

## Decision

The primary judge rows are anchored and checked by the control fixture, and
each tree is judged three times.

## Rationale

- Unanchored, `design` and `maintainability` scored 3 on all 24 trials of
  rounds 1–2.
- Six judgings of one unchanged tree disagreed
  ([ch. 10.6](../architecture/10-quality-requirements.md)).
- Under `claude-opus-5-5` the base and the damaged tree both scored 2 on
  design, each judged on dispatch on concrete classes, so design's anchors were
  moved.

## Design

The rules the anchors and the repeats follow:

| # | Rule | In practice |
| - | ---- | ----------- |
| 1 | Anchored primaries | Each primary row is anchored, and the control fixture checks it |
| 2 | Three judgings | Each tree is judged three times |
| 3 | Design's 1 | Names the damage to layering |
| 4 | Design's 3 | Dispatch on concrete classes with the layers kept apart |

## History

Every change to this decision, oldest first:

| Date | Change | Why | Issue |
| ---- | ------ | --- | ----- |
| 2026-09-19 | The primaries are anchored and checked by the control fixture | Unanchored, `design` and `maintainability` scored 3 on all 24 trials of rounds 1–2 | solid-ai-templates#1827, solid-ai-templates#1829, solid-ai-templates#1830 |
| 2026-09-19 | Each tree is judged three times | Six judgings of one unchanged tree disagreed ([ch. 10.6](../architecture/10-quality-requirements.md)) | solid-ai-templates#1830 |
| 2026-09-25 | Design's 1 names the damage to layering, and dispatch on concrete classes with the layers kept apart is a 3 | Under `claude-opus-5-5` the base and the damaged tree both scored 2, each judged on that dispatch | solid-ai-templates#1767 |
