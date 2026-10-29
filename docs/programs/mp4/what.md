# MP4 program — what (session invariants and phase specs)

*One spec per ledger row in `where.md`. Each spec's closing "Nothing else"
clause is the scope fence. Keys like R-T2-SRC, Z1, H-L1, C4, D8 refer to
`why.md`.*

---

## Session invariants for this program

1. **Never edit generated Rust.** Nothing under `MP4/translations/` is written
   by a session or a human after the pipeline produces it. `integrity.py
   --provenance` is in the floor from M6 on and fails the phase if violated.
   The one exception is the wrapper's own documented init step (D-FORBID).
2. **Prompt and config changes are logged.** Every change under `MP4/configs/`
   after the first real run gets a dated entry in `MP4/configs/CHANGELOG.md`
   citing the trajectory evidence that motivated it.
3. **Agent B isolation is asserted, not assumed.** Every headless call checks
   the `system/init` line: tools[] equals the configured set, no MCP servers, no
   slash commands, permissionMode dontAsk, model as configured. Mismatch aborts
   the iteration.
4. **Spend is within D7's envelope or it is a gate.** Full runs are announced
   in the phase log with the estimate (iterations x turns) before they start.
5. **Real output only.** Phase logs paste command output and counts. Unknown
   numbers are PENDING, never guessed. Every phase log has a NOT demonstrated
   paragraph.
6. **Commit, never push.** One intent per commit; the ledger and phase log
   change in the phase's final commit.
7. **Python 3.9-compatible, `-I` safe, stdlib + PyYAML only.** Entry points
   insert their own directory on `sys.path`.
8. **Scrub before commit.** `scrub_secrets.py --check MP4/` passes before every
   commit that touches `MP4/trajectories/` or `MP4/docs/`.
9. **Harness-file warnings are reported separately** from agent-attributable
   ones in every clippy number, with the baseline from M1 as the reference.
10. **Tooling pass each phase**: check `ListSkills`/available skills against
    the row's Tooling line; record what was used.

### Pipeline design reference (shared by M2-M4)

Entry point `MP4/src/run_pipeline.py --project project_N` with modes `--yes`
(skip the confirmation before spending quota), `--check-only` (no model; rerun
every measurement on committed translations and write
`MP4/results/project_N.check.json`), `--dry-run` (print the exact claude argv
and the composed iteration-1 prompt), `--smoke` (isolation check, <= 2 turns),
`--resume-run <run_id>` (re-enter at the recorded step), `--run-id <id>`.

Per-iteration loop: (0) init workspace from `MP4/subjects/project_N/rust_skeleton/`
into `MP4/translations/project_N/`, inject `#![forbid(unsafe_code)]` into
`src/lib.rs`, write `.integrity/manifest.sha256`, write `run_state.json`;
(1) `prompt_builder.py` renders `configs/prompts/initial.md` (k=1) or
`repair.md` (k>1) with project context, previous diagnostics digest and a
history table → `iter_KK/prompt.md`; (2) `agent_runner.py` spawns a fresh
`claude -p` session (C1-C8), cwd `MP4/translations/project_N`, `--add-dir
MP4/subjects/project_N/c`, tees stdout to `iter_KK/agent.stream.jsonl`,
45-minute wall clock; (3) `integrity.py --verify` restores touched immutable
files and records violations; workspace re-hashed against the previous
`src_after/`; (4) `checks.py`: build, test (per-test), the exact rubric clippy
command (`clippy_rubric.log`), four per-category clippy runs attributed agent vs
harness by primary span path; (5) `safety_check.py` (proxy now, course later);
(6) `check_interface.py`; (7) hard-coding scan; (8) `src_after/` snapshot,
`changes.diff`, `diagnostics.md`, `iteration_summary.json`; (9) stop or relaunch.

Stop: SUCCESS when build ok, every test passes except `known_failing_tests`
(each verified to be the only failure and to fail on the documented assertion
text), agent-attributable clippy = 0 in all four groups, safety metrics all 0,
interface missing/changed = 0, integrity clean. MAX_ITERATIONS at 8.
NO_PROGRESS when the score tuple (tests_passed desc, build_errors asc,
clippy_agent_total asc, safety_total asc, interface_missing asc) has not
strictly improved for 3 consecutive iterations. ABORT when an integrity
violation recurs in 2 consecutive iterations. USAGE_LIMIT_PAUSE (not a stop):
sleep until resetsAt + 60 s (fallback 60 min, cap 6 h), redo the same iteration
as `iter_KK_attemptN`. TIMEOUT marks the attempt aborted and still runs checks.

Trajectory layout per project: `INDEX.md`, `run_summary.json` (final run),
`baseline/`, `run_<id>/{run_state.json, run.log, run_manifest.json,
iter_KK/...}`. Config layout: `configs/pipeline.yaml`, `claude_settings.json`,
`agent_system_prompt.md`, `prompts/{initial,repair}.md`,
`prompts/status_schema.json`, `cheatsheet_c_to_rust.md`,
`projects/project_{1,2}.yaml`, `CHANGELOG.md`.

---

## M1 — MP4 layout, subjects, toolchain, baselines

**Goal**: The required `MP4/` tree exists on the branch with pristine,
checksummed copies of both C projects and Rust skeletons under `subjects/`,
the pinned toolchain is installed and proven, and the skeletons' as-shipped
behaviour and harness-only clippy baseline are measured before any pipeline
code exists.

**Why / findings covered**: Z11, Z15, Z16, H-S1, H-S2, H-L10, E2, E6, E7,
R-T1-README (environment facts), R-T2-REPRO (install steps).

**Tooling**: none beyond shell.

**Spec**:
1. Create `MP4/README.md` (stub: the eleven required section headings — the
   nine items of why.md R-T1-README + tool list + layout, each body `TODO`), `MP4/src/`,
   `MP4/configs/`, `MP4/trajectories/project_1/`, `MP4/trajectories/project_2/`,
   `MP4/translations/project_1/`, `MP4/translations/project_2/`,
   `MP4/subjects/project_1/`, `MP4/subjects/project_2/` (`.gitkeep` where
   empty) and `MP4/.gitignore` (`translations/*/target/`, `**/__pycache__/`,
   `results/*.tmp`). Keep the repo-root `.gitignore` rule for `MP4/docs/*.pdf`.
