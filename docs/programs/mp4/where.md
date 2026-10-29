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
- D-ALLOW, D-CLIMAIN, D-FAITHFUL, D-FORBID: defaults confirmed verbatim at the M3 gate (2026-10-29). D-TRAJ, D-DIAGRAM: defaults.
- D-STRUCTOUT (M3): isolation check admits `StructuredOutput` (added by `--json-schema`) beside the six tools.

## Phase ledger

| ID | Phase | Status | Session / commit | Notes |
|---|---|---|---|---|
| M1 | MP4 layout, subjects, toolchain, baselines | **done** | 2026-10-28 — 0122f84 | 9/9 paths; checksums 13/13 + 28/28 OK; nightly = rustc 1.89.0-nightly 2025-05-12; Baseline A E0583 x1 (satc) / x5 (libpsbt); Baseline B 0/4 + 0/4 tests; harness clippy satc 0/0/0/0, libpsbt style 2; H-L10 answered; 10 why.md corrections |
| M2 | Checks library, integrity guards, self-test | **done** | 2026-10-28 — a8994d9 | selftest 54 PASS / 0 FAIL (baseline null → 54); interface items satc 45, libpsbt 52; check-only on pristine satc: build.ok false, E0583, missing 45; course tool exit 2; check-only on M1 Baseline B copies reproduces M1 clippy split (libpsbt harness style 2) and 4 tests after dedupe |
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

### M1 — MP4 layout, subjects, toolchain, baselines (2026-10-28, 0122f84)

**Shipped** (product terms): The graded `MP4/` tree now exists with the
required directory names. Both assigned C projects and their CRUST-bench Rust
skeletons are committed under `MP4/subjects/`, pinned to a recorded archive
hash and checked file by file. The grading toolchain is installed on the
pipeline machine and its exact versions are recorded. Before any pipeline
code exists, we have a measured record of what the untouched skeletons do:
they don't build, the stubs fail all tests, and these are the clippy warnings
that come from immutable test files and that no translation can remove.

**Deviations from spec**:
- Toolchain step 2 used `--default-toolchain none`, which the spec does not
  mention, so that no unrequested stable toolchain was downloaded. rustup
  still made `nightly-2025-05-13` the default because it was the only one
  installed. Harmless, because every call is `+nightly-2025-05-13`. Recorded
  in `MP4/docs/environment.md`.
- The installer was saved to a file and then run, not piped to `sh` as the
  runbook had it. Runbook updated to the commands actually run.
- The archive was fetched from a commit-pinned URL
  (`.../raw/4b4702544b80.../datasets/CRUST_bench.zip`), not `main`, so it
  can be reproduced. Recorded in `SOURCE.md`.
- Added `baseline/baseline_A_build.log` and, for libpsbt,
  `baseline/test_no_fail_fast.log`. Neither is in the spec's file list, but
  both are the verbatim evidence for the Baseline A and H-L10 answers.
- `MP4/trajectories/project_N/` holds `baseline/`, so no `.gitkeep` there.
  `.gitkeep` is used in `src/`, `configs/` and `translations/project_N/`.
- Ledger hash: this row records the deliverables commit `0122f84`. The
  ledger/log update is the commit right after it, because a commit cannot
  contain its own hash.
- Spec wording "eleven required section headings from R-T1-README + tool
  list + layout" was read as the nine R-T1-README items plus tool list plus
  layout, which makes eleven. what.md was reworded to say so.

**Owner gates**: Asked: "M1 owner gate (O2): may this session install
rustup and nightly-2025-05-13 now? … [three exact commands shown] …
roughly 500 MB." Answer: "Yes, install now". After the install, the owner
asked "is the download safe?". The session answered with the installer
sha256 (`9502b514…ccafc0`), its download root (`static.rust-lang.org`), and
confirmation that no shell profile was modified. The owner replied "okay
sounds good continue with M1".

**Verification** (real output):
- `ls -d` of the 9 required paths: all 9 printed.
- `shasum -a 256 -c CHECKSUMS.sha256`: project_1 13 `OK`, project_2 28
  `OK`. `diff -rq` of the extracted archive dirs against `subjects/`: no
  differences.
