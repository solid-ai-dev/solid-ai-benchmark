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

Before starting work, read each template below and apply every rule it
holds that fits this project. They are vendored at `docs/solid-ai-templates/`,
at the revision the project adopted.

- `docs/solid-ai-templates/templates/core/quality.md`
- `docs/solid-ai-templates/templates/core/git.md`
- `docs/solid-ai-templates/templates/core/docs.md`
- `docs/solid-ai-templates/templates/core/testing.md`
- `docs/solid-ai-templates/templates/core/review.md`
- `docs/solid-ai-templates/templates/backend/http.md`
- `docs/solid-ai-templates/templates/backend/api.md`
- `docs/solid-ai-templates/templates/security/security.md`
- `docs/solid-ai-templates/templates/backend/auth.md`
- `docs/solid-ai-templates/templates/backend/database.md`
- `docs/solid-ai-templates/templates/frontend/ux.md`
- `docs/solid-ai-templates/templates/data/data-modeling.md`
- `docs/solid-ai-templates/templates/data/data-governance.md`
