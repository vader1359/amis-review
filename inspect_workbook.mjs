import { FileBlob, SpreadsheetFile } from '@oai/artifact-tool';
import fs from 'node:fs/promises';
const input = await FileBlob.load('/Users/iant1359/Downloads/(ASKademy) DS TỔNG FULL (1).xlsx');
const wb = await SpreadsheetFile.importXlsx(input);
const summary = await wb.inspect({kind:'workbook,sheet,table', maxChars:12000, tableMaxRows:8, tableMaxCols:12, tableMaxCellChars:100});
console.log('SUMMARY', summary.ndjson);
const sheets = await wb.inspect({kind:'sheet', include:'id,name'});
console.log('SHEETS', sheets.ndjson);
for (let i=0; i<20; i++) {
  let s; try { s = wb.worksheets.getItemAt(i); } catch { break; }
  if (!s) break;
  const used = s.getUsedRange();
  console.log('SHEET', s.name, 'USED', used?.address ?? 'none');
  if (used) {
    const out = await wb.inspect({kind:'region', sheetId:s.name, range:used.address, maxChars:10000, tableMaxRows:12, tableMaxCols:20, tableMaxCellChars:120});
    console.log(out.ndjson);
    const blob = await wb.render({sheetName:s.name, autoCrop:'all', scale:1, format:'png'});
    await fs.writeFile(`/Users/iant1359/Develop/amis-review/${s.name.replaceAll('/','_')}.png`, new Uint8Array(await blob.arrayBuffer()));
  }
}
