let
    Payload = GetPSIPayload(NeonHost, NeonDatabase, ReportId),
    Rows = Table.FromRows(Payload[crm_product_rows], {"SALE ORDER", "PRODUCT ID", "Product name", "QUANTITY SOLD", "NET REV SOLD", "SALES DATE"}),
    MissingCost = Table.AddColumn(Rows, "COST/UNIT", each null, type number),
    MissingCogs = Table.AddColumn(MissingCost, "COGS", each null, type number),
    MissingSupplier = Table.AddColumn(MissingCogs, "SUPPLIER", each null, type text),
    MissingBrand = Table.AddColumn(MissingSupplier, "BRAND NAME", each null, type text),
    MissingCategory = Table.AddColumn(MissingBrand, "CATEGORIES", each null, type text),
    MissingSubcategory = Table.AddColumn(MissingCategory, "SUBCATEGORIES", each null, type text),
    MissingCustomer = Table.AddColumn(MissingSubcategory, "CUSTOMER", each null, type text),
    Typed = Table.TransformColumnTypes(MissingCustomer, {{"SALES DATE", type date}, {"PRODUCT ID", type text}, {"QUANTITY SOLD", Int64.Type}, {"NET REV SOLD", Int64.Type}, {"COST/UNIT", Int64.Type}, {"COGS", Int64.Type}, {"SALE ORDER", type text}, {"Product name", type text}, {"SUPPLIER", type text}, {"BRAND NAME", type text}, {"CATEGORIES", type text}, {"SUBCATEGORIES", type text}, {"CUSTOMER", type text}}, "en-US")
in
    Typed
