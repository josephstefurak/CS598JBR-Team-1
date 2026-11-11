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

**O1 — the `read_test_vector` question (OPEN, unsent).** Deferred on
2026-10-28 until MP4 opened; MP4 is open since 2026-11-09. On 2026-11-11 the
owner chose to ask in class rather than post. The written draft is kept
locally at `docs/programs/mp4/forum-post-draft.md` (gitignored after M15); it
covers the defect (`why.md` H-L1). Its question about the unsafe-metrics tool
is answered; only the validation script is still unreleased. Relay any ruling
to a session; it goes into `MP4/configs/projects/project_2.yaml`, the README
and the local report draft. Until then every session works under D8
(known-failing, 3/4 ceiling) and flags O1 as unresolved in its report.
**This must be resolved or consciously accepted before submission** (M14 asks).

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
does it. Nothing for you to do unless M12 asks whether to retry the install
without `--locked`. To remove it later:

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

## Stage 4 — the report (yours, by hand)

**O5 is superseded (2026-11-11).** The team writes the MP4 section in
Overleaf by hand. M14 gives you a finished local draft,
`MP4/docs/report_mp4_draft.md` and `.tex` (gitignored, never committed), with
generated tables and cited repair examples, as a recommendation to write
from. The `.tex` has never been compiled; its first lines name what the
preamble needs (`\usepackage{tikz}`,
`\usetikzlibrary{positioning,arrows.meta,shapes.geometric}`). No session
waits for an export.

## Stage 5 — after the program reports ready-to-merge

**O7 — merge and push.** The close review runs itself over up to three
`/mp4-phase` invocations once M14 is done. When a session says
**ready-to-merge**, read `docs/programs/mp4/handoff.md`, then (the branch is
already on the remote; only the merge and `main` are yours):

```bash
git checkout main && git merge --no-ff mp4-program
```

```bash
git push origin main
```

Merge commit, never squash. Submit before 2026-11-18 23:59.
