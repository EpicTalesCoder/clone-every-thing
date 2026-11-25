# Hướng dẫn Decompile & Port Game J2ME 1:1 Giống Mã Nguồn Gốc

> **Mục tiêu**: Đảm bảo mọi game `.jar` (MIDP 2.0) trong từng project độc lập (`../<slug>-clone/web-port/`) **chạy, vẽ và vận hành giống bản gốc 1:1** (như chuẩn của `../bo-lac-thoi-tien-su-clone`), **TUYỆT ĐỐI KHÔNG** viết lại bản "nhái theo trí nhớ" bằng hình vuông `fillRect` hay thông số tự bịa.

---

## 1. Tại sao bản port hay bị lỗi & không giống game gốc? (5 lỗi chí mạng cần tránh)

| Lỗi phổ biến | Biểu hiện | Cách sửa bắt buộc |
|---|---|---|
| **1. Tự viết lại game theo trí nhớ** | Chỉ có ~300–500 dòng `game.js`, tự bịa HP/damage/map, vẽ ô màu bằng `fillRect`. | Phải dịch **trực tiếp từng hàm** từ `decompiled-vineflower/*.java` (`paint`, `tick`, `keyPressed`, `loadLevel`) và ghi chú rõ nguồn `Class.java:line`. |
| **2. Không có ảnh chụp đối chiếu từ giả lập** | Chạy lên tưởng đúng nhưng lệch tọa độ, sai font, mất layer, sai màu nền/HUD. | Chụp ít nhất 5–10 khung hình thật từ **FreeJ2ME** (Title, Menu, In-Game, HUD, Combat/Dialog) để đối chiếu pixel-by-pixel. |
| **3. Chỉ trích PNG rời, bỏ qua file bảng `.sprite` / BSprite / map nhị phân** | Nhân vật đứng đơ, lệch tâm, thiếu vũ khí/hiệu ứng, map không đúng bố cục gốc. | Phải đọc đúng định dạng nhị phân của chính game (bảng module/frame/animation, bảng palette, file map `.m` / `/ma` / pack `0..11`). |
| **4. Sai ngữ nghĩa J2ME `Graphics` & kiểu số Java** | Sprite bị lệch góc, lật ngược sai, tràn khung, hoặc chỉ số mảng bị âm/NaN. | Bắt buộc port đúng **Anchor** (`TOP|LEFT`, `HCENTER|VCENTER`, `RIGHT|BOTTOM`), **Transform** (`TRANS_MIRROR`, `ROT90/180/270`), **Clip** (`setClip`), và **signed byte** (`b > 127 ? b - 256 : b`). |
| **5. Chỉ dùng 1 trình decompile (hoặc `javap` rỗng)** | Mất nhánh `switch`, sai vòng lặp `while/goto`, nhầm biến bị obfuscate `a/b/c`. | Luôn chạy song song **Vineflower + CFR + `javap -c -p -v`** và kiểm tra kích thước file đầu ra > 0. |

---

## 2. Quy trình 6 bước chuẩn để Decompile & Port giống gốc 1:1

### Bước 1: Giải nén & đóng băng bản gốc (Evidence First)
```bash
python3 tools/new-game-port.py <slug> <duong-dan-file.jar> "<Tên Game>"
```
- **Không bao giờ sửa** `games/<slug>/original/*.jar`.
- Kiểm tra `games/<slug>/analysis/recovered/` đã có đủ toàn bộ `.class`, ảnh `.png`, bảng nhị phân, âm thanh `.mid`/`.amr`/`.wav`, chuỗi ngôn ngữ.

### Bước 2: Decompile đa công cụ + trích xuất Bytecode chuẩn
Chạy đủ **3 nguồn** vào `games/<slug>/analysis/`:
1. **Vineflower** (`analysis/decompiled-vineflower/`) — cấu trúc `if/switch/for` sạch nhất, dùng làm nguồn chính để đọc logic.
   ```bash
   java -jar vineflower.jar games/<slug>/original/*.jar games/<slug>/analysis/decompiled-vineflower/
   ```
2. **CFR** (`analysis/decompiled-cfr/`) — đối chiếu những hàm bị obfuscate nặng hoặc vòng lặp `goto` mà Vineflower gộp sai.
   ```bash
   java -jar cfr.jar games/<slug>/original/*.jar --outputdir games/<slug>/analysis/decompiled-cfr/
   ```
3. **Bytecode `javap -c -p -v`** (`analysis/bytecode-evidence/*.javap.txt`) — **chân lý tuyệt đối** khi nghi ngờ phép toán bit (`>>>` vs `>>`), ép kiểu `(byte)`/`(short)`, thứ tự đọc `DataInputStream`.
   ```bash
   # Luôn kiểm tra `which javap` trước khi chạy!
   for f in games/<slug>/analysis/recovered/*.class; do
     cls=$(basename "$f" .class)
     javap -c -p -v -cp games/<slug>/analysis/recovered "$cls" > "games/<slug>/analysis/bytecode-evidence/${cls}.javap.txt"
   done
   ```
   > **Kiểm tra bắt buộc**: không file `.javap.txt` nào được < 100 byte (tránh lỗi im lặng `javap: command not found`).

