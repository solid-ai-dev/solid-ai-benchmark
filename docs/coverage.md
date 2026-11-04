# Requirement coverage

- **Scope:** each live functional requirement of
  [requirements.md](requirements.md), with the self-test checks that prove
  it, or the reason it has none.
- **Checked by:** a module under `tests/efficacy/` and the label its
  `--self-test` prints for the check, one per line.
- **Gaps:** a row of kind Missing names the issue that adds its check.

`trace.py` runs every self-test, or reads their saved output, and fails
when:

| Check | Fails when |
| ----- | ---------- |
| Every requirement | A live FR has no row, or a row names an FR that is removed or absent |
| Known kinds | A row's kind is not one of the Kinds table |
| Printed | A Self-test row names a label that module's self-test does not print |
| Gaps tracked | A Missing row names no issue |
| Reasons given | An Untestable row gives no reason |
| Well formed | A line opening an FR row does not parse |

## Kinds

| Kind | Use when |
| ---- | -------- |
| Self-test | One or more self-test checks prove the rule |
| Untestable | No script can see the rule, such as a working practice; the cell says why |
| Missing | A script follows the rule but no self-test plants it yet; the cell names the issue |

## 01 Functional suitability

| ID | Kind | Checked by |
| -- | ---- | ---------- |
| FR-01-01 | Self-test | `report.py` "one landed after the first trial is refused"<br>`report.py` "one merged after the first trial is read at the merge"<br>`report.py` "a registration landed before the first trial passes, across zones" |
| FR-01-02 | Self-test | `report.py` "one changed and not committed is refused"<br>`report.py` "an amendment on a branch of its own is refused" |
| FR-01-03 | Self-test | `report.py` "a trial on another spec is refused"<br>`report.py` "a trial on another prompt is refused"<br>`report.py` "every trial on the registered spec passes"<br>`report.py` "every trial on the one prompt passes" |
| FR-01-04 | Self-test | `report.py` "a scorable trial recording no spec is refused"<br>`report.py` "a scorable trial recording no prompt is refused" |
| FR-01-05 | Self-test | `harness.py` "a spec edited mid-run refuses the next trial unbuilt"<br>`harness.py` "a spec changed as it is copied refuses the trial and frees its slot"<br>`harness.py` "a round-5 run on other content is refused"<br>`harness.py` "round 5's registered digest is SPEC.md's content" |
| FR-01-06 | Self-test | `report.py` "a trial start with no UTC offset is refused" |
| FR-01-07 | Untestable | How a commit reached `main` is the owner's practice, and no script sees it. |

## 02 Performance efficiency

| ID | Kind | Checked by |
| -- | ---- | ---------- |
| FR-02-01 | Self-test | `harness.py` "each block starts one arm later"<br>`harness.py` "over five blocks every arm runs in every place" |
| FR-02-02 | Self-test | `report.py` "every pairing improves by the same amount -> better"<br>`report.py` "every pairing improves, unstably -> better"<br>`report.py` "three identical differences -> better"<br>`report.py` "the differences change sign -> no improvement shown"<br>`report.py` "a downward metric that fell -> better"<br>`report.py` "a downward metric that rose -> worse" |
| FR-02-03 | Self-test | `report.py` "10 more lines on 100 is preserved"<br>`report.py` "20 more lines on 100 is not"<br>`report.py` "1.5 more per KLOC on 20 is preserved"<br>`report.py` "3 more per KLOC on 20 is not"<br>`report.py` "no baseline makes no relative claim" |
| FR-02-04 | Self-test | `report.py` "every per-KLOC row carries the static margin"<br>`report.py` "every primary the judge asks for is led with, worded and given its margins" |
| FR-02-05 | Self-test | `report.py` "round 5 holds adherence within one item, 8 pp" |
| FR-02-06 | Self-test | `report.py` "a rise inside the band is held"<br>`report.py` "a rise wholly past the band is worse"<br>`report.py` "one that straddles the band is undecided"<br>`report.py` "a band that holds zero is held"<br>`report.py` "round 5 reads a 10 % rise in app code as held" |
| FR-02-07 | Untestable | No script applies it: from round 5d adherence decides nothing, so the rule binds a person reading an earlier round's report. |
| FR-02-08 | Untestable | No script calls a trim free; a person reading the report applies it, on the held rows the report prints. |
| FR-02-09 | Self-test | `report.py` "from six blocks no interval is called descriptive"<br>`report.py` "a round too small to decide says so in the report and the appendix" |

## 03 Trial count

