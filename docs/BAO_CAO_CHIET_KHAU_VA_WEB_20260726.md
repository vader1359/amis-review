# PSI — Lỗi logic chiết khấu & tình trạng web online

Ngày: 2026-07-26 · Phạm vi: `psi_engine/engine.py` (sheet **Revenue final**) và bản deploy Vercel `amis-review`

---

## 1. Lỗi logic chiết khấu — đã xác nhận và đã sửa

### Nguyên nhân

Công thức **Net Revenue** được sinh ra trong `psi_engine/engine.py` (khối tạo sheet `Revenue final`):

```python
# SAI
f"=R{row_no}-MAX(0,U{row_no})-X{row_no}-Y{row_no}"
```

`MAX(0, U)` ép cột **Chiết khấu** về 0 mỗi khi giá trị âm. Trên hóa đơn điều chỉnh / trả hàng, chiết khấu âm là giá trị hợp lệ (đảo lại chiết khấu đã ghi ở hóa đơn gốc), nên việc ép về 0 làm mất phần hoàn lại → doanh thu bị ghi âm quá mức.

```python
# ĐÚNG — giữ nguyên dấu Kế toán
f"=R{row_no}-U{row_no}-X{row_no}-Y{row_no}"
```

Đúng theo quy tắc đã ghi trong `PSI checks`:
`Net Revenue = Doanh số bán − Chiết khấu − Giá trị trả lại − Giá trị giảm giá (giữ dấu Kế toán)`

### Mapping cột đã kiểm chứng

Đọc trực tiếp header dòng 4 của `input/So_chi_tiet_ban_hang 01.01.2023 đến 09.07.26.xlsx`:

| Cột | Index | Tên |
|-----|-------|-----|
| R | 17 | Doanh số bán |
| U | 20 | Chiết khấu |
| X | 23 | Giá trị trả lại |
| Y | 24 | Giá trị giảm giá |

### Kiểm chứng bằng số liệu thật

Chạy lại đúng bộ lọc của engine (TK Nợ/Có ∈ {5111, 5112, 5113}, loại `KHÔNG PHẢI REVENUE`) trên file sổ chi tiết bán hàng:

| Năm | Dòng revenue | Dòng Chiết khấu < 0 | Doanh thu bị ghi âm quá mức |
|-----|--------------|---------------------|------------------------------|
| 2023 | 2.975 | 2 | 183.372 đ |
| 2024 | 2.337 | 0 | 0 |
| 2025 | 4.044 | **19** | **82.271.779 đ** |
| 2026 | 1.814 | 0 | 0 |
| **Tổng** | **11.170** | **21** | **82.455.151 đ** |

Con số 2025 (82.271.779 đ / 19 dòng) khớp với mức lệch 82.271.782 đ mà Kế Toán báo — chênh lệch nhỏ do bản export dùng để đối chiếu khác ngày. Kết luận: **lỗi nằm ở logic tạo PSI**, không phải MISA thiếu dữ liệu chiết khấu, cũng không phải Kế Toán kiểm tra sai.

### Đã sửa ở đâu

| File | Thay đổi |
|------|----------|
| `.codex-tmp/next-deploy-20260722/psi_engine/engine.py:152` | bỏ `MAX(0, …)` |
| `.codex-tmp/preorder-contract-patch-20260722/psi_engine/engine.py:154` | bỏ `MAX(0, …)` |
| `.codex-tmp/preorder-contract-patch-20260722/tests/test_workbook_export.py` | cập nhật assert + thêm test chặn tái phát (`MAX(` không được xuất hiện ở cột Net Revenue) |

Đã chạy lại engine trên bộ fixtures: công thức ra `=R2-U2-X2-Y2`, `=R3-U3-X3-Y3`, không còn dòng nào bị clamp.

### Áp lên source đang chạy

Source thật của app nằm ở máy Linux/WSL — `deploy/psi-tool.service` trỏ tới `/home/iant1359/develop/amis-review-psi-mvp`, và thư mục `amis-review` trên Mac **không có** `psi_engine/engine.py`. Dùng patch kèm theo:

