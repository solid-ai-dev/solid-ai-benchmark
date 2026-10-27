# tariff

A pricing and invoicing web application for Imbra Ltd: a product catalog,
discount rules of several kinds, tax jurisdictions, customers, and invoices
assembled from them.

Imbra Ltd. Stack: Python 3.12, Flask 3, Jinja, HTMX, SQLite. Tooling: uv,
ruff, mypy (strict), pytest. Runs locally only; there is no deployment
target and nothing in the system reaches the network.

- Model: inline

Precedence when rules conflict: GDPR obligations (section 3.10) override
every other rule in this file; this file overrides personal preference;
`README.md` is the single source of truth for project structure. This file
carries every rule the project has adopted, inline — nothing here is a
pointer to an external document.

A sibling `AGENTS.md` carries the same rules for any non-Claude agent.
Update `CLAUDE.md`, `AGENTS.md` and `README.md` together whenever a change
touches architecture, stack, structure, setup, or the conventions below;
never let `AGENTS.md` and `CLAUDE.md` disagree.

## Rule language

A plain imperative ("Use X", "Never Y") means MUST or MUST NOT. Where
strength matters, the keyword is explicit:

| Word | Meaning |
| --- | --- |
| MUST | Absolute requirement; a deviation needs an approver's sign-off |
| MUST NOT | Absolute prohibition; a deviation needs an approver's sign-off |
| SHOULD | Recommended; a deviation needs a justification |
| SHOULD NOT | Not recommended; may be ignored with a justification |
| MAY | Optional; the developer decides |

## 1. Project

### 1.1 Overview

See the precedence and stack summary above. Two actors reach this system:
the administrator, signed in through the browser, and a second program
that imports the pricing engine directly as a Python library, with the web
application absent. Customers are data subjects under the EU GDPR: their
name, email and postal address are stored and printed on the invoices
billed to them (see section 3.10).

### 1.2 Project structure

See `README.md` for the full directory layout; this file does not
duplicate it.

- Keep the pricing engine (catalog, discount rules, tax jurisdictions,
  invoice assembly, invoice export) as a standalone Python package that
  imports nothing from Flask, Jinja, HTMX or any HTTP/web-framework code
  (MUST); another program must be able to import it with the web
  application absent.
- Keep the Flask web app a thin caller of that library: a route decodes a
  request, calls the library, renders a template; never duplicate pricing,
  discount, tax or invoice-assembly logic in the web layer (MUST).
- Keep invoice export logic (PDF/CSV/etc.) inside the library beside the
  invoice-assembly code it serializes, not in the Flask layer.

### 1.3 Commands

```bash
uv sync                    # install dependencies
uv run flask run           # run the app locally
uv run ruff check .        # lint
uv run ruff format .       # format
uv run mypy --strict .     # type-check
uv run pytest              # run tests
uv run pytest --cov        # run tests with coverage
```

## 2. Code conventions

### 2.1 Git

- Commit under one full name and one consistent email; never change
  identity mid-project.
- Work on a branch; never commit directly to `main`.
- Never commit build output, the virtual environment, `__pycache__`, or
  secrets.
- Keep a `.gitignore` covering `.venv`, `__pycache__`, build output,
  `.env*`, editor state, OS files and coverage output (MUST).
- Commit `uv.lock` (MUST).
- Treat the repository as public: no secret, credential or sensitive value
  in source or history.
- Inspect the working tree and the index before starting a task.
- Never discard, reset, stash or overwrite a change the task did not make
  (MUST NOT); never clear the tree for a clean test baseline without
  asking.
- Stage only the changes the task made; read the staged diff before
  committing.
- Stop and ask when a task change and a prior change share a hunk; report
  a pre-existing change that blocks the task rather than removing it.
- Keep a pull request to one concern (SHOULD); test locally before
  committing.
- Review every diff against the base before merging, in order: security,
  correctness, clarity, conventions. Merge only once review passes and CI
  is green.
- Read the CI run for the push before calling a change good; never merge
  while a check is failing, cancelled, or not yet registered.
- Never force-push, including `--force-with-lease` (MUST NOT); update a
  branch by merging the base into it.

#### Off-limits paths

These MUST NOT change without explicit approval. Propose a change inside
one of them with a rollback strategy and the tests that would catch a
regression, before making it:

- Authentication and session code (sign-in, password hashing, session
  cookie configuration)
- Database migrations
- `.env*` and any secrets file
- CI/CD workflow files

Name any off-limits path touched at the top of the change's summary,
whether proposed or already approved.

### 2.2 Python

