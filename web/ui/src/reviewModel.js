export function needsAttention(row) {
  return row.needs_attention === true || row.verdict === 'needs_review';
}

export function proposalState(row) {
  return row.state || row.status || 'proposed';
}

export function applicableProposal(row) {
  return ['proposed', 'pending'].includes(proposalState(row)) && ['exclude_preorder', 'exclude_order'].includes(row.action);
}

export function notesForRow(proposals, row) {
  return proposals.filter(item => item.order_id === row.order_id && (!item.sku || item.sku === row.sku));
}

export function filterEvidence(rows, search, onlyAttention) {
  const needle = search.trim().toLocaleLowerCase('vi');
  return rows.filter(row => (!onlyAttention || needsAttention(row)) && JSON.stringify(row).toLocaleLowerCase('vi').includes(needle));
}

export const reviewFieldLabels = {
  crm_quantity: 'Số lượng CRM', crm_net: 'Giá trị CRM', revenue_quantity: 'Số lượng đã ghi nhận',
  revenue_net: 'Doanh thu đã ghi nhận', cogs: 'Giá vốn', open_quantity: 'Số lượng còn mở',
  open_net: 'Giá trị còn mở', crm_present: 'Có trong CRM', preorder_present: 'Có trong Preorder',
  excluded_from_preorder: 'Đã loại khỏi Preorder', approval_date: 'Ngày duyệt', order_value: 'Giá trị đơn',
  invoiced_value: 'Giá trị đã xuất hóa đơn', state: 'Trạng thái đơn', approval_status: 'Trạng thái duyệt',
  delivery_status: 'Trạng thái giao hàng', payment_status: 'Trạng thái thanh toán',
  order_id: 'Mã đơn hàng', sku: 'SKU', as_of: 'Ngày chốt', status: 'Trạng thái', source: 'Nguồn',
};

export function reviewFieldLabel(key) {
  return reviewFieldLabels[key] || key;
}

/** Keep each HTTP request short while an asynchronous, validated workbook builds. */
export async function awaitReviewJob(initial, readJob, {
  timeoutMs = 600_000, intervalMs = 1_500, now = Date.now,
  sleep = milliseconds => new Promise(resolve => setTimeout(resolve, milliseconds)),
  signal, errorMessage = code => code,
} = {}) {
  const deadline = now() + timeoutMs;
  let result = initial;
  const jobId = initial?.job_id;
  while (true) {
    if (signal?.aborted) throw new Error('Đã dừng theo dõi. Tác vụ vẫn có thể chạy; kiểm tra lịch sử báo cáo.');
    if (result?.status === 'completed' && result.report) return result;
    // An idempotent retry can return already-created report metadata directly.
    if (!result?.status && (result?.report || result?.id || result?.report_id)) return result;
    if (result?.status === 'failed') throw new Error(errorMessage(result.error) || 'Chưa thể hoàn tất bản Draft mới.');
    if (result?.status !== 'running' || !jobId) throw new Error('Phản hồi xử lý chưa hợp lệ. Kiểm tra lịch sử báo cáo trước khi thử lại.');
    const remaining = deadline - now();
    if (remaining <= 0) throw new Error('Chưa nhận được kết quả sau 10 phút. Tác vụ có thể vẫn đang chạy; kiểm tra lịch sử báo cáo trước khi thử lại.');
    await sleep(Math.min(intervalMs, remaining));
    if (signal?.aborted) continue;
    const requestBudget = deadline - now();
    if (requestBudget <= 0) continue;
    result = await readJob(jobId, requestBudget);
  }
}
