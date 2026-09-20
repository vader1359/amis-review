// Power Query helper.  NeonHost, NeonDatabase and ReportId are text parameters.
// The query is read-only and returns exactly the immutable PSI Draft selected by
// ReportId; it never asks the database for a newest report.
let
    GetPSIPayload = (NeonHost as text, NeonDatabase as text, ReportId as text) as record =>
        let
            Source = PostgreSQL.Database(NeonHost, NeonDatabase, [CreateNavigationProperties = false]),
            Snapshot = Value.NativeQuery(
                Source,
                "SELECT payload::text AS payload_json FROM psi_preview.reports WHERE id = @report_id",
                [report_id = ReportId],
                [EnableFolding = false]
            ),
            PayloadJson = if Table.RowCount(Snapshot) = 1
                then Snapshot{0}[payload_json]
                else error "PSI ReportId must identify exactly one immutable snapshot.",
            Payload = Json.Document(Text.ToBinary(PayloadJson, TextEncoding.Utf8))
        in
            Payload
in
    GetPSIPayload
