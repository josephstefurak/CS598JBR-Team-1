# MP4 program — owner runbook

*What Joseph runs or supplies, in dependency order, with exact commands.
The owner-action queue in `where.md` records what is outstanding and why;
this file is how you work through it. Sessions append to this file as
phases queue new items.*

---

## Stage 0 — every session

```bash
cd /Users/josephstefurak/CS598JBR-Team-1
git checkout mp4-program
```

Then invoke `/mp4-phase` in Claude Code (or `/program-builder next mp4`).
One phase per session. Answer the gates it asks. Sessions push `mp4-program`
themselves (since 2026-11-11); you never need to, and nobody pushes `main`
until Stage 5.

## Stage 1 — before or during M1

**O2 — toolchain install. DONE 2026-10-28 (M1 session, owner yes in
session).** Installed to `~/.rustup` / `~/.cargo`; versions in
`MP4/docs/environment.md`. Commands as run (installer saved to a file, not
piped):

```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs -o rustup-init.sh
sh rustup-init.sh -y --no-modify-path --profile minimal --default-toolchain none
~/.cargo/bin/rustup toolchain install nightly-2025-05-13 --profile minimal --component clippy
```

**Still yours:** `--no-modify-path` means no shell profile was changed. Put
`~/.cargo/bin` on PATH in the shell that launches Claude Code (headless agent B
children inherit it), e.g. add to `~/.zshrc`:

```bash
export PATH="$HOME/.cargo/bin:$PATH"
```

To remove the toolchain entirely later: `~/.cargo/bin/rustup self uninstall`.

**O1 — the `read_test_vector` question (RESOLVED 2026-11-13).** The owner
asked on CampusWire; staff replied: implement the correct Rust behavior
corresponding to the original C implementation, do not modify the provided
tests, and document the issue in the discussion section of the report (full
text in `where.md` O1). That is what D8 already does, so nothing in the
pipeline or `MP4/configs/projects/project_2.yaml` changes and libpsbt stays
3/4 on the provided tests. Left for the owner: the hand-written report's
discussion section must describe the defect (the local draft carries
recommended wording after M14). Staff did not say whether 3/4 earns full
credit or whether Project 2 has additional grading tests.

## Stage 2 — during M3, M6, M7, M9 (runs that spend quota)

**O6 — stay logged in and awake.**

```bash
claude auth status
```

```bash
caffeinate -dims
```

Leave the second command running in a terminal for the duration of the run.
Check remaining plan quota in an interactive `claude` session with `/usage`
before M6 and M7.

**O8 — keep the Claude CLI logged in (DONE 2026-10-29).** The `claude` CLI
keeps its own login, separate from the desktop app. It was logged out, so the
first smoke attempt failed with "OAuth session expired". Fixed by running, in
your own terminal:

```bash
claude auth login
```

Before M6, M7 and M9, check that `claude auth status` shows `"loggedIn": true`.
(An earlier version of this note blamed the session sandbox. That was wrong:
once the CLI was logged in, the session shell could use it.)

**O9 — the M6 gate batch (from M5, 2026-10-29).** The M6 session starts by asking seven questions
(G1–G7) about stop rules and the agent's permissions. Each has options and a recommendation in
`docs/programs/mp4/reviews/review-1.md` § "Owner decisions for M6 step 1". Read that section before M6;
nothing in M6 starts until they are answered. **Answered 2026-10-29** (see where.md O9); M6 applies them.

**Optional — temp-dir leftovers.** Before M5's fix, every safety check left a crate copy in your temp
directory (87 found on 2026-10-29, about 75-100 MB; macOS also purges them on its own). To see them and,
if you want, remove them:

```bash
ls -d "$TMPDIR"/mp4crate_* | wc -l
```

```bash
rm -rf "$TMPDIR"/mp4crate_*
```

**Behaviour to know before M6 (M5 fixes).** A new run is refused while another run of the same project is
still open (running, paused or interrupted): continue it with `--resume-run`. A resume is refused if the
configuration changed since the run started, or if `claude auth status` is logged out. After three refused
usage-limit attempts on one iteration the run exits with code 75 instead of waiting again.

