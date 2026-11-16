# Repair satc (CRUST-bench) — iteration 2 of at most 8

Your working directory is the Rust crate `satc`, which holds the
translation from earlier iterations. The original C project is at `~/CS598JBR-Team-1/MP4/subjects/project_1/c`
(read-only). After the previous iteration the wrapper rebuilt, tested, linted
and safety-checked the crate with `+nightly-2025-05-13`. The results are below.
Fix them, starting with build errors, then failing tests, then safety, then
clippy.

## Feedback from the previous iteration

### Build: ok

### Tests: 4 of 4 passed

### Clippy (your code only; warnings from the test files are excluded): complexity 0, correctness 0, perf 0, style 0

### Safety (proxy): unsafe lines 0, unsafe calls 0, unsafe casts 0, pointer arithmetic 0

### Interface: 0 missing, 0 changed

## History

| Iteration | Agent outcome | Builds | Tests passed | Clippy (yours) | Unsafe | Interface missing |
|---|---|---|---|---|---|---|
| 1 | ok | yes | 4/4 | 0 | 0 | 0 |

## Hard rules (unchanged)

- Do not modify, rename or delete the test files, `src/interfaces/`,
  `Cargo.toml`, `Cargo.lock`, or the first line of `src/lib.rs`. If a test
  seems wrong, implement the C behaviour anyway and note it in your status.
  Never alter a test to make it pass.
- No `unsafe`, no raw pointers, no FFI (no calling the C code, no
  `extern "C"`, no `build.rs`), no new dependencies.
- No hard-coding: never return expected test outputs for known test inputs,
  and never copy test data into library code.
- Keep every public item of `src/interfaces/` with its exact signature
  (45 items across `satc`).
- Run cargo with `+nightly-2025-05-13`, one command per Bash call.

## Project notes

### Context
- The whole library is header-only C in satc.h; satc-test.c is the C test driver, not library code.
- Pure arithmetic on 2-D points; no I/O, no callbacks, nothing that needs unsafe.
- Points are [f64; 2] and Copy. Never .clone() them; pass by value or reference as the interface says.
- The interface's point functions return a new [f64; 2] where the C mutates its argument in place. Follow the interface signature and the C arithmetic.
- Polygon derived data (calc_points, edges, normals) must be recomputed on construction and whenever points are set, exactly as the C recalc helper does it.
- The polygon-polygon test uses the raw points plus the position and the normals, not calc_points. Follow the C.
- Point-in-polygon builds a tiny box polygon (1e-6 sides) and returns the response's a-in-b flag, as in the C.
- Tests compare f64 values with assert_eq!. Keep the C's order of operations so results are bit-identical.
- The interface file imports std::f64::MAX and std::f64::consts::PI. Use f64::MAX directly and drop imports you do not use.
- SatcResponse::new() takes no arguments; also implement Default.
- satc_point_copy has a first parameter the C overwrites; keep the signature.
- Edition 2024: gen is a reserved word.
- Keep every public item of a module defined directly in src/<module>.rs, not in submodules or behind pub use re-exports; the interface check reads only that file.

### C behaviour rulings (owner ruling D-FAITHFUL)
- The C point rotation computes the new y with a sign error. Reproduce it exactly.
- The C polygon translate sets every point to (x, y) instead of adding. Reproduce it exactly.
- The C polygon AABB initialises y_max from x_max. Reproduce it exactly.
- The C polygon AABB adds its bounds to an uninitialised stack position (undefined behaviour). Choose a defined, non-panicking value and state it in your final status.

### Allow-attributes
- Only `#[allow(clippy::too_many_arguments)]` on `satc_is_separating_axis` (fixed 8-parameter signature in the immutable interface). No other allow-attribute anywhere.

## Next

Read the files the feedback points at, fix the causes rather than the
symptoms, and rerun build, test and the rubric clippy command until they are
clean. Finish with the structured status.

If the feedback above shows a clean build, every test passing (apart from any
known-defective test), no clippy warnings, no safety findings, no interface
gaps, no integrity violations and no hard-coding or lint-attribute findings,
the crate already meets every check. Then review it against the C for
behaviour the tests do not cover, fix only real divergences, keep every check
clean, and do not rewrite code that is already correct.
