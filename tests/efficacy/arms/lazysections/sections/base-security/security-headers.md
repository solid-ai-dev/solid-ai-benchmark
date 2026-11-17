# Base — Application Security

Apply these cross-cutting security rules to application code in every
project, regardless of language or framework.

The sections below cover the OWASP Top 10 categories: injection, broken
access control, cryptographic failures, insecure design, security
misconfiguration, vulnerable components, identification and authentication
failures, software and data integrity failures, logging and monitoring
failures, and server-side request forgery.

## Security headers

- Set security headers on every HTTP response at the reverse proxy or
  middleware level, not per route
- Set these required headers:
  - `Content-Security-Policy` — start strict, relax only what a page needs
  - `X-Content-Type-Options: nosniff`
  - `X-Frame-Options: DENY` (or CSP `frame-ancestors`)
  - `Strict-Transport-Security` (see Transport security)
  - `Referrer-Policy: strict-origin-when-cross-origin`
  - `Permissions-Policy` — disable unused browser APIs
- Map each static asset type to its `Content-Type` in code when enabling
  `nosniff`; the browser then never corrects a wrong one
- Never let MIME resolution depend on the host when `nosniff` is enabled
  (MUST NOT)
- When enabling `nosniff`, verify script and style execution in a real
  browser, not just status codes
- Never use `unsafe-inline` or `unsafe-eval` in CSP without a written
  justification
- Do not expose server version or technology stack in headers; remove
  `X-Powered-By`, `Server` version strings