### Bước 3: Lập bản đồ Class & Định dạng dữ liệu (`CLASS-RESPONSIBILITIES.md`)
Trước khi viết 1 dòng JS nào, tạo `games/<slug>/analysis/CLASS-RESPONSIBILITIES.md` ghi rõ:
- Class nào là `MIDlet` (vòng đời app), class nào là `Canvas` (`paint`, `run`, `keyPressed`, `keyReleased`).
- Class nào đọc tài nguyên nhị phân (`getResourceAsStream`, `DataInputStream.readByte/readShort/readInt`).
- Danh sách **toàn bộ trạng thái màn hình (`gameState`)**: Splash → Logo → Language → MainMenu → MapSelect → Playing → Pause → Victory/Defeat.
- Cấu trúc bảng dữ liệu thực thể (mảng song song kiểu `entityData[offset + id]` hay mảng Object `Unit[]`).

### Bước 4: Giải mã 100% tài nguyên & bảng nhị phân gốc
Nhận diện họ engine J2ME phổ biến trong kho của chúng ta:

1. **Họ HandyGames / Bảng chỉ mục phẳng** (ví dụ: *Bộ lạc thời tiền sử*):
   - Dữ liệu nén trong `/a`, `/ma`, `/pd0`, `/sa`, ảnh chia nhóm `/pi0`, `/pi8`, `/pi9`.
   - Viết script Python giải mã ra JSON (`data-*.json`) để kiểm chứng số lượng tile, sprite leaf, composite, animation frame, bảng building specs (`mo[138]`), bảng skill (`mo[126]`/`mo[127]`).
2. **Họ Gameloft BSprite / Pack chia mảnh** (ví dụ: *Green Farm 3* — file `0`, `2`, `2.1`, `5`, `5.1`..., `EN`, `EN.1`...):
   - Các file chia mảnh (`X`, `X.1`, `X.2`...) là một khối dữ liệu liên tục ghép lại (mỗi mảnh thường 10.000 byte) theo bảng header `pack`.
   - **BSprite** chứa: `modules` (x, y, w, h trên sheet hoặc raw pixel + bảng palette nhiều màu), `fmodules` (module + ox, oy + flags flip/rotate), `frames` (danh sách fmodules), `aframes` (frame + duration + ox, oy), `anims` (danh sách aframes).
   - **Bắt buộc** viết bộ decoder BSprite thực thụ thay vì chỉ cắt ô vuông đều nhau!
3. **Họ Macrospace / Ancient Empires (`.sprite`, `.m`, `.png` dải frame)**:
   - Mỗi unit/tile có ảnh PNG dạng strip + file metadata `.sprite` (kích thước frame, số frame, tốc độ, offset) + file map `.m` (width, height, mảng tile ID, vị trí unit & nhà ban đầu).
   - Phải đọc trực tiếp file map gốc và bảng thông số unit (giá tiền, sức đánh min/max, phòng thủ, tầm di chuyển, tầm bắn, địa hình) từ bytecode của class gốc.

### Bước 5: Port chuẩn từng hàm Java → JavaScript (1:1 Semantics)

#### 5.1. Chuyển đổi chuẩn kiểu số & toán tử Java
```js
// Java byte (-128..127)
export const s8 = (v) => ((v & 0xff) > 127 ? (v & 0xff) - 256 : (v & 0xff));
export const u8 = (v) => v & 0xff;
// Java short (-32768..32767)
export const s16 = (v) => ((v & 0xffff) > 32767 ? (v & 0xffff) - 65536 : (v & 0xffff));
export const u16 = (v) => v & 0xffff;
// Java int division (hướng về 0, KHÁC Math.floor với số âm!)
export const idiv = (a, b) => Math.trunc(a / b);
```

#### 5.2. Chuyển đổi chuẩn `javax.microedition.lcdui.Graphics`
- **Anchor (`drawImage(img, x, y, anchor)` / `drawString(..., anchor)`)**:
  - `HCENTER = 1`, `VCENTER = 2`, `LEFT = 4`, `RIGHT = 8`, `TOP = 16`, `BOTTOM = 32`, `BASELINE = 64`.
  - Luôn trừ đúng `dx = (anchor & 1) ? w >> 1 : (anchor & 8) ? w : 0`, `dy = (anchor & 2) ? h >> 1 : (anchor & 32) ? h : 0`!
- **Transform (`Sprite.TRANS_*` / `DirectGraphics`)**:
  - `0 = NONE`, `1 = MIRROR_ROT180`, `2 = MIRROR`, `3 = ROT180`, `4 = MIRROR_ROT270`, `5 = ROT90`, `6 = ROT270`, `7 = MIRROR_ROT90`.
  - Bắt buộc xử lý đủ 8 phép biến hình này khi vẽ `drawRegion` / BSprite `fmodule`!
