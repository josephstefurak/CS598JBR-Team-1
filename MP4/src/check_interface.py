"""Interface conformance: pub items of src/interfaces/<mod>.rs vs src/<mod>.rs (why.md Z6, R-T3-*-COMPILE).

Regex-level item extraction (not a parser; compiling against the immutable
test file is the real conformance proof). Items: pub fn signatures (param
names dropped, paths reduced to their last segment, Self resolved), impl pub
fns as Type::name, structs with their pub fields and derives, enums with
variants and derives, pub const/static (name + type), pub type aliases, and
trait impls (`impl Trait for Type`).

missing  = in the interface, absent from the implementation
changed  = present in both, signature differs (or an interface derive is gone)
extra    = pub items only in the implementation (minor additions are allowed)

The interface is always read from MP4/subjects/<project>/rust_skeleton, the
implementation from the crate directory (default MP4/translations/<project>).
"""
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import mp4common as mc  # noqa: E402
import rustlex  # noqa: E402

_PUB_RE = re.compile(r"pub(?:\s*\([^)]*\))?\s+")


def norm(s):
    """Whitespace only where two word characters meet; paths reduced to their last segment."""
    s = re.sub(r"(?:\b[A-Za-z_]\w*\s*::\s*)+(?=[A-Za-z_<])", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"(?<=\W) | (?=\W)", "", s)
    return s


def split_top(s, sep=","):
    parts, depth, cur = [], 0, []
    i = 0
    while i < len(s):
        ch = s[i]
        if ch in "([{<":
            depth += 1
        elif ch in ")]}":
            depth -= 1
        elif ch == ">" and i > 0 and s[i - 1] != "-":
            depth -= 1
        if ch == sep and depth == 0:
            parts.append("".join(cur))
            cur = []
        else:
            cur.append(ch)
        i += 1
    if "".join(cur).strip():
        parts.append("".join(cur))
    return [p.strip() for p in parts if p.strip()]


def _drop_param_names(type_text):
    """`fn(elem: &mut X, ud: Y)` -> `fn(&mut X, Y)` inside type text."""
    return re.sub(r"(?<![:\w])(?:mut\s+)?[A-Za-z_]\w*\s*:(?!:)\s*", "", type_text)


def _balanced(code, open_idx, open_ch, close_ch):
    depth = 0
    for j in range(open_idx, len(code)):
        if code[j] == open_ch:
            depth += 1
        elif code[j] == close_ch:
            depth -= 1
            if depth == 0:
                return j
    return len(code) - 1


def _item_end(code, i):
    """End index (exclusive) of the item starting at i: through ';' or the matching '}' at depth 0."""
    depth = 0
    j = i
    while j < len(code):
        ch = code[j]
        if ch in "([":
            depth += 1
        elif ch in ")]":
            depth -= 1
        elif depth == 0 and ch == ";":
            return j + 1
        elif depth == 0 and ch == "{":
            close = rustlex.match_brace(code, j)
            return close + 1 if close >= 0 else len(code)   # unclosed (agent stopped mid-edit): rest of file
        j += 1
    return len(code)


def _sig_end(head):
    """Index of the first '{' or ';' outside () and [] (where a fn signature ends)."""
    depth = 0
    for k, ch in enumerate(head):
        if ch in "([":
            depth += 1
        elif ch in ")]":
            depth -= 1
        elif depth == 0 and ch in "{;":
            return k
    return len(head)


def _fn_sig(text, self_type=None):
    """Normalised signature from `fn name<...>(params) -> Ret where ...` (text up to the body)."""
    m = re.match(r"\s*(?:const\s+|async\s+|unsafe\s+|extern\s+\"[^\"]*\"\s+)*fn\s+([A-Za-z_]\w*)\s*", text)
    name = m.group(1)
    rest = text[m.end():]
    generics = ""
    if rest.startswith("<"):
        depth, k = 0, 0
        for k, ch in enumerate(rest):
            if ch == "<":
                depth += 1
            elif ch == ">" and rest[k - 1] != "-":
                depth -= 1
                if depth == 0:
                    break
        generics, rest = rest[:k + 1], rest[k + 1:]
    p_open = rest.find("(")
    p_close = _balanced(rest, p_open, "(", ")")
    params = []
    for p in split_top(rest[p_open + 1:p_close]):
        if re.match(r"^&?\s*('?\w+\s+)?(mut\s+)?self$", p.strip()) or p.strip() in ("self", "mut self"):
            params.append(norm(p.replace("mut self", "self") if not p.strip().startswith("&") else p))
            continue
        # the first top-level ':' (not part of '::') separates pattern from type
        ty = p
        depth = 0
        for k, ch in enumerate(p):
            if ch in "([<":
                depth += 1
            elif ch in ")]>":
                depth -= 1
            elif ch == ":" and depth == 0 and (k + 1 >= len(p) or p[k + 1] != ":") and (k == 0 or p[k - 1] != ":"):
                ty = p[k + 1:]
                break
        params.append(norm(_drop_param_names(ty)))
    tail = rest[p_close + 1:]
    ret = ""
    rm = re.match(r"\s*->\s*(.*?)\s*(?:\bwhere\b(.*))?$", tail, re.S)
    if rm:
        ret = norm(_drop_param_names(rm.group(1)))
    where = re.search(r"\bwhere\b(.*)$", tail, re.S)
    ret_part = ("->" + ret) if ret else ""
    where_part = (" where " + norm(where.group(1))) if where else ""
    sig = "fn %s%s(%s)%s%s" % (name, norm(generics), ",".join(params), ret_part, where_part)
    if self_type:
        sig = re.sub(r"\bSelf\b", self_type, sig)
    return name, sig


