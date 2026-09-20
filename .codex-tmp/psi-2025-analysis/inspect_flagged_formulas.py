import json

import openpyxl


path = "/Users/iant1359/Downloads/PSI 23.07 _KT check.xlsx"
target_rows = {
    4160,
    4870,
    4871,
    4872,
    5197,
    5198,
    5199,
    5496,
    5511,
    5512,
    5513,
    5514,
    5516,
    5584,
    5585,
    5586,
    5587,
    5588,
    5799,
}

workbook = openpyxl.load_workbook(
    path, read_only=True, data_only=False, keep_links=False
)
sheet = workbook["Revenue final"]
values = []
for row_number, row in enumerate(
    sheet.iter_rows(min_row=1, max_row=max(target_rows), max_col=17, values_only=True),
    start=1,
):
    if row_number in target_rows:
        values.append(
            {
                "row": row_number,
                "j": row[9],
                "p": row[15],
                "q": row[16],
            }
        )

print(json.dumps(values, ensure_ascii=False, default=str))
