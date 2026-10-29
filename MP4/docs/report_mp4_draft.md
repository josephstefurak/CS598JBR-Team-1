# MP4

> **Draft status.** This is the in-repo draft of the MP4 section of the progress report. The LaTeX twin,
> `report_mp4_draft.tex`, is the version that is pasted into Overleaf. Tables between `GENERATED` markers
> are written by `python3 -I MP4/src/summarize.py --report` from committed artifacts. Do not edit them by
> hand; `summarize.py --check-report` fails if they drift. The official unsafe metrics are **PENDING**:
> the course's unsafe-metrics tool has not been released, so the safety numbers below come from our
> interim proxy and are labelled as such. Trajectory paths are relative to `MP4/trajectories/`, and line
> numbers are lines of the named file (`sed -n '<line>p' <file>`). P1 = `project_1/run_20261029T184931Z`
> (satc), P2 = `project_2/run_20261029T194929Z` (libpsbt).

## Pipeline Description

**Framework, model and tools.** The translation agent is Claude Code 2.1.235, run headless
(`claude -p --output-format stream-json`). Every iteration is one fresh session of one model, Claude Opus
(the `opus` alias, reported by the CLI as `claude-opus-5`), at effort `high` and at most 60 turns and
45 minutes per iteration. We used **a single agent and a single model**; there are no subagents, no second
model and no model-based judge. The agent has seven tools: `Read`, `Glob` and `Grep` over the crate and
the original C project; `Edit` and `Write` on the crate only; `Bash` restricted to
`cargo +nightly-2025-05-13 build`, `check`, `test` and `clippy`; and `StructuredOutput` for its final
status. It has no web access, git, MCP servers or skills, and it never sees our own development setup.
The configuration is in `MP4/configs/` and the tool names it actually used are exactly these seven
(`grep -oh '"name":"[A-Za-z]*"'` over the four agent streams).

**Controller.** A Python controller (`MP4/src/run_pipeline.py`) runs the loop. It copies the CRUST-bench
Rust skeleton into `MP4/translations/project_N/`, puts `#![forbid(unsafe_code)]` at the top of
`src/lib.rs`, and checksums the files the agent may not change (tests, interfaces, `Cargo.toml`,
`Cargo.lock`). Each iteration then: (1) builds the prompt (`configs/prompts/initial.md` for the first
iteration, `repair.md` after that); (2) runs the agent session; (3) restores any protected file the agent
touched and records it as an integrity violation; (4) measures the crate itself: build, per-test results,
the exact rubric clippy command, the four clippy groups split into agent-written code and the immutable
test harness, the safety metrics, the interface check, a hard-coding scan and a lint-attribute scan;
(5) writes `diagnostics.md`, `iteration_summary.json`, `changes.diff` and a `src_after/` snapshot; and
(6) decides whether to stop.

**How feedback reaches the agent.** There are two channels.

- *Inside a session*, the agent runs cargo itself and reads the compiler errors, test failures and clippy
  warnings directly. Most repairs happened here (see Translation and Repair Analysis).
- *Between sessions*, the controller's own measurements become the next prompt. `repair.md` carries a
  "Feedback from the previous iteration" section with one block each for build errors, failing tests (with
  the panic message), clippy warnings in the agent's code (harness warnings are excluded), safety findings,
  interface gaps and integrity violations, plus a history table of every earlier iteration. Safety feedback
  comes only through this channel: the agent cannot run the safety checker, so the controller runs it and
  reports the counts. When every check is already clean, the prompt asks the agent to review the
  translation against the C "for behaviour the tests do not cover, fix only real divergences"
  (P1 `iter_02/prompt.md` line 78).

**Stopping condition.** After each iteration the controller stops with **SUCCESS** when the crate builds,
every benchmark test passes except a documented known-defective one (which must fail on its documented
assertion), agent-attributable clippy warnings are 0 in all four groups, the safety metrics are 0, the
interface is complete and unchanged, and there is no integrity violation, hard-coded test literal or lint
suppression. SUCCESS can end the run from iteration 2 on, so a crate that is clean after one session still
gets one review iteration. The run also stops with **ABORT** after integrity violations in two
consecutive iterations, **NO_PROGRESS** when the score (tests passed, then build errors, clippy warnings,
unsafe findings and missing interface items) has not improved for 3 iterations, and **MAX_ITERATIONS**
after 8. A usage-limit rejection is not a stop: the run waits for the limit to reset and repeats the
iteration.

