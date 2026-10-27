# Register a hypothesis

The owner has read round 4's report and wants to know whether a short root
file with task skills delivers what the hybrid file does. Target: the
question, its one primary measure, its threshold and the result that
refutes it, committed to the design before any trial of the round runs.

Assumptions: the round's arms are new, so the harness owes work before the
first trial. Minutes are estimated from writing round 5's section 13.

| # | Step | Minutes | Notes |
| - | ---- | ------- | ----- |
| 1 | Reads the last report and the assessment, and names what they could not show | 30 | Round 4: both hypotheses supported on a few rows, escalation owed |
| 2 | Writes the question and what varies, one knob inside a block | 20 | Round 5: the arm varies, each block moves one setting from block A |
| 3 | Picks each hypothesis's contrast, primary rows and the supported and refuted readings, from the design's registered margins | 30 | No new threshold. A new one would need its own reason |
| 4 | Lists the secondary measures, which are reported without a verdict | 10 | Every metric of section 5, worst trial beside mean, cost |
| 5 | Lists the harness work owed before the first trial, each with a self test | 15 | Round 5's section 13.4 |
| 6 | Opens a pull request to the design and merges it | 10 | Before any trial of the round |
| | Total | about 2 hours | |

## Findings

| # | Finding | Status |
| - | ------- | ------ |
| 1 | Nothing in the code checks that a round's hypothesis was committed before its first trial. The order rests on the design's date line and git history | Open |
| 2 | A hypothesis decides a record in another repository, such as ADR-058 in `solid-ai-templates`. The design names it, and the record cites the report | Settled in design §13 |
| 3 | A hypothesis on agreement across trials has one value per arm, so no interval. Its result is descriptive | Settled in design §12.1 |
| 4 | Once a round's trial has run, its section may not change | Settled in design §13.4 |
