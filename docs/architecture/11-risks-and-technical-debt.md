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
| 6 | Round 5's arms are registered but not yet built | Its hypotheses wait on harness work | Design §13.4 |