def _derives(attrs):
    out = set()
    for a in attrs:
        m = re.match(r"#\s*\[\s*derive\s*\((.*)\)\s*\]$", a, re.S)
        if m:
            out.update(norm(x) for x in split_top(m.group(1)))
    return out


def extract_items(text):
    """{key: {kind, sig, derives}} for pub items of one module file."""
    code = rustlex.strip(text)
    items = {}
    _scan_block(code, 0, len(code), items, None)
    return items


def _scan_block(code, start, end, items, self_type):
    i = start
    attrs = []
    while i < end:
        while i < end and code[i].isspace():
            i += 1
        if i >= end:
            break
        if code.startswith("#!", i) or code.startswith("#[", i):
            br = code.find("[", i)
            if br < 0:   # a stray `#!` with no attribute after it: nothing left to parse
                break
            close = _balanced(code, br, "[", "]")
            if code.startswith("#[", i):
                attrs.append(code[i:close + 1])
            i = close + 1
            continue
        pm = _PUB_RE.match(code, i)
        is_pub = bool(pm)
        j = pm.end() if pm else i
        item_end = _item_end(code, j)
        head = code[j:item_end]
        if self_type is None and re.match(r"(?:unsafe\s+)?impl\b", head):
            brace = code.find("{", j)
            if 0 <= brace < item_end:
                body_close = rustlex.match_brace(code, brace)
                if re.search(r"\bfor\b", code[j:brace]):
                    trait, ty = _impl_parts(code[j:brace])
                    key = "impl %s for %s" % (trait, ty)
                    items[key] = {"kind": "trait_impl", "sig": key, "derives": []}
                else:
                    ty = norm(re.sub(r"^\s*(?:unsafe\s+)?impl\s*(?:<[^{]*?>)?", "", code[j:brace]))
                    _scan_block(code, brace + 1, body_close, items, ty)
            attrs = []
            i = item_end
            continue
        if is_pub:
            km = re.match(r"(?:const\s+|async\s+|unsafe\s+|extern\s+\"[^\"]*\"\s+)*fn\b", head)
            if km:
                name, sig = _fn_sig(head[:_sig_end(head)], self_type)
                key = ("%s::%s" % (self_type, name)) if self_type else name
                items[key] = {"kind": "method" if self_type else "fn", "sig": sig, "derives": []}
            elif self_type is None:
                _top_item(head, attrs, items)
        attrs = []
        i = item_end


def _impl_parts(header):
    h = re.sub(r"^\s*(?:unsafe\s+)?impl\s*", "", header)
    if h.startswith("<"):
        h = h[_balanced(h, 0, "<", ">") + 1:]
    trait, ty = re.split(r"\bfor\b", h, 1)
    return norm(trait), norm(ty)


