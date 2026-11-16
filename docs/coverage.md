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
| FR-01-01 | Self-test | `report.py` "one landed after the first trial is refused"<br>`report.py` "one merged after the first trial is read at the merge"<br>`report.py` "a registration landed before the first trial passes, across zones"<br>`report.py` "the main branch is read locally, else as origin's, and a clone with neither is refused, not crashed" |
| FR-01-02 | Self-test | `report.py` "one changed and not committed is refused"<br>`report.py` "an amendment on a branch of its own is refused" |
| FR-01-03 | Self-test | `report.py` "a trial on another spec is refused"<br>`report.py` "a trial on another prompt is refused"<br>`report.py` "every trial on the registered spec passes"<br>`report.py` "every trial on the one prompt passes"<br>`report.py` "a named round's trial on a spec or prompt its entry does not pin is refused, each task held to its own" |
| FR-01-04 | Self-test | `report.py` "a scorable trial recording no spec is refused"<br>`report.py` "a scorable trial recording no prompt is refused" |
| FR-01-05 | Self-test | `harness.py` "a spec edited mid-run refuses the next trial unbuilt"<br>`harness.py` "a spec changed as it is copied refuses the trial and frees its slot"<br>`harness.py` "a round-5 run on other content is refused"<br>`harness.py` "round 6's registered digest is SPEC.md's content, and round 5's is another" |
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
| FR-04-09 | Self-test | `harness.py` "a blocked trial is probed at once, so an answer costs no wait"<br>`harness.py` "a blocked trial is probed and re-run by default, and --stop-on-block stops the run instead"<br>`harness.py` "probing stops when the generator answers"<br>`harness.py` "probing gives up at its limit" |
| FR-04-10 | Self-test | `harness.py` "a trial whose ceiling outlasts its token asks the generator first"<br>`harness.py` "a token that outlasts the ceiling is left alone"<br>`harness.py` "a generator that does not answer the ask is reported, and the trial goes on to its own ending"<br>`harness.py` "without a credentials file nothing is asked"<br>`harness.py` "a dry run asks the generator for no token, so it calls no model" |

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
| FR-06-06 | Self-test | `probes.py` "the web probe signs in and reads the pages behind it"<br>`probes.py` "a post without a token and a raw name are findings once signed in"<br>`probes.py` "a refusal says nothing about the token until a post with it is stored"<br>`probes.py` "a sign-in that does not hold fails the form rows and measures nothing"<br>`probes.py` "a page refused for want of a sign-in is withheld, not measured" |
| FR-06-07 | Self-test | `probes.py` "axe counts the WCAG 2.1 A and AA rules, not its best practice" |

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
| FR-09-10 | Self-test | `score.py` "a shallow clone starts at the newest revision"<br>`score.py` "the suite is checked out at the revision asked for"<br>`score.py` "a revision the suite has not is refused"<br>`score.py` "a short hash is refused, since the scores record the full one" |

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
| FR-12-02 | Self-test | `report.py` "a contrast across rounds is unpaired, with a verdict"<br>`report.py` "a round-5d run reads H4 against a reused `none`, unpaired"<br>`report.py` "an unpaired contrast leaves out two trials, not blocks"<br>`report.py` "a contrast crosses rounds where its arms ran in different roots, reused or not"<br>`reuse.py` "a trial copied on keeps the root it ran in as its origin"<br>`reuse.py` "a quality reading comes along with its trial" |
| FR-12-03 | Self-test | `report.py` "it prints every declared contrast its arms ran"<br>`report.py` "a three-arm run prints only its own contrasts"<br>`report.py` "a run of round 6's new arms reads each against none, in plain words" |
| FR-12-04 | Self-test | `report.py` "round 5 reports the files it supersedes without a verdict" |
| FR-12-05 | Self-test | `report.py` "the report links its appendix, and the appendix the record"<br>`report.py` "the appendix holds what produced the results, the radar's axes and the verdict vector, and nothing else" |
| FR-12-06 | Self-test | `report.py` "the radar draws a panel per arm, with the bare ring, in both themes"<br>`report.py` "an axis is better minus worse over its rows with a verdict, None without one"<br>`report.py` "the summary is the radar, one image per theme" |
| FR-12-07 | Self-test | `report.py` "the report names each approach and its verdict in plain words"<br>`report.py` "a better primary and no worse answers Yes"<br>`report.py` "a worse primary answers Worse"<br>`report.py` "nothing separated answers No" |
| FR-12-09 | Self-test | `report.py` "withdrawal blanks every value of the row"<br>`report.py` "its verdict vector row reads withdrawn"<br>`report.py` "the withdrawal section names it and why"<br>`report.py` "a run graded by another revision withdraws nothing"<br>`report.py` "a metric not withdrawn keeps its verdict" |
| FR-12-10 | Self-test | `score.py` "a score on another Python refuses the root"<br>`report.py` "scores on two Pythons are refused"<br>`report.py` "a run graded by another revision withdraws nothing" |
| FR-12-12 | Self-test | `report.py` "a sub-score is the share of its measured targets met, and one with none reads not measured"<br>`report.py` "an axis is the mean of its measured sub-scores, each weighing the same"<br>`report.py` "an arm is the mean over its trials"<br>`report.py` "a broken build counts against Reliability only"<br>`report.py` "a marker turns only past the axis's margin"<br>`report.py` "an axis that could not be read carries no marker"<br>`report.py` "the move shown is the contrast's mean over the blocks it paired"<br>`report.py` "a withdrawn metric's target is not measured"<br>`report.py` "an axis contrast over fewer pairs than blocks names its count"<br>`report.py` "the aggregate keeps the ISO reading where the round draws it"<br>`report.py` "the plain words follow the ISO markers, with the cost on its own line"<br>`report.py` "an axis not measured leaves no vertex, unlike a measured 0 %"<br>`report.py` "every axis label fits inside the image and clear of the other panel"<br>`report.py` "every target reads a metric row, a probe or a reading of the radar's own"<br>`report.py` "every axis carries a margin"<br>`report.py` "the tables mark a thin sub-characteristic and read an empty one as not measured"<br>`report.py` "the ISO radar draws a panel per arm with its cost, the target ring, the markers by shape, in both themes"<br>`report.py` "an axis label reads its share and its move past the margin"<br>`report.py` "a round after the pilot draws the ISO radar, and the pilot its own"<br>`report.py` "a later round's report, appendix and images carry the ISO radar" |
| FR-12-13 | Self-test | `report.py` "round 5e reads under round 5d's rules, against its own registration, owing its own arms' blocks"<br>`report.py` "round 5e's contrasts are declared: each map arm against none and every reused arm, and the skill against the file"<br>`report.py` "H7 to H9 are supported when every row is held or better, refuted by any worse row, reliability's included"<br>`report.py` "the plain report asks round 5e's questions, not round 5d's"<br>`report.py` "the plain report qualifies H7's answer with what the map's use says" |
| FR-12-14 | Self-test | `report.py` "the map's use counts each template read or skill loaded, with its turn, and those before the first write"<br>`report.py` "an arm's map is its skills or its vendored chain, and the bare arm has none"<br>`report.py` "a shell command that writes counts as the first write, a template off the map is not counted, and a trial that never wrote says nothing about reading up front"<br>`report.py` "every trial's reads are listed with their turns"<br>`report.py` "the aggregate keeps each trial's map use"<br>`report.py` "a shell read of a template counts, a redirection to the null device or into another stream is no write, an edit in place or a download is one, and a brace list expands"<br>`report.py` "with no trial that wrote, the note beside H7 withholds the reading"<br>`report.py` "quoted text is no shell operator, and a path a shell command lists or tests is not read"<br>`report.py` "a shell command is read one simple command at a time: every operand of a reading command counts, and a verb in an argument is no command"<br>`report.py` "a subagent's reads count at the turn that delegated, and a wildcard stands for every template of the map it matches"<br>`report.py` "a map no trial read is said to be ignored, not read on demand"<br>`report.py` "a trial that read and never wrote beside one that wrote and never read shows no on-demand reading"<br>`report.py` "each subagent is charged to the turn that started it, and a separator inside quotes splits no command"<br>`report.py` "a read before the writing command of one shell call comes before the write, a here-document body is no command, and a backslash continues a line"<br>`report.py` "a skills arm's shell write counts, a redirection after a here-document opener stays, a subagent is charged to the delegating message, and a search's pattern is no file"<br>`report.py` "a subagent pointing at the previous delegation's result is charged to its own delegation, a quoted pattern is one operand, a path follows the call's directory change, a wildcard stands for no slash, a loop's files are read by the body's command that reads its variable, a flag names a search's pattern, and a quoted null device is no write" |
| FR-12-15 | Self-test | `report.py` "the screen drops an arm worse than none on a deciding row, ranks the rest by rows better and then by cost, and keeps four"<br>`report.py` "the screen names the arms round 6 runs"<br>`report.py` "the screen names no arm for round 6 while the run is short of its K"<br>`report.py` "a reused arm short of its K holds the screen as a fresh one does"<br>`report.py` "a deciding row not computed yet holds the screen"<br>`report.py` "a candidate out on a row read worse holds the screen for no unread row"<br>`report.py` "the screen ranks what it holds and names no arm for round 6 while a candidate is missing" |
| FR-12-16 | Self-test | `report.py` "an ISO-read arm's verdict is worse on an axis worse, better on one better with none worse, and no clear gain otherwise"<br>`report.py` "the plain words name the axes behind an ISO-read verdict"<br>`report.py` "the summary's axis table of an ISO-read run is the ISO radar's, marked as the chart is" |
| FR-12-17 | Self-test | `report.py` "the ISO screen drops an arm worse on an axis, ranks the rest by axes better and then by cost, and keeps four"<br>`report.py` "an axis no target measures neither holds nor moves the ISO screen"<br>`report.py` "an axis that lists targets but has no reading yet holds the ISO screen"<br>`report.py` "the ISO screen names the arms round 6 runs and the axis that put one out" |
| FR-12-18 | Self-test | `report.py` "a pilot round read by the ISO radar is only a draft, never in or under docs/reports/, and keeps its aggregate beside the registered one"<br>`report.py` "a pilot round read by the ISO radar says it is post hoc and that its axes decide"<br>`report.py` "a run read by the ISO radar refuses a cross-check, whose withheld rows its markers would still count" |
| FR-12-21 | Self-test | `report.py` "the report loads a trial's quality reading beside its security reading"<br>`report.py` "a lost quality probe reads failed, a missing one not measured"<br>`report.py` "every reading the quality reader files reads as its target: lost fails, missing or a gone tree is not measured"<br>`report.py` "the latency target is not measured until its cutoff is registered, then met within it" |
| FR-12-22 | Self-test | `report.py` "a module passes whole only where no check failed, errored or was skipped"<br>`report.py` "a module absent from a report is not measured only where the suite's revision did not hold it"<br>`report.py` "a suite the build held past its time fails every module, and one never run is not measured" |
| FR-12-23 | Self-test | `report.py` "a pilot round read by the ISO radar keeps the targets it had before round 6, unless round 6's are asked for"<br>`report.py` "round 6's targets are refused where no pilot draft reads them" |

