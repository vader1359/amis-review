let
    Empty = #table({"PRODUCT ID", "index", "Cumulative", "Stock in date", "Số chứng từ", "QUANTITY", "Index", "CumQty", "PrevCumQty", "Total stock in"}, {}),
    Typed = Table.TransformColumnTypes(Empty, {{"PRODUCT ID", type text}, {"index", type text}, {"Cumulative", type text}, {"Stock in date", type date}, {"Số chứng từ", type text}, {"QUANTITY", Int64.Type}, {"Index", type text}, {"CumQty", Int64.Type}, {"PrevCumQty", Int64.Type}, {"Total stock in", Int64.Type}}, "en-US")
in
    Typed
