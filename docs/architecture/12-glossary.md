# 12. Glossary

Each entry says what a term names. Every threshold and rule that uses it
is in [chapter 8](08-crosscutting-concepts.md) or a round's registration
under [`docs/rounds/`](../rounds/).

| Term | Definition |
| ---- | ---------- |
| Adherence checklist | Thirteen conventions scored on every trial, the bare one included: lint-clean, type-clean, formatted, 80 % coverage, bounded complexity, a `src/` layout, one error hierarchy, no `print` in the library, a library logger with a null handler, packaging metadata, a usable README, discoverable tests and no ticket citations in code. A quality checklist, not a template checklist |
| Arm | One setting of the context-file knob, such as `none` or `hybrid`. Every arm runs once per block |
| Blind judge | The judge as the primer names it: it reads each app without knowing which arm built it. See Judge |
| Block | One pass over every arm, back to back, each block starting one arm later than the last. Trials in one block are paired. A lettered block, such as round 5's block A, names a setting of spec and model |
| Blocked | A trial the provider cut off: a usage limit, a rate limit, a crash or no result. Moved to `void/` and re-run once in its place |
| Bootstrap interval | The range of mean differences a resampling of the K differences produces: 10,000 resamples, 95 %, bias-corrected and accelerated, at a recorded seed |
| Brief | `brief.txt`: what an adopter would type to the generator. It names the domain, the stack, the personal data and the system's boundaries, and nothing the hidden suite checks |
| Builder model | The model the agent runs on, pinned by exact id, such as `claude-sonnet-5` |
| Chain | The templates a project resolves to, in resolution order. A generated arm is built from one chain at one release |
| Change task | A second session that adds a spend-threshold discount and a capped tax rate to a copy of a frozen build |
| Churn | The files touched and lines changed by the change task, counted from the commit of the copy |
| Consistency | How alike an arm's runs come out: the spread of each meter across them, and conventions agreement, the share of checklist items on which every run gives the same verdict |
| Context file | A `CLAUDE.md` the agent reads at the start of a session: project facts and house rules |
| Contrast | Two arms compared within each block, such as `full − none`. K paired differences, one interval, one verdict per metric |
| Control fixture | Trees built from two pinned applications, each damaged or improved on one judge row and each passing the same tests. A primary row counts only if it falls on the damaged trees and rises on the improved |
| Cross-check judge | `gpt-6-astra` through `codex exec`, reading a sample of whole blocks. Its scores are never averaged with the rounds' judge. It withholds a verdict only where the two read opposite directions. Dropped from round 5 |
| Data-protection probes | Three checks on personal data: a customer's email in the logs, an erased customer still in the database file, one customer's export carrying another's data |
| Escalation | The one step from K = 3 to K = 5, owed when a primary's interval contains zero while its mean exceeds the smallest change that matters. Round 5, which registers K = 15, has none |
| Evidence check | Each line the judge quotes, looked up in the bundle it was quoted from. The report prints the share found |
| Freeze | Saving a workspace as a tarball and its commit hash, before anything reads it |
| Generator | The non-interactive invocation that turns the brief and a chain into an arm's file. Nobody answers its questions |
| Held | No improvement shown, and the whole interval inside the metric's margin: nothing got worse. A non-inferiority reading |
| Hidden suite | The acceptance tests in the private `braboj/tariff-hidden-suite`, cloned only at scoring |
| Hidden tests | The primer's name for the hidden suite. See Hidden suite |
| Hybrid model | A context file that copies in the rules whose breaking is silent and no tool enforces, and names the rest, with the templates vendored beside it |
| Inline model | A context file that copies every adopted rule in |
| Judge | The model that scores a blind bundle 1 to 5 per rubric row, with a quoted line as evidence. From round 5 it is `gpt-6-astra` through `codex exec` at effort `high`. Rounds 3 and 4 used `claude-opus-5-5` |
| K | The number of blocks, so the trials per arm, fixed by each round before its first trial: 15 in round 5. A round registered at K = 3 escalates at most to 5 |
| Likely range | The primer's plain name for the bootstrap interval: where the average difference would land if the runs were redone |
| Lost probe | A probe the trial kept from running, such as one that needs a sign-in the app refuses. It fails, never drops out of the rate |
| Lost trial | A trial the provider ended rather than the agent, recorded as blocked. Re-run once in its place. A second loss stops the run |
| Margin | The largest loss a metric may show and still read held, such as 2 points of hidden-test pass rate |
| Missing | A metric that was not measured: a tool that saw no files, failed or timed out. Never recorded as zero |
| Pen | A trial's own folder in the run root, holding its workspace, its temporary directory and whatever the agent puts beside the workspace. Anything past it is a reach |
| Primary dimension | A metric the report leads with and a hypothesis may decide on: the judge's design, readability, maintainability, security and data-protection rows, and the two probe pass rates |
| Reach | A tool call in a trial's transcript that names this repository, the hidden suite, the scoring area or another trial. A reached trial is voided and re-run once |
| Reference model | A context file that only names the templates to read. Round 5's `reference` arm tests it |
| Registered | Committed to a round's registration before the first trial it governs. Only a registered check can decide |
| Round | One run of the experiment under one set of rules, reported once under `docs/audits/` |
| Rubric | The judge's rows: SRP, OCP, LSP, ISP, DIP, naming and abstraction, error design, readability, maintainability, test quality, security and data protection. The primaries are anchored at 1, 3 and 5 |
| Run record | `run-*.json` in the run root: every trial an invocation ran, with its outcome, cost, revisions and the environment names removed |
| Run root | The directory a round's trials live in, outside this repository |
| Scoring area | `<run root>-scoring`, beside the run root: the hidden suite, each trial's tree and environment, and every reading |
| Scratch home | The isolated home each trial's CLI runs under: minimal settings, deny rules, a link to the account's credentials, the transcripts |
| Security probes | Eleven checks: a plaintext password, sign-in failures that reveal accounts, an open redirect, no CSRF on sign-in, a hard-coded secret key, debug on, SQL from untraced values, vulnerable dependencies, missing cookie flags, missing security headers, stack traces in answers |
| Skills | Round 5's arm: a root file of facts and every-turn rules, a trigger table, and one skill per kind of task, loaded when the task needs it |
| Smallest change that matters | The size of effect a metric must show to count as a real change, such as 0.5 judge points |
| Spec | `SPEC.md`: what the app must do, never how it is engineered. The thin spec keeps the contract and drops the practices |
| Templates source | A git clone of `solid-ai-templates` or a fork, named by `--templates`. The arms are built from it and the reports land in it |
| Tool lock | `tool-lock.txt`: the scoring tools' versions, frozen from the first trial scored and installed for every other |
| Trial | One agent session on one arm in one block, named `<arm>-<block>`, such as `short-2` |
| Undecided | The primer's word for no improvement shown: the likely range covers zero, so neither better nor worse can be claimed |
| Verdict | Better, worse or no improvement shown, per metric per contrast, from where the interval lies |
| Verdict vector | Every verdict of a round, printed at the end of the report |
| Void | `void/` in the run root, where a blocked or reached trial's pen is kept and never scored |
| Withdrawn | A metric whose grader measured something else, listed in `withdrawn.json` against the grader's revision. Named with its reason, no number |
| Workspace | A trial's directory: an empty git repository with `SPEC.md` and the arm's files, where the agent works |
