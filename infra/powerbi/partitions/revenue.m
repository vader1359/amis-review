// NeonHost and NeonDatabase parameters required; no credentials in M.
let
    Source = PostgreSQL.Database(NeonHost, NeonDatabase, [CreateNavigationProperties=false]),
    Rows = Source{[Schema="psi_powerbi", Item="revenue"]}[Data],
    Selected = Table.SelectColumns(Rows, {"NO", "SALES DATE", "PRODUCT ID", "QUANTITY SOLD", "NET REV SOLD", "COST/UNIT", "COGS", "SALE ORDER", "Product name", "SUPPLIER", "BRAND NAME", "CATEGORIES", "SUBCATEGORIES"}),
    Typed = Table.TransformColumnTypes(Selected, {{"NO", Int64.Type}, {"SALES DATE", type datetime}, {"PRODUCT ID", type text}, {"QUANTITY SOLD", type number}, {"NET REV SOLD", Int64.Type}, {"COST/UNIT", type number}, {"COGS", Int64.Type}, {"SALE ORDER", type text}, {"Product name", type text}, {"SUPPLIER", type text}, {"BRAND NAME", type text}, {"CATEGORIES", type text}, {"SUBCATEGORIES", type text}}, "en-US")
in
    Typed
