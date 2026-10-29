# Review 1 — pipeline vs rubric, adversarial guards, fresh clone (M5, 2026-10-29)

*Program phase M5 (`what.md`). Scope: `MP4/src` and `MP4/configs` at `5a26167`, before any real run.
Internal review record. The grader-facing evidence is `MP4/docs/rubric_traceability.md`.*

## Method

| Part | What ran | Result |
|---|---|---|
| Code review | `/code-review max` over `MP4/src` and `MP4/configs`: ten finder angles in parallel, then one sweep reviewer over the fix patch. The angles were A1 run-loop line scan, A2 measurement line scan, B claimed-guard audit, C cross-file tracer, D Python/platform pitfalls, E wrapper fidelity, reuse + simplification, efficiency, altitude and CLAUDE.md conventions | 50 distinct candidates after dedup: 44 from the angles, 6 from the sweep (table below) |
| Security review | `/security-review` could not start: its first step runs `git diff origin/HEAD...`, and this clone has no `origin/HEAD` ref. Creating one would change the owner's git metadata, so the equivalent pass was done by hand (see "Security pass"). Angles B, D, E and conventions already covered most of the security surface | 4 security findings (S1–S4), all fixed or gated |
| Adversarial guard test | `what.md` M5 step 2. Seven traps (a)–(g) run through the loop's own path on copies of the selftest fixture: `init_workspace`, then an agent edit, then `do_checks`/`evaluate`. Six more gap probes (x1–x6) | 7/7 traps caught, before and after the fixes. 4 of 6 gap probes exposed real holes: 2 fixed, 2 gated |
| Fresh-clone dry audit | `git clone --branch mp4-program` into scratch, then the README followed literally up to the point a model is needed | every command exit 0; no gap that blocks a grader |
| Reusability audit | the greps and Python 3.9 / `-I` checks of M5 step 5 | clean (3 hits refuted) |

**Verification.** A candidate is **CONFIRMED** when it was reproduced, either by the finder in its scratch
directory or by this session; the evidence column names who. It is **PLAUSIBLE** when the mechanism was
confirmed by reading the code but the trigger was not reproduced. Deviation: the code-review recipe runs a
separate verifier agent per candidate, and that was not done. 36 of the 50 candidates were already
reproduced, several by two angles independently, and this session read every code path involved.

**Fix rule** (`what.md` M5 step 4). Mechanical findings are fixed in this phase: the code failed its own
documented contract, or a guard failed open. A finding whose fix would change stop semantics or tool
permissions is not fixed. It is written up as an owner decision (G1–G7 below) for M6 step 1.

## Findings

Severity: **critical** = would derail or silently falsify a real run; **high** = misreports a graded number or
lets a zero-credit trap through; **medium** = wrong under a plausible condition; **low** = hygiene.

