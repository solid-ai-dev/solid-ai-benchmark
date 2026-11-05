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
| `generate_arm.py` | Makes one arm's file once: fixed text, one non-interactive generation from `agents.md`, under a line budget where the arm has one, or the emitter. Scans prompt and output for leaks, and refuses a file over its budget | `brief.txt`, the templates source | `arms/<arm>/CLAUDE.md`, `generation.json` |
| `harness.py` | Prepares each workspace, runs the agent in isolation, catches reach, freezes the result, keeps the run record current | The specs, the arm files, the change prompt | The run root |
| `reuse.py` | Copies an earlier round's trials and readings into a new root, with their tool lock | An earlier root | The run root, the scoring area |
| `progress.py` | Watches a run: one bar per arm, its voided tries, its cost and the trial running; then its scoring: one bar per arm, the security readings and the trial being scored. Redrawn every 30 s. Read-only | The run records, the scoring area | The console |
| `score.py` | Installs each frozen trial cleanly, runs the hidden suite, the static tools and the adherence checklist, counts scope and cost | The run root, the hidden suite, `scoring-requirements.txt`, `toolconfig/` | `scores/`, `scores-change/` |
| `probes.py` | The structural and web-quality probes, run inside the trial's own interpreter | A trial's tree | Its findings, to `score.py` |
| `security.py` | Seeds each app, signs in its administrator, runs the 11 security and 3 data-protection probes | The scored trees | `security-scores/` |
| `judge.py` | Builds a blind bundle per trial, runs the judge CLI against the rubric, checks every quoted line | The scored trees | `judge/` |
| `control/control.py` | Builds the rubric control: trees damaged or improved on one row each, from two pinned bases | `base.zip`, `base-2.zip`, `overlay/` | A control root for `judge.py` |
| `report.py` | Pairs trials, computes intervals and verdicts, applies withdrawals, prints the report | The run root, the scoring area, `withdrawn.json` | `docs/audits/YYYY-MM-DD-efficacy.md` in the templates source |
| `archive.py` | Copies a round's raw data to the private archive, restores it, recomputes the report's figures from both | The run root, the scoring area | The archive clone, `archived.json` |

## 5.2 Inputs

| File | What it is | Read by |
| ---- | ---------- | ------- |
| `SPEC.md` | The application every arm builds, copied into each workspace | harness |
| `SPEC-thin.md` | The same contract without the practices, for `--spec thin` | harness |
| `brief.txt` | What an adopter would type: domain, stack, personal data, boundaries | `generate_arm.py` |
| `change-prompt.txt` | The change task's prompt, naming everything its grader drives | harness |
| `arms/<arm>/CLAUDE.md` | Each arm's context file. `arms/<arm>/skills/` holds a skills arm's skills | harness |
| `arms/<arm>/generation.json` | How each generated file was made | `report.py` |
| `scoring-requirements.txt` | The scoring tools, resolved once into the tool lock | `score.py` |
| `toolconfig/` | `ruff.toml` and `mypy.ini`, the one configuration every arm is measured under | `score.py` |
| `withdrawn.json` | Metrics withdrawn after grading, keyed by the grader's revision | `report.py` |

## 5.3 The run root

One directory per round, outside this repository, written only by the
harness and `reuse.py`.

| Path | Holds |
| ---- | ----- |
| `<arm>-<block>/` | A trial's pen, such as `skills-2/`: everything the trial owns |
| `<arm>-<block>/<arm>-<block>/` | The trial's workspace, inside its pen |
| `<arm>-<block>/tmp/<trial>/` | The trial's own temporary directory, inside its pen |
| `<arm>-<block>.tar` | The frozen workspace, the only copy scoring reads |
| `run-*.json` | One run record per invocation, rewritten after every trial |
| `home/` | The scratch home: settings with the deny rules, the credential link, the transcripts |
| `void/<trial>-<time>/` | A blocked or reached trial's whole pen, kept and never scored |

An agent checking a clean install puts its virtualenv beside the workspace, out
of the repository. In the pen, that is the trial's own. Run roots from before
round 5c hold each workspace straight in the root, with `tmp/` beside them, and
are still read.

## 5.4 The scoring area

`<run root>-scoring`, beside the root, written only by the scorers.

| Path | Holds |
| ---- | ----- |
| The hidden suite's clone | At the one revision the root is graded under |
| `scoring/<trial>/tree/` | Each trial's extracted tree, until the round is archived; its clean environment goes once it is scored |
| `tool-lock.txt` | The tool versions every trial is measured with |
| `scores/`, `scores-change/` | One score per build trial and per change task |
| `security/`, `security-scores/` | Each trial's probe files, and its readings; the probe environment goes once it is read |
| `judge/` | Each blind bundle, its judgings and the unblinding map |
| `archived.json` | The stamp a verified archive writes, with the hash of every file the report reads |
| `<tool>.running` | A claim that one run of that tool is working here |

