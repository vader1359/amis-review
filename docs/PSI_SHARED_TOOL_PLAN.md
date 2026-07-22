# PSI Shared Transparency Tool — Implementation Plan

## 1. Mục tiêu

Xây một tool dùng chung cho tất cả team để:

1. Upload các file export theo từng team và từng kỳ dữ liệu.
2. Tự động kiểm tra schema, chuẩn hóa dữ liệu và chạy bộ rule PSI.
3. Không hiển thị lại các lỗi đã được xác định/đã xử lý.
4. Highlight các mismatch mới để team xử lý ngay.
5. Cho mọi người xem được trạng thái chung, lịch sử thay đổi và nguồn dữ liệu đang được sử dụng.
6. Sinh ra file `PSI Final.xlsx` có thể download và sử dụng trực tiếp.

## 2. Nguyên tắc vận hành

- **Shared visibility:** mọi thành viên được xem dashboard, source status, mismatch và các bản PSI đã phát hành.
- **Team ownership:** mỗi team chỉ upload và cập nhật source thuộc team mình.
- **Immutable snapshot:** file upload không bị ghi đè; mỗi file là một version có thể truy vết.
- **Reporting period khác upload time:** kỳ dữ liệu và thời điểm upload là hai thông tin riêng.
- **Draft trước Final:** upload mới tạo PSI Draft; chỉ sau khi qua quality gate/review mới phát hành PSI Final.
- **Auditability:** không xóa lịch sử upload, xử lý mismatch, rule version hoặc người phát hành.

## 3. Giao diện chính

### 3.1 Shared Dashboard

Dashboard là màn hình mặc định, gồm:

- PSI Final mới nhất: kỳ dữ liệu, version, thời điểm phát hành, người phát hành, nút Download.
- Release readiness: đủ/thiếu source, source nào stale, còn mismatch blocking nào.
- Team status: từng team đã upload chưa, upload lần cuối, kỳ dữ liệu, trạng thái xử lý.
- New mismatch board: case mới, severity, owner, SLA, trạng thái.
- Source matrix: team × source type × reporting period × version đang được chọn.
- Activity feed: upload, chạy đối soát, assign, resolve, approve, publish.

### 3.2 Team Upload Workspace

Form upload cần có:

- Team và source type.
- Reporting period, ví dụ `2026-07`.
- `Data as of` — ngày dữ liệu thực tế.
- File export.
- Ghi chú ngắn và tuỳ chọn đánh dấu source thay thế version trước.

Sau upload, hiển thị ngay:

- Tên file, kích thước, checksum, người upload, thời điểm upload.
- Preview header và số dòng.
- Cột thiếu hoặc sai schema.
- Batch processing status.
- Link tới các mismatch được phát hiện.

### 3.3 Mismatch Detail

Mỗi mismatch phải có:

- Source, reporting period, record key/SKU/order key.
- Giá trị từ từng hệ thống và phần diff.
- Rule phát hiện.
- Severity: blocking, warning hoặc informational.
- Owner, comment, evidence/file reference.
- Trạng thái: `New`, `Assigned`, `In progress`, `Resolved`, `Known`, `Ignored`, `Reopened`.
- Lịch sử xử lý.

## 4. Upload khác thời điểm

Mỗi file được lưu như một `SourceSnapshot` độc lập, không ghi đè file cũ.

Ví dụ một kỳ có các version sau:

| Source | Team | Data as of | Uploaded at | Version | Đang dùng |
|---|---|---:|---:|---:|---|
| Sales | Sales | 2026-07-31 | 09:00 | v3 | Có |
| Inventory | Warehouse | 2026-07-31 | 14:00 | v2 | Có |
| Finance | Finance | 2026-07-31 | 16:30 | v5 | Có |

Mỗi upload sẽ kích hoạt một reconciliation run và tạo PSI Draft mới. Draft phải lưu chính xác version source đã dùng. Nếu có source mới sau khi Final đã phát hành, hệ thống tạo draft tiếp theo và cảnh báo cần review; không âm thầm thay đổi file Final cũ.

## 5. Quyền truy cập

