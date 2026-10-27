# 4. Solution strategy

The few ideas the rest of the architecture follows from. Each answers a
quality goal of chapter 1.

| # | Approach | Serves | How |
| - | -------- | ------ | --- |
| 1 | A paired, blocked experiment | Q1 | Every arm runs once per block, back to back, so arms in a block meet the same model on the same day. A contrast is K paired differences, not two means |
| 2 | A verdict computed, never read by eye | Q2 | `report.py` takes a bootstrap interval over the differences and applies the registered rule: better, worse, not shown, held |
| 3 | One script per stage, each with a self test | Q2, Q4 | `generate_arm`, `harness`, `score`, `security`, `judge`, `report`, `archive`. Each self test plants the fault it guards against and fails if it slips through |
| 4 | A trial runs alone, then freezes | Q3, Q5 | A scratch home, a cleaned environment, fenced file tools, a transcript scan. The workspace becomes a tarball before any scoring |
| 5 | Scoring stays outside the run root | Q3 | The scoring area sits beside the run root, so no trial is one `..` away from another's scores or the hidden suite |
| 6 | One ruler for every arm | Q1 | The tools run at versions locked on the first trial scored, under the harness's configuration, never the agent's |
| 7 | Missing is not zero | Q4 | A tool that saw no files, failed or timed out records the metric missing, with the reason |
| 8 | A blind, checked judge | Q1, Q4 | The bundle loses the context file and every arm marker. Each tree is judged three times. Every quoted line is looked up. A control fixture proves each row can move |
| 9 | Records over memory | Q5 | Run records, generation records, seeds, revisions and an archive with hashes. A report refuses to write without a verified archive |
| 10 | Refuse early | Q1, Q3 | A preflight prompt, a root inside the repository, an existing workspace, a missing arm file and a stale archive each stop the run before it costs money |

## 4.1 What the strategy rules out

- **Hand-tuning an arm.** Files are generated once per round and refused,
  not trimmed, when over budget.
- **Re-running failures.** A failed trial is scored as it stands. Only a
  trial the provider cut off is re-run, once.
- **Moving the bar.** A threshold or a metric added after results are seen
  lands in a separate section with no verdict.
- **Pooling rounds.** A contrast that pairs trials from different rounds
  keeps its mean and interval and gets no verdict.
