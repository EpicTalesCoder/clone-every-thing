# Bộ Prompt Mẫu Để AI Tự Động Decompile & Port Game J2ME Giống Bản Gốc 1:1

---

## Prompt Tổng Tự Chủ (Copy-Paste 1 lần cho mọi AI: Antigravity / Cursor / Claude / Codex)

Chỉ cần thay `<tên game hoặc slug>` (ví dụ `total-tournament`, `ancient-empires-2`, `green-farm-3` hoặc kèm đường dẫn file `.jar` mới) rồi dán nguyên đoạn sau cho AI:

```text
Hãy decompile và port 1:1 game <tên game hoặc slug> tại thư mục project độc lập `../<slug>-clone/` (tách riêng khỏi repo REA chính).

BẮT BUỘC làm đúng theo thứ tự sau (không bỏ bước, không tự bịa game theo trí nhớ):
1. ĐỌC TÀI LIỆU CHUẨN TRƯỚC:
   - docs/J2ME_DECOMPILE_FIDELITY_GUIDE.md
   - .agents/rules/j2me-port-fidelity.md
   - .agents/skills/j2me-reverse-and-web-port/SKILL.md
   - .agents/skills/j2me-reverse-and-web-port/references/decompile-to-source-parity.md
2. CHUẨN BỊ BẰNG CHỨNG TỰ ĐỘNG:
   - Nếu là file .jar mới chưa có project riêng, chạy `python3 tools/new-game-port.py <slug> <path.jar> "<Tên Game>"` (tạo project độc lập tại `../<slug>-clone/`).
   - Chạy `python3 tools/prepare-j2me-evidence.py ../<slug>-clone` để xuất đầy đủ `recovered/`, `bytecode-evidence/*.javap.txt`, `decompiled-*/*.java` và `CLASS-INDEX.md`.
   - Tuyệt đối KHÔNG sửa file `../<slug>-clone/original/*.jar`.
3. TỰ LẬP KẾ HOẠCH 4 CHẶNG RÕ RÀNG VÀ LÀM TỪNG CHẶNG:
   - Chặng 1 (Phân tích — chưa sửa web-port): Viết/cập nhật `../<slug>-clone/analysis/CLASS-RESPONSIBILITIES.md` (vai trò từng class, state machine, cấu trúc binary map/sprite/BSprite/text, công thức gốc kèm `Class.java:line`).
   - Chặng 2 (Giải mã & Vẽ 1:1): Viết decoder đọc trực tiếp map/sprite/palette/text gốc từ `assets/` + port hàm `paint()` vào `render-original.js` (đúng Anchor, 8 phép `drawRegionMIDP`, `setClip`, `imageSmoothingEnabled = false`, KHÔNG dùng `fillRect` thay sprite/map gốc).
   - Chặng 3 (Gameplay + Multiplayer chuẩn mã gốc): Port vòng lặp `run()/tick()`, điều khiển (chuột + phím), chiến đấu/kinh tế/AI/màn chơi/lưu game vào `game.js` với comment dẫn chiếu `// Port of Class.java:line`, **kèm chế độ Chơi nhiều người 2–4 người mở được cả từ Menu chính trong game lẫn thanh công cụ** (`CHƠI ONLINE` / `MULTIPLAYER` + `#mp-lobby`, `multiplayer.js`, Host Web Worker, Quad Transport `/api/mp` / `BroadcastChannel` / `ntfy` / MQTT-WSS, mã phòng có tiền tố riêng từng game, `?mp=<code>`).
   - Chặng 4 (Cổng kiểm duyệt cứng & Build): Viết unit test (decoder + gameplay + `multiplayer.test.mjs`) + chạy `python3 tools/verify-port-parity.py ../<slug>-clone` (BẮT BUỘC ra `RESULT: PASS`, exit 0), chạy `npm --prefix ../<slug>-clone run build`, kiểm tra trực quan 1 tab + đồng bộ 2 tab `?mp=` trên localhost (0 lỗi Console) rồi mới báo hoàn thành.

QUY TẮC CHỐNG TỰ BỊA (TUYỆT ĐỐI TUÂN THỦ):
- Mọi bảng map, chỉ số lính, sprite/BSprite/palette, text phải giải mã trực tiếp từ file gốc trong `.jar` — CẤM gõ tay hay tự bịa thông số.
- Chỗ nào code decompile bị rối/mơ hồ: bắt buộc đọc thẳng `bytecode-evidence/<Class>.javap.txt` để đối chiếu. Nếu vẫn chưa chắc 100%, ghi rõ `CHƯA XÁC MINH` và hỏi lại tôi — TUYỆT ĐỐI KHÔNG tự đoán công thức thay thế.
- Không được báo xong chừng nào `python3 tools/verify-port-parity.py ../<slug>-clone` chưa PASS.

Bắt đầu từ Bước 1 & 2, lập kế hoạch 4 chặng rồi tự chạy lần lượt từ Chặng 1 đến Chặng 4 cho tới khi PASS toàn bộ cổng kiểm duyệt.
```

> **Mẹo dùng siêu ngắn trong workspace này**: Vì repo đã gắn sẵn rule [.agents/rules/j2me-port-fidelity.md](../.agents/rules/j2me-port-fidelity.md), bạn chỉ cần gõ ngắn gọn:
> `Decompile và port 1:1 game total-tournament theo đúng rule j2me-port-fidelity.`
> là AI Agent sẽ tự động chạy đủ quy trình trên!

---

## Bộ Prompt Tách Từng Chặng (Dùng khi muốn kiểm soát chặt từng bước)

> **Nguyên tắc vàng**: **KHÔNG** giao cả game trong 1 câu lệnh duy nhất! Hãy thay `<slug>` bằng tên thư mục game (ví dụ `ancient-empires-2`, `green-farm-3`, `total-tournament`) và chạy lần lượt **4 chặng dưới đây**. Xong chặng nào kiểm tra trực tiếp trên trình duyệt chặng đó rồi mới sang chặng sau.

---

## Chuẩn bị trước khi gọi AI (chạy 1 lệnh — mất 10 giây)
```bash
# Nếu là game .jar hoàn toàn mới:
python3 tools/new-game-port.py <slug> <duong-dan-file.jar> "<Tên Game>"

# Tự động giải nén + chạy javap + CFR/Vineflower + tạo CLASS-INDEX.md:
python3 tools/prepare-j2me-evidence.py <slug>
```

---

## Chặng 1: Phân tích mã nguồn & định dạng dữ liệu (CẤM viết `game.js`)

```text
Đọc docs/J2ME_DECOMPILE_FIDELITY_GUIDE.md và .agents/rules/j2me-port-fidelity.md.
Chưa viết code web-port vội! Hãy phân tích games/<slug>/analysis/ (CLASS-INDEX.md, decompiled-vineflower/, decompiled-cfr/, bytecode-evidence/) và tạo/cập nhật file games/<slug>/analysis/CLASS-RESPONSIBILITIES.md gồm:
1. Vai trò từng class chính (MIDlet, Canvas/paint, GameLoop/run, Input, ResourceLoader, AI, Sound).
2. Toàn bộ state machine (Splash → Menu → SelectLevel → Playing → Dialog → Victory/Defeat).
3. Định dạng chính xác của file map, file sprite/animation/BSprite/palette, và chuỗi text trong recovered/.
4. Danh sách công thức gốc quan trọng (sát thương, phòng thủ, địa hình, kinh tế/nâng cấp) kèm dẫn chiếu chính xác Class.java:line.
```

> **Kiểm tra xong Chặng 1**: Đọc nhanh `CLASS-RESPONSIBILITIES.md` thấy đã chỉ rõ class nào vẽ, class nào load map, định dạng binary nào cần giải mã → chuyển sang Chặng 2.

---

## Chặng 2: Giải mã 100% dữ liệu gốc & dựng Renderer 1:1 (chưa cần AI/âm thanh)

```text
Áp dụng đúng .agents/skills/j2me-reverse-and-web-port/SKILL.md và CLASS-RESPONSIBILITIES.md của games/<slug>/.
Làm Chặng 2 (Data Loader + 1:1 Original Renderer):
1. Viết bộ giải mã đọc trực tiếp file map, bảng thông số, sprite/BSprite/palette và text gốc từ games/<slug>/web-port/assets/ (TUYỆT ĐỐI KHÔNG hardcode map giả hay vẽ nhân vật/nhà bằng hình vuông fillRect).
2. Port hàm paint() gốc vào render-original.js với đúng hệ tọa độ, Anchor, 8 phép Transform (drawRegionMIDP), setClip, imageSmoothingEnabled = false, và đúng thứ tự layer gốc (nền → địa hình → công trình/vật thể → nhân vật có animation → HUD gốc).
3. Chạy thử trên localhost và xác nhận màn hình Title + Map 1 + toàn bộ nhân vật/HUD hiển thị giống game gốc, không lỗi Console.
```

> **Kiểm tra xong Chặng 2**: Mở game ở `http://127.0.0.1:4180/games/<slug>/web-port/index.html` — nếu nhìn đã **giống hệt game gốc** (đúng bản đồ, đúng nhân vật, đúng giao diện) thì mới chuyển sang Chặng 3!

---

## Chặng 3: Port từng cơ chế gameplay từ Java gốc (tách nhỏ theo từng tính năng)

Dán lần lượt từng lệnh nhỏ (mỗi lượt chỉ làm 1 nhóm cơ chế để AI không cắt xén):

- **Lượt 3A — Điều khiển & Di chuyển**:
  ```text
  Dựa trên mã decompile của games/<slug>/analysis/, hãy port chính xác 1:1 cơ chế điều khiển (bàn phím + click chuột trực tiếp trên canvas), chọn ô/chọn nhân vật, tìm đường / phạm vi di chuyển và camera theo đúng Class.java:line gốc. Ghi rõ comment // Port of Class.java:line trên các hàm chính.
  ```
- **Lượt 3B — Chiến đấu / Tương tác / Kinh tế lõi**:
  ```text
  Dựa trên mã decompile của games/<slug>/analysis/, hãy port chính xác 1:1 công thức chiến đấu / trồng trọt / thu hoạch / mua bán / nâng cấp / kỹ năng (kèm hoạt ảnh tấn công, hiệu ứng va chạm, thanh máu, popup) theo đúng Class.java:line gốc.
  ```
- **Lượt 3C — AI đối thủ, Điều kiện thắng/thua & Màn chơi**:
  ```text
  Dựa trên mã decompile của games/<slug>/analysis/, hãy port đầy đủ toàn bộ các màn chơi chiến dịch, AI đối thủ (không tự sát bất hợp lý), dialog cốt truyện gốc từ file text trong JAR, và điều kiện thắng/thua + lưu tiến trình localStorage.
  ```

---

## Chặng 4: Hoàn thiện, Kiểm thử & Build Portal

```text
Hoàn thiện games/<slug>/web-port/:
1. Đảm bảo chạy tốt cả trên máy tính (chuột + phím), mobile, và Discord Activity (fallback Canvas 2D nếu CDN bị chặn), đồng thời có đầy đủ chế độ Chơi nhiều người (`multiplayer.js` + `#mp-lobby`, `?mp=<code>`, Host Web Worker, Quad Transport `/api/mp` / `BroadcastChannel` / `ntfy` / MQTT-WSS).
2. Viết bộ unit test games/<slug>/web-port/tests/*.test.mjs kiểm tra: giữ nguyên original/*.jar, giải mã map/sprite/text thành công, đồng bộ multiplayer, không lỗi cú pháp.
3. Chạy node --check, node --test, python3 tools/verify-port-parity.py <slug>, python3 tools/build-portal.py và QA đồng bộ 2 tab rồi xác nhận pass 100%.
```

---

## Prompt đặc biệt: Sửa một game ĐÃ PORT nhưng hiện đang bị lỗi / không giống bản gốc

Dùng prompt này cho các game đã có sẵn khung (`ancient-empires-2`, `green-farm-3`, `total-tournament`):

```text
Game games/<slug>/web-port/ hiện đang chạy sai và không giống bản gốc trong games/<slug>/original/*.jar.
Đọc docs/J2ME_DECOMPILE_FIDELITY_GUIDE.md và .agents/rules/j2me-port-fidelity.md.
1. Đối chiếu games/<slug>/web-port/ hiện tại với mã decompile trong games/<slug>/analysis/ (nếu thiếu bytecode/decompile thì chạy `python3 tools/prepare-j2me-evidence.py <slug>` trước).
2. Liệt kê rõ những chỗ bản web-port hiện tại đang tự bịa / thiếu asset gốc / sai công thức so với Java gốc.
3. Thay thế từng phần bằng code port trực tiếp từ Java gốc (ưu tiên: 1. Giải mã đúng sprite/map/animation gốc → 2. Render 1:1 → 3. Gameplay & công thức gốc), ghi rõ comment `// Port of Class.java:line`, rồi verify trên localhost + `python3 tools/build-portal.py`.
```
