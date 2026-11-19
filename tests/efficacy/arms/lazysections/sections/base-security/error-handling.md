# Base — Application Security

Apply these cross-cutting security rules to application code in every
project, regardless of language or framework.

The sections below cover the OWASP Top 10 categories: injection, broken
access control, cryptographic failures, insecure design, security
misconfiguration, vulnerable components, identification and authentication
failures, software and data integrity failures, logging and monitoring
failures, and server-side request forgery.

## Error handling

- Never expose stack traces, internal paths, or database errors to end
  users; return generic error messages externally
- Log full error details server-side for debugging
- Use consistent error response formats; do not leak internal structure
  through varying error shapes
- Return each error through the protocol's own error signal, never as a
  success
- Do not reveal whether a resource exists via error messages: login errors
  should say "invalid credentials", not "user not found" vs "wrong password"
