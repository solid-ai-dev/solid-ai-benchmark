---
id: "019"
status: Accepted
date: 2026-10-15
category: process
supersedes: []
superseded_by: []
---

# ADR-019: Archive before the report

## Context

A round's run root and scoring area live outside this repository, and nothing
kept a copy of them. Round 3's were deleted with nothing kept.

## Decision

A round is archived to the private `braboj/tariff-runs`, verified by restoring
it and recomputing the report's figures, before the report is written under
`docs/audits/`.

## Rationale

- With round 3's run root and scoring area gone, none of its readings can be
  re-run, re-judged or cross-checked.

## Consequences

What round 3's loss left behind:

| Consequence | Effect |
| ----------- | ------ |
| Round 3's escalation | Recorded as unrunnable ([ADR-003](003-k-blocks-and-escalation.md)) |

## History

Every change to this decision, oldest first:

| Date | Change | Why | Issue |
| ---- | ------ | --- | ----- |
| 2026-10-15 | A round is archived to the private `braboj/tariff-runs`, verified by restoring it and recomputing the report's figures, before the report is written under `docs/audits/` | Round 3's run root and scoring area were deleted with nothing kept, so none of its readings can be re-run, re-judged or cross-checked | solid-ai-templates#1904 |
