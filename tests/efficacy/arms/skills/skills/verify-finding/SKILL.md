---
name: verify-finding
description: Reporting a defect, a measurement or a claim, or acting on another agent's finding
---

# Reporting a defect, a measurement or a claim, or acting on another agent's finding

## From reading

- [ ] Reproduce the defect before reporting it: run the path
- [ ] Read a passing test that contradicts the reproduction before blaming
      the code; it may pin a decision

## From a measurement

- [ ] The tool measures the rule's unit: bytes are not characters
- [ ] The tool measured the claimed scope, not a diff, sample or partition;
      a whole-codebase claim comes from a whole-codebase run (MUST)
- [ ] The mode that produced each kept number is recorded beside it
- [ ] One flagged item was checked by hand
- [ ] Each count carrying a finding was produced twice, by different means
- [ ] A zero was checked by finding one positive by hand
- [ ] The tool fails loudly on unsupported input rather than exiting clean
      (SHOULD)

## From an extraction

- [ ] An element reported absent was checked against the raw artifact
- [ ] Extracted size was compared with the raw artifact, and known elements
      survived the round trip
- [ ] The claim is scoped to what was inspected: "not verifiable from the
      extract", never "missing"

## From a probe

- [ ] The probe ran under the conditions the finding is about, such as its
      user, credential and environment
- [ ] A claim the probe cannot make under those conditions is scoped to the
      ones it tested
