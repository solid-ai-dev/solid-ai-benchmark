# Base — Quality Attributes

How code is designed, kept clean, swept and checked.

## Deprecation and renames

- Deprecate a public symbol, naming its replacement, before a later change
  removes it
- Deprecate every part of one call site together, such as a method and its
  keyword arguments, or break the whole call; never alias the outer name
  alone
- Retire a concept by sweeping every surface that still instructs its use,
  tickets and plans included, until a search returns only historical
  records
