---
name: j2me-reverse-and-web-port
description: >-
  End-to-end playbook and hard-won lessons for reverse-engineering J2ME (.jar MIDP 2.0) games
  and porting them to native HTML5 Canvas/WebGL + ES Modules + Multiplayer + Discord Activity
  in this monorepo. Use whenever analyzing a new .jar game, decoding binary tables/sprites,
  fixing parity bugs, adding multiplayer/AI, or deploying to Vercel & Discord Activity.
---

# J2ME Reverse Engineering & Native Web Port Playbook

This skill distills practical lessons learned from reverse-engineering and porting J2ME `.jar` games (Prehistoric Tribes, Total Tournament, Green Farm 3, Ancient Empires 2) into zero-JVM HTML5 Canvas/WebGL web ports with 1:1 menu/HUD/gameplay parity, multiplayer, and Discord Activity support.

> **Gold-Standard Reference Ports**: Study `../total-tournament-clone/web-port/` (bitmap font + VI diacritics, sprite HUD, `curs.png`/`ld.png` menus, `wpn`/`wlg` bot AI, Chrome CDP visual QA) alongside `../bo-lac-thoi-tien-su-clone/web-port/`.

---

## Golden Rules

1. **Never modify original binaries**: Keep `../<slug>-clone/original/*.jar` byte-for-byte intact and record SHA-256 hashes in `analysis/ASSETS-SHA256.txt`.
2. **Decode, never guess**: Read maps, sprite tables, animation lengths, building specs, skill offsets, and strings directly from the original binary packs (`/a`, `/ma`, `/pd0`, `/sa`, `EN.*`, etc.).
3. **Verify every claim with bytecode or live tests**: Decompilers drop casts, misread signed bytes, or flatten switches — always cross-check subtle logic against `javap -c -p -v`.
4. **Preserve test invariants**: Keep source `web-port/index.html` clean (e.g. `<script type="module" src="game.js"></script>`) and apply cache-busting `?v=<ts>` only during build in `tools/build-dist.py`.

---

## Step-by-Step Workflow

### Phase 1: Scaffold & Extract Evidence
1. Initialize a new game directory with:
   ```bash
   python3 tools/new-game-port.py <slug> <path/to/game.jar> "<Display Name>"
   ```
2. Decompile with **at least two decompilers** (Vineflower + CFR/Procyon) AND dump bytecode (`javap -c -p -v`) into `analysis/bytecode-evidence/`.
   - **Check non-empty outputs immediately**: verify `.javap.txt` files are not 1-line `'command not found'` errors.
3. Write `analysis/CLASS-RESPONSIBILITIES.md` mapping every obfuscated class (`a`, `b`, `c`, ...) to its subsystem (MIDlet, GameLoop, Renderer, PackReader, Sound, AI).

### Phase 2: Decode Binary Tables & Assets
1. Identify the game's custom pack format (split chunks `5`, `5.1`, `5.2`..., indexed tables `mo[idx]`, or NET Lizard resource packs `cu2/ca/cc/ccs/cf/ll/wpn/wlg`).
2. **Inspect every field/column & Java Signed Byte Trap**: J2ME `byte` is signed (`-128..127`). Always distinguish:
   - Unsigned index/value: `b & 0xff`
   - Signed delta/offset/bias: `b > 127 ? b - 256 : b` (critical for sprite `dx`/`dy`/`ox`/`oy`, negative slope/collision codes like `cc[6] = -1`, and table-specific `+1` Y shifts such as props vs CTF bases in `ll`).