| # | Sev | Finding | Evidence | Verdict | Disposition |
|---|---|---|---|---|---|
| F1 | critical | A benchmark test that hangs, crashes (stack overflow, abort, `process::exit`) or prints no result line drops out of both passed and total, and `cargo test`'s exit code is never read. On a satc-like crate (no known-failing test) a hung test gives **SUCCESS with tests 1/1** | probe x6 (this session); finders C, B, A1, A2, altitude (stack overflow exit 101 → success; hang exit 124 → success) | CONFIRMED | fixed: tests are counted against the benchmark's declared test names (`checks.benchmark_tests`). A declared test with no result is `missing`, does not pass, and blocks SUCCESS |
| F2 | critical | `check_interface` never returns on a module with an unclosed `{` (`_item_end` returns `match_brace(...)+1 = 0`, so the scan restarts at 0) or a stray `#!` (scan jumps backwards). It also raises IndexError/AttributeError on truncated items. `measure_crate` always runs it, so the checks step wedges, and every `--resume-run` wedges or crashes again | fuzz of the six real interface files cut at 861 points (this session): **241 hangs + 92 crashes** on the original code; finders A1, A2, C, D, reuse | CONFIRMED | fixed: an unclosed item runs to the end of the file, a `#!` with no `[` ends the scan, and `compare()` reports an unreadable module as `parse_error` (its items count as missing). After: 0 hangs, 0 crashes, 92 `parse_error` |
| F3 | critical | `mp4common.cargo()`'s timeout killed only cargo. The hung test binary kept running, orphaned (PPID 1), after every timed-out check | probes x5/x6: orphan alive 28 s after the timeout (this session); finders D, A2, B | CONFIRMED | fixed: cargo runs in its own process group, and a timeout or interruption kills the whole group. Selftest checks no test process is left |
| F4 | high | Restoring a tampered immutable file with `shutil.copy2` kept the skeleton's old mtime, so cargo reused the test binary built from the agent's edit. Measured: 2/2 passed with the planted failure "fixed". That inflates `best_score` (an honest libpsbt can then never beat 4/4, so NO_PROGRESS) | `stale_probe.py` (this session): original code 2/2, fixed code 1/2; finder A2 | CONFIRMED | fixed: restores use `copyfile` (fresh mtime), and so do `tamper_check` and snapshots |
| F5 | high | Tests the agent writes (`#[cfg(test)]` modules) were counted in Tests Passed / Total Tests and in the NO_PROGRESS score: 4/5 instead of 1/2 | probe x4 (this session); finders A2, B, C | CONFIRMED | fixed: reported apart as `extra_tests`. A failing one still blocks SUCCESS, as before |
| F6 | high | `--provenance` looked only at `iter_KK` and ignored `iter_KK_attemptN`. After a usage-limit retry of the final iteration it compared against the previous iteration, so a clean translation would fail the M6/M7 floor as a "hand edit" | finders C, D, A1, A2, reuse (synthetic trees) | CONFIRMED | fixed: uses `run_summary.final_iteration_dir` (validated), falling back to the newest attempt |
| F7 | high | A lint raised to an error in the source (`#![deny(warnings)]`, `#![deny(clippy::all)]`) is not counted as a warning. Clippy errors were ignored by `evaluate`, so warnings read 0 and SUCCESS fired while the rubric command exits 101 | finders B, A2 (`clippy_errors 4, rubric exit 101, success True`) | CONFIRMED | fixed: `clippy errors: N` blocks SUCCESS and is named in the repair digest |
| F8 | high | Lint suppression is unguarded. `#![allow(clippy::all)]` / `#[expect]` in a module, `.cargo/config.toml` with `--cap-lints allow`, or `clippy.toml` thresholds bring clippy to 0 → SUCCESS. D-ALLOW exists only as prompt text | probes x2, x3 (this session); finders A1, A2, B, C, altitude | CONFIRMED | **not fixed: owner decision G1** (adds SUCCESS blockers / integrity violations) |
| F9 | high | Files the agent writes outside `src/` are never reverted, snapshotted or provenance-checked. That covers `.cargo/config.toml` (lint caps, a `runner` that fakes test output), `clippy.toml`, `tests/*.rs` and `src/main.rs`. A `build.rs` or `.c` file, once created, can never be deleted by the agent (no `rm`), so it blocks every later iteration | finders B (`runner` made `add = a - b` pass 3/3), altitude, A2 | CONFIRMED | **not fixed: owner decision G1** |
| F10 | high | Resuming a run interrupted during workspace setup (state saved at step `init`) busy-looped forever at 100% CPU: `_drive` has no `init` branch | finders D, A1, altitude (reproduced) | CONFIRMED | fixed: resume redoes the setup; `_drive` refuses an unknown step |
| F11 | high | The agent could be called twice for one attempt. If the process died after `agent_result.json` was written but before the step moved on, resume reran the agent, spending quota again and overwriting the stream | finder altitude; code read | PLAUSIBLE | fixed: a recorded result is reused |
| F12 | high | A call with no `system/init` event was never isolation-checked (`violation = []`) and could reach SUCCESS. A CLI update that rejects a flag would also burn iterations as "error" | finders conventions, E | CONFIRMED (code + `classify` on a real result with no init) | fixed: no init means isolation_violation (every recorded real call, including the auth failure, starts with init) |
| F13 | medium | Agent B and cargo inherit the launcher's environment. An `ANTHROPIC_API_KEY` in the shell would bill an API account (init's `apiKeySource` was never checked). `RUSTFLAGS`/`CARGO_TARGET_DIR`/`CARGO_ENCODED_RUSTFLAGS` would change the measurements, and the last one overrides the safety build's `-D unsafe_code` | finders E, D | PLAUSIBLE | fixed: API-key variables and cargo build-flag variables are dropped; `apiKeySource` other than `none` is an isolation violation. The inherited `CLAUDE_CODE_*` variables are **owner decision G4** |
| F14 | medium | The loop's per-iteration cargo logs and `safety_proxy.json` were written unscrubbed, so every iteration of a real run would carry the absolute home path and the commit-floor scrub check would fail. The only remedy, `scrub_secrets --fix`, would also rewrite generated Rust if the agent kept libpsbt's `base64.c` licence header, which carries 2 upstream e-mails | finders conventions, reuse, altitude, B; the e-mails grep (this session) | CONFIRMED | fixed: the iteration logs are scrubbed on write (crate path shown as `MP4/translations/project_N`), and e-mails that occur in the immutable `subjects/` are allowed |
| F15 | medium | AUTH_ERROR stops the run for good, but the log told the operator to `claude auth login` and `--resume-run`, which only reports "already stopped". A new run then wipes the workspace and uses a D7 tuning slot | finders E, A1, conventions | CONFIRMED | message fixed to the truth; resume now refuses up front when logged out. **Making AUTH_ERROR a resumable pause is owner decision G2** |
| F16 | medium | `--resume-run` used whatever configuration was on disk (no `config_hash` check) and skipped the login check | finder E | CONFIRMED (code) | fixed: resume refuses a changed `config_hash`, and refuses while logged out |
| F17 | medium | NO_PROGRESS used `len(build.errors)`, which is capped at 50. A crate going from 120 to 60 errors showed no progress, and the digest under-reported the remaining errors | finders C (55 and 70 errors both gave 50), simplification | CONFIRMED | fixed: uses `error_count` |
| F18 | medium | `toolchain.cargo_timeout_seconds` was never applied, because `cargo(..., timeout=CARGO_TIMEOUT_S)` bound the default before `pipeline.yaml` was read | finders C, D, E (YAML 5 → default still 900) | CONFIRMED | fixed: read at call time |
| F19 | medium | Agent B received the scrubbed `prompt.md`, with the C directory shown as `~/…`; the M3 probe used absolute paths. `run_manifest` and `--dry-run` showed an argv whose session id never ran | finders reuse, E, A1 | CONFIRMED (prompt read-back) | fixed: the agent gets a fresh, unscrubbed render, checked against the record, and each attempt's exact argv is saved in `agent_result.json` |
| F20 | medium | A second new run for a project, while another run is open (running, paused or interrupted), would `rmtree` the open run's workspace under it | finder A1 | CONFIRMED (code) | fixed: a new run is refused while another run of the project is not stopped |
| F21 | medium | `subjects/` was never re-verified in the loop. Code the agent runs through `cargo test`/`build.rs` could change both copies of a test file, and integrity would then report 0 violations | finders B, altitude | PLAUSIBLE | fixed: `subjects/` is checked against `CHECKSUMS.sha256` before every check, and the run stops if it changed |
| F22 | medium | A test's own stdout without a newline (libpsbt's hex printer) lands in front of libtest's `test X ... ok`. The `^test`-anchored parser then lost that test, which with the F1 fix would have become a false "no result" | finder A2 (lost in 4 of 12 runs of a model of the two-executable layout) | CONFIRMED | fixed: the parser finds the result anywhere on the line |
| F23 | medium | `check_only` replaced the home path before the log dir, so committed paths read `~/CS598JBR-Team-1/MP4/results/…`, and the temp crate showed as `/private<crate>` | finders C, D | CONFIRMED | fixed (one `_scrub_paths` for loop and check-only, both `/var` and `/private/var` spellings) |
| F24 | medium | `--check-only`, the grader path, never validated `pipeline.yaml` | finders conventions, simplification | CONFIRMED | fixed: it loads the validated configuration first |
| F25 | medium | The safety proxy's `-D unsafe_code` build left its temp crate copy, with a cold `target/`, in `$TMPDIR` on every call. 87 copies (73 MB) were found at review start | `ls $TMPDIR/mp4crate_*` (this session); finders efficiency, D, reuse | CONFIRMED | fixed: removed after the build (selftest checks it). The existing leftovers are listed in the runbook |
| F26 | medium | Usage-limit redo attempts were unbounded. A recurring error the broad text match mistakes for a limit would retry forever, a full agent session each time | finder altitude | PLAUSIBLE | fixed: after 3 refused attempts of one iteration the run exits 75 for a person. The broad match stays: a false "limit" costs a free wait, while a missed one burns iterations |
| F27 | medium | A satc-sized crate can be clean after iteration 1. The run then stops with 1 iteration, while Z8 and M6's verification expect at least 2 | finder B | CONFIRMED (code) | **owner decision G3** |
| F28 | medium | The interface check reads only `src/<mod>.rs`. `pub use inner::{…}` re-exports, or items split across submodules, read as missing even when the crate builds and passes, so the repair loop would chase a phantom until NO_PROGRESS | finder altitude (reproduced) | CONFIRMED | **owner decision G5** |
| F29 | medium | When the run stops at MAX_ITERATIONS or NO_PROGRESS, the last iteration ships, not the best-scoring one. A final session killed mid-refactor ships a crate that does not build | finder A1 | CONFIRMED (code) | **owner decision G6** |
| F30 | medium | Transient API failures (overloaded, connection drops) count as full iterations and feed NO_PROGRESS, so a 20–30 minute outage can end a run | finder A1 | PLAUSIBLE | **owner decision G7** |
| F31 | low | `known_failing_tests` values were not type-checked: a blank `expected_assertion` crashed `do_checks`, and an empty string matched anything. `c_dir` was not kept inside `subjects/`, and `setting_sources` accepted any string | finder conventions | CONFIRMED (code) | fixed in `config.py` |
| F32 | low | A stream line that is valid JSON but not an object raised AttributeError inside the read loop | finder conventions | CONFIRMED (code) | fixed |
| F33 | low | The tamper check runs only for attempt 1 and only over `src/`. An edit made during a usage-limit pause, before attempt 2, is snapshotted as agent work | finders C, B | CONFIRMED (code) | backlog: needs a snapshot at the end of the refused attempt (design) |
| F34 | low | Z2's `if <expr> == <literal> { return` heuristic is not implemented, and satc's harness has no string literals, so the hard-coding scan cannot fire for project_1 | finder A2 | CONFIRMED | why.md corrected; the M8 manual read is the guard |
| F35 | low | `safety.tool` is validated but `measure_crate` always runs the proxy, and `course()` returns `None` metrics, which `evaluate` cannot sum | finders E, simplification | CONFIRMED | M12 (its row wires the course tool) |
| F36 | low | The M3 smoke calls ran from a temp cwd, so 9 of the 11 leak markers (repo CLAUDE.md, auto-memory) could never fire. Isolation from the repo-root CLAUDE.md is therefore not demonstrated in the real cwd | finder E | CONFIRMED (code) | NOT demonstrated; M6 checks iteration 1's stream (G4) |
| F37 | low | Dead configuration: `toolchain.cargo_locked`, `checks.forbid_unsafe_in_lib`, `agent.resume_session`, project `interface_dir` and `rulings`, and `STEPS` are validated or declared but never read | finders simplification, C, E | CONFIRMED | backlog (cleanup) |
| F38–F44 | low | Efficiency and reuse: the cold deny-unsafe build costs 3.1 s per iteration (46% of check time); four clippy passes where one would do (1.6 → 0.4 s); the selftest really sleeps ~11 s; library files are re-lexed per literal; `_now`/`_read_json`/JSON writers are duplicated; smoke and probe duplicate each other; two fake CLIs | finders efficiency, reuse, simplification | CONFIRMED | backlog (no run-time risk; the agent session dominates run time) |