## 13 Records and archive

| ID | Kind | Checked by |
| -- | ---- | ---------- |
| FR-13-01 | Self-test | `harness.py` "the record is written as every trial starts and ends"<br>`harness.py` "every trial records the CLI's version, read as it starts" |
| FR-13-02 | Self-test | `generate_arm.py` "every built arm's file has its generation record beside it"<br>`report.py` "a pilot arm no script builds keeps its record for the report, and its vendored templates" |
| FR-13-03 | Self-test | `archive.py` "readings, judgings, map and lock come; bundles do not"<br>`archive.py` "the original tarball's hash is recorded"<br>`archive.py` "the revisions are recorded"<br>`archive.py` "a reading changed in the archive fails the verify"<br>`archive.py` "an archived round drops its trees and environments" |
| FR-13-04 | Self-test | `archive.py` "a reading changed after the stamp is a problem"<br>`archive.py` "a quality reading changed after the stamp is a problem"<br>`archive.py` "the report refuses docs/reports/ without a current stamp"<br>`report.py` "a report into any docs/reports needs the stamp" |
| FR-13-05 | Self-test | `archive.py` "the restored root reads as the original does"<br>`archive.py` "a restored record points at the restored tarball and void"<br>`archive.py` "a restored transcript keeps its time" |
| FR-13-06 | Self-test | `generate_arm.py` "the two map arms name the same moments in the chain's order"<br>`generate_arm.py` "the reading map names every template of the chain once, under docs/solid-ai-templates/"<br>`generate_arm.py` "each template skill is its template verbatim, named by the manifest"<br>`generate_arm.py` "a chain file the manifest does not describe is refused" |
| FR-13-07 | Self-test | `generate_arm.py` "every built root opens with the brief, verbatim, the emitted ones too"<br>`generate_arm.py` "every committed arm's root opens with the brief, verbatim"<br>`generate_arm.py` "the brief and the facts name the stack and no tooling" |
| FR-13-08 | Self-test | `generate_arm.py` "a built file naming a tool is refused" |
| FR-13-09 | Self-test | `report.py` "with no --out-dir it lands in this repository's docs/reports/, needing the stamp but no templates source" |
| FR-13-10 | Self-test | `generate_arm.py` "every committed arm is what the script builds at its recorded ref, byte for byte, the same twice" |
| FR-13-11 | Self-test | `harness.py` "C1 pins SPEC.md, both prompts and its fixtures by content"<br>`harness.py` "an unknown round is refused"<br>`harness.py` "an arm the round does not register is refused"<br>`harness.py` "a K past the round's registered K is refused"<br>`harness.py` "a C1 run reads its spec from its entry, not its arms' names"<br>`harness.py` "a build or change prompt the round does not pin is refused" |
| FR-13-12 | Self-test | `harness.py` "every trial record of a named round names its round, task, arm and block"<br>`harness.py` "a named round's run record names its round, registration and fixtures"<br>`harness.py` "a root holding another round's or registration's runs is refused"<br>`harness.py` "a named round and records naming none never share a root"<br>`harness.py` "a named round's trial record missing its identity is refused"<br>`harness.py` "a named round's run refuses a root whose records name none"<br>`harness.py` "recovery keeps a named round's identity in its run record"<br>`harness.py` "a run whose trials name a round under a header naming none is refused" |
| FR-13-13 | Self-test | `report.py` "a run its records name C1 does not read as a pilot round"<br>`report.py` "a root mixing a named round's records with others is refused"<br>`report.py` "a named round's record missing its identity is refused, not read as the pilot's"<br>`report.py` "a run whose trials name a round under a header naming none is refused, not read as the pilot's" |
| FR-13-14 | Self-test | `harness.py` "a round of two tasks is complete only with both at K for every arm"<br>`harness.py` "a change task counts though its arm's build trial failed"<br>`report.py` "a C1 round owes a block until both tasks are in for every arm"<br>`report.py` "a C1 block whose builds stand only as change tasks is still owed" |
| FR-13-15 | Self-test | `harness.py` "an empty fixture manifest refuses a named round's change task"<br>`harness.py` "a fixture listed without its baseline readings is refused"<br>`harness.py` "a fixture whose tarball differs from its listed hash is refused, at the start and at each trial"<br>`harness.py` "block b starts from the b-th qualifying build, ascending, cycling"<br>`harness.py` "a named round's change run records how many distinct fixtures its blocks take"<br>`harness.py` "a named round's change task needs no build trial of its arm"<br>`harness.py` "a change run whose manifest or block mapping differs from the root's earlier change runs is refused" |
| FR-13-16 | Self-test | `harness.py` "a change workspace keeps its fixture's code and tests"<br>`harness.py` "a change workspace drops the fixture's instructions, settings, databases, caches, environments and history"<br>`harness.py` "a change workspace carries the round's spec and only its arm's context"<br>`harness.py` "a change workspace starts from one commit, with nothing uncommitted"<br>`harness.py` "every arm's change workspace of a block holds the same code" |
| FR-13-17 | Self-test | `report.py` "a named round's change task with no build score is read on its own"<br>`report.py` "a reached build of a named round keeps its change reading, and a reached change task goes alone"<br>`report.py` "a change task standing alone counts on its ISO axes, not as a broken build"<br>`report.py` "a change task standing alone reads no build Python"<br>`report.py` "a named round's change result reads the same whether its build is unscored, working or broken" |
| FR-13-18 | Self-test | `reuse.py` "a named round's trials copied on keep its round in the run record's header"<br>`reuse.py` "a reuse never mixes a named round's trials with others"<br>`reuse.py` "a trial copied within a named round names that round in its origin"<br>`report.py` "trials reused within one named round pair with those run there" |
| FR-13-19 | Self-test | `report.py` "a named round is refused until its registration document is on main before its first trial"<br>`report.py` "a trial reused within its named round counts toward when the round began" |
| FR-13-20 | Self-test | `archive.py` "a C1 change task's score changed in the archive fails the verify" |
| FR-13-21 | Self-test | `reuse.py` "the readings are filed under the word and name their origin"<br>`reuse.py` "a quality reading comes along with its trial"<br>`reuse.py` "the judgings keep their labels and the map is theirs alone" |
| FR-13-22 | Self-test | `generate_arm.py` "the section files hold every rule block the inline root does, and no other"<br>`generate_arm.py` "the sections map names every section file once, under .agents/sections/"<br>`generate_arm.py` "a rule dropped from a section file, or a file the map does not name, is reported"<br>`harness.py` "the lazysections arm's files land where its map names them, out of the index"<br>`report.py` "the sections arm's map is its section files, and a Read or a shell read of one counts as a use"<br>`report.py` "a named round's report prints its sections arm's use of the map" |
| FR-13-23 | Self-test | `generate_arm.py` "lazyref and lazyrefold differ by the check-loop commit's lines alone, all in its section"<br>`generate_arm.py` "a line changed besides the commit's, one of its lines missing, or one outside its section is reported"<br>`generate_arm.py` "a lazyref committed at another ref than the check-loop commit is reported"<br>`harness.py` "round 6's lazyrefold vendors at its own recorded ref, lazysections vendors nothing" |
| FR-13-24 | Self-test | `generate_arm.py` "no on-demand arm tells the agent to read everything at startup"<br>`generate_arm.py` "a root telling the agent to read everything at the start is caught" |

