# Requirements

- **Scope:** what the benchmark must do, by capability, and how well, by
  ISO/IEC 25010:2023 characteristic.
- **Terms:** defined in the [glossary](architecture/12-glossary.md). The
  reasons behind each rule are in
  [chapter 8](architecture/08-crosscutting-concepts.md).
- **IDs:** `FR-<capability>-<n>` or `QG-<characteristic>-<n>` for the
  benchmark, `QT-<characteristic>-<n>` for a target the app under test is
  scored on; cite a requirement by its ID.
- **Numbering:** a new requirement takes the next free number; a removed
  ID is never reused. Before the baseline, a section may be renumbered.
- **Baseline:** none declared yet, so a requirement may still be reworded
  in place.
- **Coverage:** [coverage.md](coverage.md) names, for each functional
  requirement, the self-test checks that prove it.

## Functional requirements

- **Delivered by column:** the script expected to deliver a requirement
  (-: a removed row). The scripts, all under `tests/efficacy/`:
  - **Harness:** `harness.py`, which runs the trials.
  - **Scorer:** `score.py`, which scores a frozen build.
  - **Security reader:** `security.py`, which runs the probes.
  - **Quality reader:** `quality.py`, which runs the reliability, performance
    and portability probes.
  - **Judge:** `judge.py`, which bundles a build and has a model score it.
  - **Report:** `report.py`, which reads a round and writes its report.
  - **Archive:** `archive.py`, which carries a round to the private archive.
  - **Reuse:** `reuse.py`, which brings an earlier round's trials into a run.
  - **Arm generator:** `generate_arm.py`, which writes a generated arm's file.
  - **Control builder:** `control/control.py`, which builds the judge's
    control trees.
  - **Reuse:** `reuse.py`, which brings an earlier round's trials into a
    run root.
  - **Owner:** a working practice no script carries out.

### 01 Registration

| ID | Requirement | Delivered by |
| -- | ----------- | ------------ |
| FR-01-01 | The benchmark shall refuse, from round 5, a round whose registration landed on `main` after its first trial started, a merge counting at the merge; `main` read as the local branch, else as `origin/main`, and a clone holding neither refused with its reason. | Report |
| FR-01-02 | The benchmark shall refuse a registration that differs from `main`'s copy or has changes not committed. | Report |
| FR-01-03 | The benchmark shall refuse a trial built from a spec or prompt other than the ones its round registers, compared by content; a named round's trials each against its entry's spec and the prompt pinned for their task. | Report |
| FR-01-04 | The benchmark shall refuse a trial with something to score that records no spec or no prompt. | Report |
| FR-01-05 | The benchmark shall check the spec before every trial, and refuse unbuilt the trials after an edit made mid-run. | Harness |
| FR-01-06 | The benchmark shall record each trial's start with its UTC offset, and refuse a start with none. | Harness, Report |
| FR-01-07 | The benchmark shall land each registration through a pull request's squash or rebase merge. | Owner |

### 02 Reading a result

| ID | Requirement | Delivered by |
| -- | ----------- | ------------ |
| FR-02-01 | The benchmark shall run the arms of a block back to back, each block starting one arm later than the last. | Harness |
| FR-02-02 | The benchmark shall read a contrast as better when its 95 % bootstrap interval lies wholly on the improving side of zero, worse when wholly on the other, and no improvement shown when it contains zero. | Report |
| FR-02-03 | The benchmark shall read a metric as held only when the whole interval lies inside its margin, a relative margin taken on the baseline arm's mean. | Report |
| FR-02-04 | The benchmark shall give every primary row and every per-KLOC row its registered margin. | Report |
| FR-02-05 | The benchmark shall hold round 5's adherence within 8 pp, one checklist item of 13. | Report |
| FR-02-06 | The benchmark shall read app code's lines and files, from round 5, as held on a rise wholly inside the band and worse only on one wholly past it. | Report |
| FR-02-07 | The benchmark shall count an adherence gain only where the hidden-test pass rate held. | Report |
| FR-02-08 | The benchmark shall call a trim free only where every metric held. | Report |
| FR-02-09 | The benchmark shall call every interval descriptive below K = 6. | Report |

### 03 Trial count

| ID | Requirement | Delivered by |
| -- | ----------- | ------------ |
| FR-03-01 | Removed: the escalation to K = 5 belonged to rounds registered at K = 3, retired with rounds 1 to 4. | - |
| FR-03-02 | Removed: with FR-03-01. | - |
| FR-03-03 | Removed: with FR-03-01. | - |
| FR-03-04 | The benchmark shall refuse a block past the K a round registers. | Harness |
| FR-03-05 | The benchmark shall call a run short of its registered K part-run, and give none of its verdicts as the round's. | Report |

### 04 Failed and lost trials

