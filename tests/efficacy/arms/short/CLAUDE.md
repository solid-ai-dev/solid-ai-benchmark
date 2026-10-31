# tariff
Pricing and invoicing web app for Imbra Ltd: catalog, discounts, tax
jurisdictions, customers, invoices. Python 3.12, Flask 3, Jinja, HTMX,
SQLite, uv. One administrator; runs locally only, no deployment target.
The pricing engine is a library another program may import directly.
- Model: inline
## 1. Project
See README.md for the directory map; place code beside its layer.
```bash
uv run flask run                                    # start the app
uv run ruff check . && uv run ruff format --check . # lint
uv run mypy --strict . && uv run pytest             # types + tests
```
## 2. Code conventions
- Work on a branch; never commit to `main`. Commit `uv.lock`, never
  `.env`, secrets, or build output.
- Off-limits without approval: auth/session code, migrations, `.env*`.
- Parameterize every SQL query; never interpolate input into SQL.
- Store money as integer minor units or `Decimal`, never `float`.
- Hash the administrator's password with bcrypt, scrypt, or Argon2.
- Regenerate the session ID on login; expire idle sessions; set
  `HttpOnly`, `Secure`, `SameSite=Lax` cookies.
- Give every state-changing HTMX/form request a CSRF token.
- Encode all template output for context; never bypass autoescaping.
- Run schema changes through a migration with up/down steps; never
  edit the SQLite file by hand.
- Never log a customer's name, email, address, or any secret value.
- Classify customer PII (name, email, postal address); export or erase
  it on request: hard delete or anonymize, never soft-delete alone.
- Cover pricing, discount, and tax logic with edge-case unit tests.
## 3. Review process
Review in order: security, correctness, clarity, conventions.
- [ ] No secret or PII value in a committed file or log.
- [ ] Every SQL query parameterized; every migration has up/down.
- [ ] Money uses integer minor units or `Decimal`, never `float`.
## 4. Session protocol
- Approver: the repository owner. Tracking: open, no tracker named.
- Release: a tagged commit on `main` after lint, types, tests pass.
- End of session, run in order: `ruff check .`, `mypy --strict .`,
  `pytest`; report any that did not run as not run, never as passed.
