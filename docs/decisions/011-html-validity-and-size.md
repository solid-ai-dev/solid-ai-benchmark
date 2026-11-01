---
id: "011"
status: Accepted
date: 2026-09-15
category: measurement
supersedes: []
superseded_by: []
---

# ADR-011: HTML validity and size

## Context

HTML validity and size are measured on every trial without a judge. Each has to
count what the arm chose, not what the spec required or what a better solution
naturally adds.

## Decision

HTML validity sets aside errors on `hx-*` attributes, and from round 5 size
reads app code's lines and files against a band of 20 %, with test lines
reported without a verdict.

## Rationale

- The spec requires HTMX; otherwise the validity metric counts how much HTMX a
  trial uses.
- A better solution is often a little bigger, with tests and layering.
- Round 4's source lines missed templates, and its file count was mostly docs,
  templates and committed bytecode.

## Design

The rules size follows from round 5:

| # | Rule | In practice |
| - | ---- | ----------- |
| 1 | App code | Size reads app code's lines and files against a band of 20 %; the smallest change that matters is 40 % |
| 2 | Tests | Test lines are reported without a verdict |
| 3 | Left out | Docs and configuration leave size |
| 4 | Artifacts | Committed generated files count as artifacts nobody asked for |

## History

Every change to this decision, oldest first:

| Date | Change | Why | Issue |
| ---- | ------ | --- | ----- |
| 2026-09-15 | HTML validity sets aside errors on `hx-*` attributes | The spec requires HTMX; otherwise the metric counts how much HTMX a trial uses | — |
| 2026-10-28 | From round 5, size reads app code's lines and files against a band of 20 %, smallest change 40 %; test lines are reported without a verdict; docs and configuration leave size; committed generated files count as artifacts nobody asked for | A better solution is often a little bigger, with tests and layering. Round 4's source lines missed templates, and its file count was mostly docs, templates and committed bytecode | — |