3. Dump decoded tables into inspectable JSON/assertions and verify counts/dimensions with a Node or Python script before writing gameplay code.
4. **Crisp Pixel Art, Bitmap Fonts & Integer MIDP Primitives**:
   - `ctx.imageSmoothingEnabled = false` and `Phaser.Textures.FilterMode.NEAREST`.
   - **Never replace a JAR's custom bitmap font (`fnt.png`+`cf`) or HUD sprite digits (`s0.png`/`ccs`) with smooth system `fillText` Arial/DejaVu!** Port the bitmap font renderer directly and add crisp 1px-black-outlined NFD pixel diacritic overlays (`Đ` crossbar, `\u0300..\u036f` marks with `0` advance, and `·/•` -> `-` fallback) for Vietnamese localization.
   - **Never use blurry `ctx.strokeRect` or fractional `ctx.stroke()` for 1px pixel borders**: use integer `fillRect` helpers `drawRectMIDP` (`(w+1)×(h+1)`) and `drawLineMIDP`.
   - Distinguish **limb-relative** sprite parts (`ca` supplies `(x, y)` offsets directly) from **offset-based** blitting (`a(g, frame, x, y, facing)` applies `cu2[4..5]` `ox/oy`, critical for burn flames and effects).
   - When generating extra multiplayer faction palettes in software, **skip dark outline pixels (`r+g+b < 75`) and skin-tone pixels** so faces/limbs stay natural, and never override original `pi9` dark-skin palettes with flat tints.

### Phase 3: Simulation Loop, Responsive Shell & Menus
1. **Fixed-timestep simulation + Synchronized 60fps Interpolation**:
   - Drive the J2ME tick clock (e.g. `77ms` or `100–120ms`) with a capped accumulator (`< 6` catch-up ticks) and inline `Blob` Web Worker when hosting multiplayer (`pauseOnBlur: false`).
   - Interpolate **camera AND all world entities/projectiles/effects** symmetrically using `lerpCoordRound(prev, curr, alpha)` (`valid = false` on respawn/warp).
   - Always provide a **native Canvas 2D fallback** if Phaser 3 CDN is blocked (such as inside Discord Activity CSP).
2. **Smooth mouse/pointer performance & Viewport Shell Hygiene**:
   - Never call synchronous `draw()` directly inside `pointermove`. Set a dirty flag (`markDirty()`) and render on `requestAnimationFrame`.
   - Align tall/overhanging map objects (trees, buildings) so clickable tile hitboxes match the rendered hover cursor 1:1.
   - **Never float HTML overlays (`position: fixed; bottom: ...`) over the game `<canvas>`**: dock `.floating-toolbar` cleanly below `#game` inside a vertical `flex-direction: column` stage (`height: calc(100vh - 54px)`) so J2ME softkeys and bottom HUD stay 100% unobstructed.
3. **Menu States, Chrome & Transitions (`c.java`/`e.java`)**:
   - Port EVERY original state ID (`startup`, `title`, `K=0..22`), choice bar caps (`curs.png`) with press-down offsets, mechanical hazard curtains (`ld.png`), softkey idle/pressed sprites, typewriter description boxes, CTF locked-map skipping, Help/About headers & scrollbars, and Scoreboard columns/sorting.
   - Keep loading artwork (`li1`/`li2`) isolated to actual match loading transitions (never leak them behind Character Select if `c.java` draws black + `ld.png`), and ensure Pause preserves `backgroundName` so the frozen arena background renders behind the dimmed menu.
   - Gate cosmetic loading delays (`loadingTicks`) so they run only when `app.loop` is active, keeping synchronous Node unit tests fast and deterministic.

### Phase 4: Authentic Gameplay, Combat & AI Parity
1. **Data-Driven Bot AI Navigation & Anti-Deadlock**:
   - Wire the JAR's own nav grids (`wpn`) and steering rule tables (`wlg`) + waypoint scanner (`findNavWaypoint`) instead of ad-hoc heuristics, while keeping ranged weapons active in mid-air so jumping bots never melee-deadlock.
