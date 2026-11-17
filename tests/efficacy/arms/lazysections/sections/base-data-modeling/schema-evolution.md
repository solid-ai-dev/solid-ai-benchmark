# Base — Data Modeling

Rules for schema design, naming, normalization, and relationships, in any
store: a relational database, a document store or a static data file.

## Schema evolution

- Run every schema change through a versioned migration (MUST); never
  change a production schema by hand
- Prefer additive changes, such as a new field, table or collection
- Keep an additive change compatible with old writers: add a field
  optional or with a default, never required without one where records
  exist
- Give every destructive change (drop or rename a field) a migration plan:
  add new → migrate data → drop old (MUST)
- Include both up and down steps in every migration (MUST)
- Say so where a down step cannot restore the data, and get approval
  before applying that migration
- Test migrations against a production-like dataset before deploying
