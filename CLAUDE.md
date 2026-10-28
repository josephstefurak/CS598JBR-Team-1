# CS598JBR-Team-1

Course repository for CS598JBR machine problems. MP1-MP3 are complete
(Python scripts, logs and datasets under `MP1/`, `MP2/`, `MP3/`). MP4 is in
progress under `MP4/` and is built by the program below.

## MP4 program (2026-10-28 →)

The MP4 C-to-Rust agentic translation pipeline runs **one phase per session**
against the ledger in `docs/programs/mp4/where.md`. Per-phase specs:
`docs/programs/mp4/what.md`. Findings, rubric keys and decisions:
`docs/programs/mp4/why.md`. Manifest: `docs/programs/mp4/program.yaml`.

When asked to continue it (`/mp4-phase`, "do the next phase", "continue the
MP4 program"): the `program-builder` skill carries the protocol. Implement
exactly the first runnable row to its spec, honor its listed **owner gates**
(ask, never assume), then update the ledger and phase log, commit, and report
on that phase only.

MP4 work lives on the **`mp4-program` branch**. This program is
**commit-only**: no session pushes any ref, ever. The owner merges
`mp4-program` into `main` with a merge commit (never squash) and pushes `main`
themself before 2026-11-18 23:59.

Rules that hold in every session touching MP4:

- **Never edit generated Rust** under `MP4/translations/`. Only prompts and
  orchestration change (logged in `MP4/configs/CHANGELOG.md`), then the
  pipeline reruns. `integrity.py --provenance` enforces this.
- **Benchmark tests, interfaces, `Cargo.toml`, `Cargo.lock`** under
  `MP4/subjects/` and the copies in `MP4/translations/` are immutable.
- **Spend**: `run_pipeline.py --project ...` consumes the owner's Claude
  subscription quota. It is pre-authorized only within the envelope recorded in
  `program.yaml` `spend_surface` (<= 8 iterations x 60 turns per run, 2 full
  runs, 2 tuning reruns, 3 smoke calls, model opus). Anything beyond that is an
  owner gate. `/code-review ultra` is billed and never launched by a session.
- **Secrets**: never commit API keys or tokens; `scrub_secrets.py --check MP4/`
  runs before every commit touching trajectories. `MP4/docs/*.pdf` stays
  gitignored.
- **Headless agent B** (`claude -p` spawned by the pipeline) must not see this
  file: the pipeline sets `CLAUDE_CODE_DISABLE_CLAUDE_MDS=1` and asserts
  isolation from the `system/init` line on every call.