**Pipeline diagram.** Figure: `MP4/docs/pipeline_diagram.mmd` (Mermaid, also rendered in
`MP4/README.md`); the LaTeX draft draws the same diagram in TikZ.

**Usage limits.** No request was rejected for a usage limit and neither run paused:

<!-- BEGIN GENERATED: usage -->
| Project | `rate_limit_event` records | Statuses | Limit windows | Rejected | Usage-limit pauses |
|---|---|---|---|---|---|
| satc (CRUST-bench) | 2 | allowed | five_hour | 0 | 0 |
| libpsbt (CRUST-bench) | 2 | allowed | five_hour | 0 | 0 |

Source: `grep -c '"type":"rate_limit_event"' trajectories/project_*/run_*/iter_*/agent.stream.jsonl` and `run_summary.json` `usage_limit_pauses`.
<!-- END GENERATED: usage -->

## Overall Results

<!-- BEGIN GENERATED: overall -->
| Project | Compiles | Tests Passed | Total Tests | Pass Rate | Agent Iterations | Stop reason |
|---|---|---|---|---|---|---|
| satc (CRUST-bench) | Yes | 4 | 4 | 100.0% | 2 | SUCCESS |
| libpsbt (CRUST-bench) | Yes | 3 | 4 | 75.0% | 2 | SUCCESS |

Known-defective benchmark test: `read_test_vector` (libpsbt (CRUST-bench)), see README.
<!-- END GENERATED: overall -->

Both runs stopped at SUCCESS after the two iterations the stopping condition requires. satc passes all 4
benchmark tests. libpsbt passes 3 of 4. The failing test, `read_test_vector`, is defective: its callback
re-declares its step counter on every call, so it asserts that every record has type 0 while the test
vector contains records of other types. A faithful parser fails it (`src/bin/test.rs:126`, `left: 4`,
`right: 0`). The agent saw this failure and did not change the library to pass it (P2
`iter_01/agent.stream.jsonl` line 643). We report the test as failed and do not count it as passed
anywhere. A ruling from the course staff on this test is PENDING.

Correctness beyond the visible tests was checked by comparing each translation with the original C on
inputs the tests do not use, after the runs and without changing anything. Floating-point results were
compared bit for bit, with the C compiled with `-ffp-contract=off`, because clang's default fused
multiply-add makes the C differ from itself, while Rust never fuses. satc matched on 52 of 52 values.
libpsbt matched on 31 of 34 outputs; the other 3 are one C undefined-behaviour case (reading index 63 of a
63-entry base62 table), where the translation returns a defined value by design (source:
`docs/programs/mp4/reviews/review-2.md` §3).

## Safety Analysis

<!-- BEGIN GENERATED: safety -->
| Project | Unsafe Lines | Unsafe Calls | Unsafe Casts | Pointer Arithmetic | Measured by |
|---|---|---|---|---|---|
| satc (CRUST-bench) | 0 | 0 | 0 | 0 | interim proxy (`safety_check.py --tool proxy`); official tool PENDING |
| libpsbt (CRUST-bench) | 0 | 0 | 0 | 0 | interim proxy (`safety_check.py --tool proxy`); official tool PENDING |

Additional metrics produced by the course unsafe-metrics tool: PENDING (tool not yet released).
<!-- END GENERATED: safety -->