- `cargo +nightly-2025-05-13 --version` → `cargo 1.89.0-nightly (056f5f4f3
  2025-05-09)`. `rustc` → `1.89.0-nightly (8405332bd 2025-05-12)`. `clippy`
  → `0.1.88 (8405332bdf 2025-05-12)`.
- Baseline A: satc `error[E0583]: file not found for module satc`, exit
  101. libpsbt: 5 × E0583 (`base64`, `cli`, `compactsize`, `psbt`, `tx`),
  exit 101. `cargo fetch --locked` (libpsbt): exit 0.
- Baseline B: build exit 0 for both. `cargo test`: satc `0 passed; 4
  failed`, libpsbt `0 passed; 4 failed`, all `not implemented`. Rubric
  clippy exit 0 for both. `clippy.json` exists for both.
- Clippy, unique sites (harness / interface-induced):

  | | correctness | style | complexity | perf | rustc |
  |---|---|---|---|---|---|
  | satc | 0 / 0 | 0 / 2 | 0 / 1 | 0 / 0 | 2 / 40 |
  | libpsbt | 0 / 0 | 2 / 1 | 0 / 0 | 0 / 0 | 8 / 32 |

  Per file: satc `src/satc.rs` 150 raw diagnostics, `src/bin/satc_test.rs`
  2. libpsbt `src/psbt.rs` 76, `src/bin/test.rs` 16, `src/cli.rs` 2. Raw
  counts include cross-target duplicates. Written to `program.yaml`
  baselines.
- H-L10, verbatim: `found to be present in multiple build targets: * bin
  target test * integration-test target test`. The bin builds. `cargo test
  --no-run` lists `unittests src/bin/test.rs` and `src/bin/test.rs` as two
  executables, and with `--no-fail-fast` each reports `0 passed; 4 failed`.
- `git grep --cached -nE 'sk-ant-|Bearer |api_key=' -- MP4/`: no output.
  The same grep over `docs/` matches only lines that quote the pattern
  itself (see discoveries). `git grep -nE 'claude-501|/Users/josephstefurak'
  -- MP4/`: no output.
- Floor items for M2+ (`py_compile`, selftest, scrub, `run_pipeline`,
  provenance) do not exist yet. Not run.
- Harness counts: no harness exists yet (M2). Delta n/a.
- Docs-claims check: grepped `1\.88|~25|eleven|E0583|extern crate test`
  over `docs/ CLAUDE.md MP4 .claude`. Fixed 2 stale lines in what.md (M1
  version line, "eleven" wording) and the runbook O2 block. why.md had
  already been corrected in step 6.
- why.md corrections against the handout and the subjects (10): R-T1-README
  now says "external tools" and "or local runtime". R-T3-SAFETY records
  that it measures generated code only. Added the compile bands and the
  correctness rounding note. Idiom last band: the handout literally says
  "more than 22", recorded as a typo for >30. Z11 now quotes what the
  validator checks. H-S2 has the measured harness numbers. H-A6 gains
  `get_aabb` `y_max = x_max`. H-L6 corrected from "~25" to 29 assignment
  sites. H-L10 answered. E2 and E7 updated (E7 was "≈ 1.88.0-nightly").
  Checked against the handout with nothing to fix: the deliverable point
  values (430 = 40 + 120 + 200 + 70), the safety bands, Z1–Z16 wording, the
  Group 1 assignment, the deadline, and the Task 4 table columns. Spot-checked
  in the subjects and confirmed: H-S1, H-A2, H-A3 (`satc_point_copy`), H-A5
  (0.000001 box), H-A6, H-L1 (`let mut step = 0;` inside `checker`), H-L2,
  H-L3 (all four comments), H-L4 (2048 buffers; PSBT_HEX = 1778 chars = 889
  bytes), H-L8, H-L9, H-L13 (`cHNid`), H-L14.

**NOT demonstrated**:
- H-L1's claim that the test vector contains record types 1, 2, 4, 5 and 6
  was not checked by decoding the PSBT. Only the defective `step` variable
  was confirmed.
- H-A4, H-A7, H-A8, H-L5, H-L7, H-L11's "dead consts" wording, H-L12 and
  H-L15 were not re-read against the C.