| F45 | high | Sweep: a failing doc test (`test src/x.rs - f (line 9) ... FAILED`, a name with spaces) matched neither the benchmark nor the extra-test parser, and `cargo test`'s exit code was not read, so SUCCESS fired while `cargo test` fails | sweep (`doctest_hole.py`, both trees) | CONFIRMED | fixed: doc tests are parsed as extra tests; a non-zero `cargo test` exit with no parsed failure blocks SUCCESS |
| F46 | high | Sweep: `integrity.verify` walked a symlinked `src/bin` (or `src/`) and deleted the files in the directory it points to | sweep (`dirlink_probe.py`: deleted `thesis.tex` and `notes/todo.txt`) | CONFIRMED | fixed: a linked `src/`, `src/bin` or `src/interfaces` is removed first and recorded as kind `symlink`; selftest |
| F47 | medium | Sweep, regression from this patch: with cargo in its own session, a terminal hangup or Ctrl-\\ killed only Python (in `--check-only` there are no handlers) and left cargo and a hung test running | sweep (`hup_probe.py`) | CONFIRMED | fixed: while cargo runs, SIGHUP/SIGQUIT/SIGTERM with the default action are caught, cargo's group is killed, and the signal is re-sent; selftest sends a real SIGHUP |
| F48 | medium | Sweep, regression from this patch: the first unanchored test-line regex accepted `test x ... FAILED` quoted in compile output, and was quadratic (6.6 s on an 88 KB line) | sweep (`regex_probe.py`) | CONFIRMED | fixed: only output after cargo's first `Running` line is read, lines are anchored, and a glued line counts only for a benchmark name; selftest checks all three and the 88 KB line (< 1 s) |
| F49 | low | Sweep: resuming from step `init` raised FileExistsError for good if `init_src` was already (partly) copied | sweep (`init_resume.py`) | CONFIRMED | fixed: `init_src` is replaced; the selftest starts from an existing one |
| F50 | low | Sweep: the selftest for the agent's prompt passed on the old behaviour (nothing in the drill prompt is scrubbed) | sweep (`prompt_vacuity.py`) | CONFIRMED | fixed: the check now uses a C directory under a home path and asserts the agent gets the absolute path |