**Which project required the most unsafe behaviour.** Neither translation contains any unsafe code, so
neither "required" it in the end. In the C, libpsbt is the one that would most naturally become unsafe
Rust. It works on caller-owned byte buffers through raw cursors (`unsigned char *data`, `*write_pos` in
`subjects/project_2/c/psbt.h:57-58`), with bounds checks done by pointer arithmetic
(`tx->write_pos+(s) > tx->data + tx->data_capacity`, `psbt.c:25`) and `memcpy` into the cursor
(`psbt.c:44`, `:118`, `:129`). It reads integers through type-punned, possibly unaligned pointer casts
(`le32toh(*(u32*)cursor)`, `tx.c:30`). Its callbacks pass a `void *user_data` (`psbt.h:78`, `cli.c:10`),
and the last error lives in a mutable global (`extern char *psbt_errmsg`, `psbt.h:155`). satc's C is
mostly arithmetic on `double *` points. Its risk is memory management: arrays of `double *`
(`double **points`, `satc.h:51`), `malloc`/`free` of shapes (`satc.h:570`, `:625`, `:659`) and
`alloca`-based helper macros (`satc.h:170`, `:189`).

**Whether the agent replaced raw pointers with safe abstractions.** Yes, in both projects. In libpsbt the
raw cursor became an index into an owned `Vec<u8>` or a borrowed slice. A `Cursor<'a>` borrows the input,
and every read is `.get`-based or clamped with `.min(len)`, so out-of-range input gets an error instead of
an out-of-bounds read. The type-punned reads became `u16::from_le_bytes`/`u32::from_le_bytes` on checked
sub-slices. The interface turns `void *user_data` into `&mut dyn Any`, which the translation passes
through unchanged. Internally, the parsers are generic over an `FnMut` closure, so they need no raw
pointers and no downcasts. The error global became a `thread_local!` `Cell`. In satc, `double *` points became `[f64; 2]` values that are copied
rather than aliased, `double **` arrays became `Vec<[f64; 2]>` (as the interface specifies),
`malloc`/`free` became ownership, and the
C's nullable `double *overlap_n` became an `Option`. Where the C has undefined behaviour (an
uninitialised stack position, a read past the end of a table), the Rust picks a defined result and
documents it in a comment.

**Whether safety improved across repair iterations.** It did not need to. The proxy reported 0 on every
measure after every iteration of both runs (tables below), and no `Write` or `Edit` in the four agent
sessions ever contained `unsafe`. The reason is a design choice. `#![forbid(unsafe_code)]` was in place
before the agent's first turn, and the prompts state the no-unsafe, no-FFI rule. So unsafe code could not
compile, and the agent never tried to write any. The closest the runs came to a safety repair is a
borrow-checker error on a slice that replaced a C raw pointer (Example 2 below).

**How we measured.** Until the course tool is available, `MP4/src/safety_check.py --tool proxy` counts
unsafe blocks and functions, calls inside them, pointer casts and pointer arithmetic in the library
sources only (`src/bin/` and `src/interfaces/` are excluded). It also builds the crate with
`-D unsafe_code` and fails on any FFI (`extern "C"`, `#[link]`, `libc::`, `build.rs`, C files). The
official numbers and any additional metrics the course tool reports are **PENDING**.

### Per-iteration measurements

<!-- BEGIN GENERATED: trend_project_1 -->
Run `run_20261029T184931Z`. Clippy, safety and interface are the controller's measurements after the iteration (safety: interim proxy, official tool PENDING). Turns, output tokens and minutes are from the agent session's own `result` event; lines changed are from `changes.diff`.

| Iteration | Compiles | Tests | Clippy (agent) C/S/X/P | Clippy (harness) | Safety (proxy) | Interface missing/changed | Integrity | Turns | Output tokens | Minutes | Lines +/- | Success |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| iter_01 | Yes | 4/4 | 0/0/0/0 | 0 | 0 | 0/0 | 0 | 12 | 22801 | 4.0 | +623/-0 | Yes |
| iter_02 | Yes | 4/4 | 0/0/0/0 | 0 | 0 | 0/0 | 0 | 17 | 17170 | 3.5 | +13/-2 | Yes |
<!-- END GENERATED: trend_project_1 -->

<!-- BEGIN GENERATED: trend_project_2 -->
Run `run_20261029T194929Z`. Clippy, safety and interface are the controller's measurements after the iteration (safety: interim proxy, official tool PENDING). Turns, output tokens and minutes are from the agent session's own `result` event; lines changed are from `changes.diff`.

