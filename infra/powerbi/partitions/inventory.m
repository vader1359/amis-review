// NeonHost and NeonDatabase parameters required; no credentials in M.
let
    Source = PostgreSQL.Database(NeonHost, NeonDatabase, [CreateNavigationProperties=false]),
    Rows = Source{[Schema="psi_powerbi", Item="inventory"]}[Data],
    Selected = Table.SelectColumns(Rows, {"Date", "PRODUCT ID", "QUANTITY", "VALUE", "WAREHOUSE", "VALUE/unit", "PRODUCT NAME", "SUPPLIER", "BRAND NAME", "CATEGORIES", "SUBCATEGORIES"}),
    Typed = Table.TransformColumnTypes(Selected, {{"Date", type datetime}, {"PRODUCT ID", type text}, {"QUANTITY", type number}, {"VALUE", Int64.Type}, {"WAREHOUSE", type text}, {"VALUE/unit", type number}, {"PRODUCT NAME", type text}, {"SUPPLIER", type text}, {"BRAND NAME", type text}, {"CATEGORIES", type text}, {"SUBCATEGORIES", type text}}, "en-US")
in
    Typed
