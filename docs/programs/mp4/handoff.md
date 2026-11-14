# MP4 program — merge and submission handoff

*Written by M14 (2026-11-14). For the owner. This file says what to do at the
end; `runbook.md` Stage 5 has the same commands in dependency order.*

## Do not merge yet

**The merge happens only after both of these are true:**

1. Ledger row **M13** (course validation script) is `done` or `dropped` in
   `where.md`. It is `blocked` today: the script is not in the course
   repository as of 2026-11-14. From 2026-11-17 a session marks it `dropped`.
2. A `/mp4-phase` session has reported **ready-to-merge** (`program.yaml`
   `state: ready-to-merge`).

Still to run before that, one `/mp4-phase` session each: **M16** (the full
code review), any remediation row M16 adds, **M13**, then the short closing
check. If M16 or M13 changes anything a grader reads, that session re-runs
the affected rows of `reviews/review-4.md` and updates this file.

## What the branch holds (verified at M14)

Evidence: `reviews/review-4.md`, fresh clone of `mp4-program`.

| | satc (project_1) | libpsbt (project_2) |
|---|---|---|
| Builds with `nightly-2025-05-13` | Yes | Yes |
| Benchmark tests | 4 of 4 | 3 of 4 (`read_test_vector` is the documented defective test) |
| Clippy, agent-written code (correctness / style / complexity / perf) | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| Unsafe metrics, course tool (lines / calls / casts / pointer arithmetic) | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| Agent iterations, stop reason | 2, SUCCESS | 2, SUCCESS |

Not verified by anyone yet: the course validation script (not released).

## Step 1 — write the report (yours, by hand, any time before the deadline)

The MP4 section of the progress report is written by the team in Overleaf. It
is 70 of the 430 points (six rubric rows). Write it from the local draft:

- `MP4/docs/report_mp4_draft.md` (read this one)
- `MP4/docs/report_mp4_draft.tex` (same text in LaTeX; never compiled)

Both are gitignored and stay on this machine. The draft ends with a list,
"Check these when writing it by hand". The three that matter most:

- The staff ruling of 2026-11-13 **requires** the `read_test_vector` issue to
  be documented in the report's discussion section. The draft has the
  paragraph ("Discussion: the defective `read_test_vector` test").
- libpsbt is 3 of 4. That 3 of 4 earns full correctness credit is the team's
  assumption (why.md D-CREDIT), not something staff said.
- Name the course tool (`newmetrics` 0.1.0, commit `4597e75`) with the safety
  table.

## Step 2 — merge and push (only after "ready-to-merge")

From the repository root. The branch is already on the remote; sessions
pushed it. Only the merge and `main` are yours.

```bash
git checkout mp4-program && git pull --ff-only origin mp4-program
```

```bash
git status --short
```

The second command must print nothing. Then:

```bash
git checkout main && git pull --ff-only origin main
```

```bash
git merge --no-ff mp4-program -m "Merge mp4-program: MP4 agentic C-to-Rust translation (Group 1: satc, libpsbt)"
```

```bash
git push origin main
```

Merge commit, **never squash**: the phase commits are the record that the
Rust was produced by the pipeline and not edited by hand. If
`git pull --ff-only origin main` or the merge reports a conflict, stop and
start a session; do not resolve it by hand under time pressure.

## Step 3 — check what graders will clone

In a new directory next to the repository, cloned from the remote, so nothing
local can hide a missing file. Run the first command from the repository
root:

```bash
git clone "$(git remote get-url origin)" ../mp4-submission-check && cd ../mp4-submission-check
```

```bash
python3 -I MP4/src/run_pipeline.py --project project_1 --check-only && python3 -I MP4/src/run_pipeline.py --project project_2 --check-only
```

```bash
python3 -I MP4/src/integrity.py --provenance project_1 && python3 -I MP4/src/integrity.py --provenance project_2
```

Expected: exit 0 for all four, tests 4 of 4 and 3 of 4, `"safety_tool":
"both"`, provenance `"ok": true`. (`--check-only` rewrites
`MP4/results/project_N.check.json` with a new timestamp; that is normal. Do
not commit it from this check clone.)

## Submission checklist

- [ ] M13 is `done` or `dropped`, and a session reported **ready-to-merge**.
- [ ] The MP4 report section is written by hand from the local draft, and the
      discussion section documents `read_test_vector`.
- [ ] The report's numbers equal `MP4/results/results.md` (4/4 and 3/4,
      2 iterations each, clippy 0/0/0/0, unsafe metrics 0/0/0/0).
- [ ] `main` has the merge commit (not a squash) and is pushed.
- [ ] A fresh clone of `main` contains `MP4/src`, `MP4/configs`,
      `MP4/trajectories/project_1`, `MP4/trajectories/project_2`,
      `MP4/translations/project_1`, `MP4/translations/project_2` and
      `MP4/README.md`, and Step 3 exits 0.
- [ ] No PDF, report draft or API key is in the repository
      (`git ls-files | grep -iE '\.pdf$|report_mp4_draft'` prints nothing).
- [ ] The report PDF is submitted where the course asks for it. The handout
      is the authority on where; this program did not verify the submission
      channel.
- [ ] All of it before **2026-11-18 23:59**.

## Known and accepted

- libpsbt 3 of 4 on the provided tests, by staff ruling (where.md O1).
- Staff did not say whether Project 2 has additional grading tests; nothing
  was built for that (why.md D-CREDIT).
- `MP4/configs/pipeline.yaml` differs from the copy hashed in the two runs'
  `run_manifest.json` in its `safety` block only: the course tool was added
  after the runs (`MP4/configs/CHANGELOG.md`, 2026-11-11). The other seven
  configuration files are the ones the runs used.
- Post-merge backlog: `post-merge.md`. Nothing in it blocks the merge.
