---
id: "017"
status: Accepted
date: 2026-09-24
category: process
supersedes: []
superseded_by: []
---

# ADR-017: A round's registration

## Context

A round runs under one set of rules. When the spec or the judge changes, an
earlier round's trials were built or scored under other rules. A round can also
run for days, and an edit to the spec during it would leave its trials built
from two specs.

## Decision

A round registers its spec by content, with the harness and the report each
refusing a trial built from other content, and round 3, whose spec and judge
changed, started anew and reused no trial.

## Rationale

- Round 3's spec gained sign-in and customers, and its judge changed.
- Each trial recorded the spec's hash but nothing compared it, so an edit
  during a two-day run would have mixed two specs in one round unseen.

## History

Every change to this decision, oldest first:

| Date | Change | Why | Issue |
| ---- | ------ | --- | ----- |
| 2026-09-24 | Round 3 starts anew with all five arms and reuses no trial | The spec gained sign-in and customers, and the judge changed | solid-ai-templates#1767 |
| 2026-10-29 | A round registers its spec by content, and the harness and the report each refuse a trial built from other content | Each trial recorded the spec's hash but nothing compared it, so an edit during a two-day run would have mixed two specs in one round unseen | — |
