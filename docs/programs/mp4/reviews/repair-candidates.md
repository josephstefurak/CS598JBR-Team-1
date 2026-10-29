# MP4 repair-example candidates (M8 mining)

Source: read-only walk of the four `agent.stream.jsonl` files. All line numbers are
1-based JSON lines in that iteration's `agent.stream.jsonl`. Every quote below was
confirmed with `grep -n -F` against the named file. Paths are relative to
`MP4/trajectories/`.

- P1 = `project_1/run_20261029T184931Z` (satc), P2 = `project_2/run_20261029T194929Z` (libpsbt)
- Model thinking blocks are redacted (empty `thinking` + signature), so a repair's
  reason is only visible when the agent wrote it in a `text` item or a code comment.

## What the streams contain (and don't)

- **P1 iter_01 has no repair loop at all.** The agent wrote `src/satc.rs` once (L100),
  then build (L109/110), test 4/4 (L112/113) and clippy (L115/117) were clean on the
  first try. The only warnings are in the immutable `src/bin/satc_test.rs`.
- **P1 iter_02** and **P2 iter_02** are the controller's forced review passes. Each
  produced one fix driven by the review prompt plus the agent's own reading of the C,
  **not** by a failing check (the diagnostics going in were all green).
- **P2 iter_01** is where the in-session compiler/clippy feedback loops are: one
  build error (E0502) and one clippy warning, each fixed and confirmed. It also has
  several self-review edits made before any cargo run (no external feedback).

## Candidates driven by tool or controller feedback

### R1. Borrow-checker error on the output-buffer slice (libpsbt) — tag: safety (borrow checker), see caveat
- File: `P2/iter_01/agent.stream.jsonl`
- (a) generated: L589 (Write `src/psbt.rs`), in `psbt_encode` and `psbt_decode`
- (b) feedback: L633 (`cargo build` result, exit code 101, 2 errors at psbt.rs:322 and :381)
- (c) repair: L634 and L636 (two Edits)
- (d) confirm: L638 build command, L639 result: `Finished \`dev\` profile`, no `error[`; tests run at L642/L643
- Quote (grep L633): `error[E0502]: cannot borrow \`*dest\` as immutable because it is also borrowed as mutable`
- Generated: `let dest = &mut dest[..dest_size.min(dest.len())];`. The agent replaced the C's
  raw `char *dest` plus a trusted `dest_size` with a slice clamped to both the caller's size
  and the real buffer length. That design is visible in the generated code
  (comment "the C reads src_size bytes of a bare char pointer").
- Why wrong: it reads `dest.len()` while taking a mutable reborrow of `dest` in the same
  expression. The borrow checker rejects the overlapping shared and mutable borrow.
