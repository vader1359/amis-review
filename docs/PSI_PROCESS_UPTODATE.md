# Quy trình PSI cập nhật

## 1. Phạm vi và kỳ dữ liệu

- Chỉ xử lý dữ liệu từ `2024-01-01` đến ngày chốt kỳ.
- Ngày dùng để lọc CRM là **Ngày duyệt**, không phải Ngày tạo.
- Revenue dùng Ngày hạch toán trong Sổ chi tiết bán hàng.
- Tồn kho dùng trường **Cuối kỳ – Số lượng** (đây là số tồn cuối kỳ, không phải phép trừ).

## 2. File nguồn chính thức

Mỗi kỳ cần bốn file nguồn mới:

1. CRM Sales Order.
2. CRM Product Master.
3. Sổ chi tiết bán hàng.
4. Tổng hợp tồn kho.

Purchase/PO và Target dùng bản đã duyệt trước đó nếu người dùng không cung cấp bản mới. `PSI_Manual_Check.xlsx` là file kiểm soát dùng chung, phải được cập nhật trước khi chạy.

Các file `feedback`, `MISA Accounting`, `CRM Activities`, `old_check` và PSI cũ chỉ dùng để tra cứu bằng chứng hoặc migrate quyết định vào Manual Check. Pipeline không dùng trực tiếp các file này để tạo số liệu hoặc loại dòng.

## 3. Chuẩn hóa và lọc CRM

- Chuẩn hóa mã đơn và SKU: trim, uppercase, sau đó áp dụng các mapping `APPROVED` trong Manual Check.
- Loại khỏi `CRM Final` các đơn có mã bắt đầu bằng `CKHO`.
- Loại đơn chưa duyệt, đã hủy và đơn trước năm 2024.
- Chỉ giữ đơn có Ngày duyệt hợp lệ trong kỳ xử lý.
- `Final CRM Products` lấy đầy đủ các dòng sản phẩm thuộc các đơn còn lại trong `CRM Final`.
- Giá trị sản phẩm phải ưu tiên **Thành tiền sau CK**; nếu file dùng tên cột cũ thì dùng **Tổng tiền**. Không dùng Thành tiền trước chiết khấu.

## 4. Tạo Revenue

Nguồn duy nhất là Sổ chi tiết bán hàng.

```text
NET REV SOLD
  = Doanh số bán
  - Chiết khấu
  - Giá trị trả lại
  - Giá trị giảm giá
```

- `TOTAL QUANTITY SOLD` lấy từ **Tổng số lượng bán**, không dùng `Số lượng bán`.
- `COGS` lấy từ Giá vốn.
- `SALE ORDER` lấy từ Đơn hàng.
- Giữ đúng dấu của các dòng điều chỉnh; không tự chặn chiết khấu âm.
- Dòng FOC/quà tặng/cost-only có thể có COGS nhưng không có doanh thu hoặc số lượng bán. Không đưa dòng này vào doanh thu thuần; phân loại riêng và vẫn giữ COGS.
- Dòng có `COGS > NET REV SOLD` là mismatch cần ghi nhận, không tự loại khỏi Revenue.

## 5. Tạo Inventory

- `WAREHOUSE` lấy từ Mã kho, không lấy Loại hàng hóa hay Nhóm VTHH.
- Loại toàn bộ dòng thuộc các kho: kho lỗi, kho lỗi ảo, kho chưa xuất hóa đơn và kho chị Kathy theo danh sách chuẩn trong Manual Check.
- Chỉ giữ sản phẩm có **Cuối kỳ – Số lượng > 0**. Sản phẩm tồn cuối kỳ bằng 0 hoặc âm được loại khỏi output Inventory.
- Sau đó aggregate theo canonical SKU.

## 6. Tạo Purchase/PO

- Dùng PO/Loading List đã duyệt.
- Giữ các cột theo schema mẫu: `EXW VALUE`, `CURRENCY`, `WAREHOUSE VALUE` và các trường PO liên quan.
- PO chỉ bổ sung cost và hạn giao cho Pre-orders; PO không tự tạo dòng Pre-order.
- `COST TO WH BY PUR (Estimate)` là ước tính khi chưa xác định chắc chắn PO đúng cho đơn/SKU. Không dùng giá trị nhập kho của toàn bộ PO cho một dòng Pre-order.

## 7. Định nghĩa và tạo Pre-orders

