---
id: "015"
status: Accepted
date: 2026-09-18
category: report
supersedes: []
superseded_by: []
---

# ADR-015: Contrasts and verdicts

## Context

A contrast compares two arms within each block, so its differences are paired.
A contrast whose two arms come from different rounds is not paired that way:
anything that moved between the rounds moves its reading too.

## Decision

A contrast gets a verdict only when both its arms run in the same round, and
round 3 read eight contrasts, adding `short − full`.

## Rationale

- Round 2's `full` read Worse because `none` moved between rounds, not the
  file.
- `short − full` asks whether length matters.

## History

Every change to this decision, oldest first:

| Date | Change | Why | Issue |
| ---- | ------ | --- | ----- |
| 2026-09-18 | A contrast crossing rounds gets no verdict | Round 2's `full` read Worse because `none` moved between rounds, not the file | solid-ai-templates#1826 |
| 2026-09-24 | Eight contrasts, adding `short − full` | Does length matter | solid-ai-templates#1767 |
