# project_2 — `libpsbt` (CRUST-bench)

**Assignment.** The MP4 handout's project table assigns Group 1 `satc`
(Project 1) and `libpsbt` (Project 2). This directory holds Project 2.

**Origin.**

| Field | Value |
|---|---|
| Repository | https://github.com/anirudhkhatry/CRUST-bench |
| Commit | `4b4702544b800a3821feea128c5b9e413665dc83` (`main` on 2026-10-28, committed 2026-04-27) |
| Archive | `datasets/CRUST_bench.zip` |
| Archive URL | https://github.com/anirudhkhatry/CRUST-bench/raw/4b4702544b800a3821feea128c5b9e413665dc83/datasets/CRUST_bench.zip |
| Archive size | 45365259 bytes |
| Archive sha256 | `a9c3024fd5c7386e790938c6a2ec2c75c4d4582174289cb037881e04e9adc15e` |
| Fetched | 2026-10-28 |

**Mapping.**

| Archive path | Here |
|---|---|
| `CBench/libpsbt/` | `c/` (original C project) |
| `RBench/libpsbt/` | `rust_skeleton/` (CRUST-bench Rust interface, tests, `Cargo.toml`, `Cargo.lock`) |

**Stripped on import.** Nothing else was changed: only embedded `.git/`
directories and macOS `.DS_Store` files were removed. Every remaining file
is byte-identical to the archive (`CHECKSUMS.sha256` lists all of them).
Removed:

- `CBench/libpsbt/.git/`
- `RBench/libpsbt/.DS_Store`
- `RBench/libpsbt/src/.DS_Store`
