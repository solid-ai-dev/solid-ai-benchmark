# Base — Application Security

Apply these cross-cutting security rules to application code in every
project, regardless of language or framework.

The sections below cover the OWASP Top 10 categories: injection, broken
access control, cryptographic failures, insecure design, security
misconfiguration, vulnerable components, identification and authentication
failures, software and data integrity failures, logging and monitoring
failures, and server-side request forgery.

## Input validation

- Validate all external input at the system boundary — the first point
  where untrusted data enters the application
- Validate complex input with a schema validation library; never
  hand-write it
- Use an allowlist, not a blocklist — define what is valid, reject
  everything else
- Reject invalid input with a clear error; do not silently coerce or strip
  fields
- Do not repeat the boundary's schema validation in inner layers; a
  function still asserts the preconditions it relies on
