# 6. Runtime view

How the building blocks of chapter 5 work together in the scenarios that
shape the architecture: a build trial, a change task, scoring a trial, and
judging, archiving and reporting a round. The commands are in the
[harness guide](../guides/efficacy-harness.md).

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

| Step | What happens | Design |
| ---- | ------------ | ------ |
| 1 | `--arms` is required. The harness refuses a root inside this repository, an existing workspace, a missing arm file, or a context file above the workspace | §4.1, §7 |
| 2-3 | A preflight sends a trivial prompt through the isolated home. An unauthenticated CLI answers with a result object, not a crash, so without it a whole run could finish without reaching a model | §4.1 |
| 4 | `git init`, `SPEC.md` (the thin spec under `--spec thin`), the arm's `CLAUDE.md`. `hybrid` also gets the templates at the recorded release under `docs/solid-ai-templates/templates/`, kept out of the index | §3.3 |
| 5 | A scratch home with a hard link to the account's credentials, deny rules that keep the file tools out of everything but the trial's own workspace, the launching session's variables removed and recorded | §4.1, §7 |
| 6 | One prompt, the same for every arm, on standard input, at a pinned model id and effort | §4.1 |
| 7 | The agent works alone. Web tools are off, the shell keeps its network, and commands that stop processes by name are denied | §7 |
| 8 | The CLI's result carries its own cost, turns and tokens. A CLI that printed its result but did not exit is ended two minutes later | §4.1 |
| 9 | At $100 or two hours the whole process tree is ended and whatever was printed is kept. The trial is scored as it stands | §1.4 |
| 10 | Every process running from the workspace, its temporary directory or the scratch home is stopped. The transcript is scanned for any call naming this repository, the hidden suite, the scoring area or another trial | §7 |
| 11 | A trial the provider cut off is `blocked`, one with a hit is `reached`. Either moves to `void/` and is re-run once in its place. A second block stops the run, a second reach loses the trial | §1.4 |
| 12 | The workspace becomes a tarball plus its commit hash, and the run record is rewritten, so a stopped run keeps every trial it finished | §4.1 |

How a trial ends:

| Outcome | Ended by | Scored |
| ------- | -------- | ------ |
| `completed` | The agent finished | Yes |
| `budget` | The $100 cap | Yes |
| `timeout` | Two hours | Yes |
| `blocked` | A usage limit, a rate limit, a crash, no result | No, re-run once |
| `reached` | A tool call past the workspace | No, re-run once |
| `refused` | The harness would not start it | No |

## 6.2 A change task

A copy of a frozen build gets a change it was not built for: a
spend-threshold discount and a capped reduced tax rate, neither reachable
by configuration.

![A change task. The harness reads the build trial's tarball from the run root and gets the frozen workspace, unpacks it into a copy and commits its state. It sends the change prompt on standard input to the Claude CLI, the agent makes the change and commits, and the CLI answers with its result. The harness freezes the change trial. score.py reads the change tarball and computes churn, the build suite and the change suite](../diagrams/runtime-change.png)

| Step | What happens | Design |
| ---- | ------------ | ------ |
| 1-3 | Each change task starts from its own build trial, so it carries that arm's context file. Committing the copy first means churn counts only what the agent changed | §4.2 |
| 4 | The prompt names every class, keyword and form field the grader drives. A grader that guessed names grades guessing | §5.4 |
| 5-7 | Same isolation, bounds and outcomes as a build trial, interleaved in the same order | §4.2 |
| 8-9 | Files and lines changed since the commit, the build suite still green, the change suite's acceptance modules passed | §5.4 |

## 6.3 Scoring a trial

Every frozen trial is measured with one ruler, in a clean environment, in
the scoring area.

![Scoring a trial. score.py clones the hidden suite at the root's revision. For each frozen trial it extracts the tarball into a clean environment and installs the package, imports it, boots the app and serves the home page, runs the hidden suite and gets the pass rate and the skipped count, runs the tools from the lock on the package's own paths and gets counts or missing, runs the structure, web and adherence probes, and asks security.py to read the trial, which seeds the app, signs in and runs the 11 security and 3 data-protection probes and answers with two pass rates. Then score.py writes the score](../diagrams/runtime-scoring.png)

| Step | What happens | Design |
| ---- | ------------ | ------ |
| 1-2 | One hidden-suite revision per root. A root graded at another revision is refused | §6.5 |
| 3 | `pip install .` in a clean virtual environment. After the tools install, scoring checks the package still comes from the trial's own tree | §5.1 |
| 4 | `import tariff`, boot, serve `/`. A trial that does not install scores zero on task success | §1.4 |
| 5-6 | The pass rate is over the checks that ran. Skipped checks are counted and the trial flagged | §5.1 |
| 7-8 | The tools are found by importing the installed package and listing top-level packages, never by assuming `src/`. A tool that saw no files records missing | §5.2 |
| 9 | Layering, the import graph, extension points, kind ladders, the public surface, web quality and the 13-item adherence checklist | §5.1, §5.3 |
| 10-12 | A probe the trial keeps from running is lost, not missing, so a trial cannot score higher for not signing in | §5.8 |
| 13 | One JSON score per trial in `scores/` | §6.3 |

## 6.4 Judging, archiving and reporting

Three blind readings per trial, then an archive that is verified by
restoring it, then the report.

![Judging, archiving and reporting. For each trial, until it holds three readings, judge.py builds a blind bundle by stripping the context file, masking markers and shuffling, sends the rubric schema and the bundle to the judge CLI, gets scores from 1 to 5 with quoted lines, and looks up every quote. Then archive.py writes the records, tarballs and readings to tariff-runs, restores them, recomputes and compares the figures, and writes the archived.json stamp. report.py computes pairs, intervals and verdicts, checks the stamp and writes the dated report to docs/audits](../diagrams/runtime-report.png)

| Step | What happens | Design |
| ---- | ------------ | ------ |
| 1 | The context file, the vendored templates and every condition marker are removed. A bundle that still names its arm is not judged | §5.6 |
| 2-3 | The rubric is a JSON Schema, so a score is read by machine. Each primary row has anchors at 1, 3 and 5 in this domain's terms | §5.6 |
| 4 | Every quoted line is looked up in its bundle. A judge that never opened the code still returns plausible numbers | §5.7 |
| 5 | Run records, tarballs without their environments, transcripts and every reading go to a fresh directory of `braboj/tariff-runs` | Ch. 9 |
| 6-7 | The archive is restored into a temporary root and the report's table, contrasts, withdrawals, escalation, reach scan and lost trials are computed from both. Any difference fails | Ch. 9 |
| 8 | K paired differences per contrast, a 10,000-resample bootstrap interval at a recorded seed, the registered verdict rule, and whether the one escalation to K = 5 is owed | §1 |
| 9 | Without the stamp, or once any reading changed since it was written, the report refuses to write under `docs/audits/` | Ch. 9 |
| 10 | The finding table first, then the record behind every cell | §6.3 |
