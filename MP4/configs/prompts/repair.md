# Repair {{project_label}} — iteration {{iteration}} of at most {{max_iterations}}

Your working directory is the Rust crate `{{crate}}`, which holds the
translation from earlier iterations. The original C project is at `{{c_dir}}`
(read-only). After the previous iteration the wrapper rebuilt, tested, linted
and safety-checked the crate with `+{{toolchain}}`. The results are below.
Fix them, starting with build errors, then failing tests, then safety, then
clippy.

## Feedback from the previous iteration

{{diagnostics}}

## History

{{history}}

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
  ({{expected_pub_items}} items across {{modules}}).
- Run cargo with `+{{toolchain}}`, one command per Bash call.

## Project notes

{{project_notes}}

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
