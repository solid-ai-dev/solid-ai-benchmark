---
name: migrate-data
description: Writing or running a schema migration, a data fix or a backfill
---

# Writing or running a schema migration, a data fix or a backfill

## Indexing

- Index every foreign key column — not every engine does so automatically
- Add composite indexes for common multi-column filter + sort combinations
- Avoid over-indexing write-heavy tables — each index adds write overhead
- Drop unused indexes — check the engine's index usage statistics
  regularly