| ID | Kind | Checked by |
| -- | ---- | ---------- |
| FR-03-04 | Self-test | `harness.py` "a round-5 run takes K = 15 and refuses more"<br>`harness.py` "a K past the registered ceiling refuses"<br>`harness.py` "a round-5d run of hand and short takes K = 15 too" |
| FR-03-05 | Self-test | `report.py` "one trial of the last block leaves the round part-run"<br>`report.py` "a round 5 run short of its last block says it is provisional"<br>`report.py` "a round-5 run short of its K names the blocks still owed" |

## 04 Failed and lost trials

| ID | Kind | Checked by |
| -- | ---- | ---------- |
| FR-04-01 | Self-test | `harness.py` "a clean finish is completed"<br>`harness.py` "the budget cap is budget"<br>`harness.py` "one that never answers is ended at the timeout"<br>`score.py` "only completed, budget and timeout endings are offered, under the arms' words" |
| FR-04-02 | Self-test | `judge.py` "only a build that did not install goes unjudged"<br>`report.py` "a build that did not install has its judge rows missing" |
| FR-04-03 | Untestable | The harness has no path that re-runs a trial ended by the agent; FR-04-04 proves only a lost one re-runs. |
| FR-04-04 | Self-test | `harness.py` "a usage limit, by its wording is blocked"<br>`harness.py` "a rate limit, by its status is blocked"<br>`harness.py` "an error behind a zero status is blocked"<br>`harness.py` "an error subtype nobody listed is blocked"<br>`harness.py` "no JSON at all is blocked" |
| FR-04-05 | Self-test | `harness.py` "a blocked trial re-runs in its place"<br>`harness.py` "the re-run names the trial it substitutes"<br>`score.py` "a blocked trial yields to its re-run" |
| FR-04-06 | Self-test | `harness.py` "a voided workspace is kept under void/"<br>`harness.py` "a voided trial takes its whole pen and its tarball" |
| FR-04-07 | Self-test | `harness.py` "a second block stops the run" |
| FR-04-08 | Self-test | `harness.py` "--from short-2 starts there and keeps the order"<br>`harness.py` "--from an unknown trial refuses"<br>`harness.py` "no trial stays recorded as running" |

## 05 Reliability

| ID | Kind | Checked by |
| -- | ---- | ---------- |
| FR-05-01 | Self-test | `harness.py` "the scratch home is the home"<br>`harness.py` "the settings file carries the rules and the isolation"<br>`harness.py` "a trial reads the workspace's project settings and no other source" |
| FR-05-02 | Self-test | `harness.py` "ANTHROPIC_API_KEY is removed"<br>`harness.py` "CLAUDECODE is removed"<br>`harness.py` "VIRTUAL_ENV is removed"<br>`harness.py` "the interpreter leaves PATH" |
| FR-05-03 | Self-test | `harness.py` "other trials, their change tasks, home and void are denied"<br>`harness.py` "this repository and the scoring area are denied"<br>`harness.py` "tarballs and run records are denied"<br>`harness.py` "the templates source is denied whenever one is set"<br>`harness.py` "the trial's own workspace is not denied" |
| FR-05-04 | Self-test | `harness.py` "a trial may not fetch or search the web" |
| FR-05-05 | Self-test | `harness.py` "a planted Git helper answers outside a trial"<br>`harness.py` "it does not answer inside one" |
| FR-05-06 | Self-test | `harness.py` "every kill by name meets a deny rule" |
| FR-05-07 | Self-test | `harness.py` "every call reaching past the trial is flagged"<br>`harness.py` "the root, another pen and a climb out of the pen are flagged"<br>`harness.py` "a fetch of the templates is flagged, and only that"<br>`harness.py` "a kill by name that ran, or never answered, is a hit"<br>`harness.py` "a scorable trial with a reach becomes reached"<br>`harness.py` "the trial's own paths are not flagged, a pip extra included" |
| FR-05-08 | Self-test | `report.py` "its record's clean scan is read again and flagged"<br>`report.py` "a trial whose scan hit is named"<br>`report.py` "a reached build trial is left out whole" |
| FR-05-09 | Self-test | `harness.py` "the one running from the trial is stopped"<br>`harness.py` "two planted processes run and are listed"<br>`harness.py` "the record lists what was stopped" |

## 06 Security

