---
description: Enforce 1:1 source-faithful J2ME decompilation and web porting for standalone <slug>-clone projects
---

# J2ME Faithful Porting Rule

## Auto-Trigger Playbook ("decompile game X" / "port game X" / "import game X")

Whenever the user asks to decompile, port, fix parity, or import a J2ME game (even with a short prompt like `"decompile game total tournament"`), automatically follow this exact sequence without waiting to be told where files are:

1. **Locate or scaffold the standalone game project (`../<slug>-clone/`)**:
   - Never commit game projects inside REA's `main` branch (`clone-every-game`). Each game lives in its own standalone repository (`../<slug>-clone/`). If the user provides a new `.jar` path, run `python3 tools/new-game-port.py <slug> <jar-path> "<Display Name>"` (which scaffolds `../<slug>-clone/`).
2. **Load project standards first**:
   - Read `docs/J2ME_DECOMPILE_FIDELITY_GUIDE.md`, `.agents/skills/j2me-reverse-and-web-port/SKILL.md`, and `.agents/skills/j2me-reverse-and-web-port/references/decompile-to-source-parity.md`.
3. **Prepare evidence before coding**:
   - Run `python3 tools/prepare-j2me-evidence.py ../<slug>-clone` so `analysis/CLASS-INDEX.md`, `analysis/bytecode-evidence/*.javap.txt` (>100B each), and `analysis/decompiled-*/*.java` are up to date.
4. **Plan & execute in 4 gated stages**:
   - **Stage 1**: Write/update `../<slug>-clone/analysis/CLASS-RESPONSIBILITIES.md` (classes, state machine, binary formats, formulas with `Class.java:line`).
   - **Stage 2**: Build 100% real binary decoders + `render-original.js` (exact MIDP anchors, `drawRegionMIDP`, integer `drawRectMIDP`/`drawLineMIDP`, `setClip`, original bitmap font + NFD VI diacritics, `s0` sprite HUD, original sprites/maps/curtains — zero `fillRect` placeholders or blurry system `fillText` replacing bitmap fonts).
   - **Stage 3**: Port core gameplay (`game.js`: input/mouse+keys, movement, combat/economy formulas, nav-table AI, round/save lifecycle) **plus mandatory 2–4 player Multiplayer** (`multiplayer.js` + docked `.floating-toolbar` lobby button & `#mp-lobby` overlay, Host-authoritative tick + background Web Worker + `?mp=<code>` auto-join + Quad Transport `/api/mp` / `BroadcastChannel` / `ntfy` / MQTT-WSS) citing `// Port of Class.java:line`, keeping `.floating-toolbar` outside `#game` bounds so HUD/softkeys stay unobstructed.
   - **Stage 4**: Run `python3 tools/verify-port-parity.py ../<slug>-clone` (MUST exit 0 / PASS!), `npm --prefix ../<slug>-clone run build` (via `tools/build-dist.py`), and run a live headless browser visual QA walkthrough (capturing and visually inspecting PNG screenshots across startup, all menus in VI & EN, loading splash, pause backdrop, scoreboard, active gameplay, **plus a 2-tab Host + Guest `?mp=<code>` multiplayer sync test** with zero console errors).

## Zero-Invention Evidence Contract (Hard Locks)

When creating, fixing, or extending any J2ME web port under `../<slug>-clone/web-port/`:

1. **No "from-memory" rewrites or placeholder clones**:
   - Do NOT invent game mechanics, unit stats, map layouts, or draw placeholder `fillRect` geometry when the original `.jar` contains real sprites, maps, and formulas.
   - Always read the game's decompiled Java sources (`analysis/decompiled-vineflower/` and/or `analysis/decompiled-cfr/`) and `analysis/bytecode-evidence/*.javap.txt` first.
   - If decompiled sources or `javap` dumps are missing or empty, run `python3 tools/prepare-j2me-evidence.py <slug>` before coding.
2. **Unknown = STOP & VERIFY (Never Guess)**:
   - If any obfuscated method, formula, or binary table layout is unclear in the decompiled Java, inspect `analysis/bytecode-evidence/<Class>.javap.txt` directly.
   - If still uncertain, mark `// UNVERIFIED` and ask the user explicitly — **NEVER** silently invent a fallback formula or approximate table!
3. **100% Data-Driven Decoding (No Hand-Typed Game Data)**:
   - Decode maps, sprite/BSprite/animation frames, palettes, unit stats, and text directly from the original binary files in `assets/` (or generate verified JSON via a deterministic script reading `analysis/recovered/`).
   - Respect Java signed integer/byte semantics (`s8`, `s16`, `Math.trunc` integer division) and MIDP 2.0 `Graphics` anchors, clipping, and 8 `Sprite.TRANS_*` transforms.
4. **Mandatory Source Citations & Automated Gate**:
   - Add concise comments (`// Port of <Class>.java:<lines>`) on ported rendering passes, map/table decoders, state transitions, and combat/economy formulas.
   - **NEVER report a port complete** until `python3 tools/verify-port-parity.py ../<slug>-clone` exits `0` (`RESULT: PASS`) and `npm --prefix ../<slug>-clone run build` succeeds.
5. **Never modify `../<slug>-clone/original/*.jar`**.

## Deep Decompilation, Binary Integrity, UI & Runtime Parity Rules

Extracted from `../j2me-cpp-porter` to prevent recurring J2ME porting bugs across Web (HTML5) and Native (Desktop C++17 SDL2) targets:

