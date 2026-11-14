# MP4 program — why (evidence, rubric keys, hazards, decisions)

*Every phase in `what.md` cites keys from this document. The handout itself
is `MP4/docs/MP4 CS598JBR.pdf` (gitignored, local reference only). Row M1
verifies the rubric keys below against the handout text and corrects any
drift before any code is written.*

Source of truth for grading: the MP4 handout, 430 points, due 2026-11-18
23:59. Group 1: project_1 = `satc`, project_2 = `libpsbt` (CRUST-bench).

**Handout v2 (2026-11-11).** The owner supplied a re-export,
`MP4/docs/MP4 CS598JBR v2 (rubric + newmetrics).pdf` (gitignored). Pages 1-10
(the assignment body) are text-identical to the original, page by page
(pypdf extraction, whitespace-normalised, 10/10 same). New material: the
Canvas rubric (pages 11-15, section RC below) and the staff announcement of
the unsafe-metrics tool plus the course repo link (pages 15-16, section N
below). Nothing in R, Z or the bands changes.

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

## RC — Canvas rubric (handout v2 pages 11-15, read 2026-11-11)

- RC1 21 criteria, 430 points: the same 21 rows and point values as the R
  table above, in the same order by task. No row added, removed or re-weighted.
- RC2 Canvas shows every criterion with two ratings only, "Full Marks" and
  "No Marks". The handout's banded tables (compile 15/10/5/0, safety
  25/18/10/4/0, idiom 20/15/8/3, correctness proportional) are not encoded as
  ratings; the criterion text still says "Score is proportional to tests
  passed". Read: graders type a number per the handout bands; the two ratings
  are the Canvas default, not an all-or-nothing rule. Unconfirmed by staff.
- RC3 Asymmetry in the correctness rows: Project 1 says "pass the CRUST-Bench
  tests"; Project 2 says "pass the CRUST-Bench tests **and any additional
  grading tests**". For Group 1, Project 2 is libpsbt, the project with the
  defective `read_test_vector` (H-L1, D8). This raises the weight of the M8
  behavioural spot checks for libpsbt and of resolving O1.
- RC4 Safety row wording: "Full credit requires all primary safety metrics to
  be zero", the four primary metrics named (unsafe lines, unsafe calls, unsafe
  casts, pointer arithmetic). Matches R-T3-*-SAFETY.
- RC5 Task 4 safety row: "using the provided unsafe-metrics tool". Proxy
  numbers alone do not satisfy R-T4-SAFETY-ANALYSIS now that the tool exists.
- RC6 The Task 1 README criterion links "README.md" to an external page; the
  course repo's `MP4/README.md` (N6) is a template and is the likely target.

## N — Course release 2026-11-09: `newmetrics` (read from source 2026-11-11)

Repo: https://github.com/Intelligent-CAT-Lab/CS598JBR-Team-0/tree/main/MP4
(commits 0a75cbc, 32a1650, 4597e75, all 2026-11-09). Contents: `MP4/README.md`
(template) and `MP4/newmetrics/` (the tool). **No validation script** is in
the repo as of 2026-11-11; O4/M13 stay blocked.

- N1 Install (staff): from `MP4/newmetrics/`, `cargo install --debug --locked --path . --force`.
  Its `rust-toolchain.toml` pins `nightly-2025-05-13` with components
  `rustc-dev` and `llvm-tools-preview`. This machine has neither (installed:
  cargo, clippy, rust-std, rustc); adding them is a software install, so an
  owner gate. The repo ships **no `Cargo.lock`** while the command passes
  `--locked`; whether that installs cleanly is unverified until tried.
  **M12 (2026-11-11):** it does. `cargo install --debug --locked --path . --force` exited 0 without a lock
  file and wrote none; the resolved versions are in `MP4/docs/environment.md`.
  Installs two binaries into `~/.cargo/bin`: `cargo-newmetrics`, `newmetrics`.
- N2 Run (staff): from the translated crate root,
  `cargo newmetrics 2>&1 | python3 aggregate.py --out summary.json`.
  `aggregate.py` sums every `Label: N` line across compilation units and
  writes `pointer_arithmetic, unsafe_lines, unsafe_calls, unsafe_casts,
  total_spans, raw_pointer_dereferences, raw_pointer_declarations,
  unsafe_ratio`.