- The lint-to-category mapping comes from this clippy's group flags
  (`-A clippy::all -W clippy::<group>`). Whether the course counts
  categories the same way is unknown.
- Whether the PATH requirement holds for headless `claude -p` children is
  untested until M3.
- The ~500 MB size estimate was not measured.
- Nothing here shows the subjects are what the course grader uses beyond
  matching the public CRUST-bench archive.

**Discoveries logged for later rows**:
- (M2 checks library) libpsbt test counting must dedupe by test name: the 4
  tests run in up to 2 executables, and fail-fast hides the second. Count
  totals from distinct names, and run with `--no-fail-fast` so per-test
  results are complete.
- (M2/M5) The floor item `git grep -nE 'sk-ant-|Bearer |api_key=' -- MP4/
  docs/` can never print nothing, because what.md, why.md and program.yaml
  quote the pattern. Candidate fix: scope it to `MP4/`, or exclude
  `docs/programs/`. Not changed here because the manifest's floor is static
  config outside this row.
- (M3 prompts / D-FAITHFUL) A fourth satc C bug, not exercised by tests:
  `satc_polygon_get_aabb` sets `y_max = x_max`. Added to H-A6. It needs a
  ruling with the others.
- (M2 attribution) The interface's own `use std::f64::MAX;` and `use
  std::f64::consts::PI;` produce `unused_imports` and
  `legacy_numeric_constants` in `src/satc.rs`. The file is agent-written, so
  these count as agent-attributable, not harness.
- `MP4/docs/` already held a `CS598JBR_Report_Team_1.pdf` (gitignored)
  before this session. O5 expects that file to be produced after M10.
  Left untouched. The owner may want to confirm whether it is a template
  or a stale export.

**Queued for owner**:
- O2 cleared (installed). Remaining owner step: add `export
  PATH="$HOME/.cargo/bin:$PATH"` to the shell that launches Claude Code
  (runbook Stage 1) before M3.
- **O1 still deferred.** The course-forum post on `read_test_vector`
  (H-L1) and the tool/validator release dates has not been made. D8 remains
  the working assumption. It must be resolved or consciously accepted before
  submission.

### M2 — Checks library, integrity guards, self-test (2026-10-28, a8994d9)

**Shipped** (product terms): The pipeline can now judge a translation
without calling a model. For any crate it reports whether it builds, which
tests pass and why the others fail, the rubric clippy log, and per-category
clippy counts that separate the agent's warnings from the test file's. It
also reports proxy unsafe metrics, whether the required interface is
intact, and whether anyone touched the tests or interfaces (and puts them
back). It catches test strings copied into library code and finds secrets
before commit. `run_pipeline.py --check-only` packages all of this into one
`check.json`. A self-test proves every check against a fixture crate with
known planted problems.

**Deviations from spec**:
- Added `mp4common.py` (paths, defaults marked
  `TODO-move-to-pipeline.yaml`, cargo runner) and `rustlex.py` (strips
  comments and literal contents for the regex scans). Both are shared by
  the specified modules. No other new entry points.
- `run_pipeline.py --check-only` also takes `--crate-dir` and `--out`. The
  spec's verification runs check-only "on the pristine skeleton", but
  `MP4/translations/project_1/` is empty and cargo must not run inside
  `subjects/`. So check-only always measures a temp copy (it never touches
  the crate or its mtimes), and the verification run wrote to the
  scratchpad, not `MP4/results/`. With no crate, the default exits 2 with
  "no crate at MP4/translations/project_1 (no translation yet? pass
  --crate-dir)".
- `integrity.py` gained `--scan` (hard-coding + FFI from the CLI) beside
  the four specified modes.
- `src/lib.rs` is not in the immutable set. Integrity requires it to equal
  `#![forbid(unsafe_code)]` + the skeleton's lib.rs, per D-FORBID, and
  restores it otherwise.
- `cargo test` runs with `--no-fail-fast` so libpsbt's second test
  executable is not skipped (M1 discovery). Totals count distinct test
  names.
- The fixture's perf lint is `clippy::boxed_local`, because clippy reports
  `Box<Vec<i32>>` as a parameter that way, not as `box_collection`.
