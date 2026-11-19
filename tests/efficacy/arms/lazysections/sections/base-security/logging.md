# Base — Application Security

Apply these cross-cutting security rules to application code in every
project, regardless of language or framework.

The sections below cover the OWASP Top 10 categories: injection, broken
access control, cryptographic failures, insecure design, security
misconfiguration, vulnerable components, identification and authentication
failures, software and data integrity failures, logging and monitoring
failures, and server-side request forgery.

## Logging

- Never log secrets, tokens or passwords
- Never log personally identifiable information (PII), except the client
  IP in the security log below
- Sanitize log output; user-supplied data in logs can enable log injection
  attacks
- Log security-relevant events: authentication attempts, access denials,
  privilege changes, configuration changes
- Include enough context for investigation: timestamp, an opaque user ID,
  action, result; never a name, email or submitted username
- Record the client IP only in the security log, access-restricted and
  purged at the end of its retention period
- Retain security logs for a defined period; compliance may require 90
  days to 7 years
