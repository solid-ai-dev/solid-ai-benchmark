# Base — Data Governance

Rules for data classification, retention, privacy, and ownership.
Applies to any project that stores or processes user data, business
data, or regulated information.

## Retention

- Define a retention policy for each data category — document
  how long data is kept and when it is purged
- Meet every regulation that applies to the data in each retention
  period (MUST)
- Implement automated purging — do not rely on manual cleanup
- Apply retention policies to audit logs and backups too
- Never retain backups indefinitely
- Document the purge mechanism: soft delete → hard delete after
  N days, or direct hard delete
