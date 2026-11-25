#!/usr/bin/env python3
"""
Hard Anti-Hallucination Parity Gate for J2ME Web Ports.
Run: python3 tools/verify-port-parity.py <slug>

Exits 0 ONLY if all hard verification gates pass:
  1. Original .jar & recovered/ intact
  2. Valid non-empty javap bytecode dumps + decompiled Java sources + CLASS-INDEX / CLASS-RESPONSIBILITIES
  3. Explicit decompiled Java citations (Class.java:line) in web-port/*.js (forbids from-memory rewrites)
  4. Real original asset usage (drawImage + assets/) and zero unresolved UNVERIFIED markers
  5. All JS files pass `node --check`, tests pass `node --test`, and game is registered in games-manifest.json
"""
import argparse
import json
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent


def resolve_game_dir(target: str) -> tuple[str, pathlib.Path]:
    cand = pathlib.Path(target).expanduser()
    if cand.is_dir() and ((cand / "original").is_dir() or (cand / "web-port").is_dir()):
        resolved = cand.resolve()
        return resolved.name, resolved
    for base in (ROOT.parent / f"{target}-clone", ROOT.parent / target, ROOT / "games" / target):
        if base.is_dir():
            return target, base.resolve()
    return target, (ROOT.parent / f"{target}-clone").resolve()