## Stage 3 — course tools (rewritten 2026-11-11)

**O3 — unsafe-metrics tool. CLEARED.** Released 2026-11-09 at
`https://github.com/Intelligent-CAT-Lab/CS598JBR-Team-0` (`MP4/newmetrics/`).
You pre-approved the install on 2026-11-11 (why.md D-TOOL); the M12 session
does it. **Installed 2026-11-11 (M12)** with the staff command as written; the
clone is at `~/cs598jbr-course-tools/CS598JBR-Team-0` (commit `4597e75`), and
`MP4/configs/pipeline.yaml` `safety.course_aggregate` points at its
`aggregate.py`. Keep the clone while you run `--check-only`. To remove the
tool later (then also delete the clone):

```bash
cargo uninstall newmetrics
```

```bash
rustup component remove rustc-dev llvm-tools-preview --toolchain nightly-2025-05-13
```

**O4 — validation script.** Not released as of 2026-11-11. When it appears,
put it at `MP4/tools/validate/` or tell a session its path; the session flips
M13 to `not-started`. From **2026-11-17** a session marks M13
`dropped (course validation script not released by the 2026-11-17 cut-off)`.
Since 2026-11-14 M13 is the last build row: the final review (M14) and the
full code review (M16) run before it, so when the script arrives the rest is
two short `/mp4-phase` runs (validate, then a scoped closing check) and your
merge. As of 2026-11-14 the script is still not in the course repo.

## Stage 4 — the report (yours, by hand)

**O5 is superseded (2026-11-11).** The team writes the MP4 section in
Overleaf by hand. **M14 (2026-11-14) finished the local draft**:
`MP4/docs/report_mp4_draft.md` and `.tex` (gitignored, never committed), with
the official safety numbers, generated tables, four cited repair examples,
the five reflection answers, the recommended discussion paragraph on
`read_test_vector` (required by the staff ruling) and a closing list "Check
these when writing it by hand". Write the report from it; do not paste it
unread. The `.tex` has never been compiled; its first lines name what the
preamble needs (`\usepackage{tikz}`,
`\usetikzlibrary{positioning,arrows.meta,shapes.geometric}`). No session
waits for an export. The report can be written at any time; it does not wait
for the merge.

## Stage 5 — after the program reports ready-to-merge (final section)

**O7 — merge and push.** Full text and the submission checklist:
`docs/programs/mp4/handoff.md`. Not before **both**: M13 is `done` or
`dropped`, and a session has said **ready-to-merge**. Until then keep
invoking `/mp4-phase` (next: M16, the full code review; then M13 when the
validation script exists or on 2026-11-17; then the short closing check,
which only covers what changed after M16).

The branch is already on the remote; only the merge and `main` are yours.
From the repository root, in this order:

```bash
git checkout mp4-program && git pull --ff-only origin mp4-program
```

```bash
git status --short
```

That must print nothing. Then:

```bash
git checkout main && git pull --ff-only origin main
```

```bash
git merge --no-ff mp4-program -m "Merge mp4-program: MP4 agentic C-to-Rust translation (Group 1: satc, libpsbt)"
```

```bash
git push origin main
```

Merge commit, never squash. If a pull or the merge reports a conflict, stop
and start a session. Then check what graders will clone:

```bash
git clone "$(git remote get-url origin)" ../mp4-submission-check && cd ../mp4-submission-check
```

```bash
python3 -I MP4/src/run_pipeline.py --project project_1 --check-only && python3 -I MP4/src/run_pipeline.py --project project_2 --check-only
```

```bash
python3 -I MP4/src/integrity.py --provenance project_1 && python3 -I MP4/src/integrity.py --provenance project_2
```

All exit 0; tests 4 of 4 and 3 of 4. Submit the hand-written report where the
course asks for it. Everything before 2026-11-18 23:59.
