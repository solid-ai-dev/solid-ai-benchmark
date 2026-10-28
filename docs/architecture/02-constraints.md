# 2. Constraints

What the benchmark must work within. Each constraint is a fact about the
setting, not a choice the benchmark made. Chapter 9 records the choices.

## 2.1 Technical constraints

| # | Constraint | Consequence |
| - | ---------- | ----------- |
| 1 | The agent is Claude Code's `claude` CLI, run non-interactively with `claude -p` | The harness bounds a trial by `--max-budget-usd` and a timeout. The CLI has no turn cap |
| 2 | The CLI checks its budget between turns | A trial can pass the $100 cap by one turn's cost |
| 3 | Rounds run on a Windows machine | The CLI is a `.CMD` shim. Prompts go on standard input, and a timeout ends the whole process tree, not the shim |
| 4 | Every trial installs packages | The shell keeps its network. Only the web tools are disallowed, so reach past the workspace is caught by a transcript scan, not prevented |
| 5 | A deny rule matches a command's prefix, not the paths inside it | The file tools can be fenced, the shell cannot |
| 6 | The builder and the judge bill against subscriptions | A round's budget is quota, not invoice. The judge's weekly plan limit sets how fast a round is judged |
| 7 | This repository is public | The hidden suite and the raw runs live in private repositories, `braboj/tariff-hidden-suite` and `braboj/tariff-runs` |
| 8 | Scoring runs Python 3.12 | Every trial's environment is made by the scorer's own interpreter, so a round is scored under one version |
| 9 | A round needs about 0.5 GB free per trial: about 40 GB for round 5's 75 | Each scored trial's environment is about 290 MB |
| 10 | GitHub refuses a file over 50 MB on push | The archive refuses one too |

## 2.2 Organisational constraints

| # | Constraint | Consequence |
| - | ---------- | ----------- |
| 1 | One owner runs and reads every round | No step may wait for a person, and no person may score. A person in the loop would leak judgement into an arm |
| 2 | Rules are registered before the trials they govern | A new hypothesis is committed to its round's registration before its first trial. A check chosen afterwards describes and never decides |
| 3 | K is fixed before a round's first trial: at most 5 after one escalation from 3, or 15 in round 5 | Sampling until an interval clears zero is not possible |
| 4 | `ledger`, a second app, stays sealed | Every round so far measures `tariff`, the development app |
| 5 | The templates live in another repository | Every run names a templates source with `--templates` or `BENCHMARK_TEMPLATES`, and reports land in that source's `docs/audits/` |

## 2.3 Conventions

- Markdown wraps at 88 columns, the width `.markdownlint.json` declares and
  `report.py` reads.
- Diagrams are draw.io files in `docs/diagrams/`, exported beside them as
  PNG at twice the size with a 10 px border.
- Code comments state the substance and cite no ticket number. Docs may
  cite issues and decision records by number.
