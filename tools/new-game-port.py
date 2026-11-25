#!/usr/bin/env python3
"""
Scaffold a standalone J2ME (.jar) reverse-engineering & HTML5 web-port project
outside the REA repository (default: ../<slug>-clone/).

Usage:
  python3 tools/new-game-port.py <slug> <path-to-jar> ["Display Title"] [--out <dir>]
"""
import argparse
import hashlib
import json
import pathlib
import shutil
import zipfile

ROOT = pathlib.Path(__file__).resolve().parent.parent


def sha256_file(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description="Scaffold a standalone J2ME clone project.")
    parser.add_argument("slug", help="Game slug (e.g. my-game)")
    parser.add_argument("jar", help="Path to original .jar file")
    parser.add_argument("title", nargs="?", default="", help="Optional display title")
    parser.add_argument("--out", default="", help="Optional target project directory (default: ../<slug>-clone)")
    args = parser.parse_args()

    slug = args.slug.strip().lower()
    jar_src = pathlib.Path(args.jar).expanduser().resolve()
    title = args.title or slug.replace("-", " ").title()
    if not jar_src.exists():
        raise SystemExit(f"Error: JAR file not found: {jar_src}")

    repo_name = slug if slug.endswith("-clone") else f"{slug}-clone"
    game_dir = pathlib.Path(args.out).expanduser().resolve() if args.out else (ROOT.parent / repo_name)
    orig_dir = game_dir / "original"
    analysis_dir = game_dir / "analysis"
    recovered_dir = analysis_dir / "recovered"
    decompiled_dir = analysis_dir / "decompiled-cfr"
    bytecode_dir = analysis_dir / "bytecode-evidence"
    web_dir = game_dir / "web-port"
    assets_dir = web_dir / "assets"
    tests_dir = web_dir / "tests"

    for d in [orig_dir, recovered_dir, decompiled_dir, bytecode_dir, assets_dir, tests_dir, game_dir / "tools"]:
        d.mkdir(parents=True, exist_ok=True)

    jar_dst = orig_dir / jar_src.name
    shutil.copy2(jar_src, jar_dst)
    print(f"[1/4] Copied untouched JAR to {jar_dst} (SHA-256: {sha256_file(jar_dst)})")

    manifest_lines = []
    with zipfile.ZipFile(jar_dst, "r") as zf:
        zf.extractall(recovered_dir)
    for item in sorted(recovered_dir.rglob("*")):
        if item.is_file():
            rel = item.relative_to(recovered_dir)
            manifest_lines.append(f"{sha256_file(item)}  {rel}")
    (analysis_dir / "ASSETS-SHA256.txt").write_text("\n".join(manifest_lines) + "\n", encoding="utf-8")
    print(f"[2/4] Extracted {len(manifest_lines)} entries into {recovered_dir}")

    engine_src = ROOT / "tools" / "phaser-j2me-engine.js"
    if engine_src.exists():
        shutil.copy2(engine_src, web_dir / "phaser-engine.js")

    index_html = web_dir / "index.html"
    if not index_html.exists():
        index_html.write_text(
            f"""<!doctype html>
<html lang="vi">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title} — Web Port</title>
</head>
<body style="background:#111;color:#eee;font-family:monospace;text-align:center;padding:32px">
  <main class="app-shell">
    <section class="viewport-stage" id="viewport-stage">
      <canvas id="game" width="240" height="320" style="border:1px solid #444;image-rendering:pixelated"></canvas>
      <div class="floating-toolbar">
        <button type="button" id="btn-mp-lobby">⚔️ Phòng MP</button>
      </div>
    </section>
  </main>
  <div id="mp-lobby" class="mp-lobby-overlay" hidden></div>
  <script type="module" src="game.js"></script>
</body>
</html>
""",
            encoding="utf-8",
        )

    pkg = {
        "name": repo_name,
        "private": True,
        "type": "module",
        "scripts": {
            "test": "node --test web-port/tests/*.test.mjs",
        },
    }
    pkg_path = game_dir / "package.json"
    if not pkg_path.exists():
        pkg_path.write_text(json.dumps(pkg, indent=2) + "\n", encoding="utf-8")

    print(f"[3/4] Initialized standalone web-port project at {game_dir}")
    print(f"[4/4] Next: python3 tools/prepare-j2me-evidence.py {game_dir}")


if __name__ == "__main__":
    main()
