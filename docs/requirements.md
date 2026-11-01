# Requirements

What the benchmark must do, one rule per row, each with the self-test checks
that prove it.

- **IDs:** `FR-<topic>-<n>`. Cite a rule by its ID. A new rule takes the next
  free number in its topic; a removed ID is never reused.
- **Why:** each topic names the
  [chapter 8](architecture/08-crosscutting-concepts.md) section that explains
  its rules. The quality scenarios in
  [chapter 10](architecture/10-quality-requirements.md) name the rules they
  rest on.
- **Checked by:** the module whose `--self-test` proves the rule, and the
  label it prints for that check. `trace.py` fails when a label no self-test
  prints is named here.
- **Untestable:** a rule no script can see, with the reason.
- **Gap:** a rule a script follows that no self-test plants yet, with the
  issue that tracks it.

## 01 Registration (ch. 8.1.1)

| ID | Requirement | Checked by |
|---|---|---|
| FR-01-01 | From round 5, the report shall refuse a round whose registration landed on `main` after its first trial started, read on `main`'s first-parent line so a merge counts at the merge. | `report.py` "one landed after the first trial is refused"<br>`report.py` "one merged after the first trial is read at the merge"<br>`report.py` "a registration landed before the first trial passes, across zones" |
| FR-01-02 | The report shall refuse a registration that differs from `main`'s copy or has changes not committed. | `report.py` "one changed and not committed is refused"<br>`report.py` "an amendment on a branch of its own is refused" |
| FR-01-03 | The report shall refuse a trial built from a spec or prompt other than the ones its round registers, by content. | `report.py` "a trial on another spec is refused"<br>`report.py` "a trial on another prompt is refused"<br>`report.py` "every trial on the registered spec passes"<br>`report.py` "every trial on the one prompt passes" |
| FR-01-04 | The report shall refuse a trial with something to score that records no spec or no prompt. | `report.py` "a scorable trial recording no spec is refused"<br>`report.py` "a scorable trial recording no prompt is refused" |
| FR-01-05 | The harness shall check the spec before every trial, so an edit made mid-run refuses the trials after it unbuilt. | `harness.py` "a spec edited mid-run refuses the next trial unbuilt"<br>`harness.py` "a spec changed as it is copied refuses the trial and frees its slot"<br>`harness.py` "a round-5 run on other content is refused"<br>`harness.py` "round 5's registered digest is SPEC.md's content" |
| FR-01-06 | A trial shall record its start with its UTC offset, and the report shall refuse a start with none. | `report.py` "a trial start with no UTC offset is refused" |
| FR-01-07 | A registration shall land through a pull request's squash or rebase merge. | Untestable: how a commit reached `main` is the owner's practice, and no script sees it. |

## 02 Reading a result (ch. 8.1.1, 8.1.2)

| ID | Requirement | Checked by |
|---|---|---|
| FR-02-01 | The arms of a block shall run interleaved, each block starting one arm later, so drift lands on every arm. | `harness.py` "each block starts one arm later"<br>`harness.py` "over five blocks every arm runs in every place" |
| FR-02-02 | A contrast shall read better when its 95 % bootstrap interval lies wholly on the improving side of zero, worse when wholly on the other, and no improvement shown when it contains zero, by the metric's direction. | `report.py` "every pairing improves by the same amount -> better"<br>`report.py` "every pairing improves, unstably -> better"<br>`report.py` "three identical differences -> better"<br>`report.py` "the differences change sign -> no improvement shown"<br>`report.py` "a downward metric that fell -> better"<br>`report.py` "a downward metric that rose -> worse" |
| FR-02-03 | A metric shall read held only when the whole interval lies inside its registered margin, relative margins taken on the baseline arm's mean. | `report.py` "10 more lines on 100 is preserved"<br>`report.py` "20 more lines on 100 is not"<br>`report.py` "1.5 more per KLOC on 20 is preserved"<br>`report.py` "3 more per KLOC on 20 is not"<br>`report.py` "no baseline makes no relative claim" |
| FR-02-04 | Every primary and every per-KLOC row shall carry its registered margin. | `report.py` "every per-KLOC row carries the static margin"<br>`report.py` "every primary the judge asks for is led with, worded and given its margins" |
| FR-02-05 | Round 5 shall hold adherence within 8 pp, one checklist item of 13. | `report.py` "round 5 holds adherence within one item, 8 pp" |
| FR-02-06 | From round 5, app code's lines and files shall read held on a rise wholly inside the band, and worse only on one wholly past it. | `report.py` "a rise inside the band is held"<br>`report.py` "a rise wholly past the band is worse"<br>`report.py` "one that straddles the band is undecided"<br>`report.py` "a band that holds zero is held"<br>`report.py` "round 5 reads a 10 % rise in app code as held" |
| FR-02-07 | An adherence gain shall count only where the hidden-test pass rate held. | Gap: #109 |
| FR-02-08 | A trim shall be called free only where every metric held. | Gap: #109 |
| FR-02-09 | Below K = 6, the report shall call every interval descriptive. | `report.py` "from six blocks no interval is called descriptive"<br>`report.py` "a round too small to decide says so in the report and the appendix" |