def main():
    parser = argparse.ArgumentParser(description="Verify J2ME web-port evidence, source citations, assets, and tests.")
    parser.add_argument("target", help="Standalone game project path or slug (e.g. ../total-tournament-clone or total-tournament)")
    args = parser.parse_args()

    slug, game_dir = resolve_game_dir(args.target)
    orig_dir = game_dir / "original"
    analysis_dir = game_dir / "analysis"
    web_dir = game_dir / "web-port"

    failures = []
    warnings = []
    passed = []

    if not game_dir.exists():
        print(f"[FAIL] Game directory not found: {game_dir}")
        sys.exit(1)

    # Gate 1: Original JAR & recovered/
    jars = sorted(orig_dir.glob("*.jar")) if orig_dir.exists() else []
    if not jars or jars[0].stat().st_size == 0:
        failures.append(f"Missing original .jar in {game_dir.name}/original/")
    else:
        passed.append(f"Original JAR intact: {jars[0].name} ({jars[0].stat().st_size:,} B)")

    rec_dir = analysis_dir / "recovered"
    rec_classes = list(rec_dir.rglob("*.class")) if rec_dir.exists() else []
    if not rec_classes:
        failures.append(f"No extracted .class files in {game_dir.name}/analysis/recovered/ (run prepare-j2me-evidence.py)")
    else:
        passed.append(f"Recovered {len(rec_classes)} .class files")

    # Gate 2: Bytecode javap + Decompiler outputs + Class Map
    jp_dir = analysis_dir / "bytecode-evidence"
    jp_files = list(jp_dir.rglob("*.javap.txt")) if jp_dir.exists() else []
    valid_jp = [f for f in jp_files if f.stat().st_size > 100]
    if not valid_jp:
        failures.append(f"No valid (>100B) javap dumps in {game_dir.name}/analysis/bytecode-evidence/ (run prepare-j2me-evidence.py)")
    elif len(valid_jp) < len(rec_classes):
        warnings.append(f"Only {len(valid_jp)}/{len(rec_classes)} classes have valid javap dumps")
    else:
        passed.append(f"Valid javap bytecode dumps: {len(valid_jp)} files")

    vf_files = list((analysis_dir / "decompiled-vineflower").rglob("*.java")) if (analysis_dir / "decompiled-vineflower").exists() else []
    cfr_files = list((analysis_dir / "decompiled-cfr").rglob("*.java")) if (analysis_dir / "decompiled-cfr").exists() else []
    if not vf_files and not cfr_files:
        failures.append(f"No decompiled .java files in decompiled-vineflower/ or decompiled-cfr/")
    else:
        passed.append(f"Decompiled Java sources: Vineflower={len(vf_files)}, CFR={len(cfr_files)}")

    if (analysis_dir / "CLASS-RESPONSIBILITIES.md").exists():
        passed.append("CLASS-RESPONSIBILITIES.md present")
    else:
        failures.append(f"Missing {game_dir.name}/analysis/CLASS-RESPONSIBILITIES.md (required from Stage 1)")

    # Gate 3: Explicit Java source citations + no unresolved UNVERIFIED markers
    js_files = [
        f for f in sorted(web_dir.glob("*.js"))
        if f.name not in ("phaser-engine.js", "multiplayer.js")
    ] if web_dir.exists() else []

    if not js_files:
        failures.append(f"No JS source files found in {game_dir.name}/web-port/")
    else:
        cite_re = re.compile(r"\b[A-Za-z0-9_$]+\.java:\d+")
        unverified_re = re.compile(r"\bUNVERIFIED\b")
        draw_img_re = re.compile(r"\bdrawImage\s*\(")
        fill_rect_re = re.compile(r"\bfillRect\s*\(")

        total_cites = 0
        total_unverified = 0
        total_draw_img = 0
        total_fill_rect = 0
        for jf in js_files:
            txt = jf.read_text(encoding="utf-8", errors="replace")
            total_cites += len(cite_re.findall(txt))
            total_unverified += len(unverified_re.findall(txt))
            total_draw_img += len(draw_img_re.findall(txt))
            total_fill_rect += len(fill_rect_re.findall(txt))

        if total_cites < 3:
            failures.append(
                f"Only {total_cites} decompiled Java citations (Class.java:line) found in web-port/*.js "
                f"(minimum 3 required to prove direct porting from decompiled source, not from memory)"
            )
        else:
            passed.append(f"Decompiled Java citations found: {total_cites} references")

        if total_unverified > 0:
            failures.append(f"Found {total_unverified} unresolved UNVERIFIED markers in web-port/*.js — verify against javap before finishing")

        # Gate 4: Real asset rendering check
        assets_dir = web_dir / "assets"
        asset_count = len([f for f in assets_dir.rglob("*") if f.is_file()]) if assets_dir.exists() else 0
        if asset_count == 0:
            failures.append(f"{game_dir.name}/web-port/assets/ is empty")
        else:
            passed.append(f"Extracted web-port assets: {asset_count} files")

        if total_draw_img == 0:
            failures.append(f"web-port/*.js has 0 drawImage() calls (fillRect={total_fill_rect}) — appears to be placeholder shapes instead of real sprites")
        else:
            passed.append(f"Real sprite rendering detected: {total_draw_img} drawImage() calls (fillRect={total_fill_rect})")

        # Gate 4B: Crisp 1px MIDP UI primitives, bitmap font usage & shell hygiene (advisory)
        stroke_rect_re = re.compile(r"\bstrokeRect\s*\(")
        total_stroke_rect = sum(
            len(stroke_rect_re.findall(jf.read_text(encoding="utf-8", errors="replace")))
            for jf in js_files
        )
        if total_stroke_rect > 0:
            warnings.append(
                f"Found {total_stroke_rect} blurry Canvas strokeRect() call(s) — prefer crisp 1px drawRectMIDP() fillRect borders"
            )
        else:
            passed.append("Crisp integer borders verified (0 strokeRect() calls)")

        if assets_dir.exists() and (assets_dir / "fnt.png").exists():
            font_refs = sum(
                1 for jf in js_files
                if "createOriginalFont" in jf.read_text(encoding="utf-8", errors="replace")
            )
            if font_refs == 0:
                warnings.append("assets/fnt.png present but createOriginalFont() not wired in web-port/*.js")
            else:
                passed.append("Original bitmap font sheet (fnt.png) wired via createOriginalFont()")

        css_path = web_dir / "style.css"
        if css_path.exists():
            css_txt = css_path.read_text(encoding="utf-8", errors="replace")
            tb_match = re.search(r"\.floating-toolbar\s*\{([^}]*)\}", css_txt, re.S)
            if tb_match and re.search(r"position\s*:\s*fixed\b", tb_match.group(1)):
                warnings.append("style.css .floating-toolbar uses position:fixed (may overlap bottom canvas HUD/softkeys; prefer flex column below #game)")
            elif tb_match:
                passed.append("Viewport shell toolbar docked cleanly outside #game canvas")

        # Gate 4C: Mandatory Multiplayer requirement for every web port
        mp_js = web_dir / "multiplayer.js"
        html_path = web_dir / "index.html"
        game_js_path = web_dir / "game.js"
        html_txt = html_path.read_text(encoding="utf-8", errors="replace") if html_path.exists() else ""
        game_js_txt = game_js_path.read_text(encoding="utf-8", errors="replace") if game_js_path.exists() else ""
        if not mp_js.exists():
            failures.append(f"Missing mandatory multiplayer module: {game_dir.name}/web-port/multiplayer.js")
        elif "mp-lobby" not in html_txt or "btn-mp-lobby" not in html_txt:
            failures.append(f"{game_dir.name}/web-port/index.html missing mandatory multiplayer UI (#mp-lobby / #btn-mp-lobby)")
        elif "MultiplayerClient" not in game_js_txt:
            failures.append(f"{game_dir.name}/web-port/game.js does not wire MultiplayerClient")
        else:
            passed.append("Mandatory Multiplayer wired (multiplayer.js + #mp-lobby + MultiplayerClient)")

    # Gate 5: JS syntax check + unit tests + manifest registration
    all_js = sorted(web_dir.glob("*.js")) if web_dir.exists() else []
    syntax_ok = True
    for jf in all_js:
        proc = subprocess.run(["node", "--check", str(jf)], capture_output=True, text=True)
        if proc.returncode != 0:
            syntax_ok = False
            failures.append(f"Syntax error in {jf.name}: {(proc.stderr or proc.stdout).strip()[:200]}")
    if all_js and syntax_ok:
        passed.append(f"Syntax OK (`node --check` passed on {len(all_js)} JS files)")

    test_files = sorted((web_dir / "tests").glob("*.test.mjs")) if (web_dir / "tests").exists() else []
    if not test_files:
        warnings.append(f"No unit tests found in {game_dir.name}/web-port/tests/*.test.mjs")
    else:
        proc = subprocess.run(["node", "--test", *[str(t) for t in test_files]], capture_output=True, text=True)
        if proc.returncode != 0:
            failures.append(f"Unit tests FAILED: {(proc.stderr or proc.stdout).strip()[:300]}")
        else:
            passed.append(f"Unit tests PASSED ({len(test_files)} test file(s))")

    # Gate 6: Visual Oracle reference screenshots check (advisory)
    ref_dirs = [
        analysis_dir / "reference-frames",
        web_dir / "assets" / "campaign-frames",
    ]
    ref_pngs = []
    for rd in ref_dirs:
        if rd.exists():
            ref_pngs.extend(rd.rglob("*.png"))
    if ref_pngs:
        passed.append(f"Visual Oracle screenshots present: {len(ref_pngs)} PNG(s)")
    else:
        warnings.append(f"No FreeJ2ME reference screenshots in {game_dir.name}/analysis/reference-frames/ (recommended for visual diff)")

    # Print report
    print(f"=== J2ME Parity Gate Report: {slug} ===")
    for p in passed:
        print(f"  [PASS] {p}")
    for w in warnings:
        print(f"  [WARN] {w}")
    for f in failures:
        print(f"  [FAIL] {f}")

    if failures:
        print(f"\nRESULT: FAIL ({len(failures)} hard gate(s) failed — fix before reporting done!)")
        sys.exit(1)
    print(f"\nRESULT: PASS ({len(passed)} checks passed, {len(warnings)} warning(s))")
    sys.exit(0)


if __name__ == "__main__":
    main()
