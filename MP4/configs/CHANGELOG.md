# Configuration changelog

Every change under `MP4/configs/` after the first real run gets a dated entry
here, citing the trajectory evidence that motivated it (what.md session
invariant 2).

## 2026-10-29 — initial

Initial configuration written in program phase M3 (no run evidence yet):
`pipeline.yaml`, `claude_settings.json`, `agent_system_prompt.md`,
`prompts/{initial,repair}.md`, `prompts/status_schema.json`,
`cheatsheet_c_to_rust.md`, `projects/project_{1,2}.yaml`.

## 2026-10-29 — tool policy tightened (before any real run)

Evidence: `docs/programs/mp4/evidence/smoke/smoke_report.json`, call a. Under
`dontAsk` the agent ran `ls -a <dir> <dir> 2>&1 | head -60`, which was neither
allowlisted nor single, and it was approved. Unscoped `Read`/`Glob`/`Grep`
allows also let it read anywhere.

Change in `pipeline.yaml` `agent`: removed the unscoped `Read`, `Glob` and
`Grep` allows (reads inside the crate and the `--add-dir` C directory need no
rule). Scoped `Edit`/`Write` to `./**`. Added denials for the common
read-only shell commands (`ls`, `cat`, `head`, `tail`, `find`, `grep`, `sed`,
`awk`, `echo`, `env`, …).

Verified: `docs/programs/mp4/evidence/smoke/probe/probe_report.json`. One
probe call, the last of D7's 3 smoke calls; all 5 verdicts true.

## 2026-10-29 — loop settings (program phase M4, before any real run)

No run evidence (no run has happened yet). These are new switches for the
loop, not prompt or policy changes:

- `agent.kind: claude` (`fake` is the scripted stand-in, used only by
  selftest drills on a copy of the fixture), `agent.fake_scenario: null`, and
  `agent.resume_session: false` (Claude-session reuse is not implemented;
  `config.py` refuses true).
- `rate_limit.mode` takes `wait` or `exit`. `exit` stops with code 75 and
  prints the `--resume-run` command. It replaces the unused `stop` value.
  Added `rate_limit.resume_margin_seconds: 60`.

## 2026-10-29 — owner gates G1–G7 applied (program phase M6 step 1, before any real run)

Evidence: no run yet. The motivation is review 1
(`docs/programs/mp4/reviews/review-1.md`, findings F8, F9, F15, F27–F30, F36,
S3, S4; probes x2, x3), and the owner's answers are recorded in why.md
D-M5GATES. Each change has a selftest check (`_run_m6`).

- **G1, both guards.** Code: `integrity.sweep_strays` deletes and records
  every file outside `src/` that is not in the skeleton, and every symlink.
  `integrity.lint_attribute_scan` makes any lint-level attribute in library
  code block SUCCESS, except the D-ALLOW pairs. Config: `agent_system_prompt.md`
  now tells the agent that files outside `src/` and symlinks are deleted, and
  lists every forbidden lint-level form, not just `#[allow]`.
- **G2, pause and resume.** Code: a lost login exits 75 with the
  `--resume-run` command, and the run stays open. AUTH_ERROR is no longer a
  stop reason.
- **G3, require 2 iterations.** Config: `pipeline.yaml` `loop.min_iterations:
  2`. `prompts/repair.md` gains a paragraph for a crate that already passes
  every check: review it against the C, and do not rewrite working code.
- **G4, keep the environment, deny the flags.** Config: `pipeline.yaml`
  `agent.disallowed_tools` adds `Bash(cargo *--config*)` and
  `Bash(cargo *--manifest-path*)`. Code: every attempt's assistant text is
  scanned for the leak markers. Hits go in `agent_result.json`
  `leak_markers_found` and in `run.log`; a hit does not stop the run.
- **G5, the project note.** Config: `projects/project_{1,2}.yaml` notes gain
  "Keep every public item of a module defined directly in src/<module>.rs …".
- **G6, ship the best.** Code: at MAX_ITERATIONS and NO_PROGRESS the
  best-scoring iteration is restored into the workspace. `run_summary.json`
  names it in `final_iteration_dir`, adds `last_iteration_dir` and
  `final_selection`.
- **G7, outages pause.** Code: `overloaded` and the new `connection_error`
  outcomes pause for `rate_limit.fallback_minutes` and redo the iteration,
  under the same 3-attempt cap as a usage limit.

