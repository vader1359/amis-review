# PSI preview foundation — preparation only

This layer targets only `amis-psi-preview-20260905` in `asia-southeast1`.
It has **not been applied** and does **not satisfy Todo 6** of the approved
`.omo/plans/psi-neon-online.md`. Live console discovery on 2026-09-05 found
project number `803385681218` with no organization; the available billing
accounts were closed. Project creation alone is not infrastructure readiness.

The module declares two private, CMEK-encrypted buckets for sanitized staging
and Draft artifacts, three distinct runtime identity shells, a paused private
Cloud Tasks queue, and a private immutable-tag Artifact Registry repository.
The API can create staging objects and read artifacts; the worker can read
staging and create artifacts. These bucket-scoped custom roles cannot list,
overwrite, delete or modify IAM. Dispatcher has no grants. There is no compute,
public principal, account key, enqueue grant, OIDC impersonation, protected Final
or backup bucket, retention lock, secret value, or production resource.

Staging becomes deletion-eligible after 7 days and artifacts after 30 days.
GCS lifecycle execution is asynchronous; explicit 7-day soft delete extends
recoverability. These are disposable sanitized objects, **not retained Finals or
backups**. No owner-period workbook may enter these buckets. Object-create-only
IAM prevents replacement, but content-addressed names, generation checks and
upload capability validation still belong to the future application layer.
Bucket and registry destruction is guarded; those guards are reversible code
controls and are not Bucket Lock. Queue retries are 5 attempts with a 1-hour
duration: Cloud Tasks requires both limits to be reached, so this is not an exact
one-hour deletion promise. Queue remains paused and no runtime can enqueue.

## Required before any apply

All `bootstrap_readiness` assertions default to false and block every resource
through an explicit dependency. Empty CMEK references also block creation.
The assertions are operator inputs, **not evidence validation or permission**.
Do not turn them on until the corresponding live checks and reviewed receipts
exist. This module intentionally cannot bootstrap its own prerequisites:

1. Verify the exact isolated preview project, effective inherited IAM, billing
   authorization and cost budget. Enabling an API is a cloud mutation.
2. Separately provision and verify the GCS state backend: UBLA, versioning,
   at least 90-day superseded-generation recovery, explicit soft delete, CMEK,
   locking, isolated prefix, separate state/recovery access, alerts and a prior
   generation restore rehearsal. Supply backend bucket/prefix only from that
   reviewed inventory; never run with a local backend for an apply.
3. Verify existing regional storage/registry CMEKs, service-agent encryption
   grants and separate disable/destroy authority. Keep each key usable through
   object recovery expiry. Key rotation/old-object recovery, lifecycle alerts
   and retention policy remain external requirements. The module does not grant
   runtime accounts KMS administration or impersonation.
4. Implement and review the plan's guarded Terraform execution and fallback-state
   recovery wrappers. Every mutation must run in an encrypted restricted
   ephemeral directory outside source/evidence, fail-stop on fallback state and
   consume the real remote-state-ready receipt. This layer supplies no wrapper
   or counterfeit receipt. Bind the reviewed plan/apply to a clean committed SHA.
5. Complete the missing full bootstrap layer: durable isolated Neon preview and
   Auth prerequisites, role-specific Secret Manager containers and versions,
   protected Final/backup retention/CMEK policies with their separate irreversible
   lock authorization, reconciler queue policy and effective IAM readback.

This queue configuration is preparation and has not yet been rendered from the
plan's canonical `infra/policy/cloud-tasks.yaml`. OIDC target pinning, exact
queue-scoped API/reconciler permissions, effective `fullView`/delete/purge/run
denial checks, image-writer access and any dispatch enablement need a subsequent
reviewed layer. Neither this README nor Terraform output is an acceptance receipt.

## Offline validation

Terraform is pinned to `1.13.5`; Google provider to `7.45.0`. The lock file covers
Darwin arm64 and Linux amd64/arm64. Verify the Terraform distribution checksum
against HashiCorp's published release checksums before use. No system install
or provider authentication is needed for these mock tests:

```sh
rtk proxy terraform -chdir=infra/terraform/preview init -backend=false -lockfile=readonly
rtk proxy terraform -chdir=infra/terraform/preview fmt -check -recursive
rtk proxy terraform -chdir=infra/terraform/preview validate
rtk proxy terraform -chdir=infra/terraform/preview test
rtk proxy env PSI_TERRAFORM_BIN=/absolute/path/to/terraform uv run --extra online python -m pytest -q tests/psi_tool/test_cloud_bootstrap_policy.py
```

`terraform test` uses only `mock_provider "google"` and plan operations. Its true
readiness flags and mock key names are test fixtures, never real readiness
assertions. The pytest wrapper runs init/validate/native tests in a temporary copy,
strips Terraform/Google environment credentials and never applies. It skips when
Terraform is absent; a skip is not a passed infrastructure gate. Init downloads
the checksum-locked provider from the public registry, not a GCP API.

Provider syntax references are pinned to the selected version:
[buckets](https://github.com/hashicorp/terraform-provider-google/blob/v7.45.0/website/docs/r/storage_bucket.html.markdown),
[queues](https://github.com/hashicorp/terraform-provider-google/blob/v7.45.0/website/docs/r/cloud_tasks_queue.html.markdown),
[registry](https://github.com/hashicorp/terraform-provider-google/blob/v7.45.0/website/docs/r/artifact_registry_repository.html.markdown).