| ID | Requirement | Delivered by |
| -- | ----------- | ------------ |
| FR-04-01 | The benchmark shall score as it stands a trial that completed, or that the budget cap or the timeout ended. | Harness, Scorer |
| FR-04-02 | The benchmark shall leave unjudged a build that did not install, with its judge rows missing. | Judge, Report |
| FR-04-03 | The benchmark shall never re-run a failed trial. | Harness |
| FR-04-04 | The benchmark shall treat as lost a trial the CLI ends with any error but the budget cap: a usage limit, a rate limit, a crash or no result. | Harness |
| FR-04-05 | The benchmark shall re-run a lost trial once, in its own place in the order, and read the re-run in its stead. | Harness, Scorer |
| FR-04-06 | The benchmark shall keep a lost trial's workspace under the run's `void/` directory, and never score it. | Harness |
| FR-04-07 | The benchmark shall stop the run at a second loss of the same trial. | Harness |
| FR-04-08 | The benchmark shall resume a run that stopped part way with `--from` at the trial named, keeping the order. | Harness |
| FR-04-09 | The benchmark shall, after a lost trial, probe the generator at once and then on an interval, and re-run the trial when it answers; `--stop-on-block` stops the run instead. | Harness |
| FR-04-10 | The benchmark shall ask the generator once before a trial whose ceiling outlasts the account's token, so the trial starts on a fresh token where the CLI renews it. | Harness |

### 05 Isolation

| ID | Requirement | Delivered by |
| -- | ----------- | ------------ |
| FR-05-01 | The benchmark shall run each trial under a scratch home and minimal settings, so the owner's global `CLAUDE.md`, hooks, memory and MCP never reach it. | Harness |
| FR-05-02 | The benchmark shall run each trial in a cleaned environment, without the launching session's variables, interpreter or keys. | Harness |
| FR-05-03 | The benchmark shall deny the file tools every path outside the trial's own workspace. | Harness |
| FR-05-04 | The benchmark shall disallow the web tools in every trial. | Harness |
| FR-05-05 | The benchmark shall let no Git credential helper answer inside a trial. | Harness |
| FR-05-06 | The benchmark shall deny every command that stops a process by name. | Harness |
| FR-05-07 | The benchmark shall flag every tool call in a transcript that names a forbidden path or repository, void the trial and re-run it once. | Harness |
| FR-05-08 | The benchmark shall scan every transcript again, under the current rule, when it writes a report. | Report |
| FR-05-09 | The benchmark shall stop every process started from a trial's directories before the trial is frozen, and record each one. | Harness |

### 06 Missing values

| ID | Requirement | Delivered by |
| -- | ----------- | ------------ |
| FR-06-01 | The benchmark shall record as missing, with the reason, a metric whose tool scanned nothing, failed or timed out. | Scorer |
| FR-06-02 | The benchmark shall never count a grader's skipped check as passed. | Scorer |
| FR-06-03 | The benchmark shall count as lost, against the rate, a probe the trial keeps from running. | Security reader |
| FR-06-04 | The benchmark shall leave the rate missing for a probe it could not run itself. | Security reader |
| FR-06-05 | The benchmark shall show an unmeasured value as not measured. | Report |
| FR-06-06 | The benchmark shall read the app's pages signed in as the seeded administrator, and never measure a page answered with the sign-in's redirect: a form row the app keeps from running reads failed, a measured row missing. | Scorer |
| FR-06-07 | The benchmark shall count as accessibility violations only the rules of WCAG 2.1 levels A and AA, and keep each violated rule's id. | Scorer |

### 07 Tools and interpreter

| ID | Requirement | Delivered by |
| -- | ----------- | ------------ |
| FR-07-01 | The benchmark shall freeze the tools to a lock at the first trial scored, and install every later trial's tools from it. | Scorer |
| FR-07-02 | The benchmark shall keep the lock to the tools, never a trial's own packages. | Scorer |
| FR-07-03 | The benchmark shall run the tools under `toolconfig/` only, never a configuration the agent wrote. | Scorer |
| FR-07-04 | The benchmark shall score every build on the spec's Python, and refuse a round scored on two. | Scorer, Report |
| FR-07-05 | The benchmark shall point the tools at the installed package and every top-level package, never an assumed `src/`. | Scorer |
| FR-07-06 | The benchmark shall install every extra and dependency group a trial declares, within the lock, before it runs coverage. | Scorer |
| FR-07-07 | The benchmark shall record coverage as missing, with the conflict, where a declared test dependency conflicts with the lock. | Scorer |

### 08 Blind judging

| ID | Requirement | Delivered by |
| -- | ----------- | ------------ |
| FR-08-01 | The benchmark shall give the judge a bundle holding the trial's code without its context file, vendored templates, skills or scoring output. | Judge |
| FR-08-02 | The benchmark shall judge the bundles in an order shuffled at a recorded seed, with the unblinding map out of the judge's reach. | Judge |
| FR-08-03 | The benchmark shall refuse a bundle that still names its arm. | Judge, Arm generator |

### 09 Scoring

