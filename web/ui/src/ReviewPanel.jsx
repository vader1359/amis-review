import React, { useEffect, useMemo, useRef, useState } from 'react';
import { Alert, Button, Card, Checkbox, Descriptions, Form, Input, Modal, Select, Space, Table, Tabs, Tag, Typography } from 'antd';
import { QueryClient, QueryClientProvider, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { requestJson } from './request.js';
import { applicableProposal, awaitReviewJob, filterEvidence, needsAttention, notesForRow, proposalState, reviewFieldLabel } from './reviewModel.js';

const { Text, Paragraph } = Typography;
const actionNames = { note: 'Ghi chú lỗi', exclude_preorder: 'Loại dòng khỏi Preorder', exclude_order: 'Loại cả đơn khỏi PSI và Preorder' };
const statusNames = { proposed: 'Chờ áp dụng', pending: 'Chờ áp dụng', applied: 'Đã áp dụng', superseded: 'Đã thay thế', rejected: 'Không áp dụng' };
const kindNames = { added: 'Bổ sung', removed: 'Không còn trong kỳ này', changed: 'Thay đổi', completed: 'Hoàn thành', newly_completed: 'Mới hoàn thành', new_preorder: 'Preorder bổ sung', completed_changed: 'Đơn hoàn thành thay đổi' };
const reviewErrors = {
  REVIEW_REVISION_CONFLICT: 'Một người khác vừa cập nhật ghi chú. Danh sách đang được làm mới; kiểm tra lại trước khi gửi.',
  REVIEW_PROPOSAL_NOT_APPLICABLE: 'Đề xuất đã được áp dụng hoặc thay thế. Kiểm tra lại danh sách mới nhất.',
  REVIEW_INPUT_INVALID: 'Nội dung ghi chú chưa hợp lệ. Kiểm tra đơn hàng, SKU, người ghi nhận và lý do.',
  REVIEW_REQUEST_CONFLICT: 'Yêu cầu trước có nội dung khác. Làm mới danh sách trước khi gửi lại.',
  PROPOSAL_REVISION_CONFLICT: 'Danh sách ghi chú vừa thay đổi. Làm mới và kiểm tra lại trước khi gửi.',
  REVIEW_SOURCES_UNAVAILABLE: 'Báo cáo này chưa có đủ bộ nguồn để xuất lại. Bạn vẫn có thể ghi nhận lỗi.',
  REVIEW_SOURCE_UNAVAILABLE: 'Báo cáo này chưa có đủ bộ nguồn để xuất lại. Bạn vẫn có thể ghi nhận lỗi.',
  REVIEW_AI_UNAVAILABLE: 'Chưa kết nối được AI. Các giải thích theo dữ liệu vẫn hiển thị bên dưới.',
  AI_UNAVAILABLE: 'Chưa kết nối được AI. Các giải thích theo dữ liệu vẫn hiển thị bên dưới.',
  PREVIEW_TOKEN_REQUIRED: 'Phiên làm việc đã thay đổi. Tải lại trang để tiếp tục.',
  ONLINE_STORAGE_UNAVAILABLE: 'Chưa kết nối được nơi lưu online. Vui lòng thử lại.',
  ONLINE_REPORT_NOT_FOUND: 'Không tìm thấy báo cáo đã lưu.',
};

function showValue(value) {
  if (value === undefined || value === null || value === '') return '—';
  if (typeof value === 'boolean') return value ? 'Có' : 'Không';
  if (Array.isArray(value)) return value.length ? value.map(showValue).join('; ') : 'Không có';
  if (typeof value === 'object') return JSON.stringify(value);
  return String(value);
}

function Details({ value, fields }) {
  if (!value || typeof value !== 'object') return <Text>{showValue(value)}</Text>;
  return <Descriptions size="small" column={1} items={Object.entries(value).filter(([key]) => !fields || fields.includes(key)).map(([key, item]) => ({ key, label: reviewFieldLabel(key), children: <Text style={{ overflowWrap: 'anywhere' }}>{showValue(item)}</Text> }))} />;
}

function EvidenceTable({ rows, columns, attentionFilter = false, extra, rowSelection }) {
  const [search, setSearch] = useState('');
  const [onlyAttention, setOnlyAttention] = useState(false);
  const [page, setPage] = useState(1);
  const filtered = useMemo(() => filterEvidence(rows, search, onlyAttention), [rows, search, onlyAttention]);
  return <Space orientation="vertical" size={12} style={{ width: '100%' }}>
    <Space wrap><Input.Search aria-label="Tìm đơn, SKU hoặc nội dung" placeholder="Tìm đơn, SKU hoặc nội dung" allowClear value={search} onChange={event => { setSearch(event.target.value); setPage(1); }} style={{ width: 280, maxWidth: '100%' }} />{attentionFilter && <Checkbox checked={onlyAttention} onChange={event => { setOnlyAttention(event.target.checked); setPage(1); }}>Chỉ cần lưu ý</Checkbox>}{extra}</Space>
    <Table size="small" rowKey="id" columns={columns} dataSource={filtered} rowSelection={rowSelection} scroll={{ x: 1000 }} pagination={{ current: page, onChange: setPage, defaultPageSize: 20, showSizeChanger: true, pageSizeOptions: [20, 50, 100], showTotal: total => `${total} dòng${search || onlyAttention ? ` / ${rows.length} dòng tổng cộng` : ''}` }} locale={{ emptyText: search || onlyAttention ? 'Không có dòng khớp bộ lọc' : 'Không có dữ liệu trong nhóm này' }} />
  </Space>;
}

function ReviewContent({ report, previewToken, onReportCreated }) {
  const client = useQueryClient();
  const id = report.id || report.report_id;
  const queryKey = ['psi-review', id];
  const endpoint = `/api/reports/${encodeURIComponent(id)}`;
  const [target, setTarget] = useState(null);
  const [selected, setSelected] = useState([]);
  const [applyOpen, setApplyOpen] = useState(false);
  const [aiExplanations, setAiExplanations] = useState({});
  const lastRequests = useRef({});
  const pollController = useRef(null);
  useEffect(() => { pollController.current = new AbortController(); return () => pollController.current.abort(); }, []);
  const [form] = Form.useForm();
  const [applyForm] = Form.useForm();
  const action = Form.useWatch('action', form);
  const query = useQuery({ queryKey, queryFn: () => requestJson(`${endpoint}/review`, {}, reviewErrors), enabled: Boolean(id), staleTime: 30_000, retry: 1 });
  const data = query.data;
  const proposals = data?.proposals?.items || [];
  useEffect(() => { if (data) setSelected(current => current.filter(selectedId => data.proposals.items.some(item => item.id === selectedId && applicableProposal(item)))); }, [data]);
  function withRequestId(path, body) {
    const signature = JSON.stringify(body);
    if (lastRequests.current[path]?.signature !== signature) lastRequests.current[path] = { signature, id: crypto.randomUUID() };
    return { ...body, request_id: lastRequests.current[path].id };
  }
  const post = (path, body) => requestJson(`${endpoint}/${path}`, { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-PSI-Preview': previewToken }, body: JSON.stringify(body), timeoutMs: 90_000 }, reviewErrors);
  const refresh = () => client.invalidateQueries({ queryKey });
  const propose = useMutation({ mutationFn: values => post('proposals', withRequestId('proposals', { ...values, order_id: target.order_id, sku: values.action === 'exclude_order' ? '' : target.sku || '', expected_revision: data.proposals.revision })), onSuccess: async () => { setTarget(null); form.resetFields(); await refresh(); }, onError: refresh });
  const apply = useMutation({ mutationFn: async values => {
    const started = Date.now();
    const initial = await post('apply', withRequestId('apply', { ...values, proposal_ids: selected, expected_revision: data.proposals.revision }));
    return awaitReviewJob(initial, (jobId, remaining) => client.fetchQuery({
      queryKey: ['psi-review-job', jobId], staleTime: 0, retry: false,
      queryFn: () => requestJson(`/api/review-jobs/${encodeURIComponent(jobId)}`, { timeoutMs: Math.min(30_000, remaining) }, reviewErrors),
    }), { timeoutMs: Math.max(0, 600_000 - (Date.now() - started)), signal: pollController.current?.signal, errorMessage: code => reviewErrors[code] || 'Chưa thể hoàn tất bản Draft mới. Kiểm tra nguồn và thử lại.' });
  }, onSuccess: async result => { setApplyOpen(false); setSelected([]); applyForm.resetFields(); await refresh(); onReportCreated?.(result.report || result); }, onError: refresh });
  const ai = useMutation({ mutationFn: itemId => post('explain', { item_ids: [itemId] }), onSuccess: result => setAiExplanations(current => ({ ...current, ...Object.fromEntries((result.explanations || []).map(item => [item.evidence_id, item])) })) });
  const busy = propose.isPending || apply.isPending;
  const openProposal = row => { propose.reset(); form.resetFields(); form.setFieldsValue({ action: 'note' }); setTarget(row); };
  const identityColumns = [
    { title: 'Đơn hàng', dataIndex: 'order_id', width: 150, render: showValue },
    { title: 'SKU', dataIndex: 'sku', width: 160, render: showValue },
  ];
  const noteColumn = { title: 'Ghi chú lỗi kế toán', key: 'accounting', width: 240, render: (_, row) => <Space orientation="vertical" size={4}>{notesForRow(proposals, row).map(item => <Text key={item.id}>{item.author}: {item.note} <Tag>{statusNames[proposalState(item)] || proposalState(item)}</Tag></Text>)}<Button size="small" disabled={!row.order_id || busy} onClick={() => openProposal(row)}>Ghi chú / đề xuất loại</Button></Space> };
  const explainColumn = { title: 'Lý do và bằng chứng', key: 'explanation', width: 350, render: (_, row) => <Space orientation="vertical" size={4}><Text>{showValue(row.explanation || row.reasons)}</Text>{row.evidence && <Details value={row.evidence} />}{row.suggested_action && <Text type="secondary">Cần kiểm tra: {row.suggested_action}</Text>}{data?.ai?.enabled && <Button size="small" loading={ai.isPending && ai.variables === row.id} disabled={ai.isPending || busy} onClick={() => ai.mutate(row.id)}>Nhờ AI giải thích</Button>}{Object.values(aiExplanations).filter(item => item.evidence_id === row.id).map(item => <Alert key={item.evidence_id} type="info" showIcon title="AI · Giả thuyết cần xác nhận" description={item.explanation} />)}</Space> };
  if (!id) return <Alert type="info" showIcon title="Cần lưu báo cáo online để mở phần rà soát và ghi chú." />;
  return <Card title="Rà soát sau xuất báo cáo" extra={<Button loading={query.isFetching} disabled={busy} onClick={() => void refresh()}>Làm mới</Button>} style={{ marginTop: 24 }}>
    <Space orientation="vertical" size={16} style={{ width: '100%' }}>
      <Paragraph type="secondary" style={{ marginBottom: 0 }}>Kiểm tra chênh lệch và ghi nhận lỗi. Đề xuất chỉ có hiệu lực khi chọn và tạo một bản Draft mới; báo cáo gốc được giữ nguyên. Quyết định đã áp dụng được tự động giữ cho các kỳ sau.</Paragraph>
      {query.isPending && <Alert type="info" showIcon title="Đang đối chiếu dữ liệu báo cáo…" />}
      {query.error && <Alert type="error" showIcon title="Chưa tải được kết quả rà soát" description={query.error.message} />}
      {ai.error && <Alert type="warning" showIcon title="Chưa có giải thích AI" description={ai.error.message} />}
      {ai.data?.disclaimer && <Alert type="info" showIcon title={ai.data.disclaimer} />}
      {data && <>
        <Space wrap><Tag color="orange">Mismatch: {data.mismatches.length}</Tag><Tag color="blue">Thay đổi: {data.changes.length}</Tag><Tag>Kiểm tra Preorder: {data.preorder_checks.length}</Tag><Tag>Ghi chú / đề xuất: {proposals.length}</Tag></Space>
        <Alert type={data.baseline?.status === 'available' ? 'info' : 'warning'} showIcon title={data.baseline?.status === 'available' ? `Đối chiếu với PSI Final ngày ${data.baseline.as_of || 'chưa xác định'}` : 'Thiếu PSI Final kỳ trước: chưa thể kết luận chênh lệch tuần và Preorder mới'} />
        {!data.ai?.enabled && <Text type="secondary">AI chưa được kết nối. Lý do bên dưới được xác định trực tiếp từ dữ liệu và quy tắc đối soát.</Text>}
        <Tabs items={[
          { key: 'mismatches', label: 'Mismatch và lý do', children: <EvidenceTable rows={data.mismatches} columns={[...identityColumns, { title: 'Vấn đề', dataIndex: 'issue', width: 220, render: (value, row) => <Space orientation="vertical" size={4}><Text>{showValue(value)}</Text>{row.is_new && <Tag color="orange">Mới phát sinh</Tag>}</Space> }, explainColumn, noteColumn]} /> },
          { key: 'changes', label: 'Khác biệt so với kỳ trước', children: <EvidenceTable rows={data.changes} attentionFilter columns={[...identityColumns, { title: 'Thay đổi', dataIndex: 'kind', width: 180, render: (value, row) => <Space orientation="vertical" size={4}><Text>{kindNames[value] || showValue(value)}</Text>{needsAttention(row) ? <Tag color="orange">Cần lưu ý</Tag> : <Tag color="green">Không có nghi vấn theo quy tắc</Tag>}<Text type="secondary">{Array.isArray(row.changed_fields) ? row.changed_fields.map(reviewFieldLabel).join(', ') : showValue(row.changed_fields)}</Text></Space> }, { title: 'Kỳ trước', dataIndex: 'before', width: 260, render: (value, row) => <Details value={value} fields={row.changed_fields} /> }, { title: 'Kỳ này', dataIndex: 'after', width: 260, render: (value, row) => <Details value={value} fields={row.changed_fields} /> }, explainColumn, noteColumn]} /> },
          { key: 'preorder', label: 'Kiểm tra Preorder', children: <EvidenceTable rows={data.preorder_checks} attentionFilter columns={[...identityColumns, { title: 'Đánh giá', dataIndex: 'issue', width: 220, render: (value, row) => <Space orientation="vertical" size={4}><Text>{value ? showValue(value) : needsAttention(row) ? 'Có điểm cần xác nhận' : 'Đã kiểm tra các quy tắc'}</Text>{row.is_new === null ? <Tag>Chưa rõ có mới bổ sung</Tag> : row.is_new && <Tag color="blue">Đơn bổ sung</Tag>}<Tag color={needsAttention(row) ? 'orange' : 'green'}>{needsAttention(row) ? 'Cần kiểm tra' : 'Chưa phát hiện nghi vấn theo quy tắc'}</Tag></Space> }, explainColumn, noteColumn]} /> },
          { key: 'proposals', label: 'Ghi chú và đề xuất kế toán', children: <Space orientation="vertical" size={12} style={{ width: '100%' }}>
            {!data.can_rebuild && <Alert type="warning" showIcon title="Chưa thể xuất bản chỉnh sửa" description="Báo cáo này chưa có đủ bộ nguồn lưu kèm. Ghi chú vẫn được lưu để theo dõi." />}
            <EvidenceTable rows={proposals} rowSelection={{ selectedRowKeys: selected, onChange: setSelected, getCheckboxProps: item => ({ disabled: busy || !data.can_rebuild || !applicableProposal(item) }) }} columns={[...identityColumns, { title: 'Đề xuất', dataIndex: 'action', width: 210, render: value => actionNames[value] || value }, { title: 'Ghi chú lỗi', dataIndex: 'note', width: 280 }, { title: 'Người ghi nhận', dataIndex: 'author', width: 150 }, { title: 'Trạng thái', key: 'state', width: 140, render: (_, item) => <Tag>{statusNames[proposalState(item)] || proposalState(item)}</Tag> }]} extra={<Button type="primary" disabled={!data.can_rebuild || !selected.length || busy} onClick={() => { apply.reset(); setApplyOpen(true); }}>Tạo Draft mới từ {selected.length} đề xuất</Button>} />
          </Space> },
        ]} />
      </>}
    </Space>
    <Modal title="Ghi chú lỗi / đề xuất chỉnh sửa" open={Boolean(target)} onCancel={() => { if (!propose.isPending) setTarget(null); }} onOk={() => form.submit()} confirmLoading={propose.isPending} cancelButtonProps={{ disabled: propose.isPending }} closable={!propose.isPending} mask={{ closable: !propose.isPending }} okText="Lưu đề xuất" cancelText="Hủy">
      <Paragraph>Đơn <Text strong>{target?.order_id}</Text> · SKU <Text strong>{target?.sku || '—'}</Text></Paragraph>
      {propose.error && <Alert type="error" showIcon title={propose.error.message} />}
      <Form form={form} layout="vertical" onFinish={values => propose.mutate(values)} disabled={propose.isPending}>
        <Form.Item name="action" label="Nội dung đề xuất" rules={[{ required: true }]}><Select options={Object.entries(actionNames).map(([value, label]) => ({ value, label, disabled: value === 'exclude_preorder' && !target?.sku }))} /></Form.Item>
        {action !== 'note' && <Alert type="warning" showIcon title={action === 'exclude_order' ? 'Phạm vi: toàn bộ đơn hàng, tất cả SKU' : 'Phạm vi: đúng đơn hàng + SKU đang chọn trong Preorder'} description={action === 'exclude_order' ? 'Đơn này sẽ bị loại khỏi các sheet nghiệp vụ PSI và Preorder trong bản Draft mới. Dữ liệu nguồn và báo cáo gốc vẫn được giữ.' : 'Chỉ loại dòng Preorder đã chọn; các dòng SKU khác của đơn được giữ. Cần tạo Draft mới để áp dụng.'} />}
        <Form.Item name="note" label="Ghi chú lỗi / lý do" rules={[{ required: true, whitespace: true, message: 'Nhập lý do để người duyệt có thể kiểm tra.' }, { max: 2000 }]}><Input.TextArea rows={4} maxLength={2000} showCount /></Form.Item>
        <Form.Item name="author" label="Người ghi nhận" extra="Tên tự khai để theo dõi; tài khoản dùng chung chưa xác minh danh tính riêng." rules={[{ required: true, whitespace: true, message: 'Nhập tên người ghi nhận.' }, { max: 120 }]}><Input autoComplete="name" maxLength={120} /></Form.Item>
      </Form>
    </Modal>
    <Modal title="Xác nhận tạo bản Draft chỉnh sửa" open={applyOpen} onCancel={() => { if (!apply.isPending) setApplyOpen(false); }} onOk={() => applyForm.submit()} confirmLoading={apply.isPending} cancelButtonProps={{ disabled: apply.isPending }} closable={!apply.isPending} mask={{ closable: !apply.isPending }} okText="Áp dụng và kiểm định bản mới" cancelText="Quay lại">
      <Paragraph>Áp dụng {selected.length} đề xuất dưới đây, tính lại PSI và kiểm định trước khi lưu bản Draft mới.</Paragraph>
      {proposals.filter(item => selected.includes(item.id)).map(item => <Paragraph key={item.id}><Text strong>{item.order_id}{item.sku ? ` · ${item.sku}` : ' · Tất cả SKU'}</Text>: {actionNames[item.action]} — {item.note}</Paragraph>)}
      {apply.isPending && <Alert type="info" showIcon title="Đang tính lại và kiểm định bản Draft mới…" description="Báo cáo được xử lý trên máy chủ. Giữ trang này mở; kết quả sẽ tự cập nhật khi hoàn tất." />}
      {apply.error && <Alert type="error" showIcon title="Chưa xác nhận được bản mới" description={`${apply.error.message} Nếu kết nối bị gián đoạn, kiểm tra lịch sử báo cáo trước khi thử lại.`} />}
      <Form form={applyForm} layout="vertical" onFinish={values => apply.mutate(values)} disabled={apply.isPending}><Form.Item name="author" label="Người xác nhận áp dụng" extra="Tên tự khai để theo dõi; tài khoản dùng chung chưa xác minh danh tính riêng." rules={[{ required: true, whitespace: true, message: 'Nhập tên người xác nhận.' }, { max: 120 }]}><Input maxLength={120} /></Form.Item></Form>
    </Modal>
  </Card>;
}

export default function ReviewPanel(props) {
  const [client] = useState(() => new QueryClient());
  return <QueryClientProvider client={client}><ReviewContent key={props.report.id || props.report.report_id} {...props} /></QueryClientProvider>;
}
