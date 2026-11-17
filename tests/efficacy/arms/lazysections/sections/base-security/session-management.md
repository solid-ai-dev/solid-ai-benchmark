# Base — Application Security

Apply these cross-cutting security rules to application code in every
project, regardless of language or framework.

The sections below cover the OWASP Top 10 categories: injection, broken
access control, cryptographic failures, insecure design, security
misconfiguration, vulnerable components, identification and authentication
failures, software and data integrity failures, logging and monitoring
failures, and server-side request forgery.

## Session management

- Generate session IDs with a cryptographic random generator
- Regenerate the session ID after login; this prevents session fixation
- Set cookie flags: `HttpOnly`, `Secure`, `SameSite=Lax` (or `Strict` for
  sensitive applications)
- Expire sessions after an idle period: 30 minutes for sensitive
  applications, configurable otherwise
- Invalidate sessions on logout; do not rely on cookie expiry alone
