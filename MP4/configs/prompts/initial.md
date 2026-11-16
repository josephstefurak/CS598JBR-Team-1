# Translate {{project_label}} to Rust — iteration {{iteration}} of at most {{max_iterations}}

Your working directory is the Rust crate `{{crate}}`. The original C project
is at `{{c_dir}}` (read-only). Translate it into safe, idiomatic Rust that
implements the required interface and passes the provided tests.

## What to produce

- One file `src/<module>.rs` for each module declared in `src/lib.rs`:
  {{modules}}.
- The spec for each module is `src/interfaces/<module>.rs`. It has
  {{expected_pub_items}} public items in total, and every one must exist with
  the same signature.
- C sources to translate: {{c_files}}.
- Tests: `{{test_file}}`.

## Hard rules (also in your system prompt)

- Do not modify, rename or delete the test files, `src/interfaces/`,
  `Cargo.toml`, `Cargo.lock`, or the first line of `src/lib.rs`.
- No `unsafe`, no raw pointers, no FFI (no calling the C code, no
  `extern "C"`, no `build.rs`), no new dependencies.
- No hard-coding: never return expected test outputs for known test inputs,
  and never copy test data into library code.
- Implement the C behaviour faithfully, as described in the project notes.
- Run cargo with `+{{toolchain}}`, one command per Bash call.

## Project notes

{{project_notes}}

## C-to-Rust patterns

{{cheatsheet}}

## Start

Read the interface, the tests and the C. Write every module. Then build, test
and run the rubric clippy command, and repair until everything is clean.
Finish with the structured status.