| ID | Kind | Checked by |
| -- | ---- | ---------- |
| FR-06-01 | Self-test | `score.py` "empty tree: ruff is missing, not zero"<br>`score.py` "empty tree: mypy is missing, not zero"<br>`score.py` "empty tree: coverage is missing, not zero"<br>`score.py` "tools absent: ruff is missing, not zero"<br>`score.py` "tools absent: bandit is missing, not zero"<br>`score.py` "an empty tree reports nothing seen"<br>`score.py` "a failed listing is missing, never an empty list" |
| FR-06-02 | Self-test | `score.py` "a skipped check is recorded beside the rate"<br>`score.py` "a partial suite is flagged"<br>`score.py` "a suite that skipped nothing is not partial" |
| FR-06-03 | Self-test | `security.py` "an application that will not boot loses every runtime probe"<br>`security.py` "an administrator that cannot sign in loses what needs one"<br>`security.py` "the lost probes count against the rate" |
| FR-06-04 | Self-test | `security.py` "no report from the probe is missing, not lost"<br>`security.py` "an audit of nothing is missing, not zero"<br>`security.py` "a report that is not JSON is missing"<br>`security.py` "no roots is missing, not zero" |
| FR-06-05 | Self-test | `report.py` "an unmeasured column reads not measured"<br>`report.py` "an unmeasured run answers Not measured in every cell" |

## 07 Maintainability

| ID | Kind | Checked by |
| -- | ---- | ---------- |
| FR-07-01 | Self-test | `score.py` "the battery installs from a lock it resolved" |
| FR-07-02 | Self-test | `score.py` "only the tools reach the lock"<br>`score.py` "the lock carries none of the trial's dependencies" |
| FR-07-03 | Self-test | `score.py` "ruff and mypy take the harness's configuration, not the trial's" |
| FR-07-04 | Self-test | `score.py` "a scoring environment runs the spec's Python"<br>`score.py` "no Python at the spec's version refuses to score"<br>`score.py` "a score on another Python refuses the root"<br>`report.py` "scores on two Pythons are refused" |
| FR-07-05 | Self-test | `score.py` "the planted package is discovered"<br>`score.py` "an empty tree yields no roots" |
| FR-07-06 | Self-test | `score.py` "every extra and every group requirement is installed" |
| FR-07-07 | Self-test | `score.py` "a test dependency the lock refuses leaves coverage missing" |

## 08 Flexibility

| ID | Kind | Checked by |
| -- | ---- | ---------- |
| FR-08-01 | Self-test | `judge.py` "the trial's code reaches the bundle"<br>`judge.py` "scoring's output and the environment's stay out of the bundle"<br>`judge.py` "the skills arm's skills stay out of the bundle" |
| FR-08-02 | Self-test | `judge.py` "one seed gives one judging order"<br>`judge.py` "the order is not the arms' order, and holds every repeat"<br>`judge.py` "the unblinding map is written outside the bundles the judge reads" |
| FR-08-03 | Self-test | `judge.py` "a path naming the trial is a leak"<br>`judge.py` "an escaped path naming the trial is a leak"<br>`judge.py` "a leak in a directory the copy skips is found"<br>`judge.py` "a bundle holding neither has no leak"<br>`generate_arm.py` "the leak scan reports a planted token and passes clean text" |

## 09 Scoring

| ID | Kind | Checked by |
| -- | ---- | ---------- |
| FR-09-01 | Self-test | `harness.py` "the scoring area lies outside the run root"<br>`harness.py` "this repository and the scoring area are denied" |
| FR-09-02 | Self-test | `score.py` "an application that seeds on start, and has no default secret, boots under scoring"<br>`score.py` "a build capped below Python 3.13 installs" |
| FR-09-03 | Self-test | `score.py` "an hx-* error is set aside and another counts" |
| FR-09-04 | Self-test | `score.py` "app code is the app's Python and templates, not its tests"<br>`score.py` "test code is a tests directory or a pytest name, anywhere"<br>`score.py` "docs and configuration count toward no size"<br>`score.py` "committed bytecode and a database are artifacts nobody asked for" |
| FR-09-05 | Self-test | `score.py` "the checklist holds 13 items and reads none as any arm" |
| FR-09-06 | Self-test | `probes.py` "every design probe answers in the one structure report"<br>`probes.py` "a module's role follows what it imports"<br>`probes.py` "a module import tariff loads that reaches the store is a violation"<br>`probes.py` "an initializer on the way to an imported module is loaded too"<br>`probes.py` "an import inside a function is outside what import tariff loads"<br>`probes.py` "an import under if TYPE_CHECKING loads nothing"<br>`probes.py` "an import under a main guard loads nothing"<br>`probes.py` "an inverted main guard runs on import, so its import counts"<br>`probes.py` "a relative import names the package's module, not a driver"<br>`probes.py` "a package wins over a module of its name, as in Python"<br>`probes.py` "without a package entry the layering reading is missing, not zero"<br>`probes.py` "Decimal arithmetic inside a route is money in a route"<br>`probes.py` "a bool parameter is named by file, function and argument"<br>`probes.py` "an abstract base over rule kinds is an extension point"<br>`probes.py` "a three-deep conditional on a rule's kind is a kind ladder"<br>`probes.py` "the public surface is read against the names the spec requires"<br>`probes.py` "a price parameter annotated as a connection leaks IO"<br>`probes.py` "the import graph is a measurement or a named absence"<br>`probes.py` "a print call, a ticket citation and an exception base are findings"<br>`probes.py` "logging without a NullHandler is reported as used and unhandled"<br>`probes.py` "without source roots the structure metric is missing, not zero" |
| FR-09-07 | Self-test | `score.py` "churn counts an edit and a new file, not an environment"<br>`score.py` "the churn plant landed" |
| FR-09-08 | Self-test | `harness.py` "the change prompt names the API and fields the grader drives"<br>`harness.py` "the change prompt is read whole from its file" |
| FR-09-09 | Untestable | An order of work; the round's registration fixes it. |

