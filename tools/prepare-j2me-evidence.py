#!/usr/bin/env python3
"""
Automated Phase-1 J2ME Evidence Generator for any standalone J2ME game project.
1. Verifies <project>/original/*.jar and extracts into analysis/recovered/ (if needed)
2. Runs `javap -c -p -v` on all .class files (validating non-empty output!)
3. Runs Vineflower and/or CFR if available locally (or passed via --vineflower / --cfr)
4. Generates analysis/CLASS-INDEX.md summarizing every class's size, key J2ME hooks,
   and all recovered binary/image/audio resources so AI Agents can port 1:1 immediately.

Usage:
  python3 tools/prepare-j2me-evidence.py <slug> [--vineflower path.jar] [--cfr path.jar]
"""
import argparse
import collections
import glob
import os
import pathlib
import re
import shutil
import subprocess
import sys
import zipfile

ROOT = pathlib.Path(__file__).resolve().parent.parent


def find_tool_bin(name: str) -> str:
    # 1. Check JAVA_HOME first
    java_home = os.environ.get("JAVA_HOME")
    if java_home:
        cand = pathlib.Path(java_home) / "bin" / name
        if cand.is_file() and os.access(cand, os.X_OK):
            return str(cand)
    # 2. Check local tools/tool-downloads bundled JDKs
    for pattern in (
        str(ROOT / "tools" / "tool-downloads" / "*" / "Contents" / "Home" / "bin" / name),
        str(ROOT / "tools" / "tool-downloads" / "*" / "bin" / name),
    ):
        matches = sorted(glob.glob(pattern))
        for m in matches:
            if os.path.isfile(m) and os.access(m, os.X_OK):
                return m
    # 3. Fallback to PATH
    found = shutil.which(name)
    return found or ""


def find_decompiler_jar(explicit: str, patterns: list[str]) -> str:
    if explicit and os.path.isfile(explicit):
        return explicit
    search_dirs = [
        ROOT / "tools",
        ROOT / "tools" / "tool-downloads",
        ROOT / "games" / "j2me-cpp-porter" / "skills" / "jar-to-cpp-port" / "scripts",
        pathlib.Path.home() / ".gemini" / "config" / "plugins" / "j2me-cpp-porter" / "skills" / "jar-to-cpp-port" / "scripts",
        pathlib.Path.home() / ".cache",
        pathlib.Path.home() / "Downloads",
    ]
    for base in search_dirs:
        if not base.exists():
            continue
        for pat in patterns:
            for m in sorted(base.glob(pat)):
                if m.is_file():
                    return str(m)
    return ""


def ensure_recovered(jar_path: pathlib.Path, recovered_dir: pathlib.Path) -> None:
    if recovered_dir.exists() and any(recovered_dir.rglob("*.class")):
        print(f"[SKIP] recovered/ already populated: {recovered_dir}")
        return
    recovered_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(jar_path, "r") as zf:
        zf.extractall(recovered_dir)
    print(f"[OK] Extracted {jar_path.name} -> {recovered_dir}")


def run_javap_all(javap_bin: str, recovered_dir: pathlib.Path, out_dir: pathlib.Path) -> tuple[int, int]:
    if not javap_bin:
        print("[WARN] `javap` not found on PATH or JAVA_HOME; skipping bytecode dump.")
        return 0, 0
    out_dir.mkdir(parents=True, exist_ok=True)
    class_files = sorted(recovered_dir.rglob("*.class"))
    ok_count = 0
    bad_count = 0
    for cf in class_files:
        rel = cf.relative_to(recovered_dir)
        cls_name = str(rel.with_suffix("")).replace(os.sep, ".")
        target = out_dir / rel.with_suffix(".javap.txt")
        target.parent.mkdir(parents=True, exist_ok=True)
        proc = subprocess.run(
            [javap_bin, "-c", "-p", "-v", "-cp", str(recovered_dir), cls_name],
            capture_output=True,
            text=True,
        )
        content = proc.stdout if proc.returncode == 0 else (proc.stdout + "\n" + proc.stderr)
        target.write_text(content, encoding="utf-8", errors="replace")
        if proc.returncode == 0 and len(content) > 100:
            ok_count += 1
        else:
            bad_count += 1
            print(f"[WARN] javap failed or empty for {cls_name} (rc={proc.returncode}, bytes={len(content)})")
    print(f"[OK] javap bytecode dumps: {ok_count} valid, {bad_count} failed -> {out_dir}")
    return ok_count, bad_count


