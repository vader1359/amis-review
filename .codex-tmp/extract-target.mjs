import fs from "node:fs/promises";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const outputPath = "/Users/iant1359/Develop/amis-review/input/Target.xlsx";
const qaDir = "/Users/iant1359/Develop/amis-review/.codex-tmp/qa";

await fs.mkdir(qaDir, { recursive: true });
const values = JSON.parse(await fs.readFile(
  "/Users/iant1359/Develop/amis-review/.codex-tmp/target-values.json",
  "utf8",
));

const workbook = Workbook.create();
const sheet = workbook.worksheets.add("Target");
sheet.showGridLines = false;
sheet.getRange("A1:J21").values = values;

sheet.getRange("A2:I2").format = {
  fill: "#1F4E78",
  font: { bold: true, color: "#FFFFFF" },
  horizontalAlignment: "center",
  verticalAlignment: "center",
  wrapText: true,
  borders: { preset: "outside", style: "thin", color: "#9EADBA" },
};
sheet.getRange("A3:I21").format = {
  font: { color: "#000000" },
  verticalAlignment: "center",
};
sheet.getRange("A3:A21").format.horizontalAlignment = "center";
sheet.getRange("C3:D21").format.horizontalAlignment = "center";
sheet.getRange("E3:I21").format.horizontalAlignment = "right";
sheet.getRange("E3:I21").format.numberFormat = "#,##0.00";

sheet.getRange("A:A").format.columnWidth = 8;
sheet.getRange("B:B").format.columnWidth = 20;
sheet.getRange("C:C").format.columnWidth = 13;
sheet.getRange("D:D").format.columnWidth = 17;
sheet.getRange("E:I").format.columnWidth = 22;
sheet.getRange("J:J").format.columnWidth = 3;
sheet.getRange("2:2").format.rowHeight = 42;
sheet.freezePanes.freezeRows(2);

const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(outputPath);

console.log((await workbook.inspect({
  kind: "table",
  range: "Target!A1:I21",
  include: "values,formulas",
  tableMaxRows: 25,
  tableMaxCols: 10,
  maxChars: 10000,
})).ndjson);
console.log((await workbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
  options: { useRegex: true, maxResults: 100 },
  summary: "formula error scan",
})).ndjson);

const preview = await workbook.render({
  sheetName: "Target",
  range: "A1:I21",
  scale: 1.5,
  format: "png",
});
await fs.writeFile(`${qaDir}/target-output.png`, new Uint8Array(await preview.arrayBuffer()));
console.log(`SAVED ${outputPath}`);
