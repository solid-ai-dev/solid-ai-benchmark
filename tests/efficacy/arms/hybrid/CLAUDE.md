# tariff

A pricing and invoicing web application for Imbra Ltd — a product catalog, discount rules, tax jurisdictions, customers, and invoices assembled from them. Python 3.12, Flask 3, Jinja, HTMX, SQLite. Runs locally only; there is no deployment target.

- Model: hybrid
- Rule language: a plain imperative ("Use X", "Never Y") is MUST / MUST NOT. RFC 2119 keywords (MUST, MUST NOT, SHOULD, SHOULD NOT, MAY) are used where strength needs to be explicit.
- Precedence where sources disagree: this file, then `AGENTS.md`, then the vendored templates below. A disagreement between this file and `AGENTS.md` is a bug in one of them — fix it before continuing, never act on either alone when the running system is defensible.

Quality conventions are vendored, not submoduled, at `docs/solid-ai-templates/templates/` (a copy pinned at a fixed revision, not a git submodule — never instruct anyone to add it as one). This file inlines every rule the project has adopted from that copy and references the rest by path. Reading a newer version of a referenced template, or moving the vendored copy's pin, adopts nothing by itself (MUST); a rule joins this project only when this file is edited to state it. Exclude `docs/solid-ai-templates/` from any linter, formatter, secret scanner, or spell/link checker the project later adds (MUST), before its first commit.

Key references (read before touching the area they cover):
- `docs/solid-ai-templates/templates/core/quality.md`
- `docs/solid-ai-templates/templates/core/git.md`
- `docs/solid-ai-templates/templates/core/docs.md`
- `docs/solid-ai-templates/templates/core/testing.md`
- `docs/solid-ai-templates/templates/core/review.md`
- `docs/solid-ai-templates/templates/backend/http.md`
- `docs/solid-ai-templates/templates/security/security.md`
- `docs/solid-ai-templates/templates/backend/database.md`
- `docs/solid-ai-templates/templates/frontend/ux.md`
- `docs/solid-ai-templates/templates/data/data-modeling.md`
- `docs/solid-ai-templates/templates/data/data-governance.md`

Declined candidates: `backend/api.md` — the project's only external interfaces are the pricing engine's library API and the invoice exports (per the brief); there is no published HTTP/REST/gRPC/GraphQL contract to version or paginate. `backend/auth.md` — there is one administrator and no second role, no service-to-service API, and no bearer-token or API-key surface; `security/security.md`'s authentication and session rules already cover the single sign-in.

## 1. Project

### 1.1 Identity

- Owner: Imbra Ltd
- Stack: Python 3.12, Flask 3, Jinja, HTMX, SQLite
- Hosting: none — the application runs on the administrator's own machine; it is never deployed, and nothing in it reaches the network (MUST stay true — see §9)

### 1.2 Project structure

- The structure lives in `README.md`'s project map; this file only adds placement rules on top of it. Never duplicate the directory tree here.
- Keep the pricing engine (catalog, discount rules, tax jurisdictions, invoice assembly) in its own package, importable with no Flask, Jinja, HTMX, or SQLite-session code in its import path. Nothing under that package may import from the web layer.
- Keep the Flask app, templates, and HTMX fragment views in a separate package that imports the pricing engine; never the reverse.
- Keep this file, `AGENTS.md`, and `README.md` in the repository root; update all three in the same commit whenever a rule, the stack, or the structure changes, so none of them drifts from the others.

### 1.3 Commands and checks

No specific type checker, linter, formatter, test runner, or package manager is named by the project. Until one is chosen, every check below is a requirement on behavior, not on a tool:

- A static type check over the whole Python codebase must run clean before a commit.
- A linter and a formatter must both run clean before a commit; let the formatter run on save rather than hand-formatting.
- The full test suite (pricing engine unit tests, Flask integration tests, and any end-to-end check of the invoice export) must run clean before a merge.
- Report any of the above as "not run" when it could not run; never report it as passing.

