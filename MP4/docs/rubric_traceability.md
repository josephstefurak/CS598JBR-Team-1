# Rubric traceability matrix

One row per rubric row (`R-*`, 21 rows, 430 points) and per zero-credit trap from the handout (`Z1`–`Z16`):
37 rows. Each row names the artifact that answers it, the command that checks it, the evidence, a status and
the build phase that completes it.

- **verified**: checked now, with the command output below.
- **pending-run**: needs the translation runs (no project has been translated yet). Where a guard in the
  controller is involved, the evidence column shows it working on the controller's own test fixture.
- **proxy**: measured with the interim safety proxy until the course's unsafe-metrics tool is released.
- **owner-blocked**: needs an input from outside the repository (the course tool or validation script, or the
  progress report in Overleaf).

Phases refer to our build plan: M5 = this review (2026-10-29), M6/M7 = the translation runs for project_1/
project_2, M8 = review of the translations, M10 = results and report draft, M11 = final review,
M12/M13 = course tools, M14 = report placement. All paths are relative to `MP4/` unless they start with `MP4/`
or `docs/`.

| Key | Artifact path(s) | Verification command | Evidence | Status | Phase |
|---|---|---|---|---|---|
| R-T1-README | `README.md` | `test -f MP4/README.md`; one heading per required item; framework version vs `claude --version`; model vs `configs/pipeline.yaml`; the run command exists in `src/` | 12/12 required headings (lines 9-181); `claude --version` = `2.1.235 (Claude Code)` = README; `model: opus` = README; generated sections up to date; `src/run_pipeline.py` exists. The usage-limit section is filled from the runs (M10) | verified | M5; M10 |
| R-T1-CONFIGS | `configs/` | `ls MP4/configs/`; `grep -rn 'configs/' MP4/src/`; `git grep -nE 'sk-ant-\|api_key=' -- MP4/` | 7 entries (pipeline, settings, system prompt, cheatsheet, CHANGELOG, `prompts/`, `projects/`); `src/` loads them (`config.py`, `agent_runner.py`); secret grep prints nothing (exit 1) | verified | M5 |
| R-T1-TOOLLIST | `README.md` (Models, frameworks and tools used; External tools) | README table vs the tool names seen in `trajectories/project_*/run_*/iter_*/agent.stream.jsonl` | README lists Claude Code 2.1.235, Opus, the toolchain, clippy, Python/PyYAML, the safety proxy, CRUST-bench. No run trajectories yet; the permission probe saw exactly the configured tools (`Bash, Edit, Glob, Grep, Read, StructuredOutput, Write`) | pending-run | M6, M7, M11 |
| R-T2-SRC | `src/run_pipeline.py`, `src/agent_runner.py`, `src/prompt_builder.py`, `src/checks.py` | read the loop; stop conditions; `cargo +nightly-2025-05-13` calls; feedback into the next prompt; `--project`; `grep -niE 'satc_\|psbt_\|compactsize'` | `run_loop`/`_drive`/`do_checks`/`evaluate`/`decide_stop`/`build_prompt`; six stop constants; every cargo call is `cargo +nightly-2025-05-13`; repair prompts carry the digest; `--project` is the only project switch; project names appear only in the selftest's expected values. selftest 162 PASS, including drill A (SUCCESS at iteration 2, the iteration-2 prompt carries iteration-1 feedback) and the 7 guard traps | verified | M5 |
| R-T2-CONFIGS-PROMPTS | `configs/prompts/`, `configs/agent_system_prompt.md`, `configs/projects/*.yaml` | prompts present; guardrail phrases greppable; no function bodies | `initial.md`, `repair.md`, `status_schema.json`; "Do not modify ... test" in both templates; FFI, unsafe and hard-coding rules in all three texts; selftest: every guardrail phrase present for both projects and both templates, no `satc_`/`psbt_` identifiers and no Rust fn bodies | verified | M5 |
| R-T2-TRAJECTORIES | `trajectories/project_1/`, `trajectories/project_2/` | both non-empty; per-iteration stream, check logs and summary; iterations >= 2; secret scan empty | Only `baseline/` exists (no run yet). On the fixture every iteration directory holds all 17 design-reference files (selftest drill A); `scrub_secrets.py --check MP4/` = 0 hits | pending-run | M6, M7, M8 |
| R-T2-REPRO | `README.md` (How to run), `src/run_pipeline.py` | README commands copy-pasteable; `--dry-run` and `--check-only` exit 0 from a fresh clone | Fresh clone (M5): `--help` 0, `--dry-run` 0 for both projects, `--check-only` on the fixture 0; selftest in the clone 120/120 before the M5 fixes | verified | M5; M11 |
| R-T3-P1-COMPILE | `translations/project_1/`, `src/check_interface.py`, `results/project_1.check.json` | `cargo +nightly-2025-05-13 build --all-targets --locked` in `MP4/translations/project_1`; `python3 -I MP4/src/check_interface.py --project project_1`; `cmp` of `src/bin/satc_test.rs` with `subjects/` | Not yet measurable: `translations/project_1/` holds only `.gitkeep`. Guards proven on the fixture: trap (a) test-file edit restored and flagged, trap (f) changed signature flagged | pending-run | M6, M8 |
| R-T3-P1-CORRECT | `translations/project_1/`, `results/project_1.check.json`, `src/integrity.py` | `cargo +nightly-2025-05-13 test --locked --no-fail-fast`; `python3 -I MP4/src/integrity.py --scan --project project_1`; behavioural spot checks against the C (M8) | Not yet measurable. Counting is checked: tests are counted against the benchmark's 4 declared names (`satc_collision_test`, `satc_point_scale_xy_test`, `satc_point_test`, `satc_polygon_get_centroid_test`), and a test that hangs or crashes counts as failed (selftest) | pending-run | M6, M8 |
| R-T3-P1-SAFETY | `src/safety_check.py`, `results/project_1.check.json` | `python3 -I MP4/src/safety_check.py --project project_1` (interim proxy); official numbers with `--tool course` once the course tool is released | Proxy proven on the fixture: trap (c) `extern "C"` + `build.rs` flagged, trap (d) unsafe block counted (unsafe metrics 2) and the `-D unsafe_code` build fails | proxy | M6, M12 |
| R-T3-P1-IDIOM | `translations/project_1/`, `trajectories/project_1/run_*/iter_*/clippy_*.json` | the exact rubric clippy command in `MP4/translations/project_1`; per-group counts split agent vs harness | Not yet measurable. Harness baseline (M1): satc's test file contributes 0 clippy warnings in all four groups | pending-run | M6, M8 |
| R-T3-P2-COMPILE | `translations/project_2/`, `src/check_interface.py`, `results/project_2.check.json` | as P1 in `MP4/translations/project_2` | Not yet measurable (`.gitkeep` only) | pending-run | M7, M8 |
| R-T3-P2-CORRECT | `translations/project_2/`, `results/project_2.check.json` | as P1; `read_test_vector` is a defective benchmark test (README "Infrastructure interventions"), ceiling 3/4 | Not yet measurable. Benchmark names: `empty_input_test`, `encode_decode_test`, `read_test_vector`, `test_vector`; a result line glued behind the program's own stdout is still parsed (selftest) | pending-run | M7, M8 |
| R-T3-P2-SAFETY | `src/safety_check.py`, `results/project_2.check.json` | as P1 | as P1 | proxy | M7, M12 |
| R-T3-P2-IDIOM | `translations/project_2/`, `trajectories/project_2/run_*/iter_*/clippy_*.json` | as P1 | Not yet measurable. Harness baseline (M1): libpsbt's test file contributes 2 style warnings (`single_match`, `uninlined_format_args`), excluded from the agent counts | pending-run | M7, M8 |
| R-T4-PIPELINE-DESC | progress report (Overleaf), `README.md` | report section with framework, model, tools, feedback path, single agent, stopping condition, diagram | Report not written yet | owner-blocked | M10, M14 |
| R-T4-OVERALL-RESULTS | `results/results.md`, `results/overall.tex`, report | `python3 -I MP4/src/summarize.py` (refuses to write if the final run and `--check-only` disagree) | `summarize.py` prints `PENDING project_1: missing ...run_summary.json, ...check.json` (exit 2): no run yet | owner-blocked | M10, M14 |
| R-T4-SAFETY-ANALYSIS | `results/safety.tex`, report | course unsafe-metrics tool output; per-iteration counts from `safety_check.py --all-snapshots` | Course tool not released | owner-blocked | M12, M14 |
| R-T4-IDIOM-ANALYSIS | `results/idiom.tex`, report | generated table; lint names cited from `clippy_*.json` | No run yet | owner-blocked | M10, M14 |
| R-T4-REPAIR-ANALYSIS | report, `trajectories/` | each example cites a trajectory path whose quoted message greps in it | No run yet | owner-blocked | M8, M10, M14 |
| R-T4-REFLECTION | report | five prompts answered | No run yet | owner-blocked | M10, M14 |
| Z1 | `src/integrity.py` (`verify`), `src/run_pipeline.py` (`do_checks`) | the M5 guard traps in `python3 -I MP4/src/selftest.py`; on the submission: `cmp` of tests, interfaces, `Cargo.toml`, `Cargo.lock` against `subjects/` | Trap (a): `[("src/bin/fixture_test.rs", "modified", restored)]`, blocker `integrity violations: 1`, and the restored test is the one measured; trap (b): `Cargo.toml` modified, restored | pending-run | M5 guard; M8 on the translations |
| Z2 | `src/integrity.py` (`hardcode_scan`) | selftest trap (e); M8 manual read of every function that consumes test-visible inputs | Trap (e): blocker `hard-coding hits: 1`. Limits: literals split with `concat!` are not caught, and satc's harness has no string literals, so for project_1 the M8 read is the guard | pending-run | M5 guard; M8 |
| Z3 | `src/integrity.py` (`ffi_scan`), `src/safety_check.py` | selftest trap (c); `grep` for `extern "C"`, `#[link`, `libc::`, `build.rs`, C files in the translations | Trap (c): blockers `safety finding: extern_c`, `safety finding: build_rs`; trap (b) on an unrestored crate: `new_dependency libc` | pending-run | M5 guard; M8 |
| Z4 | `src/safety_check.py` | selftest trap (d) | Trap (d): an unsafe block inside a safe `pub fn` is counted (unsafe metrics 2), `#![forbid(unsafe_code)]` makes the build fail, and the `-D unsafe_code` build fails | pending-run | M5 guard; M8 |
| Z5 | `src/integrity.py`, `configs/agent_system_prompt.md` | as Z1 | as Z1 (trap a) | pending-run | M5 guard; M8 |
| Z6 | `src/check_interface.py` | selftest trap (f) | Trap (f): `pub fn is_positive(x: impl Into<i64>)` compiles against the tests but gives blocker `interface missing 0, changed 1` | pending-run | M5 guard; M8 |
| Z7 | `src/integrity.py` (`--provenance`), `src/run_pipeline.py` (`tamper_check`), `configs/CHANGELOG.md` | `python3 -I MP4/src/integrity.py --provenance project_N` after each run; selftest trap (g) | Trap (g): a hand edit between iterations is recorded (`modified: [fixture.rs]`) and reverted; provenance follows the final run's `final_iteration_dir`, including `iter_KK_attemptN` (selftest) | pending-run | M6, M7, M8 |
| Z8 | `src/run_pipeline.py`, `trajectories/` | iteration count in `run_summary.json`; every `prompt.md` after `iter_01` carries feedback | Fixture drill A: the iteration-2 prompt carries the clippy and interface feedback of iteration 1 | pending-run | M6, M7, M8 |
| Z9 | `configs/`, `src/` | selftest checks that no Rust fn bodies and no `satc_`/`psbt_` identifiers are in the prompts or configs; `grep -niE 'satc_\|psbt_\|compactsize'` over `src/` and the prompts | selftest PASS; the grep hits only the selftest's own check | verified | M5 |
| Z10 | `src/scrub_secrets.py`, every trajectory writer | `python3 -I MP4/src/scrub_secrets.py --check MP4/`; `git grep -nE 'sk-ant-\|api_key='` | `scrub_secrets: 0 hit(s)` on the current tree; the per-iteration cargo logs are now scrubbed on write | pending-run | M6, M7, before the owner pushes |
| Z11 | `MP4/` layout | the course validation script | Script not released; directories created by M1 with the required names | owner-blocked | M13 |
| Z12 | `configs/`, `trajectories/` | the R-T2 rows | see R-T2 rows | pending-run | M6, M7, M11 |
| Z13 | `src/run_pipeline.py` (`evaluate`) | build is the first SUCCESS condition | Trap (d): `build fails` blocks success | pending-run | M6, M7 |
| Z14 | `configs/pipeline.yaml`, `src/agent_runner.py` | init isolation check on every call; provenance; CHANGELOG | M3 probe: reads outside the crate and the C directory denied; agent has no web or git tools | pending-run | M6, M7, M8 |
| Z15 | `src/mp4common.py`, `src/config.py` | `config.py` refuses any toolchain but `nightly-2025-05-13`; every cargo call is `cargo +nightly-2025-05-13` | Pipeline side checked; the translations are built in M6/M7 | pending-run | M6, M7 |
| Z16 | `translations/`, `README.md` | `--check-only` from a fresh clone | Fresh clone: `--check-only` on the fixture exits 0; on `project_1` it says there is no translation yet | pending-run | M6, M7, M11 |