| ID | Requirement | Delivered by |
| -- | ----------- | ------------ |
| FR-09-01 | The benchmark shall keep the hidden suite outside every workspace, in a scoring area the trial is denied. | Harness |
| FR-09-02 | The benchmark shall install each build in a clean virtualenv and boot it the way the hidden suite does. | Scorer |
| FR-09-03 | The benchmark shall set aside HTML validity errors on HTMX's `hx-*` attributes, and count the rest. | Scorer |
| FR-09-04 | The benchmark shall count app code apart from tests, docs and configuration, and name artifacts nobody asked for. | Scorer |
| FR-09-05 | The benchmark shall read the adherence checklist's 13 items on every arm, the bare arm included. | Scorer |
| FR-09-06 | The benchmark shall probe each build's layering, import graph, extension points, kind ladders, boolean parameters, public surface, IO isolation and hygiene. | Scorer |
| FR-09-07 | The benchmark shall count every edited and new file as change-task churn, and nothing in an environment. | Scorer |
| FR-09-08 | The benchmark shall state in the change prompt everything the grader drives. | Harness |
| FR-09-09 | The benchmark shall have the change-task acceptance modules written before any change-task run. | Owner |
| FR-09-10 | The benchmark shall grade at the hidden suite's newest revision, or at the one named for the scoring, so a root begun at one revision is finished at it. | Scorer |

### 10 The judge

| ID | Requirement | Delivered by |
| -- | ----------- | ------------ |
| FR-10-01 | The benchmark shall judge each tree three times, and average its scores. | Judge, Report |
| FR-10-02 | The benchmark shall judge from round 5 with `gpt-6-astra` through `codex exec` at effort `high`, recording the model and the effort. | Judge |
| FR-10-03 | The benchmark shall let the judge read the bundle and do nothing else. | Judge |
| FR-10-04 | The benchmark shall count a cross-check's agreement per row, over the trials both judges read. | Report |
| FR-10-05 | The benchmark shall withdraw a verdict's direction where the other judge's mean paired difference has the opposite sign, and keep it otherwise. | Report |
| FR-10-06 | The benchmark shall print the share of the judge's quotes found in its bundle. | Report |
| FR-10-07 | The benchmark shall refuse to build a control tree whose mutation did not land, and print each change it read back. | Control builder |
| FR-10-08 | The benchmark shall refuse a control base archive whose sha256 is not the one recorded. | Control builder |
| FR-10-09 | The benchmark shall count a primary only if it falls on the control tree that damages it and rises on the one that improves it. | Owner |

### 11 Security and data protection

| ID | Requirement | Delivered by |
| -- | ----------- | ------------ |
| FR-11-01 | The benchmark shall fail the 11 security and 3 data-protection probes on an app built to fail them, and pass them on one built to pass them. | Security reader |
| FR-11-02 | The benchmark shall sign a probe in the way the hidden suite does. | Security reader |
| FR-11-03 | The benchmark shall count every planted secret, debug and assembled-SQL form in the source, and no safe one. | Security reader |
| FR-11-04 | The benchmark shall count every known vulnerability of every installed package. | Security reader |
| FR-11-05 | The benchmark shall fail the CSRF probe on a sign-in that accepts a forgery, and pass it on one that refuses it. | Security reader |
| FR-11-06 | The benchmark shall read each probe rate as the security reader files it. | Report |

### 12 The report

