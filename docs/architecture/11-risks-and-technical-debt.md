# 11. Risks and technical debt

What could make a result wrong, or the benchmark hard to keep running.
Each risk names what holds it today.

## 11.1 Risks to a result

| # | Risk | Held by | Open |
| - | ---- | ------- | ---- |
| 1 | Three trials cannot reach significance: 27 distinct resamples, a minimum two-sided p of 0.25 | Every interval is printed as descriptive. One escalation to K = 5 | Round 4's escalations are owed and not run. Round 3's cannot run, its raw data lost |
| 2 | One app: every effect may be `tariff`'s | `ledger` stays sealed for the final claim | No second app has run |
| 3 | One builder agent | | Another agent reading `AGENTS.md` is untested |
| 4 | A judge that shares a vendor with the builder may favour the templates' own style | From round 5 the judge is `gpt-6-astra`, another vendor's model than every builder | |
| 5 | A judge row is an opinion | Anchors, three readings, the evidence check, the control fixture | |
| 6 | The spec states what a file would add, so nothing is left to improve | Round 4's thin spec | Vague, pressure and conflict specs are untested |
| 7 | A missing setting measures the setting, not the code: round 4's hybrid app refused to start without a secret key the spec never named | Both specs now name `TARIFF_SECRET_KEY`, and scoring supplies it | |
| 8 | The model changes under a round | Exact ids pinned, arms interleaved | A provider-side change within one id is not detectable |
| 9 | Every trial is one session | | Drift over a project's life, the templates' strongest claim, is untested |

## 11.2 Technical debt

| # | Debt | Cost | Next step |
| - | ---- | ---- | --------- |
| 1 | No CI runs the self tests in this repository | A regression in a guard shows only when a round runs. The control guide says its self test runs in CI, which no longer holds since the split | Add a workflow that runs every `--self-test` |
| 2 | Windows-specific handling: `.CMD` shims, `cmd.exe` expansion, process trees | A run on another platform is untested | State the platform in the harness guide, or test one |
| 3 | `harness.py` and `report.py` each run past 3,000 lines | A change is hard to review in isolation | Split by stage when next touched |
| 4 | Round 1's trials keep their letter names on disk (`A1`, `B2`, `C3`) | Every reader maps them | None while round 1 is read |
| 5 | The reports land in the templates source, not here | A reader of this repository finds no results | A results index here, linking each report |
| 6 | Round 5's arms are registered but not yet built | Its hypotheses wait on harness work | Design [round 5's registration, 13.4](../rounds/round-5.md) |

## 11.3 Confounds and their controls

A confound is a second cause mixed up with the one being tested, so the
result cannot say which produced it. A control is what rules it out.

| Confound | Control |
|---|---|
| Your global `CLAUDE.md` or hooks reach the bare arm | A scratch home per trial; the harness refuses a run when a `CLAUDE.md` exists in that home or any parent directory |
| The agent reads the templates, the hidden suite or the web | Nothing mounted; web tools off; Git credentials cleared; the file tools denied this repository, the scoring area and every other entry of the run root; transcripts scanned, a trial with a hit voided and re-run once in its place, and one the report's re-scan flags left out of every figure |
| A trial stops the harness, or another process on the machine | Shell commands that stop processes by name are denied, and stopping one by PID or port is not; a trial whose transcript shows one that ran is voided and re-run like a reach; a trial in flight when its harness died is voided by the next run on that root, which refuses the root while that harness still runs |
| `hybrid` legitimately carries the templates | Its reads of its own vendored copy are not a reach; naming the repository by URL or owner still is |
| The model changes between trials | Exact id pinned; trials interleaved |
| The agent sees the acceptance tests | The hidden suite stays outside the workspace until scoring |
| The judge favours its own family or longer output | Every arm has the same generator; no builder comes from the judge's vendor; blind; shuffled; length reported |
| The judge sees which arm it reads | Context files, the vendored templates and condition markers are stripped; a bundle still naming its arm is refused |
| The judge's score is noise | Three judgings per tree, averaged |
| The judge's scale cannot move | Anchored primaries, validated by the control fixture ([ch. 8.6.7](08-crosscutting-concepts.md)) |
| A grader measures something else | Withdrawn measurements ([ch. 8.7.5](08-crosscutting-concepts.md)) |
| A trial is lost to the provider | One re-run in place ([ch. 8.1.4](08-crosscutting-concepts.md)) |
| The spec changes between rounds | No trial is reused across spec versions |
| The bar moves after seeing results | The rules in [ch. 1.4](01-introduction-and-goals.md) and this document are committed before the first trial |
| One task measures one task | A stated limitation; `ledger`, a second app, stays sealed for the final claim |