## 14 One run at a time

| ID | Kind | Checked by |
| -- | ---- | ---------- |
| FR-14-01 | Self-test | `score.py` "a live score.py run refuses a second"<br>`judge.py` "a live judge.py run refuses a second"<br>`security.py` "a live security.py run refuses a second"<br>`quality.py` "a live quality.py run refuses a second"<br>`archive.py` "a live quality.py run refuses a second" |
| FR-14-02 | Self-test | `harness.py` "an ended run is taken over"<br>`harness.py` "a live pid that is not the tool is taken over" |

## 15 Quality probes

| ID | Kind | Checked by |
| -- | ---- | ---------- |
| FR-15-01 | Self-test | `quality.py` "a sound app passes every probe"<br>`quality.py` "an app answering 500 on bad input fails fuzz_robustness, and no other probe"<br>`quality.py` "an app raising out of the client fails fuzz_robustness, and no other probe"<br>`quality.py` "an app whose form page answers 500 fails fuzz_robustness, and no other probe"<br>`quality.py` "a form that cannot be reached is no handled request"<br>`quality.py` "a value one malformed request stored reaches no other case"<br>`quality.py` "an app whose writes lock fails concurrent_writes, and no other probe"<br>`quality.py` "an app dropping an overlapping write fails concurrent_writes, and no other probe"<br>`quality.py` "the locked write is read as locked"<br>`quality.py` "a writer the app hangs fails concurrent_writes, and no other probe"<br>`quality.py` "a hung writer stops the run, every reading before it kept"<br>`quality.py` "a product a malformed request stored does not reach the concurrent writes"<br>`quality.py` "an app refusing 500 lines fails capacity_500_lines, and no other probe"<br>`quality.py` "an app that cannot show 500 lines fails capacity_500_lines, and no other probe"<br>`quality.py` "an app keeping 100 of 500 lines fails capacity_500_lines, and no other probe"<br>`quality.py` "an export with a null line fails capacity_500_lines, and no other probe"<br>`quality.py` "an export whose total is NaN fails capacity_500_lines, and no other probe"<br>`quality.py` "an export answered 500 fails capacity_500_lines, and no other probe"<br>`quality.py` "an app pricing every line at nothing fails capacity_500_lines, and no other probe"<br>`quality.py` "a database opened by a file URI with a query stays in its folder"<br>`quality.py` "a total over the first 100 of 500 exported lines fails capacity_500_lines, and no other probe"<br>`quality.py` "an app reading each line on its own fails n_plus_one, and no other probe"<br>`quality.py` "statements are counted per page, and did not grow"<br>`quality.py` "instances sharing their data fail coexistence, and no other probe"<br>`quality.py` "an app writing outside its folder fails coexistence, and no other probe"<br>`quality.py` "the stray file is named"<br>`quality.py` "a second instance whose product list answers 500 fails coexistence, and no other probe"<br>`quality.py` "a write outside before a hang still fails coexistence, the path kept"<br>`quality.py` "a database outside, opened read-only, is no stray write" |
| FR-15-02 | Self-test | `quality.py` "a sound app signs in"<br>`quality.py` "a sign-in form quoted with single quotes signs in"<br>`quality.py` "a form's own token is posted, not one from a form before it"<br>`quality.py` "a post no form's action names carries the page's first token"<br>`quality.py` "a save sent by its control's formaction carries its form's token"<br>`quality.py` "a save control outside its form, linked by its id, carries that form's token"<br>`quality.py` "a save redirected to a relative location reads as the sound app's"<br>`quality.py` "an app answering 401 until signed in, and never signing in, loses every probe"<br>`quality.py` "an app answering 403 to a malformed request loses fuzz_robustness, and no other probe"<br>`quality.py` "an app that never keeps its sign-in loses every probe, passing none"<br>`quality.py` "an app answering a malformed request with the sign-in's redirect loses fuzz_robustness, and no other probe"<br>`quality.py` "the redirect is read as lost, not as an answer" |
| FR-15-03 | Self-test | `quality.py` "an app that will not boot loses every probe"<br>`quality.py` "a trial that did not install loses every probe"<br>`quality.py` "no report from the probe is missing, not lost"<br>`quality.py` "a stalled run keeps what it read and loses the rest"<br>`quality.py` "a run that stalled booting loses every probe" |
| FR-15-04 | Self-test | `quality.py` "the latency is two repeats of 30 requests each"<br>`quality.py` "a slowed app reads slower by its delay" |
| FR-15-05 | Self-test | `quality.py` "a build that serves its page on the other Python passes portability"<br>`quality.py` "a build that boots on its own Python only fails portability"<br>`quality.py` "a build whose sign-in fails on the other Python fails portability"<br>`quality.py` "a build the other Python will not install fails portability"<br>`quality.py` "no other Python is missing, not passed" |
| FR-15-06 | Self-test | `quality.py` "a reading's environment is gone once it is read"<br>`quality.py` "a trial whose source tree is gone is missing, not lost" |

