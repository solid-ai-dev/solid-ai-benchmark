# tariff

Imbra Ltd's pricing and invoicing application: a product catalog,
discount rules of several kinds, tax jurisdictions, customers, and
invoices assembled from them. Runs locally only; no deployment target,
no live URL.

Quality conventions are defined in `docs/solid-ai-templates/templates/`
(a vendored copy at a pinned revision, not a submodule). Key references:

- `docs/solid-ai-templates/templates/core/agents.md` — governs this
  file's own structure
- `docs/solid-ai-templates/templates/core/quality.md`
- `docs/solid-ai-templates/templates/core/git.md`
- `docs/solid-ai-templates/templates/core/docs.md`
- `docs/solid-ai-templates/templates/core/testing.md`
- `docs/solid-ai-templates/templates/core/review.md`
- `docs/solid-ai-templates/templates/backend/http.md`
- `docs/solid-ai-templates/templates/backend/database.md`
- `docs/solid-ai-templates/templates/security/security.md`
- `docs/solid-ai-templates/templates/frontend/ux.md`
- `docs/solid-ai-templates/templates/data/data-modeling.md`
- `docs/solid-ai-templates/templates/data/data-governance.md`

Adoption boundary (MUST): the rules inlined or referenced below are the
adopted set. They stay in force until this file is edited to change them.
Reading a newer version of a referenced template, or moving the vendored
pin, adopts nothing by itself — only an edit to this file changes what is
adopted.

Not adopted, and intentionally absent below: `backend/api.md` and
`backend/auth.md`. The pricing engine is a library imported in-process by
two callers (the web application and another program); it is never
exposed as a network API, so REST/gRPC/GraphQL contract, versioning and
token/RBAC rules do not apply. Do not add them without first recording
why a network-facing contract has become necessary.

Before the first commit that adds `docs/solid-ai-templates/`, exclude
that directory from every tool that walks the tree: ruff, mypy, any
secret scanner, and any spell or link checker (MUST).

## 1. Project

### 1.1 Identity

- Owner: Imbra Ltd
- Stack: Python 3.12, Flask 3, Jinja, HTMX, SQLite
- Tooling: uv, ruff, mypy (strict), pytest
- Hosting: none — runs locally, single process, no deployment target
- Actors: the administrator (one account, browser-based) and another
  program that imports the pricing engine directly, in-process, without
  the web application present
- Model: hybrid

### 1.2 Project structure

Keep the authoritative directory map in `README.md`. Do not duplicate it
here. Placement rules for this project:

- Keep the pricing engine (catalog, discount rules, tax jurisdictions,
  invoice assembly) in its own package, importable with the web
  application absent (MUST)
- Keep Flask routes, Jinja templates and HTMX partials in a separate web
  package that imports the pricing engine; never the reverse (MUST)
- Mirror the source layout in `tests/`
- Keep SQLite migrations in one directory, applied in order, numbered
- Keep `docs/solid-ai-templates/` untouched except for the revision pin

### 1.3 Commands

```bash
uv sync
uv run flask --app tariff run --debug
uv run ruff check .
uv run ruff format --check .
uv run mypy --strict .
uv run pytest
```

### 1.4 Governance

- Who approves a change: open — not settled by the project yet
- How work is tracked: open — not settled by the project yet
- What is a release: open — not settled by the project yet; the
  application has no deployment target, so a release is at most a tagged
  commit, not a deployed artifact

## 2. Code conventions

### 2.1 Git

- Commit under one full name and one consistent email; never change
  identity mid-project
- Work on a branch; never commit directly to `main`
- Never commit build output, dependency directories, secrets, or the
  SQLite database file
- Keep a `.gitignore` covering dependencies, build output, secrets,
  editor state, OS files and coverage output (MUST)
- Commit the `uv.lock` lockfile (MUST)
- Inspect the working tree and index before starting a task; never
  discard, reset, stash or overwrite a change the task did not make
- Stage only the changes the task made; read the staged diff before
  committing
- Keep a pull request to one concern; test locally before committing
- Review the diff against the base before merging, in order: security,
  correctness, clarity, conventions
- Merge only after review passes and CI is green; never force-push,
  including `--force-with-lease`
- Bring a branch up to date by merging the base into it, never by
  rebase-and-force-push
- Read the CI run for the push before calling a change good; never merge
  while a check is failing, cancelled, or not yet registered

**Off-limits paths** (MUST NOT change without explicit approval; propose
first, with rollback and tests that would catch a regression):

- Authentication and session code (administrator sign-in)
- Customer data erasure and export code (GDPR compliance paths)
- SQLite migrations
- `.env*` and secret files
- CI/CD workflow files

Name any off-limits path touched at the top of the change's summary,
whether proposed or already approved; a diff confined to prose in such a
file is ordinary work.

