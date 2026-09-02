import { FileBlob, SpreadsheetFile } from '@oai/artifact-tool';

const files = process.argv.slice(2);
for (const path of files) {
  const wb = await SpreadsheetFile.importXlsx(await FileBlob.load(path));
  console.log(`=== ${path} ===`);
  console.log((await wb.inspect({kind:'sheet', include:'id,name', maxChars:4000})).ndjson);
  console.log((await wb.inspect({kind:'workbook,sheet,table', maxChars:10000, tableMaxRows:8, tableMaxCols:16, tableMaxCellChars:100})).ndjson);
}
