# tariff

Pricing/invoicing web app for Imbra Ltd, local only.
- Model: inline

## 1. Project
### 1.1 Overview
Catalog, discounts, tax rules, customers, invoices. Python 3.12, Flask 3,
Jinja, HTMX, SQLite; local only, no network egress. One admin signs in via
browser; another program also imports the pricing engine as a library.
### 1.2 Project structure
See the structure map in `README.md`; the pricing-engine library stays
free of Flask/Jinja/HTTP imports.
### 1.3 Commands
Before every commit, run a strict type check, a linter, a formatter
check and the test suite; each must report a clean pass.

## 2. Code conventions
### 2.1 Git
- Work on a branch; never commit to `main` directly.
- Off-limits, propose with a rollback plan first: login/session code,
  GDPR erasure/export code, DB migrations, `.env*` and secrets.
### 2.2 Security and data
- Parameterize every SQLite query; never interpolate input into SQL.
- Hash the admin password (bcrypt/scrypt/Argon2); lock out repeated failures.
- CSRF-protect every state-changing request; cookies: HttpOnly, Secure, SameSite=Lax.
- Rely on Jinja's autoescaping; never bypass it with raw user data.
- Never log a customer's name, email or address; use an opaque ID.
- Erase/anonymize and export a customer's data on request, machine-readable.
- Store money as integer minor units or Decimal; migrate schema with up/down steps.

## 3. Review process
Review order: security, correctness, clarity, conventions; block only on
a demonstrated defect or policy deviation.
- Approver and work tracker: open, not yet named by the project.
- Release: a tagged commit of `main`; there is no deployment step.

## 4. Session protocol
Read the diff before changing anything. At session end, read and
execute, in order, the review rules' MUST and SHOULD checklists.
