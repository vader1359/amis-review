import fs from 'node:fs/promises';
import { Workbook, SpreadsheetFile } from '@oai/artifact-tool';
const data=JSON.parse(await fs.readFile('/tmp/amis-sheet/clean_data.json','utf8'));
const wb=Workbook.create();
const summary=wb.worksheets.add('Tổng quan');
const sales=wb.worksheets.add('Doanh thu đã lọc');
const inv=wb.worksheets.add('Tồn cuối kỳ đã lọc');
const rules=wb.worksheets.add('Quy tắc lọc');
const headerFmt={fill:'#1F4E78',font:{bold:true,color:'#FFFFFF'},wrapText:true,verticalAlignment:'center'};
const titleFmt={fill:'#D9EAF7',font:{bold:true,color:'#17365D',size:14}};
function writeTable(sh,headers,rows){
  sh.getRangeByIndexes(0,0,1,headers.length).values=[headers];
  if(rows.length) sh.getRangeByIndexes(1,0,rows.length,headers.length).values=rows;
  sh.getRangeByIndexes(0,0,1,headers.length).format=headerFmt;
  sh.getRangeByIndexes(0,0,Math.max(1,rows.length+1),headers.length).format.borders={preset:'all',style:'thin',color:'#D9E2F3'};
  sh.freezePanes.freezeRows(1); sh.showGridLines=false;
}
summary.getRange('A1:F1').merge(); summary.getRange('A1').values=[['KẾT QUẢ LỌC SỔ BÁN HÀNG VÀ TỒN KHO']]; summary.getRange('A1:F1').format=titleFmt;
const s=data.summary;
summary.getRange('A3:B10').values=[['Chỉ tiêu','Giá trị'],['Số dòng sổ bán hàng ban đầu',s.sales_total_rows],['Số dòng doanh thu giữ lại',s.sales_kept_rows],['Số dòng loại khỏi sổ bán hàng',s.sales_removed_rows],['Tổng doanh số bán giữ lại',s.sales_revenue],['Số dòng tồn kho ban đầu',s.inventory_total_rows],['Số dòng tồn kho giữ lại',s.inventory_kept_rows],['Số dòng tồn kho loại bỏ',s.inventory_removed_rows]];
summary.getRange('A3:B3').format=headerFmt; summary.getRange('A3:B10').format.borders={preset:'all',style:'thin',color:'#D9E2F3'}; summary.getRange('B7').format.numberFormat='#,##0';
summary.getRange('D3:E5').values=[['Tồn cuối kỳ sau lọc','Giá trị'],['Tổng số lượng',s.inventory_qty],['Tổng giá trị',s.inventory_value]]; summary.getRange('D3:E3').format=headerFmt; summary.getRange('D3:E5').format.borders={preset:'all',style:'thin',color:'#D9E2F3'}; summary.getRange('E4:E5').format.numberFormat='#,##0';
summary.getRange('A12:F12').merge(); summary.getRange('A12').values=[['Kho loại khỏi tồn kho']]; summary.getRange('A12:F12').format=titleFmt; summary.getRangeByIndexes(12,0,s.excluded_warehouses.length,1).values=s.excluded_warehouses.map(x=>[x]);
writeTable(sales,data.sales_headers,data.sales);
writeTable(inv,data.inventory_headers,data.inventory);
rules.getRange('A1:D1').merge(); rules.getRange('A1').values=[['QUY TẮC LỌC ĐÃ ÁP DỤNG']]; rules.getRange('A1:D1').format=titleFmt;
rules.getRange('A3:B7').values=[['Phạm vi','Quy tắc'],['Sổ chi tiết bán hàng','Giữ dòng nếu TK Nợ hoặc TK Có là 5111, 5112 hoặc 5113.'],['Sổ chi tiết bán hàng','Loại dòng có KT note = Không phải Revenue.'],['Tồn kho','Chỉ lấy hai cột Cuối kỳ: Số lượng và Giá trị.'],['Tồn kho','Loại kho lỗi, Kho Chị Kathy, Kho chưa xuất hóa đơn và dòng KT note = Loại khỏi tồn kho.']]; rules.getRange('A3:B3').format=headerFmt; rules.getRange('A3:B7').format.borders={preset:'all',style:'thin',color:'#D9E2F3'}; rules.getRange('B3:B7').format.wrapText=true;
for(const sh of [summary,sales,inv,rules]){sh.getUsedRange()?.format.autofitColumns();}
summary.getRange('A:A').format.columnWidth=30; summary.getRange('B:B').format.columnWidth=18; summary.getRange('D:D').format.columnWidth=24; rules.getRange('B:B').format.columnWidth=80;
sales.getRange('A:V').format.columnWidth=16; sales.getRange('I:L').format.columnWidth=32; sales.getRange('A:B').setNumberFormat('yyyy-mm-dd'); sales.getRange('D:D').setNumberFormat('yyyy-mm-dd'); sales.getRange('Q:R').setNumberFormat('#,##0');
inv.getRange('A:I').format.columnWidth=18; inv.getRange('D:D').format.columnWidth=42; inv.getRange('F:G').setNumberFormat('#,##0');
await fs.mkdir('/Users/iant1359/Develop/amis-review/outputs',{recursive:true});
const out=await SpreadsheetFile.exportXlsx(wb); await out.save('/Users/iant1359/Develop/amis-review/outputs/So_ban_hang_va_ton_kho_da_loc_09.07.2026.xlsx');
console.log('exported');
