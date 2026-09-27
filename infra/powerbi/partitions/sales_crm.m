// NeonHost and NeonDatabase parameters required; no credentials in M.
let
    Source = PostgreSQL.Database(NeonHost, NeonDatabase, [CreateNavigationProperties=false]),
    Rows = Source{[Schema="psi_powerbi", Item="sales_crm"]}[Data],
    Selected = Table.SelectColumns(Rows, {"SALES DATE", "PRODUCT ID", "QUANTITY SOLD", "NET REV SOLD", "COST/UNIT", "COGS", "SALE ORDER", "Product name", "SUPPLIER", "BRAND NAME", "CATEGORIES", "SUBCATEGORIES", "CUSTOMER"}),
    Typed = Table.TransformColumnTypes(Selected, {{"SALES DATE", type datetime}, {"PRODUCT ID", type text}, {"QUANTITY SOLD", Int64.Type}, {"NET REV SOLD", Int64.Type}, {"COST/UNIT", Int64.Type}, {"COGS", Int64.Type}, {"SALE ORDER", type text}, {"Product name", type text}, {"SUPPLIER", type text}, {"BRAND NAME", type text}, {"CATEGORIES", type text}, {"SUBCATEGORIES", type text}, {"CUSTOMER", type text}}, "en-US")
in
    Typed
