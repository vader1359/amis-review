export const periodicRoles = ['crm', 'product', 'revenue', 'inventory'];
export const retainedRoles = ['purchase', 'target', 'manual_check', 'prior_psi'];
export const labels = {
  crm: 'CRM Sales Order', product: 'CRM Product Master',
  revenue: 'Sổ chi tiết bán hàng', inventory: 'Tổng hợp tồn kho',
  purchase: 'Purchase / Loading List', target: 'Target',
  manual_check: 'Manual Check', prior_psi: 'PSI Final kỳ trước',
};

export function assignmentState(rows) {
  const counts = Object.fromEntries(periodicRoles.map(role => [role, rows.filter(row => row.role === role).length]));
  const missing = periodicRoles.filter(role => counts[role] === 0);
  const duplicate = periodicRoles.filter(role => counts[role] > 1);
  return { missing, duplicate, ready: rows.length === 4 && rows.every(row => periodicRoles.includes(row.role)) && !missing.length && !duplicate.length };
}

export function validateBatch(files) {
  if (!files.length || files.length > 4) return 'Chọn tối đa 4 file nguồn kỳ báo cáo trong một lần.';
  if (files.some(file => !/\.xlsx$/i.test(file.name))) return 'Chỉ nhận file Excel .xlsx.';
  if (files.some(file => !file.size || file.size > 50 * 1024 * 1024)) return 'Mỗi file cần có dữ liệu và không vượt quá 50 MB.';
  return null;
}

export function mapClassifications(files, response) {
  if (!Array.isArray(response.files) || response.files.length !== files.length) throw new Error('Kết quả nhận diện chưa đầy đủ. Vui lòng thử tải lại bộ file.');
  const seen = new Set();
  for (const row of response.files) {
    if (!Number.isInteger(row.index) || row.index < 0 || row.index >= files.length || seen.has(row.index)) throw new Error('Kết quả nhận diện không khớp bộ file. Vui lòng thử lại.');
    seen.add(row.index);
  }
  return response.files.map(row => ({ ...row, key: String(row.index), file: files[row.index], role: periodicRoles.includes(row.role) ? row.role : null }));
}

export function appendClassifications(current, incoming) {
  let nextKey = current.reduce((next, row) => {
    const key = Number(row.key);
    return Number.isSafeInteger(key) ? Math.max(next, key + 1) : next;
  }, 0);
  return [...current, ...incoming.map(row => ({ ...row, key: String(nextKey++) }))];
}

export function makeDraftForm(rows, saved, cutoff) {
  if (!assignmentState(rows).ready || retainedRoles.some(role => !saved[role]?.id) || !cutoff) throw new Error('Chọn đủ nguồn và ngày chốt trước khi tạo báo cáo.');
  const form = new FormData();
  form.append('as_of', cutoff);
  for (const row of rows) form.append(row.role, row.file, row.file.name);
  for (const role of retainedRoles) form.append(role, saved[role].id);
  return form;
}
