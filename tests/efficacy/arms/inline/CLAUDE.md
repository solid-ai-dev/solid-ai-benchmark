# tariff

Pricing and invoicing web application — Imbra Ltd
Owner: Imbra Ltd. Runs locally only; no repository URL, live URL or deployment target applies.
- Model: inline

## 1. Project

### 1.1 Overview

`tariff` assembles invoices from a product catalog, several kinds of discount
rule, tax jurisdictions and customers. Stack: Python 3.12, Flask 3, Jinja,
HTMX, SQLite. It runs locally, with no deployment target.

Two actors use it: an administrator working in a browser, and a separate
program that imports the pricing engine directly as a library, without the
web application present. The store is a local SQLite file. Nothing in this
application reaches the network: no outbound HTTP call, no inbound API
beyond the local web UI, no CORS surface, no SSRF surface. Do not add one
without revisiting this file.

One administrator signs in to use the web application; nobody else has an
account. Customers are people: the system stores each one's name, email and
postal address, and names them on the invoices billed to them. Imbra Ltd is
in the EU, so GDPR applies — see section 6.

### 1.2 Project structure

See `README.md` for the directory map; do not duplicate it here.

Placement rule: keep the pricing engine in its own package, with no import
of Flask, Jinja, HTMX or any other web-layer module. It must import and run
correctly with the web application absent. The web application package may
import the pricing engine; the reverse must never happen.

### 1.3 Commands

The project has not yet chosen a package manager, test runner, type
checker, linter or formatter. Until it does, each command below names what
it must do, not how:

- **Install**: resolve and install the project's pinned dependencies from
  its lockfile.
- **Migrate**: apply pending SQLite schema migrations through a committed
  script before the application starts.
- **Run**: start the Flask application locally, reading the port from an
  environment variable, with a sensible default for local development.
- **Test**: run the automated test suite (unit and integration) covering
  both the pricing engine library and the web application.
- **Type-check / Lint / Format**: run the project's static type checker,
  linter and formatter, each in its strict and quiet mode, reporting zero
  issues.

## 2. Architecture boundaries

- Keep the pricing engine a standalone Python library with no dependency on
  Flask, Jinja, HTMX or any web-layer code (MUST); it must import and run
  with the web application absent.
- Treat the web application as one caller of the pricing engine, never a
  second place that computes a price, discount or tax figure — call the
  library; never re-implement its logic in a route handler or a template.
- Keep the module graph acyclic: the web application depends on the
  pricing engine; the pricing engine never imports the web application
  (MUST).
  **Check**: no module under the pricing-engine package imports anything
  from the web-application package; the check must report zero violations.
- Treat the pricing engine's public functions and classes as the contract
  the other program — its second caller — depends on. Apply the
  deprecation rule (section 3.2) before changing or removing any of them.
- Give the pricing engine package its own version, independent of the web
  application's; bump it deliberately, following semantic versioning,
  whenever its public API changes.
- Never let the pricing engine write to standard output or standard error,
  and never let it configure logging beyond its own logger (MUST). Make
  its logger injectable, falling back to its own module logger, so each
  caller captures its output on its own terms.
  **Check**: run the library alone in a fresh process and confirm it emits
  nothing on stdout or stderr; a test runner's own log handler can hide a
  default that would otherwise leak into both callers.

## 3. Code conventions

### 3.1 Git

- Commit under one full name and one consistent email; never change
  identity mid-project.
- Work on a branch; never commit directly to `main`.
- Never commit build output, dependency directories or secrets. Commit a
  generated file only when the project tracks it on purpose.
- Keep a `.gitignore` (MUST) covering dependencies, build output, secrets,
  editor state, OS files and coverage output.
- Commit lockfiles (MUST).
- Inspect the working tree and the index before starting a task. Never
  discard, reset, stash or overwrite a change the task did not make.
  Stage only the changes the task made — a whole file only when it held
  no prior change, otherwise only the task's hunks. Read the staged diff
  before committing. Stop and ask when a task change and a prior change
  share a hunk. Report a pre-existing change that blocks the task rather
  than removing it.
- Keep a pull request to one concern (SHOULD). Test locally before
  committing. Review the diff against the base before merging, in the
  order security, correctness, clarity, conventions. Merge only after the
  review passes and CI is green.
- Read the CI run for the push before describing a change as good. Treat
  a pull request with no registered check as not passed. Never merge
  while a check is failing, cancelled or not yet registered. Re-run a
  verification a pull request claims once the base has moved since it was
  written. Read a new or changed workflow's first run in its real
  environment before trusting it.