## 5.5 Arms

### 5.5.1 The five arms

Every arm starts from an empty git repository holding `SPEC.md`. All but
`none` add a `CLAUDE.md`.

| Arm | Adds | Budget | Asks |
|---|---|---|---|
| `none` | nothing: the bare agent | — | the baseline every file is compared with |
| `short` | one generation from `agents.md`, inline, under a budget | ≤ 40 lines, ≤ 88 characters wide | does a short generated file help |
| `hybrid` | the file the interview generates in its hybrid model, with the templates vendored into the workspace | none | does the model the owner's projects use help |
| `hand` | a hand-written file | ≤ 40 lines | is the effect the templates, or merely having a file |

The report prints each file's measured line count.

### 5.5.2 Trial names

A trial is `<arm>-<block>`: `skills-2` is arm `skills`'s trial in block 2,
paired with `none-2`. Blocks run in order and arms interleave within each,
each block starting one arm later than the last: `none-1`, `inline-1`,
`hybrid-1`, `reference-1`, `skills-1`, then `inline-2`, `hybrid-2`, and so on.

### 5.5.3 How the generated files are made

**One non-interactive invocation per generated arm, and no person answers
questions.** `tests/efficacy/generate_arm.py` hands the generator:

- `INTERVIEW.md` and the chain resolved at `v2.90.0`
- the project brief, [`tests/efficacy/brief.txt`](../../tests/efficacy/brief.txt)
- the arm's output model (inline or hybrid) and, for `short`, its budget

A record of each generation is committed beside its file as
`generation.json`: the release and the chain it resolved, the model, the
CLI's result, both leak scans and the budget check.

Why: a conversation would put the answerer's judgement into the file, and a
re-run would produce a different arm.

**The length rule.** A file's length is its count of newline-terminated
lines.

- `short`'s file must be at most 40 lines, none longer than 88 characters.
- The generator refuses a result over either bound rather than trimming it.
- The instruction asks the model to measure every line against the width
  before answering. It adds no content, only the check.
- `hybrid` has no budget. The interview's hybrid model fixes what it inlines
  and what it refers to.
- `short` and `hand` sit within a line of each other, so `short − hand`
  compares content at a fixed length.

Why: trimming by hand would put a person's judgement into the arm.

**`hybrid` reads the templates from its own workspace.** Its workspace
carries this repository's `templates/` directory at `v2.90.0` under
`docs/solid-ai-templates/templates/`.

- Only that directory is copied. The release also holds this design, and
  the arm would read its brief.
- The copy is kept out of the workspace's index and counts in no size or
  scope metric.

### 5.5.4 What the brief tells the interview

The brief is what an adopter would type:

- the domain in one line, naming discount rules, tax jurisdictions and
  customers
- the stack: Python 3.12, Flask 3, Jinja, HTMX, SQLite, uv, ruff, mypy
  strict, pytest
- personal data: customers are people with a name, email and address; the
  GDPR applies, so a customer may ask for erasure or a copy of their data;
  one administrator signs in
- the system's boundaries and actors: the administrator in a browser and
  another program; the pricing engine importable without the web app; a
  local store; no network

Why each part is there:

- The two extension axes are named because an adopter building this app
  would name them. A brief withholding them measures a product nobody uses.
- The stack is named because the spec fixes it for every arm. An interview
  left to choose might pick FastAPI and build a different app.
- Personal data is named because an adopter storing customers would say
  so, and it is what lets the interview reach for data-protection rules.
- The boundaries are there because establishing a system's boundaries and
  its interfaces is the interview's job.

**What naming the axes affects.** The report states this beside the rows it
touches:

| Measure | Affected |
|---|---|
| Extension points for rule kinds and jurisdictions; the OCP rubric row for them; the change task | Yes. The generated arms' interview was told the axes exist. The other arms read the same axes in `SPEC.md` |
| Extension point for a new export format | **No.** The brief names no export, so every arm meets this axis only through the spec |
| Everything else: task success, cost, quality counts, layering, complexity, the other rubric rows | No |

The export axis is therefore the untouched open-closed probe, and the report
leads its OCP finding with it.

**What the brief never states.** No rule semantics, rounding mode,
precedence or stacking order, route path, API name, error hierarchy or
fixture.

**Checked before the first trial:** two scans guard the generated files.

- The prompt scan is broad. A generation is never handed `SPEC.md`, so any
  spec-only token in the prompt means the wiring is wrong.
- The output scan is narrow. Once the prompt is clean, only data nobody
  could derive, such as a seed SKU, a rule id or a worked figure, counts as
  a leak.
- A hit refuses the generation rather than warning.