## 03 Trial count and escalation (ch. 8.1.3)

| ID | Requirement | Checked by |
|---|---|---|
| FR-03-01 | The report shall owe an escalation to K = 5 where a primary's interval contains zero while its mean difference exceeds the smallest change that matters, in any contrast and either direction. | `report.py` "a crossing interval with an effect of 0.67 owes it"<br>`report.py` "an effect of 0.67 the other way owes it"<br>`report.py` "the same row on C-A owes it"<br>`report.py` "an effect of exactly 0.5 does not"<br>`report.py` "an interval clear of zero does not"<br>`report.py` "an interval not computed does not"<br>`report.py` "a row outside the primary dimensions does not" |
| FR-03-02 | An escalation shall run two more blocks, once, and K shall never pass 5 under it. | `harness.py` "a K past the escalation's ceiling refuses"<br>`harness.py` "the escalation runs its blocks from none-4"<br>`report.py` "an owed escalation's command names a trial the harness takes" |
| FR-03-03 | An escalated report shall print the K = 3 and K = 5 results side by side, and a row still open at K = 5 as inconclusive. | `report.py` "an escalated report prints both vectors"<br>`report.py` "the report carries the escalation section"<br>`report.py` "a K = 5 run is judged on its first three blocks"<br>`report.py` "a K = 3 run is assessed on its own vector"<br>`report.py` "an open row leaves both inconclusive" |
| FR-03-04 | A round registered at a larger K shall take no block past it. | `harness.py` "a round-5 run takes K = 15 and refuses more"<br>`harness.py` "a round-5d run of hand and short takes K = 15 too" |
| FR-03-05 | A run short of its registered K shall be part-run, and none of its verdicts the round's. | `report.py` "one trial of the last block leaves the round part-run"<br>`report.py` "a round 5 run short of its last block says it is provisional"<br>`report.py` "a round-5 run owes no escalation and names the blocks still owed" |

## 04 Failed and lost trials (ch. 8.1.4)

| ID | Requirement | Checked by |
|---|---|---|
| FR-04-01 | A trial that completed, or was ended by the budget cap or the timeout, shall be scored as it stands. | `harness.py` "a clean finish is completed"<br>`harness.py` "the budget cap is budget"<br>`harness.py` "one that never answers is ended at the timeout"<br>`score.py` "only completed, budget and timeout endings are offered, under the arms' words" |
| FR-04-02 | A build that did not install shall go unjudged, with its judge rows missing. | `judge.py` "only a build that did not install goes unjudged"<br>`report.py` "a build that did not install has its judge rows missing" |
| FR-04-03 | A failed trial shall never be re-run. | Untestable: the harness has no path that re-runs a trial ended by the agent; FR-04-04 proves only a lost one re-runs. |
| FR-04-04 | A trial the CLI ends with any error but the budget cap shall be lost: a usage limit, a rate limit, a crash, or no result. | `harness.py` "a usage limit, by its wording is blocked"<br>`harness.py` "a rate limit, by its status is blocked"<br>`harness.py` "an error behind a zero status is blocked"<br>`harness.py` "an error subtype nobody listed is blocked"<br>`harness.py` "no JSON at all is blocked" |
| FR-04-05 | A lost trial shall be re-run once, in its own place in the order, and its re-run read in its stead. | `harness.py` "a blocked trial re-runs in its place"<br>`harness.py` "the re-run names the trial it substitutes"<br>`score.py` "a blocked trial yields to its re-run" |
| FR-04-06 | A lost trial's workspace shall be kept under the run's `void/` directory and never scored. | `harness.py` "a voided workspace is kept under void/"<br>`harness.py` "a voided trial takes its whole pen and its tarball" |
| FR-04-07 | A second loss of the same trial shall stop the run. | `harness.py` "a second block stops the run" |
| FR-04-08 | A run that stopped part way shall resume with `--from` at the trial named, keeping the order. | `harness.py` "--from short-2 starts there and keeps the order"<br>`harness.py` "--from an unknown trial refuses"<br>`harness.py` "no trial stays recorded as running" |

