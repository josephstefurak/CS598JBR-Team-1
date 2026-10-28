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
