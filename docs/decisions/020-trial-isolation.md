---
id: "020"
status: Accepted
date: 2026-10-15
category: isolation
supersedes: []
superseded_by: []
---

# ADR-020: Trial isolation

## Context

A trial runs an agent with a shell on the operator's machine, beside this
repository, the hidden suite, the scoring area and other trials. A trial that
read the hidden suite measures the suite. A trial can also harm the run itself:
in round 4's thin run an agent stopped its dev server with
`Get-Process -Name python | Stop-Process`, which stopped the harness too.

## Decision

A trial is fenced by deny rules and excluded by a scan of its transcript: a
trial that reaches past its own pen is voided and re-run once, a second reach
loses it without stopping the run, and a trial that stops processes by name is
voided.

## Rationale

- A deny rule matches a shell command's prefix, not its paths, so the shell
  cannot be fenced.
- A trial that read the hidden suite measures the suite, so counting it was
  never an option.
- A probe showed a deny rule's glob matches anywhere in a command, chained ones
  included, and lets a stop by PID through.
- A virtualenv the agent put beside its workspace, out of the repository, read
  as a reach and voided two of the first four trials of rounds 5 and 5b,
  though neither read another trial.

## Design

The rules a trial runs under:

| # | Rule | In practice |
| - | ---- | ----------- |
| 1 | Fenced | The trial's file tools are denied every path it may not reach |
| 2 | Excluded | A trial whose transcript still reaches such a path, through the shell, is voided and re-run once; a second reach loses it without stopping the run |
| 3 | No stop by name | The commands that stop processes by name are denied, and one that ran voids the trial |
| 4 | A dead harness | A trial whose harness died under it is voided before the next run re-runs it `--from` that trial |
| 5 | The pen | Each trial's workspace sits in a pen of its own in the run root; the pen is the trial's, and a voided trial takes its whole pen |

## Consequences

What the pen did to the round it arrived in:

| Consequence | Effect |
| ----------- | ------ |
| Round 5c | Round 5b stays as registered and runs again as round 5c |

## History

Every change to this decision, oldest first:

| Date | Change | Why | Issue |
| ---- | ------ | --- | ----- |
| 2026-10-15 | A trial is both fenced and excluded: its file tools are denied every path it may not reach, and a trial whose transcript still reaches one, through the shell, is voided and re-run once; a second reach loses it without stopping the run | A deny rule matches a shell command's prefix, not its paths, so the shell cannot be fenced; a trial that read the hidden suite measures the suite, so counting it was never an option, and deciding after its scores were seen would be | solid-ai-templates#1907 |
| 2026-10-16 | A trial may not stop processes by name: the commands are denied, one that ran voids the trial, and a trial whose harness died under it is voided before the next run re-runs it `--from` that trial | Round 4's thin run ended after one trial when an agent stopped its dev server with `Get-Process -Name python \| Stop-Process`, which stopped the harness too; a probe showed a deny rule's glob matches anywhere in a command, chained ones included, and lets a stop by PID through | solid-ai-templates#1928 |
| 2026-10-29 | Each trial's workspace sits in a pen of its own in the run root; the pen is the trial's, and a voided trial takes its whole pen. Round 5b stays as registered and runs again as round 5c | A virtualenv the agent put beside its workspace, out of the repository, read as a reach and voided two of the first four trials of rounds 5 and 5b, though neither read another trial | — |
