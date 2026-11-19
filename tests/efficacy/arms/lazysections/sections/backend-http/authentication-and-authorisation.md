# Backend — HTTP Conventions

## Authentication and authorisation

- Serve all API traffic over HTTPS outside local development (MUST);
  plain HTTP is not acceptable in staging or production
- Give access tokens a short, finite lifetime (MUST)
- Enforce both authentication and authorisation on every external API
  endpoint (MUST), except a public endpoint the project declares
- Make a public endpoint only a declared read, or a declared write that
  must run before the caller has an identity, such as a sign-up, sign-in,
  account recovery or a contact form
- Declare each public endpoint in the route definition and the API
  contract, in the change that makes it public; a public catalogue stays
  public, the account records beside it stay protected
- Require authentication at minimum on internal API endpoints (SHOULD)
- Never make any other write endpoint accessible without a valid
  authenticated identity (MUST NOT)
- Apply authentication and authorisation before any business logic runs
- Rate-limit each public endpoint per client — never expose an unbounded
  write operation
- Return no account data from a public write
- Rate-limit a sign-in or recovery endpoint per account and per client
- Answer a sign-up or recovery request the same way, in content and
  timing, whether or not the account exists
- Make each recovery token single-use, short-lived and bound to one account