## 05 Isolation (ch. 8.2)

| ID | Requirement | Checked by |
|---|---|---|
| FR-05-01 | A trial shall run under a scratch home and minimal settings, so the owner's global `CLAUDE.md`, hooks, memory and MCP never reach it. | `harness.py` "the scratch home is the home"<br>`harness.py` "the settings file carries the rules and the isolation"<br>`harness.py` "a trial reads the workspace's project settings and no other source" |
| FR-05-02 | A trial shall run in a cleaned environment, without the launching session's variables, interpreter or keys. | `harness.py` "ANTHROPIC_API_KEY is removed"<br>`harness.py` "CLAUDECODE is removed"<br>`harness.py` "VIRTUAL_ENV is removed"<br>`harness.py` "the interpreter leaves PATH" |
| FR-05-03 | The file tools shall be denied every path outside the trial's own workspace. | `harness.py` "other trials, their change tasks, home and void are denied"<br>`harness.py` "this repository and the scoring area are denied"<br>`harness.py` "tarballs and run records are denied"<br>`harness.py` "the templates source is denied whenever one is set"<br>`harness.py` "the trial's own workspace is not denied" |
| FR-05-04 | The web tools shall be disallowed. | Gap: #109 |
| FR-05-05 | Git credential helpers shall answer nothing inside a trial. | `harness.py` "a planted Git helper answers outside a trial"<br>`harness.py` "it does not answer inside one" |
| FR-05-06 | Commands that stop a process by name shall be denied. | `harness.py` "every kill by name meets a deny rule" |
| FR-05-07 | The transcript scan shall flag every tool call naming a forbidden path or repository; a hit voids the trial and re-runs it once. | `harness.py` "every call reaching past the trial is flagged"<br>`harness.py` "the root, another pen and a climb out of the pen are flagged"<br>`harness.py` "a fetch of the templates is flagged, and only that"<br>`harness.py` "a kill by name that ran, or never answered, is a hit"<br>`harness.py` "a scorable trial with a reach becomes reached"<br>`harness.py` "the trial's own paths are not flagged, a pip extra included" |
| FR-05-08 | The report shall scan every transcript again under the current rule. | `report.py` "its record's clean scan is read again and flagged"<br>`report.py` "a trial whose scan hit is named"<br>`report.py` "a reached build trial is left out whole" |
| FR-05-09 | Every process started from a trial's directories shall be stopped before the trial is frozen, and the record list them. | `harness.py` "the one running from the trial is stopped"<br>`harness.py` "two planted processes run and are listed"<br>`harness.py` "the record lists what was stopped" |

## 06 Missing is not zero (ch. 8.3)

| ID | Requirement | Checked by |
|---|---|---|
| FR-06-01 | A tool that scanned nothing, failed or timed out shall record its metric as missing, with the reason. | `score.py` "empty tree: ruff is missing, not zero"<br>`score.py` "empty tree: mypy is missing, not zero"<br>`score.py` "empty tree: coverage is missing, not zero"<br>`score.py` "tools absent: ruff is missing, not zero"<br>`score.py` "tools absent: bandit is missing, not zero"<br>`score.py` "an empty tree reports nothing seen"<br>`score.py` "a failed listing is missing, never an empty list" |
| FR-06-02 | A grader's skipped check shall not count as passed. | `score.py` "a skipped check is recorded beside the rate"<br>`score.py` "a partial suite is flagged"<br>`score.py` "a suite that skipped nothing is not partial" |
| FR-06-03 | A probe the trial keeps from running shall be lost, and count against the rate. | `security.py` "an application that will not boot loses every runtime probe"<br>`security.py` "an administrator that cannot sign in loses what needs one"<br>`security.py` "the lost probes count against the rate" |
| FR-06-04 | A probe the harness could not run shall leave the rate missing. | `security.py` "no report from the probe is missing, not lost"<br>`security.py` "an audit of nothing is missing, not zero"<br>`security.py` "a report that is not JSON is missing"<br>`security.py` "no roots is missing, not zero" |
| FR-06-05 | The report shall show an unmeasured value as not measured. | `report.py` "an unmeasured column reads not measured"<br>`report.py` "an unmeasured run answers Not measured in every cell" |

