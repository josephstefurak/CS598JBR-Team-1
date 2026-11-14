# Review 5 — pre-validation full review (M16, 2026-11-14)

The close's pass-1 review, run ahead of the validator (why.md D-ORDER). **Reviewed commit: `894ef53`.**
The close after M13 reviews only `894ef53..HEAD` plus whatever M13 changes.

## Scope

- Cumulative scope = PR scope: `ffcb9721..894ef53`, 39 commits, 331 files, 47,262 insertions, 0 deletions.
  `main` is an ancestor of `mp4-program` (0 commits ahead); there were no intermediate merges.
- By area: `MP4/src` + `MP4/configs` 36 files / 8,153 lines; `MP4/trajectories` 161 / 19,383;
  `MP4/subjects` 45 / 7,366; `MP4/translations` 23 / 3,053; `MP4/results` 32 / 1,975; `docs/` 26 / 6,755;
  repository root 4 files / 72 lines.
- Trajectories, subjects and translations are evidence. They were read, not reviewed as code, and nothing
  in them was edited.

## Ground truth before the review (at `894ef53`)

`integrity.py --provenance` `"ok": true` for both projects; sha256 over every file under
`MP4/translations/` `214c0f7f...`; `selftest: 316 PASS, 0 FAIL`; tree clean. Fresh-clone walk of the same
code at `195f6c6` in review 4: every documented command exit 0.

Conformance audit (done by script, not by the reviewers): 13 `done` rows, each with existing commit
hashes, a phase-log entry and numbers; 15 "NOT demonstrated" paragraphs; every path, `pipeline.yaml` key,
CLI flag and stop-reason constant cited in the README, `CLAUDE.md`, `handoff.md`, `runbook.md`,
`environment.md` and the CHANGELOG exists; ledger claims re-derived from the trajectories match
(project_1: 29 turns, 2 permission denials; project_2: 87 turns, 3). One false ledger sentence was found by
the reviewers (D6 below).

## Method

`/code-review max --fix` over the whole range. Ten finder angles, each a separate reviewer working
read-only in its own scratch copy: line-by-line, removed behaviour, cross-file tracing, Python and platform
pitfalls, wrapper correctness, reuse, simplification, efficiency, altitude (claims against enforcement),
conventions. Seven ran on the default model, three on a smaller one. 61 candidates came back.

Deviations from the skill's recipe, to limit quota (the session hit the 5-hour usage limit once, with all
ten reviewers running; they were resumed in two waves):

- No separate verifier agent per candidate and no sweep agent. A candidate counts as CONFIRMED when a
  reviewer reproduced it with a probe whose output is in its report, or when the fix's new assertion goes
  red with the fix reverted (16 of 16 mutations caught, table below). The main cluster was reproduced
  independently by three or four reviewers each. Candidates read from code only are PLAUSIBLE.
- The second-wave reviewers were given the first wave's 15 findings and told to look elsewhere.

After dedup: **47 distinct findings.** 27 fixed in this phase (the mechanical batch), 3 put to the owner,
17 to the post-merge backlog. No candidate was refuted. None makes a committed number wrong: every reviewer
that regenerated `results.md` got it byte-identical, and the unsafe metrics, test counts and clippy counts
were re-derived from the artifacts.

Where the defects were: 20 of the 30 non-backlog findings are in or around commit `cf6a831` (M12, the
course-tool retrofit), the one large change no review had covered.

## Findings

Groups: A = one command away from destroying something; B = wrong behaviour that ships; C = a check or
assertion that cannot fail; D = a false statement someone would act on. "Today" = affects a grader-run
command or a statement in the tree as committed; "future" = only a new agent run.

