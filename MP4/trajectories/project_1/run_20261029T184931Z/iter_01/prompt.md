# Translate satc (CRUST-bench) to Rust — iteration 1 of at most 8

Your working directory is the Rust crate `satc`. The original C project
is at `~/CS598JBR-Team-1/MP4/subjects/project_1/c` (read-only). Translate it into safe, idiomatic Rust that
implements the required interface and passes the provided tests.

## What to produce

- One file `src/<module>.rs` for each module declared in `src/lib.rs`:
  `satc`.
- The spec for each module is `src/interfaces/<module>.rs`. It has
  45 public items in total, and every one must exist with
  the same signature.
- C sources to translate: `satc.h`, `satc-test.c`.
- Tests: `src/bin/satc_test.rs`.

## Hard rules (also in your system prompt)

- Do not modify, rename or delete the test files, `src/interfaces/`,
  `Cargo.toml`, `Cargo.lock`, or the first line of `src/lib.rs`.
- No `unsafe`, no raw pointers, no FFI (no calling the C code, no
  `extern "C"`, no `build.rs`), no new dependencies.
- No hard-coding: never return expected test outputs for known test inputs,
  and never copy test data into library code.
- Implement the C behaviour faithfully, as described in the project notes.
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

## C-to-Rust patterns

Pattern-level guidance only. It does not describe any specific function.

| C construct | Safe Rust |
|---|---|
| `*(uint32_t *)cursor` and similar reinterpreting reads | `u32::from_le_bytes(buf[i..i + 4].try_into()?)` with checked slicing |
| byte cursor (`unsigned char *p` advanced through a buffer) | a `usize` index into a slice; `get(i..j)` returns `None` instead of reading out of bounds |
| `memcpy(dst, src, n)` | `dst[..n].copy_from_slice(&src[..n])` after checking both lengths |
| `void *user_data` passed to a callback | `&mut dyn Any` and `downcast_mut::<T>()`, or a generic closure inside a private helper |
| union with a tag field | an `enum` with data, as the interface already declares |
| global mutable state (`static char *errmsg`) | `thread_local!` with `Cell`/`RefCell`, or a `Mutex`; never `static mut` |
| `FILE *` output | `&mut dyn std::io::Write`, with `write!` errors mapped to the interface's error type |
| output parameter (`double *out`) | return the value, or `&mut` exactly as the interface declares |
| sentinel return codes | the interface's result enum, `Option` or `Result` |
| fixed-size array of points (`double p[2]`) | `[f64; 2]`, which is `Copy`, so pass by value or reference without `.clone()` |
| `for (i = 0; i < n; i++) a[i]` | `for x in &a` / `.iter().enumerate()` / `.zip()`, unless the index itself is needed |
| `x = x + y` | `x += y` |
| early `return v;` as the last statement | the tail expression `v` |
| declare-then-assign (`T x; ... x = ...;`) | `let x = ...;` at the point of assignment |
| `if (a) {...} else { if (b) {...} }` | `else if b {...}` |
| `v = vec![]; v.push(..); v.push(..)` | `vec![.., ..]` |
| redundant casts (`x as f64` on an `f64`) | drop the cast |
| `format!("{}", x)` | `format!("{x}")` (clippy's `uninlined_format_args` is in the style group) |
| `std::f64::MAX`, `std::u32::MAX` | `f64::MAX`, `u32::MAX` |
| `&Vec<T>` parameters you add yourself | `&[T]` |
| a `new()` with no arguments | also implement `Default` (clippy's `new_without_default`) |

## Start

Read the interface, the tests and the C. Write every module. Then build, test
and run the rubric clippy command, and repair until everything is clean.
Finish with the structured status.
