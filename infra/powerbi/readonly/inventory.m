let
    Payload = GetPSIPayload(NeonHost, NeonDatabase, ReportId),
    Rows = Table.FromRows(Payload[inventory_rows], {"NO", "Date", "PRODUCT ID", "PRODUCT NAME", "CATEGORIES", "SUBCATEGORIES", "SUPPLIER", "BRAND CODE", "QUANTITY", "VALUE", "WAREHOUSE"}),
    UnitValue = Table.AddColumn(Rows, "VALUE/unit", each if [QUANTITY] = null or [QUANTITY] = 0 then null else [VALUE] / [QUANTITY], type number),
    Selected = Table.SelectColumns(UnitValue, {"Date", "PRODUCT ID", "QUANTITY", "VALUE", "WAREHOUSE", "VALUE/unit", "PRODUCT NAME", "SUPPLIER", "CATEGORIES", "SUBCATEGORIES"}),
    MissingBrand = Table.AddColumn(Selected, "BRAND NAME", each null, type text),
    Ordered = Table.ReorderColumns(MissingBrand, {"Date", "PRODUCT ID", "QUANTITY", "VALUE", "WAREHOUSE", "VALUE/unit", "PRODUCT NAME", "SUPPLIER", "BRAND NAME", "CATEGORIES", "SUBCATEGORIES"}),
    Typed = Table.TransformColumnTypes(Ordered, {{"Date", type date}, {"PRODUCT ID", type text}, {"QUANTITY", type number}, {"VALUE", Int64.Type}, {"WAREHOUSE", type text}, {"VALUE/unit", type number}, {"PRODUCT NAME", type text}, {"SUPPLIER", type text}, {"BRAND NAME", type text}, {"CATEGORIES", type text}, {"SUBCATEGORIES", type text}}, "en-US")
in
    Typed