## 16 The changed tree

| ID | Kind | Checked by |
| -- | ---- | ---------- |
| FR-16-01 | Self-test | `score.py` "a changed tree is scored on every reading a build is"<br>`score.py` "a file the scorer's install writes is no unasked artifact of a changed tree"<br>`score.py` "an unchanged app that writes a secret beside its database at boot shows no churn"<br>`score.py` "a changed tree with the change's names exports no extra one, and one without them misses each"<br>`score.py` "the build is read against the build's names, the change against the change's too" |
| FR-16-02 | Self-test | `score.py` "a change keeping every interface the fixture passed reads 1"<br>`score.py` "an interface module the change broke reads 0 and is named"<br>`score.py` "a skipped or unrun interface module is not kept"<br>`score.py` "a module the fixture already failed is inherited, not the change's"<br>`score.py` "a module the change repaired reads repaired"<br>`score.py` "a build suite that ran out of time fails every interface, not missing"<br>`score.py` "interfaces read missing with no frozen baseline, no build suite, or none the fixture passed"<br>`harness.py` "a fixture whose baseline leaves an interface module unread is refused" |
| FR-16-03 | Self-test | `security.py` "a change task is read from its own scores into security-scores-change"<br>`security.py` "a changed tree that does not install loses its probes, as a build's does"<br>`quality.py` "a change task is read from its own scores into quality-scores-change" |
| FR-16-04 | Self-test | `quality.py` "a version 2 that migrates the old database keeps every record"<br>`quality.py` "a schema change shipped without a migration fails the upgrade"<br>`quality.py` "an old database rebuilt empty fails the upgrade"<br>`quality.py` "a rate the migration changes fails the invoices saved again too"<br>`quality.py` "category rates cleared or changed by the migration fail the upgrade through the exports"<br>`quality.py` "a customer the migration rewrites fails through the customer's export alone"<br>`quality.py` "a change's field dropped on an old file fails through the invoices that exercise it"<br>`quality.py` "a new jurisdiction stored with other rates fails through its invoices"<br>`quality.py` "a seeded rule that will not be deleted stops the change's invoices, never passes"<br>`quality.py` "old invoices that break on the new field fail the upgrade"<br>`quality.py` "a version 2 that will not open the old database loses the upgrade"<br>`quality.py` "every planted upgrade fault fails"<br>`quality.py` "a fixture that cannot seed leaves the upgrade missing, not failed"<br>`quality.py` "the list pages are read for the seeded identifiers alone, whatever their markup"<br>`quality.py` "an export answering an error fails the upgrade, naming its status"<br>`quality.py` "an invoice saved after the upgrade whose CSV export errs fails it"<br>`quality.py` "a change task with no starting commit leaves the upgrade missing"<br>`quality.py` "a changed tree that does not install loses the upgrade, its fixture named" |
| FR-16-05 | Self-test | `judge.py` "a changed tree that did not install goes unjudged, read from its own scores"<br>`judge.py` "a change task's trees are found by their trial, apart from the build's"<br>`judge.py` "a changed tree's bundle naming its trial in a path leaks"<br>`judge.py` "a changed tree's bundle carries the pinned change requirements, a build's none"<br>`judge.py` "a changed tree's judge is told the change extends the spec, after the build's prompt unchanged"<br>`judge.py` "a change task's judging run hands the judge the change's note and the bundle its requirements" |
| FR-16-06 | Self-test | `report.py` "a change task's security, quality and judgings go with its change score, apart from the build's"<br>`report.py` "a change reading left out takes its own readings along"<br>`report.py` "the interfaces sit on Interoperability and the data upgrade on Adaptability, once each"<br>`report.py` "a pilot round's table reads no change-task target"<br>`report.py` "a change kept, broken, lost or unread reads met, not met, not met and not measured"<br>`report.py` "a named round's change targets read whatever its build did" |
| FR-16-07 | Self-test | `archive.py` "a change task's security and quality readings and judgings are archived beside its score"<br>`archive.py` "a C1 change task's quality reading flipped in the archive fails the verify"<br>`reuse.py` "a change task comes with its arm's build trials, in a change run naming its round's fixtures"<br>`reuse.py` "a change task's score, security and quality readings and judgings come along under their own folders"<br>`reuse.py` "change tasks join a target only from the manifest its change runs took" |
| FR-16-08 | Self-test | `report.py` "a named round reads the ISO radar once a task, the build's first"<br>`report.py` "a C1 run gives lazysections and lazyrefold a verdict and a cost on each task, against none"<br>`report.py` "each task's radar reads that task's trees against `none` on the same task"<br>`report.py` "the change task's radar reads its own security, not the build's"<br>`report.py` "a named round's build radar leaves the change targets to the change task's"<br>`report.py` "each task's radar shows its own mean billed cost per trial"<br>`report.py` "a pilot round draws one radar, its trials as they are"<br>`report.py` "the summary gives a radar, a verdict and a cost for each task, each named"<br>`report.py` "a named round's report draws the change task's radar beside the build's and tables each task's axes"<br>`report.py` "a named round with no build reads its finding table from the change task's own trials and cost"<br>`report.py` "named pairs are read for every metric of a table" |
| FR-16-09 | Self-test | `report.py` "the check loop is kept on a 10 % cost drop on each task with no axis worse"<br>`report.py` "the check loop is not kept on the build task's readings alone"<br>`report.py` "a cost drop under 10 % on one task does not keep the check loop"<br>`report.py` "an axis worse on either task does not keep the check loop"<br>`report.py` "nothing flagged worse reads no degradation detected, beside the non-inferiority read apart"<br>`report.py` "an interval crossing the margin is inconclusive, never non-inferior"<br>`report.py` "the report and its full record print the registered readings"<br>`report.py` "a cost drop of exactly 10 % keeps the gate, read from the unrounded differences"<br>`report.py` "a cost drop a float's error under 10 % meets the gate"<br>`report.py` "a cost drop a float's error under 10 % reads yes in the table and keeps the loop"<br>`report.py` "C1 reads an axis non-inferior only with its lower bound strictly above minus the margin"<br>`report.py` "a round running none of the registered pairs prints none of them" |
| FR-16-10 | Self-test | `report.py` "an arm delivers on demand only reading fewer templates than reference and non-inferior to it"<br>`report.py` "an arm whose reads were not counted is not shown on demand"<br>`report.py` "each task's templates read are counted from its own transcripts, a section file by a read or a shell command"<br>`report.py` "a task's reading left out of the report counts no template use on that task"<br>`report.py` "a wildcard read of one skill's folder counts that skill once, another file there none"<br>`report.py` "a skill's file read or shell-read is that skill used, once with its loading" |