## 2. Architecture boundaries

- There are exactly two actors: the administrator, who works through the browser, and another program, which imports the pricing engine directly, with no web application present. The web application is one caller of the library among possibly several; design and test the library so it never assumes the web app is running.
- The pricing engine is a library: never let it write to standard output or standard error, and never let it configure logging beyond its own logger (MUST). Give it an injectable logger that falls back to its own module logger. Verify its silence in a fresh process — a test runner's own log handler hides the default.
- The store is a local SQLite file; nothing in the system reaches the network. Treat any change that would open a socket, call an external HTTP service, or depend on a remote resource as outside this project's design until the brief says otherwise — raise it rather than add it.
- Keep the Flask handlers thin: decode the request, call the pricing engine or a data-access function, render or encode the response. Never put discount, tax, or pricing logic in a handler or a template.

## 3. Off-limits paths

Change only with explicit approval, a stated rollback strategy, and the regression test that would catch a mistake, proposed before the change is made (MUST):

- Sign-in and session code (there is exactly one administrator account; a bug here is a full compromise or a full lockout)
- The pricing engine's discount, tax, and invoice-total calculation logic (an error here is a wrong invoice, not just a wrong screen)
- Database migrations, once merged
- `.env*` files and any other secret material
- Any CI/CD workflow the project later adds

Name any off-limits path touched by a change at the top of its summary, whether proposed or already approved (MUST). A diff confined to comments or prose inside these paths is ordinary work; anything executable — logic, flags, migration steps — is not.

## 4. Git and change conventions

- Work on a branch; never commit directly to `main`.
- Commit under one consistent name and email.
- Never commit build output, dependency directories, the SQLite database file, or any secret. Keep a `.gitignore` covering all of these plus editor and OS files.
- Commit lockfiles once the project has one.
- Inspect the working tree and the index before starting a task; never discard, reset, stash, or overwrite a change the task did not make.
- Stage only the task's own changes — a whole file only if it held no prior change, otherwise only the task's hunks. Read the staged diff before committing.
- Keep a pull request (or, for a solo change, a single commit) to one concern.
- Never force-push. Bring a branch up to date by merging the base into it, never by rebasing and force-pushing.
- Treat every repository as public: no secret or credential in source or history, ever, even though this project has no deployment target.

## 5. Code quality and Python conventions

