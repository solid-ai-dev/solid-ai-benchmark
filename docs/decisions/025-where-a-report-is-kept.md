---
id: "025"
status: Accepted
date: 2026-11-15
category: process
supersedes: []
superseded_by: []
---

# ADR-025: Where a round's report is kept

## Context

Rounds 1 to 5e wrote their reports into the templates source's `docs/audits/`,
beside the templates they measured. The templates repository is removing that
folder (solid-ai-templates#2448): a report belongs to the tool that makes it,
not to the templates. The report script also needed a templates source only to
know where to write, and with a fork named as the source a report could land
in the fork.

## Decision

A round's report, its appendix, record and radars are kept in this repository,
under `docs/reports/`, and the stamp guard protects that folder.

## Rationale

- The report, its registration under `docs/rounds/` and the code that wrote it
  sit in one repository, so a reader follows a round from question to answer
  without leaving it.
- The default output no longer depends on which templates clone a run names,
  so a report cannot land in a fork by accident.
- The guard reads a folder in its own repository, so writing a report needs no
  templates source.

## Design

| # | Rule | In practice |
| - | ---- | ----------- |
| 1 | The default output is this repository's `docs/reports/` | `report.py` with no `--out-dir` writes there |
| 2 | Any `docs/reports/` is a record | A report written to a folder ending in `docs/reports` needs the round archived as it stands; anywhere else it is a draft, as `docs/audits/` was |
| 3 | A post-hoc draft stays out | `report.py --iso` on a pilot round refuses a folder in or under any `docs/reports/` |
| 4 | Earlier reports move unchanged | Rounds 1 to 5e's 25 files are copied from the templates at 9f6b6afa, links only rewritten; none needed it |

## Alternatives considered

| # | Alternative | Outcome |
| - | ----------- | ------- |
| A | This repository's `docs/reports/` | Chosen |
| B | Keep writing into the templates source's `docs/audits/` | Why not: the templates repository removes the folder |
| C | The audits repository, `solid-ai-audits`, with the 360 audits | Why not: those audit the templates; a round's report reads the benchmark's own registration and code |
| D | Only a folder the operator names, with no default | Why not: a record with no fixed home is not found again, and the guard needs a folder to protect |

## Consequences

| Consequence | Effect |
| ----------- | ------ |
| `report.py` | Writes to `docs/reports/` by default; the guard reads that folder |
| The rounds index | Links every report in `docs/reports/` |
| The round registrations | Rounds 4 and 5 still name `docs/audits/`; a registration is fixed once its first trial has run |
| Reports in the templates' history | Stay in its past commits; the copies here are the ones linked |

## History

Every change to this decision, oldest first. An issue `solid-ai-templates#N`
is in `solid-ai-dev/solid-ai-templates`, where the benchmark lived until the
split; `#N` is in this repository; a dash means none.

| Date | Change | Why | Issue |
| ---- | ------ | --- | ----- |
| 2026-11-15 | A round's report is kept in this repository's `docs/reports/`, and the stamp guard protects it | The templates repository removes `docs/audits/` | #170 |