| Iteration | Compiles | Tests | Clippy (agent) C/S/X/P | Clippy (harness) | Safety (proxy) | Interface missing/changed | Integrity | Turns | Output tokens | Minutes | Lines +/- | Success |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| iter_01 | Yes | 3/4 | 0/0/0/0 | 2 | 0 | 0/0 | 0 | 56 | 94525 | 17.8 | +1515/-0 | Yes |
| iter_02 | Yes | 3/4 | 0/0/0/0 | 2 | 0 | 0/0 | 0 | 31 | 17044 | 4.1 | +4/-1 | Yes |
<!-- END GENERATED: trend_project_2 -->

## Idiomaticity Analysis

<!-- BEGIN GENERATED: idiom -->
| Project | Correctness | Style | Complexity | Performance |
|---|---|---|---|---|
| satc (CRUST-bench) | 0 | 0 | 0 | 0 |
| libpsbt (CRUST-bench) | 0 | 0 | 0 | 0 |

Warnings from the immutable benchmark test file are excluded above: satc (CRUST-bench) has correctness 0, style 0, complexity 0, perf 0.
Warnings from the immutable benchmark test file are excluded above: libpsbt (CRUST-bench) has correctness 0, style 2, complexity 0, perf 0.
<!-- END GENERATED: idiom -->

These are the rubric clippy command's warnings with a primary span in agent-written code. The other
warnings it prints come from the immutable benchmark test files, and no translation can remove them. For
libpsbt these are `clippy::single_match`, `clippy::uninlined_format_args` and 8 rustc warnings (`dead_code`,
`unused_imports`, `unused_assignments`) in `src/bin/test.rs`. For satc they are 2 rustc warnings in
`src/bin/satc_test.rs`. The untouched skeletons produce the same harness warnings
(`MP4/trajectories/project_N/baseline/`).

**Did clippy feedback improve the translation?** Once, directly. The only clippy warning the agent ever
received on its own code was `clippy::byte_char_slices` in libpsbt (Example 3): 1 warning, then 0 after
the fix (P2 `iter_01/agent.stream.jsonl` lines 652 and 660). Its translations were otherwise clippy-clean
from the first build. The agent ran the rubric clippy command itself in every session, and the controller
measured 0 agent-attributable warnings in every iteration (tables above).

**Common issues.** A clean clippy count does not make the code idiomatic everywhere. Reading the code by
hand (`docs/programs/mp4/reviews/review-2-structural.md`):

- **C-style loops.** satc has one index loop, `for i in 0..len` over a polygon's points
  (`translations/project_1/src/satc.rs:550`). It needs `i` for the neighbouring points, but it keeps the C's
  shape. libpsbt has no `0..x.len()` loops, and its codecs use iterators (`chunks_exact`, `zip`).
- **Unnecessary clones.** One: `cli.rs:45` clones a `PsbtScope` that could have derived `Copy`. satc has
  none, because `[f64; 2]` points are copied with `*p`.
- **Overly complex expressions and control flow.** `psbt_read` (`psbt.rs:200-293`) keeps the C's 94-line
  state-machine `while`/`match`, with seven early `return res;` sites, rather than an inner `Result`
  function.
- **Collections and strings.** There is no inefficient string building. Hex and base64 work on byte
  slices. The weak spots come from the interface: redundant length parameters next to slices, status-code
  returns, out-parameters and underscore-named parameters that are actually used.
- **Casts.** libpsbt has 13 `as` casts, all range-guarded or widening apart from two `i32` conversions
  forced by the interface. satc has none.

## Translation and Repair Analysis

**Major problems.** Neither project had a hard translation failure. Both compiled within the first session
and passed every test they could pass (4/4 and 3/4) after iteration 1. The problems the agent did meet were:

- **Ownership and borrowing.** Turning the C's pointer-plus-size buffers into slices caused the one build
  failure in the runs (Example 2).
- **Silent C semantics in macros.** satc's function-like macros are unparenthesised and unbraced, and the
  first translation read them as if they were functions (Example 1).
- **Error handling at the boundary.** The C's argv handling and numeric error codes had to be preserved
  without panics (Example 4).
