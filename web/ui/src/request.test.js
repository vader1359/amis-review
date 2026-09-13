import test from 'node:test';
import assert from 'node:assert/strict';
import { requestJson } from './request.js';

test('a stalled upload is aborted and returns a recoverable error', async context => {
  let uploadSignal;
  context.mock.method(globalThis, 'fetch', (_path, { signal }) => {
    uploadSignal = signal;
    return new Promise((_resolve, reject) => signal.addEventListener('abort', () => reject(new DOMException('Aborted', 'AbortError')), { once: true }));
  });
  await assert.rejects(requestJson('/api/sources/classify', { timeoutMs: 5 }), /Kiểm tra file có đọc được/);
  assert.equal(uploadSignal.aborted, true);
});

test('timeout also covers a stalled response body after upload succeeds', async context => {
  context.mock.method(globalThis, 'fetch', async (_path, { signal }) => ({
    ok: true,
    json: () => new Promise((_resolve, reject) => signal.addEventListener('abort', () => reject(new DOMException('Aborted', 'AbortError')), { once: true })),
  }));
  await assert.rejects(requestJson('/api/drafts', { timeoutMs: 5 }), /Tác vụ có thể vẫn đang xử lý/);
});
