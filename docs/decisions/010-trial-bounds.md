---
id: "010"
status: Accepted
date: 2026-09-12
category: process
supersedes: []
superseded_by: []
---

# ADR-010: Trial bounds

## Context

A trial is one headless agent session, and nothing stops it but a limit the
harness sets. The installed CLI decides which limits are available.

## Decision

Trials are bounded by `--max-budget-usd` and a timeout.

## Rationale

- The installed CLI (2.1.153) has no `--max-turns`.

## History

Every change to this decision, oldest first:

| Date | Change | Why | Issue |
| ---- | ------ | --- | ----- |
| 2026-09-12 | Trials are bounded by `--max-budget-usd` and a timeout | The installed CLI (2.1.153) has no `--max-turns` | solid-ai-templates#1710 |
