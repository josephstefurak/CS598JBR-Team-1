# Review 2 — translations and trajectories vs the rubric (M8, 2026-10-29)

Scope: both final translations (`MP4/translations/project_{1,2}`), their trajectories (runs
`20261029T184931Z`, satc, and `20261029T194929Z`, libpsbt), the Task 3 rubric rows, R-T2-TRAJECTORIES, the
zero-credit traps Z1–Z16, and `/code-review max` over the pipeline diff since M5 (`1ac3cd4..HEAD -- MP4/src
MP4/configs`, one commit: f69ae8d). Nothing under `MP4/translations/` was edited. Every experiment ran in
scratch copies.

Companion files:
- `review-2-structural.md`: the rubric 3.4 structural inspection, with per-file `path:line` examples (step 4).
- `repair-candidates.md`: the repair examples mined from the four agent streams, for M10 (step 5).

## 1. Independent re-measurement from a fresh clone (step 1)

`git clone` of this repository into scratch, at `88a45ac` (mp4-program), then in each
`MP4/translations/project_N`:
- `cargo +nightly-2025-05-13 clean`;
- `build --all-targets --locked`, `check --all-targets --locked` and `test --locked --no-fail-fast`;
- the exact rubric command `clippy --all-targets --all-features -- -W clippy::correctness -W clippy::style -W
  clippy::complexity -W clippy::perf`.

| Project | build | check | test | Tests (hand) | `run_summary.json` final | Clippy lines (hand) | Agent clippy (run) | Harness (run) |
|---|---|---|---|---|---|---|---|---|
| satc | exit 0 | exit 0 | exit 0 | `4 passed; 0 failed` | 4/4 | 2 rustc, both `src/bin/satc_test.rs` (unused import, unused fn) | 0/0/0/0 | 0/0/0/0 (+2 rustc) |
| libpsbt | exit 0 | exit 0 | exit 101 | `3 passed; 1 failed` in both test executables (`read_test_vector`) | 3/4 | style 2 (`single_match`, `uninlined_format_args`) + 8 rustc, every span in `src/bin/test.rs` | 0/0/0/0 | style 2 (+8 rustc) |

`run_pipeline.py --check-only` from the fresh clone (exit 0 for both), compared field by field with
`run_summary.json` `final`:
- 11 fields compared: compiles, tests passed/total, clippy agent and harness per group, the agent clippy total,
  the four safety metrics, interface missing/changed, hard-coding hits, lint-attribute hits.
- Mismatches: `{}` for project_1 and `{}` for project_2.

The hand-run numbers equal the run summaries and the committed results. There is no pipeline bug and no
provenance failure to report.

## 2. Integrity, interface and trap evidence (step 2)

Run from the fresh clone (verbatim output, trimmed only where marked):

