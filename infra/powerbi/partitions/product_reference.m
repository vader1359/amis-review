// NeonHost and NeonDatabase parameters required; no credentials in M.
let
    Source = PostgreSQL.Database(NeonHost, NeonDatabase, [CreateNavigationProperties=false]),
    Rows = Source{[Schema="psi_powerbi", Item="product_reference"]}[Data],
    Selected = Table.SelectColumns(Rows, {"NO.", "PRODUCT ID", "PRODUCT NAME", "CATEGORIES", "SUBCATEGORIES", "BRAND NAME", "BRAND CODE", "SUPPLIER", "SUPPLIER BC", "SERIES", "Image", "GIÁ BÁN LẺ MISA", "BRAND NAME BC"}),
    Typed = Table.TransformColumnTypes(Selected, {{"NO.", type text}, {"PRODUCT ID", type text}, {"PRODUCT NAME", type text}, {"CATEGORIES", type text}, {"SUBCATEGORIES", type text}, {"BRAND NAME", type text}, {"BRAND CODE", type text}, {"SUPPLIER", type text}, {"SUPPLIER BC", type text}, {"SERIES", type text}, {"Image", type text}, {"GIÁ BÁN LẺ MISA", Int64.Type}, {"BRAND NAME BC", type text}}, "en-US")
in
    Typed
