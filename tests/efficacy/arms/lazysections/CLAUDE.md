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

- Model: root and sections
- Owner: Imbra Ltd
- Repository: this repository

## Commands

Python 3.12, Flask 3, Jinja, HTMX and SQLite; the brief names no tooling. It runs locally; there is no deployment target.

## Answers

- Who approves a change: not stated in the brief
- How work is tracked: not stated in the brief
- What a release is: not stated in the brief; the application runs locally

## Rules

Built by `resolve_chain.py --emit`; change the templates, not the rules below.

The adopted rules are in the section files below, one topic each. Do not
read them before the work starts. The first time the work touches a
section's topic, read its file; then apply every rule it holds.

### Base — Quality Attributes

Architecture, code style, calibration, tool trust, testing

| When the work first touches | Read first |
| --- | --- |
| Principles | `.agents/sections/base-quality/principles.md` |
| Architecture | `.agents/sections/base-quality/architecture.md` |
| Naming | `.agents/sections/base-quality/naming.md` |
| Complexity | `.agents/sections/base-quality/complexity.md` |
| Dependencies | `.agents/sections/base-quality/dependencies.md` |
| Errors | `.agents/sections/base-quality/errors.md` |
| Deprecation and renames | `.agents/sections/base-quality/deprecation-and-renames.md` |
| Module structure | `.agents/sections/base-quality/module-structure.md` |
| Library output | `.agents/sections/base-quality/library-output.md` |
| Encoding and line endings | `.agents/sections/base-quality/encoding-and-line-endings.md` |
| Comments | `.agents/sections/base-quality/comments.md` |
| Debug code | `.agents/sections/base-quality/debug-code.md` |
| Rejected mechanisms | `.agents/sections/base-quality/rejected-mechanisms.md` |
| New constraints | `.agents/sections/base-quality/new-constraints.md` |
| Destructive operations | `.agents/sections/base-quality/destructive-operations.md` |
| Check trust | `.agents/sections/base-quality/check-trust.md` |
| Static checks | `.agents/sections/base-quality/static-checks.md` |
| Enforcement | `.agents/sections/base-quality/enforcement.md` |
| Completion | `.agents/sections/base-quality/completion.md` |

### Base — Git Conventions

Committer identity, branching, pull requests, CI evidence, regenerated artifacts, off-limits paths, .gitignore

| When the work first touches | Read first |
| --- | --- |
| Commits | `.agents/sections/base-git/commits.md` |
| Existing changes | `.agents/sections/base-git/existing-changes.md` |
| Pull requests | `.agents/sections/base-git/pull-requests.md` |
| CI evidence | `.agents/sections/base-git/ci-evidence.md` |
| Updating a branch | `.agents/sections/base-git/updating-a-branch.md` |
| Regenerated artifacts | `.agents/sections/base-git/regenerated-artifacts.md` |
| Off-limits paths | `.agents/sections/base-git/off-limits-paths.md` |

### Base — Documentation

Rule language, standard documents, upkeep, line width, writing style, diagrams, generated files, agent output files

| When the work first touches | Read first |
| --- | --- |
| Rule language | `.agents/sections/base-docs/rule-language.md` |
| Standard documents | `.agents/sections/base-docs/standard-documents.md` |
| Single source of truth | `.agents/sections/base-docs/single-source-of-truth.md` |
| Upkeep | `.agents/sections/base-docs/upkeep.md` |
| Disagreements | `.agents/sections/base-docs/disagreements.md` |
| Adopting shared rules | `.agents/sections/base-docs/adopting-shared-rules.md` |
| Line width | `.agents/sections/base-docs/line-width.md` |
| Writing style | `.agents/sections/base-docs/writing-style.md` |
| Cold readers | `.agents/sections/base-docs/cold-readers.md` |
| Diagrams and assets | `.agents/sections/base-docs/diagrams-and-assets.md` |
| Docs as code | `.agents/sections/base-docs/docs-as-code.md` |
| Generated files | `.agents/sections/base-docs/generated-files.md` |
| Output file by agent | `.agents/sections/base-docs/output-file-by-agent.md` |
| Session handoff | `.agents/sections/base-docs/session-handoff.md` |

