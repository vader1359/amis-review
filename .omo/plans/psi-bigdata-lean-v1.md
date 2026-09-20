---
slug: psi-bigdata-lean-v1
status: ready-for-implementation
kind: lean-v1
implementation_started: false
feasibility_spike: complete
supersedes_direction: psi-complete-shared-tool
todo_count: 8
---

# PSI Big-data Lean V1

## Kết quả cần đạt

Biến quy trình PSI hiện tại thành một tool cục bộ, dùng được bởi một operator, chạy bằng một lệnh và tạo workbook PSI đã được kiểm tra độc lập.

V1 được xem là hoàn chỉnh khi một run có thể đi từ manifest nguồn đến `PSI_Final.xlsx`, có log, provenance, lỗi rõ ràng và không cần sửa tay file trung gian. V1 không phải một nền tảng SaaS dùng chung.

Plan này thay hướng triển khai của `psi-complete-shared-tool.md`; không xóa hoặc sửa plan cũ.

Feasibility spike đã hoàn tất mà chưa bắt đầu các Todo nghiệp vụ. Kết quả được ghi tại `.omo/evidence/psi-bigdata-lean-v1/benchmark-spike-2026-08-30.md`.

## Quyết định chống overengineering

- Một package Python, một tiến trình, một CLI; chưa có web server, database hoặc worker queue.
- Polars là engine biến đổi duy nhất. Không dùng pandas.
- XLSX lớn được đọc bằng Calamine qua `fastexcel`, sau đó materialize thành Parquet có schema và content hash.
- Các bước sau chỉ đọc lazy bằng `pl.scan_parquet`; không giữ toàn bộ workbook dưới dạng Python object/list hoặc JSON lớn.
- `openpyxl` chỉ dùng cho `PSI_Manual_Check.xlsx` nhỏ và validator đọc-only; không nằm trên đường xử lý bulk.
- XlsxWriter ghi output theo row-major với `constant_memory=True`; toàn bộ business value được tính trước khi render.
- NumPy chỉ phục vụ kiểm tra số và benchmark; không tạo thêm một data engine.
- Không thêm DuckDB ở V1. Chỉ mở ADR sau profiling nếu một bottleneck cụ thể không đạt gate và DuckDB cải thiện tối thiểu 20% mà vẫn giữ parity.

### Vì sao V1 chưa dùng database

V1 là batch một operator: đọc một bộ source theo kỳ, tạo các relation bất biến rồi xuất một workbook. Khoảng 95 nghìn business rows hiện tại không cần database server; đưa dữ liệu qua một DB còn thêm bước import, schema migration, locking, backup và đồng bộ mà chưa tạo giá trị cho output.

Parquet là persistent analytical storage của V1, còn `run-manifest.json` giữ provenance. Database không bị loại vĩnh viễn; chỉ thêm đúng lúc có state/query problem:

- Thêm SQLite cho run catalog, approval/mismatch workflow hoặc truy vấn lịch sử trên một máy.
- Thêm PostgreSQL/Supabase khi có từ hai operator, shared deployment hoặc quyền truy cập theo người dùng.
- Cân nhắc DuckDB khi cần query nhiều kỳ trực tiếp trên nhiều Parquet hoặc profiling chứng minh Polars không đạt performance gate.

Database không được đặt vào đường tính toán V1 chỉ để gọi giải pháp là “big data”.

## Luồng dữ liệu

```text
manifest.toml + immutable XLSX inputs
  -> schema/header validation
  -> fastexcel/Calamine
  -> normalized typed Parquet cache
  -> Polars lazy transforms + PSI rules
  -> 17 relation Parquet files + run-manifest.json
  -> XlsxWriter PSI_Draft.xlsx
  -> independent validator
  -> atomic promotion of the same validated bytes to PSI_Final.xlsx
```

Mỗi run nằm trong một thư mục riêng do operator chọn:

```text
<output-root>/<run-id>/
  input-manifest.toml
  cache/*.parquet
  relations/*.parquet
  PSI_Draft.xlsx
  PSI_Final.xlsx
  run-manifest.json
  validation-report.json
  run.log
```

Tool không sửa, đổi tên hoặc di chuyển source workbook.

## Input contract

Manifest phải khai báo đường dẫn chính xác, sheet/header row, kỳ dữ liệu và SHA-256 cho:

1. Product master.
2. CRM Sales Order, gồm header và product lines theo cấu trúc nguồn được duyệt.
3. Revenue.
4. Inventory.
5. Purchase/PO.
6. Target.
7. `PSI_Manual_Check.xlsx`.
8. Prior PSI baseline để xác định mismatch `NEW` và release parity.

