# Backend — Database Conventions

## Soft deletes

- Use soft deletes (`deleted_at` timestamp) only when audit history is
  required; otherwise use hard deletes
- If using soft deletes, filter deleted rows out of every query by
  default — never return deleted rows to callers
- Keep an append-only audit log table instead of soft deletes (MAY)