- **The defective libpsbt test.** It had to be recognised as defective and left failing rather than worked
  around.
- **Budget.** libpsbt's first session used 56 of its 60 turns, so a larger crate could run out of turns
  before reporting.

There was no memory-safety repair: `#![forbid(unsafe_code)]` meant the agent never wrote unsafe code,
which also left nothing for safety feedback to repair. Following the handout's guidance, the safety
example below is replaced by the nearest case, a borrow-checker error, and labelled as such.

### Example 1 (correctness): C macro expansion in satc

- **Generated.** In iteration 1 the agent wrote `satc_point_project` as
  `point_dot(p, q) / point_len2(q)` and `satc_point_normalize` as
  `if d > 0.0 { [p[0] / d, p[1] / d] } else { *p }` (P1 `iter_01/agent.stream.jsonl` line 100).
- **Why it was incorrect.** It treated the C's macros as functions. `satc_point_dot` and
  `satc_point_len2` are unparenthesised (`subjects/project_1/c/satc.h:363`, `:370`), so the quotient
  expands to `p[0]*q[0] + p[1]*q[1] / q[0]*q[0] + q[1]*q[1]`. `satc_point_set_xy` expands to two
  statements without braces (`satc.h:276-278`), so the `if (d > 0)` in normalize guards only the `x`
  store: the zero vector normalises to `[0, NaN]`. Our ruling for C bugs that the tests do not exercise
  is to reproduce them when the C is well defined, so the iteration-1 code diverged from the C.
- **Feedback.** No check failed: 4/4 tests, 0 clippy, 0 safety. The controller's iteration-2 prompt
  reported the clean results and asked for a review against the C "for behaviour the tests do not cover,
  fix only real divergences" (P1 `iter_02/prompt.md` line 78).
- **Repair.** Reading `satc.h`, the agent wrote "Two real divergences from the C surfaced in review, both
  from macro expansion" (P1 `iter_02/agent.stream.jsonl` line 135). It then rewrote both functions to
  follow the literal expansions, with doc comments that explain the C behaviour (line 142).
- **Outcome.** Succeeded. The build, 4/4 tests and clippy stayed clean (lines 148, 151, 153), and
  `iter_02/changes.diff` holds the change. The comparison with the C later confirmed the behaviour,
  including `project` = (45, 60) and the NaN `y`. No benchmark test can see this repair. It shows what the
  forced review iteration adds.

### Example 2 (safety substitute: borrow checker): output-buffer slice in libpsbt

- **Generated.** The C's `char *dest` plus a trusted `dest_size` became a slice clamped to both the
  caller's size and the real buffer length: `let dest = &mut dest[..dest_size.min(dest.len())];`, in
  `psbt_encode` and `psbt_decode` (P2 `iter_01/agent.stream.jsonl` line 589).
- **Why it was incorrect.** The expression reads `dest.len()` while it takes a mutable reborrow of `dest`.
  The borrow checker rejects the overlapping shared and mutable borrows. This is a compile error, not a
  memory-safety bug, but it is Rust's aliasing rule doing the job the C's raw pointer left to the
  programmer.
- **Feedback.** `cargo build` failed with exit code 101 and two errors:
  "cannot borrow `*dest` as immutable because it is also borrowed as mutable" (`error[E0502]` at
  `psbt.rs:322` and `:381`), with rustc's suggestion to store the length in a local first (line 633).
- **Repair.** Two edits hoisted the length:
  `let capacity = dest_size.min(dest.len()); let dest = &mut dest[..capacity];` (lines 634, 636).
- **Outcome.** Succeeded. The next build finished without errors (line 639), the tests were back at 3/4
  with only the known-defective test failing (line 643), and the behaviour did not change.

### Example 3 (idiomaticity): `clippy::byte_char_slices` in libpsbt

- **Generated.** The NUL terminator was written as a one-element array of byte characters:
  `write_bytes(tx, &[b'\0'])` (P2 `iter_01/agent.stream.jsonl` line 589).
- **Why it was non-idiomatic.** A slice of byte characters is a byte-string literal. Clippy's style
  group flags it.
