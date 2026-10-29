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
| M3 | Configs, prompts, agent runner, smoke run | **done** | 2026-10-29 — 2e0f3d2 | rulings: all 4 defaults + D-STRUCTOUT; selftest 54 → 88 (+34, incl. 5 runner scenarios); smoke 2/3 D7 calls spent: init tools 6+StructuredOutput, mcp [], slash [], dontAsk, claude-opus-5; git denied; cargo 1.89.0-nightly; no leak markers; read-only Bash auto-approved (finding) → fixed same day, probe 5/5, D7 smoke calls now 3/3 spent |
| M4 | Iteration loop, stop logic, resume drills, README draft | **done** | 2026-10-29 — 23c88b2 | selftest 88 → 120 (+32); drills A–H + D2, E2 all PASS (A SUCCESS@2, B MAX_ITERATIONS@1, C NO_PROGRESS@4, D restored, E attempt2, E2 exit 75, F 143→resume, G rerun identical, H tamper reverted); README 12/12 headings, generated sections current; no model calls |
| M5 | Review 1: pipeline vs rubric, guard test, traceability | **done** | 2026-10-29 — 1ac3cd4 | 50 findings (44 angles + 6 sweep): 32 fixed + security S1/S2, 6 to owner gates G1–G7 (asked at M6), 12 backlog/M8/M12; selftest 120 → 166 (+46); traps 7/7; interface fuzz 241 hangs + 92 crashes → 0; matrix 37 rows (6 verified, 22 pending-run, 2 proxy, 7 owner-blocked); fresh clone exit 0 before and after the fixes |
| M6 | Full run: project_1 (satc) | **done** | 2026-10-29 — c8435d7 (step 1 f69ae8d) | G1–G7 applied, selftest 166 → 192 (+26); run `20261029T184931Z` SUCCESS after 2 iterations / 2 attempts in 7.6 min, no pauses; both iterations 4/4 tests, agent clippy 0/0/0/0, harness 0/0/0/0, proxy safety 0, interface 0/0, integrity 0, lint attrs 0; 29 turns, 39 971 output tokens; 0 leak markers; 2 denials (`ls -R`); check-only diff empty; provenance ok; D7 full run 1/1 for project_1 spent |
| M7 | Full run: project_2 (libpsbt) | **done** | 2026-10-29 — f09f89c | run `20261029T194929Z` SUCCESS after 2 iterations / 2 attempts in 22.1 min, no pauses; pipeline code and configs identical to M6 (diff empty); both iterations 3/4 tests with only `read_test_vector` failing as documented (D8, test.rs:126, left 4 right 0), agent clippy 0/0/0/0, harness style 2 + rustc 8 (M1 baseline), proxy safety 0, interface 52 items 0/0, integrity 0, lint attrs 0; 87 turns (iter 1: 56 of 60), 111 569 output tokens; 0 leak markers; 3 denials (`ls`/`wc`); check-only diff empty; provenance ok; D7 full run 1/1 for project_2 spent |
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

### M3 — Configs, prompts, agent runner, smoke run (2026-10-29, be3de95 + 2e0f3d2)

**Shipped** (product terms): The pipeline can now launch the translation
agent the way the program designed it. It runs headless on Opus with
effort high. It has only file tools and a cargo-only Bash allowlist. It
cannot see the owner's or the repo's instructions, memory, hooks, MCP
servers or skills, and it gets the project's context and the owner's
rulings in its prompt. Every call is checked at startup and stopped if it
shows any extra capability. Its full stream is saved with secrets removed
as it is written. Usage limits, turn caps and hangs are recognised. The
configuration is validated, so the spend limits and the rubric clippy
command cannot drift. Before spending anything, `--dry-run` shows the
exact command and first prompt. A real two-call smoke test proved the
isolation.

**Spend** (D7, pre-authorized; announced here as required): 3 smoke
attempts × 2 calls, each `--max-turns 2`, Opus, subscription quota.
Attempts 1 and 2 never reached the model: `duration_api_ms 0`, 0 tokens,
logged `not-spent` in `evidence/smoke/calls.log`. Attempt 3 reached it
twice: api 38.7 s and 14.3 s, `num_turns` 4 each. **Smoke calls spent:
2 of 3.** No full or tuning runs.

**Deviations from spec**:
- `pipeline.yaml` is grouped into sections (agent, loop, toolchain,
  checks, safety, rate_limit, digest, prompts, projects) rather than the
  flat key list in the spec. Every spec key is present, and `config.py`
  allowlists keys per section.
- `config.py` also enforces the D7 envelope (model opus, max_turns ≤ 60,
  max_iterations ≤ 8), the handout clippy command, the pinned toolchain
  and the settings-file values, so a config edit cannot quietly leave
  the envelope.
- `mp4common.py` (M2) changed. Before, toolchain and check settings were
  hard-coded defaults marked `TODO-move-to-pipeline.yaml`. Now it reads
  them from `pipeline.yaml` (defaults remain as fallback), so each value
  is defined once.
- The isolation check admits `StructuredOutput` (owner ruling
  D-STRUCTOUT, below).
- The smoke counter refuses calls beyond D7's 3. It counts a call only
  if it reached the model (a non-synthetic assistant event, API time or
  tokens). I corrected four log entries that the first counter version
  had marked `spent`.
- Leak markers: "CS598JBR" was removed after a false positive (it is
  in the `--add-dir` path). The verdict was recomputed from the saved
  text, and the original is preserved in `smoke_report.json`.
