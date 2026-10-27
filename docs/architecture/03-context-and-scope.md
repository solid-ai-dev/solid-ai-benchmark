# 3. Context and scope

The benchmark sits between the templates it measures and the services that
build, judge and store. This chapter draws that boundary: who is on either
side, what crosses it, and over which channel.

## 3.1 Business context

![The benchmark as one box with its neighbours. The owner gives it settings, and report readers get reports from it. It exchanges builds with Claude Code and judgings with the Codex CLI, and exchanges packages with the Python package index. Templates come in from the templates source and reports go back to it. The hidden suite gives it acceptance tests, and it sends archived rounds to the runs archive](../diagrams/context.png)

| Neighbour | Gives the benchmark | Gets from the benchmark |
| --------- | ------------------- | ----------------------- |
| Owner | A registered hypothesis, a round's settings, the go to run | Refusals before cost, records after |
| Report reader | Nothing | The dated report and its caveats |
| Claude Code | Builds and generated files | Workspaces and prompts |
| Codex CLI | Judgings, from round 5 | Blind bundles to judge |
| Python package index | The packages every app and every tool installs | Nothing |
| Templates source | The templates, the chain and the release an arm is built from | Reports under its `docs/audits/` |
| Hidden suite | Acceptance tests and the change suite, at scoring only | Nothing |
| Runs archive | A restored round, for a re-read | Each round's raw data |

Outside the boundary:

| Not the benchmark's | Who owns it |
| ------------------- | ----------- |
| The templates and the generator's instructions | The templates source |
| What the report concludes for a decision record | The owner, in the templates source |
| The hidden suite's checks and their reference implementation | `braboj/tariff-hidden-suite` |
| The models' behaviour | Anthropic and OpenAI |

## 3.2 Technical context

The channel to each neighbour, and who opens it.

| Interface | Between | Channel | Opened by |
| --------- | ------- | ------- | --------- |
| Agent session | harness and Claude | `claude -p`, prompt on standard input, JSON result on standard output, transcript in the scratch home | The harness |
| Generation | `generate_arm.py` and Claude | The same CLI, one non-interactive invocation per arm | The generator |
| Judging | `judge.py` and the judge CLI | `claude` or `codex exec`, the rubric as a JSON Schema, the bundle on standard input | The judge script |
| Hidden suite | `score.py` and GitHub | `gh repo clone` at a pinned revision, into the scoring area only | The scorer |
| Package installs | Trials, scoring, tools and PyPI | `pip` over HTTPS, the tools from `tool-lock.txt` | The trial or the scorer |
| Templates | Every script and the templates source | A local git clone, named by `--templates` | The operator |
| Archive | `archive.py` and `braboj/tariff-runs` | Files written into a local clone, pushed by the operator | The operator |
| Report | `report.py` and the templates source | A Markdown file under `docs/audits/` | The report script |

## 3.3 The app under test

### 3.3.1 What it does

"Tariff" here means a price list. `tariff` is a small invoicing engine: it
takes a basket of products and computes the final bill, with discounts and
tax. The tax is VAT or sales tax, not customs duty.

| Piece | What it is | Example |
|---|---|---|
| Product | A SKU, a name, a unit price and a tax category | `COF-250G`, "Coffee", €10.00, category `food` |
| Discount rules | Percentage, bulk ("buy 3, pay 2"), tiered (cheaper unit price from a quantity), coupon code | 10 % off coffee; coupon `WELCOME` takes €5 off |
| Jurisdiction | A country or region with a tax rate per category and a default rate | DE: `food` 7 %, everything else 19 % |
| Invoice | A currency, lines of product × quantity, and coupon codes | 3 × coffee, EUR, `WELCOME` |

A SKU (Stock Keeping Unit) is the unique code a shop gives each product it
sells. A 1 kg bag of the same coffee would be another SKU.

`price()` works in a fixed order: line discounts first, then invoice-wide
discounts, then those discounts spread back over the lines, then each line
taxed at its category's rate. Every amount is exact to the cent.

It suits the benchmark for three reasons:

- Its domain is naturally modelled with objects and classes.
- It has two independent extension axes, discount kinds and jurisdictions,
  so a missed Strategy pattern shows.
- Exact decimal arithmetic makes the hidden tests unforgiving.

The app is offline and deterministic, about 1,500–2,000 lines of code.

### 3.3.2 What the spec fixes

`tests/efficacy/SPEC.md` names what other software depends on, so the
hidden suite can drive it:

- **Domain:** products, the four discount kinds with their precedence and
  stacking, jurisdictions with rate tables, invoices.
- **Money:** `Decimal` throughout, one currency per invoice, half-even
  rounding at named points, totals reproducible to the cent.
- **Python API:** `tariff.Catalog`, `tariff.Invoice`,
  `tariff.price(invoice, rules, jurisdiction)`, the error base
  `TariffError`. The package imports without the web app.
- **Web UI:** Flask, Jinja and HTMX pages for products, rules and
  jurisdictions, and an invoice builder that re-prices on every change.
  Pages work with JavaScript disabled.
- **HTTP:** named routes, a JSON export, form posts with server-side
  validation and CSRF.
- **Persistence:** one SQLite file, schema owned by the app, a seed fixture.
- **Sign-in and customers:** one seeded administrator and every route
  behind sign-in; customers with a name, email and address, billed on
  invoices; erasure on request; a JSON export of one customer's data.
- **Constraints:** no network, Python 3.12, valid HTML.

### 3.3.3 What the spec leaves out

**The spec says what the app does, never how it is engineered.** It does not
name:

- a layout, linter, type checker, logging policy or test convention
- an error hierarchy's shape or a template organisation
- an accessibility bar
- how a password is stored, what a failed sign-in says, or where a redirect
  may lead
- whether an erased customer's data leaves the database file

Why: the "how" is what a context file adds. If the spec said "hash the
password", every arm would, and the benchmark would measure nothing.