| ID | Where (at `894ef53`) | From | Defect and failure scenario | Verdict | Went to |
|---|---|---|---|---|---|
| A1 | `safety_check.py:450-489`, `:552` | cf6a831 | `--official` deleted `official_safety/<date>/` before checking the tool could run, and on a failing tool wrote null metrics into `run_summary.json` and exited 0. Probe: `--official --date 2026-11-11` without the tool: 16 committed files deleted, exit 2; with a failing tool: `official_safety.final` all null, exit 0, then `summarize.py` exits 1 | CONFIRMED (4 reviewers) | **Fixed**: availability checked first; measured into a temporary directory that replaces `<date>/` only when every measurement succeeded; otherwise nothing is recorded and exit 2 |
| B1 | `safety_check.py:273`, `run_pipeline.py:125`, `summarize.py:119-145`, `selftest.py:2028` | cf6a831 | A missing `aggregate.py` at the configured home path counted as "tool not installed". The README's own sequence then: `--check-only` exit 0 with `"safety_tool": "proxy"`, the six committed course-tool logs deleted, `summarize.py` rewrites the row to "interim proxy; official tool PENDING", `selftest.py` 1 FAIL | CONFIRMED (4 reviewers) | **Fixed**: with `cargo newmetrics` on PATH the tool now runs and the adapter's own sum is the result. With no tool at all (owner answer Q1, "Keep official files"): the committed `check.json` and logs stay, and that machine's proxy-only result goes to `project_N.check.proxy.json` (gitignored) |
| B2 | `safety_check.py:259` | cf6a831 | `MP4_NEWMETRICS_AGGREGATE` overrode the self-test's explicit configurations: with the variable set as the README says, `selftest.py` reported 1 FAIL or aborted | CONFIRMED | **Fixed**: the override applies to `pipeline.yaml` only |
| B3 | `MP4/README.md:150`, `mp4common.py:49` | 23c88b2 | `python3 -I` ignores `pip --user` installs, pip's default on the macOS system Python: every command dies with `ModuleNotFoundError: No module named 'yaml'` | CONFIRMED (2 reviewers; the pip step itself not observed, no network) | **Fixed**: README says so and gives the venv line; the error is one sentence with the reason |
| B4 | `checks.py:219-240` | a8994d9 | A clippy that never ran (component missing, timeout) scored 0 warnings and `ok: true`; `evaluate` returned SUCCESS | CONFIRMED (2 reviewers) | **Fixed**: non-zero exit without an error message counts as an error |
| B5 | `safety_check.py:505-507` | a8994d9 | `--all-snapshots` crashed on `run_summary.json` (`NotADirectoryError`) for both projects (review 3 D10, deferred to M12 and not done) | CONFIRMED (3 reviewers) | **Fixed** |
| B6 | `safety_check.py:246-251` | cf6a831 | A unit with one metric line missing was summed as that metric being 0 | CONFIRMED | **Fixed**: unequal label counts = failed measurement |
| B7 | `safety_check.py:309-321` | cf6a831 | Course-tool timeout killed only the direct child; a hanging `aggregate.py` raised an uncaught `TimeoutExpired` | PLAUSIBLE (read) | **Fixed**: own process group and group kill; aggregate timeout = failed measurement |
| B8 | `summarize.py:335-337` | cf6a831 | The trend table knew only `"course"`; the loop writes `"both"`, so a run under the current config would be labelled "proxy ... PENDING" (future) | CONFIRMED (3 reviewers) | **Fixed**; the "during the run the controller used the proxy" note now depends on what the run recorded |
| B9 | `summarize.py:152-154`, `:181` | 73be41e | `KeyError` when the final crate does not build (future) | CONFIRMED | **Fixed**: `n/a` |
| B10 | `scrub_secrets.py:79-80` | a8994d9 | `--check` on a path that does not exist printed `0 hit(s)`, exit 0: the pre-commit secret gate passed from the wrong directory | CONFIRMED | **Fixed**: exit 2 |
| B11 | `scrub_secrets.py:64` | 1ac3cd4 | E-mail allowlist by bare suffix: `x@gobyexample.com` allowed | CONFIRMED | **Fixed** |
| B12 | `agent_runner.py:99-122` | be3de95 | The startup check ignored `skills` and `plugins` (future) | CONFIRMED | **Fixed** |
| B13 | `config.py:110-111` | be3de95 | Nothing required the two isolation variables in `agent.env` (future) | CONFIRMED | **Fixed** |
| B14 | `fake_agent.py:49-50` | 23c88b2 | The fake agent's `translations/` guard failed through a symlinked path | CONFIRMED | **Fixed** |
| B15 | `run_pipeline.py:513-520`, `safety_check.py:392` | cf6a831 | Under `both`, the proxy's own unsafe counts no longer block SUCCESS (code the course tool does not compile, e.g. behind a dead `cfg`, passes). Before M12 they blocked (future) | CONFIRMED (2 reviewers) | **Fixed** (owner answer Q2, "Restore the blocker"): `unsafe metrics (proxy): N` blocks SUCCESS under `both` |
| C1 | `selftest.py:1669` | 2cb0ce8 | The trend-label test used `"course"`, a value the loop cannot write | CONFIRMED | **Fixed**: fixture is `"both"`; new assertion, mutation caught |
| C2 | `selftest.py:1943`, `run_pipeline.py:440` | cf6a831 | "every log both writes is in the list the loop scrubs" tested four typed names; three span files were not in the list | CONFIRMED (2 reviewers) | **Fixed**: asserted over the directory; the three files added to `MEASURE_LOGS` |
| C3 | `run_pipeline.py:500-502` | 23c88b2 | The rule that makes libpsbt's 3 of 4 a legitimate SUCCESS (the known-defective test must fail on its documented assertion) had no assertion: removed, selftest 316/0 | CONFIRMED (mutation) | **Fixed**: assertion added, mutation caught |
| C4 | `safety_check.py:316` | cf6a831 | "no metric lines = failure" unguarded: removed, 316/0. Zero is the graded value | CONFIRMED (mutation) | **Fixed**: `--silent` fake, mutation caught |
| C5 | `checks.py:88` | a8994d9 | "a test that fails in any execution is failed" unguarded | CONFIRMED (mutation) | **Fixed** |
| C6 | `check_interface.py:300` | a8994d9 | "a lost derive is an interface change" unguarded | CONFIRMED (mutation) | **Fixed** |
| C7 | `safety_check.py:319-331` | cf6a831 | The `aggregate.py` cross-check ran only in the optional live case | CONFIRMED | **Fixed**: agreeing, disagreeing and hanging scripts |
| C8 | `selftest.py:469` | 23c88b2 | Each selftest run left one `mp4crate_*` copy in the temp directory (11 found) | CONFIRMED | **Fixed** |
| D1 | `MP4/README.md:225-227`, `:290`, `:330` | 73be41e | "`--provenance` checks that [translations/] is byte-identical": it compares `src/` only (edits to `Cargo.toml`, added `clippy.toml`/`build.rs`: exit 0; those are caught by `--check-only` as integrity violations), and the same edit made to the translation and the snapshot passes | CONFIRMED (9 probes) | **Fixed (wording)**: the README says what is compared. The stronger check is backlog PM11 |
| D2 | `MP4/README.md:361` | cf6a831 | The README offered graders `--official`, which writes a new dated directory and edits `run_summary.json` | CONFIRMED | **Fixed (wording)**: it is the recording command; `--check-only` and `--tool course` verify |
| D3 | `MP4/README.md:272-274` | 73be41e | "removes anything that looks like ... an e-mail address": six upstream licence-header addresses are kept on purpose | CONFIRMED | **Fixed (wording)** |
| D4 | `MP4/README.md:29-31` | be3de95 | "aborted if ... any capability beyond the configured tools": skills and plugins were not checked | CONFIRMED | **Fixed** (B12; wording lists what is checked) |
| D5 | `MP4/README.md:395-396` | cf6a831 | "both must be clean for SUCCESS" is not true of the proxy's four counts (B15) | CONFIRMED | True again through B15 |
| D6 | `where.md` M12 log | cf6a831 | "`--all-snapshots --tool course` also works": it crashed | CONFIRMED | True since B5; corrected in the M16 log |
| D7 | `runbook.md:13`, `program.yaml:21`, `where.md:171` | 04dcc76, 0122f84 | Three tracked files held the owner's absolute home path; `runbook.md:13` was also a Stage 0 command that fails on any other checkout | CONFIRMED | **Fixed**: `~` |
| D8 | `docs/programs/mp4/evidence/smoke/**` (11 files) | 2e0f3d2, 5cadf51 | The committed smoke evidence holds the per-user macOS temp path and the session scratch path with the numeric uid. No secret, e-mail or account id (all seven streams read). Reviews 3 and 4 said "temp paths: 0" because their grep was scoped to `MP4/` | CONFIRMED | **Accepted as is** (owner answer Q3): evidence is not rewritten; recorded as why.md D-EVIDENCE; a temp-path scrub rule is backlog PM23 |