```
$ python3 -I MP4/src/integrity.py --provenance project_N
provenance project_1 True MP4/trajectories/project_1/run_20261029T184931Z/iter_02/src_after
provenance project_2 True MP4/trajectories/project_2/run_20261029T194929Z/iter_02/src_after
$ python3 -I MP4/src/integrity.py --verify --no-restore --project project_N
{  "ok": true,  "violations": []} exit=0        (both projects)
$ shasum -a 256 -c CHECKSUMS.sha256   (subjects; OK lines / other lines)
project_1 13 / 0      project_2 28 / 0
$ cmp of every skeleton file against the translation (src/lib.rs compared after prepending the forbid line)
same project_1/.gitignore, Cargo.lock, Cargo.toml, src/bin/satc_test.rs, src/interfaces/satc.rs
same project_1/src/lib.rs modulo forbid line
same project_2/Cargo.lock, Cargo.toml, src/bin/test.rs, src/interfaces/{base64,cli,compactsize,psbt,tx}.rs
same project_2/src/lib.rs modulo forbid line
$ python3 -I MP4/src/check_interface.py --project project_N --json
project_1 items 45 missing 0 changed 0 {'satc': (0, 0)}
project_2 items 52 missing 0 changed 0 {'base64': (0, 0), 'cli': (0, 0), 'compactsize': (0, 0), 'psbt': (0, 0), 'tx': (0, 0)}
$ pub fn count per module, interface vs implementation
satc 34/34; base64 3/3; cli 0/1 (D-CLIMAIN: pub fn main() -> i32); compactsize 4/4; psbt 21/21; tx 1/1
(the 8 satc text differences in a one-line comparison are formatting only: methods indented inside impl
blocks, and long signatures wrapped by rustfmt; the structural check above parses them as unchanged)
$ grep in library code (src/bin and src/interfaces excluded)
project_1 unsafe(word): 0  extern/link/libc/cc: 0   build.rs/C files in the crate: 0
project_2 unsafe(word): 0  extern/link/libc/cc: 0   build.rs/C files in the crate: 0
$ python3 -I MP4/src/integrity.py --scan --project project_N
project_1 hardcode_hits 0 ffi findings [] deps []
project_2 hardcode_hits 0 ffi findings [] deps ['base64', 'thiserror']   (the skeleton's own Cargo.toml; no extra dependency)
$ lint-level attributes in library code
project_1  src/lib.rs:1 #![forbid(unsafe_code)] (wrapper, D-FORBID); src/satc.rs:411 #[allow(clippy::too_many_arguments)] (D-ALLOW)
project_2  src/lib.rs:1 #![forbid(unsafe_code)] (wrapper, D-FORBID); nothing else
$ counts in library code
project_1 unwrap=0 expect=0 panic_family=0 assert_family=0 clone=0 as_casts=0 lines=635
project_2 unwrap=0 expect=0 panic_family=0 assert_family=0 clone=1 as_casts=13 lines=1524
$ safety proxy (results/project_N.check.logs/safety_proxy.json)
both: unsafe_lines 0, unsafe_calls 0, unsafe_casts 0, pointer_arithmetic 0; raw_pointer_types 0, static_mut 0,
transmute 0; forbid_unsafe_code_first_line True; deny_unsafe_build ok, exit 0, unsafe_code_errors 0
$ iterations: run_summary.json vs INDEX.md
project_1 2 SUCCESS | `run_20261029T184931Z` | claude | ... | stopped | SUCCESS | 2 | 4/4 | yes |
project_2 2 SUCCESS | `run_20261029T194929Z` | claude | ... | stopped | SUCCESS | 2 | 3/4 | yes |
$ run_manifest.json config hashes vs the committed configs (8 files each)
project_1 mismatches [] git_head f69ae8d; project_2 mismatches [] git_head 8b9fe2f; run_state config_hash == manifest
$ every prompt.md after iter_01 carries the controller's feedback sections
iter_02 (both): ### Build, ### Tests, ### Clippy, ### Safety, ### Interface, ## History -> all True
$ isolation init, per attempt (tools; mcp; slash; mode; model; denials; leak markers)
P1 iter_01/02, P2 iter_01/02: [Bash, Edit, Glob, Grep, Read, StructuredOutput, Write]; []; []; dontAsk;
claude-opus-5; denials 0/2/1/2 (all ls/wc); leak markers [] x4
$ tool names used in the four streams (grep -oh '"name":"[A-Za-z]*"' | sort | uniq -c)
24 Bash, 17 Edit, 6 Glob, 2 Grep, 53 Read, 4 StructuredOutput, 6 Write
$ scrub_secrets.py --check MP4/ ; git grep secrets over trajectories/translations/results ; files > 50 MB
scrub_secrets: 0 hit(s) ; 0 ; 0
$ grep -rniE 'satc_|psbt_|compactsize' MP4/src/*.py MP4/configs/prompts MP4/configs/*.md, selftest.py excluded
0
```

## 3. Behavioural spot checks against the C (step 3)

Method (scratch only, never committed into `translations/`):
- The C was compiled with `/usr/bin/cc` (Apple clang 21.0.0, `-std=c99 -O0`).
- Each crate was copied from the fresh clone into scratch, with an `examples/spot.rs` added that links it.
- Both sides print every `f64` as its IEEE bit pattern, so the comparison is exact.
- libpsbt's C needs `<endian.h>`, which macOS lacks. A scratch shim defines `htole*`/`le*toh` as identity
  functions, which is exact on little-endian arm64 and refuses to compile otherwise.
- **Contraction:** clang contracts `a*b+c` into FMA by default; Rust never does. The C reference is therefore
  built with `-ffp-contract=off`. The default-contracted build is also reported, because it differs.