Nguồn fresh bắt buộc theo kỳ là Product, CRM Sales Order, Revenue và Inventory. Purchase/Target chỉ được dùng lại khi manifest khai báo rõ nguồn carry-forward đã duyệt và hash của file. `Pre order feedback.xlsx`, MISA accounting, CRM activities và PSI cũ ngoài baseline là reference-only, không được tham gia tính toán.

Ba điểm lịch sử phải được khóa thành contract test ở Todo 1, không được tự suy đoán trong code:

- Inventory signed quantity: thống nhất thứ tự aggregate theo canonical SKU/warehouse rồi mới áp điều kiện tồn khả dụng, hoặc quyết định khác được owner duyệt.
- Purchase/Target: thống nhất khi nào là fresh-required và khi nào carry-forward được phép.
- Permanent exclusion: thống nhất ý nghĩa `Effective To`/expiry đối với rule permanent.

Khuyến nghị mặc định để owner duyệt: aggregate signed inventory trước khi lọc; carry-forward phải có flag + file hash + lý do; permanent exclusion không tự hết hạn nếu không có quyết định thay thế rõ ràng.

Các rule đã khóa phải giữ nguyên:

- Preorder identity là `Order ID + canonical SKU`.
- Whole-order exclusion dùng `EXCLUDE ORDER FROM PSI` và áp dụng cho toàn bộ PSI business sheets.
- `IGNORE MISMATCH` chỉ ẩn trình bày, không thay business data.
- Mismatch identity là `Source + Key + Issue`; so với prior PSI để gắn `NEW`.

## Phạm vi file dự kiến

```text
pyproject.toml
uv.lock
src/psi_tool/
  cli.py
  contracts.py
  ingest.py
  transform.py
  rules.py
  workbook.py
  validate.py
  bench.py
tests/psi_tool/
  fixtures/
  test_contracts.py
  test_ingest.py
  test_rules.py
  test_workbook.py
  test_e2e.py
docs/psi_tool_v1/
  contract.md
  runbook.md
```

Các rule đã kiểm chứng trong `psi_engine/manual_check.py` và `psi_engine/reconcile.py` được tái sử dụng hoặc port có regression test; không viết lại song song rồi giữ hai implementation.

## Work plan

### Todo 1 — Khóa contract và golden truth

**Depends on:** không có.

**Files:** `docs/psi_tool_v1/contract.md`, `src/psi_tool/contracts.py`, `tests/psi_tool/fixtures/`, `tests/psi_tool/test_contracts.py`.

**Deliverable:**

- Manifest schema có exact input path, source role, sheet/header, `as_of`, carry-forward approval và hash.
- Contract cho canonical keys, numeric/date/null handling, 17 sheet, sheet order và header order.
- Ba quyết định TBC phía trên được owner duyệt và chuyển thành test.
- Golden corpus 27-08 chỉ lưu fixture đã loại PII hoặc hash/KPI; không copy raw business data vào Git.
- Baseline KPI được khóa: Revenue 8.733 dòng, quantity 54.623,6, net revenue 94.080.778.768, COGS 38.548.120.433; Inventory 3.157 dòng; Pre-orders 383; excluded 325; mismatch 1.050; new mismatch 19; PSI by Product 4.273.

**Acceptance:** missing source/hash/header, invalid date/numeric hoặc conflicting key đều exit non-zero trước khi tạo Draft.

```bash
rtk proxy uv run pytest tests/psi_tool/test_contracts.py -q
```

### Todo 2 — Tạo package, CLI và benchmark baseline

**Depends on:** Todo 1.

**Files:** `pyproject.toml`, `uv.lock`, `src/psi_tool/cli.py`, `src/psi_tool/bench.py`.

**Deliverable:**

- Project chạy reproducibly bằng `uv`; dependencies tối thiểu gồm `numpy`, `polars`, `fastexcel`, `pyarrow`, `xlsxwriter`, `openpyxl`, `psutil`, `pytest`, `ruff`, `basedpyright`.
- CLI surface cố định: `psi inspect`, `psi build`, `psi validate`, `psi release`, `psi bench`.
- `inspect` chỉ preflight; `build` tạo relations và Draft; `validate` ghi report; `release` chỉ tạo Final khi report PASS vẫn khớp SHA-256 của Draft. Không command nào bỏ qua chuỗi này.
- Đo baseline pipeline cũ theo phase time và peak RSS trước khi tối ưu; không dùng cảm giác để tuyên bố nhanh hơn.
- Structured log không ghi raw customer data, token hoặc full row payload.

