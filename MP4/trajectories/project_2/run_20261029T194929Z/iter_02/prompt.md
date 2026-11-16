# Repair libpsbt (CRUST-bench) — iteration 2 of at most 8

Your working directory is the Rust crate `libpsbt`, which holds the
translation from earlier iterations. The original C project is at `~/CS598JBR-Team-1/MP4/subjects/project_2/c`
(read-only). After the previous iteration the wrapper rebuilt, tested, linted
and safety-checked the crate with `+nightly-2025-05-13`. The results are below.
Fix them, starting with build errors, then failing tests, then safety, then
clippy.

## Feedback from the previous iteration

### Build: ok

### Tests: 3 of 4 passed
- `read_test_vector` FAILED (known-defective test, expected to fail)

```
thread 'read_test_vector' panicked at src/bin/test.rs:126:26:
assertion `left == right` failed
  left: 4
 right: 0
note: run with `RUST_BACKTRACE=1` environment variable to display a backtrace
```

### Clippy (your code only; warnings from the test files are excluded): complexity 0, correctness 0, perf 0, style 0

### Safety (proxy): unsafe lines 0, unsafe calls 0, unsafe casts 0, pointer arithmetic 0

### Interface: 0 missing, 0 changed

## History

| Iteration | Agent outcome | Builds | Tests passed | Clippy (yours) | Unsafe | Interface missing |
|---|---|---|---|---|---|---|
| 1 | ok | yes | 3/4 | 0 | 0 | 0 |

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
  (52 items across `base64`, `cli`, `compactsize`, `psbt`, `tx`).
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