## 2026-10-29 — review-2 orchestration fixes (program phase M8; no file under configs/ changed)

Evidence: `docs/programs/mp4/reviews/review-2.md` § 6, the `/code-review max` of the G1–G7 changes
(f69ae8d). No configuration value or prompt changed, but these fixes change how a future run (M9) is
controlled, so they are recorded here next to the G1–G7 entry. Neither committed run is affected: both
stopped at SUCCESS with no violation, pause or ship-best (review-2.md § 6, "Effect on the committed runs").

- The G1 check also runs after the controller's own measurement. The agent's unit tests run during
  `cargo test` and could plant a lint cap. Files under `.integrity/` other than the manifest are strays.
  macOS `.DS_Store` files are removed without counting against the agent. A chmod-ed directory can no
  longer hide or pin a stray. A symlink at a protected path is always replaced.
- The lint-attribute and hard-coding scans read every file under `src/` (not just `*.rs`, and including
  directories named `target`), recognise `#[r#allow]`, and accept the permitted D-ALLOW attribute in
  every valid spelling (`reason = "..."`, across lines, on a `const fn`).
- G6 ranks a guard-blocked iteration (lint attribute, hard-coding, integrity violation, or a known-failing
  test that no longer fails as documented) below every guard-clean one, so a blocked iteration is never
  shipped on a score its blocked behaviour raised.
- A stop decision is saved before the run is finalised, so an interrupted finalise is finished by
  `--resume-run` instead of starting another iteration.
- After any pause, the workspace is checked against a snapshot taken when the pause began.
- `connection_error` now also matches the CLI's own connection-failure wordings: Unable to connect,
  Connection dropped/refused/lost, Can't reach the API server, No internet route, Request timed out.
  HTTP 5xx results stay classified as `connection_error`; this is a decision now recorded. A server error
  is transient and not the agent's iteration, and the 3-attempt cap still hands a persistent one to a
  person. `terminal_reason` and `api_error_status` are recorded in `agent_result.json`.
- The leak scan reads every block the agent wrote, including Write/Edit/Bash inputs and the final status.
  It records `null` (unknown) when the stream cannot be read, and also scans interrupted attempts.
- `loop.min_iterations` may not exceed `loop.no_progress_rounds + 1`.

## 2026-11-11 — repository layout and README aligned with the course template (program phase M15; no file under configs/ changed)

Infrastructure change. Program logic affected: no. No prompt, configuration value, pipeline behaviour,
translation, trajectory or measured number changed; `results/results.md` is byte-identical.

Evidence: the course released a README template on 2026-11-09 (headings `Environment`, `Setup`, `Run`,
`Pipeline`, `Outputs`, `Evaluation`), and the team decided on 2026-11-11 to write the progress report by
hand outside the repository.

- `README.md` now uses the template's six headings in that order, with the template's six `Environment`
  bullets. The former sections are unchanged in content and sit as subsections under the heading they
  belong to. The check-only instructions moved from "How to run the pipeline" to `Evaluation`.
- The report draft, the LaTeX table fragments under `results/`, the rubric traceability map and a
  forum-post draft are no longer part of the repository. They remain in the earlier history.
- `src/summarize.py`: the LaTeX fragments are written only with `--tex`, or refreshed where `results/`
  already holds one. `--report` and `--check-report` print `local draft absent, skipped` and exit 0 when no
  draft is on disk. `results.md` and `repair_mining.md` are generated exactly as before.
- `src/selftest.py`: the README check enforces the six template headings, the section placement and the
  `Environment` bullets; new cases cover a tree without the local drafts and fragments.

## 2026-11-11 — course unsafe-metrics tool becomes the safety backend (program phase M12)

Infrastructure change. Program logic affected: no. No prompt changed, no run was repeated and no Rust
changed (`integrity.py --provenance` exit 0 for both projects before and after).

Evidence: the course released `newmetrics` on 2026-11-09, after both committed runs (2026-10-29). Measured
with it on 2026-11-11, both final translations and all four iteration snapshots score 0 unsafe lines,
0 unsafe calls, 0 unsafe casts and 0 pointer arithmetic
(`trajectories/project_N/official_safety/2026-11-11/raw_*.txt`). The interim proxy had reported the same.