- `Viewer`: xem toàn bộ và download PSI.
- `Contributor`: upload source của team mình, xem kết quả.
- `Reviewer`: assign, xử lý và resolve mismatch; duyệt PSI Draft.
- `Admin`: quản lý team, rule, known issue và phát hành PSI Final.

Mọi người có quyền xem chung, nhưng thao tác thay đổi phải được giới hạn theo role/team.

## 6. Luồng xử lý dữ liệu

```text
Upload source
  -> Validate file/schema
  -> Store immutable snapshot
  -> Normalize records
  -> Run reconciliation rules
  -> Match known/resolved fingerprints
  -> Create New mismatch board
  -> Generate PSI Draft
  -> Reviewer quality gate
  -> Publish PSI Final.xlsx
  -> Notify and retain audit trail
```

## 7. Mô hình dữ liệu tối thiểu

- `Team`
- `User`
- `ReportingPeriod`
- `UploadBatch`
- `SourceSnapshot`
- `NormalizedRecord`
- `Rule` và `RuleVersion`
- `KnownIssue`
- `Mismatch`
- `ResolutionHistory`
- `PSIRelease`
- `ActivityLog`

Mismatch cần có fingerprint ổn định từ rule + source + period + record key + normalized values, để lỗi cũ không quay lại như mismatch mới sau mỗi lần upload.

## 8. PSI Final output

Mỗi `PSIRelease` phải lưu:

- File `PSI Final.xlsx`.
- Reporting period.
- Danh sách source snapshot/version đã sử dụng.
- Rule version.
- Tổng số dòng và KPI chính.
- Checksum file.
- Người duyệt và người phát hành.
- Thời điểm phát hành.

File final phải giữ cấu trúc sheet PSI đang sử dụng và mở được bằng Excel không lỗi công thức hoặc format.

## 9. Quality gate phát hành

Không cho phát hành PSI Final khi:

- Thiếu source bắt buộc.
- Source đang stale quá ngưỡng của kỳ dữ liệu.
- Còn mismatch `blocking` chưa được resolve/known-approved.
- File không đạt schema hoặc không sinh được workbook hợp lệ.

Mismatch `warning` hoặc `informational` được phép tồn tại nếu có trạng thái và lý do rõ ràng.

## 10. Kế hoạch triển khai

### Phase 1 — Foundation

- Tách logic đối soát hiện có trong `web/server.py` thành engine có input/output rõ ràng.
- Chuẩn hóa taxonomy lỗi, record key và fingerprint.
- Chốt template `PSI Final.xlsx`.
- Viết test từ các file mẫu và workbook hiện có.

### Phase 2 — Shared workspace

- Thêm database và object storage.
- Thêm Team, User, ReportingPeriod, SourceSnapshot và UploadBatch.
- Xây Shared Dashboard, Team Upload Workspace và source version history.

### Phase 3 — Review workflow

- Xây Mismatch Board, assignment, comments, resolution và known issue.
- Thêm reconciliation run bất đồng bộ và trạng thái tiến trình.
- Thêm release gate và PSI Draft.

### Phase 4 — PSI release

- Sinh `PSI Final.xlsx` theo template.
- Lưu release metadata, checksum và source provenance.
- Download, version comparison và activity timeline.

### Phase 5 — Production hardening

- Notification cho source mới, mismatch blocking và PSI release.
- Backup, retention, monitoring, permission audit.
- Pilot với 1–2 team rồi mở rộng toàn bộ.

## 11. Definition of Done cho MVP

- Hai team có thể upload cùng một reporting period ở hai thời điểm khác nhau.
- Hệ thống giữ được cả hai lịch sử upload và biết version nào đang được dùng.
- Mọi người xem được cùng một dashboard transparency.
- Mismatch mới được highlight; lỗi đã known/resolved không bị lặp lại.
- Reviewer xử lý được mismatch và quality gate chặn release khi còn lỗi blocking.
- Tạo được `PSI Final.xlsx`, download được và mở/sử dụng được trong Excel.
- Có thể truy ngược PSI Final về source files, rule version và người phát hành.