- Name a function with a verb, a class or module with a noun, a boolean
  with `is`, `has` or `can`.
- Rename a name that needs a comment to explain it; use the same name for
  the same concept in every module (e.g. always `tax_jurisdiction`, never
  mixed with `tax_zone`).
- Name a public enum member or result discriminator for the capability it
  offers, never the library behind it.
- Keep cognitive complexity at or under 15 per function; enforce it with
  `ruff`'s `C90` rules and `max-complexity = 15` in `pyproject.toml`.
- Nest at most three levels; use guard clauses and early returns.
- Replace a boolean flag parameter that selects behaviour with an enum or
  two named functions.
- Name every magic number and magic string as a constant; keep a constant
  beside the function that uses it.
- Encode every committed text file in UTF-8 with LF line endings; keep
  identifiers ASCII.
- Prefer code that needs no comment; comment only non-obvious intent;
  never cite a ticket or PR number in a comment or docstring.
- Commit no debug output (`print()`), no commented-out code, and no
  hardcoded breakpoint; gate any debug tooling behind an environment
  variable, off by default.
- Delete a probe script before the commit that uses its findings; keep the
  findings in a comment, decision record or doc, never in the probe.
- Type-annotate every function signature; keep `mypy --strict .` and
  `ruff check .` clean as a merge gate (MUST).

## 3. Quality

### 3.1 Architecture and dependencies

- Keep one authoritative representation of each piece of knowledge (DRY);
  extract shared logic only where substantial logic repeats.
- Choose the simplest solution a stated requirement justifies (KISS);
  build only what is needed now (YAGNI).
- Compute every derived count, total, tax amount or discount from the
  data; never hardcode one.
- Remove unused modules, assets and data files promptly.
- Snapshot pricing, discount and tax data onto an invoice at creation time;
  never recompute a historical invoice from current catalog, discount or
  tax-jurisdiction state (a later price or rate change must never alter an
  already-issued invoice).
- Keep the module graph acyclic; break a cycle with a third module, never
  a divergent local copy.
- Keep coupling shallow: a change inside one module must not require
  changes in unrelated modules.
- Never let the pricing-engine library write to standard output or error,
  or configure logging beyond its own logger (MUST); make its logger
  injectable, falling back to its module logger, and verify the silence in
  a fresh process.
- Enforce the library/web-app import boundary with a test
  (e.g. `test_library_has_no_web_imports`) asserting that no module under
  the pricing-engine package imports `flask`, `jinja2`, or anything from
  the web layer.

### 3.2 Errors

- Validate input at boundaries (the HTTP layer, the library's public
  functions) and fail at once on invalid state.
- Read a value from its source-of-truth field and raise when it is
  missing; never fall back to a value derived from a slug, name or hash.
- Never break a public catch contract: a raise callers catch by a built-in
  type keeps that type.
- Add an error type only where a caller could act differently.

### 3.3 Deprecation

- Deprecate a public symbol in the pricing-engine library, naming its
  replacement, before a later change removes it; the second program
  consumes this library's API directly and has no version negotiation to
  fall back on.
- Deprecate every part of one call site together; never alias the outer
  name alone while silently changing its keyword arguments.

### 3.4 Destructive operations

- Delete, truncate or overwrite only what the operation can prove it
  should affect: a specific customer ID matched exactly, never a loose
  filter.
- Validate the input before any destructive operation: reject an empty or
  malformed ID.
- Apply this with particular care to GDPR erasure (section 3.10): verify
  the customer record matched is the one requested before deleting or
  anonymizing it.

### 3.5 Completion