**satc**: 52 output values, 5 geometric cases plus point operations. **52/52 bit-identical** to the C built
with `-ffp-contract=off`. Against the default (FMA) build, 4 values differ in the last bits: `pp_apart.overlap`,
`cp.overlap`, `cp.overlap_v.x/y`. That is a property of the C compiler, not a translation defect.

| Case (inputs) | C → Rust | Classification |
|---|---|---|
| polygon–polygon, 2×2 square (corner at its origin) rotated 30° at (0,0) vs centred 2×2 square rotated 45° at (1.5,0.5) | collides; overlap 0.773782977068247, n (-0.866…, -0.5): identical | faithful |
| same pair swapped (b, a) | collides; overlap 0.32429323428506907: identical | faithful |
| polygon–polygon, rotated square vs triangle rotated 200° at (5,5) | false; response still written (overlap 1.5602605217626528), as the C does | faithful |
| polygon–circle (rotated square, circle (2.2,1.0) r 0.75) and circle–polygon (same circle, rotated square b) | true/true; every field identical | faithful |
| `satc_point_rotate([1,2], 0.7)` | (-0.5235931871908935, -0.885466687331286): identical | faithful C bug (rotation sign, H-A6) |
| `satc_point_normalize([0,0])` | (0.0, NaN): identical | faithful C bug (unbraced `satc_point_set_xy` macro, found in M6's review iteration) |
| `satc_point_project([3,4],[1,2])` | (45, 60): identical (a correct projection would be (6.6, 8.8)) | faithful C bug (unparenthesised `satc_point_dot`/`satc_point_len2`) |
| `satc_point_reflect([1,2],[0.6,0.8])` | (4.680000000000001, 9.360000000000001): identical | faithful; it inherits the project bug |
| `satc_point_in_polygon` inside (0.4,1.0) and outside (10,10) | 1 / 0: identical | faithful |

**libpsbt**: 34 output lines (compact size write, length, read and peek; base64 encode/decode round trips;
base62; an undersized output buffer). **31/34 identical.** The 3 differing lines are all base62 alphabet index
63.

| Case | C | Rust | Classification |
|---|---|---|---|
| `compactsize_write` 0 / 252 / 253 / 65535 / 65536 / 2³²−1 / 2³² into a zeroed 9-byte buffer | `00…` / `fc…` / `fd00…` / `ffff…` / `000001…` / `ffffffff…` / `0000000001…` | identical | faithful C bug: the marker byte is overwritten by the little-endian size (65535 → `ffff`, the `fd` is lost) |
| `compactsize_length` for the same sizes | 1 1 3 3 5 5 9 | identical | faithful |
| `compactsize_read` of `fc` / `fd 34 12` / `fe 01020304` / `ff 0102…08`, plus `peek_length` | 252 ok / 4660 ok / u64::MAX err 1 / u64::MAX err 1; peek 1 3 5 9 | identical | faithful (the C reports `PSBT_COMPACT_READ_ERROR` for the 4- and 8-byte forms; reproduced) |
| base64 round trips of "", "f", "Hello, PSBT", `00 ff 10 80 7f` | `` (decode of empty fails, ok 0) / `Zg==` / `SGVsbG8sIFBTQlQ=` / `AP8QgH8=`, all decode back | identical | faithful |
| base64 encode into a 4-byte buffer | NULL | `None` | faithful |
| base62 of 1 / 4 / 7 / 10 bytes of `00 10 83 ff ff ff f8 3e 0f c0` | index 62 → `00` (the string's NUL); index 63 → `70` ('p', a read past the array) | index 62 → `00`; index 63 → `00` | **ruled divergence**: index 63 is undefined behaviour in the C (an out-of-bounds read); D-FAITHFUL requires a defined value, and the agent chose NUL and stated it in its final status. Not a translation defect |

No translation defect was found in either project's spot checks.

## 4. Structural inspection (step 4)

Full text with `path:line` examples: `review-2-structural.md`. In brief:
- **satc.** No `unwrap`/`expect`, panic macros, `clone`, `as` casts, statics or unsafe. One permitted allow
  (D-ALLOW, `satc.rs:411`). One index loop that needs neighbour access (`satc.rs:550`). All 6 out-parameters
  and the i32 voronoi code are set by the interface. The agent added `Default` for `SatcResponse` rather than
  allowing `new_without_default`.
- **libpsbt.** No `unwrap`/`expect`/panic/unsafe/allow, and no index that can panic on input the C handles
  (slices clamped or `.get`). 1 avoidable `clone` (`cli.rs:45`). 13 casts, all guarded or lossless except two
  i32 casts in the dead segwit branch (`tx.rs:99-100`). Private code uses `Result` + `?` (20 fns); the 13 public
  status-enum returns are set by the interface. The fn-pointer + `&mut dyn Any` callback API wraps a private
  generic `FnMut` parser (`tx.rs:62`), the clean design H-L5 describes. The error string is a `thread_local!`
  `Cell` (H-L6).
- **Shape of the defects.** The weak spots share a C-shaped public API that the fixed interface imposes:
  out-parameters, status codes, redundant length arguments, `num_points`. Where the agent had a free choice it
  sometimes still mirrored the C's control flow. Examples are the 94-line `psbt_read` state machine
  (`psbt.rs:200-293`) and the satc polygon–circle loop (`satc.rs:550-611`), although the same crates show it
  can write the `Result`/iterator style elsewhere.
- **Write-only error string (libpsbt, behavioural).** `psbt_geterr()` returns the interface's constant
  `PSBT_ERRMSG` (`psbt.rs:416-418`), where the C returns the last message (`c/psbt.c:793-795`). So the 28
  `set_errmsg` calls are never observable, and the CLI prints "psbt error" where the C prints the message
  (`c/cli.c:90` reads `psbt_errmsg` directly). **Cause: our own project note** (`configs/projects/project_2.yaml:30`,
  M3): "Some interface bodies are already implemented (constructor, size, error getter, Display). Keep their
  behaviour." The agent followed the configuration. See the decision table (§7).
- **Hard-coding (Z2 manual read).** None found. Every function that consumes test-visible inputs was read; the
  list is in `review-2-structural.md`. `psbt_read` calls the handler for every record (`psbt.rs:269-275`), so
  the defective `read_test_vector` is not gamed.

## 5. Repair examples (step 5)

`repair-candidates.md` has 8 candidates with stream line numbers. Every quote was confirmed with `grep -F`; this
review re-checked R1 (`error[E0502]` at P2 iter_01 L633) and R2 (`byte_char_slices` at L652, the `b"\0"` edit
at L657):
- **Feedback-driven (4):** R1 borrow-check error (E0502) fixed via rustc's own hint; R2 the only clippy-driven
  fix; R3 satc's macro faithfulness and R4 libpsbt's `args_os`, both from the review iteration.
- **Self-review edits (4):** S1–S4.

No example is a memory-safety repair: the crates never contained unsafe code. The candidates file proposes R3,
R1 and R2 for the report (R4 as the alternate); M10 picks.

## 6. Code review of the pipeline diff since M5 (step 6)

`/code-review max` over `1ac3cd4..HEAD -- MP4/src MP4/configs` (f69ae8d, the G1–G7 changes; 15 files, +507/−55).
- **Finders.** 10 independent angles, each running its experiments in its own scratch clone, with no model
  calls: line-by-line, removed behaviour, cross-file, language pitfalls, wrapper/proxy, reuse,
  simplification, efficiency, altitude, CLAUDE.md conventions. Together they returned about 70 candidates.
- **Deduplication.** The candidates collapse to 23 distinct defects (C1–C23) plus a cleanup list.
- **Gap sweep.** One gap-sweep reviewer, given the verified list, added 6 (S1–S6).
- **Verification.** No separate verifier agent per candidate was run, as at M5. Almost every finding was
  reproduced by its finder, with a script and its output; most were also found independently by several
  angles (C1 by 5, C3 by 5, C9 by 6). The single-source ones (C4, C11, C12, C15) were confirmed by this session
  against the quoted lines.

### Effect on the committed runs

Neither committed run was affected by any of these holes:
- Every Write/Edit in the four streams targets `src/*.rs`. Every shell command is a plain allowed cargo call,
  or a denied `ls`/`wc`.
- All four `integrity.json` files are `{"violations": []}`.
- Neither translation contains a non-`.rs` file under `src/`, `include!`, `#[path]`, `r#allow`, a
  macro-built attribute, `clippy::msrv` or `cfg(clippy)`.
- There is no `.cargo/config.toml`, `clippy.toml` or `.clippy.toml` in `MP4/translations`, `MP4/`, the repo
  root or `~`.
- The fresh-clone measurement under `/private/tmp`, whose ancestors differ, reproduces every number (§1).
- Both runs stopped at SUCCESS, with no pause and no ship-best.
- After the fixes, `--check-only` of both translations gives summary diff `{}` against the committed results.
  `summarize.compare` with the new guard fields gives `[]`. Provenance is ok.

### Findings and disposition

| # | Defect (evidence: finder repro unless noted) | Severity | Disposition |
|---|---|---|---|
| C2 | Measurement-time plant: the sweep ran only before measurement. `cargo test` runs agent unit tests, which can write `.cargo/config.toml` (`--cap-lints allow`) or add `#![allow]` to `src/lib.rs`. The following clippy runs are silenced, and the iteration was SUCCESS with the file left in `translations/` | high | **fixed**: `do_checks` verifies again after measuring; violations are recorded with `after_measurement`, removed and block SUCCESS. The lint scan now reads `src/lib.rs` past the wrapper's line |
| C1 | G6 ranked by `(success, score)`. A lint cap, hard-coding or a gamed known-failing test inflates the score, so ship-best shipped the blocked iteration | high | **fixed**: `guard_clean` in the history and in the ranking key |
| C4 | `integrity.py --verify --crate-dir <not a crate>` (e.g. `MP4/translations`, the repo root) deleted everything outside `src/`, `.git` included | high | **fixed**: `require_crate_workspace` (Cargo.toml + src/) in `verify` and `sweep_strays`; the CLI exits 2 |
| C3 | Stop not persisted before `finalize`/`ship_best`. An interrupt ran iteration max+1 on resume (beyond D7), or wedged the run on a missing `src/` | high | **fixed**: `pending_stop` saved with the step; resume finishes the stop; `restore_src` recreates a missing `src/` |
| C5 | Lint/hard-coding scan blind spots: non-`.rs` files via `include!`/`#[path]`, nested `target/`/`.git`/`__pycache__`/`.integrity` dirs inside `src/`, the exempt top-level `.integrity/`, `r#allow`; also macro-built attributes, `#[clippy::msrv]`, `cfg(clippy)` | high | **fixed (mechanical part)**: scans read every file under `src/` (`library_files`), `r#` recognised, `.integrity/` exempts only the manifest. **Macro/msrv/cfg(clippy): owner question M8-Q4** |
| C6 | Ancestor `.cargo/config.toml`/`clippy.toml` (written by agent code through `cargo test`) cap or relax clippy outside the workspace | high (adversarial) | **owner question M8-Q4** (pin the config through `mc.cargo_env`: `CARGO_ENCODED_RUSTFLAGS`, `CLIPPY_CONF_DIR`) |
| C7 | The permitted D-ALLOW attribute was flagged with `reason = "..."`, across lines, or on `const fn`. An allow on a generic `impl<'a>` was attributed to its first method | medium | **fixed**: `_lint_names`, qualifier-aware `_ITEM_RE`, impl attributed to its type |
| C8 | G7's `_CONNECTION_RE` missed the CLI's own wordings (Unable to connect, Connection dropped/refused/lost, Can't reach, No internet route, Request timed out; checked in the 2.1.235 binary). 5xx as `connection_error` was unlogged | medium | **fixed**: patterns added; 5xx decision logged (CHANGELOG); `terminal_reason`/`api_error_status` recorded |
| C10 | `tamper_check` only at attempt 1: edits during an exit-75 pause were credited to the agent | medium | **fixed**: `src_at_pause` snapshot, checked when the run continues |
| C11 | With `min_iterations: 2`, a success at iteration 1 followed by two violating iterations ends in ABORT and ships the broken last iteration | medium | **owner question M8-Q2** |
| C9 | INDEX.md "Final tests" read the last iteration, not the shipped one | medium | **fixed** |
| C12 | Integrity list in the repair digest uncapped: a stray dir (446 files) filled the 24 000-char budget and clipped the lint/hard-coding sections | medium | **fixed**: capped at 20 plus "... N more" |
| C13 | Sweep had no permission handling: an unlistable directory hid a stray, and a read-only one crashed `verify` on every resume | medium (adversarial) | **fixed**: owner rwx restored before listing; failures recorded, never raised |
| S1 | `--check-only` measured a copy that dereferenced symlinks (invisible to G1a); a dangling link crashed it | medium | **fixed**: `copy_crate(symlinks=True)` |
| C16 | `leak_scan`: no non-object guard (crash before `agent_result.json`), fail-open `[]` on an unreadable stream, text blocks only, interrupted attempts never scanned | medium | **fixed**: all blocks scanned, `None` when unknown, interrupted attempts scanned. On the four real streams it still finds 0 |
| C14 | `.DS_Store` (Finder) counted as an agent violation; two in a row ABORT | medium | **fixed**: removed without a record |
| C15 | A symlink at a protected path with identical content survived | low | **fixed** |
| S3 | Lost-login attempts used up the 3-attempt outage cap | low | **fixed**: the cap counts unattended waits only |
| C17 | G7 outages wait the 60-minute fallback, and `pause_until` survives an exit-75 handoff | medium (cost) | **owner question M8-Q3** |
| C18 | After a success then a regression, NO_PROGRESS needs two more full sessions | medium (cost) | **owner question M8-Q2** |
| C19 | `min_iterations` not validated against `no_progress_rounds` | low | **fixed** |
| C20 | README "Infrastructure interventions" omitted the G1a deletions and the G6 restore; docstrings said "last iteration" | low | **fixed** |
| C21 | README template `%d` truncated a fractional wait | low | **fixed** (`%g`) |
| C23 | `summarize.compare` ignored the guard counts | low | **fixed** |
| S2 | Stray records followed readdir order | low | **fixed** (`dirnames.sort()` in place) |
| S6 | `run_manifest.json` lacked `min_iterations` | low | **fixed** |
| S4 | Two new selftest checks were vacuous: the G1a report-only check, and the G3 prompt paragraph, which is static text | low | report-only check **fixed** (asserts the file still exists); G3 prompt: see S5 |
| S5 | The G3 review paragraph relies on feedback a clean crate's digest never shows (no success column, no "clean" line). The real iter_02 prompts still open with "Fix them" | low | **M9 decision table** (prompt text) |
| C22 | fake_agent `write:` unused and unconfined; the G4 drill passes without `say:` | low | `write:` confined to the workspace; the drill redundancy goes to the backlog |
| — | Cleanup: `_paren_body` duplicates `rustlex.match_brace`; `_ITEM_RE` duplicates check_interface; sweep complexity and double walk; `_usage_limit` naming and duplicated tails; unused `classify(resets_at)`; `verify()` twice per iteration; re-lexing per scan; `final_selection` derivable; selftest scaffolding | — | post-merge backlog (`post-merge.md`) |

**Fix verification:**
- `python3 -I MP4/src/selftest.py` gives `selftest: 214 PASS, 0 FAIL` (192 → 214, +22).
- The new `_run_m8` section has a check for every fixed item.
- **Mutation check.** Each of 14 fixes was reverted, one at a time, in a scratch copy, with only `_run_m8`
  run. All 14 reverts are caught:
  - 13 reverts make their check FAIL: C1, C2, C3 (C9 also fails, as it follows), C4, C5, C7, C8, C9, C10,
    C12, C14, C15, C16.
  - C13's revert raises `shutil.Error` on the hidden directory.
- `py_compile`, `flake8 --max-line-length 120` and `pyflakes` exit 0.

## 7. Decision table: tuning rerun (M9)

| Project | Measured now | Remaining gap | Proposed change (M9, prompts/config) | Would a rerun likely help? |
|---|---|---|---|---|
| satc | 4/4; clippy 0/0/0/0; proxy safety 0; interface 45/45; 52/52 spot values bit-identical to the C | none measurable. Structural: one index loop with neighbour access (`satc.rs:550`), C-shaped by the interface | none needed | no: every Task 3 row is at its ceiling |
| libpsbt | 3/4 (the D8 ceiling); clippy 0/0/0/0; proxy safety 0; interface 52/52; spot checks identical except the ruled base62 index 63 | (a) `psbt_geterr()` returns the interface constant, so the error text is write-only and the CLI prints "psbt error". **Caused by our project note** (`project_2.yaml:30`, "error getter … keep their behaviour"). (b) Structural: a 94-line C-shaped `psbt_read`, duplicated cursor logic, one avoidable `clone` (`cli.rs:45`); none is clippy-visible. (c) The review-iteration prompt (S5) | (a) Reword the note so the agent returns the last message through the thread-local (signature unchanged). (b) Add an idiom note ("give the state machine a `Result` core like the tx parser"). (c) Make the G3 paragraph conditional and add a success column to the history table | uncertain. (a) fixes a behaviour no visible test checks; whether hidden tests expect the constant or the message is unknown. (b) is not scored by clippy. A rerun re-generates the whole crate non-deterministically and could regress the 3/4 or the clean clippy. Cost: one D7 tuning slot, 0.5–4 h of quota |

Recommendation: **neither**. Accept M6/M7: both projects are at their ceilings on every measured rubric row,
and libpsbt is at the D8 ceiling. Document (a) in the README as a deliberate reading of a pre-filled interface
body. A rerun's expected gain is unmeasurable and its risk is real.

## 8. Rubric and trap verdicts

| Key | Verdict | Evidence (this review) |
|---|---|---|
| R-T3-P1-COMPILE | **pass (15/15 expected)** | fresh-clone build/check exit 0; interface 45/45, 0 changed; harness files byte-identical (§1, §2) |
| R-T3-P1-CORRECT | **pass (40/40 expected on the visible tests)** | 4/4 by hand; 0 hard-coding hits plus a manual read; 52/52 behavioural values identical to the C (§3) |
| R-T3-P1-SAFETY | **proxy: 0/0/0/0** | `-D unsafe_code` build ok; no FFI; official numbers are M12 |
| R-T3-P1-IDIOM | **pass (clippy sum 0 → 20/20 band)** | agent 0/0/0/0; the 2 rustc warnings are in the harness; structural read in `review-2-structural.md` |
| R-T3-P2-COMPILE | **pass (15/15 expected)** | build/check exit 0; interface 52/52; `pub fn main() -> i32` (D-CLIMAIN) |
| R-T3-P2-CORRECT | **3/4 (30/40), at the D8 ceiling** | `read_test_vector` fails only on the documented assertion (`test.rs:126`, left 4, right 0); 31/34 spot lines identical, the 3 others the ruled UB case |
| R-T3-P2-SAFETY | **proxy: 0/0/0/0** | as P1 |
| R-T3-P2-IDIOM | **pass (clippy sum 0 → 20/20 band)** | agent 0/0/0/0; harness style 2 + rustc 8 = the M1 baseline |
| R-T2-TRAJECTORIES | **pass** | both projects: 2 iterations each, `run_summary.json` = INDEX.md; 17 files per iteration with a `result` line; the iteration-2 prompts carry Build/Tests/Clippy/Safety/Interface/History feedback; scrub 0 |
| Z1, Z5 | pass | protected files byte-identical; `verify --no-restore` → 0 violations; checksums 13/13, 28/28 |
| Z2 | pass | `hardcode_scan` 0 (now over every library file); manual read: none (`review-2-structural.md`) |
| Z3 | pass | no `extern "C"`/`#[link]`/`libc::`/`cc::`, no build.rs or C files; dependencies are the skeleton's own |
| Z4 | pass (proxy) | `#![forbid(unsafe_code)]` line 1; the `-D unsafe_code` build is ok; 0 unsafe tokens |
| Z6 | pass | interface 0 missing, 0 changed |
| Z7 | pass | provenance ok for both; no hand edit (`workspace_tamper` []); CHANGELOG has an entry for every config change; README interventions updated (C20) |
| Z8 | pass | 2 iterations per project; repair prompts carry the controller's feedback |
| Z9 | pass | no `satc_`/`psbt_`/`compactsize` identifiers in the prompts or pipeline code outside the selftest |
| Z10 | pass | scrub 0; secret grep over trajectories/translations/results 0; no file > 50 MB |
| Z11 | owner-blocked (M13) | validation script not released |
| Z12 | pass | configs/ and trajectories/ complete (R-T2 rows) |
| Z13 | pass | both compile |
| Z14 | pass | every attempt's init: 6 tools + StructuredOutput, no MCP, no slash commands, dontAsk; 0 leak markers under the wider scan; no network tools |
| Z15 | pass | every cargo call is `+nightly-2025-05-13`; `run_manifest` records rustc 1.89.0-nightly (8405332bd 2025-05-12) |
| Z16 | pass | `--check-only` from a fresh clone reproduces both projects (§1) |
