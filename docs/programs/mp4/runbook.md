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
One phase per session. Answer the gates it asks. Never push.

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

**O1 — course forum post (DEFERRED, owner's call).** As of 2026-10-28 MP3 has
not reached its due date and MP4 is not formally open, so Joseph is holding
this post to be fair to the TAs. The full draft is ready at
`docs/programs/mp4/forum-post-draft.md`; it covers the `read_test_vector`
defect (`why.md` H-L1) and asks when and where the unsafe-metrics tool and
validation script will be released. When MP4 opens, check the course page for
news first; if nothing has been posted, paste the draft. Relay any ruling to a
session; it goes into `MP4/configs/projects/project_2.yaml`. Until then every
session works under D8 (known-failing, 3/4 ceiling) and flags O1 as
unresolved in its report. **This must be resolved or consciously accepted
before submission.**

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
nothing in M6 starts until they are answered.

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

## Stage 3 — when the course releases its tools (cut-off 2026-11-15)

**O3 — unsafe-metrics tool.** Place it at `MP4/tools/unsafe-metrics/` if its
licence allows committing it, otherwise anywhere outside the repo. Then tell a
session the exact invocation (how staff run it, what input it takes). The
session sets `safety.course_cmd` in `MP4/configs/pipeline.yaml` and flips M12
in `where.md` from `blocked (...)` to `not-started`. Then `/mp4-phase`.

**O4 — validation script.** Same pattern at `MP4/tools/validate/` or an
external path. Flip M13 to `not-started`. Then `/mp4-phase`.

If either has not arrived by 2026-11-15, tell a session to mark the row
`dropped (course tool not released by cut-off; proxy numbers shipped labelled)`.

## Stage 4 — after M10

**O5 — Overleaf.** Paste `MP4/docs/report_mp4_draft.tex` (and the TikZ
diagram block) into the team's Overleaf project as the MP4 section. Compile.
Export the PDF to `MP4/docs/CS598JBR_Report_Team_1.pdf` (gitignored). Flip
M14 to `not-started`. Then `/mp4-phase`. Jacob and Ross polish prose after
M14 confirms the numbers match.

## Stage 5 — after the program reports ready-to-merge

**O7 — merge and push.** The close review runs itself over up to three
`/mp4-phase` invocations once M14 is done. When a session says
**ready-to-merge**, read `docs/programs/mp4/handoff.md`, then:

```bash
git checkout main && git merge --no-ff mp4-program
```

```bash
git push origin main
```

Merge commit, never squash. Submit before 2026-11-18 23:59.