def run_decompiler(java_bin: str, tool_name: str, tool_jar: str, jar_path: pathlib.Path, out_dir: pathlib.Path) -> bool:
    if not java_bin or not tool_jar:
        print(f"[SKIP] {tool_name} not available (pass --{tool_name.lower()} /path/to/{tool_name.lower()}.jar to enable).")
        return False
    out_dir.mkdir(parents=True, exist_ok=True)
    if tool_name == "Vineflower":
        cmd = [java_bin, "-jar", tool_jar, str(jar_path), str(out_dir)]
    else:
        cmd = [java_bin, "-jar", tool_jar, str(jar_path), "--outputdir", str(out_dir)]
    print(f"[RUN] {tool_name}: {' '.join(cmd)}")
    proc = subprocess.run(cmd, capture_output=True, text=True)
    java_count = len(list(out_dir.rglob("*.java")))
    if proc.returncode == 0 and java_count > 0:
        print(f"[OK] {tool_name} produced {java_count} .java files -> {out_dir}")
        return True
    print(f"[WARN] {tool_name} exited {proc.returncode} ({java_count} .java files): {(proc.stderr or proc.stdout)[:300]}")
    return False


HOOK_PATTERNS = [
    ("MIDlet", re.compile(r"extends\s+(?:javax\.microedition\.midlet\.)?MIDlet\b|startApp\s*\(")),
    ("Canvas/paint", re.compile(r"\bpaint\s*\(|extends\s+(?:.*Canvas|FullCn)")),
    ("GameLoop/run", re.compile(r"\bpublic\s+void\s+run\s*\(")),
    ("Input/keys", re.compile(r"\bkeyPressed\s*\(|\bpointerPressed\s*\(")),
    ("ResourceIO", re.compile(r"getResourceAsStream|DataInputStream")),
    ("DrawImage/Region", re.compile(r"\bdrawImage\s*\(|\bdrawRegion\s*\(|\bdrawPixels\s*\(")),
    ("Audio", re.compile(r"createPlayer|javax\.microedition\.media|com\.nokia\.mid\.sound")),
    ("Save/RMS", re.compile(r"RecordStore")),
]


def build_class_index(slug: str, jar_path: pathlib.Path, analysis_dir: pathlib.Path) -> pathlib.Path:
    recovered_dir = analysis_dir / "recovered"
    vf_dir = analysis_dir / "decompiled-vineflower"
    cfr_dir = analysis_dir / "decompiled-cfr"
    jp_dir = analysis_dir / "bytecode-evidence"

    class_rows = []
    for cf in sorted(recovered_dir.rglob("*.class")):
        rel = cf.relative_to(recovered_dir)
        cls_name = str(rel.with_suffix("")).replace(os.sep, ".")
        cls_bytes = cf.stat().st_size

        src_file = vf_dir / rel.with_suffix(".java")
        if not src_file.exists():
            src_file = cfr_dir / rel.with_suffix(".java")
        if not src_file.exists():
            src_file = jp_dir / rel.with_suffix(".javap.txt")

        lines = 0
        hooks = []
        if src_file.exists():
            txt = src_file.read_text(encoding="utf-8", errors="replace")
            lines = txt.count("\n") + 1
            for label, rx in HOOK_PATTERNS:
                if rx.search(txt):
                    hooks.append(label)
        class_rows.append((cls_bytes, cls_name, lines, ", ".join(hooks) if hooks else "-"))

    class_rows.sort(key=lambda r: r[0], reverse=True)

    # Summarize non-class resources
    res_groups = collections.Counter()
    res_samples = collections.defaultdict(list)
    for f in sorted(recovered_dir.rglob("*")):
        if not f.is_file() or f.suffix == ".class":
            continue
        rel_str = str(f.relative_to(recovered_dir))
        if rel_str.startswith("META-INF/"):
            continue
        ext = f.suffix.lower() if f.suffix else "(no-ext)"
        if re.match(r"^\.\d+$", ext):
            ext = "(split-chunk .N)"
        res_groups[ext] += 1
        if len(res_samples[ext]) < 6:
            res_samples[ext].append(f"{rel_str} ({f.stat().st_size}B)")

    out_md = analysis_dir / "CLASS-INDEX.md"
    md = [
        f"# Class & Resource Index — `{slug}`",
        "",
        f"- **Original JAR**: `original/{jar_path.name}` ({jar_path.stat().st_size:,} bytes)",
        f"- **Classes**: {len(class_rows)} | **Decompilers present**: "
        f"Vineflower={'YES' if vf_dir.exists() and any(vf_dir.rglob('*.java')) else 'NO'}, "
        f"CFR={'YES' if cfr_dir.exists() and any(cfr_dir.rglob('*.java')) else 'NO'}, "
        f"javap={'YES' if jp_dir.exists() and any(jp_dir.rglob('*.javap.txt')) else 'NO'}",
        "",
        "## 1. Classes (sorted by `.class` size — start porting from the top!)",
        "",
        "| Class | `.class` Size | Lines | Detected J2ME Hooks |",
        "|---|---:|---:|---|",
    ]
    for sz, cls_name, lines, hooks in class_rows:
        md.append(f"| `{cls_name}` | {sz:,} B | {lines:,} | {hooks} |")

    md.extend([
        "",
        "## 2. Recovered Non-Class Resources",
        "",
        "| Type | Count | Sample Files |",
        "|---|---:|---|",
    ])
    for ext, cnt in res_groups.most_common():
        md.append(f"| `{ext}` | {cnt} | {', '.join(res_samples[ext])} |")

    md.extend([
        "",
        "## 3. Next Step",
        "1. Read `docs/J2ME_DECOMPILE_FIDELITY_GUIDE.md` & `docs/PROMPT_TEMPLATE_NEW_GAME.md`.",
        "2. Write `CLASS-RESPONSIBILITIES.md` from the top classes above before coding `web-port/`.",
        "",
    ])
    out_md.write_text("\n".join(md), encoding="utf-8")
    print(f"[OK] Generated {out_md}")
    return out_md


