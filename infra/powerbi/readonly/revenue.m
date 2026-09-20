let
    Payload = GetPSIPayload(NeonHost, NeonDatabase, ReportId),
    Rows = Table.FromRows(Payload[revenue_rows], {"NO", "SALES DATE", "PRODUCT ID", "Product name", "CATEGORIES", "SUBCATEGORIES", "SUPPLIER", "BRAND CODE", "QUANTITY SOLD", "NET REV SOLD", "COGS", "SALE ORDER", "SHOWROOM SOLD", "CHANEL", "Column1", "Old PSI", "Difference", "Note"}),
    UnitCost = Table.AddColumn(Rows, "COST/UNIT", each if [QUANTITY SOLD] = null or [QUANTITY SOLD] = 0 then null else [COGS] / [QUANTITY SOLD], type number),
    Selected = Table.SelectColumns(UnitCost, {"NO", "SALES DATE", "PRODUCT ID", "QUANTITY SOLD", "NET REV SOLD", "COST/UNIT", "COGS", "SALE ORDER", "Product name", "SUPPLIER", "CATEGORIES", "SUBCATEGORIES"}),
    MissingBrand = Table.AddColumn(Selected, "BRAND NAME", each null, type text),
    Ordered = Table.ReorderColumns(MissingBrand, {"NO", "SALES DATE", "PRODUCT ID", "QUANTITY SOLD", "NET REV SOLD", "COST/UNIT", "COGS", "SALE ORDER", "Product name", "SUPPLIER", "BRAND NAME", "CATEGORIES", "SUBCATEGORIES"}),
    Typed = Table.TransformColumnTypes(Ordered, {{"NO", Int64.Type}, {"SALES DATE", type date}, {"PRODUCT ID", type text}, {"QUANTITY SOLD", type number}, {"NET REV SOLD", Int64.Type}, {"COST/UNIT", type number}, {"COGS", Int64.Type}, {"SALE ORDER", type text}, {"Product name", type text}, {"SUPPLIER", type text}, {"BRAND NAME", type text}, {"CATEGORIES", type text}, {"SUBCATEGORIES", type text}}, "en-US")
in
    Typed
