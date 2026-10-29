# 6. Runtime view

How the building blocks of chapter 5 work together in the scenarios that
shape the architecture: a build trial, a change task, scoring a trial, and
judging, archiving and reporting a round. The commands are in the
[journeys](../journeys/index.md).

The diagrams are UML sequence diagrams. Each block has a lifeline. A solid
line with a filled head is a call that waits for its answer, a dashed line
is the answer, and a solid line with an open head is a message that does
not wait. A frame marks a choice (`alt`) or a repeat (`loop`), with its
condition in brackets. The numbers on the messages are the steps of each
table.

## 6.1 A build trial

The harness runs every trial the same way and freezes what the agent
leaves before anything reads it.

![A build trial. The operator starts the harness with the arms, K, the model and the templates source. The harness sends a trivial preflight prompt through the Claude CLI and refuses the run without a result. Then, for each trial in order, it initialises the workspace with SPEC.md and the arm's files, prepares the scratch home, deny rules and a clean environment, and sends the prompt on standard input with the pinned model. The agent builds the app and commits, and the CLI answers with cost, turns and tokens. If $100 or two hours is reached, the harness ends the whole process tree. It stops leftover processes and scans the transcript for reach. A blocked or reached trial moves to void and is re-run once in its place. Finally the harness freezes the tarball and rewrites the run record](../diagrams/runtime-build.png)

| Step | What happens | See |
| ---- | ------------ | ------ |
| 1 | `--arms` is required. The harness refuses a root inside this repository, an existing workspace, a missing arm file, or a context file above the workspace | section 6.1, [ch. 11.3](11-risks-and-technical-debt.md) |
| 2-3 | A preflight sends a trivial prompt through the isolated home. An unauthenticated CLI answers with a result object, not a crash, so without it a whole run could finish without reaching a model | section 6.1 |
| 4 | `git init`, `SPEC.md` (the thin spec under `--spec thin`), the arm's `CLAUDE.md`. `hybrid` also gets the templates at the recorded release under `docs/solid-ai-templates/templates/`, kept out of the index | [ch. 5.5.3](05-building-block-view.md) |
| 5 | A scratch home with a hard link to the account's credentials, deny rules that keep the file tools out of everything but the trial's own workspace, the launching session's variables removed and recorded | section 6.1, [ch. 11.3](11-risks-and-technical-debt.md) |
| 6 | One prompt, the same for every arm, on standard input, at a pinned model id and effort | section 6.1 |
| 7 | The agent works alone. Web tools are off, the shell keeps its network, and commands that stop processes by name are denied | [ch. 11.3](11-risks-and-technical-debt.md) |
| 8 | The CLI's result carries its own cost, turns and tokens. A CLI that printed its result but did not exit is ended two minutes later | section 6.1 |
| 9 | At $100 or two hours the whole process tree is ended and whatever was printed is kept. The trial is scored as it stands | [ch. 8.1.4](08-crosscutting-concepts.md) |
| 10 | Every process running from the workspace, its temporary directory or the scratch home is stopped. The transcript is scanned for any call naming this repository, the hidden suite, the scoring area or another trial | [ch. 11.3](11-risks-and-technical-debt.md) |
| 11 | A trial the provider cut off is `blocked`, one with a hit is `reached`. Either moves to `void/` and is re-run once in its place. A second block stops the run, a second reach loses the trial | [ch. 8.1.4](08-crosscutting-concepts.md) |
| 12 | The workspace becomes a tarball plus its commit hash, and the run record is rewritten, so a stopped run keeps every trial it finished | section 6.1 |

How a trial ends:

| Outcome | Ended by | Scored |
| ------- | -------- | ------ |
| `completed` | The agent finished | Yes |
| `budget` | The $100 cap | Yes |
| `timeout` | Two hours | Yes |
| `blocked` | A usage limit, a rate limit, a crash, no result | No, re-run once |
| `reached` | A tool call past the workspace | No, re-run once |
| `refused` | The harness would not start it | No |

### 6.1.1 The protocol in full

Every arm gets one prompt, identical for all:

> Implement the application described in SPEC.md. SPEC.md is the
> approved plan, and nobody will answer questions during this run, so
> build it to the end without stopping for approval. Done means:
> `pip install .` succeeds in a clean virtualenv, your own tests pass,
> and every page and route in the spec works end to end against the
> seed fixture. Commit when done.

The second sentence was added for [round 5b](../rounds/round-5b.md). A trial
runs headless, and the templates ask for a plan's approval before implementation
code, so without it a templates arm could end its trial with a plan and nothing
built.

**Isolation.** Each trial runs apart from the machine and from the others:

| What | How |
|---|---|
| Your global `CLAUDE.md`, hooks, memory, MCP | A scratch home and a minimal settings file |
| The launching session's environment | Its variables, editor, active interpreter and credentials are removed; the names removed are recorded |
| The model | Pinned by exact id; effort fixed |
| The builder's vendor | Never the judge's: each round names its builder models in its registration, none from the vendor of the rounds' judge |
| The web | Web tools disallowed. The shell keeps its network, because every trial installs packages |
| The templates repository | Not mounted |
| Git's stored credentials | Cleared |
| The other trials | Each trial gets a pen of its own in the run root, its workspace inside it; anything past the pen is a reach |
| Temporary files | Each trial gets its own directory, in its pen; entries it left in the machine's are moved into it |
| Leftover processes | Stopped when the trial ends |

**Bounds.** A trial ends at $100 of the CLI's own cost figure or at two
hours. The timeout is the bound that shapes a trial; the budget stops a
runaway. [ch. 10.6](10-quality-requirements.md) gives the figures behind them.

**Records.** Transcript, token usage, turns, wall time and cost are kept,
and the record says which bound ended the trial. The workspace is frozen as
a tarball plus commit hash before scoring. The run record is rewritten after
every trial, so a stopped run keeps every trial it finished.

### 6.1.2 Running notes

- **A dry run** prepares every workspace in `<root>-dry-run`, cleared first,
  and records the command without calling a model. The root stays untouched.
- **`--arms` is required,** for the change task as well. Block 1 runs the
  arms in that order, and each block after it starts one arm later.
- **The templates' revision.** Each trial records the templates source's
  remote, the round's ref and the commit it names. Vendoring reads that ref
  with `git archive`, so the clone's HEAD may move during a run.
- **Vendoring.** `hybrid` and `reference` get the templates' `templates/`
  directory at the ref, under `docs/solid-ai-templates/templates/`, kept out
  of the index through `.git/info/exclude`. For these arms the reach scan
  counts the templates repository as reached only when a call names its
  owner. The judge strips the copy with the context file.
- **The credential file** in the scratch home is a hard link to the account's
  live one, remade before every trial, because another client of the
  account rotates the tokens and an earlier copy would be revoked.
- **The temporary directory.** Git Bash maps `/tmp` to the machine's
  temporary directory whatever `TEMP` says, so an entry that appeared there
  during a trial and that a tool call names is moved into the trial's own.
- **The file tools are fenced** by deny rules that hold under
  `bypassPermissions`: a probe denied one file read the file beside it and
  not the denied one, and read both without the rule.
- **A blocked trial** stops the run unless it was started with
  `--resume-after-block`. The harness then probes the generator every
  `--probe-every` minutes and re-runs the trial in its place once it
  answers. A second block of the same trial, or `--give-up-after` hours
  without an answer, stops the run.
- **`--from <trial>`** starts a new run at that trial in the interleaved
  order. The run record is rewritten after every trial, so a stopped run
  keeps what it finished.

## 6.2 A change task

A copy of a frozen build gets a change it was not built for: a
spend-threshold discount and a capped reduced tax rate, neither reachable
by configuration.

![A change task. The harness reads the build trial's tarball from the run root and gets the frozen workspace, unpacks it into a copy and commits its state. It sends the change prompt on standard input to the Claude CLI, the agent makes the change and commits, and the CLI answers with its result. The harness freezes the change trial. score.py reads the change tarball and computes churn, the build suite and the change suite](../diagrams/runtime-change.png)

| Step | What happens | See |
| ---- | ------------ | ------ |
| 1-3 | Each change task starts from its own build trial, so it carries that arm's context file. Committing the copy first means churn counts only what the agent changed | section 6.2 |
| 4 | The prompt names every class, keyword and form field the grader drives. A grader that guessed names grades guessing | [ch. 8.6.4](08-crosscutting-concepts.md) |
| 5-7 | Same isolation, bounds and outcomes as a build trial, interleaved in the same order | section 6.2 |
| 8-9 | Files and lines changed since the commit, the build suite still green, the change suite's acceptance modules passed | [ch. 8.6.4](08-crosscutting-concepts.md) |

### 6.2.1 The protocol in full

The change task measures how far each design has to be disturbed to take a
change it was not built for.

- It starts from a copy of its own build trial's frozen workspace, so each
  arm's change task still carries that arm's context file.
- The copy's state is committed first. Churn counts only what the agent
  changed after that commit.
- It runs under the same isolation, bounds and outcome rules, interleaved in
  the same order.
- There is one per build trial. A build trial with nothing scorable has
  none.
- Its prompt is fixed in
  [`tests/efficacy/change-prompt.txt`](../../tests/efficacy/change-prompt.txt).

[ch. 8.6.4](08-crosscutting-concepts.md) describes the task and how it is scored.

## 6.3 Scoring a trial

Every frozen trial is measured with one ruler, in a clean environment, in
the scoring area.

![Scoring a trial. score.py clones the hidden suite at the root's revision. For each frozen trial it extracts the tarball into a clean environment and installs the package, imports it, boots the app and serves the home page, runs the hidden suite and gets the pass rate and the skipped count, runs the tools from the lock on the package's own paths and gets counts or missing, runs the structure, web and adherence probes, and asks security.py to read the trial, which seeds the app, signs in and runs the 11 security and 3 data-protection probes and answers with two pass rates. Then score.py writes the score](../diagrams/runtime-scoring.png)

| Step | What happens | See |
| ---- | ------------ | ------ |
| 1-2 | One hidden-suite revision per root. A root graded at another revision is refused | [ch. 8.7.5](08-crosscutting-concepts.md) |
| 3 | `pip install .` in a clean virtual environment. After the tools install, scoring checks the package still comes from the trial's own tree | [ch. 8.6.1](08-crosscutting-concepts.md) |
| 4 | `import tariff`, boot, serve `/`. A trial that does not install scores zero on task success | [ch. 8.1.4](08-crosscutting-concepts.md) |
| 5-6 | The pass rate is over the checks that ran. Skipped checks are counted and the trial flagged | [ch. 8.6.1](08-crosscutting-concepts.md) |
| 7-8 | The tools are found by importing the installed package and listing top-level packages, never by assuming `src/`. A tool that saw no files records missing | [ch. 8.6.2](08-crosscutting-concepts.md) |
| 9 | Layering, the import graph, extension points, kind ladders, the public surface, web quality and the 13-item adherence checklist | [ch. 8.6.1](08-crosscutting-concepts.md), [ch. 8.6.3](08-crosscutting-concepts.md) |
| 10-12 | A probe the trial keeps from running is lost, not missing, so a trial cannot score higher for not signing in | [ch. 8.6.8](08-crosscutting-concepts.md) |
| 13 | One JSON score per trial in `scores/` | [ch. 8.7.3](08-crosscutting-concepts.md) |

### 6.3.1 Scoring notes

- Scoring reads every run record in the root, so a run resumed with `--from`
  scores whole. A trial offered by two records is refused rather than picked.
- It reads the frozen tarball, never the directory the agent worked in.
- A build scoring runs `security.py` on each trial it scored and on any trial
  with no reading yet. Each trial's probe environment is under `security/` in
  the scoring area. Run it alone only to read again, with `--reread`.

## 6.4 Judging, archiving and reporting

Three blind readings per trial, then an archive that is verified by
restoring it, then the report.

![Judging, archiving and reporting. For each trial, until it holds three readings, judge.py builds a blind bundle by stripping the context file, masking markers and shuffling, sends the rubric schema and the bundle to the judge CLI, gets scores from 1 to 5 with quoted lines, and looks up every quote. Then archive.py writes the records, tarballs and readings to tariff-runs, restores them, recomputes and compares the figures, and writes the archived.json stamp. report.py computes pairs, intervals and verdicts, checks the stamp and writes the dated report to docs/audits](../diagrams/runtime-report.png)

| Step | What happens | See |
| ---- | ------------ | ------ |
| 1 | The context file, the vendored templates and every condition marker are removed. A bundle that still names its arm is not judged | [ch. 8.6.6](08-crosscutting-concepts.md) |
| 2-3 | The rubric is a JSON Schema, so a score is read by machine. Each primary row has anchors at 1, 3 and 5 in this domain's terms | [ch. 8.6.6](08-crosscutting-concepts.md) |
| 4 | Every quoted line is looked up in its bundle. A judge that never opened the code still returns plausible numbers | [ch. 8.6.7](08-crosscutting-concepts.md) |
| 5 | Run records, tarballs without their environments, transcripts and every reading go to a fresh directory of `braboj/tariff-runs` | Ch. 9 |
| 6-7 | The archive is restored into a temporary root and the report's table, contrasts, withdrawals, escalation, reach scan and lost trials are computed from both. Any difference fails | Ch. 9 |
| 8 | K paired differences per contrast, a 10,000-resample bootstrap interval at a recorded seed, the registered verdict rule, and whether the one escalation to K = 5 is owed | [ch. 8.1](08-crosscutting-concepts.md) |
| 9 | Without the stamp, or once any reading changed since it was written, the report refuses to write under `docs/audits/` | Ch. 9 |
| 10 | The finding table first, then the record behind every cell | [ch. 8.7.3](08-crosscutting-concepts.md) |

### 6.4.1 Judging notes

- `--repeat 3` tops a trial up to three readings rather than adding three.
  A trial already holding them is left alone, and a run cut short by the
  judge's usage limit resumes by being started again.
- The bundle leaves out scoring's own output: tool caches, the complexity
  report, coverage data and the install's egg-info, whose absolute paths
  name the trial. The leak scan counts the trial's name between path
  separators as a leak.
- The judge's CLI is launched by its resolved path, gets its prompt on
  standard input, and must report its version before any bundle is built.
  A `.CMD` shim ends an argument at its first newline, so a prompt passed as
  one would arrive cut short.
- A CLI the model refused leaves its final message empty. A failed judging
  records the tail of the CLI's output beside it.
- `judge.py` defaults to `gpt-6-astra` through Codex at effort `high`, the
  rounds' judge from round 5. `--cli claude` re-reads an earlier round with
  `claude-opus-5-5`.

### 6.4.2 What an archive holds

`archive.py --into` writes to a fresh directory in a clone of
`braboj/tariff-runs`, and to its `-scoring` sibling there:

- the run records, unchanged
- each frozen tarball, without its virtual environments, found by
  `pyvenv.cfg`, and without tool caches or bytecode, with the original's
  hash recorded
- the transcripts, and nothing else of the scratch home, which holds the
  account's credentials
- a marker per voided directory, whose name the report reads
- the scores, change scores, security readings, judgings, the unblinding map
  and the tool lock. The judge's bundles are rebuilt from the trees

`ARCHIVE.json` beside them lists every file with its hash, the templates and
hidden-suite revisions, and what was stripped from each tarball. A file over
50 MB is refused, because a push would be. Commit and push the archive
before the report's pull request.

`--restore` makes a working root from an archive. The records' tarball and
voided paths point at the restored copies, and each transcript gets back its
original time, which the report reads to tell a re-run's sessions from those
of the blocked attempt before it. Scoring and judging then run on it as on
any root, which is how a later round re-reads an earlier one.

### 6.4.3 The escalation in the report

The report computes the one escalation to K = 5 of a round registered at
K = 3, so nobody decides it by eye. At K = 3 it names the rows that owe it and
the `--k 5 --from` run that settles it, from the trial the rotated order puts
first in block 4. At K = 5 it reads the first three blocks alone, prints their
verdicts beside the K = 5 ones, and flags an escalation no row owed.

Round 5 registers K = 15 and no escalation. Its report says how many of the 15
blocks are in, and calls a run short of them part-run. The harness refuses
`--k` above 5, or above 15 for a run holding a round-5 arm, and the report
refuses a run past it.

### 6.4.4 Reusing an earlier round's trials

`reuse.py` copies what the report reads for each trial from an earlier root:
its run record, tarball, transcripts, score, judgings and security reading,
marked with where they came from. The earlier round's tool lock comes along,
so both rounds are measured with one ruler. Nothing copied is measured again
unless a tool is given `--rescore`, `--rejudge` or `--reread`. Round 2 reused
round 1's `full` and `hand`. Later rounds reuse nothing, because the spec and
the judge changed.
