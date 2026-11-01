---
id: "013"
status: Accepted
date: 2026-09-17
category: report
supersedes: []
superseded_by: []
---

# ADR-013: What the report opens with

## Context

A round's report first had no single headline number. Reading round 1's report,
the owner asked for a score per contrast, and reading the score table, for the
findings first.

## Decision

The report opens with the finding table, and keeps the 1–10 score table only
for contrasts between two files.

## Rationale

- A 1–10 score per contrast was asked for after reading round 1.
- The finding table was asked for after reading the score table.
- Beside the finding table, the score table repeated itself for every contrast
  but those between two files.

## History

Every change to this decision, oldest first:

| Date | Change | Why | Issue |
| ---- | ------ | --- | ----- |
| 2026-09-17 | The report opens with a 1–10 score per contrast, replacing "no single headline number" | Asked for after reading round 1 | solid-ai-templates#1786 |
| 2026-09-17 | The finding table opens the report | Asked for after reading the score table | solid-ai-templates#1789, solid-ai-templates#1791, solid-ai-templates#1796, solid-ai-templates#1798 |
| 2026-09-18 | The score table stays only for contrasts between two files | Beside the finding table it repeated itself | solid-ai-templates#1820 |
