"""Find or remove secrets, e-mail addresses and home paths in MP4 files (why.md Z10, R-T2-TRAJECTORIES).

  scrub_secrets.py --check PATH...   exit 1 and list file:line:kind for every hit
  scrub_secrets.py --fix PATH...     rewrite hits in place, then re-check

Kinds: anthropic_key (incl. OAuth token shapes), github_token, bearer,
api_key_assignment, token_field (JSON access/refresh tokens), email,
home_path (/Users/<name>, /home/<name> -> ~).

MP4/subjects/ is skipped: it is the immutable upstream benchmark (author
e-mails in its licence files are not ours to rewrite). Binary files and PDFs
are skipped. The patterns are assembled from pieces so this file does not
match its own scan or the repository's `git grep` secret check.
"""
import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import mp4common as mc  # noqa: E402

_SK = "sk" + "-ant-"
_BEARER = "Bear" + "er"
_APIKEY = "api" + "_key"
EMAIL_ALLOW = {"noreply@anthropic.com"}
EMAIL_ALLOW_DOMAINS = ("example.com", "example.org")

PATTERNS = [
    ("anthropic_key", re.compile(re.escape(_SK) + r"[A-Za-z0-9_\-]{8,}")),
    ("github_token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b")),
    ("bearer", re.compile(_BEARER + r"\s+[A-Za-z0-9._~+/=\-]{12,}")),
    ("api_key_assignment", re.compile(r"(?i)\b" + _APIKEY + r"\b\s*[=:]\s*[\"']?[A-Za-z0-9._\-]{8,}")),
    ("token_field", re.compile(r"\"(?:access|refresh|oauth|id)_?[Tt]oken\"\s*:\s*\"[^\"]{8,}\"")),
    ("email", re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b")),
    ("home_path", re.compile(r"/(?:Users|home)/[A-Za-z0-9._\-]+")),
]
SKIP_REL_PREFIXES = ("MP4/subjects/",)
SKIP_EXT = (".pdf", ".png", ".jpg", ".jpeg", ".gif", ".zip", ".gz", ".pyc")


def _allowed(kind, text):
    if kind == "email":
        low = text.lower()
        return low in EMAIL_ALLOW or low.endswith(EMAIL_ALLOW_DOMAINS)
    return False


def _replacement(kind):
    return "~" if kind == "home_path" else "[REDACTED:%s]" % kind


def _is_binary(path):
    with open(path, "rb") as fh:
        return b"\0" in fh.read(8192)


def iter_files(paths):
    for p in paths:
        p = os.path.abspath(p)
        files = [p] if os.path.isfile(p) else list(mc.walk_files(p))
        for f in files:
            r = mc.rel(f, mc.REPO_DIR)
            if r.startswith(SKIP_REL_PREFIXES) or f.endswith(SKIP_EXT) or _is_binary(f):
                continue
            yield f


def scan_text(text):
    """[(line_no, kind, matched_text)] for every hit in text."""
    hits = []
    for kind, rx in PATTERNS:
        for m in rx.finditer(text):
            if not _allowed(kind, m.group(0)):
                hits.append((text.count("\n", 0, m.start()) + 1, kind, m.group(0)))
    return sorted(hits)


def scrub_text(text):
    for kind, rx in PATTERNS:
        text = rx.sub(lambda m, k=kind: m.group(0) if _allowed(k, m.group(0)) else _replacement(k), text)
    return text


def check(paths):
    out = []
    for f in iter_files(paths):
        for line, kind, _ in scan_text(mc.read_text(f)):
            out.append({"file": mc.rel(f, mc.REPO_DIR), "line": line, "kind": kind})
    return out


def fix(paths):
    changed = []
    for f in iter_files(paths):
        text = mc.read_text(f)
        new = scrub_text(text)
        if new != text:
            with open(f, "w", encoding="utf-8") as fh:
                fh.write(new)
            changed.append(mc.rel(f, mc.REPO_DIR))
    return changed


def main(argv=None):
    ap = argparse.ArgumentParser(description="Check or scrub secrets, e-mails and home paths.")
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--fix", action="store_true")
    ap.add_argument("paths", nargs="+")
    a = ap.parse_args(argv)
    if a.fix:
        for f in fix(a.paths):
            print("scrubbed %s" % f)
    hits = check(a.paths)
    for h in hits:
        # never echo the matched text: it may be the secret itself
        print("%s:%d: %s" % (h["file"], h["line"], h["kind"]))
    print("scrub_secrets: %d hit(s)" % len(hits))
    return 1 if hits else 0


if __name__ == "__main__":
    sys.exit(main())