- Never force-push, including with `--force-with-lease` (MUST NOT). Bring
  a branch up to date by merging the base into it, never by rebasing and
  force-pushing.

**Off-limits paths** (MUST NOT change without explicit approval; propose
first, with a rollback strategy and the tests that would catch a
regression):

- Authentication and session code (the administrator's sign-in).
- SQLite migrations.
- `.env*` and secrets.
- CI/CD workflow files, if and when the project adds any.
- Payment code: not applicable — this application does not process
  payments.

A diff confined to prose is ordinary work; a comment a tool reads (a
linter disable, a coverage pragma) counts as executable content and is
off-limits the same as a command or a permission. Name an off-limits path
at the top of a change's summary whenever the diff touches one, proposal
or not.
**Check**: the change summary names every off-limits path the diff
touches; the check must report zero undeclared touches.

### 3.2 Python

- Keep one authoritative representation of each piece of pricing, discount
  or tax knowledge (DRY). Build only what a stated requirement justifies
  (YAGNI); record beside every deferral the concrete condition that
  reopens it. Delete a path once evidence shows it unreachable.
- Compute derived counts and statistics from the data; never hardcode
  them. Remove unused modules, assets and data files promptly.
- Name a function with a verb, a class or module with a noun, a boolean
  with `is`, `has` or `can`. Rename a name that needs a comment to explain
  it. Use the same name for the same concept in every module.
- Keep cognitive complexity at or under 15 per function; nest at most
  three levels; use guard clauses and early returns. Replace a boolean
  flag that selects behaviour with an enum or two named functions.
- Name every magic number and string as a constant — a discount
  percentage, a tax rate, a threshold. Size a tuned threshold from its
  measured distribution, naming the data source beside the constant;
  take a limit a specification fixes (e.g. a tax jurisdiction's own
  rounding rule) from that specification instead.
- Keep coupling shallow: a change inside one module must not require
  changes in unrelated modules. Talk only to direct dependencies. Reach a
  heavy or platform-limited dependency through one module that owns its
  import.
- Validate input at boundaries and fail at once on invalid state. Read a
  value from its source-of-truth field, and raise when it is missing;
  never fall back to a value derived from a slug, name or hash. Add an
  error type only where a caller could act differently. Never let a
  caller-side filter stand in for a precondition.
- Deprecate a public symbol, naming its replacement, before a later change
  removes it. Deprecate every part of one call site together; never alias
  the outer name alone.
- Keep constants beside the functions that use them.
- Encode every committed text file in UTF-8 with LF line endings (MUST);
  keep identifiers ASCII (MUST). Set a program's output encoding
  explicitly wherever another program reads its output — in particular,
  the invoice export path. Commit a `.gitattributes` with `* text=auto`,
  adding `eol=lf` for hard LF.
  **Check**: every tracked text file is UTF-8 with LF endings and ASCII
  identifiers; the check must report zero exceptions.
- Prefer code that needs no comment. Never cite a ticket, PR or ADR number
  in a comment or docstring — state the substance. Name a source (author,
  year, method) where a tax or discount rule's logic is non-obvious.
- Commit no debug output (`print()`) and no hardcoded breakpoint. Delete
  commented-out code. Gate debug tooling behind a flag, off by default.
- Write a probe script to measure data or behaviour rather than guess;
  delete it before the commit that uses its findings; keep the findings
  themselves in durable comments or decision records.
- Grep for a construct a comment records as not working before reusing
  it; read every hit as a suspected instance of the same defect.
- Run a new constraint — a tightened bound, a narrowed exemption — against
  the existing corpus before it merges.
- When deleting, truncating or purging data (notably a GDPR erasure, see
  section 6), act only on what the operation can prove is its target: an
  exact customer ID, not a name match or a path guess. Find nothing, and
  raise, where that proof is unavailable.
- Confirm a migration, import or bulk-edit script is correct before
  acting on its output in bulk; cross-check an independent source before
  overwriting stored data that looks wrong.
- Adopt the project's static type checker at its strictest setting and
  keep it clean (MUST); annotate every public function's parameters and
  return type (MUST). Adopt a linter and a formatter and keep both clean
  (MUST). Run all three before every commit and in CI; each must print
  nothing.
- Finish a task when the requested behaviour works through the entry
  point its caller reaches, and the checks that prove it pass. Report a
  check that could not run as not run, never as a pass. Report a problem
  found outside the task as its own task rather than folding it in.

### 3.3 Web layer (Flask / Jinja / HTMX)

- Read the port from an environment variable; never hardcode it. Keep
  initialisation short.
- Run one-off tasks (migrations, data fixes) with the application's own
  code, config and dependencies; commit admin scripts to the repository
  rather than running ad-hoc shell commands; prefer idempotent scripts;
  never run one against the live database without a tested rollback plan.
- Keep handlers thin: decode the request, call the pricing engine or a
  service function, render the response. Never put business logic in a
  handler. Validate all incoming request data before processing it.
- Parse a typed query parameter explicitly, distinguishing absent
  (default), present-and-valid (use it) and present-but-invalid (raise a
  400) — never let a parsing helper silently turn a bad value into the
  default.
- Read header names case-insensitively. Avoid the `X-` prefix on a custom
  header; use an application-specific prefix instead.
- Never let a GET or HTMX `hx-get` request change state. Make every PUT
  and DELETE (including an `hx-delete`) idempotent.
- Represent dates and times as ISO 8601, currency codes as ISO 4217, and
  country or tax-jurisdiction codes as ISO 3166-1 alpha-2, wherever the
  application stores, computes or displays them.
- Use a consistent error shape across every route and HTMX fragment. Never
  expose a stack trace or an internal path to the browser; return a
  generic message and log the detail server-side. Use proper 4xx/5xx
  status codes, never 200, for an error. Set an explicit `Content-Type`
  on every response.
- Enforce authentication on every route (MUST); this application declares
  no public endpoint. Apply the auth check before any business logic
  runs. Never expose a write path without the authenticated
  administrator's session.
- Not applicable, since nothing here reaches the network: HTTPS/TLS
  enforcement, HSTS and other reverse-proxy security headers, CORS,
  multi-instance process lifecycle (graceful shutdown, SIGKILL recovery).

### 3.4 Data model (SQLite)

- Pick one naming convention for tables, columns, keys and indexes, and
  record it here once chosen — open for the project to decide.
- Give every table a primary key; prefer a surrogate key. Store each fact
  in one place; duplicate only when measured read performance requires
  it, with the rationale documented. Never pack several values into one
  field (e.g. a composite discount-rule string) — use a related record.
- Enforce every reference (customer → invoice, invoice → product, invoice
  → tax jurisdiction) with SQLite's own foreign-key constraint, or an
  explicit check that every reference resolves. Decide what deleting the
  target of each reference does — see section 6 for the customer case.
  Document the maximum depth and cycle-prevention strategy for any
  self-referencing relationship, such as a stacked or nested discount
  rule, if one exists.
- Make every schema change through a versioned migration (MUST); never
  edit the schema by hand. Prefer additive changes, compatible with old
  writers. Give a destructive change (drop or rename a column) a plan:
  add the new column, migrate the data, drop the old one, with both up
  and down steps (MUST). Say so, and get approval, where a down step
  cannot restore the data. Test a migration against realistic data before
  applying it.
- Use the most specific SQLite type for each field: a date/time type, not
  a string, for dates. Store timestamps in UTC; convert to local time only
  at the presentation layer. Store every monetary value — a price, a
  discount, a tax amount, an invoice total — as an integer in minor units
  or an exact decimal type; never as a float (MUST). Document a maximum
  length for every text field: customer name, email, postal address,
  product description.
- Open one connection per request or worker thread; never a long-lived
  global handle. Wrap a multi-step write (e.g. assembling an invoice from
  its line items) in a transaction; commit only once every write
  succeeds; keep the transaction short.
- Bound every interactive query with a limit or pagination (e.g. a
  customer or invoice listing); a filter alone is not a bound. Select only
  the columns a code path uses. Fetch related rows for a set in one query
  or batch, never one query per row in a loop.
- Use a hard delete or an anonymizing update for a customer erasure (see
  section 6), never a soft delete that still returns the row to ordinary
  queries. Keep an append-only audit log table instead of a soft-delete
  flag.
- Reset state between test runs — truncate tables or roll back a
  transaction wrapping each test. Never substitute a different database
  engine in tests; SQLite's own behaviour is part of what is tested.
  Never run a schema migration against a production database inside a
  test suite.

## 4. Quality — testing

Classify a test by the boundary it crosses: unit (none), integration
(process/component — e.g. a real temporary SQLite file), system (the
whole application against its requirements), regression (reusing
existing tests against a fixed defect), exploratory (unscripted).

- Double only what a unit test would cross a boundary to reach: file I/O,
  the system clock (discount and tax-jurisdiction rules can be
  date-effective), randomness. Keep deterministic in-process
  collaborators real.
- Add a regression test for every fixed defect.
- Cover every happy path the pricing, discount, tax and invoicing rules
  define, plus negative inputs and edge cases (SHOULD), plus each
  dependency's faults (an unavailable database file, a malformed row).
- Meet the project's coverage threshold for new code before merging;
  never let coverage regress between releases. Run every unit test from
  CI with no human step. Name a test so its name alone states the unit,
  the input and the expected outcome (SHOULD).
- Keep pricing, discount and tax logic in pure functions; push SQLite
  access to thin adapters at the edges (SHOULD). Inject dependencies
  rather than construct them in the code under test. Split a function
  that needs more than two mocks to test.
- Test behaviour, not implementation details. Set or clear every
  environment variable a test depends on, in that test. Treat a test that
  passes or fails by run order as an isolation bug. Wait on a condition
  with a deadline, never a fixed sleep. Never enumerate, signal or
  terminate a process the test did not start. Never mutate host state
  outside the working directory. Investigate a failing test's own logic
  before skipping or suppressing it.
- Allocate a per-test temporary database file or path from a fixture or a
  module-level counter, never from state a test class inherits.
- Assert after every test that no thread, subprocess or server the suite
  started survives it; join with a timeout, never a sleep.
- Exercise every call site of a changed shared pricing, discount or tax
  path, not only the reported case; keep the list of consumers beside the
  shared path.

## 5. Security

- Validate all external input (invoice, customer and discount-rule forms)
  at the boundary, with a schema validator, using an allowlist. Reject
  invalid input with a clear error; never silently coerce or strip
  fields.
- Encode dynamic data for its rendering context at the point of output.
  Rely on Jinja's auto-escaping; never insert user-supplied data through
  a raw-HTML path (`|safe`, `Markup`) that bypasses it.
- Use parameterized SQLite queries for all database access; never
  concatenate user input into a query string.
- Hash the administrator's password with bcrypt, scrypt or Argon2 — never
  MD5, SHA-1 or plain SHA-256. Require a minimum length and reject
  known-breached passwords; impose no composition rules. Use
  constant-time comparison for secrets and tokens. Lock the account or
  throttle after repeated failed sign-in attempts.
- Generate the session ID with a cryptographic random generator;
  regenerate it after login. Set `HttpOnly`, `Secure` and
  `SameSite=Strict` on the session cookie. Expire the session after an
  idle period. Invalidate it on logout; do not rely on cookie expiry
  alone.
- Give every state-changing request (every HTMX `POST`/`PUT`/`PATCH`/
  `DELETE`) a CSRF defence (MUST), since the administrator's session is
  authenticated by an ambient cookie. Use the framework's built-in CSRF
  middleware; prefer the synchroniser token pattern. Validate the token
  on every state-changing request, never on GET. Never change state on a
  GET request.
- Never hardcode a secret, API key or credential in source. Keep local
  secret files out of version control. Rotate a secret immediately if it
  is ever committed.
- Never expose a stack trace, an internal path or a database error to the
  administrator's browser; log the full detail server-side. Answer a
  failed sign-in the same way regardless of whether the account exists:
  "invalid credentials", never "user not found".
- Never log a secret, token or password, and never log a customer's name,
  email or postal address (see section 6) — log an opaque ID instead.
  Sanitize any user-supplied data that reaches a log. Log authentication
  and authorization failures at WARN, with an opaque user ID, never a
  submitted username. Keep the client IP only in an access-restricted
  security log, purged at the end of its retention period.
- Never deserialize untrusted data with a format that can instantiate
  arbitrary types; use a data-only format (JSON) for any HTMX partial
  that carries structured data. Pin dependency versions and verify
  lockfile checksums; never trust an upstream registry blindly.
- Never read, print or `cat` a file that may hold secrets (`.env`,
  `credentials.json`, `*.pem`, `*.key`). Never echo or log an environment
  variable's value; check its presence by name only. Warn before
  committing a file that commonly holds secrets. Flag any secret exposed
  in a session immediately, name it, and recommend rotation.
- Not applicable, since nothing here reaches the network: HTTPS/HSTS/TLS
  enforcement, reverse-proxy security headers, CORS, SSRF defences. Not
  applicable, since the application has no upload feature: file-upload
  validation.

## 6. Privacy and data governance (GDPR)

- Classify a customer's name, email and postal address as Confidential
  personal data. Classify an invoice (which carries that PII alongside
  pricing and tax figures) as Confidential. Classify the product catalog,
  discount rules and tax-jurisdiction tables as Internal.
- Match access to classification: only the signed-in administrator may
  read or write Confidential data; there is no lower-privileged role to
  restrict it from.
- Encrypt PII at rest (MUST). There is no network transit to secure here.
- Minimize PII collection: store only the name, email and postal address
  the invoicing relationship needs.
- Never put a customer's name, email or postal address in an application
  log, error message or stack trace (MUST NOT); use an opaque customer ID
  there instead.
- Provide an erasure path (GDPR Art. 17) that anonymizes or removes a
  customer's name, email and postal address from the live customer record
  on request.
- Preserve the name and address already billed on a previously issued
  invoice exactly as issued (GDPR Art. 17(3)(b) permits retaining what a
  legal — here, tax and bookkeeping — obligation requires): erase or
  anonymize the customer record, never retroactively edit an issued
  invoice's billing details. Never delete an issued invoice as a side
  effect of an erasure request; clear or anonymize the customer reference
  on it instead of deleting the row.
- Provide an access/export path (GDPR Art. 15) that produces a complete,
  human-readable copy of a customer's stored personal data and the
  invoices billed to them, on request.
- Record every erasure and export request in an append-only audit trail:
  who requested it, when, and what action was taken — never the PII
  values themselves, so that erasing the PII leaves no copy in the trail.
  Log every other change to Confidential data (a customer record, an
  invoice, a price-setting discount rule) the same way: who changed what,
  when, and the previous value, with PII excluded. Keep this trail in its
  own store, separate from application logs, access-restricted to the
  administrator.
- Define a retention period for customer and invoice data that satisfies
  the bookkeeping and tax-retention law of the applicable EU member
  state, and purge data automatically once it lapses; the exact period is
  open for the project to decide, pending confirmation of the applicable
  jurisdiction. Apply the same retention and purge discipline to the
  audit trail.
- Use synthetic customer data in tests and local development fixtures;
  never real customer PII.
- Designate the administrator as the owner of every data domain
  (customers, invoices, products, discount rules, tax jurisdictions)
  until the project names otherwise.

## 7. Review process

Review in this order, most critical first, weighing each finding
separately: **security**, **correctness**, **clarity**, **conventions**.
Label each finding a demonstrated defect, a policy deviation, or a
suggestion; block a merge only on the first two.

**MUST checklist**

- [ ] No credential, token or sensitive value appears in a committed file
- [ ] Every failure path is handled; no silent catch, no swallowed
      exception
- [ ] Every new dependency carries a licence the project's policy allows
- [ ] Significant logic and architectural decisions are documented
- [ ] Existing documentation matches the code after the change
- [ ] Every changed section was re-read whole, not only the changed line
- [ ] Every claim changed text makes about itself (a count, "all") was
      checked by counting with a tool
- [ ] Input from outside the process is validated as untrusted before it
      is destructured, indexed or used as a key
- [ ] A refactor preserves behaviour on every path — each case, direction
      and mode, including null handling, sort order and boundary values

**SHOULD checklist**

- [ ] Each non-trivial function has a unit test per relevant variant
- [ ] Coverage does not fall
- [ ] Lint errors and warnings do not rise
- [ ] Each third-party dependency is necessary, understood and maintained
- [ ] No new abstraction without two call sites, and no new dependency
      without a documented reason

- Produce a plan before implementing a feature or a non-trivial change:
  the files touched, the signatures or outline, the edge cases, the
  assumptions. Never write implementation code before the plan is
  approved. Skip the plan for one-line fixes, typos and fully-specified
  requests.
- Label a finding unverified until it is demonstrated. Reproduce a defect
  by running the path before reporting it; read a passing test that
  contradicts the reproduction before blaming the code.
- Explain a deviation from a SHOULD rule in the pull request. Land a
  deviation from a MUST or MUST NOT rule only with a designated
  approver's sign-off and its reason recorded in the pull request. Never
  waive a MUST rule without that sign-off.

## 8. Session protocol

- At the start of a session, inspect the working tree and index, and read
  this file before making any change.
- While working, follow sections 2 through 7 for every change.
- Before ending a session, read the MUST and SHOULD checklists in section
  7 and execute each item in sequence, in full — do not summarize or skip
  any of them.

## 9. Governance

- **Who approves a change?** Open for the project to decide.
- **How is work tracked?** Open for the project to decide.
- **What is a release?** Open for the project to decide.
