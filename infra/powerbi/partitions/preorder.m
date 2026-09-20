// NeonHost and NeonDatabase parameters required; no credentials in M.
let
    Source = PostgreSQL.Database(NeonHost, NeonDatabase, [CreateNavigationProperties=false]),
    Rows = Source{[Schema="psi_powerbi", Item="preorder"]}[Data],
    Selected = Table.SelectColumns(Rows, {"Date", "PRODUCT ID", "QUANTITY SOLD", "NET REV SOLD", "COST/UNIT", "ĐH", "HẠN GIAO HÀNG", "COGS", "Product name", "SUPPLIER", "BRAND NAME", "CATEGORIES", "SUBCATEGORIES"}),
    Typed = Table.TransformColumnTypes(Selected, {{"Date", type datetime}, {"PRODUCT ID", type text}, {"QUANTITY SOLD", Int64.Type}, {"NET REV SOLD", Int64.Type}, {"COST/UNIT", Int64.Type}, {"ĐH", type text}, {"HẠN GIAO HÀNG", type datetime}, {"COGS", Int64.Type}, {"Product name", type text}, {"SUPPLIER", type text}, {"BRAND NAME", type text}, {"CATEGORIES", type text}, {"SUBCATEGORIES", type text}}, "en-US")
in
    Typed
