# Rà soát sau xuất PSI

Mở báo cáo đã lưu hoặc tạo Draft để dùng bảng **Rà soát sau xuất báo cáo**.

- **Mismatch và lý do**: điều kiện đối soát, bằng chứng nguồn và hướng kiểm tra.
  Nhận xét AI là giả thuyết; không thay thế kết luận Kế toán.
- **Khác biệt so với kỳ trước**: đối chiếu đúng PSI Final đã chọn và kiểm tra SHA,
  ngày, cấu trúc trước khi so sánh. Liệt kê cả thay đổi bình thường của đơn hoàn
  thành. Nếu thiếu bản đối chiếu, không tự coi tất cả đơn là mới.
- **Kiểm tra Preorder**: định danh Order ID + canonical SKU; cộng các dòng cùng
  định danh, kiểm tra số lượng/giá trị còn mở và hiển thị các điểm cần xác minh.
- **Ghi chú và đề xuất kế toán**: lưu online trên Neon, có phiên bản và lịch sử.
  Chọn ghi chú, loại đúng dòng Preorder, hoặc loại toàn bộ đơn khỏi các sheet
  nghiệp vụ PSI. Phải xác nhận phạm vi trước khi tạo bản chỉnh sửa.

Các đề xuất chưa áp dụng không thay đổi dữ liệu. Khi xác nhận, hệ thống tạo một
bản Manual Check riêng, chạy lại quy trình đối soát độc lập, Parquet và kiểm định
Excel 17 sheet. Bản gốc được giữ nguyên. Quyết định đã áp dụng được nạp lại từ
Neon cho các kỳ sau theo ngày hiệu lực, kể cả khi nguồn Manual Check được tải lên
chưa chứa quyết định online. Không tự đổi Draft thành PSI Final.

Tên người ghi nhận và xác nhận hiện là tên tự khai trong tài khoản dùng chung,
không phải danh tính đã xác minh riêng cho từng nhân viên.

## Vận hành

- Migration: `infra/sql/psi_preview_reviews.sql`; thử trên nhánh QA trước khi
  áp dụng vào nhánh preview. Quyền ứng dụng chỉ SELECT/INSERT trên bảng sự kiện.
- Nguồn báo cáo được giữ riêng, bất biến, trong `PSI_REPORT_SOURCE_DIR` trên
  Ian's Win. Báo cáo cũ thiếu đủ bộ nguồn vẫn xem/ghi chú được nhưng không xuất lại.
- Bản báo cáo, sự kiện áp dụng và khóa giao dịch dùng chung một giao dịch Neon.
  Nếu lưu nguồn hoặc sự kiện thất bại, báo cáo mới không được commit; có thể còn
  file riêng chưa được tham chiếu để dọn sau. Không sửa/xóa báo cáo cũ.
- Tạo bản chỉnh sửa chạy nền; trình duyệt theo dõi trạng thái bằng TanStack Query,
  tránh thời gian chờ của proxy. Dịch vụ hiện chạy một tiến trình. Khởi động lại
  giữa tác vụ có thể mất trạng thái theo dõi; kiểm tra lịch sử và gửi lại cùng
  yêu cầu. Khóa và mã yêu cầu chống áp dụng trùng ở database.
- AI chạy phía máy chủ qua 9router (`PSI_AI_BASE_URL`, `PSI_AI_MODEL`,
  `PSI_AI_API_KEY`). Không gửi khóa tới trình duyệt. Chỉ gửi loại vấn đề, số liệu
  và trạng thái cho phép; thay ID bằng mã tạm, bỏ mã đơn/SKU/tên khách/ghi chú tự do.
  Mỗi phản hồi được gắn với bằng chứng được yêu cầu; lỗi AI không chặn bảng đối soát.

## Kiểm chứng

Kiểm tra đơn vị bao phủ đối chiếu Final, thay đổi của đơn hoàn thành, quy tắc
Preorder, kiểm tra phạm vi, xung đột phiên bản, gửi lại yêu cầu, rollback giao dịch,
giữ quyết định qua các kỳ, tác vụ nền và lọc dữ liệu trước khi gửi AI. Bộ dữ liệu
03/09 đối chiếu Final 27/08 cho 1.054 mismatch, 125 thay đổi, 37 Preorder mới và
13 Preorder có điểm cần kiểm tra. Kết quả kiểm định thực tế nằm trong bằng chứng
QA riêng của phiên làm việc; các con số này không phải số liệu cố định của UI.