| ID | Requirement | Delivered by |
| -- | ----------- | ------------ |
| FR-12-01 | The benchmark shall give no verdict to a paired contrast crossing rounds, and count it nowhere. | Report |
| FR-12-02 | The benchmark shall read unpaired, with a verdict, a contrast a round registers against an earlier round's arm. | Report |
| FR-12-03 | The benchmark shall print every declared contrast its arms ran, and no other. | Report |
| FR-12-04 | The benchmark shall print a neutral row without a verdict. | Report |
| FR-12-05 | The benchmark shall write a report, an appendix and a record for each round, each linking the next. | Report |
| FR-12-06 | The benchmark shall draw one radar panel per file arm against `none`, in both themes, each axis better minus worse over its rows with a verdict. | Report |
| FR-12-07 | In the pilot rounds the benchmark shall give each approach Yes where a deciding measure is better and none worse, Worse where any is worse, and No where none moved. | Report |
| FR-12-08 | Removed: rounds 1 and 2's security checks, declared after their runs, were printed apart; from round 3 every check is a probe declared before the run, and those rounds are retired. | - |
| FR-12-09 | The benchmark shall blank a withdrawn metric on every run its grader's revision graded, and keep it on the others. | Report |
| FR-12-10 | The benchmark shall fix a fault found in its instruments, validate the fix, re-score in full every round that reads the faulty scores, and replace each report with a dated note keeping the verdicts it replaces. | Scorer, Report, Owner |
| FR-12-11 | Removed: merged into FR-12-10. | - |
| FR-12-12 | From round 6 the benchmark shall draw one radar per file arm against `none` on the eight ISO/IEC 25010:2023 characteristics, each axis the share of its targets met, with a marker only past the axis's margin, a broken build counted against Reliability alone, the cost shown above and one table of sub-scores per axis in the appendix. | Report |
| FR-12-13 | The benchmark shall read round 5e's H7 to H9 under round 5d's rules, each a map arm against the arm it answers, unpaired where the arms ran in different rounds. | Report |
| FR-12-14 | The benchmark shall count, per trial of an arm whose file points at the templates, each template read from the vendored copy or loaded as a skill, the turn it happened at, and how many came before the trial's first write to a file of its own. | Report |
| FR-12-15 | The benchmark shall screen round 6's candidates against `none` as round 5d registers: out on a deciding row worse, the rest ranked by rows better and then by mean cost, the top four kept. | Report |
| FR-12-16 | From round 6 the benchmark shall give each approach its verdict from the ISO radar's axes: Yes where an axis is better and none worse, Worse where any is worse, No where none moved; and the summary's axis table shall be the ISO radar's. | Report |
| FR-12-17 | The benchmark shall screen round 6's candidates on the ISO radar's axes: out on an axis worse, the rest ranked by axes better and then by mean cost, the top four kept; an axis no target measures shall neither hold nor move it, and an axis that lists targets but has no reading yet shall hold it. | Report |
| FR-12-18 | The benchmark shall read a pilot round by the ISO radar only as a draft that says it is post hoc, never under `docs/reports/`, and keep its aggregate beside the registered one; a run read by the ISO radar shall take no cross-check. | Report |
| FR-12-21 | From round 6 the benchmark shall load each trial's quality reading beside its security reading and read each quality probe as an ISO target: a lost probe fails, a missing one is not measured, and the latency target is not measured until its cutoff is registered. | Report |
| FR-12-22 | From round 6 the benchmark shall read functional correctness as one target per hidden-suite build module, met only where every check in it ran and passed; a module the trial's report lacks is not measured where the suite's revision did not hold it, and not met where it did; a suite that ran out of time fails every module. | Report |
| FR-12-23 | The benchmark shall read a pilot round by the ISO radar with the targets it had before round 6, and by round 6's only where asked, refusing that request where no pilot draft would read it. | Report |

### 13 Records and archive

| ID | Requirement | Delivered by |
| -- | ----------- | ------------ |
| FR-13-01 | The benchmark shall write the run record as every trial starts and ends, with the CLI's version. | Harness |
| FR-13-02 | The benchmark shall write `generation.json` beside every file the arm generator writes. | Arm generator |
| FR-13-03 | The benchmark shall archive every reading, judging, map and lock, with a hash per file, and fail the verify on a changed one. | Archive |
| FR-13-04 | The benchmark shall refuse to write a report under `docs/reports/` once a reading changed since the archive was verified. | Archive, Report |
| FR-13-05 | The benchmark shall restore an archive so it reads as the original root does, its records pointing at the restored files. | Archive |
| FR-13-06 | The benchmark shall build a map arm's root from the brief, the chain and the templates' manifest alone, the same moments in the same order for both map arms, and each `lazyskills` skill holding one template verbatim. | Arm generator |
| FR-13-07 | The benchmark shall give every arm's root the same project facts: the brief, verbatim under the title, the emitted roots too, which names the stack the spec fixes and no tooling. | Arm generator |
| FR-13-08 | The benchmark shall refuse a built arm file that names a tool. | Arm generator |
| FR-13-09 | The benchmark shall write a round's report, by default, to its own `docs/reports/`, with no templates source named. | Report |
| FR-13-10 | The benchmark shall build every arm a round runs by script, with no model call, and fail its self-test where a committed arm differs from what the script builds at the arm's recorded ref. | Arm generator |
| FR-13-11 | From round 6 the benchmark shall run a round only as `--round` names it, under its registration: refusing a round not registered, an arm it does not register, a K past its K, and a spec, build prompt or change prompt other than the ones it pins by digest. | Harness |
| FR-13-12 | The benchmark shall write a named round and its registration's digest in the run record, and the round, task, arm and block in every trial record, keeping them when a recovery rewrites the record; and refuse a run in a root whose records name another round or digest, or where a named round and records naming none would meet, a header naming no round over trials that name one counting as a named round's record. | Harness |
| FR-13-13 | The benchmark shall read a round from its run records where they name one, refuse records of a named round missing its identity, in a trial or in the header, and infer the round from the arms only for records naming none. | Report |
| FR-13-14 | The benchmark shall call a round of two tasks complete only with both at K for every arm, a change task counting whatever its arm's build trial did. | Harness, Report |
| FR-13-15 | The benchmark shall start every arm's change task of block b of a named round from one fixture, the b-th qualifying build in ascending trial order, cycling when fewer qualify; record the manifest's sha256, each block's fixture and how many distinct fixtures the blocks take; refuse a change run whose manifest or block mapping differs from the root's earlier change runs; and refuse to run while the fixture manifest lists none, lists one without its baseline readings, or names a tarball whose sha256 differs, at the start and at each trial. | Harness |
| FR-13-16 | The benchmark shall derive each change workspace from its fixture's code and tests alone, without its instructions, settings, databases, caches, environments or history, with the round's spec and only the arm's context, in one commit. | Harness |
| FR-13-17 | The benchmark shall read a named round's change task whether or not its build trial was scored or left out for a reach, as a trial of its own whose build rows read not measured; count its change targets on their ISO axes whether its build is unscored, working or broken, a broken build gating only the build's own targets; and keep a pilot round's change task with its build. | Report |
| FR-13-18 | The benchmark shall reuse a named round's trials under a run record naming that round and its registration's digest, and never reuse trials into a root of another round, a named round's into a root of none, or another round's into a named round's; name the round and its digest in each reused trial's origin, and pair a trial reused within one named round, under one digest, with the trials run there. | Reuse, Report |
| FR-13-19 | The benchmark shall refuse a named round's report unless the document its registration entry names exists and landed on `main` before the round's first trial, unchanged since, a trial reused within the round counting toward its start. | Report |
| FR-13-20 | The benchmark shall verify an archive by the report's own reading of its round, through one entry point, a named round's change tasks and its reach rule included. | Archive, Report |
| FR-13-21 | The benchmark shall bring a reused trial's score, security and quality readings and judgings into the later round, each naming the trial it came from. | Reuse |
| FR-13-22 | The benchmark shall build the `lazysections` arm with the templates' emitter in its sections mode, for the chain and declined list the other emitted arms take, place its section files where its map names them, out of the workspace's index, and fail its self-test where the section files' rule blocks differ from the inline root's, or the map names a section file other than once; and count a trial's Read or shell read of a section file as a use of its map, printed in a named round's report. | Arm generator, Harness, Report |
| FR-13-23 | The benchmark shall build the `lazyrefold` arm as `lazyref` at the parent of the templates commit that cuts the check loop to one check command, and fail its self-test where the two committed arms' workspace files, at the refs their records name, differ by other than that commit's lines, all within the section it changes. | Arm generator |
| FR-13-24 | The benchmark shall refuse an on-demand arm (`lazyref`, `lazyskills`, `lazysections`, `lazyrefold`) whose files tell the agent to read everything at the start. | Arm generator |