## 07 One ruler (ch. 8.4, 8.6.2)

| ID | Requirement | Checked by |
|---|---|---|
| FR-07-01 | The first trial scored shall freeze the tools to a lock, and every later trial install from it. | `score.py` "the battery installs from a lock it resolved" |
| FR-07-02 | The lock shall hold only the tools, never a trial's own packages. | `score.py` "only the tools reach the lock"<br>`score.py` "the lock carries none of the trial's dependencies" |
| FR-07-03 | The tools shall run under `toolconfig/` only, never the configuration the agent wrote. | Gap: #109 |
| FR-07-04 | Every build shall be scored on the spec's Python, and the report refuse a round scored on two. | `score.py` "a scoring environment runs the spec's Python"<br>`score.py` "no Python at the spec's version refuses to score"<br>`score.py` "a score on another Python refuses the root"<br>`report.py` "scores on two Pythons are refused" |
| FR-07-05 | The tools shall be pointed at the installed package and every top-level package, never an assumed `src/`. | `score.py` "the planted package is discovered"<br>`score.py` "an empty tree yields no roots" |
| FR-07-06 | The coverage run shall first install every extra and dependency group the trial declares, within the lock. | `score.py` "every extra and every group requirement is installed" |
| FR-07-07 | A declared test dependency that conflicts with the lock shall record coverage as missing, with the conflict. | Gap: #109 |

## 08 Blindness (ch. 8.5)

| ID | Requirement | Checked by |
|---|---|---|
| FR-08-01 | The judge's bundle shall hold the trial's code without the context file, the vendored templates, the skills, or scoring's output. | `judge.py` "the trial's code reaches the bundle"<br>`judge.py` "scoring's output and the environment's stay out of the bundle"<br>`judge.py` "the skills arm's skills stay out of the bundle" |
| FR-08-02 | The bundles shall be judged in an order shuffled at a recorded seed, with the unblinding map out of the judge's reach. | Gap: #109 |
| FR-08-03 | A bundle that still names its arm shall be refused. | `judge.py` "a path naming the trial is a leak"<br>`judge.py` "an escaped path naming the trial is a leak"<br>`judge.py` "a leak in a directory the copy skips is found"<br>`judge.py` "a bundle holding neither has no leak"<br>`generate_arm.py` "the leak scan reports a planted token and passes clean text" |

## 09 Scoring (ch. 8.6.1 to 8.6.4)

| ID | Requirement | Checked by |
|---|---|---|
| FR-09-01 | The hidden suite shall live outside every workspace, in a scoring area the trial is denied. | `harness.py` "the scoring area lies outside the run root"<br>`harness.py` "this repository and the scoring area are denied" |
| FR-09-02 | A build shall install in a clean virtualenv and boot under scoring as the hidden suite boots it. | `score.py` "an application that seeds on start, and has no default secret, boots under scoring"<br>`score.py` "a build capped below Python 3.13 installs" |
| FR-09-03 | HTML validity shall set aside the errors on HTMX's `hx-*` attributes, and count the rest. | `score.py` "an hx-* error is set aside and another counts" |
| FR-09-04 | Scope shall count app code apart from tests, docs and configuration, and name artifacts nobody asked for. | `score.py` "app code is the app's Python and templates, not its tests"<br>`score.py` "test code is a tests directory or a pytest name, anywhere"<br>`score.py` "docs and configuration count toward no size"<br>`score.py` "committed bytecode and a database are artifacts nobody asked for" |
| FR-09-05 | The adherence checklist's 13 items shall be read on every arm, the bare arm included. | Gap: #109 |
| FR-09-06 | The design-structure probes shall read layering, the import graph, extension points, kind ladders, boolean parameters, the public surface, IO isolation and hygiene. | Gap: #109 |
| FR-09-07 | Change-task churn shall count every edited and new file, and nothing in an environment. | `score.py` "churn counts an edit and a new file, not an environment"<br>`score.py` "the churn plant landed" |
| FR-09-08 | The change prompt shall state everything the grader drives. | `harness.py` "the change prompt names the API and fields the grader drives"<br>`harness.py` "the change prompt is read whole from its file" |
| FR-09-09 | The change-task acceptance modules shall be written before any change-task run. | Untestable: an order of work; the round's registration fixes it. |

