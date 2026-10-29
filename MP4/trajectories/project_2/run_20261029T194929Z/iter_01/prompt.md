# Translate libpsbt (CRUST-bench) to Rust — iteration 1 of at most 8

Your working directory is the Rust crate `libpsbt`. The original C project
is at `~/CS598JBR-Team-1/MP4/subjects/project_2/c` (read-only). Translate it into safe, idiomatic Rust that
implements the required interface and passes the provided tests.

## What to produce

- One file `src/<module>.rs` for each module declared in `src/lib.rs`:
  `base64`, `cli`, `compactsize`, `psbt`, `tx`.
- The spec for each module is `src/interfaces/<module>.rs`. It has
  52 public items in total, and every one must exist with
  the same signature.
- C sources to translate: `base64.c`, `base64.h`, `cli.c`, `common.h`, `compactsize.c`, `compactsize.h`, `psbt.c`, `psbt.h`, `result.h`, `tx.c`, `tx.h`.
- Tests: `src/bin/test.rs`.

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
- cli.c is a command-line driver; test.c is the C test driver. The library is base64, compactsize, psbt and tx.
- Ignore misleading interface comments. The `hex` crate is not a dependency and you cannot add it. The C implements hex, base64 and base62 encodings (protobuf returns NotImplemented). Reading does not "simulate" anything and calls the callback for every element. "For simulation purposes we keep a list of records" is not how the C works.
- Parameters with a leading underscore (source size, PSBT length, tx size, data) are real inputs. Tests pass 2048-byte buffers whose real content is shorter. Use the length arguments as the C does.
- Callbacks are plain fn pointers with `&mut dyn Any` user data. Reading must count inputs and outputs from the unsigned transaction and forward every transaction element to the user's handler, like the C counter does. A clean design is a private generic parser taking a closure, wrapped by the fn-pointer API.
- The C keeps a global error message written from many places. The interface's error getter returns a constant; a thread_local or Mutex is acceptable. Never static mut.
- The C byte cursor reads and writes through one pointer with space checks. Use a usize index with checked slicing and return the interface's error variants instead of panicking.
- Some interface bodies are already implemented (constructor, size, error getter, Display). Keep their behaviour. The Display impl's `{:?}` format trips clippy's uninlined_format_args.
- The enums derive only Debug, PartialEq, Eq (the scope enum also Clone). Add derives if you need them; do not remove any.
- Hex output is lowercase with a trailing NUL and out_len = 2*len + 1. Decoding detects base64 by the prefix the C checks. The C base64 decoder is lenient, so translate it by hand rather than using the base64 crate's strict engine.
- Dependencies are pinned in Cargo.lock (base64, thiserror). Always build with the locked versions.
- The `test` bin is also declared as [[test]], so the tests run twice under cargo test. That is benchmark infrastructure; ignore the warning about multiple build targets.
- cli::main must become `pub fn main() -> i32` (owner ruling D-CLIMAIN). Do not add a bin target.
- Keep every public item of a module defined directly in src/<module>.rs, not in submodules or behind pub use re-exports; the interface check reads only that file.

### C behaviour rulings (owner ruling D-FAITHFUL)
- The C compact-size writer overwrites its 0xFD/0xFE/0xFF marker byte for sizes >= 253. Reproduce it exactly.
- The C base62 encoder indexes its 62-character alphabet with 6-bit values. Index 62 reads the string's terminating NUL (well defined: reproduce it as a 0 byte). Index 63 is past the array (undefined behaviour): choose a defined, non-panicking result and state it in your final status.
- The C transaction parser's segwit witness branch is dead (its flag is never set). Keep it dead.

### Allow-attributes
- None permitted.

### Known-defective tests
- `read_test_vector`: Defective benchmark test (why.md H-L1). Its checker callback declares `let mut step = 0;` inside the callback, so every record callback asserts record_type == 0, but the test vector contains records of other types. A faithful parser fails here. Do not suppress, skip or reorder callbacks to make it pass. Implement the C behaviour; this test is expected to fail and is reported separately. Do not modify the test.

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