### 2.2 Python

- Run under mypy strict mode; add no untyped `def`, no implicit `Any`,
  and no `# type: ignore` without the specific error code it silences
- Run ruff as both linter and formatter; a generator-produced file must
  pass both without `--fix`
- Encode every committed text file UTF-8 with LF line endings, and keep
  identifiers ASCII:

```bash
pre-commit run check-ascii-identifiers --all-files --verbose
```

Pass condition: inspected count above zero, `non-ASCII identifiers` zero.

- Commit a `.gitattributes` with `* text=auto`, adding `eol=lf` where LF
  must be forced, and `-text` on any path that is genuinely binary or
  must keep CRLF

## 3. Quality

- Keep one authoritative representation of each piece of knowledge
  (e.g., a tax rule, a currency format); the third copy is a bug
- Choose the simplest solution a stated requirement justifies; build only
  what the catalog, discount, tax, customer and invoice features need now
- Record, beside every deferral, the concrete condition that reopens it
- Delete a path once it has no caller or its input is retired

**Naming**

- Name a function with a verb, a class or module with a noun, a boolean
  with `is`/`has`/`can`
- Use the same name for the same concept in every module (e.g., one name
  for "discount rule" throughout catalog, pricing and invoice code)
- Name a public enum member or result discriminator for the capability it
  offers, never the library behind it

**Complexity**

- Keep cognitive complexity at or under 15 per function; nest at most
  three levels, with guard clauses and early returns
- Replace a boolean flag that selects behaviour with an enum or two named
  functions
- Name every magic number and magic string as a constant
- Take a tax, currency or rounding limit from the applicable law or
  specification and name it; never derive it from an observed sample

**Dependencies and module structure**

- Keep the module graph acyclic: the pricing engine never imports the web
  package
- Enforce that boundary mechanically once the import-ban check is wired
  into pre-commit, with the pricing-engine-to-web direction declared as a
  forbidden pair:

```bash
pre-commit run find-import-bans --all-files --verbose
```

- Keep the Flask web application a thin layer over the pricing engine
  library: decode request → call the library → render response; push
  catalog, discount, tax and invoice logic into the library, not into
  route handlers
- Never write to standard output or standard error from the pricing
  engine library, and never configure logging beyond its own logger
  (MUST); make its logger injectable, falling back to its module logger
- Keep constants beside the functions that use them

**Errors**

- Validate input at the boundary (HTTP handlers, the other program's call
  sites) and fail at once on invalid state
- Never break a public catch contract: a raise callers catch by a
  built-in type keeps that type
- Add an error type only where a caller could act differently
- Never let a caller-side filter stand in for a precondition inside the
  pricing engine; assert the precondition there

**Deprecation**

- Deprecate a public symbol in the pricing engine's API, naming its
  replacement, before a later change removes it; the other program and
  the web application are both callers that can be broken by a silent
  removal

**Comments and debug code**

- Prefer code that needs no comment; never cite a ticket or PR number in
  a comment — state the substance instead
- Commit no debug output (`print()`) and no commented-out code; gate
  debug tooling behind a flag, off by default
- Delete a probe script before the commit that uses its findings; keep
  the findings in a comment, decision record or doc, never in the probe

**Destructive operations** (governs GDPR erasure above all)

- Delete, anonymize or overwrite only what the operation can prove it
  owns: match an erasure or export request by customer ID, never by a
  name or email string match
- Validate the input as well: reject an empty or malformed customer
  identifier before acting
- Find nothing, and change nothing, where the proof of ownership is
  unavailable: no guess, no partial match

**Check trust**

- Confirm a migration or data-fix script is correct, on a copy of real
  data, before running it against the live SQLite file
- Cross-check an independent source before overwriting stored customer or
  pricing data with a source that looks wrong

**Completion**

- Finish a task when the requested behaviour works through the entry
  point its user or caller reaches (the browser UI, or the library call
  the other program makes), and the checks that prove it pass
- Report a check that could not run as not run, never as a pass

## 4. Security

- Validate all external input (HTTP form/query data, and any input the
  other program passes into the pricing engine) at the boundary, with a
  schema validator; use an allowlist, never a blocklist
- Encode dynamic data for its rendering context at the point of output in
  Jinja templates; never bypass auto-escaping with a raw-HTML path for
  customer- or admin-supplied text
- Use parameterized queries for every SQLite access; never concatenate
  input into SQL
- Hash the administrator's password with bcrypt, scrypt or Argon2; use
  constant-time comparison for any token; lock out or throttle after
  repeated failed sign-in attempts
- Generate the session ID with a cryptographic random generator;
  regenerate it after login; set `HttpOnly`, `Secure`, `SameSite=Lax`
  cookie flags; expire idle sessions; invalidate on logout
