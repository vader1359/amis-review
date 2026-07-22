const files = { product: 'Product master', purchase: 'Purchase / PO', revenue: 'Sổ chi tiết bán hàng (MISA)', inventory: 'Inventory', preorder: 'Pre-order feedback (đã ghi nhận)', crm: 'CRM Sale', target: 'Target' };
const team = document.querySelector('#team');
const week = document.querySelector('#week');
const dataAsOf = document.querySelector('#data-as-of');
const checklist = document.querySelector('#checklist');
const message = document.querySelector('#message');
const ready = document.querySelector('#ready');
const download = document.querySelector('#download');
const diagnostics = document.querySelector('#diagnostics');
const releaseButton = document.querySelector('#release');
const loginCard = document.querySelector('#login-card');
const workspace = document.querySelector('#workspace');
const authBadge = document.querySelector('#auth-badge');
let accessToken = '';
let supabaseClient = null;

function headers() { return accessToken ? { Authorization: `Bearer ${accessToken}` } : {}; }
function formData(source, file) { const data = new FormData(); data.append('team_id', team.value); data.append('week', week.value); data.append('data_as_of', dataAsOf.value); data.append('source_type', source); data.append('file', file); return data; }
function escapeHtml(value) { return String(value ?? '').replace(/[&<>"']/g, character => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[character]); }
async function api(path, options = {}) { const request = { ...options, headers: { ...headers(), ...(options.headers || {}) } }; return fetch(path, request); }
function showAuth(authenticated) { loginCard.classList.toggle('hidden', authenticated); workspace.classList.toggle('hidden', !authenticated); authBadge.textContent = authenticated ? 'ĐÃ ĐĂNG NHẬP' : 'YÊU CẦU ĐĂNG NHẬP'; authBadge.className = `ant-tag badge ${authenticated ? 'ant-tag-green' : 'ant-tag-gold'}`; }
async function loadConfig() { const response = await fetch('/api/config'); if (!response.ok) return null; const config = await response.json(); return config.url && config.publishable_key ? config : null; }
async function login(email, password) {
  if (!supabaseClient) { message.textContent = 'Chưa cấu hình Supabase; dùng chế độ xem trước cục bộ.'; return; }
  const result = await supabaseClient.auth.signInWithPassword({ email, password });
  if (result.error) throw result.error;
  accessToken = result.data.session?.access_token || '';
  showAuth(Boolean(accessToken));
  await refresh();
}
async function refresh() {
  const response = await api(`/api/weekly-status?team=${encodeURIComponent(team.value)}&week=${encodeURIComponent(week.value)}`);
  if (!response.ok) { message.textContent = await response.text(); return; }
  const status = await response.json();
  const owned = Array.isArray(status.owned_sources) ? status.owned_sources : Object.keys(files);
  const required = Array.isArray(status.required_sources) ? status.required_sources : owned.filter(source => source !== 'preorder');
  const optional = new Set(Array.isArray(status.optional_sources) ? status.optional_sources : ['preorder']);
  checklist.innerHTML = owned.map(source => { const label = files[source] || source; const item = status.files?.[source] || { status: 'missing' }; const isOptional = optional.has(source); return `<div class="check-item"><div><strong>${label}${isOptional ? ' · tùy chọn' : ''}</strong><small>${item.status === 'uploaded' ? `Đã nộp · phiên bản ${item.version}${isOptional ? ' · chỉ tham chiếu' : ''}` : isOptional ? 'Chưa nộp · không ảnh hưởng PSI Final' : 'Chưa có file'}</small></div><label class="ant-btn ant-btn-default">${item.status === 'uploaded' ? 'Tải lại' : 'Chọn file'}<input type="file" accept=".xlsx" data-source="${source}" hidden></label></div>`; }).join('');
  const isReady = Boolean(status.ready);
  const mismatches = Array.isArray(status.mismatches) ? status.mismatches : [];
  const gateReasons = Array.isArray(status.gate_reasons) ? status.gate_reasons : [];
  const releaseAllowed = status.release_allowed === undefined ? isReady && mismatches.length === 0 : Boolean(status.release_allowed);
  ready.textContent = releaseAllowed ? 'PSI sẵn sàng' : !isReady ? 'Chưa đủ file' : mismatches.length ? 'Cần xử lý mismatch' : 'Chưa đạt điều kiện xuất';
  ready.className = `badge ${releaseAllowed ? '' : 'quiet'}`;
  message.textContent = !isReady ? `Cần đủ ${required.length || 6} file nguồn bắt buộc để tạo PSI Final.` : mismatches.length ? `Còn ${mismatches.length} mismatch phải xử lý trước khi xuất PSI.` : gateReasons.length ? gateReasons.join('. ') : 'Đã đủ file và không còn mismatch mở. Có thể tạo PSI Final.';
  releaseButton.disabled = !releaseAllowed;
  download.classList.toggle('hidden', !status.download_url);
  download.href = status.download_url || '#';
  diagnostics.innerHTML = mismatches.length ? `<div class="mismatch-heading"><strong>${mismatches.length} mismatch mới cần kiểm tra</strong><span>Phải xử lý trước khi xuất PSI</span></div><div class="table-scroll"><table class="mismatch-table"><thead><tr><th>File nguồn</th><th>Sheet / dòng</th><th>Mã</th><th>Mô tả</th><th>Lỗi</th><th>Trạng thái</th><th>Xử lý</th></tr></thead><tbody>${mismatches.map(row => `<tr class="mismatch-${escapeHtml(row.status)}"><td>${escapeHtml(row.file || row.source_type)}</td><td>${escapeHtml(row.sheet)} / ${escapeHtml(row.row)}</td><td>${escapeHtml(row.code || row.record_key)}</td><td>${escapeHtml(row.description)}</td><td>${escapeHtml(row.issue)}</td><td>${escapeHtml(row.status)}</td><td><div class="mismatch-actions"><button class="ant-btn ant-btn-default" data-mismatch-id="${escapeHtml(row.id)}" data-status="resolved">Đã sửa</button><button class="ant-btn ant-btn-default" data-mismatch-id="${escapeHtml(row.id)}" data-status="known">Đã ghi nhận</button><button class="ant-btn ant-btn-default" data-mismatch-id="${escapeHtml(row.id)}" data-status="ignored">Bỏ qua</button></div></td></tr>`).join('')}</tbody></table></div>` : '<p class="hint">Không có mismatch mới. Các case đã biết hoặc đã xử lý được ẩn khỏi bảng.</p>';
  checklist.querySelectorAll('input[type=file]').forEach(input => input.addEventListener('change', () => upload(input.dataset.source, input.files[0])));
  diagnostics.querySelectorAll('[data-mismatch-id]').forEach(button => button.addEventListener('click', () => resolveMismatch(button.dataset.mismatchId, button.dataset.status)));
}
async function upload(source, file) { if (!file) return; message.textContent = `Đang tải ${files[source] || source}...`; const response = await api('/api/weekly-upload', { method: 'POST', body: formData(source, file) }); message.textContent = response.ok ? 'Đã lưu phiên bản file.' : await response.text(); await refresh(); }
async function resolveMismatch(mismatchId, toStatus) { message.textContent = 'Đang cập nhật mismatch...'; const response = await api('/api/mismatch', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ mismatch_id: mismatchId, to_status: toStatus, comment: 'Đã kiểm tra trên PSI shared tool', evidence: { source: 'web' } }) }); message.textContent = response.ok ? 'Đã cập nhật mismatch.' : await response.text(); await refresh(); }
async function release() { message.textContent = 'Đang tạo PSI Final...'; const response = await api('/api/release', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ reporting_period: week.value }) }); if (!response.ok) { message.textContent = await response.text(); return; } const record = await response.json(); message.textContent = 'Đã tạo PSI Final. Link tải có hiệu lực trong 5 phút.'; if (record.signed_url) { download.href = record.signed_url; download.classList.remove('hidden'); } }