2. Download `datasets/CRUST_bench.zip` from the CRUST-bench GitHub repo into
   the scratchpad (E6), record its sha256, extract only `CBench/satc`,
   `CBench/libpsbt`, `RBench/satc`, `RBench/libpsbt`, strip `.git/` dirs and
   `.DS_Store`. Copy to `MP4/subjects/project_1/c/`,
   `MP4/subjects/project_1/rust_skeleton/`, `MP4/subjects/project_2/c/`,
   `MP4/subjects/project_2/rust_skeleton/`. Write
   `MP4/subjects/project_N/CHECKSUMS.sha256` (every file) and
   `MP4/subjects/project_N/SOURCE.md` (archive URL, archive sha256, date,
   Group 1 assignment statement, what was stripped).
3. Toolchain (gate): show the exact commands, get the yes, run the official
   rustup installer (`--no-modify-path`, default profile minimal), then
   `rustup toolchain install nightly-2025-05-13 --profile minimal --component clippy`.
   Record `rustup --version`, `cargo +nightly-2025-05-13 --version`,
   `rustc +nightly-2025-05-13 --version`, `cargo +nightly-2025-05-13 clippy
   --version`, `sw_vers`, `python3 --version`, `claude --version`, and the
   PATH requirement in `MP4/docs/environment.md`.
4. Baseline A (scratch copy): `cargo +nightly-2025-05-13 build --all-targets
   --locked` on each untouched skeleton; record the exact failure (expected
   E0583 missing modules) in `MP4/trajectories/project_N/baseline/README.md`.
   Confirm `cargo +nightly-2025-05-13 fetch --locked` succeeds for libpsbt.
5. Baseline B (scratch copy): skeleton + `src/interfaces/<mod>.rs` copied to
   `src/<mod>.rs`; run build, test, the exact rubric clippy command, and
   `--message-format=json`; save `build.log`, `test.log`, `clippy_rubric.log`,
   `clippy.json` under `MP4/trajectories/project_N/baseline/`; classify every
   warning as harness-file (`src/bin/*`) or interface-induced with lint name
   and category in `baseline/README.md`. Verify empirically whether libpsbt's
   bin named `test` builds and whether `cargo test` runs it (H-L10); record
   verbatim.
6. Verify every R, Z, H key in `why.md` against the handout text
   (`MP4/docs/MP4 CS598JBR.pdf`, extract with pypdf) and the committed
   subjects; correct drift in `why.md` and list each correction in the phase
   log.
7. Nothing else. No pipeline code, no configs, no prompts, no Rust stubs that
   make the skeleton build (the agent must do that), no edits under
   `MP4/translations/` beyond the empty directories.

**Owner gates**: "May this session run the rustup installer and install
nightly-2025-05-13 now? Exact commands: <shown>. Network download, roughly
500 MB." (O2)

**Verification**: `ls` of the nine required paths; `shasum -a 256 -c
MP4/subjects/project_N/CHECKSUMS.sha256` passes for both; `cargo
+nightly-2025-05-13 --version` prints a 1.89.0-nightly dated 2025-05-09/12/13
(corrected M1: the pinned nightly is rustc/cargo 1.89.0-nightly, clippy 0.1.88);
Baseline A failure text recorded for both; `baseline/clippy.json` exists for
both with per-category and per-file counts pasted in the phase log and
written to `program.yaml` baselines; H-L10 answer recorded verbatim; `git grep
-nE 'sk-ant-|Bearer ' -- MP4/` empty; `git status` clean after the commit.

**Out of scope**: fixing anything in the skeletons (`std::f64::MAX` import,
the defective libpsbt test, the `test` bin quirk) — immutable benchmark
infrastructure, log only; writing any pipeline code.

---

## M2 — Checks library, integrity guards, self-test

**Goal**: A no-model checks layer exists that, for any crate directory,
produces the exact rubric clippy log, per-category agent-attributable clippy
counts, build/test results, proxy safety metrics, interface conformance,
integrity and provenance verdicts, and proves itself against a fixture crate.

**Why / findings covered**: R-T2-SRC (feedback production), R-T3-*-IDIOM,
R-T3-*-SAFETY (proxy), R-T3-*-COMPILE, Z1-Z7, Z9, Z10, H-S2, D5, D6.

**Tooling**: none.

**Spec**:
1. `MP4/src/checks.py`: `run_build`, `run_test` (per-test pass/fail + panic
   text), `run_clippy_rubric` (exact rubric command, saves `clippy_rubric.log`),
   `run_clippy_groups` (four runs `-A clippy::all -W clippy::<group>` with
   `--message-format=json`, `touch src/lib.rs` between runs; attribution by
   primary span path: `src/bin/*` = harness, else agent; rustc warnings
   counted alongside). Plain dicts out; log files named as in the design
   reference.
