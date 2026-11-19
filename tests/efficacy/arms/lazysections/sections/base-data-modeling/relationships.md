# Base — Data Modeling

Rules for schema design, naming, normalization, and relationships, in any
store: a relational database, a document store or a static data file.

## Relationships

- Never rely on application code alone to keep references valid
- Enforce valid references with the store's own constraint where it has
  one, else with a check that every reference resolves
- Decide for every reference what deleting its target does:
  - delete the referencing records for strong ownership
  - clear the reference for a weak one
  - refuse the delete when an orphan indicates a bug
- Keep a record apart, referenced by key, unless it has no life outside
  its parent
- Document a self-referencing relationship's (e.g. `parent_id`) maximum
  depth and cycle prevention strategy (MUST)
