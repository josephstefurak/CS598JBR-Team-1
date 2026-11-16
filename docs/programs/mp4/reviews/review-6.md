# Review 6 — the close, pass 1 (scoped)

*2026-11-16. Ledger row M17. Scope by owner direction (why.md D-ORDER): only
`894ef53..bc78d11`, the diff since the commit M16's full review covered, under
the production bar of the program-builder close protocol.*

## Scope

`git diff --stat 894ef53..bc78d11`: 24 files, 1018 insertions, 78 deletions.

| Area | Files | What |
|---|---|---|
| Controller | 10 files under `MP4/src` (about 260 changed lines) | M16's fixes |
| Self-test | `MP4/src/selftest.py` (+289) | `_run_m16`, 29 assertions |
| Grader-facing docs | `MP4/README.md`, `MP4/configs/CHANGELOG.md`, `MP4/docs/validation_output.txt`, `.gitignore` | M16 wording, M13 output |
| Program docs | 9 files under `docs/programs/mp4` | ledger, reviews, backlog, handoff, evidence |

Cumulative scope and PR scope are the same range, `ffcb9721..HEAD` (no
intermediate merge happened); the part before `894ef53` is review 5's.

## How it was reviewed

Two independent reads of the source diff, not the ten-reviewer `max` recipe
(deviation, see the phase log: the owner asked on 2026-11-14 to be mindful of
usage limits, and the range is small):

1. The session read every source hunk.
2. One fresh reviewer, given the diff and the bar but not the session's
   conclusions, read the changed functions and ran probes in scratch clones.

Proof rule: a finding counts only with a concrete scenario and a probe that
shows it.

## Findings that meet the bar

**None.** No code was changed by this pass.

## Probes (reviewer, scratch clones of `bc78d11`; the repository was not touched)

| Probe | Result |
|---|---|
| `parse_course_output` on the 8 committed `raw_*.txt` files | 2 compilation units each, all 7 labels the same number of times: the new rule fails no committed measurement |
| `summarize.py`, `--check-readme`, `scrub_secrets.py --check MP4/`, provenance for both projects | all exit 0, tree clean afterwards |
| `--check-only` for project_1 with the course tool hidden from PATH | exit 0, both notes printed, `project_1.check.proxy.json` written and ignored by git, committed `check.json` hash unchanged |
| `--check-only` for both projects with the tool present | exit 0; differences from the committed files are the timestamp, cargo timings and the key order of two tests; no number changes |
| `safety_check.py --official --date 2026-11-11` with the tool hidden | exit 2, the existing directory intact, no temporary directory left |
| `safety_check.py --all-snapshots --no-build` | exit 0, `iter_01` and `iter_02` |
| Course-tool timeout set to 2 s with a command that forks a sleeper | returns in 2.0 s, exit 124, `course_tool_failed`, 0 processes left |
| `--dry-run` | exit 0, both `CLAUDE_CODE_DISABLE_*=1` shown |
| The new `skills`/`plugins` rule against the 11 committed init lines | 0 violations |
| README's virtual-environment instruction under `python3 -I` | true: the environment's packages are importable |
| `selftest.py` in the clone | 344 PASS, 0 FAIL with the tool; 342 PASS, 0 FAIL with it hidden |
| Four `_run_m16` guarantees reverted one at a time (proxy blocker, restore of `check.json`, `if bad:` in `_official`, `skills`/`plugins` rule) | each turns its assertion red (the fourth by an `IndexError` at the assertion) |

## Below the bar (to `post-merge.md`, reasoning only, not proven)

PM24 to PM28: an interrupt inside `--check-only` can leave the logs directory
deleted (as before M16); Ctrl-C does not reach the course tool's process
group; a future CLI that lists built-in skills would abort every call; the
CHANGELOG entry counts 25 assertions where the phase ended with 29; a
`.venv/` created inside `MP4/` would be walked by the scrubber.

## Not read

By the reviewer, hunk only: `agent_runner.check_init`,
`config.validate_pipeline`, `summarize.iteration_trend`/`md_idiom`/
`render_tex`, `run_pipeline.check_only` body and the loop's use of
`MEASURE_LOGS`, `fake_agent.main`, `mp4common.load_pipeline_config`, and
`selftest.py` outside `_run_m16`. The session read those hunks. The program
docs in the range were not reviewed by the reviewer; they were written and
checked in M16 and M13.

## Outcome

Pass 1 changed no code and found nothing that survived, so `state` goes from
`building` to `ready-to-merge`. No pass 2.