- Keep one authoritative representation of each piece of pricing, discount, tax, or invoicing rule; a second copy is a bug waiting to diverge from the first.
- Build only what the brief or an approved plan calls for; no speculative discount types, tax rules, or export formats ahead of a stated need.
- Name a function with a verb, a class or module with a noun, a boolean with `is`/`has`/`can`. Name a discount kind, tax rule, or export format for the capability it offers (`DiscountKind.PERCENTAGE`), never for a library behind it.
- Keep cognitive complexity at or under 15 per function; nest at most three levels; use guard clauses over nested conditionals.
- Replace a boolean flag that selects behavior with an enum or two named functions.
- Name every magic number and magic string (a tax rate, a rounding mode, a discount cap) as a constant.
- Keep the module graph acyclic and coupling shallow: a change to one discount kind or tax rule must not force a change in an unrelated one.
- Validate input at the Flask boundary and fail at once on invalid state; do not re-validate the same precondition in every inner function, but do assert it where a function depends on it.
- Add an error type only where a caller (the web layer, or the other program) could act differently on it; never change what type a public function raises.
- Prefer code that needs no comment; when a comment is needed, state the non-obvious why, never the what. Never cite an issue or PR number in a comment — state the substance instead.
- Commit no debug `print()`/breakpoints and no commented-out code.
- Annotate every public function's parameters and return type.
- Encode every committed text file in UTF-8 with LF line endings; keep identifiers ASCII.
- Wrap Markdown documentation conservatively (roughly 80-100 columns) until the project declares and enforces a specific width.
- A task finishes when the requested behavior works through the entry point that reaches it (a route, the library's public function, or the export) and the tests that prove it pass — not when surrounding code has also been rewritten.

## 6. Data modeling and database conventions

- Use one naming convention across every SQLite table, column, key, and index.
- Give every table a primary key; prefer a surrogate key internally.
- Store each fact once; duplicate only with a documented reason.
- Never pack several values into one text column (e.g., an address) — use separate columns or a related table.
- Enforce every foreign key with SQLite's own constraint; decide and document, per relationship, whether deleting the target deletes the referencing rows, clears the reference, or is refused.
- Store a discount's kind as a discriminator column plus the fields that kind needs; never overload one column to mean different things for different kinds.
- Store monetary values (prices, discount amounts, tax amounts, invoice totals) as integers in minor units or as a fixed-precision decimal type — never as floating point.
- Store every date and time in ISO 8601, in UTC where a time is involved; convert to local time only when displaying it.
- Represent a tax jurisdiction's country as an ISO 3166-1 alpha-2 code and every currency as an ISO 4217 code.
- Document a maximum length for every text field, including name, email, and postal-address fields.
- Run every schema change through a migration committed to the repository, with both an `up` and a `down` step; never hand-edit the schema. Say so, and get approval, when a `down` step would lose data.
- Parameterize every query that takes a value; never build SQL by string interpolation.
- Bound every interactive query (an invoice list, a customer list) with a limit or pagination; never load an unbounded result into a page.
- Fetch related rows for a set of records in one query, never one query per row in a loop.
- Wrap each multi-step write (e.g., assembling an invoice from catalog, discount, and tax rows) in a transaction; keep transactions short and never call out to the pricing engine's I/O from inside one.
- Use soft deletes only where audit history is required (see §7); otherwise delete the row.
- In tests, use the real SQLite engine, not an in-memory substitute with different behavior, and reset state between tests rather than relying on run order.

## 7. Privacy and data governance (GDPR)

The business is in the EU; the GDPR applies to every customer's name, email, and postal address, and to any invoice that names them.

- Classify customer name, email, and postal address, and any invoice line that carries them, as confidential data; scope database and export access to the single administrator account accordingly.
- Encrypt the SQLite file at rest (e.g., full-disk or file-level encryption on the machine it runs on) given it holds confidential PII, and never transmit it anywhere — nothing in this project reaches the network.
- Minimize collection: store only the name, email, and postal address the invoicing process needs; add no further personal field without a stated reason.
- Never put a customer's name, email, or address in an application log, error message, or stack trace (MUST NOT). Identify a customer in a log by an opaque internal ID only.
- Implement the customer's right of access (GDPR Art. 15) as a function that exports everything stored about one customer, keyed by that customer's ID, in a form the administrator can hand over.
- Implement the customer's right to erasure (GDPR Art. 17) as a real delete or anonymization of the customer's personal fields — never a soft delete that leaves the name, email, or address readable.
- Resolve the conflict between erasure and invoice retention explicitly: when a legal or tax obligation requires keeping a past invoice's financial record, anonymize that invoice's customer-identifying fields (name, email, address) in place rather than deleting the invoice row, and delete the live customer record itself. Document the retention period that obligation sets, and purge personal data automatically once it lapses rather than relying on a manual sweep.
- Keep an audit trail, separate from the application log, of every access-and-erasure action taken (export produced, erasure applied) and every edit to a customer's PII: actor (the administrator), timestamp, action, and that a value changed — never the old or new value itself. Make this trail append-only.
- Treat Imbra Ltd (via the administrator account) as the owner of every data domain — catalog, discount rules, tax jurisdictions, customers, invoices — there being no separate team to assign it to.

## 8. Security

- Validate all input arriving through a Flask route (form fields, query parameters, HTMX payloads) at that boundary, with an allowlist, before it reaches the pricing engine or the database.
- Encode every value rendered into a Jinja template for its context; never bypass Jinja's autoescaping with a raw-HTML path for user-supplied or stored data (customer names and addresses included).
- Parameterize every database query (see §6); never pass stored data to a shell or an `eval`-like construct.
- Hash the administrator's password with bcrypt, scrypt, or Argon2 — never MD5, SHA-1, or plain SHA-256. Require a minimum length and reject known-breached passwords; impose no composition rules.
- Lock the account or throttle sign-in after repeated failed attempts; compare secrets and tokens in constant time.
- Generate the session ID cryptographically at random, regenerate it on successful sign-in, and invalidate it on logout rather than relying on cookie expiry alone.
- Set the session cookie `HttpOnly`, `Secure`, and `SameSite=Strict` given the data behind it is financial and personal. Current browsers treat `http://localhost` as a secure context, so `Secure` does not block local-only operation.
- Expire the session after 30 minutes of idleness, given the sensitivity of the data.
- Give every state-changing HTMX request (`hx-post`, `hx-put`, `hx-delete`) CSRF protection bound to the session; validate the token on every such request and never on a `GET`. Never let a `GET`/`hx-get` request change state.
- Never hardcode a secret, API key, or credential in source; keep any local secret file out of version control and out of logs.
- Return generic error messages to the browser (no stack trace, no file path, no SQL error) while logging full detail server-side without PII.
- Set standard security response headers (`Content-Security-Policy`, `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY` or an equivalent CSP directive, `Referrer-Policy`) at the application level even though the app never leaves the local machine — they are the only defense against a stored-XSS in a customer name or product field reaching the administrator's own browser.
- Require the administrator's authenticated session on every route; the application has no public endpoint, so no route is exempt.
- Not adopted, and why: HTTPS/HSTS/TLS cipher rules (the brief's own carve-out for local development, and the app never serves over a public network), CORS rules (single-origin, no cross-origin API), SSRF rules (the app makes no outbound request to a user-supplied URL), file-upload rules (the brief describes no upload feature).
- Never read, print, or log the contents of `.env*`, credential files, or key files while working in this repository; check a secret's presence by name only, never by value. Warn before committing any file that commonly holds secrets.

## 9. Web and UI conventions

- Read the port the Flask app binds to from an environment variable, with a well-known local-development default; never hardcode it.
- Run migrations and any other one-off admin task through the application's own committed code, never as an ad-hoc shell command against the database file.
- Keep no state in process memory that a restart cannot rebuild from the SQLite file; a crash must lose nothing already committed.
- Parse a typed query parameter (an invoice-list filter, a pagination offset) so that absent, present-and-valid, and present-but-invalid are distinguished; never let a malformed value silently fall back to a default.
- Read request headers case-insensitively; avoid an `X-` prefix on any custom header the app introduces.
- Serialize any date on a page or in an export as ISO 8601, any currency amount as the stored decimal/integer value with its ISO 4217 code, and any country as its ISO 3166-1 alpha-2 code (see §6).
- Make every view usable at a small viewport, not desktop-only, even for a single-administrator tool.
- Meet WCAG 2.1 AA: keyboard-operable controls, a visible `:focus-visible` indicator, semantic HTML and heading structure, no meaning conveyed by color alone, descriptive `alt` text on any image.
- Give an HTMX partial swap that changes meaningful page state an `aria-live` region or equivalent announcement; a partial swap triggers no page-load announcement on its own, so a screen reader user would otherwise miss it.
- Take any visual value (color, spacing, type scale) from a single place in the codebase rather than repeating it per template; adopt a design system only if the project introduces one.
- Support the last two versions of Chrome, Firefox, Safari, and Edge.

## 10. Testing

- Classify a test by the boundary it crosses: a pricing-engine unit test crosses none; a Flask route test crosses the process boundary into the engine and the database; a full invoice-export run is a system test.
- Keep the pricing engine's own test suite runnable with no Flask app, Jinja, HTMX, or SQLite session present — it must prove itself as a library.
- Cover every discount kind, every tax-jurisdiction rule, and every rounding path with its own unit test, including edge cases (zero quantity, 100% discount, a jurisdiction with no tax).
- Assert at least one tax or rounding calculation against a fixed external vector (a published tax table or worked example) rather than only round-tripping the engine's own output back through itself.
- Add a regression test for every fixed defect.
- Test the Flask layer's sign-in: an unauthenticated request to any route is rejected, and a session expires after its idle timeout.
- Test the erasure and access-export functions directly: erasure removes or anonymizes every personal field everywhere it is stored (including past invoices, per §7), and the access export contains everything stored about that customer.
- Reset database state between tests (truncate or roll back a transaction) rather than relying on test order; never substitute an in-memory engine for SQLite in a test that exercises real queries.
- Investigate a failing test before anything else; never skip or silence one without a documented reason.

## 11. Review process

Review in this order, most critical first; items 2-4 are held to the standard in §§5-9 above.

1. Security
2. Correctness (wrong invoice totals, wrong tax, unhandled failure, a race on a shared SQLite write)
3. Clarity
4. Conventions

Produce a plan — files touched, signatures, edge cases, assumptions — before implementing a feature or any change to the pricing engine; do not write implementation code until the plan is agreed (MUST NOT), except for one-line fixes, typos, or fully specified work.

MUST checklist, run on every change before it merges:

- [ ] No credential, token, or sensitive value appears in a committed file
- [ ] Every failure path is handled; no silent catch, no swallowed exception
- [ ] Every new dependency carries a license the project allows
- [ ] Significant logic and architectural decisions are documented
- [ ] Existing documentation (`README.md`, `AGENTS.md`, this file) matches the code after the change
- [ ] Every changed section was re-read whole, not only the changed line
- [ ] Every claim changed text makes about itself (a count, "every", "all") was checked by actually counting
- [ ] Input from outside the process (a form field, a query parameter, an HTMX payload) is validated as untrusted before it is used
- [ ] A refactor of the pricing engine preserves behavior on every discount kind, tax rule, and rounding case, including boundary values

SHOULD checklist:

- [ ] Each non-trivial function has a unit test per relevant variant
- [ ] Coverage does not fall
- [ ] Lint and type-check findings do not rise
- [ ] Each third-party dependency is necessary, understood, and maintained
- [ ] No new abstraction without two call sites, and no new dependency without a documented reason

Label a review finding a demonstrated defect, a policy deviation, or a suggestion; block a merge only on the first two. Label a finding unverified until it has been reproduced by running the path, or the measurement that produced it has been checked against the real scope and a hand-checked sample. Run a structure audit (every MUST above, plus the project's layer-specific MUSTs) after a framework or stack change and before any release milestone. Land a deviation from a MUST or MUST NOT rule only with the designated approver's sign-off, recorded with its reason (see §12 for who that is).

## 12. Open questions and answers

- **Who approves a change?** Not named by the project brief. Until named, the person making the change reviews it themselves against the MUST checklist in §11 before it merges.
- **How is work tracked?** Not named by the project brief; open for the project to decide.
- **What is a release?** The project has no deployment target. A release is a tagged commit on `main` that has passed the MUST checklist and the full test suite — the version a local installation updates to, nothing more.

## 13. Session protocol

- Start a session by reading this file, `AGENTS.md`, and the relevant templates referenced in §0 for the area about to change; re-read §3 (off-limits paths) before touching anything that might qualify.
- Produce a plan (§11) before implementing a feature or a non-trivial change; stay inside an approved plan, and stop and re-surface the options when a constraint invalidates it.
- During the session, update `README.md`, `AGENTS.md`, and this file in the same commit as any change to structure, stack, conventions, or adopted rules.
- Before ending the session, execute the MUST checklist in §11, top to bottom, in order, against the actual change made — not a summary of it. Do not skip or paraphrase an item; a failing item is a fix, not a note. Only once every item passes (or is explicitly and visibly not applicable) is the session's work ready to hand off.