## 10 The judge

| ID | Kind | Checked by |
| -- | ---- | ---------- |
| FR-10-01 | Self-test | `judge.py` "each tree is read three times by default"<br>`report.py` "a trial's repeats are meaned, and one judging means itself" |
| FR-10-02 | Self-test | `judge.py` "the default judge is gpt-6-astra through codex"<br>`judge.py` "the default effort is high"<br>`judge.py` "the codex command carries the model and the effort"<br>`judge.py` "the recorded effort is the one passed" |
| FR-10-03 | Self-test | `judge.py` "it may read and nothing else"<br>`judge.py` "the claude backend is not in plan mode" |
| FR-10-04 | Self-test | `report.py` "agreement is counted per row over the trials both read" |
| FR-10-05 | Self-test | `report.py` "a direction the other judge reverses loses its verdict"<br>`report.py` "a direction both judges read keeps its verdict"<br>`report.py` "a contrast the other judge did not read keeps its verdict"<br>`report.py` "the rounds' own judge is caught posing as the other" |
| FR-10-06 | Self-test | `report.py` "the judge is checked by its evidence, not a person" |
| FR-10-07 | Self-test | `control/control.py` "the domain imports flask"<br>`control/control.py` "ValidationError derives from TariffError"<br>`control/control.py` "the secret key is a literal"<br>`control/control.py` "customer data is written to the log" |
| FR-10-08 | Self-test | `control/control.py` "a base archive with another sha256 is refused" |
| FR-10-09 | Untestable | A judged control root is read by hand, and [validation](validation.md) records each reading. |

## 11 Security and data protection

| ID | Kind | Checked by |
| -- | ---- | ---------- |
| FR-11-01 | Self-test | `security.py` "exposed fails every probe"<br>`security.py` "hardened passes every probe"<br>`security.py` "exposed rates are zero"<br>`security.py` "hardened rates are whole" |
| FR-11-02 | Self-test | `security.py` "exposed signs in"<br>`security.py` "hardened signs in" |
| FR-11-03 | Self-test | `security.py` "every planted secret form is counted"<br>`security.py` "every planted debug form is counted"<br>`security.py` "every planted assembled statement is counted"<br>`security.py` "parameters, plain f-strings and constant names are not assembled SQL"<br>`security.py` "hardened source finds no secret" |
| FR-11-04 | Self-test | `security.py` "every vulnerability of every package is counted" |
| FR-11-05 | Self-test | `security.py` "public pages with a forgeable sign-in fail only its CSRF probe"<br>`security.py` "public pages with a token-checked sign-in pass every probe"<br>`security.py` "a refused forgery passes though a failed sign-in answers as a real one" |
| FR-11-06 | Self-test | `report.py` "every probe rate reads the rate security.py files" |

## 12 The report

