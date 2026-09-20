let
    Payload = GetPSIPayload(NeonHost, NeonDatabase, ReportId),
    Rows = Table.FromRows(Payload[preorder_rows], {"NO", "Date", "PRODUCT ID", "Product name", "CATEGORIES", "SUBCATEGORIES", "SUPPLIER", "BRAND CODE", "QUANTITY SOLD", "NET REV SOLD", "Estimated cost", "INVOICE NO.", "ĐH", "HẠN GIAO HÀNG", "Column1", "Map", "KT check", "Xử lý"}),
    MissingCost = Table.AddColumn(Rows, "COST/UNIT", each null, type number),
    MissingCogs = Table.AddColumn(MissingCost, "COGS", each null, type number),
    Selected = Table.SelectColumns(MissingCogs, {"Date", "PRODUCT ID", "QUANTITY SOLD", "NET REV SOLD", "COST/UNIT", "ĐH", "HẠN GIAO HÀNG", "COGS", "Product name", "SUPPLIER", "CATEGORIES", "SUBCATEGORIES"}),
    MissingBrand = Table.AddColumn(Selected, "BRAND NAME", each null, type text),
    Ordered = Table.ReorderColumns(MissingBrand, {"Date", "PRODUCT ID", "QUANTITY SOLD", "NET REV SOLD", "COST/UNIT", "ĐH", "HẠN GIAO HÀNG", "COGS", "Product name", "SUPPLIER", "BRAND NAME", "CATEGORIES", "SUBCATEGORIES"}),
    Typed = Table.TransformColumnTypes(Ordered, {{"Date", type date}, {"PRODUCT ID", type text}, {"QUANTITY SOLD", Int64.Type}, {"NET REV SOLD", Int64.Type}, {"COST/UNIT", Int64.Type}, {"ĐH", type text}, {"HẠN GIAO HÀNG", type date}, {"COGS", Int64.Type}, {"Product name", type text}, {"SUPPLIER", type text}, {"BRAND NAME", type text}, {"CATEGORIES", type text}, {"SUBCATEGORIES", type text}}, "en-US")
in
    Typed