2. **Weapon, Physics & Game-Mode Edge Cases**:
   - Apply exact armor/HP splits, splash radii derived from sprite bounds (e.g. `cu2[39].w + cu2[39].h`), self-kill frag penalties, corpse platform landing (unless over a pit), ledge-clipped ground shadows (`shadowEdgeClip`), beam weapon truncation (`hitOnce` preventing multi-tick double hits), CTF pit auto-return + SFX, and Last Hero graduated placement + dead-player Fire skip.
   - Always pass sprite/tile `tables` into every round-reset/respawn helper (`advanceLastHeroRound` -> `respawnActor`).
3. **Village / Campaign / RPG Subsystems (when applicable)**:
   - Preserve `savedJobs` when workers step out to heal/eat/defend; hook all work loops into real skill tables; reserve a home workforce (`minHomeReserve = Math.max(4, Math.ceil(adults.length * 0.55))`) for AI opponents; use smooth age/HP curves rather than abrupt cutoffs.

### Phase 5: Multiplayer, Lobby & Discord Activity (Mandatory for Every Game)
1. **Every Web Port Must Be Multiplayer-Capable**:
   - Adapt the multiplayer mode to the game's core J2ME loop: arena PvP/Team/CTF/Survival + AI bots (`total-tournament`, `bo-lac-thoi-tien-su`), online turn-based tactical skirmish replacing/extending J2ME Hotseat (`ancient-empires-2`), or co-op shared farm / timed harvest challenge (`green-farm-3`).
   - Add a `CHƠI ONLINE` / `MULTIPLAYER` option **directly inside the game's in-game Main Menu canvas** alongside the `#btn-mp-lobby` shortcut in `.floating-toolbar`, both opening the bilingual VI/EN `#mp-lobby` modal supporting **Create Room**, **Join by Code**, **Copy Link (`?mp=<code>`)**, **Open Tab 2**, character/team selection, Ready/Countdown (`2–4` players + optional AI bots), and `?mp=<code>` auto-join on boot.
2. **Multi-Transport + Unique Room Namespace on Shared `/api/mp`**:
   - Public non-standard MQTT ports (`8084`/`8884`) can be blocked by Discord CSP and strict firewalls; public HTTP relays like `ntfy.sh` can rate-limit; Vercel Serverless spins up multiple instances concurrently.
   - **Solution**: Run a same-origin `/api/mp` (`api/mp.mjs`, pinned to `regions: ["sin1"]`) that **bridges instances server-side via EMQX MQTT**, combined with client-side `BroadcastChannel` (<5ms local/tab-2), `NtfyHttpsRelay`, and `MqttWssRelay`. Stop probing `/api/mp` after a `404` on static local HTTP servers, and **never** embed blocking third-party `<script>` CDN tags (use `window.Peer` opportunistically only if already present).
   - **Prefix every game's room codes uniquely** via `normalizeRoomCode` (e.g. `TT4829`, `AE4829`, `GF4829` — keeping `<= 8` alnum chars for `api/mp.mjs`) so different games never collide on `bltts/mp/v2/${code}/+`.
3. **Authoritative Host → Guest Parity & Background Tick**:
   - Drive the Host simulation tick via an inline `Blob` Web Worker (`setInterval`) with fallback to `app.loop` if `Worker` is blocked by CSP, so background tabs keep simulating cleanly.
   - Pack compact authoritative snapshots (`packMatchSnapshot`) and restore them via `applyMatchSnapshot` (setting `prevX`/`prevY` for 60fps lerp, syncing HUD/scores/pickups/flags/rankings, inferring local SFX per client, and computing win/loss/draw **relative to the local player/team**, not Host!).
   - In `createEngineLoop`, skip key interception when `event.target` is `INPUT`/`TEXTAREA`/`SELECT`; on Host `onGuestInput`, OR-accumulate edge triggers (`switchWeapon`) until consumed and reset `switchWeapon = false` after tick; clear held remote inputs on `onGuestLeave`.

