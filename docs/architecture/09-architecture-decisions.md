# 9. Architecture decisions

Every decision the benchmark has taken, dated, with its reason. The log is
append-only: a later row supersedes an earlier one, and no row is edited
for meaning.

An issue number refers to `solid-ai-dev/solid-ai-templates`, where the
benchmark lived until the split. A dash marks a decision taken in this
repository. A chapter reference points to where that rule now lives. A row
that mentions the design means the document these chapters replaced.

## 9.1 Decision log

| Date | Decision | Why | Issue |
|---|---|---|---|
| 2026-09-12 | The app is `tariff`, chosen over `logsift`, `flowkit`, `ledger` and `convert` | Natural object model, two extension axes, sharp decimal tests | #1712 |
| 2026-09-12 | The hand-written arm runs | Only it separates the templates from having any file | #1705 |
| 2026-09-12 | K = 3, one bounded escalation to 5 | The smallest set an interval can be computed on; the bound stops sampling to significance | #1705 |
| 2026-09-12 | Generator `claude-sonnet-5` at effort `high`; judge `gpt-6-astra` through `codex exec`, effort set explicitly | What a typical adopter runs; a stronger model's ceiling would hide the effect; a different vendor judges | #1711 |
| 2026-09-12 | The hidden suite lives in the private `braboj/tariff-hidden-suite` | This repository is public, so a suite here is one search away from a future trial | #1705 |
| 2026-09-12 | Flask stays | Server-rendered Jinja with HTMX is its home ground | #1705 |
| 2026-09-12 | The baseline runs against `v2.90.0`, before the v3.0 split moves any template | [ch. 4.2](04-solution-strategy.md)'s comparison needs a baseline older than the move | #1705 |
| 2026-09-12 | The hidden suite is written and validated before any trial | Written afterwards, it would be shaped by the first outputs ([ch. 10.6](10-quality-requirements.md)) | #1714, #1715 |
| 2026-09-12 | The brief names the two extension axes | An adopter would; [ch. 5.5.4](05-building-block-view.md) states what that costs | #1713 |
| 2026-09-12 | The change task adds a spend threshold and a capped rate, replacing a first draft of buy-one-get-one and a reduced rate | Both first-draft items were already expressible by configuration, so every arm would score zero churn | #1717 |
| 2026-09-12 | Trials are bounded by `--max-budget-usd` and a timeout | The installed CLI (2.1.153) has no `--max-turns` | #1710 |
| 2026-09-15 | HTML validity sets aside errors on `hx-*` attributes | The spec requires HTMX; otherwise the metric counts how much HTMX a trial uses | — |
| 2026-09-15 | The escalation reads the effect in either direction, on any contrast; a row with no interval triggers nothing | An escalation owed only to a favourable effect would lean toward "better" | — |
| 2026-09-16 | Security and data protection become primary dimensions from round 3 | Owner decision after reading round 1's report | #1767 |
| 2026-09-16 | Round 1 is read for security with checks declared after the run | Its fixed security checks passed on every trial and separated nothing | #1766 |
| 2026-09-17 | The report opens with a 1–10 score per contrast, replacing "no single headline number" | Asked for after reading round 1 | #1786 |
| 2026-09-17 | The finding table opens the report | Asked for after reading the score table | #1789, #1791, #1796, #1798 |
| 2026-09-17 | Round 1's change-task pass rate is withdrawn | Its grader built the new rule and rate through names the prompt never gave | #1772 |
| 2026-09-17 | No human holdout | Scoring many implementations by hand cannot be sustained, and a person in the loop breaks [ch. 4.3](04-solution-strategy.md) | #1774 |
| 2026-09-17 | Round 2 holds length fixed and adds the hybrid model | Owner's reading of round 1: the generated file is too long to add quality, and a short one can¹ | #1795 |
| 2026-09-18 | The score table stays only for contrasts between two files | Beside the finding table it repeated itself | #1820 |
| 2026-09-18 | A contrast crossing rounds gets no verdict | Round 2's `full` read Worse because `none` moved between rounds, not the file | #1826 |
| 2026-09-19 | The primaries are anchored and checked by the control fixture | Unanchored, `design` and `maintainability` scored 3 on all 24 trials of rounds 1–2 | #1827, #1829, #1830 |
| 2026-09-19 | Each tree is judged three times | Six judgings of one unchanged tree disagreed ([ch. 10.6](10-quality-requirements.md)) | #1830 |
| 2026-09-19 | A second judge, Claude, reads the control fixture only | A second vendor's reading of the same trees; never averaged with the rounds' judge | #1831 |
| 2026-09-24 | Round 3 starts anew with all five arms and reuses no trial | The spec gained sign-in and customers, and the judge changed | #1767 |
| 2026-09-24 | Eight contrasts, adding `short − full` | Does length matter | #1767 |
| 2026-09-24 | The brief and the change prompt live in files of their own | The design's restructure would have broken the code that read them by heading | #1843 |
| 2026-09-24 | The change prompt states the API, the form fields and the rules its acceptance modules check; the UI is graded by HTTP cases from round 3 | A grader driving names the prompt never gave grades guessing; the UI was asked for but never graded | #1767 |
| 2026-09-24 | The brief names customers as personal data under the GDPR and one signing-in administrator; `hand` gains two generic lines (OWASP ASVS level 1, GDPR) | An adopter storing customers would say so. `hand`'s lines stay generic: lines mirroring the probes would hand it the answer key | #1767 |
| 2026-09-24 | Security and data protection: an anchored judge row and a probe pass rate each, all primary; probe margins mean no probe lost | A judge row alone is an opinion; the probes are deterministic. Security regressions get no tolerance | #1767 |
| 2026-09-24 | The control's application for the security and data-protection rows is one uncounted calibration trial on the extended spec | The first application has no sign-in or customers; the reference implementation is a worked answer and stays private | #1767 |
| 2026-09-25 | A probe the trial keeps from running is lost, not missing | Missing would drop it from the rate, so a trial would score higher for not signing in | #1767 |
| 2026-09-25 | The security and data-protection rows' 3 describes the common defences and nothing more; their 5 asks for an explicitly configured deployment and one declaration of what is personal | Anchored first at a level the calibration application already met, both rows fell on damage and could not rise | #1767 |
| 2026-09-25 | Design's 1 names the damage to layering, and dispatch on concrete classes with the layers kept apart is a 3 | Under `claude-opus-5-5` the base and the damaged tree both scored 2, each judged on that dispatch | #1767 |
| 2026-09-25 | The rounds' judge is `claude-opus-5-5`; `gpt-6-astra` reads a sample as a cross-check | gpt-6-astra's plan allows about thirty judgings a week and a round needs three times as many; Opus 5.5 runs on capacity the owner already pays for | #1767 |
| 2026-09-26 | `short`'s instruction asks the model to measure every line against the width before answering | On the round-3 brief two generations in a row were refused, with 1 and then 9 lines over 88 characters; retrying until one passed would select the tersest sample, and dropping the width lets a line carry a paragraph | #1767 |
| 2026-09-27 | The SQL probe counts a statement only where an interpolated value cannot be traced to the module's constants | SQLite binds values only, so a table name, a PRAGMA value or a migration script has to be interpolated; round 3's 23 hits were all such, and every user value was bound | #1882 |
| 2026-10-15 | A round is archived to the private `braboj/tariff-runs`, verified by restoring it and recomputing the report's figures, before the report is written under `docs/audits/` | Round 3's run root and scoring area were deleted with nothing kept, so none of its readings can be re-run, re-judged or cross-checked | #1904 |
| 2026-10-15 | Round 3's K = 5 escalation is recorded as unrunnable, and its report stays at K = 3 | The escalation adds blocks 4 and 5 to round 3's root, which no longer exists; re-running the whole round would not reproduce the three blocks its report read | #1767 |
| 2026-10-15 | Round 4 is judged by `claude-opus-5-5` alone, without the cross-check | The owner keeps `gpt-6-astra`'s weekly plan free; round 4's thirty build trials would take all of it. The same-vendor caveat round 3 carried stands for round 4 | #1903 |
| 2026-10-15 | The security probes read a client as signed in by what it is shown beside an anonymous client, not by `GET /` answering 200 | The thin specification lets the dashboard be public, and a public dashboard read a CSRF-checked sign-in as forged: 100 % fell to 90.91 %, past round 4's 9-point threshold | #1876 |
| 2026-10-15 | A trial is both fenced and excluded: its file tools are denied every path it may not reach, and a trial whose transcript still reaches one, through the shell, is voided and re-run once; a second reach loses it without stopping the run | A deny rule matches a shell command's prefix, not its paths, so the shell cannot be fenced; a trial that read the hidden suite measures the suite, so counting it was never an option, and deciding after its scores were seen would be | #1907 |
| 2026-10-15 | The cross-check reads whole blocks, reports agreement per judge row, and withholds a verdict only where the two judges read opposite directions | A shared vendor could favour the templates' style in every arm; opposite signs is the disagreement a verdict cannot survive, and a missed confirmation is what the interval already weighs | #1903 |
| 2026-10-16 | A trial may not stop processes by name: the commands are denied, one that ran voids the trial, and a trial whose harness died under it is voided before the next run re-runs it `--from` that trial | Round 4's thin run ended after one trial when an agent stopped its dev server with `Get-Process -Name python \| Stop-Process`, which stopped the harness too; a probe showed a deny rule's glob matches anywhere in a command, chained ones included, and lets a stop by PID through | #1928 |
| 2026-10-27 | Round 5 is judged by `gpt-6-astra` through `codex exec` at effort `high` alone, three times per trial, with no cross-check | The owner's OpenAI plan is raised to cover a round's judgings. With a judge from another vendor than every round-5 builder, the same-vendor concern the cross-check answered is gone, and a second judge could only withhold verdicts | — |
| 2026-10-27 | Each round names its builder models in its registration, and none comes from the vendor of the rounds' judge | The models are a knob a round sets, not a fixed list. A builder from the judge's vendor would bring back the self-preference the cross-check once answered, which no longer runs | — |
| 2026-10-27 | Round 5 runs block A alone, at K = 15 with no escalation, each block starting one arm later; adherence is held within 8 pp, and H2 reads the mean over pairs of trials. Blocks B and C wait for a later round | The report's rules, run on round 3's per-trial noise, decide almost nothing at K = 3: H1 is supported in 29 % of rounds when true, and a chance "worse" turns up in 36 %. At K = 15 those are 73 % and 12 %. On round 4's noise, B and C would contradict block A by chance at any affordable K | — |
| 2026-10-28 | From round 5, size reads app code's lines and files against a band of 20 %, smallest change 40 %; test lines are reported without a verdict; docs and configuration leave size; committed generated files count as artifacts nobody asked for | A better solution is often a little bigger, with tests and layering. Round 4's source lines missed templates, and its file count was mostly docs, templates and committed bytecode | — |

¹ This agrees with Anthropic's guidance on context engineering, which asks for the
smallest set of high-signal tokens: [Effective context engineering for AI
agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents).

## 9.2 Decisions about the templates

The decisions about the templates themselves, such as ADR-052 (hybrid is
the delivery floor) and ADR-058 (task procedures load on demand), live in
`solid-ai-templates` under `docs/decisions/`. A round's hypotheses name the
record they decide.
