# BLS MCP evaluation lessons

Keep one Markdown file per confirmed failure pattern or investigated intervention,
using `BLS-001.md`, `BLS-002.md`, and so on. Copy `TEMPLATE.md` and retain
links to the immutable run IDs and Git commits. Do not commit full transcripts,
credentials, user data, or unreviewed tool payloads.

Separate **observation** from **hypothesis**. A model failure is not proof of
an MCP defect. Record the exact tool or behavior changed and the expected
outcome *before* making the change. After rerunning, record the new run ID,
score delta, regressions, and the decision to keep, revise, or revert.

Compare only like-for-like runs: matching eval fingerprints, case coverage,
snapshot, and compatible model and prompt configuration. If a grader or case
changes, start a new measurement series rather than claiming improvement.

Score history is generated from `results/runs/*/run.json` with
`uv run --locked poe eval-history`; it is not manually edited.
