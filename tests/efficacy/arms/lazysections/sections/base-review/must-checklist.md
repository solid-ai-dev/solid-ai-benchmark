# Base — Peer Review

How a change is reviewed, and how a finding is proven before it is reported.

## MUST checklist

- [ ] No credential, token or sensitive value appears in a committed file
- [ ] Every failure path is handled; no silent catch, no swallowed exception
- [ ] Every new dependency carries a licence the project's policy allows
- [ ] Significant logic and architectural decisions are documented
- [ ] Existing documentation matches the code after the change
- [ ] Every changed section was re-read whole, not only the changed line
- [ ] Every claim changed text makes about itself, such as a count or "all",
      was checked by counting with a tool
- [ ] Input from outside the process, such as a URL parameter, is
      validated as untrusted before it is destructured, indexed or used as
      a key
- [ ] A refactor preserves behaviour on every path: each case, direction and
      mode, including null handling, sort order and boundary values
