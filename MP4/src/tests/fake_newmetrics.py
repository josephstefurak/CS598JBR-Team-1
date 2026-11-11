"""Stand-in for `cargo newmetrics` in the self-test: replays a recorded run of the real tool.

It prints tests/newmetrics_fixture_raw.txt (real output of newmetrics 0.1.0 on selftest_fixture) and leaves the
same files in the working directory that the real analyzer leaves (unsafe_spans.txt, derefs.txt, decls.txt, a
target/ directory), so the adapter's copy-and-clean-up behaviour is tested without the tool being installed.
With `--fail` it prints the tool's failure line and exits 1, as the real driver does when `cargo check` fails.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def main(argv):
    if "--fail" in argv:
        print("Running cargo newmetrics\nFinished with non-zero exit code")
        return 1
    with open(os.path.join(HERE, "newmetrics_fixture_raw.txt"), encoding="utf-8") as fh:
        sys.stdout.write(fh.read().replace("<crate>", os.getcwd()))
    for name in ("unsafe_spans.txt", "derefs.txt", "decls.txt"):
        with open(name, "w", encoding="utf-8"):
            pass
    os.makedirs("target", exist_ok=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
