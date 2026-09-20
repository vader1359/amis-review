// NeonHost and NeonDatabase parameters required; no credentials in M.
let
    Source = PostgreSQL.Database(NeonHost, NeonDatabase, [CreateNavigationProperties=false]),
    Rows = Source{[Schema="psi_powerbi", Item="stock_in"]}[Data],
    Selected = Table.SelectColumns(Rows, {"PRODUCT ID", "index", "Cumulative", "Stock in date", "Số chứng từ", "QUANTITY", "Index", "CumQty", "PrevCumQty", "Total stock in"}),
    Typed = Table.TransformColumnTypes(Selected, {{"PRODUCT ID", type text}, {"index", type text}, {"Cumulative", type text}, {"Stock in date", type datetime}, {"Số chứng từ", type text}, {"QUANTITY", Int64.Type}, {"Index", type text}, {"CumQty", Int64.Type}, {"PrevCumQty", Int64.Type}, {"Total stock in", Int64.Type}}, "en-US")
in
    Typed