- The interface checker drops parameter names, reduces paths to their last
  segment, and resolves `Self`. Renaming `_src_size` to `src_size` (H-L4)
  or writing `Write` for `std::io::Write` is therefore not a "change".
- The self-test goes beyond the spec's assertion list. Extra assertions
  cover harness attribution, test-name dedupe, comment/string immunity,
  added-file detection, lib.rs header, workspace drift, provenance, a
  changed-signature check, and home-path scrubbing.
- Owner chose "Do it here" for M2 in the same session that ran M1. The
  program's one-phase-per-session invariant was waived by the owner for
  this session only.

**Owner gates**: none for this row. Before the phase, the owner was offered
a new session and answered "Do it here".

**Verification** (real output):
- `python3 -I -m py_compile MP4/src/*.py` → exit 0.
- `python3 -I MP4/src/selftest.py` → `selftest: 54 PASS, 0 FAIL`. Spec
  counts all PASS: unsafe_lines 1 (>= 1), unsafe_casts 1,
  pointer_arithmetic 1, clippy agent correctness/style/complexity/perf
  1/1/1/1, tests 1/2, hard-coding hits 1, interface missing 1, integrity
  violations detected 1 restored 1, scrub hits 1. Harness count:
  selftest_pass_count null → 54 (+54).
- `check_interface.py --project project_1` (pristine) → `interface items:
  45  missing: 45  changed: 0  extra: 0`, exit 1. project_2 → `52 missing:
  52`. On M1's Baseline B copies (interfaces copied in): 45/0/0 and 52/0/0,
  exit 0.
- `run_pipeline.py --help` → exit 0.
- `run_pipeline.py --project project_1 --check-only --crate-dir
  MP4/subjects/project_1/rust_skeleton --out <scratch>` → `"compiles":
  false`, `"build_error_codes": ["E0583"]`, and `first_error` begins
  `error[E0583]: file not found for module `satc``. `interface_missing`
  45; `integrity_violations` 1 (lib_rs: no forbid header, reported, not
  restored). `git status` shows nothing written under `MP4/subjects/`.
- Cross-check against M1 baselines: check-only on Baseline B copies gives
  libpsbt clippy agent style 1 / harness style 2, tests 0/4 (8 executions
  deduped to 4 names). satc gives agent style 2 / complexity 1, harness 0.
  Both match the M1 hand classification.
- `safety_check.py --tool course --project project_1` → stderr `course
  safety tool not configured (set safety.course_cmd in
  MP4/configs/pipeline.yaml)`, exit 2.
- `integrity.py --provenance project_1` → `no final run recorded
  (MP4/trajectories/project_1/run_summary.json missing)`, exit 1. This is
  expected before M6. Provenance logic is covered by the self-test.
- `scrub_secrets.py --check MP4/` → `scrub_secrets: 0 hit(s)`, exit 0. The
  first run found 1 hit (a home-path literal in selftest.py), fixed by
  assembling the string.
- `git grep -nE 'sk-ant-|Bearer |api_key=' -- MP4/` → no output. Over
  `docs/` it gives 8 self-referential lines (M1 discovery, unchanged).
- Lint (no mypy installed): `pyflakes` exit 0. `flake8
  --max-line-length 120` exit 0 after fixing 3 findings. `pylint
  --disable=C,R` leaves 2× subprocess-run-check, which is intentional
  because return codes are read, and the TODO marker.
- Docs-claims check: grepped `~45|~50|box_collection|selftest_pass_count|
  interface_pub_items` over `docs CLAUDE.md MP4`. Updated the 3
  program.yaml baselines; no other stale lines.
- Security: subprocesses are argv lists, never a shell. `--project` is
  restricted to choices and `run_id` to a safe-name regex before it is
  used in a path. `course_cmd` comes only from repo config and is split
  with shlex, not passed to a shell. The scrubber never prints the
  matched text. Secret patterns in code are assembled from pieces so the
  repo grep stays empty. Rate limiting and CSRF do not apply (local CLI,
  no network service).

**NOT demonstrated**:
- No check has run on a real translation. The regex safety counts, the
  pointer-receiver heuristic and the interface normaliser have only seen
  the fixture and the stub skeletons. They may over- or under-count on
  agent code (generics, macros, `where` clauses, nested impls).