Security findings from the manual pass are S1–S4 below. S1 and S2 are new; S3 is F13, S4 is F9/F21.

## Adversarial guard test (M5 step 2)

Each trap starts from a freshly initialised workspace (`init_workspace`: skeleton copy, `#![forbid(unsafe_code)]`
injected, integrity manifest) holding the fixture's clean variant, which is the state after an agent turn. The trap
applies the agent's edit. Then the loop's own `do_checks` runs: integrity restore, build/test/clippy, safety,
interface, hard-coding, `evaluate`. The control (no edit) succeeds with 1/2 tests, because the planted
known-failing test fails as documented. The traps are now permanent selftest assertions (`_run_m5`), so every
later phase re-proves them.

| Trap | Agent edit | Caught by | Exact result (same before and after the fixes) |
|---|---|---|---|
| (a) | test file `assert_eq!(double(2), 5,` → `4,`, then `cargo test` builds it | `integrity.verify` → `evaluate` | violation `("src/bin/fixture_test.rs", "modified", restored)`; blocker `integrity violations: 1`. Since F4 the restored test is the one measured (1/2); before, the stale tampered binary measured 2/2 |
| (b) | `Cargo.toml`: `libc = "0.2"` | `integrity.verify`; `ffi_scan` on an unrestored crate | `("Cargo.toml", "modified")`, restored; blocker `integrity violations: 1`; unrestored copy: `new_dependency libc` |
| (c) | `build.rs` + `extern "C" { fn abs(x: i32) -> i32; }` | `integrity.ffi_scan` via `safety_check.proxy` | blockers `safety finding: extern_c`, `safety finding: build_rs` |
| (d) | `pub fn first(v: &[u32]) -> u32 { unsafe { *v.as_ptr() } }` | `#![forbid(unsafe_code)]`, proxy counts, `-D unsafe_code` build | blockers `build fails`, `unsafe metrics: 2`, `safety finding: deny_unsafe_build_failed` |
| (e) | `greeting()` returns the 30-character test literal | `integrity.hardcode_scan` | blocker `hard-coding hits: 1` |
| (f) | `pub fn is_positive(x: impl Into<i64>)`, which still compiles against the test | `check_interface.compare` | blocker `interface missing 0, changed 1` |
| (g) | hand edit of `src/fixture.rs` between iterations | `run_pipeline.tamper_check` | record `{"iteration": 2, "modified": ["fixture.rs"], "reverted": true}`; the edit is gone from the workspace |