Pre-orders **không phải file nguồn** và không được copy nguyên từ feedback hay bất kỳ file tham khảo nào.

```text
Pre-order mở theo ĐH + canonical SKU
  = dòng đã duyệt trong Final CRM Products
  - phần đã ghi nhận trong Revenue
```

Quy tắc:

1. Base line chỉ đến từ `Final CRM Products`.
2. Match Revenue theo `Order ID + canonical SKU`.
3. Số lượng mở = `SL CRM - Tổng số lượng bán Revenue`. Chỉ tạo dòng khi số lượng mở > 0.
4. Giá trị mở dùng giá trị CRM sau chiết khấu trừ phần Revenue tương ứng.
5. Dòng CRM giảm 100% có thể có số lượng mở nhưng giá trị bằng 0; cần phân loại FOC/nội bộ nếu có bằng chứng.
6. SKU mới trong cùng đơn là một case mới, không kế thừa exclusion của SKU khác.

### 7.1. Permanent Exclusion từ Manual Check

`PSI_Manual_Check.xlsx / Preorder Exclusions` là **nguồn exclusion duy nhất** cho mọi kỳ PSI.

Một dòng được loại khỏi Pre-orders vĩnh viễn khi:

- `Status = APPROVED`;
- `Action = EXCLUDE FROM PREORDER`;
- `Disposition` hoặc `Exclusion Type = PERMANENT / DONE`;
- có lý do, bằng chứng, người duyệt và ngày duyệt;
- key khớp theo **Order ID + canonical SKU**.

Các ghi chú KT đã xác nhận hoàn tất như `Done`, hàng tặng/FOC đã xử lý, đã xuất hóa đơn/MISA hoàn tất, hủy/hoàn tiền đã xử lý, đơn nội bộ/Lakeview/Showroom, bảo hành/giao bù/claim hoặc thay mã/gộp mã đã có bằng chứng được chuyển thành `PERMANENT / DONE` và không xuất lại trong Pre-orders các kỳ sau.

`Quantity` và `Net Value` trong Manual Check chỉ là **snapshot audit** tại thời điểm ghi nhận. Chúng không nằm trong fingerprint định danh và không được dùng để mở lại exclusion khi số lượng hoặc giá trị thay đổi ở kỳ sau.

Fingerprint permanent chỉ được tạo từ identity ổn định:

```text
PERMANENT KEY = Order ID + canonical SKU
```

Không đưa Quantity, Net Value hoặc số liệu biến động theo kỳ vào fingerprint permanent. Nếu cùng Order ID xuất hiện SKU mới, SKU mới không bị loại theo exclusion cũ.

Các ghi chú `pending`, `đang đợi`, `sẽ trao đổi`, `chưa kết luận` hoặc chưa có bằng chứng đầy đủ **không** được chuyển thành Permanent Exclusion. Các dòng này giữ lại trong Pre-orders và/hoặc Mismatch để review.

Mỗi lần refresh chỉ cập nhật snapshot audit và Change Log; không thay đổi lý do, bằng chứng hoặc trạng thái Permanent nếu chưa có quyết định mới được phê duyệt.

### 7.2. Loại toàn bộ đơn khỏi PSI

`PSI_Manual_Check.xlsx / Order Exclusions` là nguồn duy nhất cho quyết định loại toàn bộ một đơn khỏi PSI. Rule này dùng cho đơn đã được xác nhận hủy hoặc một trường hợp khác được phê duyệt rõ ràng là không thuộc PSI.

Rule hợp lệ phải có:

- `Status = APPROVED`;
- `Action = EXCLUDE ORDER FROM PSI`;
- `Scope = ALL PSI BUSINESS SHEETS`;
- `Disposition = PERMANENT / DONE`;
- `Order ID`, lý do, bằng chứng, người duyệt và ngày duyệt đầy đủ.

Rule được áp dụng trước khi tạo các sheet và phép tổng hợp. Order ID khớp sẽ bị loại khỏi `CRM Final`, `Final CRM Products`, `Revenue`, `Pre-orders`, `Mismatch` phát sinh từ chính đơn đó và phần đóng góp của đơn trong `PSI by Product`. Dữ liệu nguồn không bị sửa; record vẫn được giữ trong Manual Check để audit.

Không dùng `Preorder Exclusions` để loại cả đơn. Một dòng chỉ có `EXCLUDE FROM PREORDER` không được phép ảnh hưởng đến CRM hoặc Revenue.