### Phase 6: Visual Browser QA, Parity Gate & Zero-Cache Build
1. In `vercel.json`:
   - Set `"installCommand": "true"` when the repo contains heavy non-web dev dependencies (`package.json`) so static+API deploys stay ~15s fast.
   - Set `Cache-Control: no-store, no-cache, must-revalidate, max-age=0` + `CDN-Cache-Control: no-store` on `/`, `/games/*/`, and `*.html|js|mjs|css|json` (keep `assets/` immutable).
2. In `tools/build-portal.py`:
   - Stamp `?v=<timestamp>` onto `index.html` script/CSS tags, `games-manifest.json` entry URLs, and all relative ES module imports in `dist/`.
3. **Mandatory Live Headless Browser Visual QA Loop** (never rely on unit tests alone!):
   - Expose read-only state inspection during browser boot (e.g. `window.__TT_APP__ = app`).
   - Run an automated local HTTP + Chrome headless CDP (`--headless=new --remote-debugging-port=0` with Node `http` + `WebSocket`) or Playwright script stored in scratch space (outside the repo) that walks through **Startup -> Title -> Every Menu Screen (VI & EN) -> Config -> Map/Char Select -> Loading -> Multiple Arenas/Modes (HUD, firing, effects) -> Pause -> Scoreboard**.
   - **Include a 2-Tab Multiplayer E2E Check**: open Tab 1 (Host creates room), open Tab 2 (`?mp=<code>` auto-joins), swap faction, Ready both, wait for Countdown launch, send remote actions/keys on Tab 2 and Host actions on Tab 1, verify synchronized actor coordinates/projectiles/HUD across both tabs, inspect MP lobby + live 2-tab screenshots via `read_file`, and confirm `consoleErrors.length === 0`.
4. **Final Verification & Pre-push Checklist**:
   - `node --check` on all modified `.js` / `.mjs` files in the standalone `../<slug>-clone/web-port/` repo
   - `node --test ../<slug>-clone/web-port/tests/*.test.mjs` (unit, parity, AND `multiplayer.test.mjs` regression tests)
   - `python3 tools/verify-port-parity.py ../<slug>-clone` (MUST exit 0 / `RESULT: PASS`)
   - `npm --prefix ../<slug>-clone run build`
   - Verify no oversized files (>25MB / JDK downloads / emulator capture dumps / scratch scripts) are staged.

For detailed bug case studies and concrete code patterns, read:
- [references/decompile-to-source-parity.md](./references/decompile-to-source-parity.md) — exact Java MIDP 2.0 → JS translation helpers (`drawRegionMIDP`, signed byte/short, BSprite/Macrospace/HandyGames pack patterns, citation discipline).
- [references/pitfalls-and-patterns.md](./references/pitfalls-and-patterns.md) — real bugs encountered in this monorepo and their verified fixes.
- [docs/J2ME_DECOMPILE_FIDELITY_GUIDE.md](../../../docs/J2ME_DECOMPILE_FIDELITY_GUIDE.md) — full Vietnamese guide for humans & AI agents.
- **Bundled Offline Decompilers & Native C++/QA References** (`../j2me-cpp-porter/`):
  - `../j2me-cpp-porter/skills/jar-to-cpp-port/scripts/decompile_jar.sh` (with local `vineflower-1.12.0.jar` + `cfr-0.152.jar`)
  - `../j2me-cpp-porter/skills/jar-to-cpp-port/resources/prepare_assets.py` (magic-byte inspection, stripped-header PNG `IHDR`/`PLTE`/`tRNS`/`IDAT` CRC reconstruction & `zlib` verification)
  - `../j2me-cpp-porter/skills/jar-to-cpp-port/references/vietnamese-ui-layout.md` (lookahead word-wrap, `textBounds` separation, midpoint anti-overlap, calm auto-scroll)
  - `../j2me-cpp-porter/skills/jar-to-cpp-port/references/desktop-pitfalls-and-qa.md` (floor-div negative scroll `>> k`, zero-ghosting camera+entity sync lerp, keypad scancode ownership, focus-lost vs menu-toggle input clearing, ASan+UBSan QA)
