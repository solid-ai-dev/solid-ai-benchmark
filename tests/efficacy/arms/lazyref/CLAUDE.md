# tariff

`tariff` — Imbra Ltd — a pricing and invoicing web application:
a product catalog, discount rules of several kinds, tax jurisdictions,
customers, and invoices assembled from them — Python 3.12 / Flask 3 /
Jinja / HTMX / SQLite — runs locally, no deployment target

Personal data: customers are people, stored with their name, email and
postal address and named on the invoices billed to them. The business is
in the EU, so the GDPR applies: a customer may ask for their data to be
erased or for a copy of it. One administrator signs in to use the
application; nobody else has an account.

Boundaries and actors: two actors, the administrator working in a browser
and another program; the pricing engine is a library the program imports
without the web application present, and the web application is one
caller of it. The store is a local file. Nothing reaches the network.
The program's interfaces are the library's own API and the invoice
exports.

The project's rules are the templates below, one per topic. Do not read them
before the work starts. The first time the work touches a template's topics,
read that template, vendored at `docs/solid-ai-templates/` at the revision the
project adopted; then apply every rule it holds that fits this project.

| When the work first touches | Read first |
| --- | --- |
| Architecture, code style, calibration, tool trust, testing | `docs/solid-ai-templates/templates/core/quality.md` |
| Committer identity, branching, pull requests, CI evidence, regenerated artifacts, off-limits paths, .gitignore | `docs/solid-ai-templates/templates/core/git.md` |
| Rule language, standard documents, upkeep, line width, writing style, diagrams, generated files, agent output files | `docs/solid-ai-templates/templates/core/docs.md` |
| Test types, isolation, assertions, proving a change | `docs/solid-ai-templates/templates/core/testing.md` |
| Peer review priority, MUST/SHOULD checklists, deviation rules | `docs/solid-ai-templates/templates/core/review.md` |
| Port, lifecycle, admin tasks, handlers, headers, methods, payloads, errors, auth | `docs/solid-ai-templates/templates/backend/http.md` |
| API-first, contracts, versioning, deprecation, pagination | `docs/solid-ai-templates/templates/backend/api.md` |
| Application security rules — input, output, injection, auth, sessions, TLS, headers | `docs/solid-ai-templates/templates/security/security.md` |
| Authn/authz, JWT, RBAC, sessions, API keys | `docs/solid-ai-templates/templates/backend/auth.md` |
| Migrations, transactions, parameterised queries, connection pooling | `docs/solid-ai-templates/templates/backend/database.md` |
| UX principles, WCAG 2.1 AA, accessibility testing, design system, browser support | `docs/solid-ai-templates/templates/frontend/ux.md` |
| Schema design, naming, normalization, relationships, data types | `docs/solid-ai-templates/templates/data/data-modeling.md` |
| Classification, PII handling, retention, ownership, audit trail | `docs/solid-ai-templates/templates/data/data-governance.md` |
