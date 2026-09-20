import fs from "node:fs/promises";
import path from "node:path";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const inputPath = path.resolve("outputs/PSI-Final-Remote-2026-07.xlsx");
const renderDir = path.resolve(".codex-tmp/psi-verify/renders");
await fs.mkdir(renderDir, { recursive: true });

const input = await FileBlob.load(inputPath);
const workbook = await SpreadsheetFile.importXlsx(input);

const overview = await workbook.inspect({
  kind: "workbook,sheet,table",
  maxChars: 8000,
  tableMaxRows: 6,
  tableMaxCols: 10,
  tableMaxCellChars: 80,
});
console.log("OVERVIEW");
console.log(overview.ndjson);

const errors = await workbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
  options: { useRegex: true, maxResults: 300 },
  summary: "final formula error scan",
});
console.log("FORMULA_ERRORS");
console.log(errors.ndjson);

const sheets = workbook.worksheets.items;
console.log("SHEETS", JSON.stringify(sheets.map((sheet) => sheet.name)));
for (const sheet of sheets) {
  const sample = await workbook.inspect({
    kind: "table",
    sheetId: sheet.name,
    range: "A1:N12",
    include: "values,formulas",
    maxChars: 3500,
    tableMaxRows: 12,
    tableMaxCols: 14,
    tableMaxCellChars: 80,
  });
  console.log(`SAMPLE ${sheet.name}`);
  console.log(sample.ndjson);
  const render = await workbook.render({
    sheetName: sheet.name,
    range: "A1:N30",
    scale: 1,
    format: "png",
  });
  const safeName = sheet.name.replace(/[^a-zA-Z0-9_-]+/g, "_");
  await fs.writeFile(path.join(renderDir, `${safeName}.png`), new Uint8Array(await render.arrayBuffer()));
}
