# Base — Peer Review

How a change is reviewed, and how a finding is proven before it is reported.

## Verifying a finding

- Label a finding unverified until it is demonstrated (MUST)

### From reading

- [ ] Reproduce the defect before reporting it: run the path
- [ ] Read a passing test that contradicts the reproduction before blaming
      the code; it may pin a decision

### From a measurement

- [ ] The tool measures the rule's unit: bytes are not characters
- [ ] The tool measured the claimed scope, not a diff, sample or partition;
      a whole-codebase claim comes from a whole-codebase run (MUST)
- [ ] The mode that produced each kept number is recorded beside it
- [ ] One flagged item was checked by hand
- [ ] Each count carrying a finding was produced twice, by different means
- [ ] A zero was checked by finding one positive by hand
- [ ] The tool fails loudly on unsupported input rather than exiting clean
      (SHOULD)

### From an extraction

- [ ] An element reported absent was checked against the raw artifact
- [ ] Extracted size was compared with the raw artifact, and known elements
      survived the round trip
- [ ] The claim is scoped to what was inspected: "not verifiable from the
      extract", never "missing"

### From a probe

- [ ] The probe ran under the conditions the finding is about, such as its
      user, credential and environment
- [ ] A claim the probe cannot make under those conditions is scoped to the
      ones it tested

### From an agent

- Check an agent's finding against the file, commit or document that
  settles it before acting on it or repeating it
- Distinguish a verified negative from a failed lookup, and say which
- Count a finding several agents agree on as one finding
- Correct a finding you passed on that proves wrong, and name what the
  check showed
- Reconcile a finding with a verified record it contradicts before
  changing anything: confirm both read the same artifact, prefer the more
  specific evidence, and record the outcome
- Record a reversal of a documented decision, with its reason, in the
  artifact that documented it
- Give a verifying agent the existing record and ask it to reconcile, not
  re-derive
- Never delete a record because a check "could not confirm" it (MUST NOT)