### 14 One run at a time

| ID | Requirement | Delivered by |
| -- | ----------- | ------------ |
| FR-14-01 | The benchmark shall refuse a second scoring, judging, security or quality run that finds a live claim on its root. | Scorer, Judge, Security reader, Quality reader |
| FR-14-02 | The benchmark shall take over a claim naming a process that has ended, and say so. | Harness |

### 15 Quality probes

| ID | Requirement | Delivered by |
| -- | ----------- | ------------ |
| FR-15-01 | The benchmark shall fail each of the fuzz, concurrent-write, 500-line, N+1 and co-existence probes on an app planted with the fault it guards against, and no other probe there, and pass every probe on an app built to pass them; the 500-line probe passes only where the invoice previews 2xx, saves and renders 2xx, its JSON export answers 2xx and lists all 500 lines in order, each a well-formed record, with a finite, positive total, and its first 100 lines, saved alone, export a total a fifth of it within a cent; pages are read for answering, never for the amounts they show; the co-existence probe reads a database opened by a `file:` URI as the file it names, fails where either instance's product list does not answer 2xx, and fails a build that, at any time in the run, opens to write a file outside the workspace and the reader's own database root, a database opened read-only by a `mode=ro` URI being no write, each such write filed as it happens so a run killed later keeps it; each malformed request is sent to a fresh instance of its own, signed in afresh, and one whose form page does not answer 200 fails as unreached; and the concurrent writes run last, on a fresh instance of their own, a writer the app hangs failing them and stopping the run there, every reading before it kept. | Quality reader |
| FR-15-02 | The benchmark shall read every quality probe signed in as the seeded administrator, through the sign-in form's hidden fields however they are quoted, each post carrying the hidden fields of the form whose action, or one of whose submit controls' `formaction`, it is sent to, or else the page's first of each name, every redirect resolved against its request as a browser resolves it, the sign-in holding only where the dashboard then answers 200, and never measure a request the sign-in turns away with its redirect, a 401, or a 403 to a request that carried its token. | Quality reader |
| FR-15-03 | The benchmark shall count as lost, reading failed, a quality probe the trial keeps from running, by not installing, not booting, not signing in or not finishing in time, and as missing one it could not run itself. | Quality reader |
| FR-15-04 | The benchmark shall record the latency as two repeats of the 95th percentile over 30 requests to the main routes, with no pass threshold until one is calibrated. | Quality reader |
| FR-15-05 | The benchmark shall read portability on Python 3.14, the trial installed, booted and serving a signed-in page there, and leave it missing where no Python 3.14 is found. | Quality reader |
| FR-15-06 | The benchmark shall read the quality probes in a fresh environment per trial on the spec's Python, and remove every environment once it is read; a trial whose source tree is not present has every probe missing. | Quality reader |