- Finish a task when the requested behaviour works through the entry point
  its user or caller reaches (the browser UI or the library's public API),
  and the checks that prove it pass.
- Report a check that could not run as not run, never as a pass.
- Add an abstraction or process step only when a stated requirement, a
  demonstrated defect, or a material risk justifies it.
- Report a problem found outside the task's scope rather than fixing it in
  the same change (SHOULD).

### 3.6 Testing

- Classify a test by the boundary it crosses: unit (none), integration
  (the SQLite database), system (the whole app against its requirements),
  regression (reusing existing tests), exploratory (unscripted).
- Double only what crosses a boundary: the database, time, randomness;
  keep deterministic in-process collaborators real.
- Add a regression test for every fixed defect (SHOULD).
- Cover every happy path the pricing, discount, tax and invoicing rules
  define, plus negative inputs and edge cases (SHOULD).
- Keep pricing, discount and tax logic in pure functions; push the SQLite
  access to thin adapters at the edges; inject the database session rather
  than construct it inside the code under test.
- Set or clear every environment variable a test depends on inside that
  test; never rely on ambient process state.
- Treat a test that passes or fails by run order as an isolation bug;
  investigate a failing test before skipping or suppressing it.
- Reset database state between test runs (a transaction rolled back per
  test, or a fresh SQLite file); never substitute a different database
  engine in tests.
- Assert at least one case against a fixed vector from the ISO 4217 minor-
  unit table for currency rounding; never take a round trip through your
  own rounding code as proof it is correct.
- Give every fact stored in two places (a documented field's maximum
  length and the constant enforcing it, for instance) a test that fails
  when the two diverge.
- Verify a change to rendered HTML or an HTMX fragment against the
  rendered output, not the template source.
- Never let coverage regress between commits; run every test from CI with
  no human step.

### 3.7 HTTP and web conventions

- Keep Flask route handlers thin: decode the request, call the pricing
  library or a service function, render the response; never put pricing,
  discount, tax or invoice logic in a handler.
- Parse a typed query parameter explicitly so absent (use the default),
  present-and-valid (use it), and present-but-invalid (raise 400) are
  distinct; never let a parsing helper silently turn an invalid value into
  a default.
- Never let a `GET` or `HEAD` request change state; make every HTMX
  `PUT`/`DELETE`-driven action idempotent.
- Represent every date and time as ISO 8601 and every currency amount with
  its ISO 4217 code; store and compute money as an integer in minor units
  or as a decimal type, never as a float.
- Use a consistent error response shape across the app; never return a
  stack trace, an internal path, or a raw database error to the browser;
  log the full detail server-side and show the administrator a generic
  message.
- Enforce authentication on every route (MUST); this application declares
  no public endpoint. Apply authentication before any business logic
  runs.
- Run a one-off task (a migration, a data fix, a REPL session) as a script
  committed to the repository, using the application's own code and
  config, never as an ad-hoc shell command.

### 3.8 Database conventions

- Make every schema change through a migration committed to source control
  (MUST); never edit the SQLite file by hand. One migration per logical
  change, with both an `up` and a `down` step; say in the migration and
  get approval when the `down` step would lose data.
- Never modify a migration that is already merged.
- Parameterize every query that takes a value; never build a query by
  string interpolation (see also section 3.9).
- Bound every query an interactive request runs with a limit or
  pagination; select only the columns the code uses; fetch an invoice's
  related line items in one query, never one query per row.
- Index every foreign key column (`customer_id` on invoices, `product_id`
  on line items, and similarly for discount and tax-jurisdiction
  references); drop an index once it is unused.
- Wrap a multi-step write (assembling an invoice across its tables) in a
  transaction; keep transactions short; never call out to another process
  inside one.
- Inject the database session as a dependency; no global database handle.
- Use hard delete or anonymization for a GDPR erasure request, never a
  soft-delete flag alone (see section 3.10); where a soft delete is used
  elsewhere for audit history, filter deleted rows out of every query by
  default.
- Never run a schema migration against production data inside a test
  suite.

### 3.9 Security

- Validate all external input (every form field, query parameter and HTMX
  payload) at the boundary with a schema-validation library; use an
  allowlist, not a blocklist; reject invalid input with a clear error
  rather than silently coercing it.
- Never bypass Jinja's autoescaping with a raw-HTML path for user-supplied
  data (product names, customer names and addresses, discount codes
  included).
- Use parameterized queries for all database access; never concatenate
  user input into SQL.
- Hash the administrator's password with bcrypt, scrypt or Argon2; never
  MD5, SHA-1 or plain SHA-256. Require a minimum password length and
  reject known-breached passwords; impose no composition rules.
- Use constant-time comparison for secrets and tokens; lock the account or
  throttle after repeated failed sign-in attempts.
- Generate the session ID with a cryptographic random generator and
  regenerate it after login (session fixation).
- Set `HttpOnly`, `Secure` and `SameSite=Strict` on the session cookie;
  expire the session after 30 minutes idle; invalidate it on logout.
- Give every state-changing request (every `POST`, `PUT`, `PATCH`,
  `DELETE` the admin UI issues, HTMX included) a CSRF defence, since the
  session is carried by an ambient cookie; use Flask's own CSRF protection
  rather than hand-rolled tokens; never change state on a `GET`.
- Never hardcode a secret, API key or credential in source; keep `.env`
  out of version control; rotate a secret immediately if it is
  accidentally committed, and warn the user before committing a file that
  commonly holds one.
- Set `X-Content-Type-Options: nosniff` and `X-Frame-Options: DENY` (or an
  equivalent CSP `frame-ancestors`) on every response.
- Never expose a stack trace, internal path or database error to the
  administrator's browser; return a generic message and log the detail
  server-side.
- Never log a secret, token, password, or PII (name, email, address); log
  authentication failures and access denials at WARN with an opaque user
  ID, never a submitted username.
- As the coding agent: never read, print or `cat` a file that may hold a
  secret (`.env`, `*.pem`, `*.key`, `credentials.json`); never echo or log
  an environment variable's value; verify a secret's presence by an
  existence check, never by printing it.

### 3.10 Data modeling and GDPR

- Use one naming convention for every table, field, key and index
  (`snake_case`); give every table a primary key, surrogate for internal
  use.
- Store each fact once; document the rationale for any intentional
  denormalization.
- Never pack several values into one field (a comma-joined list of line
  items, for instance); use a related record instead.
- Enforce every reference (customer, product, discount rule, tax
  jurisdiction) with a foreign-key constraint; decide and document what
  happens on delete for each: clear the reference, refuse the delete, or
  (for an invoice, which must keep its billed values regardless of later
  catalog changes) rely on the snapshot in section 3.1 rather than a live
  reference.
- Run every schema change through a versioned migration; keep an additive
  change compatible with old data (a new field optional or defaulted);
  give a destructive change an add-migrate-drop plan.
- Store timestamps in UTC; store monetary values as an integer in minor
  units or a decimal type, never a float; document a maximum length for
  every text field (customer name, email, postal address, product name,
  discount code).
- Classify every field: customer name, email and postal address are
  Confidential (PII); invoice amounts and line items are Confidential;
  product catalog, discount rules and tax-jurisdiction data are Internal.
  Document this in the schema or a data dictionary, and restrict access to
  the Confidential tier to the signed-in administrator.
- Minimize PII collection: store only what invoicing needs (name, email,
  postal address); never put PII in an application log, error message or
  stack trace.
- Mask or use synthetic data for PII in any non-production environment
  (development fixtures, test data).
- Provide a mechanism to erase a customer's PII on request (GDPR Art. 17):
  hard-delete or anonymize it, never a soft-delete flag alone. Where a
  statutory retention duty (e.g. tax-record retention) requires keeping
  the invoice itself, anonymize the customer's name, email and address on
  the retained invoice rather than deleting the invoice, and document the
  retention period relied on.
- Provide a mechanism to export a copy of everything held about a customer
  on request (GDPR Art. 15/20), in a structured, commonly used format.
- Define and document a retention period for each data category
  (customers, invoices, backups); implement automated purging rather than
  a manual process; apply the same retention to backups, and never retain
  a backup indefinitely.
- Log every change to Confidential data: who (the administrator's opaque
  ID), when, what changed, and the previous value — except a credential's
  or a PII field's own value, which the audit entry must record as
  "changed" without storing either value, so an erasure leaves no copy in
  the append-only trail.
- Data ownership (who owns the customers, invoices and catalog domains) is
  not settled by the project; assign one before this matters operationally.

### 3.11 Accessibility and UX

- Make every interactive element reachable and operable by keyboard; never
  put a click handler on a non-focusable element — use a native button or
  link instead.
- Style focus with `:focus-visible` and keep a visible focus indicator on
  every focusable element, including links.
- Never convey meaning by colour alone; keep text contrast at 4.5:1 (3:1
  for large text); give every image descriptive `alt` text (`alt=""` when
  decorative).
- Use semantic HTML with a correct heading hierarchy.
- Scan rendered pages with an automated accessibility checker in CI, and
  merge only on zero violations.
- Before shipping a new interactive component: tab through it without a
  mouse, walk it with one screen reader, and zoom to 200% to check nothing
  clips or scrolls horizontally.
- Support the last two versions of Chrome, Firefox, Safari and Edge.

## 4. Review process

Review in this order, most critical first:

1. **Security**: anything exploitable, any credential or licence problem
2. **Correctness**: wrong results, unhandled failures, race conditions
3. **Clarity**: obscure names, deep nesting, high cognitive complexity,
   boolean flag parameters
4. **Conventions**: deviations from the rules in section 2 and 3

Label each finding a demonstrated defect, a policy deviation, or a
suggestion. Block a merge only on a defect or a policy deviation; leave a
suggestion to the author.

### End-of-session checklist

Read every item below and execute it in sequence before ending a session;
never summarize or skip one.

**MUST**

- [ ] No credential, token or sensitive value appears in a committed file
- [ ] Every failure path is handled; no silent catch, no swallowed
      exception
- [ ] Every new dependency carries a licence the project's policy allows
- [ ] Significant logic and architectural decisions are documented
- [ ] Existing documentation matches the code after the change
- [ ] Every changed section was re-read whole, not only the changed line
- [ ] Every claim changed text makes about itself, such as a count or
      "all", was checked by counting with a tool
- [ ] Input from outside the process (a form field, a query parameter) is
      validated as untrusted before it is destructured, indexed, or used
      as a key
- [ ] A refactor preserves behaviour on every path: each case, direction
      and mode, including null handling, sort order and boundary values

**SHOULD**

- [ ] Each non-trivial function has a unit test per relevant variant
- [ ] Coverage does not fall
- [ ] Lint errors and warnings do not rise
- [ ] Each third-party dependency is necessary, understood and maintained
- [ ] No new abstraction without two call sites, and no new dependency
      without a documented reason

### CI signals

- Read the log of a red check before calling the pull request green or
  red.
- Separate an infrastructure failure (the check could not run) from a diff
  failure (it ran and found something), and say which in the merge
  decision.
- Never retry until green without saying so; never bypass a failing check
  by skipping hooks or an admin merge without the approver's explicit
  acceptance of the risk.

### Picking up an issue

- Re-read the target for existing coverage before writing anything; verify
  everything the issue cites as existing against the current tree.
- Check open pull requests and accepted decisions since the issue's filing
  date for work that already closes or moves it.
- Resolve a cited version or classification against its actual source
  rather than trusting the issue's description of it.

### Planning

- Produce a plan before implementing a feature or a non-trivial change:
  the files, the signatures or outline, the edge cases, the assumptions.
- Never write implementation code until the plan is approved (MUST NOT);
  skip the plan only for one-line fixes, typos, and changes the requester
  has specified in full.
- Stay inside the approved plan; when a constraint invalidates it, stop
  and re-surface the options.

### Verifying a finding

Label a finding unverified until it is demonstrated.

- From reading: reproduce the defect by running the path; read a passing
  test that contradicts the reproduction before blaming the code.
- From a measurement: confirm the tool measured the rule's actual unit and
  the claimed scope (not a diff or a sample); check one flagged item and
  one zero result by hand.
- From an extraction: check an element reported absent against the raw
  artifact; scope the claim to what was inspected ("not verifiable from
  the extract", never "missing").
- From a probe: confirm it ran under the conditions the finding is about
  (user, credential, environment); scope the claim to what it actually
  tested.
- From an agent: check its finding against the file, commit or document
  that settles it before acting on it or repeating it; count a finding
  several agents agree on as one finding.

### Deviations

- Explain a deviation from a SHOULD rule in the pull request.
- Land a deviation from a MUST or MUST NOT rule only with a designated
  approver's sign-off and its reason recorded in the pull request; never
  waive one yourself.

### Cold-reader writing

Apply this to every ticket, pull request and defect record, since the
record outlives the session:

- State the symptom before the mechanism; expand a term taken from the
  code at its first use, or avoid it.
- Show a real example rather than describe one; keep to one idea per
  sentence.

### Governance questions

- **Who approves a change?** Not stated by the project; open for the
  project to decide. Until an approver is named, treat every MUST/MUST NOT
  deviation above as blocked.
- **How is work tracked?** Not stated; open for the project to decide.
- **What is a release?** Not applicable in the usual sense: the project
  runs locally with no deployment target. "Shipping" a change means
  merging it to `main` with a green CI run; there is no deployment step.

## 5. Session protocol

- **Start**: read this file and `README.md`; run `git status` and inspect
  the working tree and index before making any change; never discard or
  overwrite a change the task did not make.
- **Proceed**: follow the planning rule in section 4 for anything beyond a
  one-line fix; stay inside the approved plan; propose any off-limits-path
  change (section 2.1) before making it.
- **Disagreement between a document and the system**: never act on the
  document alone when the observed system state is defensible; find the
  rule that governs both (this file, or GDPR for section 3.10) and fix
  whichever one that rule does not support.
- **End**: read the end-of-session checklist in section 4 and execute each
  item in sequence, without summarizing or skipping any; run
  `uv run ruff check .`, `uv run mypy --strict .` and `uv run pytest`;
  confirm no off-limits path changed without recorded approval; update
  `README.md`, `AGENTS.md` and this file together if the change touched
  structure, stack, or any convention above; commit only the task's
  changes, following section 2.1.
