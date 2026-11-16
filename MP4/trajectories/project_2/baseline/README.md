# project_2 (libpsbt) — skeleton baselines

Measured on 2026-10-28, before any pipeline code existed, with
`nightly-2025-05-13` (`rustc 1.89.0-nightly (8405332bd 2025-05-12)`,
`clippy 0.1.88`). Both baselines ran on throwaway copies of
`MP4/subjects/project_2/rust_skeleton/`, never in `MP4/translations/`. Scratch
paths in the logs are rewritten to `<baseline-A-workdir>` /
`<baseline-B-workdir>`.

## Baseline A — the skeleton exactly as shipped

Command: `cargo +nightly-2025-05-13 build --all-targets --locked`
Log: `baseline_A_build.log`. Exit code 101. The pinned dependencies
(`base64 0.21.7`, `thiserror 1.0.69`, plus `proc-macro2`, `quote`, `syn`,
`unicode-ident`) downloaded and compiled. Then the crate failed with five
E0583 errors, one for each module declared in `src/lib.rs`:

```
error[E0583]: file not found for module `base64`
error[E0583]: file not found for module `cli`
error[E0583]: file not found for module `compactsize`
error[E0583]: file not found for module `psbt`
error[E0583]: file not found for module `tx`
error: could not compile `libpsbt` (lib) due to 5 previous errors
```

Cause: same as satc (why.md H-S1). The interfaces live in `src/interfaces/`,
which nothing compiles.

`cargo +nightly-2025-05-13 fetch --locked`: **exit 0**. `Cargo.lock`
resolves without changes.

## Baseline B — the interface files copied to `src/<mod>.rs`

Copied each `src/interfaces/<mod>.rs` to `src/<mod>.rs` (`base64`, `cli`,
`compactsize`, `psbt`, `tx`) and changed nothing else.

| Step | Command | Log | Result |
|---|---|---|---|
| build | `cargo +nightly-2025-05-13 build --all-targets --locked` | `build.log` | exit 0 (warnings only) |
| test | `cargo +nightly-2025-05-13 test --locked` | `test.log` | exit 101; 0 passed, 4 failed (`empty_input_test`, `encode_decode_test`, `read_test_vector`, `test_vector`), all failing on `not implemented` |
| test, no fail-fast | `cargo +nightly-2025-05-13 test --locked --no-fail-fast` | `test_no_fail_fast.log` | exit 101; see H-L10 below |
| rubric clippy | `cargo +nightly-2025-05-13 clippy --all-targets --all-features -- -W clippy::correctness -W clippy::style -W clippy::complexity -W clippy::perf` | `clippy_rubric.log` | exit 0 |
| rubric clippy, JSON | same, with `--message-format=json` | `clippy.json` | exit 0 |

### H-L10 — the `test` bin: answered empirically

`Cargo.toml` declares `[[test]] name = "test", path = "src/bin/test.rs"`.
Cargo also auto-discovers `src/bin/test.rs` as a bin named `test`. Every
cargo command prints this, verbatim:

```
warning: file `<baseline-B-workdir>/src/bin/test.rs` found to be present in multiple build targets:
  * `bin` target `test`
  * `integration-test` target `test`
```

- **Does the bin named `test` build?** Yes. `build --all-targets --locked`
  exits 0. There is no clash with the injected `extern crate test`.
- **Does `cargo test` run it?** Yes, and **the same four tests are compiled
  into two separate test executables**. `cargo test --no-run` lists:

  ```
  Executable unittests src/lib.rs (target/debug/deps/libpsbt-988333bac3d1cde3)
  Executable unittests src/bin/test.rs (target/debug/deps/test-a6484d7750abaf7b)
  Executable src/bin/test.rs (target/debug/deps/test-da6ede4e6fc56d5e)
  ```

  With `--no-fail-fast`, both run, and each reports `0 passed; 4 failed`:

  ```
       Running unittests src/bin/test.rs (target/debug/deps/test-a6484d7750abaf7b)
  test result: FAILED. 0 passed; 4 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s
  error: test failed, to rerun pass `--bin test`
       Running src/bin/test.rs (target/debug/deps/test-da6ede4e6fc56d5e)
  test result: FAILED. 0 passed; 4 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s
  error: test failed, to rerun pass `--test test`
  error: 2 targets failed:
  ```

  Without `--no-fail-fast`, `cargo test` stops after the bin's test
  executable fails, so the `[[test]]` target never runs (see `test.log`).

**Consequence for counting.** A naive count of `test result:` lines gives
up to 8 executions of 4 distinct tests. Totals must count distinct test
names (4), not executions. Recorded as a discovery for the M2 checks
library.

### Warning classification

Same method as project_1: primary-span file decides harness (`src/bin/`) or
interface-induced; clippy group found by per-group reruns; rustc lints
listed separately; unique sites are (lint, file, line) after removing
cross-target duplicates.

| Category | Lint | Origin | File | Unique sites |
|---|---|---|---|---|
| style | `clippy::single_match` | harness | `src/bin/test.rs` (line 123) | 1 |
| style | `clippy::uninlined_format_args` | harness | `src/bin/test.rs` (line 6) | 1 |
| style | `clippy::uninlined_format_args` | interface | `src/psbt.rs` | 1 |
| rustc | `dead_code` | harness | `src/bin/test.rs` (lines 4, 12, 13, 23, 30, 35) | 6 |
| rustc | `unused_assignments` | harness | `src/bin/test.rs` (line 133) | 1 |
| rustc | `unused_imports` | harness | `src/bin/test.rs` (line 1) | 1 |
| rustc | `dead_code` | interface | `src/cli.rs` | 1 |
| rustc | `unused_variables` | interface | `src/psbt.rs` | 31 |

| Category | Harness | Interface-induced |
|---|---|---|
| correctness | 0 | 0 |
| style | 2 | 1 |
| complexity | 0 | 0 |
| perf | 0 | 0 |
| rustc (not a clippy category) | 8 | 32 |

**Harness clippy baseline for libpsbt: style 2 (`single_match`,
`uninlined_format_args`), every other category 0.** These two warnings come
from the immutable test file. No translation can remove them, and they are
reported apart from agent-attributable warnings (why.md H-S2, H-L11).

Interface-induced items: `Display for PsbtResult` uses `write!(f, "{:?}",
self)` (`uninlined_format_args`, why.md H-L8). `cli::main` is private in a
library module (`dead_code`, why.md H-L2 / D-CLIMAIN).

Raw summary lines from `clippy_rubric.log` (trailing `(run cargo clippy --fix ...)` hints trimmed):

```
warning: `libpsbt` (lib) generated 39 warnings (32 duplicates)
warning: `libpsbt` (lib test) generated 39 warnings (7 duplicates)
warning: `libpsbt` (bin "test") generated 8 warnings
warning: `libpsbt` (test "test") generated 4 warnings (2 duplicates)
warning: `libpsbt` (bin "test" test) generated 4 warnings (4 duplicates)
```
