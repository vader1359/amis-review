/** Bound both upload and response decoding so a browser file-read cannot freeze the UI. */
export async function requestJson(path, { timeoutMs = 90_000, ...options } = {}, messages = {}) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(path, { ...options, signal: controller.signal });
    const data = await response.json();
    if (!response.ok) throw new Error(messages[data.error || data.detail] || 'Không xử lý được yêu cầu. Kiểm tra file và thử lại.');
    return data;
  } catch (failure) {
    if (controller.signal.aborted) {
      throw new Error(path === '/api/drafts'
        ? 'Chưa nhận được kết quả sau 10 phút. Tác vụ có thể vẫn đang xử lý; chờ rồi thử lại.'
        : 'Yêu cầu mất quá lâu. Kiểm tra file có đọc được trên máy, tải lại trang rồi thử lại.');
    }
    if (failure instanceof TypeError) throw new Error('Không đọc hoặc gửi được file. Kiểm tra file trên máy và kết nối rồi thử lại.');
    throw failure;
  } finally {
    clearTimeout(timer);
  }
}