## Quality requirements

- **Numbering:** characteristics follow ISO/IEC 25010:2023 order, 01
  functional suitability to 09 safety. A characteristic with no goal here
  is left out.
- **Sub-characteristic:** the ISO 25010 term the goal refines.
- **Goal:** what must hold, in plain words.
- **Target:** the measurable pass condition.
- **Motivation:** why it matters.
- **Quality goals:** chapter 1 ranks the five goals, Q1 to Q5, that these
  requirements make measurable.

### 01 Functional suitability

| ID | Sub-characteristic | Goal | Target | Motivation |
| -- | ------------------ | ---- | ------ | ---------- |
| QG-01-01 | Functional correctness | Arms differ in their context file and in nothing else (Q1). | Every trial of a round built from the registered spec and prompt, under one model, one budget and one timeout, scored under one tool lock on the spec's Python, with each block starting one arm later. | A difference between arms from anything but the file would be read as the file's effect. |
| QG-01-02 | Functional correctness | The hidden suite marks a correct build correct and a wrong one wrong. | The reference implementation passes every build check; a change made from the change prompt alone passes every change check; the mutation control's 12 planted violations are each caught. | A suite that fails a correct build, or passes a broken one, makes task success measure the suite. |
| QG-01-03 | Functional correctness | Every primary judge row can move (Q4). | Under the rounds' judge, three judgings per tree, every primary falls on the control tree built to damage it and rises on the one built to improve it, read again whenever the judge model, its effort or the rubric changes. | A row that cannot move can never separate two arms. |
| QG-01-04 | Functional correctness | The judge reads the code it scores (Q4). | 100 % of the evidence lines quoted on every control judging found in their bundle. | A judge that never opened the code still returns plausible numbers. |
| QG-01-05 | Functional correctness | A value that was not measured never reads as a result (Q4). | Every planted empty, failed or skipped case in the self-tests reads missing, lost or not passed. | A zero from a tool that scanned nothing reads as a clean arm. |

### 02 Performance efficiency

| ID | Sub-characteristic | Goal | Target | Motivation |
| -- | ------------------ | ---- | ------ | ---------- |
| QG-02-01 | Resource utilisation | A trial stays within its bounds. | Every trial ends within its budget of $100 API-equivalent, plus at most one turn, and within two hours. | A trial without a bound can spend a plan's limit on one arm. |
| QG-02-02 | Capacity | A round's judging fits the judge's plan. | Three judgings of every trial of a K = 15 round within the judge plan's weekly limit. | A judging stopped at a usage limit leaves a round half-judged. |

### 05 Reliability

| ID | Sub-characteristic | Goal | Target | Motivation |
| -- | ------------------ | ---- | ------ | ---------- |
| QG-05-01 | Fault tolerance | A provider failure never changes which trials a round counts. | Every lost trial re-run once in its place; zero lost trials scored. | Re-running one arm's failures alone would quietly improve that arm. |
| QG-05-02 | Recoverability | A run that stops resumes where it stopped. | A stopped run resumed with `--from` runs the remaining trials in the registered order, with none left recorded as running. | A round restarted from scratch would run some trials twice and mix two days' model behaviour into one block. |
| QG-05-03 | Recoverability | A round can be restored and its report recomputed (Q5). | A round restored from the archive reproduces every figure of its report. | A deleted run root with nothing kept leaves no reading that can be re-run, re-judged or checked. |

### 06 Security

| ID | Sub-characteristic | Goal | Target | Motivation |
| -- | ------------------ | ---- | ------ | ---------- |
| QG-06-01 | Confidentiality | A trial reaches nothing it is defined not to have (Q3). | Zero counted trials whose transcript reaches the hidden suite, the templates source, another trial, the scoring area or the owner's home. | A trial that read the hidden suite measures the suite, not its context file. |
| QG-06-02 | Integrity | No rule for reading a result is chosen after the results (Q2). | From round 5, every round refused whose registration landed after its first trial or differs from `main`; every check declared after a run printed without a verdict. | Otherwise the bar moves with the results. |
| QG-06-03 | Accountability | Every reading names what produced it (Q5). | Every score, judging and reading records the revisions, model, effort and seed it was made under, and the archive holds a hash per file. | A figure that cannot be traced to its inputs cannot be checked or re-run. |

### 07 Maintainability

| ID | Sub-characteristic | Goal | Target | Motivation |
| -- | ------------------ | ---- | ------ | ---------- |
| QG-07-01 | Testability | Every rule has a check. | `trace.py` passes in CI: every live FR has a self-test check, a reason it is untestable, or an open issue for its check. | Rules with no check behind them are where review findings come from. |

### 08 Flexibility