Gap probes (same driver):

| Probe | Edit | Before | After |
|---|---|---|---|
| x1 (control) | `return x * 2;` (needless_return) | blocked: `agent clippy warnings: 1` | same |
| x2 | x1 + `#![allow(clippy::all)]` in the module | **SUCCESS, clippy 0** | same: gate G1 |
| x3 | x1 + `.cargo/config.toml` `rustflags = ["--cap-lints", "allow"]` | **SUCCESS, clippy 0** | same: gate G1 |
| x4 | three `#[cfg(test)]` unit tests | SUCCESS, tests **4/5** | SUCCESS, tests 1/2 (agent tests reported apart) |
| x5 | `passes` loops forever (fixture, with known-failing `fails`) | blocked only by accident (the cut-off output lost the panic text), tests 0/1, **orphaned test process** | blocked: `tests with no result (hung, crashed or timed out): passes`, tests 0/2, no orphan |
| x6 | the same hang on a satc-like crate (no known-failing test) | **SUCCESS, tests 1/1**, orphaned test process | blocked, tests 1/2, no orphan |
| x6 (control) | no edit | SUCCESS 2/2 | SUCCESS 2/2 |

The scratch driver (`adversarial.py`, session scratchpad) is not committed. Its committed equivalent is selftest
`_run_m5`.

