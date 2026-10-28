Continue the MP4 C-to-Rust agentic translation program — one phase only.

Run the `program-builder` skill in `next` mode for program `mp4`. Its
manifest is `docs/programs/mp4/program.yaml`; everything else — the docs,
the branch, the gates, the verification floor — comes from there.

Implement exactly one phase. When the ledger runs out of rows, do not stop —
the program closes itself in at most three capped review passes, per the state
machine. Do not open a PR. Never push. Never edit anything under
`MP4/translations/`. Spend only within the pre-authorized envelope in the
manifest's `spend_surface`.