```bash
cd ~/develop/amis-review-psi-mvp
git apply /path/to/discount-sign-fix-20260726.patch
# hoặc sửa tay:
sed -i 's/-MAX(0,U{row_no})-/-U{row_no}-/' psi_engine/engine.py
sed -i 's/=R2-MAX(0,U2)-X2-Y2/=R2-U2-X2-Y2/' tests/test_workbook_export.py
```

Sau khi apply: build lại PSI của kỳ đang mở rồi đối chiếu 19 dòng 2025 với file KT check — variance phải về 0 (trừ `NBL2621WD` còn lệch ~3d do làm tròn ở nguồn MISA, không phải lỗi logic).

---

## 2. Web online cho các team submit — chẩn đoán

### Hiện trạng deploy

- Vercel project `amis-review` (scope `tech-nano-usm`), **không nối Git** → deploy bằng Vercel CLI.
- Next.js UI (`app/page.js`) + 1 route Node (`/api/upload-url`) + 4 function Python bọc `web/server.py`: `weekly_status`, `weekly_upload_staged`, `mismatch`, `release`.
- Supabase làm auth + DB + Storage.

**Site vẫn sống, không phải chết deploy:** `GET /` trả 200 ("NanoHome PSI Shared Tool"), `GET /api/weekly_status` trả **401** (function Python chạy, chỉ thiếu bearer token). Nếu function Python không được deploy thì đã là 404.

### Vấn đề chính: bước build PSI quá nặng so với giới hạn của Vercel

Đo thật với 7 file nguồn hiện tại (22 MB), chạy đúng `psi_engine.build()`:

| Chỉ số | Đo được |
|--------|---------|
| Thời gian build | **88,4 s** (trên container ~nhiều vCPU) |
| RAM đỉnh | **1.418 MB** |
| File PSI xuất ra | **28,9 MB** |

Đối chiếu giới hạn Vercel Functions (07/2026, fluid compute):

| Giới hạn | Hobby | Pro |
|----------|-------|-----|
| Max duration | 300 s (mặc định = tối đa, không nâng được) | 300 s mặc định, 800 s tối đa |
| Memory / CPU | 2 GB / 1 vCPU (cứng) | 2 GB mặc định, tối đa 4 GB / 2 vCPU |
| Request **và** response body | 4,5 MB | 4,5 MB |

Suy ra:

1. **Timeout là rủi ro số một.** 88 s đo trên máy nhiều vCPU; Vercel Hobby chỉ **1 vCPU**, cùng khối lượng này dễ thành 3–5 phút → vượt trần 300 s → `504 FUNCTION_INVOCATION_TIMEOUT`. Trần 300 s của Hobby là cứng, `maxDuration: 300` trong `vercel.json` đã là mức cao nhất có thể.
2. **RAM sát trần.** 1,42 GB đo riêng phần build; cộng thêm 22 MB file tải từ Storage và 29 MB file xuất ra trong cùng invocation là đụng 2 GB → `FUNCTION_INVOCATION_FAILED` (OOM).
3. **Không thể trả file PSI qua function.** File 29 MB > 4,5 MB. Chỗ này code đã làm đúng (signed URL từ Storage) — giữ nguyên.
4. Client không có timeout/abort: `app/page.js` gọi `/api/release` rồi `await` không giới hạn → khi function chết, UI treo im, người dùng thấy "web không hoạt động".

### Ba điểm phụ nên xử lý luôn

| Vấn đề | Ảnh hưởng |
|--------|-----------|
| `H.last`, `H.actors`, `H.roles` là class attribute (state trong RAM) | Serverless mỗi lần gọi có thể là instance khác → mất state. Đây là di sản từ thiết kế `ThreadingHTTPServer` chạy 1 process lâu dài. |
| `/api/dashboard` trả **503** khi repository là `SupabaseRepository` | Dashboard vĩnh viễn không dùng được ở bản online (UI Next hiện không gọi endpoint này, nên chưa lộ ra). |
| `/api/download/<token>` chỉ tra `self.actors` trong RAM | Online luôn trả 401. |
| `.vercel/output/builds.json`: lần prebuild cuối lỗi `uv is required but was not found in PATH`, và `.vercel/output/functions/` **không có** function Python nào | Nếu lần tới deploy bằng `vercel deploy --prebuilt` từ máy Mac thì toàn bộ API Python sẽ mất. Cần cài `uv` hoặc luôn để Vercel build trên cloud. |

