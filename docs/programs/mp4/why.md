# MP4 program — why (evidence, rubric keys, hazards, decisions)

*Every phase in `what.md` cites keys from this document. The handout itself
is `MP4/docs/MP4 CS598JBR.pdf` (gitignored, local reference only). Row M1
verifies the rubric keys below against the handout text and corrects any
drift before any code is written.*

Source of truth for grading: the MP4 handout, 430 points, due 2026-11-18
23:59. Group 1: project_1 = `satc`, project_2 = `libpsbt` (CRUST-bench).

---

## R — Rubric rows (21 rows, 430 points)

*Corrected M5 (2026-10-29): the handout lists 3 + 4 + 2 x 4 + 6 = 21 point-bearing
deliverables; the earlier "22 rows" was a miscount (the table always had 21).*

| Key | Task | Pts | Requirement (condensed from handout) | How a reviewer verifies it from the repo | Owner-blocked |
|---|---|---|---|---|---|
| R-T1-README | 1 | 15 | README.md covers: framework + version, model + provider (or local runtime), inference settings, OS/runtime, external tools available to the agent, dependency install steps, how to run, stopping condition, usage limits that affected the experiment | `test -f MP4/README.md`; one heading per item; framework version equals `claude --version`; model equals `configs/pipeline.yaml`; "how to run" command exists in `MP4/src/` | no |
| R-T1-CONFIGS | 1 | 15 | Configuration files under `configs/` (agent/model config, prompts, settings); never commit credentials | `ls MP4/configs/` non-empty; `grep -rn 'configs/' MP4/src/` proves src loads them; `git grep -nE 'sk-ant-\|api_key=' -- MP4/` empty | no |
| R-T1-TOOLLIST | 1 | 10 | A clear list of models, frameworks and tools used | README table; every tool name in it appears in trajectories (`grep -oh '"name":"[A-Za-z]*"' MP4/trajectories/project_*/run_*/iter_*/agent.stream.jsonl \| sort -u`) and vice versa | no |
| R-T2-SRC | 2 | 45 | Iterative agentic workflow in `src/`: inspect C, generate Rust, build, test, observe feedback, repair, repeat; reusable across both projects; no hard-coded C function implementations; clear stopping condition | Read `run_pipeline.py`: outer loop, stop conditions, cargo +nightly-2025-05-13 invocations, feedback written into next prompt; `--project` parameter; `grep -niE 'satc_\|psbt_' MP4/src/*` hits only path/context plumbing | no |
| R-T2-CONFIGS-PROMPTS | 2 | 20 | Pipeline configuration and prompts under `configs/` | prompts present; guardrail phrases greppable (`do not modify.*test`, `FFI`, `unsafe`, `hard-cod`); no function bodies in prompts | no |
| R-T2-TRAJECTORIES | 2 | 35 | Complete trajectories per project under `trajectories/project_N/`: prompts, model interactions, tool calls, files modified, diagnostics, test failures, clippy, safety output, repair iterations, final status; secrets removed | both dirs non-empty; per-iteration stream-json + check logs + summary; iterations >= 2; iteration count equals report; secret scan empty | no |
| R-T2-REPRO | 2 | 20 | A command or script that reproduces the pipeline on an assigned project | README "how to run" is copy-pasteable; `--dry-run` and `--check-only` exit 0 from a fresh clone | no |
| R-T3-P1-COMPILE | 3 | 15 | satc builds with nightly-2025-05-13 and matches the required interface and test harness | `cargo +nightly-2025-05-13 build --all-targets --locked` in `MP4/translations/project_1` exits 0; `check_interface.py` reports 0 missing/changed; test file byte-identical to `subjects/` | no |
| R-T3-P1-CORRECT | 3 | 40 | 40 x (tests passed / total); hidden tests possible; hard-coded outputs = 0 | `cargo +nightly-2025-05-13 test` output; hard-coding scan; behavioural spot checks vs C (M8) | no |
| R-T3-P1-SAFETY | 3 | 25 | Unsafe lines, calls, casts, pointer arithmetic all 0 (course unsafe-metrics tool); FFI = 0 pts; measured on generated Rust only (dependencies, std and benchmark infrastructure excluded) | proxy now: `#![forbid(unsafe_code)]` present + `-D unsafe_code` build + regex counts (`safety_check.py --tool proxy`); official: `--tool course` (M12) | **yes** (official numbers) |
| R-T3-P1-IDIOM | 3 | 20 | Clippy correctness/style/complexity/perf each targeting 0 (sum 0-10 = 20 pts) plus structural inspection | the exact rubric clippy command; per-category counts attributed agent vs harness; structural checklist (M8) | no |
| R-T3-P2-COMPILE | 3 | 15 | same as P1 for libpsbt | same in `MP4/translations/project_2` | no |
| R-T3-P2-CORRECT | 3 | 40 | same as P1 for libpsbt | same; note H-L1 (defective test) ceiling 3/4 | no |
| R-T3-P2-SAFETY | 3 | 25 | same as P1 for libpsbt | same | **yes** (official numbers) |
| R-T3-P2-IDIOM | 3 | 20 | same as P1 for libpsbt | same | no |
| R-T4-PIPELINE-DESC | 4 | 10 | framework(s), model(s), tools; how compiler/test/clippy/safety feedback returned to the agent; single vs multiple agents/models; stopping condition; diagram encouraged | report section present with all 5 bullets + diagram | **yes** (Overleaf placement) |
| R-T4-OVERALL-RESULTS | 4 | 10 | table: Project, Compiles, Tests Passed, Total Tests, Pass Rate, Agent Iterations — one row per project from the final implementations | table equals `MP4/results/results.md` generated by `summarize.py` | **yes** (Overleaf) |
| R-T4-SAFETY-ANALYSIS | 4 | 15 | table: Unsafe Lines, Unsafe Calls, Unsafe Casts, Pointer Arithmetic (+ extra metrics) from the course tool; discuss which project needed most unsafe, which C constructs caused it, whether pointers were replaced, whether safety improved across iterations | table equals official tool output (M12); discussion cites `subjects/` constructs and per-iteration counts | **yes** (tool + Overleaf) |
| R-T4-IDIOM-ANALYSIS | 4 | 10 | table: Correctness, Style, Complexity, Performance per project; discuss C-style loops, clones, complexity, string handling; whether clippy feedback improved the translation | table equals generated results; discussion cites lint names from clippy logs | **yes** (Overleaf) |
| R-T4-REPAIR-ANALYSIS | 4 | 15 | major problems; >= 3 concrete examples each with: what was generated, why wrong/unsafe/non-idiomatic, feedback received, repair attempted, success; ideally one correctness, one safety, one idiomaticity | each example cites a trajectory path that exists and whose quoted message greps in it | **yes** (Overleaf) |
| R-T4-REFLECTION | 4 | 10 | what worked; main limitation; which feedback signals improved output; hardest C constructs; what to change with more time | all five prompts answered | **yes** (Overleaf) |