1. **Dual-Decompiler + Bytecode Cross-Check (Offline Jars Available)**:
   - Always decompile every `.jar` with **both** Vineflower and CFR (`../j2me-cpp-porter/skills/jar-to-cpp-port/scripts/vineflower-1.12.0.jar` & `cfr-0.152.jar`, plus `javap -c -p -v`), read `META-INF/MANIFEST.MF`, and record `origW x origH`, fixed tick `frameDelayMs`, font format, binary `.ui`/map schemas, event opcodes, and `RecordStore` layout before coding.
2. **Magic-Byte Asset Verification & Stripped-PNG Reconstruction**:
   - **Never trust file extensions inside a `.jar`** (e.g. PNGs disguised as `.mid`/`.bin` or XOR-100 / length-prefixed XOR streams). Inspect magic bytes first.
   - For stripped-header PNG blobs (`[w, h, bitDepth, colorType, PLTE, optional "tRNS", IDAT]`), reconstruct full `IHDR`/`PLTE`/`tRNS`/`IDAT`/`IEND` chunks with valid CRC32 and verify every extracted PNG with `zlib.decompress(IDAT)` (see `../j2me-cpp-porter/skills/jar-to-cpp-port/resources/prepare_assets.py`).
3. **Exact Java Arithmetic, Signed Tables & State Lifecycle**:
   - **Signed byte/short & collision checks**: distinguish `s8` vs `u8`; never assume non-empty collision flags are `> 0` when source checks `!== 0` (e.g. negative slope/ramp offsets like `-1`).
   - **Negative scroll shifts**: Java `x >> k` paired with `x & ((1 << k) - 1)` floors toward `-∞` — use floor division (`Math.floor(x / 16)` / `floorDivPow2`), **never** truncating `/` which stalls negative camera scrolling.
   - **String indexing**: decode Modified UTF-8 into UTF-16 code units matching Java `charAt`/`substring` (never raw UTF-8 byte offsets).
   - **Safe teardown & VM completeness**: clear child views holding references before resetting owning world state; verify 100% of state `switch` cases, cutscene opcode return values (`true` only on map change), inverted quality flags (`!lowQuality`), and autosave dirty-flag ownership.
   - **Strip commercial locks**: remove SMS activation gates, trial caps (`Midlet.a`), IAP `+` prompts, and `"vnđ"` strings cleanly.
4. **Vietnamese / Localized UI Layout Discipline**:
   - Use **Lookahead Word-Boundary Wrapping** (strip color tags `#0..#7`/`#RRGGBB` from width math; never subtract `spaceRefWidth` early; only break mid-word if one word exceeds the full box width).
   - **Separate `textBounds` from icon/background rects**: never shift button/icon frames when widening Vietnamese labels; fit or auto-scroll overflowing labels and resolve adjacent label overlaps by midpoint split (`textOverlaps === 0`).
   - Render Vietnamese UI with the JAR's own bitmap font when present (`fnt.png` + `cf`) using `.normalize('NFD')` (`Đ->D` crossbar + crisp 1px-outlined `\u0300-\u036f` pixel accents with `0` advance, plus `·/•->-` fallback) and verify visually across VI & EN screens.
5. **Input Focus Hygiene & Zero-Ghosting Timing**:
   - Drive fixed simulation ticks with a high-resolution accumulator (cap catch-up ticks `< 6`). If interpolating to 60 FPS, interpolate **both camera AND every world entity/projectile/particle/floating text** symmetrically with rounded lerp and snap (`valid = false`) on warp/map load.
   - Clear input queues (`clearQueues + clearHeldInputs`) on menu/pause toggle without wiping physical key state; call full `resetAllState()` **only** on window blur / focus lost. Account for HiDPI scaling on pointer/mouse coordinates and track scancode ownership for shifted keys (`*`, `#`).
   - Support full J2ME phone keypad (`0..9`, Numpad, `*` = `42`, `#` = `35`, Arrows/`WASD`, `Enter`/`Space` = FIRE, `Q`/`Tab` = LSK, `E`/`Backspace` = RSK) alongside mouse/touch, resolve physical `event.code` (`KeyW`/`KeyA`/`KeyS`/`KeyD`/`KeyQ`) so `ASDW` & action keys work under Vietnamese Telex/Unikey IME, include an in-game key customization option in Settings when appropriate, `.blur()` HTML toolbar buttons on click so `Space` doesn't re-trigger them, and skip keyboard capture when `event.target` is `INPUT`/`TEXTAREA`/`SELECT` inside `#mp-lobby`.
6. **Mandatory Multiplayer Mode & Room Namespace Isolation**:
   - **Every web port MUST include a playable 2–4 player Multiplayer mode** matching its genre (arena PvP/co-op/team modes, turn-based tactical PvP, or co-op shared town/harvest competition), **accessible both directly from the in-game Main Menu canvas (e.g. `CHƠI ONLINE` / `MULTIPLAYER`) and from `#btn-mp-lobby` in `.floating-toolbar`**, using `multiplayer.js` (`Host`-authoritative state, inline `Blob` Web Worker host tick for background tabs, `?mp=<code>` link + `"Open Tab 2"`, bilingual VI/EN `#mp-lobby` overlay).
   - Isolate every game's room code prefix on shared `/api/mp` (`api/mp.mjs` `bltts/mp/v2/${code}/+`, e.g. `TTxxxx`, `AExxxx`, `GFxxxx` via `normalizeRoomCode`) so rooms never collide across games; omit blocking third-party CDN `<script>` tags so offline/Discord CSP runs with `0` console errors; verify Host/Guest sync with both `tests/multiplayer.test.mjs` and a 2-tab headless Chrome test.
