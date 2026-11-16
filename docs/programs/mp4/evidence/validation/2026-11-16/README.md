# Course validation script run — 2026-11-16 (M13)

| | |
|---|---|
| Script | `MP4/validate.py` in `https://github.com/Intelligent-CAT-Lab/CS598JBR-Team-0`, commit `5f9213a` (2026-11-14, "MP4 validate script added.") |
| Script sha256 | `36e76f12fe0d8027351e91a9f2ca42b13122e5133fc6d942e7b3451d57e0c305` |
| Read from | `git show origin/main:MP4/validate.py` in the course clone at `~/cs598jbr-course-tools/CS598JBR-Team-0`. The clone's checkout stays at `4597e75`, the commit the unsafe-metrics tool was built from. The script is not vendored |
| Command | `python -I validate.py <origin URL of this repository> mp4-program`, from an empty directory |
| What it validated | its own fresh clone of the remote, branch `mp4-program`, HEAD `a737093efa8d08c55b24a50fd912c6861df549ce` |
| Python | 3.9.12, throwaway virtual environment outside the repository |
| Packages | GitPython 3.2.1, colorama 0.4.6 (gitdb 4.0.12, smmap 5.0.3) |
| Exit code | **0** |
| Result | `MP4 STRUCTURE VALIDATION PASSED!` — 20 checks passed, 0 errors, 0 warnings |

`validate_output.txt` is the complete stdout and stderr with the ANSI colour
codes removed and nothing else changed.

The script checks structure only. Its header: it "does not run Rust
compilation, tests, Clippy, or safety analysis" and "Passing validation does
not guarantee full credit."

**After the merge (same day):** the same script, environment and command with
branch `main`, on its own fresh clone of `main` at the merge commit `ca12d2a`:
exit 0, `MP4 STRUCTURE VALIDATION PASSED!`, 20 checks passed, 0 errors, 0
warnings. Output: `validate_output_main.txt`.

## Classification of reported issues

| Issue reported | Class | Action |
|---|---|---|
| none | — | none |
