import test from 'node:test';
import assert from 'node:assert/strict';
import { applicableProposal, awaitReviewJob, filterEvidence, notesForRow, reviewFieldLabel } from './reviewModel.js';

test('full-order notes are visible beside each SKU without leaking to another order', () => {
  const all = [{ id: 'all', order_id: 'O1', sku: '' }, { id: 'one', order_id: 'O1', sku: 'A' }, { id: 'other', order_id: 'O2', sku: '' }];
  assert.deepEqual(notesForRow(all, { order_id: 'O1', sku: 'A' }).map(row => row.id), ['all', 'one']);
  assert.deepEqual(notesForRow(all, { order_id: 'O1', sku: 'B' }).map(row => row.id), ['all']);
});

test('ordinary completed changes remain visible until the attention filter is explicitly enabled', () => {
  const rows = [{ id: 'ordinary', order_id: 'O1', needs_attention: false, after: { state: 'Hoàn thành' } }, { id: 'warning', order_id: 'O2', needs_attention: true }, { id: 'preorder', verdict: 'needs_review' }];
  assert.equal(filterEvidence(rows, '', false).length, 3);
  assert.deepEqual(filterEvidence(rows, '', true).map(row => row.id), ['warning', 'preorder']);
  assert.deepEqual(filterEvidence(rows, 'HOÀN THÀNH', false).map(row => row.id), ['ordinary']);
});

test('applied proposals and notes cannot be selected for another exclusion build', () => {
  assert.equal(applicableProposal({ state: 'applied', action: 'exclude_order' }), false);
  assert.equal(applicableProposal({ state: 'proposed', action: 'note' }), false);
  assert.equal(applicableProposal({ state: 'proposed', action: 'exclude_preorder' }), true);
  assert.equal(applicableProposal({ state: 'unknown', action: 'exclude_order' }), false);
});

test('async apply waits through running states and only delivers the completed report', async () => {
  let time = 0;
  const polls = [];
  const report = { id: 'new-report', download_url: '/download/new-report' };
  const result = await awaitReviewJob({ job_id: 'job-1', status: 'running' }, async (id, budget) => {
    polls.push({ id, budget });
    return polls.length === 2 ? { status: 'completed', report } : { status: 'running' };
  }, { now: () => time, sleep: async milliseconds => { time += milliseconds; } });
  assert.equal(result.report, report);
  assert.deepEqual(polls, [{ id: 'job-1', budget: 598500 }, { id: 'job-1', budget: 597000 }]);
});

test('async apply propagates translated failure without claiming a new report', async () => {
  await assert.rejects(awaitReviewJob({ job_id: 'job-1', status: 'running' }, async () => ({ status: 'failed', error: 'VALIDATION_FAILED' }), {
    sleep: async () => {}, errorMessage: code => code === 'VALIDATION_FAILED' ? 'Kiểm định chưa đạt' : code,
  }), /Kiểm định chưa đạt/);
});

test('job polling stops at its deadline and does not start a request after it', async () => {
  let time = 0;
  let polls = 0;
  await assert.rejects(awaitReviewJob({ job_id: 'job-1', status: 'running' }, async () => { polls += 1; return { status: 'running' }; }, {
    timeoutMs: 3000, now: () => time, sleep: async milliseconds => { time += milliseconds; },
  }), /10 phút/);
  assert.equal(time, 3000);
  assert.equal(polls, 1);
});

test('completed idempotent retries do not poll and abandoned panels stop polling', async () => {
  const report = { id: 'ready' };
  assert.equal(await awaitReviewJob(report, () => assert.fail('Already completed')), report);
  const controller = new AbortController();
  controller.abort();
  await assert.rejects(awaitReviewJob({ job_id: 'job-1', status: 'running' }, () => assert.fail('Aborted'), { signal: controller.signal }), /dừng theo dõi/);
});

test('changed-field names use the same Vietnamese labels as their evidence details', () => {
  assert.equal(reviewFieldLabel('open_quantity'), 'Số lượng còn mở');
  assert.equal(reviewFieldLabel('payment_status'), 'Trạng thái thanh toán');
  assert.equal(reviewFieldLabel('new_unknown_field'), 'new_unknown_field');
});
