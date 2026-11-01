---
id: "006"
status: Accepted
date: 2026-09-12
category: measurement
supersedes: []
superseded_by: []
---

# ADR-006: The hidden suite

## Context

The hidden suite is the set of acceptance tests every trial is graded by. A
trial that could find the suite would measure the suite, and a suite shaped by
the trials it grades would grade what they happened to build.

## Decision

The hidden suite lives in the private `braboj/tariff-hidden-suite` and is
written and validated before any trial.

## Rationale

- This repository is public, so a suite here is one search away from a future
  trial.
- Written afterwards, the suite would be shaped by the first outputs
  ([validation](../validation.md)).

## History

Every change to this decision, oldest first:

| Date | Change | Why | Issue |
| ---- | ------ | --- | ----- |
| 2026-09-12 | The hidden suite lives in the private `braboj/tariff-hidden-suite` | This repository is public, so a suite here is one search away from a future trial | solid-ai-templates#1705 |
| 2026-09-12 | The hidden suite is written and validated before any trial | Written afterwards, it would be shaped by the first outputs ([validation](../validation.md)) | solid-ai-templates#1714, solid-ai-templates#1715 |