- Give every state-changing request (`POST`/`PUT`/`PATCH`/`DELETE`) a
  CSRF token, since the administrator's session is authenticated by an
  ambient cookie; use the framework's CSRF middleware (e.g. Flask-WTF),
  never a hand-rolled check
- Include the CSRF token explicitly in every HTMX request that mutates
  state (`hx-headers` or a hidden field); HTMX does not add it on its own
- Never change state on a `GET` request
- Never hardcode secrets (session signing key, any admin credential) in
  source; keep them in a local secret file excluded from version control
- Never expose a stack trace, internal path or SQLite error to the
  browser; return a generic error externally and log full detail
  server-side
- Never log secrets, tokens, or personally identifiable information
  (customer name, email, postal address); log authentication and
  authorization failures with an opaque user ID and the client IP, kept
  only in a security log with its own retention
- Pin dependency versions and verify them via `uv.lock`; never trust an
  unpinned upstream package
- Set security headers on every response (`Content-Security-Policy`,
  `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY` or CSP
  `frame-ancestors`, `Referrer-Policy`, `Permissions-Policy`); do not
  expose `Server`/`X-Powered-By` version strings

Not applicable, and do not add without a stated reason:

- Transport security (HTTPS/HSTS/TLS) and CORS — the application serves
  only loopback HTTP to the administrator's local browser; it has no
  deployment target and no second origin to allow
- SSRF defences — the application makes no outbound network requests;
  nothing it does reaches the network
- File-upload rules — there is no file-upload feature

## 5. Data modeling and GDPR compliance

**Modeling** (products, discount rules, tax jurisdictions, customers,
invoices)

- Use one naming convention for every table and column (snake_case)
- Give every table a primary key; store monetary values as integers in
  minor units, never floating point; store timestamps in UTC; document a
  maximum length for every text field
- Enforce every reference (invoice → customer, invoice line → product,
  discount → product or category) with SQLite foreign key constraints
  (`PRAGMA foreign_keys = ON`); decide per reference whether deleting the
  target cascades, clears the reference, or is refused
- Run every schema change through a versioned migration with both up and
  down steps; never hand-edit the schema

**Classification**

- Confidential: customer name, email, postal address; invoice records
  (they carry the same fields)
- Restricted: the administrator's password hash and the session signing
  key
- Internal: product catalog, discount rules, tax jurisdiction
  configuration

**Personal data (customers)**

- Encrypt PII at rest if the deployment environment changes from a single
  trusted local machine; document the decision either way
- Minimize collection: store only name, email and postal address, no more
- Provide an erasure mechanism: hard-delete or anonymize the customer
  record on request; never a soft delete of PII
- Anonymize the customer's name, email and postal address on invoices
  that must be retained for tax or accounting records after an erasure
  request, rather than deleting the invoice itself; keep the invoice's
  financial figures intact
- Provide a data-portability export: on request, produce the customer's
  own stored data (name, email, postal address, and the invoices billed
  to them) in a structured, machine-readable format
- Never put a customer's name, email or address in an application log or
  error message; the audit trail below is a separate store, not a log

**Retention**

- Define, per data category, how long it is kept and when it is purged;
  the statutory retention period for invoices under the applicable tax
  law is open — settle it before relying on a default
- Retain customer PII only until it is no longer needed for an open
  invoice relationship, or until an erasure request, whichever is sooner

**Ownership and audit**

- The administrator is the sole owner of every data domain (customers,
  products, discounts, tax jurisdictions, invoices) while the application
  has one operator
- Log every change to a customer's PII and to the administrator's
  credentials in an append-only audit table, separate from application
  logs: who changed what, when, and that a value changed, never the old
  or new PII value itself
- Erasing a customer's PII must still leave an audit trail entry that the
  erasure happened, without a copy of the erased value

## 6. Database

- Parameterize every SQLite query; never build one by string
  interpolation
- Bound every list view (customers, invoices, products) with a limit or
  pagination; never load a full table for an interactive request
- Fetch related rows (e.g., invoice lines for a set of invoices) in one
  query, never one query per row in a loop
- Wrap a multi-table write (assembling an invoice from catalog, discount
  and tax data) in a transaction; commit only after every write succeeds
- Keep transactions short; never call the pricing engine's heavier
  computations or any I/O inside an open transaction
- Open one connection per request through Flask's application context,
  closed at teardown; do not size a connection pool for this — SQLite is
  an embedded local file, not a networked database server
- Reset state between test runs by wrapping each test in a transaction
  rolled back after completion, or by using a fresh temporary SQLite file
  per test; never substitute an in-memory or different database engine in
  tests
- Never run a migration against the real local SQLite file from a test
  suite

## 7. Web interface and UX

**HTTP**

