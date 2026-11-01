---
id: "018"
status: Accepted
date: 2026-09-25
category: measurement
supersedes: []
superseded_by: []
---

# ADR-018: The security probes

## Context

The security and data-protection probes are deterministic checks run against
each trial's app ([ADR-012](012-security-and-data-protection.md)). A probe
reads a trial's failure only if it can tell the trial's choice from its own
assumptions about the app: whether it could sign in, what SQL had to be
interpolated, and what a signed-in client sees.

## Decision

A probe the trial keeps from running is lost, the SQL probe counts a statement
only where an interpolated value cannot be traced to the module's constants,
and a client reads as signed in by what it is shown beside an anonymous client.

## Rationale

- Counted as missing, a probe would drop out of the rate, so a trial would
  score higher for not signing in.
- SQLite binds values only, so a table name, a PRAGMA value or a migration
  script has to be interpolated; round 3's 23 hits were all such, and every
  user value was bound.
- The thin specification lets the dashboard be public, and a public dashboard
  read a CSRF-checked sign-in as forged: 100 % fell to 90.91 %, past round 4's
  9-point threshold.

## Design

The rules the probes follow:

| # | Rule | In practice |
| - | ---- | ----------- |
| 1 | Lost, not missing | A probe the trial keeps from running fails; it never drops out of the rate |
| 2 | Traced SQL | A statement counts only where an interpolated value cannot be traced to the module's constants |
| 3 | Signed in | A client reads as signed in by what it is shown beside an anonymous client, not by `GET /` answering 200 |

## History

Every change to this decision, oldest first:

| Date | Change | Why | Issue |
| ---- | ------ | --- | ----- |
| 2026-09-25 | A probe the trial keeps from running is lost, not missing | Missing would drop it from the rate, so a trial would score higher for not signing in | solid-ai-templates#1767 |
| 2026-09-27 | The SQL probe counts a statement only where an interpolated value cannot be traced to the module's constants | SQLite binds values only, so a table name, a PRAGMA value or a migration script has to be interpolated; round 3's 23 hits were all such, and every user value was bound | solid-ai-templates#1882 |
| 2026-10-15 | The security probes read a client as signed in by what it is shown beside an anonymous client, not by `GET /` answering 200 | The thin specification lets the dashboard be public, and a public dashboard read a CSRF-checked sign-in as forged: 100 % fell to 90.91 %, past round 4's 9-point threshold | solid-ai-templates#1876 |
