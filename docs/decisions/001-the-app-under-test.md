---
id: "001"
status: Accepted
date: 2026-09-12
category: design
supersedes: []
superseded_by: []
---

# ADR-001: The app under test

## Context

Every trial builds the same app from the same spec, then extends it in a change
task, so the app decides what the benchmark can see. It needs an object model a
design can get right or wrong, room to extend, and tests that tell a correct
answer from a near one.

## Decision

The app every trial builds is `tariff`, a small invoicing app on Flask,
rendered on the server with Jinja and HTMX.

## Rationale

- `tariff` has a natural object model, two extension axes and sharp decimal
  tests.
- Server-rendered Jinja with HTMX is Flask's home ground.

## Alternatives considered

The apps `tariff` was weighed against. The decision named `tariff`'s
strengths, not a reason against each of the others:

| # | Alternative | Outcome |
| - | ----------- | ------- |
| A | `tariff` | Chosen |
| B | `logsift` | Not chosen as the app under test |
| C | `flowkit` | Not chosen as the app under test |
| D | `ledger` | Not chosen as the app under test |
| E | `convert` | Not chosen as the app under test |

## History

Every change to this decision, oldest first:

| Date | Change | Why | Issue |
| ---- | ------ | --- | ----- |
| 2026-09-12 | The app is `tariff`, chosen over `logsift`, `flowkit`, `ledger` and `convert` | Natural object model, two extension axes, sharp decimal tests | solid-ai-templates#1712 |
| 2026-09-12 | Flask stays | Server-rendered Jinja with HTMX is its home ground | solid-ai-templates#1705 |