## 10 The judge (ch. 8.6.5 to 8.6.7)

| ID | Requirement | Checked by |
|---|---|---|
| FR-10-01 | Each tree shall be judged three times, and its scores averaged. | `judge.py` "each tree is read three times by default"<br>`report.py` "a trial's repeats are meaned, and one judging means itself" |
| FR-10-02 | From round 5, the judge shall be `gpt-6-astra` through `codex exec` at effort `high`, with model and effort recorded. | `judge.py` "the default judge is gpt-6-astra through codex"<br>`judge.py` "the default effort is high"<br>`judge.py` "the codex command carries the model and the effort"<br>`judge.py` "the recorded effort is the one passed" |
| FR-10-03 | The judge may read the bundle and do nothing else. | `judge.py` "it may read and nothing else"<br>`judge.py` "the claude backend is not in plan mode" |
| FR-10-04 | A cross-check's agreement shall be counted per row over the trials both judges read. | `report.py` "agreement is counted per row over the trials both read" |
| FR-10-05 | A verdict shall lose its direction when the other judge's mean paired difference has the opposite sign, and keep it otherwise. | `report.py` "a direction the other judge reverses loses its verdict"<br>`report.py` "a direction both judges read keeps its verdict"<br>`report.py` "a contrast the other judge did not read keeps its verdict"<br>`report.py` "the rounds' own judge is caught posing as the other" |
| FR-10-06 | The report shall print the share of the judge's quotes found in its bundle. | `report.py` "the judge is checked by its evidence, not a person" |
| FR-10-07 | The control builder shall refuse when a mutation did not land, and print each change it read back. | `control/control.py` "the domain imports flask"<br>`control/control.py` "ValidationError derives from TariffError"<br>`control/control.py` "the secret key is a literal"<br>`control/control.py` "customer data is written to the log" |
| FR-10-08 | The control builder shall refuse a base archive whose sha256 is not the one recorded. | Gap: #109 |
| FR-10-09 | A primary shall count only if it falls on the control tree that damages it and rises on the one that improves it. | Untestable: a judged control root is read by hand, and ch. 10.7 records each reading. |

## 11 Security and data protection (ch. 8.6.8)

| ID | Requirement | Checked by |
|---|---|---|
| FR-11-01 | The 11 security and 3 data-protection probes shall fail an app built to fail them and pass one built to pass them. | `security.py` "exposed fails every probe"<br>`security.py` "hardened passes every probe"<br>`security.py` "exposed rates are zero"<br>`security.py` "hardened rates are whole" |
| FR-11-02 | A probe shall sign in the way the hidden suite does. | `security.py` "exposed signs in"<br>`security.py` "hardened signs in" |
| FR-11-03 | The source probes shall count every planted secret, debug and assembled-SQL form, and no safe one. | `security.py` "every planted secret form is counted"<br>`security.py` "every planted debug form is counted"<br>`security.py` "every planted assembled statement is counted"<br>`security.py` "parameters, plain f-strings and constant names are not assembled SQL"<br>`security.py` "hardened source finds no secret" |
| FR-11-04 | The dependency probe shall count every vulnerability of every installed package. | `security.py` "every vulnerability of every package is counted" |
| FR-11-05 | The CSRF probe shall fail a sign-in that accepts a forgery, and pass one that refuses it. | `security.py` "public pages with a forgeable sign-in fail only its CSRF probe"<br>`security.py` "public pages with a token-checked sign-in pass every probe"<br>`security.py` "a refused forgery passes though a failed sign-in answers as a real one" |
| FR-11-06 | The report shall read each probe rate as `security.py` files it. | `report.py` "every probe rate reads the rate security.py files" |

## 12 The report (ch. 8.7)

