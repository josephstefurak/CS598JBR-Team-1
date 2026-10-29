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