def resolve_game_dir(target: str) -> pathlib.Path:
    cand = pathlib.Path(target).expanduser()
    if cand.is_dir() and (cand / "original").is_dir():
        return cand.resolve()
    for base in (ROOT / "games" / target, ROOT / "games" / f"{target}-clone"):
        if (base / "original").is_dir():
            return base.resolve()
    return (ROOT / "games" / target).resolve()


def main():
    parser = argparse.ArgumentParser(description="Prepare full J2ME reverse-engineering evidence for a game project.")
    parser.add_argument("target", help="Game slug under games/ or project path (e.g. total-tournament)")
    parser.add_argument("--vineflower", default="", help="Optional path to vineflower.jar")
    parser.add_argument("--cfr", default="", help="Optional path to cfr.jar")
    args = parser.parse_args()

    game_dir = resolve_game_dir(args.target)
    orig_dir = game_dir / "original"
    analysis_dir = game_dir / "analysis"
    jars = sorted(orig_dir.glob("*.jar"))
    if not jars:
        print(f"[ERROR] No .jar found in {orig_dir}", file=sys.stderr)
        sys.exit(1)
    jar_path = jars[0]

    java_bin = find_tool_bin("java")
    javap_bin = find_tool_bin("javap")
    vf_jar = find_decompiler_jar(args.vineflower, ["*vineflower*.jar", "*fernflower*.jar"])
    cfr_jar = find_decompiler_jar(args.cfr, ["*cfr*.jar"])

    print(f"[INFO] Project: {game_dir} | JAR: {jar_path.name}")
    print(f"[INFO] java={java_bin or 'MISSING'} | javap={javap_bin or 'MISSING'}")
    print(f"[INFO] vineflower={vf_jar or 'not found'} | cfr={cfr_jar or 'not found'}")

    ensure_recovered(jar_path, analysis_dir / "recovered")
    run_javap_all(javap_bin, analysis_dir / "recovered", analysis_dir / "bytecode-evidence")
    run_decompiler(java_bin, "Vineflower", vf_jar, jar_path, analysis_dir / "decompiled-vineflower")
    run_decompiler(java_bin, "CFR", cfr_jar, jar_path, analysis_dir / "decompiled-cfr")
    build_class_index(game_dir.name, jar_path, analysis_dir)
    print(f"[DONE] Evidence ready for {analysis_dir}")


if __name__ == "__main__":
    main()
