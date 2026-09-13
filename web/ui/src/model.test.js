import test from 'node:test';
import assert from 'node:assert/strict';
import { appendClassifications, assignmentState, makeDraftForm, mapClassifications, validateBatch } from './model.js';

const files = ['a', 'b', 'c', 'd'].map(name => new File(['excel'], `${name}.xlsx`));
const rows = ['inventory', 'crm', 'revenue', 'product'].map((role, index) => ({ role, file: files[index] }));
const saved = Object.fromEntries(['purchase', 'target', 'manual_check', 'prior_psi'].map(role => [role, { id: `saved-${role}` }]));

test('unordered batch maps by response index and produces every source exactly once', () => {
  const mapped = mapClassifications(files, { files: rows.map((row, index) => ({ role: row.role, index })).reverse() });
  assert.equal(mapped[0].file.name, 'd.xlsx');
  assert.equal(assignmentState(mapped).ready, true);
  const form = makeDraftForm(mapped, saved, '2026-09-03');
  assert.equal(form.get('crm').name, 'b.xlsx');
  assert.equal(form.get('prior_psi'), 'saved-prior_psi');
  assert.equal([...form].length, 9);
});
test('duplicate roles never silently replace a source', () => {
  const invalid = rows.map((row, i) => i === 3 ? { ...row, role: 'crm' } : row);
  assert.deepEqual(assignmentState(invalid).duplicate, ['crm']);
  assert.deepEqual(assignmentState(invalid).missing, ['product']);
  assert.throws(() => makeDraftForm(invalid, saved, '2026-09-03'));
});
test('ambiguous, missing, or corrupt classification results cannot build', () => {
  assert.equal(assignmentState([...rows.slice(0, 3), { ...rows[3], role: null }]).ready, false);
  assert.throws(() => mapClassifications(files, { files: [] }));
  assert.throws(() => mapClassifications(files, { files: [0, 1, 2, 2].map(index => ({ index, role: 'crm' })) }));
  assert.throws(() => makeDraftForm(rows, { ...saved, prior_psi: undefined }, '2026-09-03'));
});
test('invalid file batches reject without replacing current selection', () => {
  assert.equal(validateBatch(files), null);
  assert.match(validateBatch([...files, files[0]]), /tối đa 4/);
  assert.match(validateBatch([new File(['x'], 'wrong.csv')]), /xlsx/);
  assert.match(validateBatch([new File([], 'empty.xlsx')]), /50 MB/);
});


test('single files and successive batches accumulate without losing prior files', () => {
  const first = appendClassifications([], mapClassifications(files.slice(0, 1), { files: [{ index: 0, role: 'inventory' }] }));
  const second = appendClassifications(first, mapClassifications(files.slice(1, 3), { files: [{ index: 0, role: 'crm' }, { index: 1, role: 'revenue' }] }));
  assert.equal(second.length, 3);
  assert.equal(second[0].file, first[0].file);
  assert.equal(assignmentState(second).ready, false);
  const complete = appendClassifications(second, mapClassifications(files.slice(3), { files: [{ index: 0, role: 'product' }] }));
  assert.equal(new Set(complete.map(row => row.key)).size, 4);
  assert.equal(assignmentState(complete).ready, true);
  const form = makeDraftForm(complete, saved, '2026-09-03');
  for (const row of complete) assert.equal(form.get(row.role).name, row.file.name);
});

test('duplicates across batches remain visible and removing one restores readiness', () => {
  const original = appendClassifications([], rows);
  const appended = appendClassifications(original, [{ role: 'crm', file: new File(['new'], 'new-crm.xlsx'), key: '0' }]);
  assert.equal(new Set(appended.map(row => row.key)).size, 5);
  assert.deepEqual(assignmentState(appended).duplicate, ['crm']);
  assert.throws(() => makeDraftForm(appended, saved, '2026-09-03'));
  const kept = appended.filter(row => row.key !== original.find(row => row.role === 'crm').key);
  assert.equal(assignmentState(kept).ready, true);
  assert.equal(makeDraftForm(kept, saved, '2026-09-03').get('crm').name, 'new-crm.xlsx');
  const removed = original.filter(row => row.key !== original[3].key);
  assert.equal(new Set(appendClassifications(removed, [{ role: 'product', file: files[3] }]).map(row => row.key)).size, 4);
});
