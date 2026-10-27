---
name: deprecate
description: Deprecating, renaming or removing a public name, an endpoint or a template
---

# Deprecating, renaming or removing a public name, an endpoint or a template

## Deprecation and renames

- Deprecate a public symbol, naming its replacement, before a later change
  removes it
- Deprecate every part of one call site together, such as a method and its
  keyword arguments, or break the whole call; never alias the outer name
  alone
- Retire a concept by sweeping every surface that still instructs its use,
  tickets and plans included, until a search returns only historical
  records

## Deprecation strategy
When a breaking change is introduced:

1. Deploy the new version alongside the old one
2. Add the `Deprecation` header to all responses from the old version with
   the Unix timestamp of when deprecation started:
   `Deprecation: @<unix-timestamp>`
3. Optionally add the `Sunset` header with the planned removal date:
   `Sunset: <HTTP-date>`
4. Notify all consumers and agree on a migration timeline
5. Remove the old version only after the sunset date has passed; without
   a `Sunset` header, only after the timeline agreed in step 4 ends
