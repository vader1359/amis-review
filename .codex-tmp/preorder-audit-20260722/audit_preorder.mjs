import { FileBlob, SpreadsheetFile } from '@oai/artifact-tool';

const sourcePath = '/Users/iant1359/Develop/amis-review/input/Pre order feedback.xlsx';
const input = await FileBlob.load(sourcePath);
const workbook = await SpreadsheetFile.importXlsx(input);

const sheets = await workbook.inspect({
  kind: 'sheet',
  include: 'id,name',
  maxChars: 3000,
});
const sample = await workbook.inspect({
  kind: 'region',
  sheetId: 'Pre-orders',
  range: 'A1:K25',
  maxChars: 12000,
  tableMaxRows: 25,
  tableMaxCols: 11,
  tableMaxCellChars: 160,
});
const sheet = workbook.worksheets.getItem('Pre-orders');
const rows = sheet.getRange('A2:J403').values;
const noteCounts = {};
const orderNotes = {};
for (const row of rows) {
  const note = String(row[9] ?? '').trim() || '(blank)';
  noteCounts[note] = (noteCounts[note] || 0) + 1;
  const order = String(row[7] ?? '').trim();
  if (order) {
    orderNotes[order] ||= new Set();
    orderNotes[order].add(note);
  }
}
const mixedOrders = Object.entries(orderNotes)
  .filter(([, notes]) => notes.size > 1)
  .map(([order, notes]) => [order, [...notes]]);

console.log('SHEETS');
console.log(sheets.ndjson);
console.log('SAMPLE');
console.log(sample.ndjson);
console.log('NOTE_COUNTS');
console.log(JSON.stringify(noteCounts));
console.log('MIXED_ORDER_NOTES');
console.log(JSON.stringify(mixedOrders));
