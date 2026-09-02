import fs from 'node:fs/promises';
import { FileBlob, SpreadsheetFile } from '@oai/artifact-tool';
const p='/Users/iant1359/Develop/amis-review/outputs/So_ban_hang_va_ton_kho_da_loc_09.07.2026.xlsx';
const wb=await SpreadsheetFile.importXlsx(await FileBlob.load(p));
console.log((await wb.inspect({kind:'sheet',include:'id,name',maxChars:5000})).ndjson);
console.log((await wb.inspect({kind:'table',sheetId:'Tổng quan',range:'A1:F15',include:'values,formulas',tableMaxRows:15,tableMaxCols:6,maxChars:6000})).ndjson);
console.log((await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A',options:{useRegex:true,maxResults:100},summary:'formula errors'})).ndjson);
for(const [sheetName,range,file] of [['Tổng quan','A1:F15','verify_summary.png'],['Doanh thu đã lọc','A1:V12','verify_sales.png'],['Tồn cuối kỳ đã lọc','A1:I12','verify_inventory.png']]){
  const b=await wb.render({sheetName,range,scale:1,format:'png'}); await fs.writeFile('/Users/iant1359/Develop/amis-review/outputs/'+file,new Uint8Array(await b.arrayBuffer()));
}