2. `MP4/src/safety_check.py`: `--tool proxy` (assert `#![forbid(unsafe_code)]`
   is the first non-comment line of `src/lib.rs`; `RUSTFLAGS="-D unsafe_code"`
   build in a temp copy; brace-tracked regex counts for unsafe lines, unsafe
   calls, unsafe casts (`transmute`, `as *const|*mut`), pointer arithmetic
   (`.add/.sub/.offset/.byte_add/.byte_offset/.wrapping_*` on pointer
   receivers); extras: FFI, deps, `build.rs`, `*.c`); `--tool course` wired to
   `pipeline.yaml safety.course_cmd` and failing loudly ("course safety tool
   not configured") when unset; `--all-snapshots` iterating over
   `iter_*/src_after/`. Fixed output schema `{tool, tool_version,
   unsafe_lines, unsafe_calls, unsafe_casts, pointer_arithmetic, extra,
   findings[], raw_path}`.
3. `MP4/src/check_interface.py`: extract pub items (fn signatures, structs +
   pub fields, enums + variants, consts, type aliases, impl pub fns, derives)
   from `src/interfaces/<mod>.rs` and `src/<mod>.rs`; normalise whitespace and
   comments; report missing/changed/extra. Run on the pristine skeletons and
   record item counts in `program.yaml` baselines.
4. `MP4/src/integrity.py`: `--write-manifest`, `--verify` (restore from
   `subjects/` on mismatch, return violations), `--check-workspace
   <snapshot_dir>`, `--provenance project_N` (translations `src/` ==
   final run's last `src_after/`), test-literal hard-coding scan (every string
   literal >= 20 chars in the test file grepped in library src = hard fail),
   FFI/dep/`build.rs`/`*.c` scan shared with safety.
5. `MP4/src/scrub_secrets.py --check|--fix` (`sk-ant-`, `Bearer `, `api_key=`,
   OAuth token shapes, owner email, `/Users/<name>` → `~`).
6. `MP4/src/selftest_fixture/`: a tiny non-benchmark crate (lib +
   `src/bin/fixture_test.rs` + `src/interfaces/fixture.rs`) with exactly one
   unsafe block, one transmute, one `ptr.add`, one lint from each clippy group,
   one failing test, one 20+ char test literal copied into library code, one
   interface item missing. `MP4/src/selftest.py` runs every check against it
   and asserts the expected counts; mutates a temp copy's test file and asserts
   integrity restores it; plants a secret and asserts scrub finds it. Record
   PASS count in `program.yaml`.
7. `MP4/src/run_pipeline.py` with only `--help` and `--check-only --project
   project_N` wired (writes `MP4/results/project_N.check.json`).
8. Nothing else. No agent invocation code, no prompts, no configs beyond
   hard-coded defaults marked `TODO-move-to-pipeline.yaml`.

**Owner gates**: none.

**Verification**: `python3 -I -m py_compile MP4/src/*.py` clean; `python3 -I
MP4/src/selftest.py` prints PASS for every assertion with the fixture counts
(unsafe_lines >= 1, unsafe_casts = 1, pointer_arithmetic = 1, clippy
correctness = 1, style = 1, complexity = 1, perf = 1, tests 1/2, test-literal
hits = 1, interface missing = 1, integrity violations detected = 1 restored =
1, scrub hits = 1); `check_interface.py --project project_1` on the pristine
skeleton reports all items missing with the count; `--help` exits 0;
`--check-only --project project_1` on the pristine skeleton writes
`check.json` with `build.ok false` and the E0583 text; `safety_check.py --tool
course` exits non-zero with the configured message.

**Out of scope**: perfect Rust parsing (regex-level is enough; the compile
against the immutable test file is the real conformance proof); tuning regexes
against real translations; any mode that edits Rust.

---

## M3 — Configs, prompts, agent runner, smoke run

**Goal**: Agent B can be launched headless with the exact isolation and tool
restrictions, its stream-json trajectory is captured, parsed and scrubbed,
usage limits and timeouts are detected, and a smoke run proves no
CLAUDE.md/memory/skill leakage and that git is denied.

**Why / findings covered**: R-T1-CONFIGS, R-T2-CONFIGS-PROMPTS, R-T1-TOOLLIST,
R-T2-TRAJECTORIES (format), C1-C9, H-A*, H-L*, D1, D7, D8, D-ALLOW, D-CLIMAIN,
D-FAITHFUL, D-FORBID.

**Tooling**: none.

**Spec**:
1. Owner gate first: confirm the four defaults (D-ALLOW, D-CLIMAIN,
   D-FAITHFUL, D-FORBID) in one `AskUserQuestion` batch; record answers
   verbatim in the phase log and `why.md` § D.
2. Write `MP4/configs/pipeline.yaml` (claude_bin, model opus, effort high,
   max_turns 60, max_budget_usd 30 as tripwire, max_iterations 8,
   no_progress_rounds 3, wall_clock_minutes 45, toolchain nightly-2025-05-13,
   cargo_locked true, clippy_rubric_args, clippy_groups, tools / allowed /
   disallowed, env isolation vars, setting_sources, forbid_unsafe_in_lib,
   safety {tool: proxy, course_cmd: null}, rate_limit {mode: wait,
   fallback_minutes 60, max_wait_hours 6}, digest caps),
   `claude_settings.json` (`autoMemoryEnabled false`, `disableAllHooks true`),
   `agent_system_prompt.md` (role, immutable files, interface rules, no
   unsafe/FFI/deps/hard-coding/test edits, fidelity to C over test-passing,
   single cargo commands, finish with the structured status),
   `prompts/initial.md`, `prompts/repair.md`, `prompts/status_schema.json`,
   `cheatsheet_c_to_rust.md` (pattern-level only, from why.md H-L15 and
   H-A8), `projects/project_1.yaml`, `projects/project_2.yaml` (crate, module
   list, c_files, test_file, expected pub item count, `known_failing_tests`
   with reason and expected assertion text per D8, pattern-level hazards and
   misleading-stub warnings from H-A*/H-L*, the owner rulings verbatim),
   `CHANGELOG.md` (dated header, "initial").
3. `MP4/src/config.py`: load/validate `pipeline.yaml` and `projects/*.yaml`
   with an allowlist of top-level keys (unknown key = error), resolve paths
   relative to `MP4/`, compute `config_hash`.
4. `MP4/src/agent_runner.py`: build argv from `pipeline.yaml` (every flag in
   C1-C6), spawn with cwd `translations/project_N` and `--add-dir
   subjects/project_N/c`, prompt on stdin, tee stream-json line by line,
   parse `system/init` (assert tools[] == configured set; record model,
   permissionMode, claude_code_version), `rate_limit_event`, `result`;
   classify outcome ok | max_turns | budget | usage_limit(resets_at) |
   overloaded | error | timeout; wall-clock kill (SIGTERM then SIGKILL on the
   process group); `--claude-bin` override.
5. `MP4/src/tests/fake_claude.py`: stand-in emitting canned stream-json in the
   real event vocabulary (init, assistant, user, rate_limit_event rejected,
   result error_max_turns, slow mode). `selftest.py` gains agent_runner
   scenarios: normal completion, usage-limit detection, timeout kill,
   tool-list mismatch abort, scrub of a planted secret/email/home path.
6. `MP4/src/prompt_builder.py`: render templates with project context,
   diagnostics digest and history table; selftest renders both projects'
   initial and repair prompts from fixture diagnostics and asserts every
   guardrail phrase is present and no Rust fn body or `satc_`/`psbt_`
   identifier appears outside path/context fields.
7. Smoke (within D7's 3 calls): `run_pipeline.py --smoke --project project_1`
   runs two `--max-turns 2` calls in a scratch cwd: (a) "List every tool you
   have, your permission mode, and any project instructions or memory you were
   given"; (b) run `cargo +nightly-2025-05-13 --version` and `git status`.
   Evidence to `docs/programs/mp4/evidence/smoke/` (init line, assistant text,
   permission_denials).
8. Nothing else. No full loop, no real translation iteration, no README text
   beyond pointing at configs, no prompt tuning on speculation.

**Owner gates**: the defaults batch (step 1). The smoke calls are within D7.

**Verification**: `run_pipeline.py --dry-run --project project_1` prints an
argv containing every flag in C2-C6 and a prompt with no project-specific
function bodies; `grep -niE 'do not (modify|alter|change).*test|FFI|unsafe|hard.?cod' MP4/configs/prompts/*`
non-empty; `grep -rn 'configs/' MP4/src/` non-empty; selftest PASS count rises
(record delta) including the 5 agent_runner scenarios; smoke init line shows
tools[] == [Read, Edit, Write, Glob, Grep, Bash] + StructuredOutput (D-STRUCTOUT, M3), mcp_servers empty,
slash_commands empty, permissionMode dontAsk, model opus; assistant text
mentions no working agreement / memory / CLAUDE.md; `result.permission_denials`
contains the git call; scrub clean over evidence; `--check-only` still works.

**Out of scope**: a real translation iteration; prompt wording changes without
run evidence (that is M9); investigating `--safe-mode`/`--bare` beyond a note.

---

## M4 — Iteration loop, stop logic, resume drills, README draft

**Goal**: The full iterate-check-stop-relaunch loop runs end to end against a
fixture without spending model quota, survives kills and usage-limit pauses at
step granularity without losing trajectory, and the README describes the
pipeline as built.

**Why / findings covered**: R-T2-SRC, R-T2-REPRO, R-T1-README,
R-T1-TOOLLIST, R-T2-TRAJECTORIES, R-T4-OVERALL-RESULTS (generator), Z8, C7,
D7, D8.

**Tooling**: none.

**Spec**:
1. `run_pipeline.py` full loop per the design reference: workspace init,
   `run_state.json` step cursor {init|prompt|agent|checks|closed} + `run.lock`,
   iteration directory layout, agent call, integrity verify + workspace tamper
   check, checks, safety, interface, hard-coding scan, `src_after/` snapshot
   + `changes.diff`, `iteration_summary.json`, score tuple, all stop conditions
   including the known-failing-test verification (D8), usage-limit pause with
   `rate_limit.mode` wait|exit (exit code 75 with the exact `--resume-run`
   command printed), `iter_KK_attemptN` redo, `--resume-run` re-entry at the
   recorded step, `run_summary.json`, `INDEX.md`, `run_manifest.json`
   (git HEAD, `claude --version`, rustc/cargo versions, config hashes,
   secrets-free argv, env isolation vars), `run.log`; confirmation prompt
   before a real run unless `--yes`.
2. `MP4/src/fake_agent.py` and `pipeline.yaml agent.kind: fake`: a scripted
   stand-in driven by a scenario file that copies prepared fixture variants
   into the workspace, does nothing, edits the test file, emits a synthetic
   rejected rate_limit_event, or sleeps; used only against a copy of
   `selftest_fixture`, never the benchmark.
3. Drills in `selftest.py`: A success at iteration 2; B max_iterations 1 →
   MAX_ITERATIONS; C agent does nothing → NO_PROGRESS at iteration 4; D fake
   agent edits the test file → violation recorded, restored, not green; E
   synthetic rate-limit rejected with resets_at = now + 5 s → paused and
   redone as `iter_KK_attempt2`; F SIGTERM during the agent step →
   `--resume-run` marks aborted-interrupted, runs checks, continues; G kill
   during checks → `--resume-run` reruns checks idempotently with identical
   `iteration_summary.json`; H hand edit of workspace src between iterations →
   workspace_tamper recorded and reverted.
4. `MP4/src/summarize.py`: builds `MP4/results/results.md` and `.tex` table
   fragments (overall results, clippy per category per project with harness
   counts footnoted, safety metrics with backend label, iterations) from
   `run_summary.json` + `check.json`, asserting equality with `--check-only`
   output; generates the README "Stopping condition" and "Inference settings"
   sections from `pipeline.yaml` between marker comments.
5. `MP4/README.md` draft: all required sections filled with what is known
   (framework 2.1.235 headless, model/provider/subscription, inference
   settings actually configurable and what is not, OS/runtime from
   `environment.md`, tools table, install steps, how to run including
   `--check-only` for graders without a subscription and `--resume-run`,
   generated stopping condition, usage limits marked "to be filled from
   trajectories", models/frameworks/tools table, directory layout, documented
   infrastructure interventions including D-FORBID and D8).
6. Nothing else. No real run; no report prose; no prompt tuning.

**Owner gates**: none (D7 already settled `rate_limit.mode: wait`).

**Verification**: `selftest.py` prints PASS for drills A-H with the recorded
stop reasons, iteration counts and exit codes (baseline recorded); the
scenario run directory shows `iter_01/`, `iter_02/` (and `iter_KK_attempt2/`
for E) with every file named in the design reference; `grep -nE
'max_iter|no_progress|SUCCESS|resets_at|step' MP4/src/run_pipeline.py` shows
the conditions and cursor; `py_compile` clean; `--dry-run` for both projects
exits 0; README has every required heading and the generated sections equal
`pipeline.yaml` values; `summarize.py` on fixture output produces
`results.md`; scrub clean.

**Out of scope**: spending any model budget; writing the report; making the
fake agent produce benchmark Rust; `--resume` (Claude session) modes beyond a
config switch defaulting off.

---

## M5 — Review 1: pipeline vs rubric, adversarial guard test, traceability matrix

**Goal**: Every Task 1/2 rubric row that can be judged before a run is
verified with evidence in an in-repo traceability matrix, each integrity guard
is shown to catch its zero-credit trap, a grader's fresh-clone dry audit
passes, and pipeline bugs are fixed before any quota is spent.

**Why / findings covered**: R-T1-*, R-T2-*, Z1-Z16, D4.

**Tooling**: `code-review` (max) over `MP4/src` and `MP4/configs`;
`security-review` (subprocess spawning, file writes from model output);
optionally `simplify`.

**Spec**:
1. Create `MP4/docs/rubric_traceability.md`: one row per why.md R and Z key
   (37 rows: 21 R + 16 Z; corrected M5, was 38) with columns Artifact path(s) | Verification command | Evidence
   (output excerpt or path) | Status (verified / pending-run / proxy /
   owner-blocked) | Phase. Fill the seven T1/T2 rows now by running each
   verification command and pasting real output. Write
   `docs/programs/mp4/reviews/review-1.md` with verdicts, fixes, refutations
   (what was checked and found immaterial) and the shape the bugs share.
2. Adversarial guard test against a scratch copy of the fixture workspace:
   (a) modify the test file, (b) add a dependency to Cargo.toml, (c) add
   `build.rs` + `extern "C"`, (d) add an unsafe block, (e) paste a test
   literal into library code, (f) change a pub signature, (g) hand-edit src
   between iterations; assert each is caught by the named check with the
   exact message; record in review-1.md.
3. Fresh-clone dry audit in scratch: `git clone` the branch, follow README
   install/how-to-run text literally up to the point a model is needed
   (`--help`, `--dry-run` both projects, `--check-only` on the fixture); every
   gap becomes a README fix.
4. Run `/code-review` at max and `/security-review` over `MP4/src` and
   `MP4/configs`; fix mechanical findings in-session (pipeline code and prose
   are not generated Rust); anything changing stop semantics or tool
   permissions is logged as a discovery and asked at the start of M6, not
   decided here.
5. Reusability audit: `grep -niE 'satc_|psbt_|compactsize' MP4/src/*
   MP4/configs/prompts/* MP4/configs/agent_system_prompt.md` hits are only
   path/context plumbing; `git grep -nE 'sk-ant-|Bearer |api_key|/Users/' --
   MP4/src MP4/configs` empty; Python 3.9 compatibility and `-I` safety
   confirmed.
6. Nothing else. Do not run the agent; do not touch `translations/`; prompt
   changes without run evidence are logged for M9.

**Owner gates**: none.

**Verification**: `rubric_traceability.md` has 37 rows; the 7 T1/T2 rows are
verified with pasted command + output, the rest pending-run/owner-blocked
(status histogram printed); adversarial table shows 7/7 traps caught with
check name and message; fresh-clone transcript pasted with exit codes 0;
review-1.md lists findings with severity, fix commit or row id, and >= 1
refutation; floor passes after fixes; `git diff --stat` of fixes in the phase
log.

**Out of scope**: judging translation quality (nothing is translated yet);
rewriting prompts for style; adding pipeline features the rubric does not ask
for.

---

## M6 — Full run: project_1 (satc)

**Goal**: The pipeline has translated satc end to end on the owner's
subscription, with a complete per-iteration trajectory committed under
`MP4/trajectories/project_1` and the final crate under
`MP4/translations/project_1`, untouched by hand.

**Why / findings covered**: R-T3-P1-*, R-T2-TRAJECTORIES,
R-T4-OVERALL-RESULTS (data), R-T1-README (usage-limit evidence), Z1-Z10, D7.

**Tooling**: none.

**Spec**:
1. If M5 logged discoveries that change stop semantics or tool permissions,
   ask them now in one batch and apply to configs with CHANGELOG entries.
   (M5's batch G1–G7 was answered on 2026-10-29: why.md D-M5GATES. Apply those
   answers, code and config, with a selftest check for each; do not re-ask.)
2. Pre-flight: `--dry-run --project project_1`, `claude auth status` logged
   in, toolchain present, `caffeinate` running (O6); write the run
   announcement (model, max_iterations 8, max_turns 60, estimated 2-4 h) in
   the phase log.
3. Run `python3 -I MP4/src/run_pipeline.py --project project_1 --yes`. The
   session monitors `run.log` and touches nothing in the workspace. If a
   usage-limit pause or the session boundary outlasts the run, commit
   `run_state.json` and the closed iteration dirs, mark the row
   `in-progress` with the exact `--resume-run` command in the notes; the next
   session resumes rather than restarts.
4. After the stop: `--check-only --project project_1`, `integrity.py
   --provenance project_1`, `scrub_secrets.py --check MP4/`, `find
   MP4/trajectories -size +50M`; commit `translations/project_1`,
   `trajectories/project_1` and `results/project_1.check.json` as one commit.
5. Phase log: stop reason, closed/aborted iterations, per-iteration score
   table, tests passed/total, clippy per category (agent vs harness), proxy
   safety metrics, interface verdict, permission denials, rate-limit events
   with timestamps, total turns/tokens; update `rubric_traceability.md`
   T3-P1 rows to pending-review with artifact paths.
6. If the stop reason is not SUCCESS, do not edit prompts or configs in this
   session; log the diagnosis as a discovery for M8/M9.
7. Nothing else. No manual edits under `translations/`; no prompt tuning; no
   second run; no project_2.

**Owner gates**: none (D7 pre-authorizes this run and its resume). Any
M5 discovery that changes stop semantics or permissions is asked in step 1.

**Verification**: `run_summary.json` exists with stop_reason and closed
iterations >= 2; every `iter_KK/` has the full file set with a `result` line
in `agent.stream.jsonl`; `--check-only` reproduces the final iteration's
counts exactly (JSON diff empty); provenance passes; `diff` of
`src/bin/satc_test.rs`, `Cargo.toml`, `Cargo.lock` against `subjects/` empty;
scrub clean; size scan empty; the rubric clippy command rerun by hand matches
the last `clippy_rubric.log`; `cargo +nightly-2025-05-13 test` output pasted
(target 4 passed).

**Out of scope**: fixing generated Rust by hand (forbidden and blocked by
provenance); changing prompts mid-phase; running project_2.

---

## M7 — Full run: project_2 (libpsbt)

**Goal**: The pipeline has translated libpsbt end to end with identical code
and prompts (project context from `configs/projects/project_2.yaml` only),
with the complete trajectory and final crate committed.

**Why / findings covered**: R-T3-P2-*, R-T2-TRAJECTORIES, R-T2-SRC
(reusability evidence), R-T4-OVERALL-RESULTS (data), H-L1, D7, D8.

**Tooling**: none.

**Spec**:
1. Pre-flight as M6 for project_2; confirm `project_2.yaml` carries the D8
   known-failing entry with the expected assertion text, D-CLIMAIN and
   D-FAITHFUL rulings.
2. Run `python3 -I MP4/src/run_pipeline.py --project project_2 --yes` with
   the same parameters as M6. Any parameter change is an owner gate, recorded
   in `pipeline.yaml`, `CHANGELOG.md` and the phase log, and applies to both
   projects going forward.
3. Same monitoring, pause/resume, post-run checks and single commit as M6.
4. Phase log as M6; additionally record whether `read_test_vector` failed for
   the expected reason and was the only failure, whether the `test` bin built
   under `cargo test`, whether unsafe ever appeared in any iteration, and how
   the agent handled the fn-pointer/dyn Any plumbing (H-L5) and the global
   error string (H-L6).
5. Nothing else. No manual edits under `translations/`; no prompt tuning; no
   rerun of project_1.

**Owner gates**: none within D7; any parameter change from M6 is a gate.

**Verification**: as M6 for project_2; additionally `git diff <M6 commit>..HEAD
-- MP4/src` is empty (identical pipeline code) and `git diff <M6
commit>..HEAD -- MP4/configs` shows only `project_2.yaml` or owner-approved
changes recorded in CHANGELOG; test output shows 3 or 4 passed with the
known-failing test, if failing, failing inside the checker; `ls
MP4/translations/project_2` contains no C sources or `build.rs`; interface
items complete.

**Out of scope**: hand edits to generated Rust; modifying the benchmark test;
adding the `hex` crate or any dependency; renaming the `test` target; writing
callback plumbing code "to help".

---

## M8 — Review 2: translations and trajectories vs rubric

**Goal**: Both translations and their trajectories are independently
re-measured and audited against every Task 3 row (compile, correctness
including anti-hard-coding and behavioural spot checks against the C, proxy
safety, idiomaticity including structural inspection), the trajectory row and
every zero-credit trap, with a decision table on whether a tuning rerun is
warranted.

**Why / findings covered**: R-T3-*, R-T2-TRAJECTORIES, R-T2-SRC, Z1-Z16, D4,
D5.

**Tooling**: `code-review` (max) over the diff since M5 (orchestration only);
`Workflow` for parallel readers over both trajectories (one per iteration)
extracting candidate repair examples, judged for R-T4-REPAIR-ANALYSIS.

**Spec**:
1. Independent re-measurement from a fresh clone in scratch: `cargo clean`,
   then build/check/test and the exact rubric clippy command by hand for both
   projects; compare to `run_summary.json` and results; any mismatch is a
   pipeline bug (fix) or a provenance failure (report).
2. `docs/programs/mp4/reviews/review-2.md` and `rubric_traceability.md` rows
   T3-P1-*, T3-P2-*, T2-TRAJECTORIES, Z1-Z16 with pasted commands/output:
   byte-identity of test files, `Cargo.toml`/`Cargo.lock`, `lib.rs` (modulo
   the documented forbid line), interfaces vs `subjects/`; pub-signature diff
   per module; grep for unsafe/FFI/`build.rs`; hard-coding scan plus a manual
   read of every function that consumes test-visible inputs; `grep -rn
   'allow(clippy'`; unwrap/expect/panic/clone counts; iteration count >= 2 and
   equal across `run_summary.json`/`INDEX.md`; secret and size scans;
   trajectory hashes vs `run_manifest`; each `prompt.md` after iter_01
   contains compiler/test/clippy/safety feedback text.
3. Behavioural spot check vs the C (scratch, never committed into
   `translations/`): compile the C with `/usr/bin/cc` and compare 3-5 non-test
   inputs per project against the Rust via a scratch example binary linking
   the translated crate (satc polygon-polygon with rotated polygons; libpsbt
   compactsize 252/253/65535/65536 and a base64 round trip); classify
   divergences as faithful-bug vs translation defect.
4. Structural inspection per rubric 3.4 (ownership, types, control flow,
   error handling, organisation) with file:line examples, plus the shape
   question (what do the defects have in common?).
5. Mine candidate repair examples (what generated / why wrong / feedback /
   repair / outcome, tagged correctness/safety/idiomaticity) from the
   trajectories into `docs/programs/mp4/reviews/repair-candidates.md` for M10.
6. `/code-review` (max) over the diff since M5; fix mechanical findings in
   `MP4/src`/`MP4/configs` only. Decision table: for each gap, the proposed
   prompt/config change and whether a rerun is worth the quota; present as
   one batch to the owner; record the decision verbatim; flip M9 to
   `not-started` (with the chosen project(s) in its notes) or `dropped`.
7. Nothing else. No edits to `translations/`; prompt/config edits are proposed
   here and made only in M9.

**Owner gates**: "Given the review-2 decision table, run the optional tuning
rerun M9 for project_1, project_2, both, or neither? Each rerun costs another
2-4 h of plan quota (within D7's two-rerun envelope). If a project's ceiling
is reached (libpsbt 3/4 under D8), accept rather than rerun?"

**Verification**: review-2.md and `rubric_traceability.md` show the 9 T3/T2
rows plus Z1-Z16 with pasted outputs and a verdict each (safety rows marked
proxy); hand-run numbers equal `run_summary.json`/results (table, zero
mismatches after fixes); behavioural spot-check table with >= 3 inputs per
project; `repair-candidates.md` has >= 5 candidates with trajectory paths;
provenance and checksum checks pass; owner decision on M9 recorded verbatim
and the M9 row flipped; floor passes.

**Out of scope**: hand-fixing anything in `translations/` (strongest
temptation here: a one-line clippy fix is still forbidden); editing prompts in
this session; drafting Task 4 text.

---

## M9 — Tuning rerun (optional — owner-triggered)

**Goal**: Prompt or orchestration changes motivated by review 2 are applied,
logged, and the affected project(s) rerun from the pristine skeleton as a new
run, with the previous run preserved for the report's before/after story.

**Why / findings covered**: R-T3-* (improved), R-T4-REPAIR-ANALYSIS
(before/after evidence), R-T4-REFLECTION, D5, D7.

**Tooling**: none.

**Spec**:
1. Apply only the owner-approved changes from the review-2 decision table to
   `MP4/configs/` (and `MP4/src/` only for orchestration defects); each change
   gets a dated `CHANGELOG.md` entry citing the evidence iteration; the phase
   log states what each changed thing did before and why.
2. Rerun `run_pipeline.py --project project_N --yes --run-id run_02` for the
   chosen project(s); the previous run stays under
   `trajectories/project_N/run_01/`; `INDEX.md` marks which run is final
   (default: the better-scoring one on the rubric tuple, documented);
   `translations/project_N` holds the final run's output; provenance points
   at it.
3. Post-run checks and commit exactly as in M6/M7. A generic prompt change
   applied for one project is re-validated against the other by
   `--check-only` and, if it would plausibly change its outcome, queued as an
   owner question for a second rerun (still within D7).
4. At most two tuning rounds total across the program; a third requires the
   owner to add a row.
5. Nothing else. No hand edits to Rust; no changes unrelated to the approved
   findings; no change to the stopping condition to make a run look green.

**Owner gates**: "If run_02 scores worse than run_01 on the rubric tuple,
which run is submitted as final? (default: the better-scoring one, documented
in INDEX.md and README)".

**Verification**: as M6/M7 for the rerun; `git diff` of `configs/` matches the
approved change list and CHANGELOG has one entry per change; both runs'
`run_summary.json` present; `INDEX.md` marks the final run; provenance passes
against the final run; results regenerated.

**Out of scope**: a third run without a new owner gate; hand-patching Rust;
adding function-level hints to prompts.

---

## M10 — Results, README finalisation, report draft

**Goal**: Every number the report needs is generated from committed
artifacts, the README is complete and truthful, and the MP4 report section
exists in-repo as Markdown plus LaTeX with generated tables, a pipeline
diagram and >= 3 trajectory-traced repair examples, with official-metric
cells marked PENDING rather than invented.

**Why / findings covered**: R-T1-README, R-T1-TOOLLIST, R-T2-REPRO, R-T4-*
(drafts), D-DIAGRAM, D-TRAJ.

**Tooling**: `Workflow` to have independent readers score the
`repair-candidates.md` entries and a judge pick the three (one correctness,
one safety if any unsafe ever appeared, one idiomaticity).

**Spec**:
1. `summarize.py`: regenerate `MP4/results/results.md` and `.tex` fragments
   for both projects (Overall results; Safety with backend label "interim
   proxy — official tool PENDING"; Idiomaticity agent-attributable with
   harness counts footnoted; per-iteration trend tables; usage-limit digest
   from `rate_limit_event` records); add a repair-example miner that emits the
   feedback digest and `changes.diff` stats per iteration so examples cite
   `trajectories/project_N/run_*/iter_KK/<file>`.
2. `MP4/README.md` final: usage limits from `rate_limit_event` and pause
   records (or "none observed" with the grep that shows it); tools table
   cross-checked two-way against trajectory tool names; generated stopping
   condition and inference settings re-synced; how to reproduce including
   `--check-only`, `--resume-run` and the subscription-login requirement;
   documented infrastructure interventions (D-FORBID, scrub, D8 ruling, any
   restores) each with "program logic affected: no"; academic-integrity
   statement.
3. `MP4/docs/report_mp4_draft.md` and `report_mp4_draft.tex` with all six
   sections: pipeline description (framework, model, tools, how each feedback
   channel returns to the agent, single agent / single model statement,
   stopping condition) + diagram (`MP4/docs/pipeline_diagram.mmd` for README;
   TikZ in the .tex); overall results table; safety table (proxy, labelled) +
   the four discussion points citing C constructs in `subjects/` and
   per-iteration proxy counts; idiomaticity table + discussion citing lint
   names with before/after counts; translation and repair analysis with >= 3
   examples each giving generated / why wrong / feedback / repair / outcome,
   tagged, each citing a trajectory path (if unsafe never appeared, say so and
   substitute a labelled second correctness or idiom example); reflection
   answering all five prompts. Headings follow the MP1-MP3 sectioning of the
   existing report (`MP4/docs/CS598JBR_Report_Team_1.pdf`).
4. Update `rubric_traceability.md` T1/T4 rows with artifact paths and Status
   (T4 "drafted — Overleaf pending"; safety "proxy — official pending").
5. Nothing else. No Overleaf, no PDF, no changes to `translations/` or
   pipeline logic beyond `summarize.py`.

**Owner gates**: none (D-DIAGRAM settled; teammates' co-authoring is O5's
concern).

**Verification**: `summarize.py` asserts results equal `--check-only` output
for both projects (exit 0); README section count complete and the two-way
tool-name diff empty (pasted); draft has 6 top-level sections, the three
tables byte-identical to the generator output (regenerate and diff), >= 3
examples each with 5 sub-points and a cited trajectory path that exists
(`test -e`) and whose quoted message greps in that file; `grep -c PENDING
MP4/docs/report_mp4_draft.tex` recorded (> 0 until M12); Mermaid source
present; scrub clean; floor passes.

**Out of scope**: polishing prose beyond rubric completeness (D10); official
safety numbers; inventing a usage-limit anecdote; editing `translations/`.

---

## M11 — Review 3: README, report draft, trajectories, fresh-clone reproducibility

**Goal**: Everything a grader will read or run is verified against the full
22-row checklist from a fresh clone, numbers agree across README, results,
report and trajectories, and the branch is in a state the owner could submit
as-is if the blocked rows never cleared.

**Why / findings covered**: all 21 R keys, Z1-Z16, D4, D9.

**Tooling**: `code-review` (max) over the diff since M8.

**Spec**:
1. Rubric walk: for each of the 21 rows run the verification from `why.md`
   against a fresh clone in scratch (`--help`, `--dry-run` both projects,
   `--check-only` both projects after `cargo clean`); mark verified / proxy /
   owner-blocked in `rubric_traceability.md` with pasted evidence; every T4
   row checked in full against the handout bullets.
2. Three-way consistency table: README, configs, results and report draft
   agree on framework version, model, effort, max turns, tools list, stopping
   values, iteration counts, test counts, clippy and safety numbers; fix prose
   mismatches in README/report in-session, never in trajectories or
   translations.
3. Integrity sweep: secret and personal-data scan of the whole `MP4` tree and
   `git log -p -- MP4 | grep -cE 'sk-ant-'` == 0; `find MP4 -size +50M`; no
   PDFs committed; provenance for both projects; trajectory hashes vs
   `run_manifest`.
4. `/code-review` (max) over the diff since M8; fix mechanical findings;
   `docs/programs/mp4/reviews/review-3.md` with findings, refutations, shared
   shapes, and a "submission as-is" statement listing exactly what is
   proxy/pending (official unsafe metrics, validation script, Overleaf).
5. Nothing else. No edits to `translations/`; no Overleaf; any finding needing
   a rerun is queued as an owner question.

**Owner gates**: none.

**Verification**: `rubric_traceability.md` status histogram printed: 21 rows
none pending except exactly the owner-blocked ones; fresh-clone output pasted
with exit codes 0; consistency table with zero mismatches after fixes; scans
clean; provenance exit 0 both projects; review-3.md committed; floor passes.

**Out of scope**: touching generated Rust; writing final safety numbers;
pushing; polishing translations.

---

## M12 — Official unsafe-metrics tool: adapter, retroactive measurement, table swap

**Goal**: The course unsafe-metrics tool replaces the proxy in the pipeline
and the report, both final translations and every historical iteration
snapshot carry official numbers recorded beside the trajectories, and the
safety discussion rests on official data.

**Why / findings covered**: R-T3-P1-SAFETY, R-T3-P2-SAFETY,
R-T4-SAFETY-ANALYSIS, D6, D9.

**Tooling**: none.

**Spec**:
1. Precondition in code: `safety_check.py --tool course --probe` must find
   the tool at `pipeline.yaml safety.course_cmd` (owner places it under
   `MP4/tools/unsafe-metrics/` or a documented external path per the
   runbook); if absent, keep the row blocked and stop.
2. Write the course adapter (json key map or regex table) from the tool's
   real output; add a fixture of its real output to `selftest.py`; set
   `safety.tool: both` so proxy and official are reported side by side.
3. Run `--check-only` for both projects and `safety_check.py --all-snapshots`
   over every `run_*/iter_KK/src_after/`; store raw output as
   `trajectories/project_N/official_safety/<date>/raw_final.txt` and
   `raw_iter_KK.txt`; update `check.json` and `run_summary.json` safety
   blocks.
4. Regenerate results and the report/README safety tables and discussion with
   official values (remove PENDING and the proxy label; keep a
   proxy-vs-official comparison line); update `rubric_traceability.md`
   T3-*-SAFETY and T4-SAFETY-ANALYSIS to verified.
5. If any primary metric is nonzero on a final translation: do not edit Rust;
   show the owner the counts and offending lines and propose a prompt /
   orchestration change plus an owner-gated rerun as a new M9-shaped row.
6. Nothing else. No Rust edits; no rerun inside this row; no retroactive
   change to the proxy regexes to match the tool (log differences).

**Owner gates**: supplying the tool (O3); "If official metrics are nonzero:
authorize a tuning rerun for the affected project?".

**Verification**: `official_safety/` raw outputs present for both final
translations and every snapshot; `check.json` safety block shows `tool: both`
with the four official metrics and `tool_version`; results/README/report
safety tables equal the raw tool output (pasted side by side); `grep -c
PENDING` on report and README safety cells == 0; `selftest.py` still PASS
including the course-output fixture; provenance exit 0; floor passes.

**Out of scope**: reworking the stop condition retroactively; hand-editing
Rust to drive metrics to zero; modifying the tool.

---

## M13 — Course validation script run and structural fixes

**Goal**: Both submissions pass the instructional team's validation script as
the owner received it, and any infrastructure-only issue it reveals is fixed
and documented without touching program logic.

**Why / findings covered**: Z11, Z16, R-T3-*-COMPILE, R-T2-REPRO,
R-T1-CONFIGS (structure), R-T2-TRAJECTORIES (presence), D9.

**Tooling**: none.

**Spec**:
1. Precondition: the script is present at the path the owner names (per the
   runbook, `MP4/tools/validate/` or external, recorded in the runbook);
   otherwise keep the row blocked and stop.
2. Run it from a fresh clone of the branch on `MP4/translations/project_1`
   and `project_2` (and the MP4 layout if it checks structure); commit full
   output under `docs/programs/mp4/evidence/validation/<date>/` and
   `MP4/docs/validation_output.txt`.
3. Classify every reported issue: layout/infrastructure (fixable here with
   `git mv`, `CHECKSUMS.sha256` regenerated, config paths and README updated,
   documented in README interventions with "program logic affected: no") vs
   program-logic (requires an owner-gated pipeline rerun — new row) vs
   validator expectation mismatch (document; raise with staff if the owner
   agrees).
4. Update `rubric_traceability.md` and the report's results section if the
   validator's numbers differ from ours; `--check-only` both projects after
   any move.
5. Nothing else. No manual Rust repair even if the fix is "one line"; no
   change to tests or interfaces to satisfy the validator.

**Owner gates**: supplying the script (O4); confirming any file move it
demands; authorizing any rerun it necessitates.

**Verification**: validator output committed for both projects with exit
codes; classification table of every reported issue; `git diff --stat` of
fixes limited to moves/configs/README (printed); `integrity.py --verify` and
provenance exit 0 after moves; `--check-only` both projects exit 0; scrub
clean; floor passes.

**Out of scope**: anything beyond structure; interpreting a validation pass as
full credit; editing translations.

---

## M14 — Review 4: Overleaf placement check and merge handoff

**Goal**: The MP4 section is in the team's Overleaf report with tables and
examples identical to the in-repo draft and final numbers, every rubric row is
verified, and the owner has an exact handoff packet for merge and submission.

**Why / findings covered**: R-T4-*, R-T1-README (final), D4, D9, D10.

**Tooling**: `anthropic-skills:pdf` or pypdf for extracting the export.

**Spec**:
1. Precondition: the owner has pasted `report_mp4_draft.tex` (and the diagram)
   into Overleaf and exported the PDF to
   `MP4/docs/CS598JBR_Report_Team_1.pdf` (gitignored); otherwise keep the row
   blocked and stop.
2. Extract the PDF text and verify each Task 4 row: 6 section headings, both
   tables' exact column headings and the row labels satc/libpsbt, >= 3
   examples x 5 sub-points, reflection 5 prompts; diff every table value and
   example quote against `results.md` / `report_mp4_draft.md`; list
   discrepancies for the owner to fix in Overleaf; re-check once; record in
   `docs/programs/mp4/reviews/review-4.md`.
3. Final consistency: regenerate tables (`summarize.py`), rerun the three-way
   consistency table, secret scan, provenance, size guard; `grep -c PENDING`
   == 0 or list what remains and why (if M12/M13 were dropped);
   `rubric_traceability.md` every row verified; top-level repo README
   mentions MP4.
4. Write `docs/programs/mp4/handoff.md` and the runbook's final section: exact
   owner commands to merge `mp4-program` into `main` (merge commit, never
   squash), push `main`, and the submission checklist; sessions never push.
5. Nothing else. No code changes, no translations changes, no push, no PR, no
   edits to MP1-MP3 report sections.

**Owner gates**: the Overleaf export (O5); "Confirm M12/M13 outcomes (done or
dropped) before the numbers are declared final."

**Verification**: PDF text extraction shows the 6 section headings, both
tables' column headings and row labels; value-by-value comparison with
`results.md` shows zero mismatches (or the list the owner fixed and the
re-check); `rubric_traceability.md` histogram all 22 verified; PENDING count
printed; provenance exit 0 both projects; `git status -sb` shows the branch
not pushed; review-4.md and handoff.md committed; floor passes.

**Out of scope**: rewriting MP1-MP3 sections; any pipeline or Rust change;
pushing from a session; last-minute "small" Rust fixes.
