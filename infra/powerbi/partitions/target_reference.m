// NeonHost and NeonDatabase parameters required; no credentials in M.
let
    Source = PostgreSQL.Database(NeonHost, NeonDatabase, [CreateNavigationProperties=false]),
    Rows = Source{[Schema="psi_powerbi", Item="target_reference"]}[Data],
    Selected = Table.SelectColumns(Rows, {"SUPPLIER BC", "TARGET 2026", "Supplier Image", "Supplier Target"}),
    Typed = Table.TransformColumnTypes(Selected, {{"SUPPLIER BC", type text}, {"TARGET 2026", Int64.Type}, {"Supplier Image", type text}, {"Supplier Target", Int64.Type}}, "en-US")
in
    Typed