- `unsafe_calls` is a proxy (call expressions inside unsafe regions) and
  will differ from the course tool's definition.
- The `-D unsafe_code` build was shown to fail on the fixture. A passing
  case was not shown, because no forbid-clean crate exists yet.
- The hard-coding scan catches literal reuse only, not numeric or
  structural hard-coding (Z2's `if input == KNOWN` shape). The spec's
  heuristic for that shape is not in M2.
- `--all-snapshots` and `--check-workspace` from the CLI were not run on
  real trajectories (none exist). The workspace and provenance logic is
  only self-tested.
- Timing: the self-test takes about 1–2 minutes and runs cargo several
  times. Check-only on libpsbt rebuilds dependencies in a temp target
  dir every call. Fine for now, but not measured under the pipeline's
  45-minute wall clock.

**Discoveries logged for later rows**:
- (M3) `configs/pipeline.yaml` must carry the `TODO-move-to-pipeline.yaml`
  defaults in `mp4common.py`: toolchain, clippy groups, rubric args,
  forbid line, hard-coding minimum, cargo timeout, plus
  `safety.course_cmd`.
- (M4) The checks currently `touch src/lib.rs` in the crate they run on.
  In the loop that crate is the workspace under `MP4/translations/`,
  where that is allowed. check-only uses a copy.
- (M5 review) The Z2 `if <expr> == <literal> { return` heuristic named in
  why.md is not implemented. Only literal reuse is.
- (M1 carry-over, still open) The floor's `git grep … -- MP4/ docs/` item
  can never be empty.

**Queued for owner**: nothing new. **O1 still deferred.** D8 remains the
working assumption, and O1 must be resolved or consciously accepted before
submission.

## Owner-action queue (only the owner can clear these)

> **Running these? Use `runbook.md`.** It is the same items in DEPENDENCY
> order with the exact commands. This queue is the per-item record of what is
> outstanding and why.

| # | Item | Why it exists | Blocks | Status |
|---|---|---|---|---|
| O1 | Post the `read_test_vector` defect (why.md H-L1) on the course forum, together with the question of when/where the unsafe-metrics tool and validation script will be released. Draft ready at `docs/programs/mp4/forum-post-draft.md` | D8; a staff ruling may lift the 3/4 ceiling; O3/O4 depend on the release | nothing in M1-M11 (ruling is injected whenever it arrives) | **deferred by owner 2026-10-28**: MP3 has not reached its due date, so MP4 is not formally open; Joseph will check for news and post once MP4 opens. Every session must treat D8 as the working assumption and must flag this item in its report until it is resolved. **Must be resolved or consciously accepted before submission.** |
| O2 | Approve the rustup + nightly-2025-05-13 install in the M1 session (commands shown first) | E2; invariant 4 | M1 | **done 2026-10-28** (approved in the M1 session; installed). Follow-on: owner puts `~/.cargo/bin` on PATH for the shell that launches Claude Code before M3 (runbook Stage 1) |
| O3 | Supply the course unsafe-metrics tool at the path the runbook names, then flip M12 to not-started | R-T3-*-SAFETY official numbers, R-T4-SAFETY-ANALYSIS | M12 | open (cut-off 2026-11-15); not yet released by the course as of 2026-10-28; owner checks periodically |
| O4 | Supply the course validation script at the path the runbook names, then flip M13 to not-started | Z11, Z16 | M13 | open (cut-off 2026-11-15); not yet released by the course as of 2026-10-28; owner checks periodically |
| O5 | After M10: paste `MP4/docs/report_mp4_draft.tex` into Overleaf, compile, export the PDF to `MP4/docs/CS598JBR_Report_Team_1.pdf` (gitignored), flip M14 to not-started | R-T4-* | M14 | open |
| O6 | Stay logged in (`claude auth status`) and keep the Mac awake (`caffeinate -dims`) during M3, M6, M7, M9 | D7 auto-resume | M3, M6, M7, M9 | open |
| O7 | After the program reports ready-to-merge: merge `mp4-program` into `main` with a merge commit and push `main` before 2026-11-18 23:59 | invariant 6/7 | submission | open |