- **Clip (`g.setClip(x, y, w, h)`)**:
  - Dùng `ctx.save(); ctx.beginPath(); ctx.rect(x, y, w, h); ctx.clip(); ... ctx.restore();`.
- **Pixel-art 1:1**:
  - Luôn đặt `ctx.imageSmoothingEnabled = false` và `FilterMode.NEAREST`.
  - Vẽ trên khung logic gốc (`240x320` hoặc viewport mở rộng giữ nguyên tỉ lệ tile gốc).

#### 5.3. Đối chiếu cấu trúc module (theo chuẩn `bo-lac-thoi-tien-su`)
Mỗi game nên tách rõ tối thiểu 4 file để dễ kiểm tra và sửa lỗi:
1. `<slug>-loader.js` (hoặc `scenario-loader.js`): giải mã 100% file map/table/unit specs từ `assets/` gốc.
2. `render-original.js`: port 1:1 hàm `paint()` của game gốc (lớp nền → đối tượng/công trình → nhân vật/hiệu ứng → HUD/menu gốc).
3. `game.js`: port vòng lặp `run()` / `tick()` / state machine / AI / điều khiển chuột + bàn phím (ánh xạ phím số `2/4/6/8/5`, softkey trái/phải, và click chuột trực tiếp).
4. `multiplayer.js` + giao diện phòng chờ `#mp-lobby`: chế độ chơi nhiều người **bắt buộc** (2–4+ người chơi / Host-authoritative + background Web Worker + Quad Transport `/api/mp`, `BroadcastChannel`, `ntfy`, MQTT-WSS + mã phòng có tiền tố riêng từng game + tự vào phòng qua `?mp=<code>`).
5. `tests/*.test.mjs`: unit test kiểm tra decoder, độ toàn vẹn file gốc, logic lõi và `multiplayer.test.mjs`.

### Bước 6: Đối chiếu thị giác (Visual Oracle) & Cổng kiểm duyệt 11 điểm

Trước khi coi một game port là hoàn thành, kiểm tra đủ **11 tiêu chí**:
1. Mở được ngay trên trình duyệt & Portal (`python3 tools/build-portal.py`), không có lỗi `404` / `TypeError` trong Console.
2. Màn hình Title / Menu sử dụng **đúng ảnh nền, logo, font/nút gốc** từ `.jar` (không vẽ khung CSS/HTML thay thế sơ sài).
3. Bản đồ màn 1 khớp **100% bố cục địa hình, vị trí nhà và quân** với file map gốc trong `.jar`.
4. Mọi nhân vật/quân lính vẽ bằng **đúng sprite sheet & frame animation gốc** (đi bộ, đứng yên, tấn công, chết), không dùng hình khối `fillRect` thay thế.
5. Màu phe / palette gốc hiển thị đúng (không bị mất màu da, không nhầm màu địch/ta).
6. Vòng lặp game chính (lượt đánh / xây nhà / thu hoạch / thắng-thua) chạy theo đúng công thức trong Java gốc (có comment dẫn chiếu `Class.java:line`).
7. Hoạt động tốt bằng cả **chuột** (click/kéo) lẫn **bàn phím** (mũi tên/WASD/Enter/Escape).
8. Chạy mượt khi chuyển tab / phóng to cửa sổ, có fallback Canvas 2D khi CDN bị chặn (chạy được trong Discord Activity).
9. Giữ nguyên `original/*.jar` và có bộ test `node --test` pass 100%.
10. Chạy QA trình duyệt thật (`Chrome headless CDP` / localhost): chụp & soi từng PNG across Startup → Menus (VI & EN) → Loading → Gameplay → Pause → Scoreboard, bảo đảm `Console errors: 0`, không mất dấu/ký tự bitmap, `strokeRect` nhòe hay thanh công cụ HTML đè lên HUD/softkey; đối chiếu ảnh FreeJ2ME gốc nếu có.
11. **Multiplayer bắt buộc (Chơi nhiều người)**: Mọi game đều phải có mục **Chơi Online / Multiplayer ngay trong Menu chính trong game** kèm nút `#btn-mp-lobby`, mở phòng chờ 2–4+ người (`#mp-lobby`, Tạo/Vào phòng với mã phòng riêng theo game, Mở Tab 2 `?mp=<code>`, chọn phe/nhân vật, Sẵn sàng & đếm ngược, Host Web Worker chống nghẽn tab nền, đồng bộ hành động 2 tab không lỗi Console).

---

## 3. Tài liệu liên quan trong kho mã nguồn
- Skill tự động cho AI Agent: [.agents/skills/j2me-reverse-and-web-port/SKILL.md](../.agents/skills/j2me-reverse-and-web-port/SKILL.md)
- Tham chiếu lỗi thực tế & mẫu dịch chuẩn: [.agents/skills/j2me-reverse-and-web-port/references/decompile-to-source-parity.md](../.agents/skills/j2me-reverse-and-web-port/references/decompile-to-source-parity.md)
- Luật bắt buộc cho AI Agent khi port game: [.agents/rules/j2me-port-fidelity.md](../.agents/rules/j2me-port-fidelity.md)
