import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const psiPath = "/Users/iant1359/Downloads/PSI 23.07 _KT check.xlsx";
const misaPath =
  "/Users/iant1359/Downloads/mismatch/So_chi_tiet_ban_hang 22.07.xlsx";

async function loadWorkbook(path) {
  return SpreadsheetFile.importXlsx(await FileBlob.load(path));
}

function print(label, value) {
  console.log(`${label}\t${JSON.stringify(value)}`);
}

const psi = await loadWorkbook(psiPath);
console.log(
  "PSI_SHEETS",
  (await psi.inspect({ kind: "sheet", include: "id,name", maxChars: 12000 }))
    .ndjson,
);

const revenue = psi.worksheets.getItem("Revenue final");
print("REVENUE_TOP", revenue.getRange("A1:Q12").values);

const checkValues = revenue.getRange("P1:Q9000").values;
const checkedRows = [];
for (let index = 0; index < checkValues.length; index += 1) {
  const [correctValue, variance] = checkValues[index] ?? [];
  if (
    index >= 5 &&
    (correctValue !== null ||
      variance !== null) &&
    (correctValue !== "" || variance !== "")
  ) {
    checkedRows.push(index + 1);
  }
}
print("CHECKED_ROW_NUMBERS", checkedRows);
for (const rowNumber of checkedRows) {
  print(
    `REVENUE_ROW_${rowNumber}`,
    revenue.getRange(`A${rowNumber}:Q${rowNumber}`).values[0],
  );
}

const misa = await loadWorkbook(misaPath);
console.log(
  "MISA_SHEETS",
  (await misa.inspect({ kind: "sheet", include: "id,name", maxChars: 12000 }))
    .ndjson,
);
const misaSheet = misa.worksheets.getItemAt(0);
print("MISA_TOP", misaSheet.getRange("A1:AC12").values);