### Base — Testing

Test types, isolation, assertions, proving a change

| When the work first touches | Read first |
| --- | --- |
| Test types | `.agents/sections/base-testing/test-types.md` |
| Coverage | `.agents/sections/base-testing/coverage.md` |
| Testability | `.agents/sections/base-testing/testability.md` |
| Isolation | `.agents/sections/base-testing/isolation.md` |
| External definitions | `.agents/sections/base-testing/external-definitions.md` |
| Guard use | `.agents/sections/base-testing/guard-use.md` |
| Provenance | `.agents/sections/base-testing/provenance.md` |
| Thresholds | `.agents/sections/base-testing/thresholds.md` |
| Empty results | `.agents/sections/base-testing/empty-results.md` |
| Fault injection | `.agents/sections/base-testing/fault-injection.md` |
| Unique resources | `.agents/sections/base-testing/unique-resources.md` |
| Worker leaks | `.agents/sections/base-testing/worker-leaks.md` |
| Call sites | `.agents/sections/base-testing/call-sites.md` |
| Real data | `.agents/sections/base-testing/real-data.md` |
| Rendered output | `.agents/sections/base-testing/rendered-output.md` |
| Drift guards | `.agents/sections/base-testing/drift-guards.md` |

### Base — Peer Review

Peer review priority, MUST/SHOULD checklists, deviation rules

| When the work first touches | Read first |
| --- | --- |
| Principle | `.agents/sections/base-review/principle.md` |
| Priority order | `.agents/sections/base-review/priority-order.md` |
| MUST checklist | `.agents/sections/base-review/must-checklist.md` |
| SHOULD checklist | `.agents/sections/base-review/should-checklist.md` |
| CI signals | `.agents/sections/base-review/ci-signals.md` |
| Structure audit | `.agents/sections/base-review/structure-audit.md` |
| Picking up an issue | `.agents/sections/base-review/picking-up-an-issue.md` |
| Planning | `.agents/sections/base-review/planning.md` |
| Verifying a finding | `.agents/sections/base-review/verifying-a-finding.md` |
| Deviations | `.agents/sections/base-review/deviations.md` |

### Backend — HTTP Conventions

Port, lifecycle, admin tasks, handlers, headers, methods, payloads, errors, auth

| When the work first touches | Read first |
| --- | --- |
| Port binding | `.agents/sections/backend-http/port-binding.md` |
| Process lifecycle | `.agents/sections/backend-http/process-lifecycle.md` |
| Admin processes | `.agents/sections/backend-http/admin-processes.md` |
| Handler design | `.agents/sections/backend-http/handler-design.md` |
| Query parameters | `.agents/sections/backend-http/query-parameters.md` |
| Request headers | `.agents/sections/backend-http/request-headers.md` |
| HTTP methods | `.agents/sections/backend-http/http-methods.md` |
| Resource representation | `.agents/sections/backend-http/resource-representation.md` |
| Error responses | `.agents/sections/backend-http/error-responses.md` |
| Authentication and authorisation | `.agents/sections/backend-http/authentication-and-authorisation.md` |

### Backend — API Design

API-first, contracts, versioning, deprecation, pagination

| When the work first touches | Read first |
| --- | --- |
| API-first | `.agents/sections/backend-api/api-first.md` |
| Protocol selection | `.agents/sections/backend-api/protocol-selection.md` |
| API contract | `.agents/sections/backend-api/api-contract.md` |
| Versioning | `.agents/sections/backend-api/versioning.md` |
| Backward compatibility | `.agents/sections/backend-api/backward-compatibility.md` |
| Deprecation strategy | `.agents/sections/backend-api/deprecation-strategy.md` |
| Statelessness | `.agents/sections/backend-api/statelessness.md` |
| Pagination | `.agents/sections/backend-api/pagination.md` |

### Base — Application Security

