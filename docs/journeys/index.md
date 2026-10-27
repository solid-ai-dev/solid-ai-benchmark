# User journeys

A journey walks one person through one task, step by step, with the minutes and cost
each takes, and ends with findings: what the walk showed missing, unclear or at odds.
Journeys are not normative. The rules are in the
[architecture](../architecture/08-crosscutting-concepts.md), the commands in each
journey.

They are grouped by the stage of a round's life. A round is prepared, run,
checked and read. Each figure is marked measured, with the round it came
from, or estimated.

![User journeys by stage: prepare (register a hypothesis, generate the arms), run (run a round, resume a blocked run), check (check the judge, archive and report) and read (read a report, measure a template change, re-read an old round)](../diagrams/journeys.png)

## Prepare

| Journey | Role | Target |
| ------- | ---- | ------ |
| [Register a hypothesis](prepare/register-a-hypothesis.md) | Owner | A testable question registered before any trial runs |
| [Generate the arms](prepare/generate-the-arms.md) | Operator | Each generated arm's file made once, clean and within budget |

## Run

| Journey | Role | Target |
| ------- | ---- | ------ |
| [Run a round](run/run-a-round.md) | Operator | Every trial built, changed and scored, with none lost |
| [Resume a blocked run](run/resume-a-blocked-run.md) | Operator | A round finished after a usage limit, with no trial counted twice |

## Check

| Journey | Role | Target |
| ------- | ---- | ------ |
| [Check the judge](check/check-the-judge.md) | Owner | Proof that every primary judge row can move |
| [Archive and report](check/archive-and-report.md) | Operator | A verified archive, then the dated report |

## Read

| Journey | Role | Target |
| ------- | ---- | ------ |
| [Read a report](read/read-a-report.md) | Adopter with little technical background | A yes or no on adopting a generated file, in 15 minutes |
| [Measure a template change](read/measure-a-template-change.md) | Maintainer of a fork | Whether a trim is free |
| [Re-read an old round](read/re-read-an-old-round.md) | Owner | A second judge's reading of a finished round |

## Open findings

| Finding | Journey | Issue |
| ------- | ------- | ----- |
| Nothing checks that a hypothesis was committed before its round's first trial | [Register a hypothesis](prepare/register-a-hypothesis.md) | #14 |
| No CI runs the self tests | [Check the judge](check/check-the-judge.md) | #6 |
| No index of reports in this repository | [Read a report](read/read-a-report.md) | #17 |
| A candidate compared with an earlier round's baseline gets no verdict | [Measure a template change](read/measure-a-template-change.md) | #18 |