- Read the port from an environment variable such as `PORT`; use a
  well-known development default
- Keep Flask handlers thin: decode request → call the pricing engine →
  render the Jinja template or HTMX fragment; validate all incoming
  request data before processing
- Parse a typed query parameter explicitly, distinguishing absent,
  present-and-valid, and present-but-invalid (raise 400 on the last)
- Never let a `GET` or `HEAD` request change state; make every `PUT` and
  `DELETE` idempotent
- Format every date and time field as ISO 8601, every currency code as
  ISO 4217, and every country code as ISO 3166-1 alpha-2, in invoice
  exports and in any JSON the application emits
- Serialise a computed float that is non-finite (`NaN`/`Infinity`) as
  `null` in any JSON export, never as a bare token
- Use a consistent error response shape across all routes; 4xx for client
  errors, 5xx for server errors, never 200 for an error
- Enforce authentication on every route except none are declared public;
  the application has a single administrator account and no self-service
  sign-up or recovery flow

Not applicable: the process-lifecycle rules for graceful shutdown under
an orchestrator (drain deadlines, `SIGTERM` handling across instances) —
the application runs as a single local process with no deployment target
and no second instance to drain into.

**UX and accessibility**

- Meet WCAG 2.1 AA: keep text contrast at 4.5:1 (3:1 for large text),
  keep every interactive element keyboard-reachable, use a native button
  or link rather than a click handler on a non-focusable element, style
  focus with `:focus-visible`, and never convey meaning by colour alone
- Give an icon-only control a descriptive `aria-label`
- Scan rendered pages with an automated accessibility checker; before
  shipping a new interactive component, tab through it without a mouse
  and verify with one screen reader
- Keep visual values (colour, spacing, type) in one CSS source of truth;
  the project has no shared design system yet, so do not hardcode a
  visual value in more than one place
- Support the last two versions of Chrome, Firefox, Safari and Edge

## 8. Review process

Review in this order, most critical first: security, correctness,
clarity, conventions. `docs/solid-ai-templates/templates/core/quality.md`
is the standard for items 2–4.

**MUST checklist**

- [ ] No credential, token or sensitive value appears in a committed file
- [ ] Every failure path is handled; no silent catch, no swallowed
      exception
- [ ] Every new dependency carries an acceptable licence
- [ ] Existing documentation matches the code after the change
- [ ] Every changed section was re-read whole, not only the changed line
- [ ] Input from outside the process (query params, form fields) is
      validated as untrusted before it is used
- [ ] A refactor preserves behaviour on every path, including null
      handling, sort order and boundary values
- [ ] A change touching customer PII or erasure/export code was proposed
      first, per the off-limits rule in section 2.1

**SHOULD checklist**

- [ ] Each non-trivial function has a unit test per relevant variant
- [ ] Coverage does not fall; lint and mypy warnings do not rise
- [ ] Each third-party dependency is necessary, understood and maintained
- [ ] No new abstraction without two call sites

**Testing**

- Double only what a unit test would cross a boundary to reach (SQLite
  I/O, time, randomness); keep deterministic in-process collaborators
  real
- Assert at least one case against a fixed external vector for every
  format defined outside the codebase: an ISO 8601 date, an ISO 4217
  currency code, a jurisdiction's published tax rate
- Allocate a per-test SQLite file or in-memory-equivalent resource from a
  fixture, never a shared one across tests
- Add a regression test for every fixed defect

**Verifying a finding**

- Label a finding unverified until demonstrated by running the path
- Reproduce a defect before reporting it; read a passing test that
  contradicts the reproduction before blaming the code

**Deviations**

- Explain a deviation from a SHOULD rule in the pull request
- Land a deviation from a MUST or MUST NOT rule only with an approver's
  sign-off and its reason recorded in the pull request; never waive one
  yourself

## 9. Session protocol

**Start**

- Run `git status` before touching the tree; never discard or overwrite
  a change the current task did not make
- Re-read the target code for existing coverage before writing anything
- Produce a plan (files, signatures, edge cases, assumptions) before a
  non-trivial change; skip it only for one-line fixes, typos, or fully
  specified changes

**Proceed**

- Stay inside the approved plan; stop and re-surface the options when a
  constraint invalidates it
- Treat any change inside an off-limits path (section 2.1) as needing a
  proposal before it is made, not after

**End**

Before ending any session, read the MUST checklist in section 8 top to
bottom and execute every item in order, without summarizing or skipping
any:

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy --strict .
uv run pytest
git status
git diff --staged
```

- Confirm every check above passes or is explicitly reported as not run
- Confirm `CLAUDE.md` and `README.md` still match the code after the
  change, updating whichever has drifted in the same commit
- Confirm no secret, credential or customer PII value appears in the
  diff or in any commit message before committing
