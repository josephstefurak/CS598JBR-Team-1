# project_1 (satc) — skeleton baselines

Measured on 2026-10-28, before any pipeline code existed, with
`nightly-2025-05-13` (`rustc 1.89.0-nightly (8405332bd 2025-05-12)`,
`clippy 0.1.88`). Both baselines ran on throwaway copies of
`MP4/subjects/project_1/rust_skeleton/`, never in `MP4/translations/`. Scratch
paths in the logs are rewritten to `<baseline-A-workdir>` /
`<baseline-B-workdir>`.

## Baseline A — the skeleton exactly as shipped

Command: `cargo +nightly-2025-05-13 build --all-targets --locked`
Log: `baseline_A_build.log`. Exit code 101.

```
error[E0583]: file not found for module `satc`
 --> src/lib.rs:1:1
  |
1 | pub mod satc;
  | ^^^^^^^^^^^^^
  |
  = help: to create the module `satc`, create file "src/satc.rs" or "src/satc/mod.rs"
```

The skeleton cannot build as shipped. `src/lib.rs` declares `pub mod satc;`,
but the interface lives at `src/interfaces/satc.rs`, which nothing compiles
(why.md H-S1). The agent must create `src/satc.rs`.

## Baseline B — the interface file copied to `src/satc.rs`

Copied `src/interfaces/satc.rs` to `src/satc.rs` and changed nothing else.
Every function body is still the interface's `unimplemented!()`.

| Step | Command | Log | Result |
|---|---|---|---|
| build | `cargo +nightly-2025-05-13 build --all-targets --locked` | `build.log` | exit 0 (warnings only) |
| test | `cargo +nightly-2025-05-13 test --locked` | `test.log` | exit 101; 0 passed, 4 failed (`satc_collision_test`, `satc_point_scale_xy_test`, `satc_point_test`, `satc_polygon_get_centroid_test`), all failing on `not implemented` |
| rubric clippy | `cargo +nightly-2025-05-13 clippy --all-targets --all-features -- -W clippy::correctness -W clippy::style -W clippy::complexity -W clippy::perf` | `clippy_rubric.log` | exit 0 |
| rubric clippy, JSON | same, with `--message-format=json` | `clippy.json` | exit 0 |

Test targets that `cargo test` runs: `unittests src/lib.rs` (0 tests), then
`unittests src/bin/satc_test.rs` (4 tests). Doc-tests: 0.

### Warning classification

**Method.** Each diagnostic in `clippy.json` is assigned to a file by its
primary span. Files under `src/bin/` are **harness** files: immutable test
files the agent cannot fix. Everything else is **interface-induced**: it
comes from the copied interface and will change once the agent writes the
module. A clippy lint's category was found by rerunning clippy once per
group with `-A clippy::all -W clippy::<group>`. Rustc lints (`dead_code`,
`unused_*`) are not in any clippy category and are listed as `rustc`.

`cargo` reports the lib's warnings once per target (`lib` and `lib test`).
"Unique sites" counts each (lint, file, line) once. The text log's
`generated N warnings (M duplicates)` lines are reproduced at the end.

| Category | Lint | Origin | File | Unique sites |
|---|---|---|---|---|
| complexity | `clippy::too_many_arguments` | interface | `src/satc.rs` | 1 |
| style | `clippy::legacy_numeric_constants` | interface | `src/satc.rs` | 1 |
| style | `clippy::new_without_default` | interface | `src/satc.rs` | 1 |
| rustc | `unused_variables` | interface | `src/satc.rs` | 38 |
| rustc | `unused_imports` | interface | `src/satc.rs` | 2 |
| rustc | `dead_code` | harness | `src/bin/satc_test.rs` (line 3) | 1 |
| rustc | `unused_imports` | harness | `src/bin/satc_test.rs` (line 1) | 1 |

| Category | Harness | Interface-induced |
|---|---|---|
| correctness | 0 | 0 |
| style | 0 | 2 |
| complexity | 0 | 1 |
| perf | 0 | 0 |
| rustc (not a clippy category) | 2 | 40 |

**Harness clippy baseline for satc: 0 in every category.** The harness
emits only the rustc warnings `dead_code` and `unused_imports`. So any
clippy-category warning in a satc translation can be attributed to the
agent.

Interface-induced items the agent will inherit (why.md H-A2):
`use std::f64::MAX;` (`legacy_numeric_constants`), `use
std::f64::consts::PI;` (unused), `SatcResponse::new` without `Default`
(`new_without_default`), and `satc_is_separating_axis` with 8 parameters
(`too_many_arguments`, fixed by the interface signature; see D-ALLOW).

Raw summary lines from `clippy_rubric.log` (trailing `(run cargo clippy --fix ...)` hints trimmed):

```
warning: `satc` (lib test) generated 75 warnings (35 duplicates)
warning: `satc` (lib) generated 75 warnings (40 duplicates)
warning: `satc` (bin "satc_test") generated 2 warnings
```