**Acceptance:** help/invalid manifest chạy ổn; baseline report có elapsed time, RSS, row count và input hashes.

```bash
rtk proxy uv sync --locked
rtk proxy uv run psi --help
```

### Todo 3 — Fast XLSX ingest và typed Parquet cache

**Depends on:** Todo 2.

**Files:** `src/psi_tool/ingest.py`, `src/psi_tool/contracts.py`, `tests/psi_tool/test_ingest.py`.

**Deliverable:**

- Mỗi adapter đọc đúng sheet, `header_row`, `use_columns` và dtype bằng Calamine/fastexcel.
- Header aliases được khai báo trong contract; không dò fuzzy hoặc tự chọn workbook “mới nhất”.
- Cache key gồm source SHA-256, adapter contract version và normalized schema version.
- Mỗi normalized relation có schema, row count, min/max date, key uniqueness/null report và Parquet hash.
- Cache hit không mở lại XLSX; cache lỗi hoặc contract version đổi thì rebuild đúng relation.

**Acceptance:** source không thay đổi không bị ghi; cùng input tạo cùng normalized relation hashes; malformed workbook fail closed.

```bash
rtk proxy uv run pytest tests/psi_tool/test_ingest.py -q
```

### Todo 4 — Port business rules sang Polars

**Depends on:** Todo 3.

**Files:** `src/psi_tool/transform.py`, `src/psi_tool/rules.py`, `tests/psi_tool/test_rules.py`.

**Deliverable:**

- Normalize canonical SKU/order/customer keys, dates, signed quantity và tiền theo contract.
- Joins, anti-joins, group-bys và dedupe chạy bằng Polars expressions/lazy frames; không row-loop Python trên bulk data.
- Tích hợp Manual Check hiện có: SKU mapping, whole-order exclusion, permanent preorder identity và mismatch ignore.
- Business decimal/rounding không đi qua binary float nếu ảnh hưởng kết quả tiền.
- Rule order rõ ràng và được ghi vào `rule_version`.

**Acceptance:** fixture bao phủ canonical mapping, order exclusion, permanent preorder, duplicate/conflict và invalid-value failure; parity với rule hiện tại.

```bash
rtk proxy uv run pytest tests/psi_tool/test_rules.py -q
```

### Todo 5 — Tạo 17 release relations và provenance

**Depends on:** Todo 4.

**Files:** `src/psi_tool/transform.py`, `tests/psi_tool/test_e2e.py`.

**Deliverable:**

- Tạo đúng 17 relation theo sheet contract, gồm CRM Final, Revenue, Inventory, Purchase, Pre-orders, mismatches/new mismatches, PSI by Product và các sheet còn lại đã khóa ở Todo 1.
- Áp whole-order exclusion trước mọi business sheet; `IGNORE MISMATCH` chỉ tác động view relation tương ứng.
- Ghi `relations/*.parquet` và `run-manifest.json` với source hashes, relation hashes, row counts, totals, rule/contract version và phase timings.
- Relation sort order cố định để output và semantic hash ổn định.

**Acceptance:** golden KPI khớp toàn bộ, 17 relation đủ schema và cùng run lặp lại cho cùng semantic hashes.

```bash
rtk proxy uv run pytest tests/psi_tool/test_e2e.py -q -k relations
```

### Todo 6 — Render workbook bằng XlsxWriter

**Depends on:** Todo 5.

**Files:** `src/psi_tool/workbook.py`, `tests/psi_tool/test_workbook.py`.

**Deliverable:**

- Ghi đúng 17 sheet, thứ tự sheet/header, formats, freeze panes, widths và 8.546 công thức theo contract.
- Dùng `constant_memory=True` và ghi row-major; không dùng Excel Table hoặc merge sau khi đã stream data.
- Công thức có cached value khi contract yêu cầu; workbook không làm business aggregation thay engine.
- Set document properties ổn định; tạo `PSI_Draft.xlsx` rồi đóng file hoàn toàn trước validator.

**Acceptance:** package XLSX mở được, đúng 17 sheet và 8.546 formula pattern; peak memory không tăng tuyến tính theo số cell output.

```bash
rtk proxy uv run pytest tests/psi_tool/test_workbook.py -q
```

### Todo 7 — Independent validator và release fail-closed

**Depends on:** Todo 6.

**Files:** `src/psi_tool/validate.py`, `src/psi_tool/cli.py`, `tests/psi_tool/test_workbook.py`, `tests/psi_tool/test_e2e.py`.

**Deliverable:**

