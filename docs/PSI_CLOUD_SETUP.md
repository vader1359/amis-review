# PSI cloud setup

## Verified environment — 5 September 2026

The Google Cloud Console was inspected in the user's signed-in Chrome session.
No PSI project was present, so a separate empty preview project was created:

| Field | Value |
| --- | --- |
| Project name | AMIS PSI Preview |
| Project ID | `amis-psi-preview-20260905` |
| Project number | `803385681218` |
| Organization | No organization |
| Billing | Not linked; no active billing account available |
| Application deployed | No |

The project creation completed successfully and its identity was verified on
the Console welcome page. The billing-link dialog refused to proceed because
the existing billing accounts are closed. The unfiltered account list showed
both **My Billing Account** and **nanoHome** as **Closed**. My Billing Account
also displayed an expired free trial and an **Upgrade** action. No billing
account was reopened or upgraded, and no payment method was changed.

## Scope of the current implementation

The accepted local implementation is commit
`8a98b79d99ee3fad14480889b386de5a7d8f83f5` and is documented in
`PSI_ONLINE_ACCEPTANCE.md`. It provides the offline-equivalent Draft pipeline
and a loopback browser preview. It is not the shared cloud application.

The selected architecture remains Neon Postgres/Auth, Google Cloud Run,
Google Cloud Storage, Cloud Tasks, and Power BI Import. The old
`web/server.py` Supabase MVP must not be used as the cloud deployment target.
The preview Terraform directory is preparation for the non-compute foundation;
its tests do not constitute live cloud acceptance.

## Resume sequence

1. Establish an active billing account and explicitly authorize its use for
   the PSI preview project. Recheck the Console instead of assuming a prior
   account status is current.
2. Review the preview infrastructure against the immutable
   `.omo/plans/psi-neon-online.md` contract. Complete the separate state,
   retention, CMEK, recovery, and least-privilege prerequisites before any
   infrastructure apply. Do not bypass a blocked plan with dummy receipts.
3. Establish an isolated Neon preview environment with empty, schema-only,
   or approved sanitized data. Do not branch from the linked production
   environment or upload owner workbooks as preview fixtures.
4. Commit and independently review each implementation milestone, then run
   its live checks against the exact committed sources. Record sanitized
   resource identities and real results; do not mark the plan's Todo 6 done
   from project creation or local Terraform tests.
5. Implement and verify persistent uploads, authentication, durable worker
   delivery, Draft/Final governance, and Power BI before shared acceptance.

Production cutover and irreversible retention locking are separate actions;
neither was performed by this setup step.