Fixed in the mechanical batch (`9e9ee59`, `7b98412`): 27 (A1, B2-B14 = 13, C1-C8 = 8, D1-D4, D7 = 5); D6
became true through B5. Fixed after the owner's answers, in the same session: B1 (rest), B15 and with it
D5. Accepted by the owner: D8. No remediation row was needed.

Owner batch, asked once with `AskUserQuestion` (answers verbatim): Q1 no-tool `--check-only` -> "Keep
official files (Recommended)"; Q2 proxy counts under `both` -> "Restore the blocker (Recommended)"; Q3
temp paths in the smoke evidence -> "Accept as is (Recommended)".

### Mutation check of the fixes

Each fix reverted one at a time in a scratch copy, running only the new section (`_run_m16`, 25 assertions,
baseline 25 PASS / 0 FAIL): parser label counts, no-metrics guard, known-failing rule, any-execution rule,
lost derive, trend label, clippy exit code, aggregate disagreement, `--official` failed run, env override,
scrub missing path, e-mail suffix, skills/plugins, env isolation, fake-agent guard, idiom table.
**16 of 16 caught** (14 by a FAIL, 2 by an exception the reverted code raises).

### Below the production bar: post-merge backlog (17 findings in 13 rows, `post-merge.md` PM10-PM22)