- **Feedback.** The rubric clippy command reported "can be more succinctly written as a byte str" at
  `psbt.rs:694:21`, lint `byte_char_slices` (line 652).
- **Repair.** The agent wrote "One warning in my code. Fixing it:" (line 656) and changed the call to
  `write_bytes(tx, b"\0")` (line 657).
- **Outcome.** Succeeded. The clippy rerun showed no warning in library code (line 660), and the
  controller measured 0 agent-attributable warnings for the iteration (`iter_01/diagnostics.md`).

### Example 4 (robustness, review-driven): non-UTF-8 command-line input in libpsbt

- **Generated.** The CLI read its argument with `std::env::args().nth(1)`
  (P2 `iter_01/agent.stream.jsonl` line 616).
- **Why it was incorrect.** `args()` panics if an argument is not valid UTF-8. The C passes `argv[1]`
  to `psbt_decode` as raw bytes (`subjects/project_2/c/cli.c:107-111`), which returns
  `PSBT_READ_ERROR` when a byte is not a hex digit (`psbt.c:667`). The Rust aborted where the C reports
  an error.
- **Feedback.** No check failed. The iteration-2 review prompt (P2 `iter_02/prompt.md` line 89) led the
  agent to note that `args()` "panics on non-UTF-8 argv, where the C just fails hex decoding"
  (P2 `iter_02/agent.stream.jsonl` line 178).
- **Repair.** It switched to `std::env::args_os().nth(1)` followed by `to_string_lossy()` (line 179).
- **Outcome.** Succeeded. The build, tests (3/4, unchanged) and clippy stayed clean (lines 182, 185, 188),
  and bad input now takes the normal error path. No test exercises it.

A line-by-line timeline of every compiler, test and clippy message in each session is generated in
`MP4/results/repair_mining.md`.

## Reflection

**What worked.** Three things worked. Giving one strong agent the real toolchain in its own session meant
it could build, test and lint as often as it liked. Both crates compiled within the first session, and
the one build error and one clippy warning were fixed within minutes. The controller measured the crate
independently of the agent and enforced the rules in code rather than in the prompt alone:
`#![forbid(unsafe_code)]` from the start, checksums on the tests and interfaces, an `--check-only`
re-measurement, and provenance checks against the trajectory snapshots. As a result, every number we
report can be recomputed from the repository without a model call. Finally, the forced review iteration
found real divergences from the C that no test covers (Examples 1 and 4).

**Main limitation.** The visible tests are thin: 4 per project, and one of libpsbt's 4 is defective.
Beyond them, nothing tells the agent whether it matches the C. Iteration 1 of satc was clean on every
check and still diverged from the C. We relied on a prompted review and a manual comparison with the C
after the runs. A differential test against the compiled C, built into the loop, would have caught this
automatically. Our safety numbers are also an interim proxy until the course tool is released.

**Which feedback signals improved the output.** The compiler did the most: it caught the one real
ownership error (Example 2). Clippy improved style once (Example 3). Test feedback changed nothing,
because the tests passed from the first build, and the one failing test was correctly left alone. Safety
feedback never fired, because forbidding unsafe code at the crate root prevents unsafe code rather than
repairing it. The controller's review prompt was the most valuable signal for correctness, and it is not a
compiler, test, clippy or safety signal at all.

**Which C constructs were hardest.** The hardest constructs were those whose meaning is not visible at the
use site:

- function-like macros that are unparenthesised or expand to several statements (satc);
- pointer-plus-size buffer APIs whose aliasing has to become borrows (libpsbt);
- `void *` callback state;
- a global error variable;
- undefined behaviour that the Rust has to turn into a defined choice.

The interface itself also preserves several C shapes, such as out-parameters, status codes and redundant
lengths. The agent kept them at the boundary, and sometimes copied C control flow below it (`psbt_read`).

**What we would change with more time.** We would add a differential tester that runs the C and the Rust
on generated inputs and feeds mismatches back as failing tests. We would harden the lint-suppression guard
against the remaining bypasses, and give large crates a bigger per-iteration turn budget. With the course
safety tool, we would also add its findings to the feedback loop rather than only reporting them.
