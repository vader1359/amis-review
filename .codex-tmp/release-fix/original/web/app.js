const files = { product: 'Product master', purchase: 'Purchase / PO', revenue: 'Revenue MISA', inventory: 'Inventory', preorder: 'Pre-order', crm: 'CRM Sale', target: 'Target' };
const team = document.querySelector('#team');
const week = document.querySelector('#week');
const checklist = document.querySelector('#checklist');
const message = document.querySelector('#message');
const ready = document.querySelector('#ready');
const download = document.querySelector('#download');
const diagnostics = document.querySelector('#diagnostics');
const loginCard = document.querySelector('#login-card');
const workspace = document.querySelector('#workspace');
const authBadge = document.querySelector('#auth-badge');
let accessToken = '';
let supabaseClient = null;

function headers() { return accessToken ? { Authorization: `Bearer ${accessToken}` } : {}; }
function formData(source, file) { const data = new FormData(); data.append('team_id', team.value); data.append('week', week.value); data.append('source_type', source); data.append('file', file); return data; }
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
  checklist.innerHTML = owned.map(source => { const label = files[source] || source; const item = status.files?.[source] || { status: 'missing' }; return `<div class="check-item"><div><strong>${label}</strong><small>${item.status === 'uploaded' ? `Đã nộp · phiên bản ${item.version}` : 'Chưa có file'}</small></div><label class="ant-btn ant-btn-default">${item.status === 'uploaded' ? 'Tải lại' : 'Chọn file'}<input type="file" accept=".xlsx" data-source="${source}" hidden></label></div>`; }).join('');
  const isReady = Boolean(status.ready); ready.textContent = isReady ? 'PSI sẵn sàng' : 'Chưa đủ file'; ready.className = `badge ${isReady ? '' : 'quiet'}`; message.textContent = isReady ? 'Đã đủ file nguồn. Có thể tạo PSI Final.' : `Cần đủ ${owned.length || 7} file được phân quyền để tạo PSI Final.`; download.classList.toggle('hidden', !status.download_url); download.href = status.download_url || '#';
  diagnostics.textContent = status.mismatches?.length ? `Chẩn đoán: ${status.mismatches.length} mismatch cần rà soát; không chặn tạo workbook.` : 'Không có mismatch được trả về.';
  checklist.querySelectorAll('input[type=file]').forEach(input => input.addEventListener('change', () => upload(input.dataset.source, input.files[0])));
}
async function upload(source, file) { if (!file) return; message.textContent = `Đang tải ${files[source] || source}...`; const response = await api('/api/weekly-upload', { method: 'POST', body: formData(source, file) }); message.textContent = response.ok ? 'Đã lưu phiên bản file.' : await response.text(); await refresh(); }
async function release() { message.textContent = 'Đang tạo PSI Final...'; const response = await api('/api/release', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ reporting_period: week.value }) }); if (!response.ok) { message.textContent = await response.text(); return; } const record = await response.json(); message.textContent = 'Đã tạo PSI Final.'; if (record.signed_url) { download.href = record.signed_url; download.classList.remove('hidden'); } await refresh(); }
async function generate() { await release(); }

document.querySelector('#login-form').addEventListener('submit', async event => { event.preventDefault(); const email = document.querySelector('#login-email').value; const password = document.querySelector('#login-password').value; document.querySelector('#login-message').textContent = 'Đang đăng nhập...'; try { await login(email, password); document.querySelector('#login-message').textContent = ''; } catch (error) { document.querySelector('#login-message').textContent = error instanceof Error ? error.message : 'Đăng nhập thất bại.'; } });
document.querySelector('#logout').addEventListener('click', async () => { if (supabaseClient) await supabaseClient.auth.signOut(); accessToken = ''; showAuth(false); });
team.addEventListener('change', refresh); week.addEventListener('change', refresh); document.querySelector('#refresh').addEventListener('click', refresh); document.querySelector('#generate').addEventListener('click', generate); document.querySelector('#release').addEventListener('click', release);
(async () => { const config = await loadConfig(); if (config && window.supabase?.createClient) supabaseClient = window.supabase.createClient(config.url, config.publishable_key); if (supabaseClient) { const session = await supabaseClient.auth.getSession(); accessToken = session.data.session?.access_token || ''; } else { const preview = await fetch('/api/local-preview-session?role=contributor'); if (preview.ok) accessToken = (await preview.json()).token; } showAuth(Boolean(accessToken)); if (accessToken) await refresh(); })();
