# Base — Application Security

Apply these cross-cutting security rules to application code in every
project, regardless of language or framework.

The sections below cover the OWASP Top 10 categories: injection, broken
access control, cryptographic failures, insecure design, security
misconfiguration, vulnerable components, identification and authentication
failures, software and data integrity failures, logging and monitoring
failures, and server-side request forgery.

## Deserialization and data integrity

- Never deserialize untrusted data with a format that can instantiate
  arbitrary types; use a data-only format such as JSON
- Validate the structure and types of deserialized data before use; treat
  it as untrusted input
- Verify integrity of downloaded artifacts, updates, and dependencies; use
  checksums or digital signatures
- Pin dependency versions and verify checksums in lockfiles; do not trust
  upstream registries blindly
- Use pinned, verified steps and images in CI/CD pipelines (MUST)
- Never pull `latest` tags in production CI/CD pipelines