- Validator đọc file đã đóng bằng `zipfile` và `openpyxl(read_only=True, data_only=False)`; không tái sử dụng transform result trong RAM làm bằng chứng.
- Kiểm tra ZIP/package integrity, 17 sheet/order/header, keys, row counts, totals, formula count/pattern, cached values và không có formula error đã biết.
- `psi release` chỉ promote đúng bytes của Draft đã PASS; ghi Draft/Final SHA-256 vào report và dùng atomic rename/copy trong cùng run directory.
- Validation fail giữ Draft để điều tra nhưng không tạo Final; exit code và lỗi chỉ rõ source/sheet/key đã mask.

**Acceptance:** corrupt workbook, thiếu sheet, sai KPI hoặc formula pattern đều bị chặn; PASS tạo Final có cùng SHA-256 với Draft đã validate.

```bash
rtk proxy uv run pytest tests/psi_tool/test_workbook.py tests/psi_tool/test_e2e.py -q -k 'validate or release'
```

### Todo 8 — E2E, performance gate và operator handoff

**Depends on:** Todo 7.

**Files:** `src/psi_tool/bench.py`, `tests/psi_tool/test_e2e.py`, `docs/psi_tool_v1/runbook.md`.

**Deliverable:**

- Chạy synthetic fixture và approved corpus theo đúng CLI thật, không gọi internal function trực tiếp.
- Benchmark một warm-up và 5 measured runs; ghi riêng XLSX ingest, Parquet materialize, transform, workbook và validation.
- Mở Final bằng Microsoft Excel thật, recalculate và xác nhận không có repair/error warning.
- Runbook một trang: chuẩn bị manifest, inspect, build, validate/release, đọc lỗi và xóa cache an toàn.

**Performance gate trên corpus hiện tại khoảng 95 nghìn business rows:**

- Mỗi cold XLSX-to-Final run không quá 60 giây và median không quá 50% baseline cũ.
- Mỗi warm Parquet-to-Final run không quá 30 giây.
- Peak RSS không quá 1,5 GiB.
- Cả 5 runs có cùng relation hashes, semantic workbook hash và KPI.
- Không báo p95 từ chỉ 5 mẫu.

Nếu gate không đạt: profile theo phase trước. Chỉ đề xuất DuckDB bằng ADR khi chỉ ra query/bottleneck cụ thể, parity vẫn xanh và cải thiện ít nhất 20%; không thêm engine vì dự đoán.

```bash
rtk proxy uv run pytest tests/psi_tool -q
rtk proxy uv run psi bench --manifest <approved-manifest> --runs 5
```

## Global quality gate

Các lệnh này chỉ chạy sau khi Todo tương ứng đã tạo file:

```bash
rtk proxy uv sync --locked
rtk proxy uv run ruff check src tests
rtk proxy uv run basedpyright src tests
rtk proxy uv run pytest -q
rtk proxy uv run psi inspect --manifest <approved-manifest>
rtk proxy uv run psi build --manifest <approved-manifest> --out <output-root>
rtk proxy uv run psi validate <output-root>/<run-id>/PSI_Draft.xlsx
rtk proxy uv run psi release <output-root>/<run-id>/PSI_Draft.xlsx
```

## Definition of Done

- Một operator tạo được Final từ manifest bằng CLI, không sửa source hoặc file trung gian.
- Invalid/missing/conflicting input fail trước Final và có lỗi hữu ích.
- Đúng 17 sheet, golden KPI, 8.546 công thức và Manual Check semantics.
- Independent validator PASS và Draft/Final hash chứng minh release không regenerate.
- Cold/warm/RSS/determinism gates đạt trên corpus approved.
- Source/hash/rule/relation/output provenance nằm trong run directory.
- Tất cả lint, typecheck và test pass; Excel native mở không repair.
- Không có pandas, DuckDB, web, Supabase, auth, queue hoặc cloud dependency trong V1.

## Hoãn sang Phase 1.1/2

- Local drag-and-drop web UI; chỉ cân nhắc sau khi CLI core ổn định và operator xác nhận cần UI.
- Multi-user upload, shared dashboard, auth/RBAC và mismatch workflow database.
- Supabase/object storage, job queue, notification và concurrent workers.
- Deployment service, backup/retention, KMS/WORM và disaster recovery.
- DuckDB/lakehouse/Iceberg/Delta hoặc distributed processing.
- AI classification hoặc auto-approval.

## Start condition

Implementation chỉ bắt đầu sau khi owner duyệt ba quyết định TBC ở Todo 1 và chỉ rõ approved corpus/output root. Trước thời điểm đó plan là artifact duy nhất; product code không thay đổi.
