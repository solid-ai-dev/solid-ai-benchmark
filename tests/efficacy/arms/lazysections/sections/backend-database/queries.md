# Backend — Database Conventions

## Queries

- Parameterise every query that takes a value; never build a query by
  string interpolation
- Bound every query an interactive request runs with a limit or
  pagination; a filter alone is no bound, since a filter on a flag can
  still match millions of rows
- Stream or batch a deliberate export or batch scan, never load it whole
- Select only the columns or fields the code uses — never every column by
  default
- Fetch related data for a set of rows in one query or batch, never one
  query per row in a loop (N+1)