- N3 **Side effects in the crate root**: the analyzer writes
  `unsafe_spans.txt`, `derefs.txt`, `decls.txt` into the working directory,
  the documented command writes `summary.json` there, and the driver runs
  `cargo clean -p <pkg>` then `cargo check`. Run in place this drops files into
  `MP4/translations/project_N/`, which the outside-src guard and
  `integrity.py --provenance` treat as violations. M12 must run it on a copy
  (or a snapshot), never in `translations/`.
- N4 What it analyses: one `cargo check` per lib target and per `bin` target
  of the package. satc's `src/bin/satc_test.rs` is an auto-discovered bin, so
  the harness is analysed too. libpsbt declares `src/bin/test.rs` as
  `[[test]]`, whose kind is `test`: printed as "not supported" and skipped,
  but the same file is also an auto-discovered bin (H-L10) and is analysed in
  that role. Neither harness contains `unsafe` (grep, 2026-11-11).
  Workspaces are unsupported. Files whose diagnostic path is absolute
  (dependencies, std) are skipped; macro-expanded code is not skipped.
- N5 How the metrics are actually computed (differs from the handout's prose):
  - Unsafe lines = sum of `end_line - start_line + 1` over every user
    `unsafe { }` block and every `unsafe fn` item (whole item, signature
    included). Blank and comment lines inside count; nested blocks count twice.
  - Unsafe calls = every call or method call expression lexically inside an
    `unsafe { }` block, safe callees included. Calls inside an `unsafe fn`
    body but outside a block are **not** counted (the flag is set and reset
    before the walk).
  - Unsafe casts = every `as` cast inside an `unsafe { }` block, ordinary
    numeric casts included.
  - Pointer arithmetic = method calls on a raw-pointer receiver named
    `add, sub, offset, offset_from, byte_add, byte_sub, byte_offset,
    wrapping_add, wrapping_sub, wrapping_offset, wrapping_byte_add,
    wrapping_byte_sub`, anywhere (no unsafe block needed).
  - Extra: raw-pointer dereferences and raw-pointer-typed bindings, anywhere.
  - "Total spans" is the crate's source size in **bytes**, so `unsafe_ratio`
    is lines over bytes and not a meaningful fraction.
  - `transmute`, FFI and `extern` are not detected by this tool; Z3 stays
    guarded by `safety_check.py`.
  Consequence for us: a crate with no `unsafe` block, no `unsafe fn` and no
  raw pointers scores 0 on all four primary metrics. Both translations carry
  `#![forbid(unsafe_code)]` (D-FORBID) and the proxy reports 0, so the expected
  official result is 0/0/0/0 for both. Expected, not measured.
  **M12 (2026-11-11): measured.** 0/0/0/0, and 0 raw-pointer dereferences and declarations, for both final
  translations and all four iteration snapshots
  (`MP4/trajectories/project_N/official_safety/2026-11-11/`). Also confirmed on the self-test fixture: the
  three span files are rewritten per compilation unit (they end up holding the last target's spans), and a
  `transmute` is a call, not a cast, for the tool (proxy casts 1, tool casts 0).
- N6 Course `MP4/README.md` template headings: `Environment` (bullets: agent
  framework and version; model(s) and provider/runtime; inference settings;
  OS/runtime; tools available to the agent; API or usage limits), `Setup`,
  `Run`, `Pipeline`, `Outputs`, `Evaluation`. Our README covers every item
  under 14 differently named headings. Whether the unreleased validator
  matches on these heading names is unknown.
  **M15 (2026-11-11):** the README now uses these six headings, with the 14
  former sections as subsections.
- N7 The announcement repeats Task 4: run the tool on both final projects and
  report the four primary metrics in the progress report.

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
- C6 `--max-turns N` is the authoritative cap (hidden flag; result subtype error_max_turns). M3 smoke: with `--max-turns 2` both calls ended `success` with `num_turns: 4` (a tool round plus the StructuredOutput call). The counter does not map 1:1 to the cap. M6 (real loop, `--max-turns 60`): `num_turns` 12 with 11 tool calls and 17 with 16, so here num_turns = tool calls + 1; neither iteration came near the cap, so what happens at 60 is still unobserved. `--max-budget-usd` is a secondary tripwire (behaviour on subscription unverified). `--session-id <uuid4>` pre-assigns the on-disk JSONL path. `--json-schema` forces a structured final status. `--model opus --effort high`.
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
- D2 program-builder, branch `mp4-program` from `ffcb972`, commit-only, never push. **Revised 2026-11-11 (owner: "I'm authorizing the sessions to push the MP4 program"):** sessions push `mp4-program` after each phase commit (`program.yaml git.push_ref`). `main` is never pushed by a session; no PR, no merge.
- D3 Owner-blocked rows last (M12-M14) with preconditions in code.
- D4 Reviews validate the rubric with evidence AND hunt bugs.
- D5 No manual Rust repair; integrity guards in code; `configs/CHANGELOG.md`.
- D6 Interim safety = wrapper-injected `#![forbid(unsafe_code)]` + `-D unsafe_code` build + regex counts; course tool as second backend, run retroactively over snapshots.
- D7 **Spend envelope pre-authorized**: <= 8 iterations x <= 60 turns per project per run, <= 2 full runs, <= 2 tuning reruns, <= 3 smoke calls; auto-resume after usage-limit pause (`rate_limit.mode: wait`, cap 6 h).
- D8 `read_test_vector` is **known-failing**: excluded from the success predicate, wrapper verifies it is the only failure and fails on the documented assertion, prompt forbids suppressing callbacks, README and report disclose it, **owner raises it with course staff**; any ruling is injected into `configs/projects/project_2.yaml`. **Staff ruling 2026-11-13 (CampusWire, relayed verbatim by the owner; full text in where.md O1):** implement the correct Rust behavior corresponding to the original C implementation, do not modify the provided tests, document the issue in the report's discussion section. D8 stands unchanged; the ruling does not say whether 3/4 earns full credit or whether Project 2 has additional grading tests.
- D9 Cut-off **2026-11-15** for M12/M13; afterwards they are marked dropped and proxy numbers ship labelled. **Revised 2026-11-11 (owner: "Extend to Nov 17"):** the unsafe-metrics tool is released, so M12 has no cut-off; the validator row M13 is dropped if the script has not appeared by **2026-11-17**.
- D10 Jacob and Ross polish the report prose; Joseph + sessions do everything else. **Superseded 2026-11-11 by D-REPORT.**
- D-ALLOW (**confirmed M3 gate 2026-10-29: "One allow, that fn only"**) exactly one `#[allow(clippy::too_many_arguments)]` on `satc_is_separating_axis`; all other allow-attributes forbidden (grep-checked by the M8 review; M5 found the loop does not enforce it, review-1 G1 asks the owner at M6).
- D-CLIMAIN (**confirmed M3 gate 2026-10-29: "Make it pub fn main"**) libpsbt `cli::main` becomes `pub fn main() -> i32`, no extra bin.
- D-FAITHFUL (**confirmed M3 gate 2026-10-29: "Faithful; define UB safely"**) faithful where the C is well-defined; defined non-panicking behaviour where the C is UB; every ruling in the project yaml and README.
- D-FORBID (**confirmed M3 gate 2026-10-29: "Yes, inject it"**) the wrapper injects `#![forbid(unsafe_code)]` at workspace init as a documented infrastructure intervention ("program logic affected: no").
- D-TRAJ (default) commit every run as stream-json + diagnostics; no `~/.claude` session copies; home paths → `~`.
- D-DIAGRAM (default) TikZ in `.tex`, Mermaid in README.
- D-M5GATES (owner, 2026-10-29, review-1 G1–G7, answered in the M5 session): G1 "Both guards" (revert and record files outside src/ that are not in the skeleton, plus symlinks; and a lint-attribute scan that blocks SUCCESS except the D-ALLOW pair); G2 "Pause, resumable" (auth failure exits 75, resume after `claude auth login`); G3 "Require 2 iterations" (`loop.min_iterations: 2`); G4 "Keep env, deny flags" (keep the smoke-verified environment, M6 scans iteration 1 for leak markers, deny `--config` and `--manifest-path` on the allowed cargo commands); G5 "Add the project note" (keep every public item in `src/<module>.rs`); G6 "Ship the best" (restore the best-scoring snapshot into translations/ and name it in `final_iteration_dir`); G7 "Pause" (overloaded/connection failures pause like a usage limit, same 3-attempt cap). Applied in M6 step 1, with CHANGELOG entries for the config parts.
- D-M8GATES (owner, 2026-10-29, M8 gate, review-2.md §6–7; verbatim option labels):
  - M9 rerun: "Neither (Recommended)". M9 is dropped and the M6/M7 results are accepted.
  - After a success that min_iterations continues past: "Ship the success, stop (Recommended)". Once an
    iteration has succeeded and min_iterations is reached, stop at the first unsuccessful iteration and ship
    the successful one; this also covers ABORT.
  - Outage wait: "Short backoff (Recommended)": 2, then 4, then 8 minutes under the 3-attempt cap, with no
    wait carried over to a resume.
  - Lint hardening: "Before any rerun (Recommended)": pinned cargo/clippy config plus a `--force-warn`
    comparison.

  The last three were asked as "applied before any rerun; otherwise the post-merge backlog". With M9 dropped
  they are approved changes in `post-merge.md`; none affects the committed runs.
- D-STRUCTOUT (owner, M3 2026-10-29: "Allow StructuredOutput too") `--json-schema` adds a `StructuredOutput` tool to the init tools[]; the isolation check expects exactly the configured six plus `StructuredOutput`, anything else aborts. Evidence: `docs/programs/mp4/evidence/smoke/attempt1_isolation_abort/`.
- D-REPORT (owner, 2026-11-11) The MP4 report section is **written by hand by the team in Overleaf**. The program's deliverable for Task 4 is a local draft (`MP4/docs/report_mp4_draft.md` / `.tex`, gitignored) offered as a recommendation, with numbers generated from committed artifacts. No row waits on an Overleaf export; O5 is superseded. When the program ends, everything is done except the hand-written report.
- D-UNTRACK (owner, 2026-11-11, verbatim selection: "Only the two drafts, LaTeX table fragments, Forum-post draft, Rubric traceability") These stay on disk, are gitignored and are removed from the tracked tree going forward; history is left as it is ("It's okay if they're in history"): `MP4/docs/report_mp4_draft.md`, `MP4/docs/report_mp4_draft.tex`, `MP4/results/*.tex`, `docs/programs/mp4/forum-post-draft.md`, `MP4/docs/rubric_traceability.md`. `MP4/results/results.md` and the check JSON/logs stay tracked. Executed by M15.
- D-TOOL (owner, 2026-11-11: "I'm okay with it as long as you make sure that it's safe ... If it is safe, go for it") The course `newmetrics` tool was read in full on 2026-11-11 (why.md N): it runs `cargo clean`/`cargo check` on the crate it is pointed at and writes four small files into the working directory; no network use, no writes elsewhere. Install is pre-approved: `rustc-dev` + `llvm-tools-preview` on nightly-2025-05-13, then the staff install command. Not vendored into this repo (the course repo has no licence file); cloned outside the repo at commit `4597e75`. Always run on a copy of the crate, never inside `MP4/translations/` (N3). If `--locked` fails because the tool ships no `Cargo.lock`, the session asks before retrying without it.
- D-ORDER (owner, 2026-11-14: "Can we do everything assuming the validation script passes ... but don't leave the program complete until we get it? When we do get it, it should literally be as simple as running the validation, confirming it works, and then just the final push") The remaining rows run M14, M16, M13. M16 is the close's full pass-1 review pulled forward as a build row. M13 stays the last build row and stays `blocked` until the script exists (cut-off 2026-11-17 unchanged). The close after M13 reviews only the diff since M16's reviewed commit. Considered and rejected: dropping M13 now and treating the validator as a post-program owner step (the owner wants the program open until it runs); letting M13's session also set `ready-to-merge` (breaks one phase per session; the scoped close is a second short run instead).
- D-CREDIT (owner, 2026-11-14: "let's just assume that 3 of 4 on libpsbt gets full correctness credit as long as we justify it correctly in our report ... if ours is correct, it is correct") An owner assumption, not a staff statement: the staff ruling of 2026-11-13 (D8 note) does not state the credit. No follow-up is sent to staff and nothing is built for possible hidden Project 2 tests (RC3).