Future-run only, latent with everything at 0, or quality: no course-tool preflight before a run; three
SUCCESS blockers missing from the repair digest; `summarize.compare` gaps (crate path,
`subjects_checksums_ok`, interface counts, the proxy-against-course pair); `--check-only` measures a
tampered benchmark file before reporting it; provenance could replay the agent's own Write/Edit calls;
the official numbers are stored five times with one cross-check; `safety.course_version` is free text;
two config keys nothing reads; JSON is scrubbed after encoding; three duplicated constants; `both()`
drops the course tool's per-metric findings; the selftest globs the shared temp directory; a prompt line
cites `why.md`; no selftest drives `measure_crate` with `both`; `selftest.py --help` runs the suite.

## Checked and clean

- Secrets and personal data: no key-shaped string, no account e-mail, organisation id or host name in any
  tracked file; every `system/init` line shows `apiKeySource: none`; home paths under `MP4/` are `~`.
- Tracked files: no PDF, report draft, `.tex`, traceability map, forum-post draft, `__pycache__`,
  `target/`; every file the README names is tracked.
- Zero-credit traps: benchmark tests, interfaces, `Cargo.toml`, `Cargo.lock` byte-identical to the
  skeleton for both projects (checksums 13/13, 28/28); library code has the forbid line and the one
  permitted `#[allow]`; no `unsafe`, `extern`, `transmute` or raw pointer; prompts contain no function
  body and no expected output.
- CHANGELOG rule: the only post-run configuration change (`cf6a831`, `pipeline.yaml` safety block) has
  its dated entry; the other seven configuration files hash-match both run manifests.
- Generators: `summarize.py` regenerates `results.md` and `repair_mining.md` byte-identical;
  `--check-readme` up to date; every number in the tables re-derived from the artifacts.
- Python: 3.9-clean, stdlib + PyYAML only, no `shell=True`, every `open()` has an encoding, every
  subprocess on the grader paths has a timeout (slowest call about 4 s against 900 s).
- Cost of the grader commands: `--check-only` for libpsbt 12.5 s cold (13 cargo calls); selftest about
  155 s, no network.
- `handoff.md` and runbook Stage 5: commands are in a safe order and push only `main` after a `--no-ff`
  merge.