- `pipeline.yaml` `safety.tool`: `proxy` -> `both`. `safety.course_cmd`: `[cargo, newmetrics]`.
  New key `safety.course_aggregate` (path to the staff `aggregate.py`; the environment variable
  `MP4_NEWMETRICS_AGGREGATE` overrides it). `safety.course_version` records the tool version and commit.
  The value `course` is no longer accepted for `safety.tool`: the course tool has no forbid, FFI,
  `build.rs` or dependency guard, so it never runs without the proxy.
- `src/safety_check.py`: the course adapter copies the crate to a temporary directory, runs the staff
  command there, parses the result and deletes the copy. It never runs in `translations/`. New
  `--official` mode measures the final crate and every iteration snapshot of the final run.
- `src/run_pipeline.py`: the safety step follows `safety.tool`. A course tool that is not installed, or
  that fails, is a finding that blocks SUCCESS; `--check-only` then prints a note and reports the proxy's
  numbers under their own label.
- `src/summarize.py`: the safety table names the measuring tool, lists the tool's two extra metrics and
  one proxy comparison line; the per-iteration tables use the official per-snapshot counts. A mismatch
  between `run_summary.json` `official_safety` and the check-only result stops the generator.
- `run_summary.json` of both projects gained an `official_safety` block. The run's own record (`final`,
  `iteration_summary.json`) is unchanged and still names the proxy it used at the time.
- Differences between the proxy and the tool are documented in the README, not "fixed": on the
  self-test fixture the proxy counts a `transmute` as an unsafe cast (1) where the tool counts 0 casts;
  the other three counts agree (1 line, 2 calls, 1 pointer arithmetic). The proxy's regexes were left as
  they are.
- The config hash changes with `pipeline.yaml`, so the two finished runs cannot be resumed under the new
  configuration. Neither needs to be: both ended at SUCCESS.

## 2026-11-14 — full-review fixes to the controller (program phase M16; no file under configs/ changed)

Infrastructure change. Program logic affected: no. No prompt or configuration file changed, no run was
repeated and no Rust changed (`integrity.py --provenance` exit 0 for both projects before and after; the
committed results regenerate byte-identical).

Evidence: a full code review of the whole pipeline (ten independent reviewer angles; probes in scratch
copies). Most findings were in the course-tool adapter added on 2026-11-11, which had not been reviewed.
None of them changes a committed number.

- `src/safety_check.py`: a missing `aggregate.py` no longer counts as "tool not installed": when
  `cargo newmetrics` is on PATH the tool runs and the controller's own sum of its metric lines is the
  result (`"aggregate": "summed by the adapter ..."`). `MP4_NEWMETRICS_AGGREGATE` applies to
  `pipeline.yaml` only, not to the self-test's own configurations. A compilation unit with a metric line
  missing is a failed measurement, not a 0. The tool runs in its own process group, and a hanging
  `aggregate.py` is a failed measurement. `--official` checks that the tool can run before it touches
  anything, measures into a temporary directory, and records nothing (exit 2) unless every measurement
  succeeded; before, it deleted the dated directory first and recorded null metrics with exit 0 when the
  tool failed. `--all-snapshots` no longer crashes on `run_summary.json`.
- `src/checks.py`: a clippy run that exits non-zero without an error message (component not installed,
  timeout) counts as an error; before, it was read as 0 warnings.
- `src/summarize.py`: the per-iteration table recognises `safety_tool: both`; the idiom table prints `n/a`
  for a crate whose clippy did not run.
- `src/scrub_secrets.py`: `--check` on a path that does not exist is an error (exit 2); the example-domain
  allowlist matches the domain or a subdomain only.
- `src/agent_runner.py`, `src/config.py`: a startup line that reports a skill or plugin is an isolation
  violation; `agent.env` must set `CLAUDE_CODE_DISABLE_CLAUDE_MDS` and `CLAUDE_CODE_DISABLE_AUTO_MEMORY`
  to `"1"`.
- `src/mp4common.py`: a PyYAML that `python3 -I` cannot import is reported in one sentence with the
  reason. `src/fake_agent.py`: its `translations/` guard resolves symlinks.
- `src/run_pipeline.py`: the course tool's three span files are in the list of logs the loop scrubs.
- `src/selftest.py`: 25 new assertions, including four rules that had none (known-defective test must
  fail on its documented assertion; a test that fails in any execution is failed; a lost derive is an
  interface change; a tool run without metric lines is a failure).
- README: PyYAML and `python3 -I`; what `--provenance` compares; `--official` is the recording command.
