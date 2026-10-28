# MP4 program — state & session protocol

*The working ledger for executing `what.md` phase by phase, one phase per
session. Every session reads this file first and updates it last. If this
ledger and the repo disagree, **the repo wins** — stop and report the
divergence instead of guessing.*

---

## Session protocol

Carried by the `program-builder` skill (`next` mode). In short: get on the
`mp4-program` branch → verify the ledger against the repo → take the first
runnable row → implement only that → run the floor plus the phase's checks and
record real output → update this doc → commit → **do not push** (commit-only
program) → report on that phase only.

## Standing priorities (apply to every phase, in order)

1. The generated Rust under `MP4/translations/` is never edited by a human or
   by a session. Only prompts and orchestration change, logged in
   `MP4/configs/CHANGELOG.md`, then the pipeline reruns. The provenance check
   enforces this.
2. Every number in README, results and report is generated from committed
   artifacts and reproducible with `run_pipeline.py --check-only`. Nothing is
   typed in by hand or invented; unknown values are marked PENDING.
3. Benchmark tests, interfaces, `Cargo.toml` and `Cargo.lock` are immutable and
   guarded by checksums in code.
4. Owner-blocked work stays in M12-M14. Nothing earlier waits on it.
5. Trajectories are complete, per-iteration, scrubbed, and prove the loop was
   feedback-driven.

## Ratified decisions

*Settled by the owner on 2026-10-28. Do not reopen. Full text: `why.md` § D.
If implementation reveals a settled decision is unworkable, stop and report
the specific conflict rather than picking an alternative.*

- D1 agent B = Claude Code headless, opus, effort high.
- D2 branch `mp4-program`, commit-only, never push.
- D3 owner-blocked rows last.
- D4 reviews = rubric validation + bug hunt.
- D5 no manual Rust repair; guards in code; CHANGELOG.
- D6 interim safety proxy; course tool as second backend.
- D7 spend envelope pre-authorized (see `program.yaml` spend_surface).
- D8 `read_test_vector` known-failing; owner raises with staff.
- D9 cut-off 2026-11-15 for M12/M13.
- D10 Jacob and Ross polish report prose.
- D-ALLOW, D-CLIMAIN, D-FAITHFUL, D-FORBID, D-TRAJ, D-DIAGRAM: defaults, confirmed at the M3 gate.

## Phase ledger

| ID | Phase | Status | Session / commit | Notes |
|---|---|---|---|---|
| M1 | MP4 layout, subjects, toolchain, baselines | **not-started** | — | — |
| M2 | Checks library, integrity guards, self-test | **not-started** | — | — |
| M3 | Configs, prompts, agent runner, smoke run | **not-started** | — | — |
| M4 | Iteration loop, stop logic, resume drills, README draft | **not-started** | — | — |
| M5 | Review 1: pipeline vs rubric, guard test, traceability | **not-started** | — | — |
| M6 | Full run: project_1 (satc) | **not-started** | — | — |
| M7 | Full run: project_2 (libpsbt) | **not-started** | — | — |
| M8 | Review 2: translations and trajectories vs rubric | **not-started** | — | — |
| M9 | Tuning rerun | **optional — owner-triggered** | — | Flipped to not-started by the M8 session only if the owner chooses a rerun at the M8 gate; otherwise set `dropped (owner accepted M6/M7 results)` |
| M10 | Results, README final, report draft | **not-started** | — | — |
| M11 | Review 3: fresh-clone rubric walk, consistency, submittable as-is | **not-started** | — | — |
| M12 | Course unsafe-metrics tool: adapter, retroactive run, table swap | **blocked (course unsafe-metrics tool not yet released; owner drops it at the path named in the runbook and flips this row to not-started)** | — | Cut-off 2026-11-15 (D9) |
| M13 | Course validation script run, structural fixes | **blocked (course validation script not yet released; owner drops it at the path named in the runbook and flips this row to not-started)** | — | Cut-off 2026-11-15 (D9) |
| M14 | Review 4: Overleaf placement check, merge handoff | **blocked (Overleaf export not yet supplied; owner pastes the .tex from M10 and exports the PDF to MP4/docs/)** | — | Depends on M10; M12/M13 done or dropped |

> Sequencing note for `next`: rows M1-M11 are the unblocked spine. When the
> first runnable row is M12 and it is still `blocked`, the session reports
> what it is blocked on and stops (per protocol). The owner flips a blocked
> row to `not-started` when its input is in place, or to `dropped (...)` after
> 2026-11-15.

## Phase log

*One entry per completed phase, appended in the phase's final commit.*

## Owner-action queue (only the owner can clear these)

> **Running these? Use `runbook.md`.** It is the same items in DEPENDENCY
> order with the exact commands. This queue is the per-item record of what is
> outstanding and why.

| # | Item | Why it exists | Blocks | Status |
|---|---|---|---|---|
| O1 | Post the `read_test_vector` defect (why.md H-L1) on the course forum, together with the question of when/where the unsafe-metrics tool and validation script will be released. Draft ready at `docs/programs/mp4/forum-post-draft.md` | D8; a staff ruling may lift the 3/4 ceiling; O3/O4 depend on the release | nothing in M1-M11 (ruling is injected whenever it arrives) | **deferred by owner 2026-10-28**: MP3 has not reached its due date, so MP4 is not formally open; Joseph will check for news and post once MP4 opens. Every session must treat D8 as the working assumption and must flag this item in its report until it is resolved. **Must be resolved or consciously accepted before submission.** |
| O2 | Approve the rustup + nightly-2025-05-13 install in the M1 session (commands shown first) | E2; invariant 4 | M1 | open |
| O3 | Supply the course unsafe-metrics tool at the path the runbook names, then flip M12 to not-started | R-T3-*-SAFETY official numbers, R-T4-SAFETY-ANALYSIS | M12 | open (cut-off 2026-11-15); not yet released by the course as of 2026-10-28; owner checks periodically |
| O4 | Supply the course validation script at the path the runbook names, then flip M13 to not-started | Z11, Z16 | M13 | open (cut-off 2026-11-15); not yet released by the course as of 2026-10-28; owner checks periodically |
| O5 | After M10: paste `MP4/docs/report_mp4_draft.tex` into Overleaf, compile, export the PDF to `MP4/docs/CS598JBR_Report_Team_1.pdf` (gitignored), flip M14 to not-started | R-T4-* | M14 | open |
| O6 | Stay logged in (`claude auth status`) and keep the Mac awake (`caffeinate -dims`) during M3, M6, M7, M9 | D7 auto-resume | M3, M6, M7, M9 | open |
| O7 | After the program reports ready-to-merge: merge `mp4-program` into `main` with a merge commit and push `main` before 2026-11-18 23:59 | invariant 6/7 | submission | open |