## Status histogram

```
$ grep -oE '\| (verified|pending-run|proxy|owner-blocked) \| M' MP4/docs/rubric_traceability.md | awk '{print $2}' | sort | uniq -c
   7 owner-blocked
  22 pending-run
   2 proxy
   6 verified
```

## Evidence for the Task 1 and Task 2 rows (2026-10-29)

Commands run from the repository root on the M5 tree; output pasted as printed. `<selftest output>` is a saved
run of `python3 -I MP4/src/selftest.py`.

```
## R-T1-README
$ test -f MP4/README.md && echo present
present
[exit 0]

$ grep -c '^## ' MP4/README.md
12
[exit 0]

$ grep -nE '^## (Agentic framework and version|Model\(s\) and provider / runtime|Inference settings|OS and runtime|External tools available to the agent|Dependency installation|How to run the pipeline|Stopping condition|API and usage limits that affected the experiment|Models, frameworks and tools used|Repository layout|Infrastructure interventions)$' MP4/README.md
9:## Agentic framework and version
21:## Model(s) and provider / runtime
31:## Inference settings
46:## OS and runtime
57:## External tools available to the agent
76:## Dependency installation
100:## How to run the pipeline
126:## Stopping condition
139:## API and usage limits that affected the experiment
151:## Models, frameworks and tools used
163:## Repository layout
181:## Infrastructure interventions
[exit 0]

$ claude --version
2.1.235 (Claude Code)
[exit 0]

$ grep -n '2.1.235' MP4/README.md | head -3
11:[Claude Code](https://docs.anthropic.com/en/docs/claude-code) **2.1.235**, run headless with
55:| Agent | Claude Code 2.1.235 |
155:| Claude Code | 2.1.235 | Agent framework, headless |
[exit 0]

$ grep -nE '^  model:' MP4/configs/pipeline.yaml
10:  model: opus
[exit 0]

$ python3 -I MP4/src/summarize.py --check-readme
README generated sections: up to date
[exit 0]

$ ls MP4/src/run_pipeline.py
MP4/src/run_pipeline.py
[exit 0]

## R-T1-CONFIGS
$ ls MP4/configs/ MP4/configs/prompts MP4/configs/projects
MP4/configs/:
CHANGELOG.md
agent_system_prompt.md
cheatsheet_c_to_rust.md
claude_settings.json
pipeline.yaml
projects
prompts

MP4/configs/projects:
project_1.yaml
project_2.yaml

MP4/configs/prompts:
initial.md
repair.md
status_schema.json
[exit 0]

$ grep -rn 'configs/' MP4/src/*.py | grep -v selftest | head -5
MP4/src/agent_runner.py:3:why.md C1-C9, D1. The argv comes entirely from configs/pipeline.yaml. The
MP4/src/config.py:1:"""Load and validate MP4/configs/pipeline.yaml and configs/projects/*.yaml.
MP4/src/config.py:6:the handout's exactly. Paths resolve relative to MP4/configs/ (config files)
MP4/src/mp4common.py:25:# Fallback defaults. configs/pipeline.yaml (toolchain.*, checks.*) overrides them at import
MP4/src/mp4common.py:46:    """Return configs/pipeline.yaml as a dict, or {} when it does not exist yet."""
[exit 0]

$ git grep -nE 'sk-ant-|api_key=' -- MP4/
[exit 1]

## R-T1-TOOLLIST
$ sed -n '/^## Models, frameworks and tools used/,/^## Repository layout/p' MP4/README.md
## Models, frameworks and tools used

| Item | Version / identifier | Role |
|---|---|---|
| Claude Code | 2.1.235 | Agent framework, headless |
| Claude Opus (`opus` alias) | reported as `claude-opus-5` | The only model |
| Rust toolchain | nightly-2025-05-13 (rustc 1.89.0-nightly) | Build, test, used by the agent and the controller |
| Clippy | 0.1.88 | Idiomaticity feedback and scoring (correctness, style, complexity, perf) |
| Python + PyYAML | 3.9.12, 6.0 | Controller (`src/`) |
| Safety proxy | `src/safety_check.py` (`proxy-1`) | Interim unsafe metrics until the course tool is released |
| CRUST-bench | commit `4b47025`, `datasets/CRUST_bench.zip` | Source of the C projects, Rust interfaces and tests |

## Repository layout
[exit 0]

$ grep -oh '"name":"[A-Za-z]*"' MP4/trajectories/project_*/run_*/iter_*/agent.stream.jsonl 2>/dev/null | sort -u
[exit 0]

$ python3 -c "import json;d=json.load(open('docs/programs/mp4/evidence/smoke/probe/probe_report.json'));print(sorted(d['init']['tools']), sorted({t['name'] for t in d['tool_calls']}))"
['Bash', 'Edit', 'Glob', 'Grep', 'Read', 'StructuredOutput', 'Write'] ['Bash', 'Glob', 'Grep', 'Read', 'StructuredOutput', 'Write']
[exit 0]

## R-T2-SRC
$ grep -nE 'def (run_loop|_drive|do_checks|decide_stop|evaluate|build_prompt)|STOP_[A-Z_]+ = ' MP4/src/run_pipeline.py
385:STOP_SUCCESS = "SUCCESS"
386:STOP_MAX_ITERATIONS = "MAX_ITERATIONS"
387:STOP_NO_PROGRESS = "NO_PROGRESS"
388:STOP_ABORT = "ABORT"
389:STOP_ABORT_ISOLATION = "ABORT_ISOLATION"
390:STOP_AUTH_ERROR = "AUTH_ERROR"
421:def evaluate(check, proj):
700:def build_prompt(run, k):
720:def do_checks(run, k, n, agent_outcome):
769:def decide_stop(run, summary):
845:def run_loop(cfg, run_id=None, resume=False, yes=False, between_iterations=None):
955:def _drive(run, between_iterations):
[exit 0]

$ grep -nE '"\+" \+ TOOLCHAIN|TOOLCHAIN = ' MP4/src/mp4common.py
27:TOOLCHAIN = "nightly-2025-05-13"
122:    cmd = ["cargo", "+" + TOOLCHAIN] + list(args)
228:    TOOLCHAIN = tc.get("name", TOOLCHAIN)
[exit 0]

$ grep -n 'build_repair\|diagnostics' MP4/src/prompt_builder.py | head -6
171:def build_repair(cfg, iteration, check, history):
175:    vals["diagnostics"] = digest(check, cfg["pipeline"]["digest"])
[exit 0]

$ grep -n 'add_argument("--project"' MP4/src/run_pipeline.py
72:    ap.add_argument("--project", required=True, choices=mc.PROJECTS, help="which assigned project")
[exit 0]

$ grep -niE 'satc_|psbt_|compactsize' MP4/src/*.py MP4/configs/prompts/* MP4/configs/agent_system_prompt.md
MP4/src/selftest.py:309:    expect("templates/system prompt/cheatsheet: no satc_/psbt_ identifiers",
MP4/src/selftest.py:678:           ["satc_collision_test", "satc_point_scale_xy_test", "satc_point_test", "satc_polygon_get_centroid_test"])
MP4/src/selftest.py:848:    satc_iface = os.path.join(mc.skeleton_dir("project_1"), "src", "interfaces")
MP4/src/selftest.py:851:        fh.write(mc.read_text(os.path.join(satc_iface, "satc.rs"))[:1350])
MP4/src/selftest.py:852:    rep = check_interface.compare(satc_iface, cut)
[exit 0]

$ grep -E 'drill A|selftest:' <selftest output>
PASS  drill A: success at iteration 2                            actual=(0, 'SUCCESS', 2) expected=(0, 'SUCCESS', 2)
PASS  drill A: iter_01 has every design-reference file           actual=[] expected=[]
PASS  drill A: iter_02 has every design-reference file           actual=[] expected=[]
PASS  drill A: run files                                         actual=[] expected=[]
PASS  drill A: iteration 1 blockers (clippy + interface)         actual=['agent clippy warnings', 'interface missing 1, changed 0'] expected=['agent clippy warnings', 'interface missing 1, changed 0']
PASS  drill A: known-failing test verified (D8)                  actual={'assertion_matches': True, 'failed': True, 'location_matches': True} expected={'failed': True, 'assertion_matches': True, 'location_matches': True}
PASS  drill A: repair prompt carries iteration-1 feedback        actual=True expected=True
PASS  drill A: manifest records versions and config hash         actual=[] expected=[]
PASS  drill A: changes.diff shows the repair                     actual=True expected=True
PASS  summarize: results.md row from drill A                     actual=True expected=True
selftest: 166 PASS, 0 FAIL
[exit 0]

## R-T2-CONFIGS-PROMPTS
$ ls MP4/configs/prompts
initial.md
repair.md
status_schema.json
[exit 0]

$ grep -niE 'do not modify.*test|do not (alter|change).*test' MP4/configs/agent_system_prompt.md MP4/configs/prompts/*.md | head -5
MP4/configs/prompts/initial.md:19:- Do not modify, rename or delete the test files, `src/interfaces/`,
MP4/configs/prompts/repair.md:20:- Do not modify, rename or delete the test files, `src/interfaces/`,
[exit 0]

$ grep -c 'FFI' MP4/configs/agent_system_prompt.md MP4/configs/prompts/initial.md MP4/configs/prompts/repair.md
MP4/configs/agent_system_prompt.md:1
MP4/configs/prompts/initial.md:1
MP4/configs/prompts/repair.md:1
[exit 0]

$ grep -ciE 'unsafe' MP4/configs/agent_system_prompt.md MP4/configs/prompts/initial.md MP4/configs/prompts/repair.md
MP4/configs/agent_system_prompt.md:2
MP4/configs/prompts/initial.md:1
MP4/configs/prompts/repair.md:1
[exit 0]

$ grep -ciE 'hard.?cod' MP4/configs/agent_system_prompt.md MP4/configs/prompts/initial.md MP4/configs/prompts/repair.md
MP4/configs/agent_system_prompt.md:1
MP4/configs/prompts/initial.md:1
MP4/configs/prompts/repair.md:1
[exit 0]

$ grep -iE 'guardrail|fn bodies|identifiers' <selftest output>
PASS  project_1 initial: every guardrail phrase present          actual=[] expected=[]
PASS  project_1 repair: every guardrail phrase present           actual=[] expected=[]
PASS  project_2 initial: every guardrail phrase present          actual=[] expected=[]
PASS  project_2 repair: every guardrail phrase present           actual=[] expected=[]
PASS  templates/system prompt/cheatsheet: no satc_/psbt_ identifiers actual={} expected={}
[exit 0]

## R-T2-TRAJECTORIES
$ ls MP4/trajectories/project_1 MP4/trajectories/project_2
MP4/trajectories/project_1:
baseline

MP4/trajectories/project_2:
baseline
[exit 0]

$ grep -E 'drill A: (iter_0|run files)' <selftest output>
PASS  drill A: iter_01 has every design-reference file           actual=[] expected=[]
PASS  drill A: iter_02 has every design-reference file           actual=[] expected=[]
PASS  drill A: run files                                         actual=[] expected=[]
[exit 0]

$ python3 -I MP4/src/scrub_secrets.py --check MP4/
scrub_secrets: 0 hit(s)
[exit 0]

## R-T2-REPRO
$ sed -n '/^## How to run the pipeline/,/^## Stopping condition/p' MP4/README.md | grep -E '^python3'
python3 -I MP4/src/run_pipeline.py --project project_1 --dry-run     # print the agent command and first prompt (home paths as ~); no model call
python3 -I MP4/src/run_pipeline.py --project project_1               # full run; asks for confirmation (add --yes to skip)
python3 -I MP4/src/run_pipeline.py --project project_1 --resume-run <run_id>   # continue an interrupted or paused run
python3 -I MP4/src/run_pipeline.py --project project_1 --check-only
python3 -I MP4/src/summarize.py                      # results/results.md and LaTeX table fragments
python3 -I MP4/src/selftest.py                       # the controller's own test suite (no model calls)
[exit 0]
```
