# Base — Application Security

Apply these cross-cutting security rules to application code in every
project, regardless of language or framework.

The sections below cover the OWASP Top 10 categories: injection, broken
access control, cryptographic failures, insecure design, security
misconfiguration, vulnerable components, identification and authentication
failures, software and data integrity failures, logging and monitoring
failures, and server-side request forgery.

## Authentication

- Hash passwords with a modern algorithm: bcrypt, scrypt, or Argon2 — never
  MD5, SHA-1, or plain SHA-256
- Require a minimum password length and reject known-breached passwords;
  never impose composition rules (NIST SP 800-63B)
- Use constant-time comparison for secrets and tokens; timing attacks leak
  information through response time
- Lock accounts or throttle after repeated failed attempts

## Session management

- Generate session IDs with a cryptographic random generator
- Regenerate the session ID after login; this prevents session fixation
- Set cookie flags: `HttpOnly`, `Secure`, `SameSite=Lax` (or `Strict` for
  sensitive applications)
- Expire sessions after an idle period: 30 minutes for sensitive
  applications, configurable otherwise
- Invalidate sessions on logout; do not rely on cookie expiry alone

# Backend — Authentication and Authorization

Rules for identity verification (authn) and access control (authz).
Applies to any backend service that has protected resources.
Extends the security rules "Authentication" (`security-authn`) and
"Session management" (`security-sessions`), with backend-specific depth.

## Authentication

- Prefer delegating authentication to an identity provider (IdP) over
  rolling your own
- Expire an access token within 15 minutes when the service issues tokens
  itself
- Issue refresh tokens only to user sessions, such as a browser or mobile
  client; rotate each on use and expire it within 7 days
- Never issue a refresh token to a service
- Authenticate a service by credentials of its own, such as OAuth 2.0
  client credentials, mutual TLS or a scoped API key (below)
- Validate every signed token's signature, expiry, issuer and audience
- Reject a token that lacks any required claim
- Store refresh tokens server-side, in a database or a dedicated session
  store, so they can be revoked; stateless refresh tokens cannot be
  invalidated before expiry

## Token transport

- Send access tokens in the `Authorization: Bearer <token>` header (MUST)
- Do NOT accept tokens in query parameters — they appear in server logs and
  browser history
- Store a browser client's refresh tokens in `httpOnly`, `Secure`,
  `SameSite=Strict` cookies (MUST)
- Never store refresh tokens in `localStorage` or JavaScript-accessible memory