Total: 40 + 120 + 200 + 70 = 430.

Per-project Task 3 split: compile 15, correctness 40, safety 25, idiom 20.
Compile bands: fully compiles and matches interface 15; compiles with minor
integration/interface problems 10; substantial implementation that does not
build 5; little or no compilable Rust 0. Correctness = 40 x passed/total,
"may be rounded to the nearest whole point".
Safety bands: all zero 25; 1-10 findings 18; 11-20 findings 10; >20 findings 4;
FFI 0. Idiom bands by clippy sum: 0-10 = 20; 11-20 = 15; 21-30 = 8; more = 3.
(Handout text for the last idiom band literally reads "more than 22", which
overlaps the 21-30 band; read as a typo for >30. Verified M1, 2026-10-28.)

## Z — Zero-credit traps (verbatim or near-verbatim from the handout)

| Key | Trap | Guard in code |
|---|---|---|
| Z1 | Altering benchmark tests or required public interfaces to force a pass may result in zero credit for the affected categories | `integrity.py` checksum manifest; restore + record; iteration can never be green. M5: files the agent adds outside `src/` (`.cargo/config.toml`, `clippy.toml`, `tests/`, `build.rs`) are not reverted; review-1 G1, asked at M6 |
| Z2 | Detecting benchmark inputs and returning hard-coded outputs receives zero functional-correctness credit even if visible tests pass | test-literal hard-coding scan (M5: satc's harness has no string literals, so it cannot fire for project_1); the `if <expr> == <literal> { return` heuristic is not implemented in code (M5), so the M8 manual read is the guard |
| Z3 | Calls the original C implementation through FFI = 0 safety points; the Rust must implement the behaviour itself | `safety_check.py` fails on `extern "C"`, `#[link`, `libc::`, `cc::`, `build.rs`, any `*.c`/`*.h` under translations |
| Z4 | Wrapping unsafe inside a safe-looking function does not remove it from the metrics | regex counts count every unsafe region regardless of wrapper |
| Z5 | Do not modify the provided tests (reading and running is allowed) | Z1 guard; agent has no git; test files in manifest |
| Z6 | Do not replace the specified Rust interface | `check_interface.py` pub-item diff; interfaces in manifest |
| Z7 | Do not manually repair individual translated functions; prompts, agent config, orchestration and reruns are allowed; infrastructure interventions must be documented | `integrity.py --provenance` (translations == the snapshot of the final run's `final_iteration_dir`, M5) in the floor; `configs/CHANGELOG.md`; README interventions section |
| Z8 | A single "translate this project" prompt saved to disk does not satisfy Task 2 | loop with >= 2 iterations recorded; feedback text in every repair prompt |
| Z9 | Supplying project-specific context is allowed; hard-coding individual C function implementations is not | selftest asserts no Rust fn bodies for interface items in configs/ or src/ |
| Z10 | Never commit API keys, tokens, passwords or credentials; remove secrets from trajectories | `scrub_secrets.py --check` on write, before commit, in the floor; `git log -p` scan before the owner pushes |
| Z11 | Do not rename or remove the required directories; minor additions allowed | M1 creates exact names; M13 validator (handout: it "checks the required directories, project names, configuration files, trajectories, and translations") |
| Z12 | A submission without configuration and trajectories demonstrating the agentic workflow may lose Task 2 points even if the code is correct | R-T2-* rows |
| Z13 | If the project does not compile sufficiently to run tests, correctness may be zero | build is the first stop-condition term |
| Z14 | Academic integrity: no copying other teams' or existing Rust translations, no exchanging implementations, no hard-coded outputs, no modified tests, no undocumented manual repair | agent B has no network tools; provenance; CHANGELOG |
| Z15 | All submitted Rust must compile and run with nightly-2025-05-13; the pipeline must use the same toolchain | `+nightly-2025-05-13` hard-coded in `checks.py`; recorded in `environment.md` |
| Z16 | Graders must be able to clone and evaluate without reconstructing files from a transcript | translations committed; `--check-only` documented in README |

## H — Project hazards (from reading CBench/RBench; M1 re-verifies on the committed copies)

### Shared
- H-S1 Skeleton layout trap: `src/lib.rs` declares `pub mod <name>;` which resolves to `src/<name>.rs`; the spec files live in `src/interfaces/<name>.rs` and are never compiled. The skeleton does not build as shipped (E0583). The agent must create `src/<mod>.rs` reproducing every pub item.
- H-S2 `cargo clippy --all-targets` compiles `src/bin/*.rs` as a bin and as a test harness; the immutable test files emit warnings the agent cannot fix. The pipeline must baseline them (M1) and attribute agent vs harness per category. M1 measured (unique sites, `trajectories/project_N/baseline/README.md`): satc harness = 0 in all four clippy categories (only rustc `dead_code` + `unused_imports`); libpsbt harness = style 2 (`single_match`, `uninlined_format_args`), others 0, plus 8 rustc warnings.
- H-S3 `cargo test` on a bin target: tests live in `src/bin/<name>.rs` with `fn main() {}`; `use <crate>::<mod>` imports.
- H-S4 Both interfaces are complete with respect to the tests but omit private C helpers; the agent must add private helpers and may add extra pub fns (minor additions).
- H-S5 Exact-value assertions: satc compares f64 with `assert_eq!`; libpsbt compares hex strings and lengths. Operation order must match the C.

### satc (project_1)
- H-A1 Pure arithmetic, no I/O, no callbacks; no unsafe is ever needed. Risk is needless `.clone()` on Copy `[f64;2]`.
- H-A2 Interface imports `std::f64::MAX` (clippy `legacy_numeric_constants`) and `std::f64::consts::PI` (unused); `SatcResponse::new` without `Default` (`new_without_default`); `satc_is_separating_axis` has 8 parameters (`too_many_arguments`, unavoidable on the fixed signature) — see D-ALLOW.
- H-A3 Point functions are value-returning (`-> [f64;2]`) where the C mutates in place; `satc_point_copy(p, q)` has a dead first parameter.
- H-A4 `calc_points`, `edges`, `normals` must be recomputed on construction and `set_points` exactly like `_satc_polygon_recalc`; `satc_test_polygon_polygon` uses raw `points` + `pos` and `normals`, not `calc_points`.
- H-A5 `satc_point_in_polygon` builds a 1e-6 box polygon and returns `response.a_in_b`.
- H-A6 C bugs not test-exercised: `satc_point_rotate` sign, `satc_polygon_translate` sets instead of adds, `satc_polygon_get_aabb` reads uninitialised `pos` (UB) and initialises `y_max = x_max` instead of `y_min` (added M1). See D-FAITHFUL.
- H-A7 Edition 2024: `gen` reserved; nothing else relevant unless the agent reaches for statics.
- H-A8 Clippy temptations: `needless_range_loop`, `clone_on_copy`, `needless_return`, `needless_late_init`, `assign_op_pattern`, `vec_init_then_push`, `collapsible_else_if`, `unnecessary_cast`, `ptr_arg`, `uninlined_format_args`.

### libpsbt (project_2)
- H-L1 **Defective benchmark test** `read_test_vector`: the checker declares `let mut step = 0;` inside the callback, so every Record callback asserts `record_type == 0`; the vector contains record types 1, 2, 4, 5, 6. A faithful parser panics in this test. Passing requires suppressing callbacks (forbidden by Z2/Z14 spirit). Ceiling 3/4 = 30/40 correctness. See D8.
- H-L2 `cli.rs` is `fn main() -> i32 { unimplemented!() }` — private, in a library module, no bin target → dead_code. See D-CLIMAIN.
- H-L3 Misleading stub comments the agent must ignore: "uses the hex crate" (not a dependency; Cargo.toml immutable), "only Hex is implemented for simplicity" (C implements hex, base64, base62; protobuf NotImplemented), "simulate reading by calling the callback twice", "for simulation purposes we keep a list of records".
- H-L4 Underscore-prefixed stub params (`_src_size`, `_psbt_len`, `_tx_size`, `_data`) are semantically required: tests pass 2048-byte buffers with a real length of 889.
- H-L5 Callbacks are non-capturing `fn` pointers with `&mut dyn Any` user data; `psbt_read` must count inputs/outputs from the unsigned tx and forward every txelem to the user handler like C `tx_counter`. Clean design: a private generic `FnMut` parser wrapped by the fn-pointer API. Unguided agents reach for raw pointers or `Box<dyn Any>` smuggling.
- H-L6 Global mutable `psbt_errmsg` written from 29 assignment sites (`grep -n 'psbt_errmsg *=' c/*.c`, M1); interface stubs `psbt_geterr` to a const. Safe options: `thread_local!` or `Mutex<&'static str>`; never `static mut`.
- H-L7 Byte-cursor state machine (`write_pos` pointer used for reading and writing, `ASSERT_SPACE`, unchecked reads) → usize index with checked slicing; return `ReadError`, never panic.
- H-L8 Pre-implemented interface bodies the agent inherits: `Psbt::new`, `psbt_size = data.len()`, `psbt_geterr`, `Display for PsbtResult` (`write!(f, "{:?}", self)` trips `uninlined_format_args`).
- H-L9 Enums derive only `Debug, PartialEq, Eq` (PsbtScope also Clone); `psbt_state_tostr(state: PsbtState)` takes by value → add derives or match-and-reconstruct.
- H-L10 `src/bin/test.rs` is both the declared `[[test]] name = "test"` and an auto-discovered bin named `test`; Benchmark infrastructure: document, never rename. **M1 answer**: it builds (no `extern crate test` clash), and `cargo test` compiles the same 4 tests into TWO executables (`unittests src/bin/test.rs` and `src/bin/test.rs`); without `--no-fail-fast` the second is skipped once the first fails. Counting must use distinct test names (4), not `test result:` lines (up to 8). Verbatim in `trajectories/project_2/baseline/README.md`.
- H-L11 Harness noise in `test.rs`: `single_match`, `uninlined_format_args`, `unused_assignments`, dead consts in the bin build.
- H-L12 C bugs not test-exercised: `compactsize_write` overwrites the 253/254/255 marker for sizes >= 253; `base62_encode` indexes a 62-entry table with 0..63 (UB → Rust index panic); segwit witness branch is dead (`flag` never set). See D-FAITHFUL.
- H-L13 Encoding exactness: hex is lowercase with trailing NUL, `out_len = 2*len + 1`; `psbt_decode` detects base64 by prefix `cHNid`; C base64 decoder is lenient — hand-translate rather than use the `base64` crate's strict engine.
- H-L14 Dependencies pinned in Cargo.lock (`base64 0.21.7`, `thiserror 1.0.69`); use `--locked`; first build needs network for crates.io.
- H-L15 Unsafe temptations: `*(u32*)cursor` → `from_le_bytes`; `void *user_data` casts → `downcast_mut`; unions → the interface's enums; `memcpy` → `copy_from_slice`; `FILE*` → `&mut dyn Write`.

## C — Claude Code 2.1.235 headless facts (from `claude --help` and binary strings; M3 smoke run confirms)

- C1 `-p --output-format stream-json --verbose` emits `system/init` (tools[], model, permissionMode, slash_commands, mcp_servers, session_id), `assistant`, `user` (tool results), `rate_limit_event` (status allowed|allowed_warning|rejected, resetsAt, rateLimitType), and one terminal `result` (subtype success|error_max_turns|error_max_budget_usd|error_during_execution|error_max_structured_output_retries, is_error, num_turns, usage, total_cost_usd, permission_denials[], structured_output).
- C2 `--permission-mode dontAsk` denies anything not pre-approved without prompting (cannot hang). `--allowedTools "Read Edit Write Glob Grep Bash(cargo *)"` + `--disallowedTools "Bash(git *) Bash(rm *) Bash(curl *) Bash(wget *) Bash(cargo install *) Bash(cargo add *) ..."`. Compound/subshell Bash commands are treated as unparseable → denied; the system prompt must demand single cargo commands. **Corrected by the M3 smoke (2026-10-29):** under dontAsk the agent ran `ls -a <dir> <dir> 2>&1 | head -60` and it was allowed; Claude Code auto-approves read-only commands even when they are not on the allowlist, piped ones included. Mutating or unlisted commands (`git status`) were denied. Read/Glob/Grep are unrestricted by path (`evidence/smoke/smoke_report.json`). **Fixed and probed the same day** (`evidence/smoke/probe/probe_report.json`): with no unscoped Read/Glob/Grep allow, `Edit(./**)`/`Write(./**)` scoped to the crate, and explicit denials for the common read-only commands, a planted file outside the working dirs was denied to Read, `cat`, piped `ls`, Glob and Grep. Bare `ls` was denied, and a Write into `subjects/` was refused ("directory denied by your permission settings"). Reading the `--add-dir` C header, `cargo +nightly-2025-05-13 --version` and a Write in the crate were allowed. `system/permission_denied` events carry `message` as a plain string. `rate_limit_event` nests `status` under `rate_limit_info`, beside a separate `overageStatus` that must not be read as a limit.
- C3 `--tools "Read,Edit,Write,Glob,Grep,Bash"` shrinks the built-in tool set (M3 smoke: init also lists `StructuredOutput`, added by `--json-schema`; see D-STRUCTOUT; init additionally carries `agents[]`, `skills: []`, `plugins: []`); `--strict-mcp-config --mcp-config '{"mcpServers":{}}'` removes MCP; `--disable-slash-commands` removes skills.
- C4 `--bare` is unusable (refuses OAuth auth; owner has no API key). M3: the CLI keeps its own login, separate from the desktop app; on 2026-10-29 it was logged out (`claude auth status` → loggedIn false) until the owner ran `claude auth login`. Isolation instead: env `CLAUDE_CODE_DISABLE_CLAUDE_MDS=1` (required once this program's CLAUDE.md exists at repo root), `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1` (memory dir already holds MP4 notes), `--setting-sources project`, `--settings '{"autoMemoryEnabled":false,"disableAllHooks":true}'`.
- C5 `--append-system-prompt-file` (hidden flag) keeps Claude Code's default tool guidance; `--system-prompt-file` replaces it. Use append.
- C6 `--max-turns N` is the authoritative cap (hidden flag; result subtype error_max_turns). M3 smoke: with `--max-turns 2` both calls ended `success` with `num_turns: 4` (a tool round plus the StructuredOutput call). The counter does not map 1:1 to the cap; still to be confirmed against a real loop in M4. `--max-budget-usd` is a secondary tripwire (behaviour on subscription unverified). `--session-id <uuid4>` pre-assigns the on-disk JSONL path. `--json-schema` forces a structured final status. `--model opus --effort high`.
- C7 Usage limits: `rate_limit_event` with status `rejected` and/or a result with is_error and text matching `/limit|resets|rate_limit|429/i`. Exit code on is_error is unverified → parse stream lines, never rely on exit status. Wrapper imposes its own 45-minute wall clock.
- C8 Settings files that fail validation are silently ignored in `-p`; verify isolation via the `system/init` line on every call, not only in the smoke run.
- C9 The repo-root `CLAUDE.md` this program adds, the owner's `~/.claude/CLAUDE.md` working agreement, and auto-memory would all leak into agent B without C4.

## E — Environment facts (2026-10-28)

- E1 macOS Darwin 25.5.0, Apple Silicon, 10 cores, 32 GB; Xcode CLT present (`/usr/bin/cc`).
- E2 rustup, cargo, rustc ABSENT before M1 (installed by M1 on 2026-10-28 with owner approval; versions in `MP4/docs/environment.md`). M1 installs `rustup` then `rustup toolchain install nightly-2025-05-13 --profile minimal --component clippy`. `~/.cargo/bin` must be on PATH for headless children.
- E3 Python 3.9.12 (no `match`, no `X | Y` unions); PyYAML 6.0 installed. `python3 -I` drops the script dir from `sys.path`; entry points insert their own dir.
- E4 Claude Code 2.1.235 at `~/.local/bin/claude`, authenticated via claude.ai Max subscription. No `ANTHROPIC_API_KEY`.
- E5 Repo `main` at `ffcb972`, remote `origin` = github.com/josephstefurak/CS598JBR-Team-1. No `docs/`, no `CLAUDE.md`, no `.claude/` before this program.
- E6 CRUST-bench: https://github.com/anirudhkhatry/CRUST-bench, `datasets/CRUST_bench.zip` (45 MB) → `CBench/{satc,libpsbt}`, `RBench/{satc,libpsbt}`; strip embedded `.git/` and `.DS_Store`.
- E7 nightly-2025-05-13 = `rustc 1.89.0-nightly (8405332bd 2025-05-12)`, `cargo 1.89.0-nightly (056f5f4f3 2025-05-09)`, `clippy 0.1.88` (corrected M1; was "≈ 1.88.0-nightly"); edition 2024 (satc) and Cargo.lock v4 are supported; `uninlined_format_args` is in the style group on this clippy.

## D — Ratified decisions (owner, 2026-10-28; see also the plan file)

- D1 Agent B = Claude Code headless, **model opus, effort high**, one model for every iteration, subscription auth.
- D2 program-builder, branch `mp4-program` from `ffcb972`, commit-only, never push.
- D3 Owner-blocked rows last (M12-M14) with preconditions in code.
- D4 Reviews validate the rubric with evidence AND hunt bugs.
- D5 No manual Rust repair; integrity guards in code; `configs/CHANGELOG.md`.
- D6 Interim safety = wrapper-injected `#![forbid(unsafe_code)]` + `-D unsafe_code` build + regex counts; course tool as second backend, run retroactively over snapshots.
- D7 **Spend envelope pre-authorized**: <= 8 iterations x <= 60 turns per project per run, <= 2 full runs, <= 2 tuning reruns, <= 3 smoke calls; auto-resume after usage-limit pause (`rate_limit.mode: wait`, cap 6 h).
- D8 `read_test_vector` is **known-failing**: excluded from the success predicate, wrapper verifies it is the only failure and fails on the documented assertion, prompt forbids suppressing callbacks, README and report disclose it, **owner raises it with course staff**; any ruling is injected into `configs/projects/project_2.yaml`.
- D9 Cut-off **2026-11-15** for M12/M13; afterwards they are marked dropped and proxy numbers ship labelled.
- D10 Jacob and Ross polish the report prose; Joseph + sessions do everything else.
- D-ALLOW (**confirmed M3 gate 2026-10-29: "One allow, that fn only"**) exactly one `#[allow(clippy::too_many_arguments)]` on `satc_is_separating_axis`; all other allow-attributes forbidden (grep-checked by the M8 review; M5 found the loop does not enforce it, review-1 G1 asks the owner at M6).
- D-CLIMAIN (**confirmed M3 gate 2026-10-29: "Make it pub fn main"**) libpsbt `cli::main` becomes `pub fn main() -> i32`, no extra bin.
- D-FAITHFUL (**confirmed M3 gate 2026-10-29: "Faithful; define UB safely"**) faithful where the C is well-defined; defined non-panicking behaviour where the C is UB; every ruling in the project yaml and README.
- D-FORBID (**confirmed M3 gate 2026-10-29: "Yes, inject it"**) the wrapper injects `#![forbid(unsafe_code)]` at workspace init as a documented infrastructure intervention ("program logic affected: no").
- D-TRAJ (default) commit every run as stream-json + diagnostics; no `~/.claude` session copies; home paths → `~`.
- D-DIAGRAM (default) TikZ in `.tex`, Mermaid in README.
- D-STRUCTOUT (owner, M3 2026-10-29: "Allow StructuredOutput too") `--json-schema` adds a `StructuredOutput` tool to the init tools[]; the isolation check expects exactly the configured six plus `StructuredOutput`, anything else aborts. Evidence: `docs/programs/mp4/evidence/smoke/attempt1_isolation_abort/`.