| ID | Requirement | Checked by |
|---|---|---|
| FR-12-01 | A paired contrast crossing rounds shall get no verdict and count nowhere. | `report.py` "a contrast crossing rounds carries no verdict and counts nowhere"<br>`report.py` "a comparison across rounds reads as not given, not too few runs" |
| FR-12-02 | A contrast a round registers against an earlier round's arm shall be read unpaired, with a verdict. | `report.py` "a contrast across rounds is unpaired, with a verdict"<br>`report.py` "a round-5d run reads H4 against a reused `none`, unpaired"<br>`report.py` "an unpaired contrast leaves out two trials, not blocks" |
| FR-12-03 | The report shall print every declared contrast its arms ran, and no other. | `report.py` "it prints every declared contrast its arms ran"<br>`report.py` "a three-arm run prints only its own contrasts"<br>`report.py` "an earlier round computes no round-5d contrast" |
| FR-12-04 | A neutral row shall print without a verdict. | `report.py` "an earlier round rescored prints app code without a verdict"<br>`report.py` "round 5 reports the files it supersedes without a verdict" |
| FR-12-05 | A round shall write a report, an appendix and a record, each linking the next. | `report.py` "the report links its appendix, and the appendix the record"<br>`report.py` "the appendix holds what produced the results, the radar's axes and the verdict vector, and nothing else" |
| FR-12-06 | The radar shall draw one panel per file arm against `none`, in both themes, each axis better minus worse over its rows with a verdict. | `report.py` "the radar draws a panel per arm, with the bare ring, in both themes"<br>`report.py` "an axis is better minus worse over its rows with a verdict, None without one"<br>`report.py` "the summary is the radar, one image per theme" |
| FR-12-07 | Each approach's verdict shall be Yes where a deciding measure is better and none worse, Worse where any is worse, and No where none moved. | `report.py` "the report names each approach and its verdict in plain words"<br>`report.py` "a better primary and no worse answers Yes"<br>`report.py` "a worse primary answers Worse"<br>`report.py` "nothing separated answers No" |
| FR-12-08 | A check declared after a run shall print in its own section, with no verdict, outside the verdict vector. | `report.py` "the report prints the section"<br>`report.py` "its row carries no verdict"<br>`report.py` "its row is not in the verdict vector"<br>`report.py` "no after-the-results check is a verdict metric" |
| FR-12-09 | A withdrawn metric shall lose every value on the runs its grader's revision graded, and keep them on the others. | `report.py` "withdrawal blanks every value of the row"<br>`report.py` "its verdict vector row reads withdrawn"<br>`report.py` "the withdrawal section names it and why"<br>`report.py` "a run graded by another revision withdraws nothing"<br>`report.py` "a metric not withdrawn keeps its verdict" |
| FR-12-10 | A corrected grader shall never re-grade the trials its earlier revision graded. | Untestable: a working rule; a re-grade and a first grade leave the same record. |

## 13 Records (ch. 8.8)

| ID | Requirement | Checked by |
|---|---|---|
| FR-13-01 | The harness shall write the run record as every trial starts and ends, with the CLI's version. | `harness.py` "the record is written as every trial starts and ends"<br>`harness.py` "every trial records the CLI's version, read as it starts" |
| FR-13-02 | The arm generator shall write `generation.json` beside every file it generates. | Gap: #109 |
| FR-13-03 | The archive shall carry every reading, judging, map and lock, with a hash per file, and fail its verify on a changed one. | `archive.py` "readings, judgings, map and lock come; bundles do not"<br>`archive.py` "the original tarball's hash is recorded"<br>`archive.py` "the revisions are recorded"<br>`archive.py` "a reading changed in the archive fails the verify" |
| FR-13-04 | The report shall refuse to write under `docs/audits/` once a reading changed since the archive was verified. | `archive.py` "a reading changed after the stamp is a problem"<br>`archive.py` "the report refuses docs/audits/ without a current stamp"<br>`report.py` "a report into a templates source's docs/audits needs the stamp" |
| FR-13-05 | A restored archive shall read as the original root does, its records pointing at the restored files. | `archive.py` "the restored root reads as the original does"<br>`archive.py` "a restored record points at the restored tarball and void"<br>`archive.py` "a restored transcript keeps its time" |

## 14 One run at a time (ch. 8.9)

| ID | Requirement | Checked by |
|---|---|---|
| FR-14-01 | A second `score.py`, `judge.py` or `security.py` run that finds a live claim on the root shall be refused. | `score.py` "a live score.py run refuses a second"<br>`judge.py` "a live judge.py run refuses a second"<br>`security.py` "a live security.py run refuses a second" |
| FR-14-02 | A claim naming a process that has ended shall be taken over, and the run say so. | `harness.py` "an ended run is taken over"<br>`harness.py` "a live pid that is not the tool is taken over" |
