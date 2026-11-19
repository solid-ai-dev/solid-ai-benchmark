# Base — Data Governance

Rules for data classification, retention, privacy, and ownership.
Applies to any project that stores or processes user data, business
data, or regulated information.

## Data classification

- Classify every data field into one of four tiers:
  - **Public** — safe to expose (product names, documentation)
  - **Internal** — business-sensitive, not for external use
    (internal metrics, cost data)
  - **Confidential** — restricted access (customer PII, financial
    records, API keys)
  - **Restricted** — highest sensitivity (passwords, payment card
    data, health records)
- Document the classification in the schema or data dictionary (MUST)
- Match access controls to the classification tier (MUST)
- Grant confidential and restricted data only to the roles or identities
  that need it
