// Create parameters NeonHost and NeonDatabase in Power BI, then create one query
// per view below.  Keep this source in Import mode for the existing PSI model.
// The gateway credential must be the read-only powerbi_reader database role.
let
    Source = PostgreSQL.Database(
        NeonHost,
        NeonDatabase,
        [CreateNavigationProperties = false]
    ),
    Product = Source{[Schema = "psi_powerbi", Item = "product_reference"]}[Data],
    Inventory = Source{[Schema = "psi_powerbi", Item = "inventory"]}[Data],
    Purchase = Source{[Schema = "psi_powerbi", Item = "purchase"]}[Data],
    Sales_CRM = Source{[Schema = "psi_powerbi", Item = "sales_crm"]}[Data],
    Revenue = Source{[Schema = "psi_powerbi", Item = "revenue"]}[Data],
    Preorder = Source{[Schema = "psi_powerbi", Item = "preorder"]}[Data],
    Stock_In = Source{[Schema = "psi_powerbi", Item = "stock_in"]}[Data],
    Target = Source{[Schema = "psi_powerbi", Item = "target_reference"]}[Data]
in
    [
        #"1. Product" = Product,
        #"2. Inventory" = Inventory,
        #"3. Purchase" = Purchase,
        #"4. Sales_CRM" = Sales_CRM,
        #"5. Revenue" = Revenue,
        #"6. Preorder" = Preorder,
        #"7. Stock_In" = Stock_In,
        Target = Target
    ]