## Fresh-clone dry audit (M5 step 3)

`git clone -q --branch mp4-program <repo> <scratch>/clone` at `5a26167`, then the README followed literally:

```
$ python3 -I MP4/src/run_pipeline.py --help                                 -> exit 0
$ python3 -I MP4/src/run_pipeline.py --project project_1 --dry-run          -> exit 0 (92 lines)
$ python3 -I MP4/src/run_pipeline.py --project project_2 --dry-run          -> exit 0 (94 lines)
$ python3 -I MP4/src/run_pipeline.py --project project_1 --check-only
no crate at MP4/translations/project_1 (no translation yet? pass --crate-dir)  -> exit 2 (expected before M6)
$ python3 -I MP4/src/run_pipeline.py --project project_1 --check-only --crate-dir MP4/src/selftest_fixture --out <scratch>/fixture.check.json
compiles true, tests 1/2, clippy agent 1/1/1/1, harness style 1, unsafe 1/2/1/1  -> exit 0
$ python3 -I MP4/src/summarize.py
PENDING project_1: missing MP4/trajectories/project_1/run_summary.json, MP4/results/project_1.check.json  -> exit 2 (expected)
$ python3 -I MP4/src/summarize.py --check-readme                            -> up to date, exit 0
$ python3 -I MP4/src/config.py --project project_2                          -> config OK, exit 0
$ python3 -I MP4/src/selftest.py                                            -> selftest: 120 PASS, 0 FAIL, exit 0 (47 s)
$ ~/.cargo/bin/rustup toolchain list                                        -> nightly-2025-05-13-aarch64-apple-darwin
$ python3 -c "import yaml; print(yaml.__version__)"                         -> 6.0
```

The clone's tree stayed clean (`git status --short` empty).

- **Not re-run:** the rustup installer and `pip install pyyaml`. Both are already present, and installing
  software is an owner gate.
- **README gaps that block a grader:** none.
- **Wording fixed:**
  - `--dry-run` said it prints the "exact" command; it shows home paths as `~`.
  - The tool-scope section now says the tool rules bound the agent's tool calls, not the code cargo runs.

**After the fixes** (commit `1ac3cd4`), audited again the same way from a new clone:

```
$ python3 -I MP4/src/run_pipeline.py --help                                 -> exit 0
$ python3 -I MP4/src/run_pipeline.py --project project_1 --dry-run          -> exit 0 (92 lines)
$ python3 -I MP4/src/run_pipeline.py --project project_2 --dry-run          -> exit 0 (94 lines)
$ python3 -I MP4/src/run_pipeline.py --project project_1 --check-only       -> no crate at MP4/translations/project_1 ..., exit 2
$ ... --check-only --crate-dir MP4/src/selftest_fixture --out <scratch>/... -> exit 0; tests 0/4 (counted against satc's 4
                                                                               declared tests; the fixture is not satc),
                                                                               clippy agent 1/1/1/1, harness style 1;
                                                                               0 home paths in the JSON and logs
$ python3 -I MP4/src/summarize.py                                          -> PENDING ..., exit 2 (expected)
$ python3 -I MP4/src/summarize.py --check-readme                           -> up to date, exit 0
$ python3 -I MP4/src/selftest.py                                           -> selftest: 166 PASS, 0 FAIL, exit 0 (86 s)
$ git status --short                                                       -> (empty)
```

## Reusability audit (M5 step 5)

```
$ grep -niE 'satc_|psbt_|compactsize' MP4/src/* MP4/configs/prompts/* MP4/configs/agent_system_prompt.md
MP4/src/selftest.py:308:    expect("templates/system prompt/cheatsheet: no satc_/psbt_ identifiers",
$ git grep -nE 'sk-ant-|Bearer |api_key|/Users/' -- MP4/src MP4/configs
MP4/src/scrub_secrets.py:7:api_key_assignment, token_field (JSON access/refresh tokens), email,
MP4/src/scrub_secrets.py:8:home_path (/Users/<name>, /home/<name> -> ~).
MP4/src/scrub_secrets.py:34:    ("api_key_assignment", re.compile(...
```

