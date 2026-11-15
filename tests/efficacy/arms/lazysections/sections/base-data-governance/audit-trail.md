# Base — Data Governance

Rules for data classification, retention, privacy, and ownership.
Applies to any project that stores or processes user data, business
data, or regulated information.

## Audit trail

- Log every change to confidential and restricted data (MUST):
  who changed what, when, and the previous value
- Never record a credential's or secret's value in the audit trail, old or
  new (MUST NOT); record that it changed, who changed it and when
- Record a PII field's change the same way, without its values, so
  deleting the PII leaves no copy in the append-only trail
- Keep the audit trail in its own store, never in application logs,
  with access restricted to the tier of the data it records
- Make audit logs append-only (MUST); never let application code edit
  or delete them
- Include the actor (user ID or service identity), timestamp,
  action (create, update, delete), and affected record
