# Base — Application Security

Apply these cross-cutting security rules to application code in every
project, regardless of language or framework.

The sections below cover the OWASP Top 10 categories: injection, broken
access control, cryptographic failures, insecure design, security
misconfiguration, vulnerable components, identification and authentication
failures, software and data integrity failures, logging and monitoring
failures, and server-side request forgery.

## Transport security

- Use HTTPS everywhere, with no exceptions for production traffic
- Enable HSTS on all production sites (MUST), with `includeSubDomains` and
  a minimum `max-age` of one year
- Require TLS 1.2 as the minimum version; disable TLS 1.0 and 1.1
- Use strong cipher suites; disable known-weak ciphers
