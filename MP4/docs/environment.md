# MP4 environment

Recorded on 2026-10-28 from the machine that runs the pipeline. Every value
here is pasted command output.

## Rust toolchain (pinned: `nightly-2025-05-13`)

| Command | Output |
|---|---|
| `rustup --version` | `rustup 1.29.2 (d8c92c676 2026-10-21)` |
| `cargo +nightly-2025-05-13 --version` | `cargo 1.89.0-nightly (056f5f4f3 2025-05-09)` |
| `rustc +nightly-2025-05-13 --version` | `rustc 1.89.0-nightly (8405332bd 2025-05-12)` |
| `cargo +nightly-2025-05-13 clippy --version` | `clippy 0.1.88 (8405332bdf 2025-05-12)` |

Host target: `aarch64-apple-darwin`. Toolchain profile: `minimal` plus the
`clippy` component.

### Install steps (as run)

```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs -o rustup-init.sh
sh rustup-init.sh -y --no-modify-path --profile minimal --default-toolchain none
~/.cargo/bin/rustup toolchain install nightly-2025-05-13 --profile minimal --component clippy
```

Because rustup had no default toolchain, it made `nightly-2025-05-13` the
default. The pipeline does not rely on that default: it always calls
`cargo +nightly-2025-05-13`.

### PATH requirement

The installer ran with `--no-modify-path`, so `~/.cargo/bin` is **not** added
to any shell profile. Everything that runs `cargo` needs it on `PATH`,
including the headless `claude -p` agent processes the pipeline spawns:

```bash
export PATH="$HOME/.cargo/bin:$PATH"
```

## Host

| Command | Output |
|---|---|
| `sw_vers` | `ProductName: macOS`, `ProductVersion: 26.5.2`, `BuildVersion: 25F84` |
| `uname -m` | `arm64` |
| `python3 --version` | `Python 3.9.12` |
| `claude --version` | `2.1.235 (Claude Code)` |

## Benchmark source

CRUST-bench `datasets/CRUST_bench.zip` at commit
`4b4702544b800a3821feea128c5b9e413665dc83`, sha256
`a9c3024fd5c7386e790938c6a2ec2c75c4d4582174289cb037881e04e9adc15e`. See
`MP4/subjects/project_N/SOURCE.md`.

## Course unsafe-metrics tool (`newmetrics`)

Installed on 2026-11-11. The tool is not part of this repository.

| Item | Value |
|---|---|
| Source | `https://github.com/Intelligent-CAT-Lab/CS598JBR-Team-0`, `MP4/newmetrics/` |
| Commit | `4597e75700f1d9d13205352dcc9f2b43459be099` (2026-11-09; `main` on the install date) |
| Clone location | `~/cs598jbr-course-tools/CS598JBR-Team-0` (outside this repository) |
| Package | `newmetrics v0.1.0` |
| Binaries | `~/.cargo/bin/cargo-newmetrics`, `~/.cargo/bin/newmetrics` |
| Aggregator | `MP4/newmetrics/aggregate.py` in the clone (run with `python3 -I`) |
| Toolchain components added | `rustc-dev`, `llvm-tools-preview` on `nightly-2025-05-13` (reported by rustup as `rustc-dev-aarch64-apple-darwin`, `llvm-tools-aarch64-apple-darwin`) |

### Install steps (as run)

```bash
git clone https://github.com/Intelligent-CAT-Lab/CS598JBR-Team-0 ~/cs598jbr-course-tools/CS598JBR-Team-0
git -C ~/cs598jbr-course-tools/CS598JBR-Team-0 checkout 4597e75
rustup component add rustc-dev llvm-tools-preview --toolchain nightly-2025-05-13
cd ~/cs598jbr-course-tools/CS598JBR-Team-0/MP4/newmetrics && cargo install --debug --locked --path . --force
```

The course repository ships no `Cargo.lock`. `cargo install --locked` accepted that and resolved the
dependencies at install time (exit 0, `Finished dev profile`), and wrote no lock file. The versions it
built, read from the build's dependency files:

`cargo_metadata 0.11.4`, `itoa 1.0.19`, `libc 0.2.191`, `memchr 2.8.3`, `proc-macro2 1.0.107`,
`quote 1.0.47`, `rustc_version 0.2.3`, `semver 0.10.0`, `semver 0.9.0`, `semver-parser 0.7.0`,
`serde 1.0.229`, `serde_core 1.0.229`, `serde_derive 1.0.229`, `serde_json 1.0.154`, `syn 2.0.119`,
`syn 3.0.10`, `thiserror 1.0.69`, `thiserror-impl 1.0.69`, `unicode-ident 1.0.27`, `wait-timeout 0.2.1`,
`which 4.0.2`, `zmij 1.0.23`.

A later install can resolve newer versions, because nothing pins them.

To remove it: `cargo uninstall newmetrics`, then
`rustup component remove rustc-dev llvm-tools-preview --toolchain nightly-2025-05-13`, and delete the clone.