| ID | Sub-characteristic | Goal | Target | Motivation |
| -- | ------------------ | ---- | ------ | ---------- |
| QG-08-01 | Adaptability | A later template revision is measured with the same harness. | A candidate and a baseline arm run head to head in one round, read as one contrast, with no change to the harness. | A harness rebuilt for every revision would compare revisions under different rulers. |
| QG-08-02 | Adaptability | The scripts run on the owner's Windows machine and on Linux. | Every self-test passes on the `windows-latest` and `ubuntu-latest` CI runners. | The owner runs rounds on Windows, and CI proves the POSIX paths. |

## Test artefacts

- **Use:** the quality goals are measured against these sets, suites and
  setups.
- **Freeze:** an artefact a round reads is fixed with that round's
  registration.

| Artefact | Contents | Used by |
| -------- | -------- | ------- |
| Hidden suite | At revision `a8e7935`, 544 build checks across 19 modules, 5 of them browser flows that skip where no browser is installed, and 74 change checks, in the private `braboj/tariff-hidden-suite`. | QG-01-02 |
| Reference implementation | A build written from the spec alone, and the change task made on it from the change prompt alone. Private, beside the hidden suite. | QG-01-02 |
| Mutation control | Fifteen spec violations, each planted alone in the reference implementation. | QG-01-02 |
| Control fixture | The judge's control trees, built by `control/control.py` from two pinned applications; see [validation](validation.md). | QG-01-03, QG-01-04 |
| Self-tests | Each script's `--self-test`, which plants the case each rule guards against. | QG-01-05, QG-05-01, QG-05-02, QG-06-01, QG-06-02, QG-07-01 |
| CI runners | `ubuntu-latest` and `windows-latest`, Python 3.12, stub agent CLIs that refuse to run. | QG-07-01, QG-08-02 |
| Private archive | `braboj/tariff-runs`, each round's run root and readings. | QG-05-03, QG-06-03 |

## Quality targets of the app under test

- **Use:** the report's radar scores every build on ISO/IEC 25010:2023, each
  axis the share of its targets met. These are the targets.
- **Numbering:** characteristics in the standard's order, as the quality
  requirements above; a sub-characteristic with no target is not listed, and
  reads not measured in the report.
- **Target:** a pass or a fail per build. "The judge reads it as 3 or better"
  is the mean of the judge's three readings on its 1 to 5 scale.
- **Fixed:** before round 6's first trial, for this app; a change is a new
  registration.
- **Read from:** the scorer's row, the probe, the hidden-suite module, or the
  judge's row the target reads; a build the reading did not reach is not
  measured, never a fail. A probe the build itself kept from running is lost,
  and fails.
- **Pilot drafts:** a pilot round read by the ISO radar keeps the targets it
  had before round 6: the hidden suite at 98 % or more for correctness, and
  no quality probe. Round 6's are read there only when asked for.
- **Later:** interoperability and the migration targets come with the
  changed tree's scoring. The export formats take no target of their own:
  the hidden suite's export modules grade them.

### 01 Functional suitability

| ID | Sub-characteristic | Target | Read from |
| -- | ------------------ | ------ | --------- |
| QT-01-01 | Functional completeness | Every name the specification requires is exported. | Specified names missing |
| QT-01-02 | Functional correctness | Each of the hidden suite's 19 build modules passes whole, one target per module: every check ran and passed, none failed, errored or skipped. A module missing from a build's report is not measured where the suite's revision did not hold it, and not met where it did; a suite that ran out of time fails every module. | Hidden suite, per module |
| QT-01-03 | Functional appropriateness | Nothing nobody asked for is delivered. | Artifacts nobody asked for |

### 02 Performance efficiency

| ID | Sub-characteristic | Target | Read from |
| -- | ------------------ | ------ | --------- |
| QT-02-01 | Resource utilisation | The invoice builder answers in 100 KB or less. | Invoice builder response size |
| QT-02-02 | Resource utilisation | The invoice builder makes at most 3 subrequests. | Invoice builder subrequests |
| QT-02-03 | Time behaviour | The 95th-percentile latency, the worse of two repeats, is within the cutoff registered before round 6; not measured until one is. | Quality probe `latency_p95_ms` |
| QT-02-04 | Resource utilisation | A page's SQL statements do not grow with an invoice's lines. | Quality probe `n_plus_one` |
| QT-02-05 | Capacity | An invoice of 500 lines is kept, shown and exported whole. | Quality probe `capacity_500_lines` |

### 03 Compatibility

| ID | Sub-characteristic | Target | Read from |
| -- | ------------------ | ------ | --------- |
| QT-03-01 | Co-existence | Two instances side by side keep their data and files apart. | Quality probe `coexistence` |

### 04 Interaction capability

| ID | Sub-characteristic | Target | Read from |
| -- | ------------------ | ------ | --------- |
| QT-04-01 | Operability | The HTML is valid. | HTML validity errors |
| QT-04-02 | Inclusivity | No WCAG 2.1 AA violation. | Accessibility violations |