def _top_item(head, attrs, items):
    m = re.match(r"struct\s+([A-Za-z_]\w*)\s*(<[^{(;]*>)?", head)
    if m:
        name = m.group(1)
        rest = head[m.end():].strip()
        fields = []
        if rest.startswith("{"):
            for f in split_top(rest[1:rest.rfind("}")]):
                fm = _PUB_RE.match(f)
                if fm:
                    fields.append(norm(f[fm.end():]))
        elif rest.startswith("("):
            for f in split_top(rest[1:_balanced(rest, 0, "(", ")")]):
                fm = _PUB_RE.match(f)
                fields.append(norm(f[fm.end():]) if fm else "<private>")
        sig = "struct %s%s{%s}" % (name, norm(m.group(2) or ""), ",".join(sorted(fields)))
        items[name] = {"kind": "struct", "sig": sig, "derives": sorted(_derives(attrs))}
        return
    m = re.match(r"enum\s+([A-Za-z_]\w*)\s*(<[^{]*>)?\s*\{", head)
    if m:
        body = head[m.end():head.rfind("}")]
        variants = [norm(_drop_param_names(v)) if "{" in v else norm(v) for v in split_top(body)]
        sig = "enum %s%s{%s}" % (m.group(1), norm(m.group(2) or ""), ",".join(variants))
        items[m.group(1)] = {"kind": "enum", "sig": sig, "derives": sorted(_derives(attrs))}
        return
    m = re.match(r"(const|static)\s+(?:mut\s+)?([A-Za-z_]\w*)\s*:\s*([^=]*)", head)
    if m:
        items[m.group(2)] = {"kind": m.group(1), "sig": "%s %s:%s" % (m.group(1), m.group(2), norm(m.group(3))),
                             "derives": []}
        return
    m = re.match(r"type\s+([A-Za-z_]\w*)\s*(<[^=]*>)?\s*=\s*(.*?);?\s*$", head, re.S)
    if m:
        items[m.group(1)] = {"kind": "type", "sig": "type %s%s=%s" % (
            m.group(1), norm(m.group(2) or ""), norm(_drop_param_names(m.group(3)))), "derives": []}
        return
    m = re.match(r"(trait|mod|use|macro_rules|union)\b\s*([A-Za-z_]\w*)?", head)
    if m and m.group(1) in ("trait", "union") and m.group(2):
        items[m.group(2)] = {"kind": m.group(1), "sig": norm(head[:head.find("{")] if "{" in head else head),
                             "derives": []}


def module_file(crate, mod):
    for cand in (os.path.join(crate, "src", mod + ".rs"), os.path.join(crate, "src", mod, "mod.rs")):
        if os.path.exists(cand):
            return cand
    return None


def compare(interface_dir, crate):
    report = {"modules": {}, "interface_items": 0, "missing": 0, "changed": 0, "extra": 0}
    for fname in sorted(os.listdir(interface_dir)):
        if not fname.endswith(".rs"):
            continue
        mod = fname[:-3]
        want = extract_items(mc.read_text(os.path.join(interface_dir, fname)))
        impl_path = module_file(crate, mod)
        parse_error = None
        try:
            have = extract_items(mc.read_text(impl_path)) if impl_path else {}
        except (IndexError, AttributeError, ValueError) as exc:
            # a file this regex-level scan cannot read (e.g. cut off mid-edit) has no checkable items; the
            # build reports the real error, and the loop must go on rather than crash on every resume
            have, parse_error = {}, "%s: %s" % (type(exc).__name__, exc)
        missing = sorted(k for k in want if k not in have)
        changed = []
        for k in sorted(set(want) & set(have)):
            w, h = want[k], have[k]
            lost = sorted(set(w["derives"]) - set(h["derives"]))
            if w["sig"] != h["sig"] or lost:
                changed.append({"item": k, "expected": w["sig"], "actual": h["sig"],
                                "missing_derives": lost})
        extra = sorted(k for k in have if k not in want)
        report["modules"][mod] = {"file": mc.rel(impl_path, crate) if impl_path else None,
                                  "interface_items": len(want), "missing": missing, "changed": changed,
                                  "extra": extra, "parse_error": parse_error}
        report["interface_items"] += len(want)
        report["missing"] += len(missing)
        report["changed"] += len(changed)
        report["extra"] += len(extra)
    report["ok"] = report["missing"] == 0 and report["changed"] == 0
    return report


def main(argv=None):
    ap = argparse.ArgumentParser(description="Compare pub items of the required interface with the implementation.")
    ap.add_argument("--project")
    ap.add_argument("--interface-dir", help="default: subjects/<project>/rust_skeleton/src/interfaces")
    ap.add_argument("--crate-dir", help="default: MP4/translations/<project>")
    ap.add_argument("--json", action="store_true", help="print the full JSON report")
    a = ap.parse_args(argv)
    if not a.project and not (a.interface_dir and a.crate_dir):
        ap.error("give --project, or both --interface-dir and --crate-dir")
    if a.interface_dir:
        idir = os.path.abspath(a.interface_dir)
    else:
        idir = os.path.join(mc.skeleton_dir(a.project), "src", "interfaces")
    crate = os.path.abspath(a.crate_dir) if a.crate_dir else mc.translation_dir(a.project)
    rep = compare(idir, crate)
    if a.json:
        print(json.dumps(rep, indent=2))
    else:
        print("interface items: %d  missing: %d  changed: %d  extra: %d" % (
            rep["interface_items"], rep["missing"], rep["changed"], rep["extra"]))
        for mod, m in rep["modules"].items():
            print("  %-12s items %3d  missing %3d  changed %3d  extra %3d  (%s)" % (
                mod, m["interface_items"], len(m["missing"]), len(m["changed"]), len(m["extra"]),
                m["file"] or "no module file"))
    return 0 if rep["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
