'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { createClient } from '@supabase/supabase-js';

const TEAM_ID = '11111111-1111-4111-8111-111111111111';
const XLSX_TYPE = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet';
const MAX_UPLOAD_BYTES = 25 * 1024 * 1024;
const SOURCES = {
  product: 'Product master',
  purchase: 'Purchase / PO',
  revenue: 'Revenue MISA',
  inventory: 'Inventory',
  preorder: 'Pre-order',
  crm: 'CRM Sale',
  target: 'Target',
};

async function responseMessage(response) {
  const text = await response.text();
  try {
    const payload = JSON.parse(text);
    if (Array.isArray(payload.reasons)) return payload.reasons.join('. ');
    return payload.message || payload.error || text;
  } catch {
    return text || `HTTP ${response.status}`;
  }
}

export default function Home() {
  const supabase = useMemo(() => {
    const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
    const key = process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY;
    return url && key ? createClient(url, key) : null;
  }, []);
  const [accessToken, setAccessToken] = useState('');
  const [authChecked, setAuthChecked] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loginMessage, setLoginMessage] = useState('');
  const [week, setWeek] = useState('2026-07');
  const [dataAsOf, setDataAsOf] = useState('2026-07-09');
  const [status, setStatus] = useState(null);
  const [message, setMessage] = useState('Đang kiểm tra checklist.');
  const [uploadingSource, setUploadingSource] = useState('');
  const [releasing, setReleasing] = useState(false);

  const api = useCallback(
    (path, options = {}) =>
      fetch(path, {
        ...options,
        cache: 'no-store',
        headers: {
          ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
          ...(options.headers || {}),
        },
      }),
    [accessToken],
  );

  const refresh = useCallback(async () => {
    if (!accessToken) return;
    setMessage('Đang cập nhật trạng thái dùng chung...');
    try {
      const response = await api(`/api/weekly_status?team=${TEAM_ID}&week=${encodeURIComponent(week)}`);
      if (!response.ok) {
        setMessage(await responseMessage(response));
        return;
      }
      const nextStatus = await response.json();
      setStatus(nextStatus);
      const owned = Array.isArray(nextStatus.owned_sources) ? nextStatus.owned_sources : Object.keys(SOURCES);
      const mismatches = Array.isArray(nextStatus.mismatches) ? nextStatus.mismatches : [];
      const gateReasons = Array.isArray(nextStatus.gate_reasons) ? nextStatus.gate_reasons : [];
      if (!nextStatus.ready) {
        setMessage(`Cần đủ ${owned.length || 7} file nguồn để tạo PSI Final.`);
      } else if (mismatches.length) {
        setMessage(`Còn ${mismatches.length} mismatch phải xử lý trước khi xuất PSI.`);
      } else if (gateReasons.length) {
        setMessage(gateReasons.join('. '));
      } else {
        setMessage('Đã đủ file và không còn mismatch mở. Có thể tạo PSI Final.');
      }
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Không thể tải trạng thái PSI.');
    }
  }, [accessToken, api, week]);

  useEffect(() => {
    if (!supabase) {
      setLoginMessage('Thiếu cấu hình Supabase public cho Next.js.');
      setAuthChecked(true);
      return undefined;
    }
    let active = true;
    supabase.auth.getSession().then(({ data }) => {
      if (active) {
        setAccessToken(data.session?.access_token || '');
        setAuthChecked(true);
      }
    });
    const { data } = supabase.auth.onAuthStateChange((_event, session) => {
      if (active) setAccessToken(session?.access_token || '');
    });
    return () => {
      active = false;
      data.subscription.unsubscribe();
    };
  }, [supabase]);

  useEffect(() => {
    if (accessToken) void refresh();
  }, [accessToken, refresh]);

  async function login(event) {
    event.preventDefault();
    if (!supabase) return;
    setLoginMessage('Đang đăng nhập...');
    const { data, error } = await supabase.auth.signInWithPassword({ email, password });
    if (error) {
      setLoginMessage(error.message);
      return;
    }
    setAccessToken(data.session?.access_token || '');
    setLoginMessage('');
  }

  async function logout() {
    if (supabase) await supabase.auth.signOut();
    setAccessToken('');
    setStatus(null);
  }

  async function upload(source, file) {
    if (!file || !supabase) return;
    if (!file.name.toLowerCase().endsWith('.xlsx') || file.size < 1 || file.size > MAX_UPLOAD_BYTES) {
      setMessage('File phải là XLSX và không vượt quá 25 MB.');
      return;
    }
    setUploadingSource(source);
    setMessage(`Đang chuẩn bị tải ${SOURCES[source] || source}...`);
    let stagingPath = '';
    try {
      const prepare = await api('/api/upload-url', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          team_id: TEAM_ID,
          filename: file.name,
          content_type: XLSX_TYPE,
          byte_size: file.size,
        }),
      });
      if (!prepare.ok) throw new Error(await responseMessage(prepare));
      const prepared = await prepare.json();
      stagingPath = prepared.staging_path;
      setMessage(`Đang tải ${SOURCES[source] || source} thẳng lên kho dữ liệu...`);
      const { error: uploadError } = await supabase.storage
        .from('psi-source')
        .uploadToSignedUrl(stagingPath, prepared.upload_token, file, {
          contentType: XLSX_TYPE,
          cacheControl: '0',
        });
      if (uploadError) throw uploadError;

      setMessage('Đã tải file. Đang kiểm tra dữ liệu và cập nhật mismatch...');
      const finalize = await api('/api/weekly_upload_staged', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          team_id: TEAM_ID,
          week,
          data_as_of: dataAsOf,
          source_type: source,
          filename: file.name,
          staging_path: stagingPath,
        }),
      });
      if (!finalize.ok) throw new Error(await responseMessage(finalize));
      setMessage('Đã lưu phiên bản file và cập nhật bảng mismatch.');
      await refresh();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Tải file thất bại.');
    } finally {
      setUploadingSource('');
    }
  }

  async function resolveMismatch(mismatchId, toStatus) {
    setMessage('Đang cập nhật mismatch...');
    const response = await api('/api/mismatch', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        mismatch_id: mismatchId,
        to_status: toStatus,
        comment: 'Đã kiểm tra trên PSI shared tool',
        evidence: { source: 'web' },
      }),
    });
    setMessage(response.ok ? 'Đã cập nhật mismatch.' : await responseMessage(response));
    await refresh();
  }

  async function release() {
    setReleasing(true);
    setMessage('Đang tạo PSI Final...');
    try {
      const response = await api('/api/release', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reporting_period: week }),
      });
      if (!response.ok) throw new Error(await responseMessage(response));
      const record = await response.json();
      setStatus((current) => ({ ...current, download_url: record.signed_url || current?.download_url }));
      setMessage('Đã tạo PSI Final. Link tải có hiệu lực trong 5 phút.');
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Không thể tạo PSI Final.');
    } finally {
      setReleasing(false);
    }
  }

  const ownedSources = Array.isArray(status?.owned_sources) ? status.owned_sources : Object.keys(SOURCES);
  const mismatches = Array.isArray(status?.mismatches) ? status.mismatches : [];
  const releaseAllowed = Boolean(status?.release_allowed);

  return (
    <main className="shell">
      <header className="topbar">
        <div className="hero-copy">
          <p className="eyebrow">PSI / CÔNG CỤ DÙNG CHUNG</p>
          <h1>Danh sách file cần nộp</h1>
          <p className="lead">Các team tải đủ 7 file nguồn theo thời điểm của mình. Mỗi lần tải lại được lưu thành một phiên bản mới.</p>
        </div>
        <span className={`ant-tag badge ${accessToken ? 'ant-tag-green' : 'ant-tag-gold'}`}>
          {!authChecked ? 'ĐANG KIỂM TRA PHIÊN' : accessToken ? 'ĐÃ ĐĂNG NHẬP' : 'YÊU CẦU ĐĂNG NHẬP'}
        </span>
      </header>

      {!accessToken ? (
        <section className="card">
          <div className="section-heading">
            <div><p className="eyebrow">XÁC THỰC</p><h2>Đăng nhập PSI</h2><p className="hint">Dùng tài khoản purchase, sale, accounting hoặc tech đã được cấp.</p></div>
          </div>
          <form className="form-grid" onSubmit={login} noValidate>
            <label className="ant-form-item">Email<input className="ant-input" type="email" autoComplete="username" value={email} onChange={(event) => setEmail(event.target.value)} required /></label>
            <label className="ant-form-item">Mật khẩu<input className="ant-input" type="password" autoComplete="current-password" value={password} onChange={(event) => setPassword(event.target.value)} required /></label>
            <button className="ant-btn ant-btn-primary" type="submit">Đăng nhập</button>
          </form>
          <p className="hint" role="status" aria-live="polite">{loginMessage}</p>
        </section>
      ) : (
        <>
          <div className="notice" role="note"><strong>Lưu ý:</strong> Mọi tài khoản cùng xem trạng thái chung. Mismatch mới phải được xử lý hoặc ghi nhận trước khi xuất PSI Final.</div>
          <section className="card">
            <div className="section-heading">
              <div><p className="eyebrow">01 / PHẠM VI</p><h2>Kỳ báo cáo dùng chung</h2></div>
              <span className={`badge ${releaseAllowed ? 'ready' : 'quiet'}`}>{releaseAllowed ? 'PSI sẵn sàng' : !status?.ready ? 'Chưa đủ file' : mismatches.length ? 'Cần xử lý mismatch' : 'Chưa đạt điều kiện xuất'}</span>
            </div>
            <div className="form-grid">
              <label className="ant-form-item">Workspace<select className="ant-select-selector" value={TEAM_ID} disabled><option value={TEAM_ID}>NanoHome PSI</option></select></label>
              <label className="ant-form-item">Tháng báo cáo<input className="ant-input" type="month" value={week} onChange={(event) => setWeek(event.target.value)} required /></label>
              <label className="ant-form-item">Ngày dữ liệu<input className="ant-input" type="date" value={dataAsOf} onChange={(event) => setDataAsOf(event.target.value)} required /></label>
            </div>
          </section>

          <section className="card">
            <div className="section-heading"><div><p className="eyebrow">02 / CHECKLIST</p><h2>File bắt buộc</h2><p className="hint">Tất cả team nhìn cùng một checklist và lịch sử phiên bản.</p></div><button className="ant-btn ant-btn-default" type="button" onClick={refresh}>Cập nhật</button></div>
            <div className="checklist">
              {ownedSources.map((source) => {
                const item = status?.files?.[source] || { status: 'missing' };
                const busy = uploadingSource === source;
                return (
                  <div className="check-item" key={source}>
                    <div><strong>{SOURCES[source] || source}</strong><small>{item.status === 'uploaded' ? `Đã nộp · phiên bản ${item.version} · ${item.filename || ''}` : 'Chưa có file'}</small></div>
                    <label className={`ant-btn ant-btn-default file-button ${busy ? 'disabled' : ''}`}>
                      {busy ? 'Đang xử lý...' : item.status === 'uploaded' ? 'Tải lại' : 'Chọn file'}
                      <input type="file" accept=".xlsx" hidden disabled={Boolean(uploadingSource)} onChange={(event) => upload(source, event.target.files?.[0])} />
                    </label>
                  </div>
                );
              })}
            </div>
          </section>

          <section className="card result-card">
            <div className="section-heading"><div><p className="eyebrow">03 / PSI FINAL</p><h2>Kết quả tháng</h2></div><button className="ant-btn ant-btn-primary" type="button" disabled={!releaseAllowed || releasing} onClick={release}>{releasing ? 'Đang tạo...' : 'Xuất PSI Final'}</button></div>
            <p className="hint" role="status" aria-live="polite">{message}</p>
            <div className="diagnostics" aria-live="polite">
              {mismatches.length ? (
                <>
                  <div className="mismatch-heading"><strong>{mismatches.length} mismatch mới cần kiểm tra</strong><span>Phải xử lý trước khi xuất PSI</span></div>
                  <div className="table-scroll">
                    <table className="mismatch-table">
                      <thead><tr><th>File nguồn</th><th>Sheet / dòng</th><th>Mã</th><th>Mô tả</th><th>Lỗi</th><th>Trạng thái</th><th>Xử lý</th></tr></thead>
                      <tbody>
                        {mismatches.map((row) => (
                          <tr className={`mismatch-${row.status}`} key={row.id}>
                            <td>{row.file || row.source_type}</td><td>{row.sheet} / {row.row}</td><td>{row.code || row.record_key}</td><td>{row.description}</td><td>{row.issue}</td><td>{row.status}</td>
                            <td><div className="mismatch-actions"><button className="ant-btn ant-btn-default" type="button" onClick={() => resolveMismatch(row.id, 'resolved')}>Đã sửa</button><button className="ant-btn ant-btn-default" type="button" onClick={() => resolveMismatch(row.id, 'known')}>Đã ghi nhận</button><button className="ant-btn ant-btn-default" type="button" onClick={() => resolveMismatch(row.id, 'ignored')}>Bỏ qua</button></div></td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </>
              ) : <p className="hint">Không có mismatch mới. Các case đã biết hoặc đã xử lý được ẩn khỏi bảng.</p>}
            </div>
            {status?.download_url ? <a className="ant-btn ant-btn-primary download" href={status.download_url}>Tải PSI Final</a> : null}
          </section>
          <button className="ant-btn ant-btn-default logout" type="button" onClick={logout}>Đăng xuất</button>
        </>
      )}
    </main>
  );
}
