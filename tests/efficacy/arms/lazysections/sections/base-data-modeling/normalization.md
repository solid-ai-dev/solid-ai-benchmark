# Base — Data Modeling

Rules for schema design, naming, normalization, and relationships, in any
store: a relational database, a document store or a static data file.

## Normalization

- Give every table or collection a primary key — prefer surrogate keys for
  internal use, natural keys for external-facing APIs
- Store each fact in one place by default — duplicate it only when
  measured read performance requires it
- Never pack several values into one string field, such as
  comma-separated values — use a list or a related record
- Document the rationale when intentionally denormalizing