- Repair: hoist the length into a local first:
  `let capacity = dest_size.min(dest.len()); let dest = &mut dest[..capacity];` (rustc's own `help:` suggestion).
- Outcome: build clean at L639. Behaviour unchanged.
- Caveat for the tag: this is a compile error, not a memory-safety bug. It counts as
  "safety" only in that (1) the borrow checker enforces Rust's aliasing rules and (2) the
  code it guards is the agent's bounds-clamped replacement for a C raw-pointer write. If
  the report needs a strict safety repair, there isn't one (see "Safety: plain answer").

### R2. clippy `byte_char_slices` on the NUL terminator (libpsbt) — tag: idiomaticity
- File: `P2/iter_01/agent.stream.jsonl`
- (a) generated: L589 (Write `src/psbt.rs`): `write_bytes(tx, &[b'\0'])` (in JSON: `&[b'\\0']`)
- (b) feedback: L651 rubric clippy command; L652 result (warning at psbt.rs:694:21)
- (c) repair: L656 text "One warning in my code. Fixing it:"; L657 Edit to `write_bytes(tx, b"\0")`
- (d) confirm: L659 clippy rerun; L660 result has no `src/psbt.rs` warning (the remaining warnings are all in `src/bin/test.rs`)
- Quote (grep L652): `warning: can be more succinctly written as a byte str`
  (lint name `byte_char_slices`, also on L652)
- Why: a one-element array of byte chars is a byte-string literal. Style lint, no behaviour change.
- Outcome: library clippy count 0, which the controller's post-iteration diagnostics also report
  (`P2/iter_01/diagnostics.md`: "correctness 0, style 0, complexity 0, perf 0").

### R3. C macro-expansion faithfulness in `satc_point_project` / `satc_point_normalize` (satc) — tag: correctness (fidelity to C), review-pass
- (a) generated: `P1/iter_01/agent.stream.jsonl` L100 (Write `src/satc.rs`), with
  `let amt = point_dot(p, q) / point_len2(q);` and
  `if d > 0.0 { [p[0] / d, p[1] / d] } else { *p }`
- (b) feedback: **no failing check**. The controller prompt (`P1/iter_02/prompt.md` L14
  "Tests: 4 of 4 passed", and L77 "review it against the C for behaviour the tests do not
  cover") plus the agent's reading of `satc.h` (`P1/iter_02/agent.stream.jsonl` L137
  shows `#define satc_point_dot(p, q) ...` unparenthesised).
- (c) repair: `P1/iter_02/agent.stream.jsonl` L135 (text), L141 (text), L142 (Edit)
- (d) confirm: same file, L147/148 build, L150/151 test (`test result: ok. 4 passed; 0 failed`), L152/153 clippy
- Quote (grep P1/iter_02 L135): `Two real divergences from the C surfaced in review, both from macro expansion`
- Quote (grep P1/iter_02 L141): `are unparenthesised, and \`satc_point_set_xy\` expands to two statements`
- Why wrong: iteration 1 read the C as if the macros were functions.
  `satc_point_dot(p,q) / satc_point_len2(q)` actually expands to
  `p[0]*q[0] + p[1]*q[1] / q[0]*q[0] + q[1]*q[1]`, and the unbraced
  `if (d > 0) satc_point_set_xy(...)` guards only the `x` store, so `y` is always divided
  (zero point gives `[0.0, NaN]`). I checked both against `subjects/project_1/c/satc.h`
  L276-278, L363, L370, L485-503: the agent's reading is right.
- Repair: reproduce the literal expansions, with doc comments explaining the C macro behaviour.
  The change also flows into `satc_point_reflect`, the polygon edge normals and `satc_test_circle_circle`.
- Outcome: 4/4 tests both before and after, because no test reaches these paths.
  `P1/iter_02/changes.diff` contains the new expression.
- Honest framing: this "repair" makes the Rust *more* faithful to buggy C (owner ruling
  D-FAITHFUL), not more mathematically correct. The evidence is the C source, not a test.

### R4. `std::env::args()` panics on non-UTF-8 argv (libpsbt CLI) — tag: safety (panic-freedom / robustness), review-pass
- (a) generated: `P2/iter_01/agent.stream.jsonl` L616 (Write `src/cli.rs`): `std::env::args().nth(1)`
- (b) feedback: **no failing check** (`P2/iter_01/diagnostics.md`: build ok, 3/4 with only
  the known-defective test, clippy 0). Review prompt (`P2/iter_02/prompt.md` L88) plus the agent's reading of `cli.c`.
- (c) repair: `P2/iter_02/agent.stream.jsonl` L178 (text), L179 (Edit)
- (d) confirm: same file, L181/182 build, L184/185 test (still 3/4, same known failure), L187/188 clippy
- Quote (grep P2/iter_02 L178): `which panics on non-UTF-8 argv, where the C just fails hex decoding`
- Why wrong: `args()` panics if any argument is not valid UTF-8. The C reads `argv[1]` as raw
  bytes and returns `PSBT_READ_ERROR` from `isxdigit` (cli.c L96-111). So the Rust aborted
  where the C reports an error.
- Repair: `std::env::args_os().nth(1)` followed by `to_string_lossy()`, so bad input goes
  through the normal error path. `P2/iter_02/changes.diff` contains `args_os`.
- Outcome: checks unchanged. No test exercises it.
- Tag note: this is a panic-freedom / robustness fix, not a memory-safety fix.

## Candidates from self-review, with no external feedback

In each of these the agent edited its own just-written code before running any cargo command,
or after a clean run, with no compiler, test or clippy message prompting it. The reasoning is
in redacted thinking, so the only evidence is the diff of the edit. Usable as "self-repair", but
label them that way.

### S1. CLI error code printed as enum name instead of the C's `%d` (libpsbt) — tag: correctness
- `P2/iter_01/agent.stream.jsonl`: (a) L616 `fn check(res: &PsbtResult, state: PsbtState)` printing `res`;
  (c) L624 Edit to `fn check(res: PsbtResult, ...)` printing `res as i32,`, with call sites at L626, L628;
  (d) L638/639 build ok
- Why: the interface's `Display` for `PsbtResult` is `write!(f, "{:?}", self)` (variant name),
  while `cli.c` L90 prints `"error (%d): ..."`. The edit restores the numeric code.
- Quote (grep L624): `res as i32,`. There is no feedback quote because none exists.

### S2. Lossy `size as usize` casts replaced by the `try_from`-checked value (libpsbt) — tag: safety (lossy casts) / idiomaticity
- `P2/iter_01/agent.stream.jsonl`: (a) L589 `assert_space(tx, size as usize)?;` after a
  `.and_then(|size| tx.write_pos.checked_add(size))` check; (c) L613 Edit to
  `usize::try_from(size).ok().filter(...)` + `let Some(size) = fits else {...}` so the validated
  `usize` is used directly; (d) L638/639 build ok
- Why: the original validated with `try_from` but then threw the result away and cast with
  `as`, which truncates silently on 32-bit targets. Follow-up at L688 ("Let me tidy one helper
  signature"), L695-L699: argument order, plus removal of a duplicate `assert_space` in the value
  path. Confirmed at L701/702 (test still 3/4) and L703/704 (no lib clippy lines).

### S3. Over-checked arithmetic in base64 output length (libpsbt) — tag: idiomaticity
- `P2/iter_01/agent.stream.jsonl`: (a) L556 `checked_mul(4)?.checked_div(3)?.checked_add(5)?`;
  (c) L563 `checked_mul(4)? / 3 + 5`; (d) L638/639 build ok (first build of the crate)
- Why: `checked_div(3)` cannot fail and `/3 + 5` cannot overflow once `*4` succeeded, so only
  the multiply needs checking. Small change, but it keeps the C overflow guard's meaning.

### S4. Duplicated `match txelem` in the CLI print callback (libpsbt) — tag: idiomaticity
- `P2/iter_01/agent.stream.jsonl`: (a) L616, two consecutive `match txelem` blocks
  (`let type_str = match txelem {`); (c) L719 and L721 collapse them into one match plus a
  `print_type` helper; (d) L723/724 clippy (no lib lines), L728/729 test (3/4, unchanged)
- Why: two passes over the same enum. One-match form, same output. The comment was also
  corrected: "the C driver prints nothing for witness items" became "prints the type of a witness item and nothing else".

## Non-repair worth citing: the known-defective test (libpsbt)
- `P2/iter_01/agent.stream.jsonl` L643 (also L702, L729): `thread 'read_test_vector' panicked at src/bin/test.rs:126:26`
  and `test result: FAILED. 3 passed; 1 failed`. At L650 the agent attributes it to the test
  ("fails exactly as the notes predict") and does **not** change library behaviour to pass it.
  This is a useful counter-example (feedback correctly *not* acted on, no hard-coding), not a repair.

## Safety: plain answer
There is **no** feedback-driven memory-safety repair in these four streams. Both crates use
`#![forbid(unsafe_code)]`, the safety proxy was 0 for every iteration, and the agent never wrote
`unsafe` or a raw pointer that then had to be removed. The safety-relevant material that exists:
R1 (a borrow-checker error inside a bounds-clamped slice design that replaces a C raw pointer),
R4 (panic-freedom, review-driven), S2 (lossy casts, self-review). There are also design-time UB
decisions made with no feedback, which are not repairs: P1/iter_01 L131 text ("AABB
uninitialised stack position (UB in C)", which the Rust defines as origin) and P2/iter_01 L556
(base62 index 63 "reads past the array, which is undefined in C", defined as NUL).

## Tally
| Tag | Feedback-driven | Self-review |
|---|---|---|
| correctness | R3 (review-pass) | S1 |
| safety (loose) | R1 (borrow check), R4 (panic, review-pass) | S2 (also idiomaticity) |
| idiomaticity | R2 (clippy) | S3, S4 (S2) |

## Ranked shortlist for the report
1. **R3 (satc macro expansion, correctness).** It is the most substantive: a real semantic gap
   between the C and the Rust that no test caught. The agent's explanation is clear and
   checkable against `satc.h`, and it shows what the forced review pass adds. Frame it as
   review-driven, with no failing check, and as "faithful to buggy C".
2. **R1 (E0502 borrow error, safety/compiler).** This is the clean compiler-feedback loop:
   generate (L589), rustc error (L633), fix following rustc's `help:` (L634/636), green build
   (L639). It also shows the C raw-pointer plus size pair becoming a clamped slice. Keep the
   tag caveat.
3. **R2 (clippy byte_char_slices, idiomaticity).** This is the only clippy-driven repair in the
   runs. It is small but it is an exact generate, warn, fix, re-lint cycle on the rubric command.
   **Alternate: R4** if a review-pass safety/robustness example is preferred over a trivial lint.