- **Project identifiers:** the only hit is the selftest's own check.
- **Secret grep:** the three hits are the scanner's own pattern names (refuted above).
- **Python 3.9.12:** `py_compile` of every file exits 0.
- **`-I` safety:** every entry point with a `__main__` inserts its own directory on `sys.path` (11/11).
- **Project switch:** `--project` is the only one; project specifics live in `configs/projects/*.yaml`.

## Security pass

Required for every task that touches input, auth, storage or network (owner's working agreement). The
controller spawns `claude` and `cargo`, writes files derived from model output, and is driven by YAML.

| # | Threat | Where | What was done |
|---|---|---|---|
| S1 | Symlinks planted by agent code (via `cargo test` or `build.rs`). `copytree` copied the **target's content** into committed snapshots (`src_after/`, `changes.diff`), which exfiltrates it into git. The integrity restore (`copy2` / `open(..., "w")`) wrote **through** a symlinked test file into whatever the link points at | `run_pipeline.do_checks`, `integrity.verify` | fixed: snapshots leave symlinks out (`mc.copy_src_tree`), and restores unlink a link before writing. Selftest plants both |
| S2 | `scrub_secrets.py --fix` followed symlinks and would rewrite files outside the repository | `scrub_secrets.iter_files` | fixed: symlinks are skipped. Selftest |
| S3 | Inherited credentials and build flags (API-key billing, changed measurements) | `agent_runner.agent_env`, `mc.cargo_env` | fixed (F13). The remaining `CLAUDE_CODE_*` inheritance is gate G4 |
| S4 | The tool rules are not an OS boundary. Agent-written code runs under cargo with the owner's privileges. The allowed `cargo … test *` also accepts `--config 'target.<triple>.runner=…'`: finder B ran `/bin/echo` that way in scratch, but whether Claude Code's matcher admits the quoted form was not checked | `configs/pipeline.yaml` | README corrected (it claimed "nothing else on the machine"); `subjects/` re-verified before every check (F21). An OS sandbox and a `--config` denial are gate G4 |

**Checked and clean:**
- No `shell=True`, `os.system`, `eval`/`exec`, `yaml.load` (only `safe_load`), `pickle` or `mktemp` anywhere.
- Every subprocess gets an argv list.
- Run ids and `final_iteration_dir` are regex-validated before they become paths.
- Config paths cannot escape `MP4/configs/`.
- Secrets are never echoed: `scrub_secrets` prints file:line:kind only.

**Not applicable or handled:**
- Rate limiting: usage limits pause or exit, and redo attempts are now capped (F26).
- CSRF: no web surface.
- Injection: the repair prompt includes compiler and test output that contains agent-written text. That text
  only reaches the same agent, with the same permissions.

## Refutations (checked and found immaterial)

- `git grep -nE 'sk-ant-|Bearer |api_key|/Users/' -- MP4/src MP4/configs` prints 3 lines, all in
  `scrub_secrets.py`: the docstring `home_path (/Users/<name> ...)` and two lines naming the `api_key_assignment`
  kind. They are the scanner's own pattern names, not secrets. The floor grep (`api_key=`) does not match
  them.
- `evaluate()`'s hard-coded list of blocking safety-finding kinds equals the kinds `integrity.ffi_scan` and
  `safety_check.proxy` emit today. The only risk is future drift (altitude angle).
- Clippy harness attribution by the `src/bin/` path prefix is sound, because integrity deletes any file the
  agent adds there (altitude angle).
- `rate_limit_event` nesting (`rate_limit_info.status`) and `overageStatus` are parsed as the real stream
  shows (E angle, against the M3 streams).
- The `--dry-run` argv equals the argv the loop builds, except for the per-call session id (E angle). The
  session id is now recorded per attempt (F19).
- Every `{{placeholder}}` in the prompt templates has a value, both configurations validate, and every
  documented CLI entry point runs standalone (C angle).
- Python 3.9 / `-I`: every file compiles under the host's 3.9.12, imports are stdlib plus PyYAML, and every
  entry point inserts its own directory on `sys.path` (conventions angle and this session).
- The lexer (`rustlex.scan`) terminates on unterminated strings, raw strings, char literals and block
  comments. All the malformed-input hangs were in `check_interface` (this session, F2).

## The shape of the bugs

Almost every serious finding is the same mistake: **a missing signal read as a good signal.**

| Missing signal | Read as |
|---|---|
| no `FAILED` line for a test | the test passed |
| no `system/init` event | the call was isolated |
| no closing brace | the start of the file |
| no `iter_KK/src_after` | use the previous iteration |
| a lint reported as an error, not a warning | no warning |
| no tamper check on attempt N>1 | no tamper |
| a file outside the two listed directories | not a violation |

The guards were written as lists of known-bad things (a denylist of shell commands, two infrastructure
directories, a tuple of finding kinds, the lines a parser recognises) rather than as closed sets of
known-good things (the declared benchmark tests, the files the agent may write, the events that must
appear). The fixes in this phase convert the measurement side to closed sets: declared test names, a
required init event, an explicit `final_iteration_dir`. Gate G1 asks whether to do the same for the files
the agent may leave in the crate.

## Owner decisions for M6 step 1 (stop semantics and tool permissions)

`what.md` M6 step 1: "If M5 logged discoveries that change stop semantics or tool permissions, ask them now in
one batch and apply to configs with CHANGELOG entries." Some of these need code as well as config, and each
row says so. The recommendations are this review's, not decisions.

| Gate | Question for the owner | Options | Recommendation and why |
|---|---|---|---|
| G1 | Should lint suppression, and files the agent leaves outside `src/`, block a run? (F8, F9; probes x2, x3) | (a) integrity reverts and records every file outside `src/` that is not in the skeleton, and any symlink; (b) a lint-attribute scan of library code (`allow` / `expect` / `deny` / `warn` / `forbid` / `cfg_attr`) blocks SUCCESS, except the D-ALLOW pair; (c) both; (d) neither, and rely on M8's manual grep | (c). Both holes reach SUCCESS today and also silence the graders' own clippy run. (a) also frees an agent stuck with a `build.rs` it cannot delete. Needs code in `integrity.py` and `run_pipeline.py` |
| G2 | Should an auth failure pause the run (resume after `claude auth login`) instead of stopping it? (F15) | pause like a usage limit, with exit 75; or keep the stop | Pause. OAuth expiry already happened in M3, and a stop costs a D7 rerun slot plus the workspace |
| G3 | If satc is clean after iteration 1, is a one-iteration run acceptable? (F27) | (a) keep stopping at the first SUCCESS, and change M6's "iterations ≥ 2" check, since the agent's in-session build/test/clippy cycles are visible in the stream; (b) set `loop.min_iterations: 2`, which costs one more session of quota | Owner's call. (a) spends nothing, and the controller loop is still the Task 2 artefact. (b) shows a controller-fed repair, at the cost of a session that may churn a clean crate |
| G4 | Agent B's environment and cargo flags (S3, S4, F36) | (a) keep the inherited desktop-session environment, as smoke-verified in M3; (b) strip `CLAUDE_CODE_*` and `ANTHROPIC_BASE_URL`, which cannot be verified without one more smoke call beyond D7's 3; (c) start M6/M7 from a plain terminal. Separately: deny `--config` and `--manifest-path` on the allowed cargo commands, and/or use Claude Code's Bash sandbox | (a) for the environment, because it is evidence-backed, with M6 scanning iteration 1's stream for the leak markers. Add the `--config` / `--manifest-path` denials, which have no legitimate use |
| G5 | Tell the agent to keep every public item in `src/<module>.rs`? (F28) | a project-note line (config + CHANGELOG); or a rustdoc-JSON interface comparison (bigger) | The note: one line, and it prevents a phantom "missing" loop |
| G6 | At MAX_ITERATIONS or NO_PROGRESS, ship the best-scoring iteration instead of the last? (F29) | keep the last; or restore the best snapshot into `translations/` and name it in `run_summary.final_iteration_dir` (provenance already follows that field) | Best. Otherwise a session killed mid-refactor in the last iteration ships a crate that does not build |
| G7 | Treat `overloaded` and connection failures like a usage-limit pause, rather than a full iteration? (F30) | pause, with the fallback wait and the attempt cap; or keep | Pause. An outage should not consume NO_PROGRESS rounds |

## Backlog (below the bar, not rows)

F33 (tamper snapshot at the end of a refused attempt), F37 (dead configuration keys), F38–F44 (efficiency and
duplication), plus two minor items:
- after a resumed usage-limit result whose `resets_at` has passed, the wait is the 60-minute fallback rather
  than the margin;
- SIGKILL of the controller still leaves agent B running without its wall clock. SIGHUP is now handled like
  SIGTERM; recording agent B's process group for the next resume needs a PID-reuse guard.
