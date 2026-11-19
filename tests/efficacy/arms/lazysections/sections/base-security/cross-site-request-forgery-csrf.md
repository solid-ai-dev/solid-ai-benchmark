# Base — Application Security

Apply these cross-cutting security rules to application code in every
project, regardless of language or framework.

The sections below cover the OWASP Top 10 categories: injection, broken
access control, cryptographic failures, insecure design, security
misconfiguration, vulnerable components, identification and authentication
failures, software and data integrity failures, logging and monitoring
failures, and server-side request forgery.

## Cross-site request forgery (CSRF)

- Give every state-changing request a CSRF defence (MUST) when the session
  is authenticated by an ambient credential
- Treat as ambient any credential the browser attaches on its own: a
  cookie, HTTP Basic, or a client certificate
- Use the framework's built-in CSRF middleware; never hand-roll token
  generation or comparison
- Treat `SameSite=Lax` on the session cookie as defence in depth, not the
  defence; it does not cover top-level `POST` navigation on older browsers,
  and a subdomain takeover defeats it
- Prefer the synchroniser token pattern
- Use the signed double-submit cookie where the server holds no session
  state, with the token bound to the session identifier
- Validate the token on every `POST`, `PUT`, `PATCH` and `DELETE`, never on
  `GET`
- Never change state on a `GET` request (MUST NOT)
- Treat an API authenticated only by a bearer token the client attaches
  explicitly as needing no CSRF token; the browser never adds that header
  on its own
- Require a CSRF token on a bearer-token API that also accepts cookie
  authentication
