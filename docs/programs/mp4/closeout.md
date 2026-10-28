# Closing out the MP4 program

*Owner-facing summary. **The protocol is not duplicated here** — it lives in
`~/.claude/skills/program-builder/references/close.md` and is read live, so
improvements to it reach this program without this file changing. Values for
this program are in `docs/programs/mp4/program.yaml`.*

Companion docs: `what.md` (the specs each phase was built to), `why.md` (why
each phase existed), `where.md` (the ledger and phase logs the review holds
the code against).

---

## You do not run this manually

Closeout is automatic. Keep invoking `/mp4-phase` (or `/program-builder next
mp4`). When the ledger runs out of build rows, the next invocation moves the
program into review on its own and tells you what it found. Keep going until a
session reports the program **ready to merge**.

The close is **capped**: pass 1 reviews everything and auto-fixes the
mechanical findings; pass 2 re-checks only the fixes; pass 3 runs only if pass
2 fixed something critical. Real-but-minor findings go to
`docs/programs/mp4/post-merge.md`, a backlog that never blocks the merge.

**Program-specific caution for the close:** `/code-review max --fix` must
never touch `MP4/translations/`. The floor's `integrity.py --provenance`
fails if it does; the session reverts those hunks and logs the finding as a
prompt/orchestration proposal instead.

## Moment 1 — one batch of decisions

Pass 1 ends by asking you every decision it needs in one sitting. Answer, or
reshape the list. Nothing gated gets fixed until you do.

## Moment 2 — the merge

A session never opens a PR, never merges, never pushes. When one reports ready
to merge, it hands you `docs/programs/mp4/handoff.md`. Then, per the runbook
Stage 5: merge `mp4-program` into `main` with a merge commit and push `main`
yourself before 2026-11-18 23:59.

## If you want a deeper review than the automatic one

`/code-review ultra` is cloud-hosted and **billed separately**, which is why
no session launches it. Trigger it yourself if you want it.
