# Base — Peer Review

How a change is reviewed, and how a finding is proven before it is reported.

## Priority order

Review in this order, most critical first. The quality rules, and any
language quality rules the project carries, are the standard for items 2
to 4.

1. **Security**: anything exploitable, any credential or licence problem
2. **Correctness**: wrong results, unhandled failures, race conditions
3. **Clarity**: obscure names, deep nesting, high cognitive complexity,
   boolean flag parameters
4. **Conventions**: deviations from the project's agreed patterns

The order above is by area; weigh each finding separately.

- Label each finding a demonstrated defect, a deviation from a policy the
  project adopted, or a suggestion
- Block a merge only on a defect or a policy deviation; leave a
  suggestion to the author
