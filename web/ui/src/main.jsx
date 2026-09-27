import React, { useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { Alert, App as AntApp, Avatar, Button, Card, Col, Collapse, ConfigProvider, DatePicker, Descriptions, Divider, Flex, Form, Input, Layout, Popconfirm, Progress, Row, Select, Space, Table, Tag, Typography, Upload } from 'antd';
import { CheckCircleOutlined, CloudUploadOutlined, CloseOutlined, DownloadOutlined, FileExcelOutlined, FolderOpenOutlined, InboxOutlined, SafetyCertificateOutlined, SwapOutlined } from '@ant-design/icons';
import viVN from 'antd/locale/vi_VN';
import dayjs from 'dayjs';
import 'dayjs/locale/vi';
import 'antd/dist/reset.css';
import './styles.css';
import { appendClassifications, assignmentState, labels, makeDraftForm, mapClassifications, periodicRoles, retainedRoles, validateBatch } from './model.js';
import { requestJson } from './request.js';
import ReviewPanel from './ReviewPanel.jsx';

dayjs.locale('vi');
const { Title, Text, Paragraph } = Typography;
const messages = {
  BUILD_IN_PROGRESS: 'Một báo cáo đang được xử lý. Chờ hoàn tất rồi thử lại.',
  SOURCE_SET_INVALID: 'Cần đủ 7 nguồn và PSI Final kỳ trước, mỗi nguồn một file.',
  SOURCE_PACKAGE_INVALID: 'Có file không phải Excel hợp lệ hoặc vượt giới hạn xử lý.',
  SOURCE_SIZE_INVALID: 'Mỗi file phải có dữ liệu và không vượt quá 50 MB.',
  REQUEST_TOO_LARGE: 'Bộ file vượt giới hạn tải lên.',
  CUTOFF_INVALID: 'Ngày chốt phải từ 01/01/2024 trở đi.',
  BASELINE_FINAL_REQUIRED: 'Chọn PSI Final đã được người phụ trách duyệt.',
  BASELINE_NOT_EARLIER: 'PSI kỳ trước phải có ngày chốt sớm hơn kỳ đang xử lý.',
  BASELINE_DATE_MISMATCH: 'Ngày trong tên file PSI kỳ trước không khớp nội dung báo cáo.',
  BASELINE_DATE_MISSING: 'Không xác định được ngày chốt trong PSI kỳ trước.',
  BASELINE_SCHEMA_INVALID: 'PSI kỳ trước chưa đúng cấu trúc 17 sheet đã quy định.',
  BASELINE_CHECKS_FAILED: 'PSI kỳ trước có kiểm định chưa đạt, không thể dùng đối chiếu.',
  SOURCE_VALIDATION_FAILED: 'Dữ liệu chưa đạt kiểm tra nguồn. Kiểm tra nội dung, Manual Check và PSI kỳ trước.',
  INDEPENDENT_VALIDATION_FAILED: 'Đối soát độc lập chưa đạt. Chưa tạo báo cáo.',
  WORKBOOK_VALIDATION_FAILED: 'File Excel chưa đạt kiểm định. Chưa cho phép tải xuống.',
  SAVED_SOURCE_NOT_FOUND: 'Bản đã lưu không còn khả dụng. Vui lòng chọn lại file.',
  SAVED_SOURCE_INTEGRITY_FAILED: 'Bản đã lưu không còn nguyên vẹn. Vui lòng thay file.',
  SOURCE_STORE_INVALID: 'Chưa đọc được nơi lưu nguồn. Vui lòng thử lại.',
  SOURCE_SCHEMA_INVALID: 'Cấu trúc file chưa phù hợp với loại nguồn đã chọn.',
  SAVED_SOURCE_ROLE_INVALID: 'Loại nguồn này không hỗ trợ lưu để dùng lại.',
  CLASSIFICATION_FILES_INVALID: 'Chọn từ 1 đến 4 file nguồn Excel để nhận diện.',
  SOURCE_EXTENSION_INVALID: 'Chỉ nhận file Excel .xlsx.',
  SOURCE_FILE_REQUIRED: 'Cần chọn một file Excel hợp lệ.',
  SAVED_SOURCE_INVALID: 'Bản đã lưu không còn hợp lệ. Vui lòng thay file.',
  SOURCE_ROLE_INVALID: 'File chưa phù hợp với loại nguồn đã chọn.',
  PREVIEW_TOKEN_REQUIRED: 'Phiên làm việc đã thay đổi. Tải lại trang để tiếp tục.',
  ONLINE_STORAGE_UNAVAILABLE: 'Chưa kết nối được nơi lưu online. Báo cáo chưa được xác nhận lưu; thử lại khi kết nối ổn định.',
  ONLINE_REPORT_INTEGRITY_FAILED: 'Báo cáo đã lưu không qua kiểm tra tính toàn vẹn. Chưa thể mở hoặc tải xuống.',
  ONLINE_REPORT_VERSION_UNSUPPORTED: 'Báo cáo này cần phiên bản ứng dụng mới hơn để mở.',
  ONLINE_REPORT_NOT_FOUND: 'Không tìm thấy báo cáo đã lưu. Làm mới danh sách để kiểm tra lại.',
};

const request = (path, options) => requestJson(path, options, messages);

function sizeLabel(size) { return size >= 1024 * 1024 ? `${(size / 1024 / 1024).toFixed(1)} MB` : `${Math.ceil(size / 1024)} KB`; }

function ReportHistory({ revision, onOpen }) {
  const [offset, setOffset] = useState(0);
  const [refresh, setRefresh] = useState(0);
  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(true);
  const [opening, setOpening] = useState('');
  const [error, setError] = useState('');
  const limit = 20;

  useEffect(() => { setOffset(0); }, [revision]);
  useEffect(() => {
    let active = true;
    setLoading(true); setError('');
    request(`/api/reports?limit=${limit}&offset=${offset}`)
      .then(result => { if (active) setReports(result.reports || []); })
      .catch(failure => { if (active) { setError(failure.message); setReports([]); } })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [offset, revision, refresh]);

  async function openReport(id) {
    setOpening(id); setError('');
    try { onOpen(await request(`/api/reports/${encodeURIComponent(id)}`)); }
    catch (failure) { setError(failure.message); }
    finally { setOpening(''); }
  }

  return <Card className="report-history" title="Báo cáo đã lưu online" extra={<Button size="small" loading={loading} onClick={() => setRefresh(current => current + 1)}>Làm mới</Button>}>
    {error && <Alert className="history-alert" type="error" showIcon title="Chưa đọc được báo cáo" description={error} />}
    <Table size="small" rowKey="id" dataSource={reports} loading={loading} pagination={false} scroll={{ x: 660 }} locale={{ emptyText: error ? 'Chưa tải được danh sách báo cáo' : 'Chưa có báo cáo được lưu online' }} columns={[
      { title: 'Ngày chốt', dataIndex: 'as_of', render: value => value ? dayjs(value).format('DD/MM/YYYY') : '—' },
      { title: 'Lưu lúc', dataIndex: 'created_at', render: value => value ? dayjs(value).format('DD/MM/YYYY HH:mm') : '—' },
      { title: 'Trạng thái', render: () => <Tag color="blue">Draft</Tag> },
      { title: 'Sheet', dataIndex: 'sheet_count', width: 65 },
      { title: '', key: 'actions', width: 190, render: (_, item) => <Space size={4}><Button size="small" loading={opening === item.id} disabled={Boolean(opening)} onClick={() => void openReport(item.id)}>Mở báo cáo</Button><Button size="small" icon={<DownloadOutlined />} href={item.download_url} aria-label={`Tải Excel Draft ngày ${item.as_of}`}>Excel</Button></Space> },
    ]} />
    <Flex className="history-pagination" align="center" justify="space-between" gap={12} wrap><Text type="secondary">Trang {Math.floor(offset / limit) + 1} · Tối đa 20 báo cáo mỗi trang</Text><Space><Button size="small" disabled={loading || offset === 0} onClick={() => setOffset(current => Math.max(0, current - limit))}>Trước</Button><Button size="small" disabled={loading || Boolean(error) || reports.length < limit} onClick={() => setOffset(current => current + limit)}>Tiếp</Button></Space></Flex>
  </Card>;
}

function Workspace({ initialConfig }) {
  const [config, setConfig] = useState(initialConfig);
  const [rows, setRows] = useState([]);
  const [cutoff, setCutoff] = useState(dayjs());
  const [busy, setBusy] = useState('');
  const [error, setError] = useState('');
  const [report, setReport] = useState(null);
  const [historyRevision, setHistoryRevision] = useState(0);
  const { message } = AntApp.useApp();
  const saved = config.saved_sources || {};
  const assignments = assignmentState(rows);
  const completeCount = periodicRoles.filter(role => rows.filter(row => row.role === role).length === 1).length + retainedRoles.filter(role => saved[role]?.id).length;
  const ready = assignments.ready && retainedRoles.every(role => saved[role]?.id) && cutoff && !busy;
  const headers = { 'X-PSI-Preview': config.preview_token };

  async function reloadSaved() { const latest = await request('/api/config'); setConfig(latest); return latest; }

  async function classify(files) {
    const validation = validateBatch(files);
    if (validation) { setError(validation); return; }
    setBusy('classify'); setError(''); setReport(null);
    try {
      const body = new FormData(); files.forEach(file => body.append('files', file));
      const result = await request('/api/sources/classify', { method: 'POST', headers, body });
      const incoming = mapClassifications(files, result);
      setRows(current => appendClassifications(current, incoming));
    } catch (failure) { setError(failure.message); }
    finally { setBusy(''); }
  }

  async function saveSource(role, file) {
    const validation = validateBatch([file]);
    if (validation) { setError(validation); return; }
    setBusy(role); setError(''); setReport(null);
    try {
      const body = new FormData(); body.append('file', file);
      const metadata = await request(`/api/sources/${role}`, { method: 'POST', headers, body });
      // Keep the successful upload visible even if the follow-up refresh fails.
      setConfig(current => ({ ...current, saved_sources: { ...current.saved_sources, [role]: metadata } }));
      await reloadSaved();
      message.success(`Đã lưu ${labels[role]}. Các kỳ sau sẽ dùng lại bản này.`);
    } catch (failure) { setError(failure.message); }
    finally { setBusy(''); }
  }

  async function clearSource(role) {
    setBusy(role); setError(''); setReport(null);
    try {
      await request(`/api/sources/${role}`, { method: 'DELETE', headers });
      setConfig(current => ({ ...current, saved_sources: Object.fromEntries(Object.entries(current.saved_sources || {}).filter(([key]) => key !== role)) }));
      await reloadSaved();
    } catch (failure) { setError(failure.message); }
    finally { setBusy(''); }
  }

  async function build() {
    if (!ready) return;
    setBusy('build'); setError(''); setReport(null);
    try {
      const body = makeDraftForm(rows, saved, cutoff.format('YYYY-MM-DD'));
      const result = await request('/api/drafts', { method: 'POST', headers, body, timeoutMs: 600_000 });
      setReport(result);
      if (result.storage === 'neon') setHistoryRevision(current => current + 1);
      try { await reloadSaved(); } catch { message.warning('Báo cáo đã tạo. Chưa làm mới được danh sách file đã lưu.'); }
      window.setTimeout(() => document.getElementById('draft-result')?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 100);
    } catch (failure) { setError(failure.message); }
    finally { setBusy(''); }
  }

  function SavedSource({ role, compact = false }) {
    const source = saved[role];
    if (compact) return <div className="saved-source-row">
      <Text strong className="saved-source-label" ellipsis={{ tooltip: labels[role] }}>{role === 'purchase' ? 'Purchase' : labels[role]}</Text>
      <Text className="saved-source-filename" type={source ? undefined : 'secondary'} ellipsis={{ tooltip: source?.filename }}>{source?.filename || 'Chưa có file'}</Text>
      <Space size={4} className="saved-source-actions">
        <Upload accept=".xlsx" showUploadList={false} disabled={Boolean(busy)} beforeUpload={file => { void saveSource(role, file); return false; }}><Button size="small" loading={busy === role} disabled={Boolean(busy)} aria-label={`${source ? 'Thay file' : 'Chọn file'} ${labels[role]}`}>{source ? 'Thay file' : 'Chọn file'}</Button></Upload>
        {source && <Popconfirm title="Bỏ dùng bản đã lưu?" onConfirm={() => clearSource(role)} okText="Bỏ dùng" cancelText="Giữ lại"><Button size="small" type="text" icon={<CloseOutlined />} disabled={Boolean(busy)} title={`Bỏ dùng ${labels[role]}`} aria-label={`Bỏ dùng ${labels[role]}`} /></Popconfirm>}
      </Space>
    </div>;
    return <Card className="source-card" size="small">
      <Flex gap={12} align="start"><Avatar className="file-avatar" shape="square" icon={<FileExcelOutlined />} /><div className="source-body">
        <Text strong>{labels[role]}</Text>
        <div className="source-state"><Tag color={source ? 'green' : 'default'} icon={source ? <CheckCircleOutlined /> : undefined}>{source ? 'Đang dùng bản đã lưu' : 'Chưa có file'}</Tag></div>
        {source ? <><Paragraph className="filename" ellipsis={{ rows: 2, tooltip: source.filename }}>{source.filename}</Paragraph><Text type="secondary" className="file-meta">{sizeLabel(source.size)} · Lưu {dayjs(source.stored_at).format('DD/MM/YYYY HH:mm')}</Text></> : <Paragraph type="secondary" className="source-empty">{role === 'prior_psi' ? 'Chọn PSI Final gần nhất đã duyệt.' : 'Chọn bản đã được người phụ trách duyệt.'}</Paragraph>}
      </div></Flex>
      <Flex gap={8} wrap className="source-actions">
        <Upload accept=".xlsx" showUploadList={false} disabled={Boolean(busy)} beforeUpload={file => { void saveSource(role, file); return false; }}><Button icon={source ? <SwapOutlined /> : <CloudUploadOutlined />} loading={busy === role} disabled={Boolean(busy)} aria-label={`${source ? 'Thay file' : 'Chọn file'} ${labels[role]}`}>{source ? 'Thay file' : 'Chọn file'}</Button></Upload>
        {source && <Popconfirm title="Bỏ dùng bản đã lưu?" description="Bạn sẽ cần chọn lại file trước khi tạo báo cáo." onConfirm={() => clearSource(role)} okText="Bỏ dùng" cancelText="Giữ lại"><Button type="text" disabled={Boolean(busy)} aria-label={`Bỏ dùng ${labels[role]}`}>Bỏ dùng</Button></Popconfirm>}
      </Flex>
    </Card>;
  }

  const columns = [
    { title: 'File đã chọn', key: 'file', render: (_, row) => <Space align="start"><FileExcelOutlined className="table-file-icon" /><div><Text className="filename">{row.file.name}</Text><div><Text type="secondary" className="file-meta">{sizeLabel(row.file.size)}</Text></div></div></Space> },
    { title: 'Loại nguồn', key: 'role', width: 255, render: (_, row) => <Select className="role-select" aria-label={`Loại nguồn cho ${row.file.name}`} placeholder="Chọn loại nguồn" value={row.role || undefined} disabled={Boolean(busy)} status={!row.role || assignments.duplicate.includes(row.role) ? 'warning' : undefined} options={periodicRoles.map(value => ({ value, label: labels[value] }))} onChange={role => { setRows(current => current.map(item => item.key === row.key ? { ...item, role } : item)); setReport(null); }} /> },
    { title: '', key: 'remove', width: 40, render: (_, row) => <Button type="text" size="small" icon={<CloseOutlined />} disabled={Boolean(busy)} aria-label={`Bỏ file ${row.file.name}`} title="Bỏ file" onClick={() => { setRows(current => current.filter(item => item.key !== row.key)); setReport(null); }} /> },
    { title: 'Kết quả', key: 'status', width: 140, render: (_, row) => <Tag color={assignments.duplicate.includes(row.role) ? 'red' : row.role ? 'green' : 'orange'}>{assignments.duplicate.includes(row.role) ? 'Trùng loại nguồn' : row.role ? 'Đã xếp nguồn' : 'Cần chọn loại'}</Tag> },
  ];

  return <Layout className="workspace">
    <Layout.Header className="page-header"><Flex justify="space-between" align="center" className="header-inner"><Space size={12}><Avatar shape="square" className="brand-mark">P</Avatar><Text strong className="brand-name">NANOHOME <Text type="secondary">/ PSI</Text></Text></Space><Tag icon={<SafetyCertificateOutlined />} color="blue">Không gian báo cáo</Tag></Flex></Layout.Header>
    <Layout.Content className="page-content">
      <Flex justify="space-between" align="end" wrap gap={20} className="page-intro"><div><Text className="eyebrow">BÁO CÁO ĐỊNH KỲ</Text><Title level={1}>Chuẩn bị báo cáo PSI</Title><Paragraph type="secondary">Thả bộ nguồn mới, kiểm tra file đang dùng và xuất Excel đã đối soát.</Paragraph></div><Card size="small" className="cutoff-card"><Text strong>Ngày chốt dữ liệu</Text><DatePicker aria-label="Ngày chốt dữ liệu" value={cutoff} onChange={value => { setCutoff(value); setReport(null); }} format="DD/MM/YYYY" placeholder="Chọn ngày chốt" disabled={Boolean(busy)} minDate={dayjs('2024-01-01')} allowClear /></Card></Flex>
      <Row gutter={[24, 24]}><Col xs={24} xl={17}>
        <Space orientation="vertical" size={24} className="full-width">
          <Card title={<Space><Tag color="blue">01</Tag><span>Nguồn kỳ báo cáo</span></Space>} extra={<Space size={8}><Tag>{periodicRoles.length - assignments.missing.length}/4 loại nguồn</Tag>{rows.length > 0 && <Button type="text" size="small" disabled={Boolean(busy)} onClick={() => { setRows([]); setReport(null); setError(''); }}>Bỏ tất cả</Button>}</Space>}>
            <Paragraph type="secondary">Tải từng file hoặc nhiều file mỗi đợt. Các file sẽ được cộng vào bộ nguồn đang chọn.</Paragraph>
            <Upload.Dragger accept=".xlsx" multiple fileList={[]} showUploadList={false} disabled={Boolean(busy)} beforeUpload={(file, fileList) => { if (file === fileList[0]) void classify(fileList); return false; }}>
              <div className="ant-upload-drag-icon"><InboxOutlined /></div><Paragraph strong className="upload-heading">{busy === 'classify' ? 'Đang nhận diện bộ nguồn…' : rows.length ? 'Thêm file vào bộ nguồn' : 'Thả hoặc chọn file Excel'}</Paragraph><Text type="secondary">CRM Sales Order · Product Master · Bán hàng · Tồn kho</Text><div className="upload-limit"><Text type="secondary">.xlsx · Tối đa 50 MB mỗi file</Text></div>
            </Upload.Dragger>
            {rows.length > 0 && <><Table className="assignment-table" dataSource={rows} columns={columns} pagination={false} size="small" scroll={{ x: 650 }} />{!assignments.ready && <Alert className="assignment-alert" type="warning" showIcon title="Kiểm tra cách xếp nguồn" description={assignments.duplicate.length ? `Đang trùng: ${assignments.duplicate.map(role => labels[role]).join(', ')}. Bỏ file thừa hoặc sửa loại nguồn; mỗi loại cần đúng một file.` : `Còn thiếu: ${assignments.missing.map(role => labels[role]).join(', ')}. Tải thêm file còn thiếu hoặc chọn lại loại nguồn.`} />}</>}
          </Card>
          <Card className="retained-sources" title={<Space><Tag color="blue">02</Tag><span>Nguồn và quyết định đã duyệt</span></Space>}><div className="saved-source-list">{retainedRoles.filter(role => role !== 'prior_psi').map(role => <SavedSource key={role} role={role} compact />)}</div></Card>
          <Card title={<Space><Tag color="blue">03</Tag><span>Báo cáo đối chiếu</span></Space>}><Paragraph type="secondary">Dùng lại PSI Final đã lưu để nhận diện mismatch mới. Ngày báo cáo đối chiếu phải trước ngày chốt hiện tại.</Paragraph><SavedSource role="prior_psi" /><Alert className="baseline-note" type="info" showIcon title="Draft mới không tự thay PSI Final" description="Khi đã duyệt một kỳ mới, bạn chủ động thay file đối chiếu bằng bản Final đó." /></Card>
        </Space>
      </Col><Col xs={24} xl={7}><Card className="build-card" title={<Space><FolderOpenOutlined /><span>Sẵn sàng xuất báo cáo</span></Space>}><Flex justify="space-between" align="center"><Text type="secondary">Nguồn đã chọn</Text><Text strong>{completeCount}/8</Text></Flex><Progress percent={Math.round(completeCount / 8 * 100)} showInfo={false} /><Divider /><Space orientation="vertical" size={14} className="full-width"><Flex justify="space-between"><Text>Nguồn kỳ này</Text><Tag color={assignments.ready ? 'green' : 'default'}>{assignments.ready ? 'Đủ 4 nguồn' : 'Cần bổ sung'}</Tag></Flex><Flex justify="space-between"><Text>Bản đã lưu</Text><Text>{retainedRoles.filter(role => saved[role]?.id).length}/4 file</Text></Flex><Flex justify="space-between"><Text>Ngày chốt</Text><Text strong>{cutoff?.format('DD/MM/YYYY') || 'Chưa chọn'}</Text></Flex></Space><Divider /><Button type="primary" size="large" block icon={<SafetyCertificateOutlined />} disabled={!ready} loading={busy === 'build'} onClick={build}>Kiểm định và tạo Draft</Button><Paragraph type="secondary" className="build-caption">Đối soát độc lập, kiểm tra dữ liệu và kiểm định Excel 17 sheet trước khi cho tải xuống.</Paragraph>{busy === 'build' && <Alert type="info" showIcon title="Đang kiểm định và xuất Excel…" description="Bộ dữ liệu lớn có thể mất vài phút. Giữ trang này mở." />}</Card></Col></Row>
      {error && <Alert className="page-alert" type="error" showIcon title="Chưa hoàn tất" description={error} closable onClose={() => setError('')} />}
      {report && <Card id="draft-result" className="result-card" title={<Space><CheckCircleOutlined className="success-icon" /><span>PSI Draft sẵn sàng</span><Tag color={report.storage === 'neon' ? 'green' : 'default'}>{report.storage === 'neon' ? 'Đã lưu online' : 'Chỉ có trên máy này'}</Tag>{report.as_of && <Tag>{dayjs(report.as_of).format('DD/MM/YYYY')}</Tag>}</Space>} extra={<Button type="primary" icon={<DownloadOutlined />} href={report.download_url}>Tải Excel Draft</Button>}><Paragraph>Đã qua đối soát độc lập và kiểm định file Excel. Người phụ trách cần duyệt Draft trước khi dùng làm PSI Final.</Paragraph><Space wrap>{Object.entries(report.validation || {}).map(([key, value]) => <Tag color="green" icon={<CheckCircleOutlined />} key={key}>{({ payload: 'Dữ liệu', parquet: 'Chuyển đổi dữ liệu', workbook: 'Excel 17 sheet' })[key] || key}: {value}</Tag>)}</Space><Collapse className="result-details" items={[{ key: 'gates', label: 'Xem kết quả kiểm định', children: <Table size="small" pagination={false} rowKey={(_, index) => String(index)} dataSource={report.gates || []} columns={[{ title: 'Kiểm tra', render: (_, gate) => gate.check || gate.name }, { title: 'Kết quả', dataIndex: 'status', width: 100, render: status => <Tag color={status === 'WARN' ? 'orange' : 'green'}>{status}</Tag> }]} /> }, { key: 'hashes', label: 'Thông tin kiểm chứng', children: <Descriptions column={1} items={[{ key: 'input', label: 'Bộ nguồn', children: <Text className="hash-value">{report.input_hash}</Text> }, { key: 'workbook', label: 'File Excel', children: <Text className="hash-value">{report.workbook_sha256}</Text> }]} /> }]} /></Card>}
      {report?.storage === 'neon' && <ReviewPanel report={report} previewToken={config.preview_token} onReportCreated={next => { setReport(next); setHistoryRevision(current => current + 1); }} />}
      {config.report_storage?.enabled && <ReportHistory revision={historyRevision} onOpen={savedReport => { setReport(savedReport); window.setTimeout(() => document.getElementById('draft-result')?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 100); }} />}
      <Layout.Footer className="page-footer"><Text type="secondary">{config.report_storage?.enabled ? 'Báo cáo và dữ liệu sheet PSI được lưu online trên Neon' : 'Chưa bật lưu báo cáo online'} · File nguồn dùng lại được giữ trên máy chủ · Chưa phát hành lên Power BI</Text></Layout.Footer>
    </Layout.Content>
  </Layout>;
}

function Login({ onSuccess }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  async function submit(values) {
    setBusy(true); setError('');
    try {
      await requestJson('/__login', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(values) }, { LOGIN_INVALID: 'Tên đăng nhập hoặc mật khẩu chưa đúng.' });
      onSuccess();
    } catch (failure) { setError(failure.message); }
    finally { setBusy(false); }
  }
  return <Layout style={{ minHeight: '100vh', padding: '64px 20px' }}><Card style={{ width: '100%', maxWidth: 420, margin: '0 auto' }}>
    <Title level={3}>Đăng nhập PSI</Title><Paragraph type="secondary">Nhập tài khoản để mở không gian báo cáo.</Paragraph>
    {error && <Alert type="error" showIcon title={error} />}
    <Form layout="vertical" onFinish={submit} style={{ marginTop: 24 }}>
      <Form.Item label="Tên đăng nhập" name="username" rules={[{ required: true, message: 'Nhập tên đăng nhập.' }]}><Input autoComplete="username" /></Form.Item>
      <Form.Item label="Mật khẩu" name="password" rules={[{ required: true, message: 'Nhập mật khẩu.' }]}><Input.Password autoComplete="current-password" /></Form.Item>
      <Button type="primary" htmlType="submit" loading={busy} block>Đăng nhập</Button>
    </Form>
  </Card></Layout>;
}

function Bootstrap() {
  const [config, setConfig] = useState(null);
  const [error, setError] = useState('');
  function load() { setError(''); request('/api/config').then(setConfig).catch(failure => setError(failure.message)); }
  useEffect(load, []);
  // Obtain the nonce before mounting Ant Design so its first injected styles are allowed.
  if (!config) return <div className="bootstrap" role="status">{error ? `${error} Tải lại trang để thử lại.` : 'Đang kết nối không gian báo cáo…'}</div>;
  return <ConfigProvider locale={viVN} csp={config?.style_nonce ? { nonce: config.style_nonce } : undefined} theme={{ token: { colorPrimary: '#245bd7', colorBgLayout: '#f5f7fb', borderRadius: 10, fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif" }, components: { Card: { headerFontSize: 16 }, Layout: { headerBg: '#ffffff' } } }}><AntApp>{config.login_required ? <Login onSuccess={load} /> : <Workspace initialConfig={config} />}</AntApp></ConfigProvider>;
}

createRoot(document.getElementById('root')).render(<Bootstrap />);