## 8. Manual Check và mismatch

- Tạo mismatch từ bốn nguồn chính thức và các phép đối chiếu deterministic.
- `Exceptions` chỉ là audit/note; không tự loại dòng khỏi PSI.
- `IGNORE MISMATCH` chỉ làm thay đổi trạng thái trình bày mismatch; không loại dòng khỏi Revenue, CRM, Inventory hoặc Pre-orders.
- Chỉ `Preorder Exclusions` có `EXCLUDE FROM PREORDER` và đủ điều kiện Permanent ở mục 7.1 mới loại dòng khỏi Pre-orders.
- Chỉ `Order Exclusions` có `EXCLUDE ORDER FROM PSI` và đủ điều kiện ở mục 7.2 mới loại toàn bộ đơn khỏi các sheet nghiệp vụ PSI.
- Các case `OPEN`, `REVIEW_REQUIRED`, `KEEP AS MISMATCH` hoặc `RESOLVED` chưa được phê duyệt Permanent vẫn phải giữ trong mismatch theo quy trình.
- Một số mismatch hợp lệ như lịch sử không còn trong CRM snapshot được ghi chú `historical coverage`, không tự kết luận là lỗi.
- Mỗi lần xuất PSI phải so sánh mismatch với `PSI Final` gần nhất theo khóa ổn định `Source + Key + Issue`. Case chưa có ở kỳ trước được ghi `NEW` trong cột `New since prior PSI` và highlight toàn dòng trên sheet `Mismatch` để ưu tiên review. Highlight chỉ là trạng thái trình bày: không tự loại, không tự chuyển `APPROVED`, và không thay đổi số liệu.

Khi phát sinh lỗi mới:

1. Ghi vào Manual Check với Order ID, canonical SKU, lý do, bằng chứng và trạng thái `OPEN`.
2. Người phụ trách xác minh.
3. Nếu chỉ loại dòng Pre-order, chuyển `APPROVED / EXCLUDE FROM PREORDER / PERMANENT / DONE`.
4. Nếu xác nhận loại cả đơn, ghi rule riêng tại `Order Exclusions` dưới dạng `APPROVED / EXCLUDE ORDER FROM PSI / ALL PSI BUSINESS SHEETS / PERMANENT / DONE`.
5. Chạy validator trước khi rerun PSI.
6. Ghi Change Log; không tạo exclusion rải rác trong PSI cũ, feedback hoặc file tham khảo.

## 9. Output PSI

Giữ đúng schema file PSI mẫu, gồm các sheet chính:

`PSI Summary`, `Checks`, `Sources`, `Mismatch`, `Data gaps`, `PO excluded`, `PSI by Product`, `Brand`, `Category`, `Purchase`, `Inventory`, `Pre-orders`, `Preorder excluded KT`, `Revenue`, `CRM Final`, `Final CRM Products`, `Target`.

`Preorder excluded KT` là audit output của các dòng bị loại theo Manual Check; không phải nguồn độc lập để chạy kỳ sau.

## 10. Release gate

Chỉ xuất PSI khi:

- schema và các cột bắt buộc đã đủ;
- Manual Check validator trả về `PASS`;
- không có fingerprint permanent chứa Quantity/Net Value;
- mọi dòng loại khỏi Pre-orders đều match đúng `Order ID + canonical SKU` và có `PERMANENT / DONE`;
- mọi đơn loại toàn bộ đều có rule `Order Exclusions` hợp lệ và không còn xuất hiện trong CRM, Revenue, Pre-orders, Mismatch hoặc aggregate PSI;
- các mismatch chưa được phê duyệt vẫn hiển thị;
- đã xác định `PSI Final` kỳ trước làm baseline và highlight tất cả mismatch `NEW` theo `Source + Key + Issue`;
- không có lỗi công thức như `#REF!`, `#DIV/0!`, `#VALUE!`, `#NAME?`;
- kiểm tra lại `CRM Final`, `Final CRM Products`, `Revenue`, `Inventory`, `Pre-orders` và `Mismatch` trước khi giao file.

Khoảng 90–95% pipeline phải deterministic bằng code/Power Query. AI chỉ hỗ trợ đọc diễn giải, đề xuất nhóm lỗi hoặc draft evidence; AI không được tự đặt `APPROVED`, tự loại Pre-orders hoặc tự sửa số liệu nguồn.