### 05 Reliability

| ID | Sub-characteristic | Target | Read from |
| -- | ------------------ | ------ | --------- |
| QT-05-01 | Faultlessness | The build installs and boots. | Installs and boots |
| QT-05-02 | Faultlessness | At most 10 type errors per KLOC under `mypy --strict`. | Type errors per KLOC |
| QT-05-03 | Fault tolerance | A malformed request leaks no stack trace. | Probe `error_leakage` |
| QT-05-04 | Availability | Concurrent writes all land, none refused for a lock. | Quality probe `concurrent_writes` |
| QT-05-05 | Fault tolerance | A malformed request never answers a server error. | Quality probe `fuzz_robustness` |

### 06 Security

| ID | Sub-characteristic | Target | Read from |
| -- | ------------------ | ------ | --------- |
| QT-06-01 | Confidentiality | Passwords are hashed at rest. | Probe `password_at_rest` |
| QT-06-02 | Confidentiality | Sign-in does not tell an account from a stranger. | Probe `account_enumeration` |
| QT-06-03 | Confidentiality | No hard-coded secret key. | Probe `secret_key` |
| QT-06-04 | Confidentiality | The session cookie carries its flags. | Probe `cookie_flags` |
| QT-06-05 | Integrity | Sign-in refuses a post without a token. | Probe `sign_in_csrf` |
| QT-06-06 | Integrity | A form refuses a post without a token. | CSRF refused without a token |
| QT-06-07 | Integrity | No open redirect. | Probe `open_redirect` |
| QT-06-08 | Integrity | No SQL assembled from strings. | Probe `sql_strings` |
| QT-06-09 | Integrity | A stored payload renders inert. | Stored payload renders inert |
| QT-06-10 | Resistance | Debug is off. | Probe `debug` |
| QT-06-11 | Resistance | The security headers are set. | Probe `security_headers` |
| QT-06-12 | Resistance | No vulnerable dependency. | Probe `vulnerable_dependencies` |
| QT-06-13 | Resistance | No high or medium `bandit` finding. | Security findings, high and medium |
| QT-06-14 | Resistance | The judge reads its security as 3 or better. | Judge, security |
| QT-06-15 | Data protection | Personal data stays out of the log. | Probe `log_leak` |
| QT-06-16 | Data protection | Erasure leaves no residue. | Probe `erasure_residue` |
| QT-06-17 | Data protection | An export holds its own data only. | Probe `export_scope` |
| QT-06-18 | Data protection | The judge reads its data protection as 3 or better. | Judge, data protection |

### 07 Maintainability

| ID | Sub-characteristic | Target | Read from |
| -- | ------------------ | ------ | --------- |
| QT-07-01 | Modularity | No module `import tariff` loads reaches Flask or the database. | Layering violations |
| QT-07-02 | Modularity | No two modules import each other. | Mutually importing module pairs |
| QT-07-03 | Modularity | The judge reads its design as 3 or better. | Judge, design |
| QT-07-04 | Modularity | The judge reads its single responsibility as 3 or better. | Judge, SRP |
| QT-07-05 | Analysability | At most 100 lint findings per KLOC. | Lint findings per KLOC |
| QT-07-06 | Analysability | The formatter would change no file. | Files the formatter would change |
| QT-07-07 | Analysability | No function over cognitive complexity 15. | Functions over complexity 15 |
| QT-07-08 | Analysability | Half the definitions carry a docstring. | Docstring coverage |
| QT-07-09 | Analysability | The judge reads its readability as 3 or better. | Judge, readability |
| QT-07-10 | Modifiability | No conditional ladder over rule kinds. | Conditional ladders over rule kinds |
| QT-07-11 | Modifiability | No boolean parameter. | Boolean parameters |
| QT-07-12 | Modifiability | At most 5 unused names per KLOC. | Unused names per KLOC |
| QT-07-13 | Modifiability | The judge reads its maintainability as 3 or better. | Judge, maintainability |
| QT-07-14 | Modifiability | The judge reads its openness to extension as 3 or better. | Judge, OCP |
| QT-07-15 | Modifiability | The change task passes 90 % of its checks. | Change task, acceptance pass rate |
| QT-07-16 | Modifiability | The change task keeps 98 % of the build suite. | Change task, build suite pass rate after it |
| QT-07-17 | Testability | Its own tests pass. | The trial's own tests |
| QT-07-18 | Testability | Its own tests cover 80 % of the lines. | Line coverage of the trial's own tests |
| QT-07-19 | Testability | The judge reads its tests as 3 or better. | Judge, test quality |

### 08 Flexibility

| ID | Sub-characteristic | Target | Read from |
| -- | ------------------ | ------ | --------- |
| QT-08-01 | Installability | `pip install .` succeeds in a clean environment. | Installs in a clean environment |
| QT-08-02 | Adaptability | The build installs and serves a signed-in page on a second Python. | Quality probe `python_portability` |
