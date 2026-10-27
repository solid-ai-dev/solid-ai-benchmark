# 5. Building block view

The benchmark is a set of Python scripts under `tests/efficacy/`, each a
command with its own `--self-test`, sharing helpers from `tests/lib.py`.
They pass work to one another through files, never through calls: a run
root the harness writes, and a scoring area the scorers write beside it.

The diagram is a UML component diagram. A box with the component icon is a
script, a folder is a store of files, and a dashed open-headed line is a
dependency with its keyword.

## 5.1 Overview

![The benchmark's building blocks. The running group, generate_arm.py, harness.py and reuse.py, reads the inputs: the specs, the brief, the change prompt, the arms' files, the scoring requirements, the tool configuration and the withdrawn list. It writes the run root, which holds workspaces, tarballs and run records. The scoring group, score.py with probes.py, security.py and judge.py, reads the run root and writes the scoring area. control.py builds damaged and improved trees for the judge. report.py reads the scoring area, checks the archive's stamp and writes the dated report to docs/audits in the templates source. archive.py copies the scoring area and the run root and pushes them to braboj/tariff-runs](../diagrams/building-blocks.png)

| Block | Responsibility | Reads | Writes |
| ----- | -------------- | ----- | ------ |
| `generate_arm.py` | Makes a generated arm's file in one non-interactive call, scans prompt and output for leaks, checks the budget | `brief.txt`, the templates source | `arms/<arm>/CLAUDE.md`, `generation.json` |
| `harness.py` | Prepares each workspace, runs the agent in isolation, catches reach, freezes the result, keeps the run record current | The specs, the arm files, the change prompt | The run root |
| `reuse.py` | Copies an earlier round's trials and readings into a new root, with their tool lock | An earlier root | The run root, the scoring area |
| `score.py` | Installs each frozen trial cleanly, runs the hidden suite, the static tools and the adherence checklist, counts scope and cost | The run root, the hidden suite, `scoring-requirements.txt`, `toolconfig/` | `scores/`, `scores-change/` |
| `probes.py` | The structural and web-quality probes, run inside the trial's own interpreter | A trial's tree | Its findings, to `score.py` |
| `security.py` | Seeds each app, signs in its administrator, runs the 11 security and 3 data-protection probes | The scored trees | `security-scores/` |
| `judge.py` | Builds a blind bundle per trial, runs the judge CLI against the rubric, checks every quoted line | The scored trees | `judge/` |
| `control/control.py` | Builds the rubric control: trees damaged or improved on one row each, from two pinned bases | `base.zip`, `base-2.zip`, `overlay/` | A control root for `judge.py` |
| `report.py` | Pairs trials, computes intervals, verdicts and the escalation, applies withdrawals, prints the report | The run root, the scoring area, `withdrawn.json` | `docs/audits/YYYY-MM-DD-efficacy.md` in the templates source |
| `archive.py` | Copies a round's raw data to the private archive, restores it, recomputes the report's figures from both | The run root, the scoring area | The archive clone, `archived.json` |

## 5.2 Inputs

| File | What it is | Read by |
| ---- | ---------- | ------- |
| `SPEC.md` | The application every arm builds, copied into each workspace | harness |
| `SPEC-thin.md` | The same contract without the practices, for `--spec thin` | harness |
| `brief.txt` | What an adopter would type: domain, stack, personal data, boundaries | `generate_arm.py` |
| `change-prompt.txt` | The change task's prompt, naming everything its grader drives | harness |
| `arms/<arm>/CLAUDE.md` | Each arm's context file | harness |
| `arms/<arm>/generation.json` | How each generated file was made | `report.py` |
| `scoring-requirements.txt` | The scoring tools, resolved once into the tool lock | `score.py` |
| `toolconfig/` | `ruff.toml` and `mypy.ini`, the one configuration every arm is measured under | `score.py` |
| `withdrawn.json` | Metrics withdrawn after grading, keyed by the grader's revision | `report.py` |

## 5.3 The run root

One directory per round, outside this repository, written only by the
harness and `reuse.py`.

| Path | Holds |
| ---- | ----- |
| `<arm>-<block>/` | A trial's workspace, such as `full-2/` |
| `<arm>-<block>.tar` | The frozen workspace, the only copy scoring reads |
| `run-*.json` | One run record per invocation, rewritten after every trial |
| `home/` | The scratch home: settings with the deny rules, the credential link, the transcripts |
| `tmp/<trial>/` | Each trial's own temporary directory |
| `void/<trial>-<time>/` | A blocked or reached trial, kept and never scored |

## 5.4 The scoring area

`<run root>-scoring`, beside the root, written only by the scorers.

| Path | Holds |
| ---- | ----- |
| The hidden suite's clone | At the one revision the root is graded under |
| `scoring/<trial>/tree/`, `venv/` | Each trial's extracted tree and clean environment |
| `tool-lock.txt` | The tool versions every trial is measured with |
| `scores/`, `scores-change/` | One score per build trial and per change task |
| `security/`, `security-scores/` | Each trial's probe environment, and its readings |
| `judge/` | Each blind bundle, its judgings and the unblinding map |
| `archived.json` | The stamp a verified archive writes, with the hash of every file the report reads |
| `<tool>.running` | A claim that one run of that tool is working here |