- The D-FAITHFUL UB cases (satc AABB position, libpsbt base62 index 63)
  are left to the agent to define and report in its final status. The
  ruling says "defined, non-panicking". The session did not invent a
  specific value, so no ruling detail was made up. Index 62 is noted as
  well defined (the alphabet's NUL).
- Owner chose "Do it here" again (third phase in this session). Logged
  as a waiver of one-phase-per-session.

**Owner gates**:
- Defaults batch, asked in one `AskUserQuestion`. Answers verbatim:
  D-ALLOW "One allow, that fn only"; D-CLIMAIN "Make it pub fn main";
  D-FAITHFUL "Faithful; define UB safely"; D-FORBID "Yes, inject it".
  Recorded in why.md § D and in both project yamls.
- Spec conflict raised mid-phase: the real init lists `StructuredOutput`
  (added by `--json-schema`), but the spec required exactly six tools.
  Asked; answer: "Allow StructuredOutput too (Recommended)". Recorded as
  D-STRUCTOUT in why.md and where.md, and what.md's verification line
  updated.
- Auth: the CLI was logged out. The owner ran `claude auth login`
  themself ("Login successful"). The session did not handle credentials.

**Verification** (real output):
- `run_pipeline.py --dry-run --project project_1` exits 0 and prints
  `claude -p --output-format stream-json --verbose --model opus --effort
  high --max-turns 60 --max-budget-usd 30 --permission-mode dontAsk
  --tools Read,Edit,Write,Glob,Grep,Bash --allowedTools …
  --disallowedTools 'Bash(git *)' … --setting-sources project
  --settings … --append-system-prompt-file … --json-schema …
  --strict-mcp-config --mcp-config '{"mcpServers":{}}'
  --disable-slash-commands --session-id … --add-dir …/project_1/c`.
  That is every C2–C6 flag. project_2 also exits 0. The prompt carries
  no fn body (self-test asserts it for both projects, initial and
  repair).
- `grep -niE 'do not (modify|alter|change).*test|FFI|unsafe|hard.?cod'
  MP4/configs/prompts/*` → 6 lines.
- `grep -rn 'configs/' MP4/src/` → non-empty (config.py, agent_runner.py,
  run_pipeline.py, …).
- `python3 -I MP4/src/selftest.py` → `selftest: 88 PASS, 0 FAIL`
  (54 → 88, +34). New assertions: config loads, unknown key / model /
  max_turns rejected, config_hash stable, argv flags, git denial,
  add-dir, isolation env. The 5 runner scenarios: normal → ok, usage
  limit → usage_limit with resets_at, timeout kill → timeout in 2.0 s,
  tool mismatch → isolation_violation, scrub of planted
  key/e-mail/home path. Also max_turns, and prompt guardrails / no fn
  body / no placeholder / repair carries failures and clippy sites for
  both projects. Templates have no `satc_`/`psbt_`.
- Smoke attempt 3 (`evidence/smoke/smoke_report.json`). Both calls'
  init: `tools ['Bash','Edit','Glob','Grep','Read','StructuredOutput',
  'Write']`, `mcp_servers []`, `slash_commands []`, `permissionMode
  dontAsk`, `model claude-opus-5`, `claude_code_version 2.1.235`;
  init also shows `skills []`, `plugins []`. Call a's answer lists the 7
  tools and describes only the appended system prompt. Its Glob for
  `**/{CLAUDE.md,AGENTS.md,.claude/**}` found nothing, and it says "I
  found no CLAUDE.md, AGENTS.md or .claude/ memory files". No leak
  marker (working agreement, program-builder, commit-only, mp4-program,
  memory notes) appears. Call b's `permission_denials`: `[{tool_name:
  Bash, tool_input: {command: "git status"}}]`, and it reports `cargo
  1.89.0-nightly (056f5f4f3 2025-05-09)`. Verdict: all 5 true.
- `scrub_secrets.py --check MP4/ docs/programs/mp4/evidence/` → 0 hits.
  `git grep -nE 'sk-ant-|Bearer |api_key=' -- MP4/` → empty.
- `--check-only` still works: pristine satc skeleton → `"compiles":
  false`, E0583.
- `py_compile` (src + tests) exit 0; flake8 (120 cols) exit 0; pyflakes
  exit 0.
- Docs-claims check: grepped `TODO-move`, `tools\[\] ==`, `confirm at
  M3`, `sandbox`. Updated why.md (C2, C3, C4, C6, D-ALLOW…D-FORBID,
  D-STRUCTOUT), what.md M3 verification line, where.md ratified list,
  runbook O8 (the wrong sandbox diagnosis corrected). Historical log
  lines were left as written.
- Security: the agent's argv is a list (no shell). Config paths cannot
  escape `MP4/configs`. Streams are scrubbed on write and the scrubber
  never echoes matches. The smoke ledger caps spend in code. Prompt
  injection from C sources into agent B is bounded by the tool allowlist
  (see the finding below). Rate limiting and CSRF do not apply.

**NOT demonstrated**:
- **The tool restriction has a read-only hole.** Under `dontAsk` the
  agent ran `ls -a … | head -60`, which is not allowlisted and is piped,
  and it was approved. Claude Code auto-approves read-only shell
  commands. Read/Glob/Grep are not path-restricted either. So agent B
  can read any file the user can, including `~/.claude/CLAUDE.md` and
  the rest of this repo, if it chooses to. Isolation from *automatic*
  injection is shown; isolation from deliberate reading is not.
  Mutating commands (`git status` was denied) appear blocked, but only
  `git` was tested.
- The `Edit(//…/subjects/**)` / `Write(…)` denials were never exercised.
- `--max-turns 2` produced `num_turns: 4`, so how the cap counts is not
  understood. A 60-turn cap may allow more model turns than intended.
- No real translation prompt has reached the model. The prompts are
  unproven on actual work (M4/M6).
- The rate-limit event shape is taken from C1 and the fake. No real
  `rate_limit_event` has been observed (none occurred).
- An expired login gives `is_error` with "Failed to authenticate" and
  is classified `error`. The loop does not yet stop on it specifically.

**Discoveries logged for later rows**:
- (M4/M5, security) Close the read-only hole. Candidates: path-scoped
  `Read(./**)`, `Glob`/`Grep` rules plus an `Read(//<c_dir>/**)` allow;
  explicit denials for `Bash(cat *)`, `Bash(ls *)`, `Bash(head *)`,
  `Bash(find *)` and similar; or a sandboxed cwd. Each needs smoke
  evidence, and only 1 D7 smoke call remains, so testing it costs the
  last one or needs an owner yes beyond D7.
- (M4) Treat "Failed to authenticate" as its own outcome that stops the
  run and points to `claude auth login`, instead of a retryable
  `error`.
- (M4) Measure how `--max-turns` maps to `num_turns` on the first real
  iteration, and record the result in why.md C6.
- (M4) The pre-run checklist should run `claude auth status` and refuse
  to start when loggedIn is false. That would have saved attempt 2.

**Queued for owner**: O8 done (CLI logged in). Decision for the next
phase or the owner: whether to spend the last D7 smoke call verifying a
tightened tool policy (discovery 1), or to approve calls beyond D7 for
it. **O1 still deferred.** D8 remains the working assumption, and O1
must be resolved or consciously accepted before submission.

### M3 addendum — tool policy tightened and probed (2026-10-29, 5cadf51)

**Why**: M3 found that agent B could read outside its directories:
unscoped Read/Glob/Grep allows, plus read-only shell commands that Claude
Code auto-approves. The owner chose "Fix it now", using the last D7 smoke
call to verify.

**Shipped**: The agent can now read only its crate and the project's C
directory, write only inside its crate, and run only the pinned cargo
commands. Everything else is refused, including shell reads and any write
into `subjects/`.

**Spend**: 1 probe call (Opus, `--max-turns 2`, api 28.3 s, `num_turns`
12). **D7 smoke calls spent: 3 of 3**, and the counter now refuses
further smoke or probe calls (`probe refused: 3 of 3 D7 smoke calls
already spent`, exit 3).

**Changes**: `pipeline.yaml` tool policy (see `configs/CHANGELOG.md`).
`run_pipeline.py --smoke-probe`: a one-call probe with a random canary
file outside the working dirs, plus `probe_evaluate()`, which can rebuild
the report from a saved stream. Real files were never probed, so no
personal file content can enter the evidence.

**Deviation**: the live probe's post-processing crashed on
`system/permission_denied` events (their `message` is a string). The call
was already complete and its stream saved, so the report was rebuilt from
the stream with no new call. The random canary token was not persisted,
so the check uses its fixed prefix `MP4-CANARY-`, which the prompt does
not contain. The note is in `probe_report.json`. The parser is fixed and
the token is now saved in the report.

**Verification** (`evidence/smoke/probe/probe_report.json`): init tools
= six + StructuredOutput, mcp [], slash [], dontAsk, claude-opus-5. 11
tool calls, 6 permission denials:
- denied: Read of the canary; `cat` canary; `ls <outside> | head -5`;
  Glob `*` in outside; Grep in outside; bare `ls`.
- refused: Write `…/subjects/project_1/c/PROBE_SHOULD_FAIL.txt` ("File is
  in a directory that is denied by your permission settings"). No file
  on disk; `git status MP4/subjects` empty.
- allowed: Read `…/c/satc.h` (5 lines returned); `cargo
  +nightly-2025-05-13 --version` → `cargo 1.89.0-nightly (056f5f4f3
  2025-05-09)`; Write `probe_inside.txt` in the crate.
- `MP4-CANARY-` is absent from the stream. Verdict 5/5 true.

Floor: py_compile, flake8 and pyflakes clean; selftest 88 PASS, 0 FAIL;
dry-run exit 0 for both projects; check-only E0583 on the pristine
skeleton; scrub 0 hits; secret grep empty.

**NOT demonstrated**: Glob/Grep *inside* the working dirs under the new
policy (only Read was probed inside). Edit (as opposed to Write) in the
crate. Every denied read-only command except `cat`/`ls`. Whether
read-only commands not on the deny list (e.g. `nl`, `fold`, `column`)
are still auto-approved: the denylist is necessarily incomplete, and
only the commands probed are proven blocked. The git denial and leak
checks from attempt 3 ran under the previous policy; the new policy
only removes permissions, so they should still hold, but they were not
re-run. `--max-turns 2` gave `num_turns` 12, so the cap's meaning is
still open for M4.

**Discoveries logged for later rows**: (M4) record the canary-style
probe as a reusable pre-run check, at a cost of one call, which needs
an owner yes because the D7 smoke allowance is exhausted. (M4) The
digest/trajectory parsers must accept string `message` fields. (M5)
review the read-only denylist for gaps.

### M4 — Iteration loop, stop logic, resume drills, README draft (2026-10-29, 23c88b2)

**Shipped** (product terms): The pipeline is complete end to end, and
proven without spending any quota. One command now sets up a fresh crate
from the benchmark skeleton and runs the agent. After each session it
checks, restores and measures everything, feeds the results into the
next prompt, and stops on success, lack of progress, the iteration cap,
or repeated tampering. It waits out usage limits and resumes, and a
killed run can be continued from exactly where it stopped. Every step
leaves a complete trajectory. The results tables are generated from
those artifacts and cross-checked against an independent re-measurement.
The README now describes the pipeline as built.

**Deviations from spec**:
- The loop lives in `run_pipeline.py` as the spec says (it grew to ~960
  lines), with helpers `measure_crate`, `evaluate`, `do_checks`,
  `decide_stop`, `finalize`, `_usage_limit` and a `Run` class. Taking
  the config and paths as parameters is what lets the drills run it on
  temp copies of the fixture.
- The fake agent runs as a subprocess through `agent_runner.run`, not
  as in-process code. That way the drills exercise the real stream tee,
  init isolation check, wall-clock and process-group kill, and outcome
  classification.
- Added stop reasons beyond the spec list: `ABORT_ISOLATION` (an init
  mismatch aborts the run, not just the iteration, because the next
  iteration would repeat it with the same config) and `AUTH_ERROR` (M3
  discovery). `agent_runner` gained an `auth_error` outcome.
- `rate_limit.mode` values are `wait|exit` per this spec. M3's config
  validator accepted `wait|stop`; `stop` was never used.
- Spend guards in code beyond the spec: a real run refuses without `--yes`
  or a terminal confirmation, refuses when `claude auth status` is not
  logged in (M3 discovery), and refuses beyond the D7 envelope (one full
  run per project plus 2 tuning reruns in total, counted from committed
  `run_manifest.json` files).
- Integrity verify-and-restore results are persisted in `integrity.json`
  before cargo runs. Without that, a rerun after a crash would see the
  already-restored files, report 0 violations, and break drill G's
  idempotency.
- Extra drills beyond A–H: D2 (two violations in a row → ABORT) and E2
  (`rate_limit.mode exit` → code 75 → `--resume-run`). Also a guard
  check (fake agent refused for `MP4/translations/`) and README checks.
- The drill fixture needed two prepared variants
  (`selftest_fixture_variants/{partial,clean}`). The drills use a
  benchmark-shaped skeleton copy with no `src/fixture.rs`. The clean
  variant uses one `#[allow(clippy::boxed_local)]`, declared in the drill
  project config, because the fixture interface fixes a `Box<Vec<i32>>`
  parameter. It builds its greeting with `concat!` of two short literals,
  which shows the hard-coding scan's known limit (literal reuse only).
- `--help` texts lost their internal phase tags because graders see
  them. `check_only` now reuses `measure_crate()`; before, it duplicated
  the measurement calls.
- Mistake, corrected before reporting: the first commit of this phase
  contained invalid YAML in `program.yaml` (an unquoted drill baseline).
  The commit command was not chained to the YAML check. It was fixed and
  the unpushed commit amended (23c88b2).
- Owner chose "Do it here" again: the fourth phase in this session.

**Owner gates**: none for this row (D7 settled `rate_limit.mode: wait`).

**Verification** (real output):
- `python3 -I MP4/src/selftest.py` → `selftest: 120 PASS, 0 FAIL` in
  about 48 s (88 → 120, +32). Drills:
  - A: `(0, 'SUCCESS', 2)`. Both iter dirs hold every design-reference
    file (prompt.md, agent.stream.jsonl, agent_result.json,
    integrity.json, check.json, build.log, test.log, clippy_rubric.log,
    clippy_{correctness,style,complexity,perf}.json, safety_proxy.json,
    src_after/, changes.diff, diagnostics.md, iteration_summary.json).
    The run dir has run_state.json, run.log and run_manifest.json; the
    trajectory root has INDEX.md and run_summary.json. Iteration-1
    blockers are clippy + interface. The known-failing test is verified
    (failed, assertion and location match). The iteration-2 prompt
    carries `needless_return` and the missing item, and changes.diff
    shows the repair.
  - B `(0, 'MAX_ITERATIONS', 1)`; C `(0, 'NO_PROGRESS', 4)`.
  - D: violation `('src/bin/fixture_test.rs', 'modified', True)`, not
    green, file hash restored, then `(0, 'SUCCESS', 2)`. D2 `(1, 'ABORT')`.
  - E: `(0, 'SUCCESS', 1 pause, [iter_01, iter_01_attempt2, iter_02])`,
    waited 5 s. E2: `(75, attempt 2, step prompt)`, then resume →
    `(0, 'SUCCESS')`.
  - F: exit 143, state `(1, 'agent')`. Resume → `aborted_interrupted`,
    checked, `SUCCESS`.
  - G: exit -9 at step `checks`. Resume → `SUCCESS` (stale lock taken
    over). Rerunning `do_checks` gives a byte-identical
    iteration_summary.json.
  - H: `workspace_tamper` `[(2, ['fixture.rs'], True)]`, and the hand
    edit is gone from the workspace.
  - summarize: results.md row `| selftest fixture | Yes | 1 | 2 | 50.0% |
    2 | SUCCESS |`; a tampered run_summary is refused (MismatchError).
  - README: 12/12 required headings; the generated sections equal
    `pipeline.yaml`.
- `grep -nE 'max_iter|no_progress|SUCCESS|resets_at|step'
  MP4/src/run_pipeline.py` → 40 lines (STEPS cursor at 367, STOP_*
  constants, no_progress at 714, resets_at at 936).
- `py_compile` (src + tests) exit 0; flake8 (120 cols) exit 0; pyflakes
  exit 0.
- `--dry-run` exits 0 for project_1 and project_2. `--help` exit 0.
  `--check-only` still works (pristine satc: compiles false).
- Real-run guard: `run_pipeline.py --project project_1 < /dev/null`
  prints the estimate ("up to 8 iterations x 60 turns of opus …") and
  `refusing without --yes (no terminal to confirm on)`, exit 2. No run
  dir was created and `MP4/translations/project_1` still holds only
  `.gitkeep`. The guard ran `claude auth status` but made no model call.
- `summarize.py --check-readme` → `up to date`; regenerating twice is
  stable. `summarize.py` on the real repo → `PENDING project_1: missing
  …run_summary.json, …check.json`, exit 2 (expected before M6).
- `scrub_secrets.py --check MP4/ docs/programs/mp4/evidence/` → 0 hits.
  `git grep … -- MP4/` → empty. No `fake_agent` processes left.
  `git status MP4/translations MP4/subjects` → clean.
- Docs-claims check: grepped `wait\|stop`, `not implemented yet`,
  `arrives in M4`, and phase tags in `--help`. Fixed the help texts and
  logged the config change in `configs/CHANGELOG.md`. why.md and what.md
  already said wait|exit.
- Security: the run id is regex-validated before it becomes a path.
  The fake agent is refused near the benchmark (in the loop and in the
  agent itself). Trajectory JSON is scrubbed on write (`_write_json`,
  run.log, prompt.md, diagnostics.md). Signal handlers kill agent B's
  process group so no orphan agent keeps editing. The lock prevents two
  live processes driving one run. Spend guards are as above.

**NOT demonstrated**:
- No real agent has run the loop. Everything above uses the fake agent
  on a toy crate. How Opus behaves inside the loop (turn use, repair
  quality, whether prompts fit the digest caps) is unknown until M6.
- The wait-mode pause was drilled at 5 s. Multi-hour sleeps, and a
  machine sleeping through one, were not tested (O6: `caffeinate`).
- Drill G showed checks rerun identically on an unchanged workspace. A
  checks step killed after integrity restore but before persistence
  cannot happen (restore and persist are adjacent, but not atomic).
- The D7 envelope counter trusts committed `run_manifest.json` files.
  Deleting a run dir would reset it.
- The confirmation prompt's interactive "y" path was not exercised (only
  `--yes` and the refusal).
- `summarize.py`'s equality check was shown on fixture output only. The
  `.tex` fragments were written but not compiled in LaTeX.
- The README's tool scope describes the configured policy and the M3
  probe, not a real translation run.

**Discoveries logged for later rows**:
- (M5) The hard-coding scan misses literals split across `concat!` or
  `format!` pieces, as the clean variant shows. Review whether a
  normalised-concatenation pass is worth it.
- (M5) A `run_manifest.json`-based spend counter can be reset by
  deleting run dirs. Consider an append-only ledger like the smoke
  `calls.log`.
- (M6) The first real iteration should record how `--max-turns 60` maps
  to `num_turns` (M3: 2 → 4 and 12), and update why.md C6.
- (M6) A real run replaces `MP4/translations/project_N`. That is the
  intended behaviour, and the confirmation states it.

**Queued for owner**: nothing new. Before M6: `claude auth status` must show
loggedIn true, and `caffeinate -dims` should be running (O6). **O1 still
deferred.** D8 remains the working assumption, and O1 must be resolved or
consciously accepted before submission.

### M5 — Review 1: pipeline vs rubric, guard test, traceability (2026-10-29, 1ac3cd4 + this commit)

**Shipped** (product terms): Before any quota is spent, the pipeline has been reviewed end to end, attacked
the way a misbehaving agent would attack it, and repaired. The run can no longer:
- declare success while a test hangs or crashes;
- wedge forever, or crash on every resume, when the agent leaves a half-written file;
- leave runaway test processes behind;
- measure a tampered test build after restoring the test file;
- count the agent's own unit tests in the graded totals;
- fail provenance after a usage-limit retry;
- spend a second agent call on one attempt;
- inherit an API key or the caller's build flags.

Every graded rubric row and zero-credit trap now has a row in `MP4/docs/rubric_traceability.md`, with the
command that checks it and the evidence so far. The seven zero-credit traps from the spec are permanent
selftest assertions. The holes that need an owner decision (lint suppression, files outside `src/`,
auth-error pause, minimum iterations, agent environment, interface layout, best-vs-last, transient
errors) are written up as a seven-question batch for the start of M6.

**Deviations from spec**:
- **37 rows, not 38.** The handout has 21 point-bearing rubric rows, and why.md's table always had 21. The
  "22 rows" header was a miscount, and the spec's 38 was derived from it. The handout was re-read with
  pypdf to confirm. Counts corrected in why.md and in what.md (M5, M11).
- **T1/T2 rows: 5 of 7 verified.** R-T1-TOOLLIST and R-T2-TRAJECTORIES depend on trajectories, so they are
  `pending-run`, with their pre-run evidence pasted. The spec's "the 7 T1/T2 rows are verified" was read as
  "verified as far as they can be judged before a run" (the spec's own Goal wording).
- **Z9 marked `verified`.** It is a pipeline-side check and complete now; the spec expected the non-T1/T2
  rows to be pending-run or owner-blocked.
- **`/security-review` could not start.** Its first step needs `origin/HEAD`, which this repository does not
  have. Setting it would change the owner's git metadata, so the security pass was done by hand and
  recorded in review-1.md.
- **No per-candidate verifier agents.** The code-review recipe's separate verifier per candidate was not
  run. Candidates were verified by reproduction (by the finders or this session) or by direct reading
  (review-1.md, Method).
- **Fixes built in a scratch clone.** They were written in a scratch clone while the reviewers read the real
  tree, then ported as one patch.
- **Fixes beyond "mechanical", flagged for owner veto:**
  - the missing-init fail-closed rule;
  - the `apiKeySource` check;
  - the cap of 3 consecutive usage-limit attempts before exit 75;
  - refusing a new run while another run of the project is open.

  All four enforce documented invariants (isolation asserted on every call, D1 subscription only, no
  unattended unbounded spend), so they were treated as bug fixes rather than stop-semantics changes. They
  are listed so the owner can veto them at the M6 gate.
- **New SUCCESS blockers counted as bug fixes.** The hung-test, clippy-error and unexplained-`cargo test`-exit
  blockers make SUCCESS match its documented definition: "every test passes", and "clippy warnings 0" assumes
  that clippy ran. They are listed for the same veto.
- Spec drift count: 1 immaterial (the row count). No plan amendment proposed.

**Owner gates**: none for this row. The seven gate questions (G1–G7) are logged for M6 step 1, per spec, and
not asked here.

**Verification** (real output):
- **Self-test.** `python3 -I MP4/src/selftest.py` printed `selftest: 166 PASS, 0 FAIL` (exit 0, 86.9 s), up
  from the 120 baseline (+46).
  - The new `_run_m5` section holds the 7 guard traps through `do_checks`, and a regression for every fix.
  - Each new check was shown to fail on the unfixed code: by this session for trap (a)'s stale binary (2/2 vs
    1/2), the hang (x6: SUCCESS 1/1 vs blocked 1/2) and the parser and prompt checks; the sweep confirmed the
    rest.
  - The patched suite ran 162/162 three times in a row in the scratch clone before the sweep fixes added four
    more checks.
- **Guard traps** (M5 step 2). All seven are caught: (a) `integrity violations: 1`; (b) the same, and
  `new_dependency libc` on an unrestored copy; (c) `safety finding: extern_c` + `build_rs`; (d) `build fails`
  + `unsafe metrics: 2` + `deny_unsafe_build_failed`; (e) `hard-coding hits: 1`; (f) `interface missing 0,
  changed 1`; (g) `workspace_tamper` with `modified [fixture.rs]`, reverted. The before/after table for these
  and probes x1–x6 is in review-1.md.
- **Interface fuzz.** 861 truncations of the 6 real interface files. The original code gave 528 ok, 241 HANG
  and 92 exceptions. Fixed: 769 ok, 92 `parse_error`, 0 hangs, 0 exceptions.
- **Fresh clone.** At `5a26167`: `--help` 0, `--dry-run` 0 for both projects (92 and 94 lines), `--check-only`
  on the fixture 0, on `project_1` exit 2 (no translation yet), `summarize.py` exit 2 (PENDING), `--check-readme`
  0, `config.py` 0, selftest 120/0, tree clean. At `1ac3cd4`: the same exits, check-only on the fixture shows
  tests 0/4 (satc's declared tests) with 0 home paths in its output, selftest 166/0, tree clean.
- **Traceability.** `MP4/docs/rubric_traceability.md` has 37 rows, and its R and Z keys are identical to
  why.md (diff empty). Histogram: `7 owner-blocked, 22 pending-run, 2 proxy, 6 verified`. The T1/T2 evidence is
  pasted from the real tree (`claude --version` = `2.1.235 (Claude Code)`, matching the README).
- **Reusability.** `satc_|psbt_|compactsize` hits only selftest.py, whose assertions use the benchmark names as
  expected values. The `sk-ant-|Bearer |api_key|/Users/` grep has 3 hits, the scanner's own pattern names
  (refuted). py_compile exit 0 on 3.9.12. 11/11 entry points insert their own dir.
- **Lint.** `py_compile` exit 0; `pyflakes` exit 0; `flake8 --max-line-length 120 MP4/src/` exit 0.
- **Floor and safety checks.**
  - Scrub: `scrub_secrets.py --check MP4/` → `scrub_secrets: 0 hit(s)`; on `MP4/docs/` → 0 hits.
  - CLI: `run_pipeline.py --help` exit 0; `--dry-run` exit 0 for both projects; `summarize.py --check-readme` →
    up to date.
  - Floor `git grep -nE 'sk-ant-|Bearer |api_key=' -- MP4/ docs/`: empty over `MP4/`, 9 lines over `docs/`.
    All 9 quote the pattern itself in the program docs, including the floor line in program.yaml:44, so the
    floor item as written can never print nothing (discovery below).
  - Subjects checksums: `verify_subjects` → `{project_1: [], project_2: []}`.
  - No leftover test processes after the selftest (`ps` empty).
- **Docs-claims check.** Grepped for "22 rows" / "38 rows", "grep-checked", the Z1/Z2/Z7 guard cells, and the
  README tool-scope, isolation, `--dry-run` and usage-limit sentences. Fixed 5 count lines in what.md and
  why.md, 4 guard claims in why.md and 5 README passages, and regenerated the README stopping condition from
  `summarize.py`.
- **Spend.** No pipeline model call: no run, no smoke, the D7 envelope is untouched. The review itself ran 11
  subagents (10 finder angles + 1 sweep), about 3.2 M subagent tokens of this session's subscription, as the
  spec's `/code-review max` requires.
- **Tooling pass.** Used: `code-review`. `security-review` was attempted and could not start (`origin/HEAD`).
  `simplify` was considered and rejected: its cleanups are backlog and out of this row's scope. Workflow was not
  used (not opted into).

**NOT demonstrated**:
- No real agent has run against the fixed loop. Every behaviour above is shown with the fake agent or
  direct calls on the fixture.
- The agent receiving an unscrubbed prompt, and the `apiKeySource` check, are verified only against
  recorded streams and the fake CLI.
- Lint suppression and crate-root files still reach SUCCESS (probes x2, x3), pending G1.
- Isolation from the repo-root CLAUDE.md in the real working directory is not demonstrated (F36): the
  smoke calls ran from a temp directory.
- The SIGKILL-orphaned agent B and the tamper check on attempts after a usage-limit pause are not fixed
  (backlog).
- The libpsbt stdout-glue fix is shown on synthetic output, not on a real libpsbt test run.
- The fuzzing covers truncations of the six interface files, not arbitrary agent code.

**Discoveries logged for later rows**:
- (M6 step 1) G1–G7, review-1.md § "Owner decisions for M6 step 1".
- (M6) Scan iteration 1's assistant text for the leak markers (F36).
- (M12) Wire `safety.tool`; `course()` must return numbers, not None (F35).
- (M8) The Z2 numeric heuristic does not exist; the manual read is the only guard for project_1 (F34).
- (post-merge backlog) F33, F37–F44.
- (close-out) The floor item `git grep -nE 'sk-ant-|Bearer |api_key=' -- MP4/ docs/` always matches its own
  text in program.yaml and the program docs. Narrow it to `MP4/` (plus `docs/programs/mp4/evidence/`) or
  accept the known 9 lines.

**Queued for owner**: O9 (answer G1–G7 at the start of M6; runbook Stage 2). Optional: remove the leaked
`$TMPDIR/mp4crate_*` copies (runbook Stage 2). **O1 still deferred.** D8 remains the working assumption.

### M6 — Full run: project_1 (satc) (2026-10-29, f69ae8d + c8435d7 + this commit)

**Shipped** (product terms): satc is translated. The pipeline produced a safe Rust crate that builds, passes all
4 benchmark tests, and has no clippy warnings of its own in any of the four rubric groups. It has no unsafe code,
no FFI, and implements every interface item unchanged. The guards now close the remaining holes from review 1,
as the owner ruled at G1–G7:
- lint suppression or files planted outside `src/` can no longer fake a clean run;
- a lost login or an API outage pauses the run instead of ending it;
- a run always gets at least one review iteration;
- a run that ends without success ships its best iteration, not its last.

The full trajectory of both agent sessions is committed. The final crate is exactly what the pipeline wrote.

**Run announcement** (written to the ledger row before the run started, 18:49 UTC): opus, effort high,
max_iterations 8, min_iterations 2, max_turns 60, 45-minute wall clock, estimated 2–4 h of subscription quota.
D7 full run 1 of 1 for project_1. Started as `caffeinate -dims python3 -I MP4/src/run_pipeline.py --project
project_1 --yes`.

**Deviations from spec**:
- **Existing code modified (step 1).** The working-agreement rule asks what each function did before and why it
  changed:
  - `integrity.verify` restored immutable files only. It now also calls the new `sweep_strays` (G1a).
  - `measure_crate`, `summarize`, `evaluate` and `do_checks` did not look at lint attributes. They now run the new
    `lint_attribute_scan`, report `lint_attribute_hits` and block SUCCESS on it (G1b).
  - `decide_stop` stopped at the first SUCCESS. It now waits for `loop.min_iterations` (G3).
  - `finalize` always shipped the last iteration. At MAX_ITERATIONS and NO_PROGRESS it now ships the best (G6).
  - `_drive` stopped on `auth_error` and treated `overloaded` as a full iteration. Both now go to `_usage_limit`,
    which records the cause; a lost login always exits 75 (G2, G7).
  - `agent_runner.classify` had no connection-error class. It now reads the result text, or stderr when no
    result arrived (G7).
  - `STOP_AUTH_ERROR` was removed because it can no longer be reached.
- **Judgment calls the gate answers did not fix:**
  - G4 leak markers are recorded in `agent_result.json` and `run.log`, but do not stop the run, so a false
    positive cannot burn a D7 slot. Considered: abort on a hit.
  - G6 applies to MAX_ITERATIONS and NO_PROGRESS only, as asked; ABORT and ABORT_ISOLATION still ship the last
    iteration. Ranking is success first, then the score tuple, and on a tie the later iteration.
  - G7 waits `rate_limit.fallback_minutes` (60), the "fallback wait" in the option text.
  - G1a deletes empty directories the agent created outside `src/` without recording them; only files and links
    are violations. `.claude/` is not exempt, because under `--setting-sources project` a planted
    `.claude/settings.json` could widen the next iteration's permissions.
  - G1b skips `src/lib.rs`, which integrity restores to the wrapper's text, and flags `cfg_attr` only when it
    carries a lint level.
- **Prompt text added so the agent knows the new rules.** The system prompt now covers files outside `src/` and
  the full set of lint-level forms. `repair.md` gains a paragraph for a crate that is already clean (G3). Both are
  logged in CHANGELOG.
- **Selftest trap c changed.** `build.rs` is now removed as an `outside_src` violation before measuring, so the
  `build_rs` safety finding no longer appears in the loop. The baseline in program.yaml is updated.
- **`caffeinate` started by the session.** O6 asks the owner to keep the Mac awake. The session wrapped the run in
  `caffeinate -dims`, which ends with the run. The Mac was on AC power.
- **Cargo run by hand in `translations/project_1/`.** The spec's verification asks for `cargo test` and the rubric
  clippy command. The only side effect is the gitignored `target/`, and provenance still passes.
- **Traceability doc.** It gains a `pending-review` status definition. The stale R-T2-SRC grep evidence was
  re-run (line numbers, five stop constants), and its selftest count is now 192.
- Spec drift: none material. The run was far shorter than the 2–4 h estimate.

**Owner gates**: none asked. G1–G7 were answered in the M5 session (why.md D-M5GATES) and applied here without
re-asking, per spec.

**Verification** (real output):
- **Step 1.**
  - `python3 -I MP4/src/selftest.py` → `selftest: 192 PASS, 0 FAIL` (166 → 192, +26). There are 26 new `_run_m6`
    checks, one or more per gate, and trap c is re-expected.
  - Mutation check in a scratch copy, with each gate's code disabled: G1a/G1b assertions FAIL. G1a shows
    `(True, [], …)`, i.e. the lint cap plus planted files reach SUCCESS again (probe x3). G2 and G7 raise
    `KeyError: 'pauses'` because no pause is recorded. G3 raises `FileNotFoundError` because there is no
    iteration 2. G6 FAILs with `iter_02` shipped and `compiles False`.
  - `py_compile` exit 0, `flake8 --max-line-length 120 MP4/src/` exit 0, `pyflakes` exit 0. `--dry-run` exit 0
    for both projects; the argv carries `Bash(cargo *--config*)` and `Bash(cargo *--manifest-path*)`, and the
    prompt carries the G5 note. `summarize.py --check-readme` → up to date (stopping condition regenerated).
- **Pre-flight.** `claude auth status` → loggedIn true, claude.ai, max. `claude --version` → `2.1.235 (Claude
  Code)`. `~/.cargo/bin/cargo +nightly-2025-05-13 --version` → `cargo 1.89.0-nightly (056f5f4f3 2025-05-09)`
  (cargo is not on this shell's PATH; `mc.cargo_env` prepends it). `caffeinate` was not running, so the run was
  wrapped in it. `real_run_count` → `{project_1: 0, project_2: 0}`, `spend_check` None, no open runs.
- **Run `20261029T184931Z`.** Exit 0; `SUCCESS after 2 iteration(s)`; 18:49:31 → 18:57:06 UTC.
  `final_iteration_dir` iter_02, `final_selection` last, `usage_limit_pauses` [], `workspace_tamper` [].

  | Iter | Outcome | Turns | Agent s | Builds | Tests | Clippy agent c/s/cx/p | Harness | Safety (proxy) | Interface miss/chg | Integrity | Lint | Hard-coding | Score |
  |---|---|---|---|---|---|---|---|---|---|---|---|---|---|
  | 1 | ok | 12 | 240.1 | yes | 4/4 | 0/0/0/0 | 0/0/0/0 | 0/0/0/0 | 0/0 | 0 | 0 | 0 | [4,0,0,0,0] |
  | 2 | ok | 17 | 212.1 | yes | 4/4 | 0/0/0/0 | 0/0/0/0 | 0/0/0/0 | 0/0 | 0 | 0 | 0 | [4,0,0,0,0] |

  - Tokens: input 44, output 39 971 (thinking 22 979), cache read 914 538, cache creation 123 028. Reported
    `total_cost_usd` equivalent 2.69, but the run used subscription auth (`apiKeySource` none), so nothing was
    billed in dollars.
  - Tool calls: iteration 1 used 11 (Read 4, Write 1, Grep 1, cargo build/check/test/clippy 1 each,
    StructuredOutput 1). Iteration 2 used 16 (Read 6, Glob 2, Grep 1, Edit 1, cargo build/test/clippy, 2 × `ls
    -R`, StructuredOutput).
  - Permission denials: iteration 1 none; iteration 2 had 2, both `ls -R ~/…` (the read-only denylist working).
  - Rate-limit events: one `allowed` five_hour event per attempt; no rejection.
  - Leak markers in the agent text: `[]` for both attempts, from the real cwd inside the repo (F36's open
    question, for the text).
  - Isolation init: tools Bash, Edit, Glob, Grep, Read, StructuredOutput, Write; mcp `[]`; slash `[]`; dontAsk;
    `claude-opus-5`.
  - Iteration 2 (the G3 review pass) changed 30 diff lines. `satc_point_normalize` and `satc_point_project` now
    reproduce the C's unbraced `satc_point_set_xy` and unparenthesised `satc_point_dot`/`satc_point_len2` macro
    expansions. Checked against `satc.h:276-278, 363, 370, 485-504`: the C reads that way.
- **Step 4.**
  - `--check-only --project project_1` exit 0. The summary diff against `iter_02/check.json` is `{}`.
  - `integrity.py --provenance project_1` → `"ok": true` against `iter_02/src_after`.
  - `scrub_secrets.py --check MP4/` → 0 hits. `find MP4/trajectories -size +50M` → nothing. The run dir is
    996 KB.
  - `diff` of `src/bin/satc_test.rs`, `Cargo.toml`, `Cargo.lock` and `src/interfaces/` against `subjects/` → no
    differences.
  - Every `iter_KK/` has all 17 files and a `result` line. `grep` for `/Users/` and `claude-501` over the
    committed run and results → none.
- **By hand.**
  - The rubric clippy command in `translations/project_1` exits 0. Its warning lines are identical to
    `iter_02/clippy_rubric.log`: 2 rustc warnings, both in the harness `src/bin/satc_test.rs` (unused import
    `satc::satc`, unused fn `satc_nearest_hundredth`). That is the M1 baseline `rustc: 2`.
  - `cargo +nightly-2025-05-13 test` → `test result: ok. 4 passed; 0 failed` (satc_point_scale_xy_test,
    satc_collision_test, satc_polygon_get_centroid_test, satc_point_test).
  - One `#[allow(clippy::too_many_arguments)]` on `satc_is_separating_axis` (D-ALLOW).
- **Floor after the artifacts commit.** py_compile 0; selftest 192/0; scrub 0; `--help` 0; check-only 0;
  provenance ok; `--check-readme` up to date; `summarize.py` exit 2 `PENDING project_2` (expected before M7).
- **Secret grep.** The floor `git grep -nE 'sk-ant-|Bearer |api_key=' -- MP4/` prints 3 lines, all in
  `MP4/docs/rubric_traceability.md` (22, 51, 150), quoting the pattern itself. They were already there at
  0097efa, so M5's "empty over MP4/" was true at 1ac3cd4 only (discovery below).
- **Docs-claims check.** Grepped `AUTH_ERROR|pending G1|gate G1|still reach(es)? SUCCESS|ships the last|
  min_iterations|iterations >= 2` over README, MP4/docs, configs, the program docs and src. Fixed:
  - the README stopping condition (regenerated);
  - the run_pipeline docstring;
  - rubric_traceability R-T2-SRC: evidence block, "five stop constants", selftest count;
  - the program.yaml baselines `c_build_rs_extern_c` and `m5_open_gaps`;
  - why.md C6, now with the max-turns observation.

  The historical phase-log lines in this file are left as written.
- **Tooling pass.** The row's Tooling line is "none". The installed skills were checked: code-review is meant for
  M8, simplify is out of scope. None used. Workflow was not opted into.

**NOT demonstrated**:
- The G4 cargo denials (`Bash(cargo *--config*)`, `--manifest-path`) are shown only to be in the argv. The agent
  never tried either flag, and the D7 smoke allowance is spent, so Claude Code's matcher was not observed to deny
  them.
- G2 and G7 pauses, and G6 ship-best, were exercised only with the fake agent. The real run had no pause and
  stopped at SUCCESS.
- G1's guards fired on nothing in the real run. That shows the agent did not plant files or lint attributes, not
  that every evasion is caught. The scan is regex-level, and `src/main.rs` and non-`.rs` files inside `src/`
  are outside both guards.
- The leak-marker scan covers the agent's own text. It does not prove that `CLAUDE.md` content was absent from
  the context. Claude Code also puts the repo's git status (branch `mp4-program`, recent commit subjects) into
  its system prompt, because the crate sits inside this git repository. No marker surfaced, and that context was
  not inspected.
- The 4 benchmark tests pass, but behaviour the tests do not cover was not checked against the C here; that is
  M8. The agent's own `c_behaviour_notes` (rotation sign, AABB `y_max`, AABB UB → origin, the two macro
  expansions) are its claims, and only the two macro claims were spot-read against `satc.h`.
- What `--max-turns 60` does at the cap is unobserved: 12 and 17 turns were used.
- Safety numbers are the interim proxy, not the course tool (M12).
- `results/project_1.check.json` is not byte-stable across reruns: the timestamp, cargo timings and the order
  of keys in the per-test dict change. The summary is stable.

**Discoveries logged for later rows**:
- (M8) The C has two macro bugs the program docs do not list: the unbraced two-statement `satc_point_set_xy`
  (`satc.h:276`), which leaves `y` unguarded in `satc_point_normalize`, and the unparenthesised
  `satc_point_dot`/`satc_point_len2` (`:363`, `:370`), which change `satc_point_project`'s quotient. The
  translation reproduces both (D-FAITHFUL). Add them to why.md H-A, and check whether other macro uses in
  `satc.h` expand the same way.
- (M8) Only iteration 2's review prompt surfaced those macro bugs. Iteration 1 was clean on every check while
  diverging from the C. That is evidence for the report that the G3 review iteration adds fidelity the tests
  cannot see.
- (M10/M11) `check.json` per-test dict order follows completion order. Sort it, or compare summaries only, if
  byte-identical reruns are wanted.
- (close-out) The floor's secret grep also matches 3 self-quoting lines in `MP4/docs/rubric_traceability.md`,
  in addition to the 9 in `docs/` noted at M5. Narrow the floor item or accept the known lines.
- (M7) The run took 7.6 min against a 2–4 h estimate. libpsbt is larger and has the known-failing
  `read_test_vector` (D8), so do not assume the same.

**Queued for owner**: nothing new. O6 still applies for M7 (the session can wrap the run in `caffeinate` as it
did here, but the machine must stay on and logged in). **O1 still deferred.** D8 remains the working assumption,
and O1 must be resolved or consciously accepted before submission.

### M7 — Full run: project_2 (libpsbt) (2026-10-29, f09f89c + this commit)

**Shipped** (product terms): libpsbt is translated by the same pipeline, with the same code and prompts as satc.
Only the project file differs. The crate builds and passes 3 of the 4 benchmark tests. The fourth,
`read_test_vector`, fails for the documented reason (a defect in the benchmark test, D8) and nothing else: a
faithful parser cannot pass it. The crate has no clippy warnings of its own, no unsafe code and no FFI, and
implements all 52 interface items unchanged. The full trajectory of both agent sessions is committed, and the
committed crate is exactly what the pipeline wrote.

**Run announcement** (written to the ledger row before the run started, 19:49 UTC): same parameters as M6
(opus, effort high, max_iterations 8, min_iterations 2, max_turns 60, 45-minute wall clock), estimated 2–4 h of
subscription quota. D7 full run 1 of 1 for project_2. Started as `caffeinate -dims python3 -I
MP4/src/run_pipeline.py --project project_2 --yes`. The Mac was on battery (100 %, about 9:53 remaining), and
`caffeinate -i` blocks idle sleep on battery.

**Deviations from spec**:
- None in the pipeline: no parameter change, no prompt or config edit, no rerun of project_1.
- The phase ran in the same Claude session as M6. The owner chose "Do it here" when offered a new session.
- Cargo was run by hand in `translations/project_2/` for the spec's verification. The only side effect is the
  gitignored `target/`, and provenance still passes.
- Spec drift: none. As with satc, the run was far shorter than the estimate.

**Owner gates**: none (D7 pre-authorizes the run; no parameter changed).

**Verification** (real output):
- **Pre-flight.**
  - `project_2.yaml` has the D8 entry `read_test_vector` with `expected_assertion` "assertion `left == right`
    failed", `expected_location` `src/bin/test.rs:126`, and the rulings D-CLIMAIN "Make it pub fn main" and
    D-FAITHFUL "Faithful; define UB safely".
  - `git diff c8435d7..HEAD --stat -- MP4/src MP4/configs` is empty, before the run and after it.
  - `--dry-run --project project_2` exit 0, config_hash 7e0f3378….
  - `claude auth status` True, claude.ai, max. `cargo 1.89.0-nightly (056f5f4f3 2025-05-09)`.
  - `real_run_count` `{project_1: 1, project_2: 0}`, `spend_check` None, no open runs.
- **Run `20261029T194929Z`.** Exit 0; `SUCCESS after 2 iteration(s)`; 19:49:30 → 20:11:35 UTC.
  `final_iteration_dir` iter_02, `final_selection` last, `usage_limit_pauses` [], `workspace_tamper` [].

  | Iter | Outcome | Turns | Agent s | Builds | Tests | Known-failing verified | Clippy agent c/s/cx/p | Harness | Safety (proxy) | Interface miss/chg | Integrity | Lint | Hard-coding | Score |
  |---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
  | 1 | ok | 56 | 1069.3 | yes | 3/4 | failed, assertion ✓, location ✓ | 0/0/0/0 | style 2 | 0/0/0/0 | 0/0 | 0 | 0 | 0 | [3,0,0,0,0] |
  | 2 | ok | 31 | 245.6 | yes | 3/4 | failed, assertion ✓, location ✓ | 0/0/0/0 | style 2 | 0/0/0/0 | 0/0 | 0 | 0 | 0 | [3,0,0,0,0] |

  - Tokens: input 120, output 111 569 (thinking 73 891), cache read 5 689 092, cache creation 257 763. Reported
    `total_cost_usd` equivalent 8.21; subscription auth, so nothing billed in dollars.
  - Tool calls:
    - Iteration 1: Read 22, Glob 2, Write 5, Edit 15, cargo build 2 / test 3 / clippy 4, 1 `ls`,
      StructuredOutput.
    - Iteration 2: Read 21, Glob 2, Edit 1, cargo build/test/clippy 1 each, 1 `ls`, 1 `wc`, StructuredOutput.
  - Permission denials: 1 in iteration 1 (`ls -la`), 2 in iteration 2 (`ls -la`, `wc -l`).
  - Rate-limit events: one `allowed` five_hour per attempt.
  - Leak markers `[]` for both attempts. Isolation init clean.
- **Iteration 2 (review pass).** 16 diff lines. `cli::main` now reads `argv[1]` with `std::env::args_os()` and a
  lossy conversion: a non-UTF-8 argument is a read error, as in the C, instead of a panic.
- **M7 step-4 questions.**
  - (a) `read_test_vector` is the only failure, and it fails for the expected reason. It panics at
    `src/bin/test.rs:126:26` with `left: 4` / `right: 0`: the second record (type 4) meets the checker's
    per-callback `step = 0` (H-L1). The controller verified it failed, the assertion matched and the location
    matched, in both iterations.
  - (b) The `test` bin built under `cargo test`. By hand, `cargo +nightly-2025-05-13 test --no-fail-fast` runs
    it as both `unittests src/bin/test.rs` and `src/bin/test.rs`, each `3 passed; 1 failed`, with the H-L10
    "multiple build targets" warning. `empty_input_test`'s result line is glued behind the program's stdout,
    and it is parsed as `ok` on real output; M5 had shown that only on synthetic output.
  - (c) Unsafe never appeared. The proxy metrics are 0 in both iterations, and no agent Write or Edit input
    contains the word `unsafe`.
  - (d) H-L5 callbacks follow the clean design H-L5 describes. The public API is the interface's
    `PsbtElemHandler = fn(&mut PsbtElem, &mut dyn Any)`. `psbt_read` parses the unsigned transaction through a
    private generic `parse_btc_tx<F: FnMut(PsbtTxElem)>` (`tx.rs:62`). That closure forwards each txelem to
    the user handler and counts inputs and outputs. There are no raw pointers and no `Box<dyn Any>` smuggling.
  - (e) H-L6 error string: a `thread_local!` `Cell<&'static str>` set through `set_errmsg`, with no `static
    mut`. There are 28 call sites (psbt 25, compactsize 1, tx 2) against 29 `psbt_errmsg =` lines in the C (26,
    1, 2). The thread-local is never read: the interface fixes `psbt_geterr()` to return the constant
    `PSBT_ERRMSG`, and the agent's status says it kept that.
- **Step 4.**
  - `--check-only --project project_2` exit 0; the summary diff against `iter_02/check.json` is `{}`.
  - `integrity.py --provenance project_2` → ok against `iter_02/src_after`.
  - `scrub_secrets.py --check MP4/` → 0 hits. `find MP4/trajectories -size +50M` → nothing; the run dir is
    3.1 MB.
  - `diff` of `src/bin/test.rs`, `Cargo.toml`, `Cargo.lock` and `src/interfaces/` against `subjects/` → no
    differences. No `.c`, `.h` or `build.rs` in `translations/project_2`.
  - Interface 52 items, 0 missing, 0 changed. Every `iter_KK/` has all 17 files and a `result` line. No
    `/Users/` or `claude-501` in the committed run, results or crate.
- **By hand.** The rubric clippy command exits 0, with the same warning texts as `iter_02/clippy_rubric.log`.
  Only cargo's per-target duplicate counts and the absolute path in the H-L10 warning differ (the log is
  scrubbed). Every diagnostic points into `src/bin/test.rs`. `check.json` attributes them as clippy harness
  style 2 and rustc harness 8 (`dead_code` 6, `unused_imports` 1, `unused_assignments` 1), agent 0: the M1
  baseline exactly.
- **Floor.** py_compile 0; selftest `192 PASS, 0 FAIL` (no delta: the pipeline is unchanged); scrub 0; `--help`
  0; check-only and provenance 0 for both projects, and the rerun summaries equal the committed ones (`{}` for
  each); `--check-readme` up to date. The secret grep over `MP4/` gives the 3 known self-quoting lines (M6
  discovery). Tree clean after the commit.
- **Docs-claims check.** This phase changed no code, names or constants. Grepped the traceability doc for
  "Not yet measurable" on the P2 rows and updated R-T3-P2-COMPILE, -CORRECT and -IDIOM to `pending-review` and
  -SAFETY to the proxy numbers (4 rows).
- **Tooling pass.** The row's Tooling line is "none". No skill was used.

**NOT demonstrated**:
- Correctness beyond the 4 benchmark tests. `test_vector` and `encode_decode_test` exercise the main paths.
  The C-behaviour rulings are the agent's claims: compact-size marker overwrite, base62 index 62/63 → NUL,
  dead segwit branch, `base64_decode`'s assert-at-capacity defined as no abort, and the zero-fill reads past
  the psbt. Only the dead segwit flag was spot-read. Checking them against the C is M8.
- That `read_test_vector` could pass with a faithful parser under any reading. D8 is still the working
  assumption, and O1 (the staff ruling) is still deferred.
- The G4 cargo-flag denials were again not exercised (the agent never tried them). Pause, resume and ship-best
  were again not exercised by a real run.
- What `--max-turns 60` does at the cap: iteration 1 used 56 turns and ended `ok` with the structured status,
  4 turns short.
- Safety numbers are the interim proxy (M12).
- Whether the 28-vs-29 error-site difference loses a C error message. M8 should diff the message strings.

**Discoveries logged for later rows**:
- (M8) The H-L6 thread-local is write-only: `psbt_geterr()` returns the constant the interface specifies, so
  the 28 `set_errmsg` calls have no observable effect. Decide whether that is the faithful reading of the
  interface, and say so in the README's interventions or idiom notes. Also check the 28-vs-29 site count.
- (M8) The parameter `_src_size` in `psbt_read` is used despite its leading underscore (it mirrors the
  interface name). Clippy's default groups do not flag it, but it is an idiom point for the manual read.
- (M9 / report) Iteration 1 used 56 of 60 turns on libpsbt. A larger crate could hit the cap before the
  structured status. This is evidence for the report's discussion of per-iteration budgets. It is not a reason
  to retune, since both runs succeeded.
- (M10) Both projects now have committed run summaries and check results. `summarize.py` (results.md and LaTeX)
  was deliberately not run here; that is M10.

**Queued for owner**: nothing new. M8 (review 2) is next and asks the M9 rerun question at its gate. **O1 still
deferred.** D8 remains the working assumption, and O1 must be resolved or consciously accepted before
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
| O8 | Log the `claude` CLI in (`claude auth login`) and keep it logged in for model runs (runbook Stage 2) | The CLI's login is separate from the desktop app's; it was logged out, so agent B failed with "OAuth session expired" (first diagnosed, wrongly, as a sandbox issue) | M3 smoke; M6, M7, M9 | **done 2026-10-29** (owner ran `claude auth login`; status loggedIn true, claude.ai, max) |
| O9 | Answer the M6 gate batch G1–G7 (stop semantics and tool permissions), each with options and a recommendation in `docs/programs/mp4/reviews/review-1.md` § "Owner decisions for M6 step 1" | M5 found holes whose fixes change stop semantics or permissions; what.md M5/M6 route them to the owner at M6 step 1 | M6 | **answered 2026-10-29** (in the M5 session, at the owner's request): G1 "Both guards" (revert and record files outside src/ that are not in the skeleton, plus symlinks; and a lint-attribute scan that blocks SUCCESS except the D-ALLOW pair); G2 "Pause, resumable" (auth failure exits 75, resume after `claude auth login`); G3 "Require 2 iterations" (`loop.min_iterations: 2`); G4 "Keep env, deny flags" (keep the smoke-verified environment, M6 scans iteration 1 for leak markers, deny `--config` and `--manifest-path` on the allowed cargo commands); G5 "Add the project note" (keep every public item in `src/<module>.rs`); G6 "Ship the best" (restore the best-scoring snapshot into translations/ and name it in `final_iteration_dir`); G7 "Pause" (overloaded/connection failures pause like a usage limit, same 3-attempt cap). M6 step 1 applies them; it does not re-ask |
| O7 | After the program reports ready-to-merge: merge `mp4-program` into `main` with a merge commit and push `main` before 2026-11-18 23:59 | invariant 6/7 | submission | open |