---

## 3. Đề xuất — theo thứ tự ưu tiên

### (1) Tách "submit" khỏi "build" — quan trọng nhất

Việc team submit file phải luôn nhẹ và không bao giờ kéo theo build:

- **Submit** = xin signed URL → browser upload trực tiếp lên Supabase Storage → ghi 1 dòng vào DB. Không đụng openpyxl nặng, không đụng trần thời gian. (Phần này code đã đúng hướng, chỉ cần tách hẳn khỏi build.)
- **Build PSI** = job bất đồng bộ: bấm "Tạo PSI" chỉ ghi 1 job `queued` rồi trả về ngay; UI poll trạng thái `queued → running → done/failed`; tải kết quả qua signed URL.

Không có bước này thì mọi cách tối ưu khác chỉ dời được thời điểm vỡ.

### (2) Giảm tải chính bản build — đã đo, hiệu quả lớn

File PSI hiện nhúng lại 8 sheet **copy thô** của chính các file nguồn: `Product detail`, `Purchase PO detail`, `Inventory source`, `Pre-order source`, `Revenue raw`, `CRM orders`, `CRM items`, `Target detail`. Bỏ 8 sheet đó (giữ toàn bộ sheet `* final` + `PSI Summary` + `Mismatch` + `Data gaps` + `PO excluded` + `PSI by Product`):

| | Hiện tại | Sau khi bỏ copy thô | Cải thiện |
|---|---|---|---|
| Thời gian | 88,4 s | **28,3 s** | nhanh 3,1× |
| RAM đỉnh | 1.418 MB | **490 MB** | giảm 2,9× |
| File xuất | 28,9 MB | **8,2 MB** | nhỏ 3,5× |

Team vẫn có file gốc trên Storage nên không cần nhúng lại vào PSI. Thêm biên an toàn nữa thì dùng `Workbook(write_only=True)` và stream từng dòng từ nguồn `read_only` sang output, thay vì giữ toàn bộ trong RAM.

### (3) Chọn chỗ chạy build

| Phương án | Ưu | Nhược |
|-----------|-----|-------|
| **A. Worker nội bộ (đã có sẵn)** — `deploy/psi-tool.service` chuyển thành worker poll job từ Supabase, build, upload kết quả, cập nhật trạng thái | Không giới hạn thời gian/RAM; tận dụng hạ tầng đang có; ít việc phải làm nhất | Máy phải bật; cần theo dõi service |
| **B. Container job** — Cloud Run job / Fly.io / Railway / Render, 2–4 GB RAM, timeout 15 phút, kích bằng DB webhook hoặc HTTP; Vercel chỉ enqueue | Ổn định, tự scale, không phụ thuộc máy nội bộ | Thêm 1 hạ tầng + chi phí nhỏ |
| **C. Ở lại Vercel** — Pro + fluid, `maxDuration` 800 s, memory 4 GB, kèm mục (2) | Không đổi hạ tầng | Vẫn có trần; càng nhiều dữ liệu càng sát trần; tốn tiền theo CPU time |

Khuyến nghị: **(2) + (A)** trước — rẻ nhất, dùng đúng thứ đang có, và giải quyết tận gốc cả timeout lẫn OOM. Chuyển sang (B) khi muốn bỏ phụ thuộc máy nội bộ.

### (4) Dọn phần state trong RAM

Chuyển `actors` / `roles` / `last` và `/api/dashboard`, `/api/download` sang đọc từ Supabase, để cùng một code chạy đúng ở cả bản local và bản serverless.

### (5) Chống bẫy prebuilt

Cài `uv` trên máy Mac, hoặc bỏ hẳn thói quen `vercel build` + `--prebuilt`, để Vercel build Python trên cloud.

---

## Nguồn

- [Vercel Functions Limits](https://vercel.com/docs/functions/limitations)
- [Configuring Maximum Duration for Vercel Functions](https://vercel.com/docs/functions/configuring-functions/duration)
- [Configuring Memory and CPU for Vercel Functions](https://vercel.com/docs/functions/configuring-functions/memory)
- [How to bypass the 4.5MB body size limit](https://vercel.com/kb/guide/how-to-bypass-vercel-body-size-limit-serverless-functions)
