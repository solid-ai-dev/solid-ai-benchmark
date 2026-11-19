# Base — Peer Review

How a change is reviewed, and how a finding is proven before it is reported.

## SHOULD checklist

- [ ] Each non-trivial function has a unit test per relevant variant
- [ ] Coverage does not fall
- [ ] Lint errors and warnings do not rise
- [ ] Each third-party dependency is necessary, understood and maintained
- [ ] No new abstraction without two call sites, and no new dependency
      without a documented reason