document.querySelector('#login-form').addEventListener('submit', async event => { event.preventDefault(); const email = document.querySelector('#login-email').value; const password = document.querySelector('#login-password').value; document.querySelector('#login-message').textContent = 'Đang đăng nhập...'; try { await login(email, password); document.querySelector('#login-message').textContent = ''; } catch (error) { document.querySelector('#login-message').textContent = error instanceof Error ? error.message : 'Đăng nhập thất bại.'; } });
document.querySelector('#logout').addEventListener('click', async () => { if (supabaseClient) await supabaseClient.auth.signOut(); accessToken = ''; showAuth(false); });
team.addEventListener('change', refresh); week.addEventListener('change', refresh); document.querySelector('#refresh').addEventListener('click', refresh); document.querySelector('#release').addEventListener('click', release);
(async () => { const config = await loadConfig(); if (config && window.supabase?.createClient) supabaseClient = window.supabase.createClient(config.url, config.publishable_key); if (supabaseClient) { const session = await supabaseClient.auth.getSession(); accessToken = session.data.session?.access_token || ''; } else { const preview = await fetch('/api/local-preview-session?role=contributor'); if (preview.ok) accessToken = (await preview.json()).token; } showAuth(Boolean(accessToken)); if (accessToken) await refresh(); })();
