# tariff

Pricing and invoicing web app for Imbra Ltd: catalog, discount rules, tax
jurisdictions, customers, invoices. Python 3.12, Flask 3, Jinja, HTMX,
SQLite; uv, ruff, mypy strict, pytest. Runs locally only; no deploy target.
- Model: inline
## 1. Project
The pricing engine is a standalone, framework-free library with its own
public API, called by the Flask app and by another program, never the
reverse. See `README.md` for structure; do not duplicate it here.
```bash
uv run ruff check . && uv run mypy --strict . && uv run pytest
```
## 2. Code conventions
- Branch-only commits, never `main`; commit `uv.lock`, never secrets,
  `.env*`, or the SQLite file; off-limits: admin auth/session, migrations, secrets.
- Keep routes thin: decode, call the library/service, render; give the
  library its own injectable logger and never print or configure logging.
- Store money as `Decimal` (minor units or decimal column), never `float`;
  store timestamps in UTC; parameterize every SQL query.
- Hash the admin password with bcrypt/scrypt/Argon2; set session cookie
  flags `HttpOnly`, `Secure`, `SameSite=Lax` with a 30-minute idle expiry;
  require a CSRF token on every POST/PUT/PATCH/DELETE route.
- Never log a customer's name, email or address, only an opaque ID. Erase
  personal data on request by hard delete or anonymization, never a
  soft-delete flag alone, and provide a way to export one customer's data.
## 3. Quality and review
- Cover each discount rule, tax jurisdiction and invoice path, happy and
  edge cases, with pytest; add a regression test per fixed bug; test
  against a real SQLite file, never an in-memory substitute. Keep ruff,
  mypy --strict and pytest green before merging.
- Self-review every change against this file (solo maintainer, no other
  approver). Block a merge on a secret in the diff, a missing migration,
  an unhandled failure path, or PII in a log line; tracking/release: open.
## 4. Session protocol
Run each item in order at session end, never skipped or summarized:
1. `uv run ruff check .`, `uv run mypy --strict .`, `uv run pytest`
2. Confirm no secret, `.env` value or the SQLite file is staged
3. Update `README.md`, `AGENTS.md` and this file if conventions changed
4. Review the staged diff for off-limits paths before committing
