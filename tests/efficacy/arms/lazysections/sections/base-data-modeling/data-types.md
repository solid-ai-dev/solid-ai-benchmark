# Base — Data Modeling

Rules for schema design, naming, normalization, and relationships, in any
store: a relational database, a document store or a static data file.

## Data types

- Use the most specific type the store offers — a date type, not a
  string, for dates
- Store timestamps in UTC — convert to local time at the
  presentation layer
- Store monetary values as integers in minor units or as a decimal type —
  never floating point
- Use `UUID` or `ULID` for distributed ID generation — auto-increment
  is acceptable for single-database systems
- Document a maximum length for every text field (MUST); unbounded text
  invites abuse and complicates indexing