Application security rules — input, output, injection, auth, sessions, TLS, headers

| When the work first touches | Read first |
| --- | --- |
| Input validation | `.agents/sections/base-security/input-validation.md` |
| Output encoding (XSS) | `.agents/sections/base-security/output-encoding-xss.md` |
| Injection prevention | `.agents/sections/base-security/injection-prevention.md` |
| Authentication | `.agents/sections/base-security/authentication.md` |
| Session management | `.agents/sections/base-security/session-management.md` |
| Cross-site request forgery (CSRF) | `.agents/sections/base-security/cross-site-request-forgery-csrf.md` |
| Secrets in code | `.agents/sections/base-security/secrets-in-code.md` |
| Transport security | `.agents/sections/base-security/transport-security.md` |
| Security headers | `.agents/sections/base-security/security-headers.md` |
| Error handling | `.agents/sections/base-security/error-handling.md` |
| Logging | `.agents/sections/base-security/logging.md` |
| Deserialization and data integrity | `.agents/sections/base-security/deserialization-and-data-integrity.md` |
| Agent secrets handling | `.agents/sections/base-security/agent-secrets-handling.md` |

### Backend — Authentication and Authorization

Authn/authz, JWT, RBAC, sessions, API keys

| When the work first touches | Read first |
| --- | --- |
| General principles | `.agents/sections/backend-auth/general-principles.md` |
| Authentication | `.agents/sections/backend-auth/authentication.md` |
| Token transport | `.agents/sections/backend-auth/token-transport.md` |
| Authorization | `.agents/sections/backend-auth/authorization.md` |
| Observability | `.agents/sections/backend-auth/observability.md` |
| Testing | `.agents/sections/backend-auth/testing.md` |

### Backend — Database Conventions

Migrations, transactions, parameterised queries, connection pooling

| When the work first touches | Read first |
| --- | --- |
| Schema changes | `.agents/sections/backend-database/schema-changes.md` |
| Queries | `.agents/sections/backend-database/queries.md` |
| Indexing | `.agents/sections/backend-database/indexing.md` |
| Transactions | `.agents/sections/backend-database/transactions.md` |
| Connections | `.agents/sections/backend-database/connections.md` |
| Soft deletes | `.agents/sections/backend-database/soft-deletes.md` |
| Testing | `.agents/sections/backend-database/testing.md` |

### Frontend — UX Principles

UX principles, WCAG 2.1 AA, accessibility testing, design system, browser support

| When the work first touches | Read first |
| --- | --- |
| UX principles | `.agents/sections/frontend-ux/ux-principles.md` |
| Accessibility — WCAG 2.1 AA | `.agents/sections/frontend-ux/accessibility-wcag-2-1-aa.md` |
| Accessibility testing | `.agents/sections/frontend-ux/accessibility-testing.md` |
| Design system | `.agents/sections/frontend-ux/design-system.md` |
| Browser support | `.agents/sections/frontend-ux/browser-support.md` |

### Base — Data Modeling

Schema design, naming, normalization, relationships, data types

| When the work first touches | Read first |
| --- | --- |
| Naming conventions | `.agents/sections/base-data-modeling/naming-conventions.md` |
| Normalization | `.agents/sections/base-data-modeling/normalization.md` |
| Relationships | `.agents/sections/base-data-modeling/relationships.md` |
| Schema evolution | `.agents/sections/base-data-modeling/schema-evolution.md` |
| Data types | `.agents/sections/base-data-modeling/data-types.md` |

### Base — Data Governance

Classification, PII handling, retention, ownership, audit trail

| When the work first touches | Read first |
| --- | --- |
| Data classification | `.agents/sections/base-data-governance/data-classification.md` |
| PII handling | `.agents/sections/base-data-governance/pii-handling.md` |
| Retention | `.agents/sections/base-data-governance/retention.md` |
| Data ownership | `.agents/sections/base-data-governance/data-ownership.md` |
| Audit trail | `.agents/sections/base-data-governance/audit-trail.md` |
