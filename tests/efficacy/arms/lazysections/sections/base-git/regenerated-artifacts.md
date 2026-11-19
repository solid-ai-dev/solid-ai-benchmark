# Base — Git Conventions

How changes are committed, reviewed, verified and merged.

## Regenerated artifacts

- Regenerate a derived artifact in the change that edits its source, and
  stage both together (MUST)
- Name the regeneration trigger beside the sources it derives from (MUST)
- Run the staleness comparison after the edit, and again after any merge
  that brings another branch's sources in (MUST)

```bash
<regenerate-command> || exit 1
git ls-files --error-unmatch -- <artifact-path> > /dev/null || exit 1
git diff --exit-code --stat -- <artifact-path>
```

- Read the staged copy as the baseline: the comparison runs before the
  commit, and in a clean checkout, such as CI's, the index is the commit
- Require a zero status; a failed regenerator, an artifact that is not
  staged and any diff each fail it
- Treat any diff as a staged artifact that does not match its sources
- Treat a regenerator that fails this on a current artifact as defective:
  it is not idempotent
- Summarise the visible impact before and after in the pull request body:
  a verdict matrix, a delta table, a screenshot diff
- Open a tracked follow-up naming the stale files, by name or glob, where
  regeneration is too expensive to bundle (MUST)
- Drop a regenerated file whose diff is line endings only:

```bash
git diff --ignore-cr-at-eol <file>
```

- Read an empty diff as noise, and drop the file with
  `git checkout -- <file>`
- Never drop a file on `--ignore-all-space`; it hides `"a b"` becoming
  `"ab"`
- Read any other whitespace-only diff before dropping it
- Open every regenerated binary artifact in a viewer or an image-read tool,
  and confirm it tracks its source
- Regenerate a known-current control artifact first; a non-zero diff there
  means the environment disagrees with the committed files
- Reconcile a non-zero control diff before committing anything regenerated
- Pair a spot-check of three to five representative artifacts with one
  population metric when a change regenerates many
