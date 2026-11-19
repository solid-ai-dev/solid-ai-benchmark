# Backend — HTTP Conventions

## Resource representation

- Make a text payload's field types conform to the relevant ISO standard
  (MUST):
  - Date and time values: ISO 8601
  - Language codes: ISO 639
  - Country codes: ISO 3166-1 alpha-2
  - Currency codes: ISO 4217
- Serialise any JSON integer outside ±(2^53 − 1), -9007199254740991 to
  9007199254740991, as a string (MUST); JavaScript cannot represent one
  beyond that range precisely, in either direction
- Reject non-finite values in an endpoint that serialises computed floats
  to JSON (MUST); `NaN`/`Infinity` are not valid RFC 8259 JSON
- Configure the JSON encoder to reject them, so it fails loud at the
  serialisation boundary (a 500) instead of emitting a bare `NaN` token
  that strict parsers reject
- Represent an undefined computed float in JSON as `null`, normalised
  before serialisation
- Document such a JSON field as nullable in the contract
- Return only the fields the caller needs (MUST); never pad a payload
  with fields that are not consumed
