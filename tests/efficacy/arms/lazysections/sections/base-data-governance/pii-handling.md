# Base — Data Governance

Rules for data classification, retention, privacy, and ownership.
Applies to any project that stores or processes user data, business
data, or regulated information.

## PII handling

- Identify all personally identifiable information (PII) fields
  in the schema — name, email, phone, address, IP, device IDs
- Encrypt PII at rest and in transit (MUST)
- Minimize PII collection — do not store what you do not need
- Provide a mechanism to delete PII — hard delete or anonymize, never
  just soft-delete it
- Never put PII in application logs, error messages, or stack traces
  (MUST NOT); the audit trail is a separate store, not a log
- Keep the client IP, the one PII field a security log may hold, in that
  log alone, access-restricted and purged when its retention ends
- Mask or redact PII in non-production environments
