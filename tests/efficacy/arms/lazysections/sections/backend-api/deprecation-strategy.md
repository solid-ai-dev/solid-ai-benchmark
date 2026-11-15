# Backend — API Design

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