| ID | Kind | Checked by |
| -- | ---- | ---------- |
| FR-12-01 | Self-test | `report.py` "a contrast crossing rounds carries no verdict and counts nowhere"<br>`report.py` "a comparison across rounds reads as not given, not too few runs" |
| FR-12-02 | Self-test | `report.py` "a contrast across rounds is unpaired, with a verdict"<br>`report.py` "a round-5d run reads H4 against a reused `none`, unpaired"<br>`report.py` "an unpaired contrast leaves out two trials, not blocks" |
| FR-12-03 | Self-test | `report.py` "it prints every declared contrast its arms ran"<br>`report.py` "a three-arm run prints only its own contrasts" |
| FR-12-04 | Self-test | `report.py` "round 5 reports the files it supersedes without a verdict" |
| FR-12-05 | Self-test | `report.py` "the report links its appendix, and the appendix the record"<br>`report.py` "the appendix holds what produced the results, the radar's axes and the verdict vector, and nothing else" |
| FR-12-06 | Self-test | `report.py` "the radar draws a panel per arm, with the bare ring, in both themes"<br>`report.py` "an axis is better minus worse over its rows with a verdict, None without one"<br>`report.py` "the summary is the radar, one image per theme" |
| FR-12-07 | Self-test | `report.py` "the report names each approach and its verdict in plain words"<br>`report.py` "a better primary and no worse answers Yes"<br>`report.py` "a worse primary answers Worse"<br>`report.py` "nothing separated answers No" |
| FR-12-09 | Self-test | `report.py` "withdrawal blanks every value of the row"<br>`report.py` "its verdict vector row reads withdrawn"<br>`report.py` "the withdrawal section names it and why"<br>`report.py` "a run graded by another revision withdraws nothing"<br>`report.py` "a metric not withdrawn keeps its verdict" |
| FR-12-10 | Self-test | `score.py` "a score on another Python refuses the root"<br>`report.py` "scores on two Pythons are refused"<br>`report.py` "a run graded by another revision withdraws nothing" |
| FR-12-12 | Self-test | `report.py` "a sub-score is the share of its measured targets met, and one with none reads not measured"<br>`report.py` "an axis is the mean of its measured sub-scores, each weighing the same"<br>`report.py` "an arm is the mean over its trials"<br>`report.py` "a broken build counts against Reliability only"<br>`report.py` "a marker turns only past the axis's margin"<br>`report.py` "an axis that could not be read carries no marker"<br>`report.py` "the move shown is the contrast's mean over the blocks it paired"<br>`report.py` "a withdrawn metric's target is not measured"<br>`report.py` "an axis contrast over fewer pairs than blocks names its count"<br>`report.py` "the aggregate keeps the ISO reading where the round draws it"<br>`report.py` "the plain words follow the ISO markers, with the cost on its own line"<br>`report.py` "an axis not measured leaves no vertex, unlike a measured 0 %"<br>`report.py` "every axis label fits inside the image and clear of the other panel"<br>`report.py` "every target reads a metric row, a probe or a reading of the radar's own"<br>`report.py` "every axis carries a margin"<br>`report.py` "the tables mark a thin sub-characteristic and read an empty one as not measured"<br>`report.py` "the ISO radar draws a panel per arm with its cost, the target ring, the markers by shape, in both themes"<br>`report.py` "an axis label reads its share and its move past the margin"<br>`report.py` "a round after the pilot draws the ISO radar, and the pilot its own"<br>`report.py` "a later round's report, appendix and images carry the ISO radar" |

## 13 Records and archive

| ID | Kind | Checked by |
| -- | ---- | ---------- |
| FR-13-01 | Self-test | `harness.py` "the record is written as every trial starts and ends"<br>`harness.py` "every trial records the CLI's version, read as it starts" |
| FR-13-02 | Self-test | `generate_arm.py` "every generated arm's file has its generation record beside it" |
| FR-13-03 | Self-test | `archive.py` "readings, judgings, map and lock come; bundles do not"<br>`archive.py` "the original tarball's hash is recorded"<br>`archive.py` "the revisions are recorded"<br>`archive.py` "a reading changed in the archive fails the verify" |
| FR-13-04 | Self-test | `archive.py` "a reading changed after the stamp is a problem"<br>`archive.py` "the report refuses docs/audits/ without a current stamp"<br>`report.py` "a report into a templates source's docs/audits needs the stamp" |
| FR-13-05 | Self-test | `archive.py` "the restored root reads as the original does"<br>`archive.py` "a restored record points at the restored tarball and void"<br>`archive.py` "a restored transcript keeps its time" |

## 14 One run at a time

| ID | Kind | Checked by |
| -- | ---- | ---------- |
| FR-14-01 | Self-test | `score.py` "a live score.py run refuses a second"<br>`judge.py` "a live judge.py run refuses a second"<br>`security.py` "a live security.py run refuses a second" |
| FR-14-02 | Self-test | `harness.py` "an ended run is taken over"<br>`harness.py` "a live pid that is not the tool is taken over" |
