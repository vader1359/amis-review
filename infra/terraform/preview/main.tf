locals {
  labels = {
    application = "psi"
    environment = "preview"
    data_class  = "sanitized-only"
    managed_by  = "terraform"
  }
  buckets = {
    staging   = 7
    artifacts = 30
  }
  identities = toset(["api", "worker", "dispatcher"])
  # Project-defined permissions are bound only on the individual buckets below.
  object_roles = {
    create = ["storage.objects.create"]
    read   = ["storage.objects.get"]
  }
  object_grants = {
    api_staging_create     = { identity = "api", bucket = "staging", role = "create" }
    worker_staging_read    = { identity = "worker", bucket = "staging", role = "read" }
    worker_artifacts_write = { identity = "worker", bucket = "artifacts", role = "create" }
    api_artifacts_read     = { identity = "api", bucket = "artifacts", role = "read" }
  }
}

resource "terraform_data" "readiness" {
  input = var.bootstrap_readiness
  lifecycle {
    precondition {
      condition     = alltrue(values(var.bootstrap_readiness))
      error_message = "NO_START: complete preview, budget, remote-state recovery, CMEK, guarded-execution, and sanitized-only gates first. Operator assertions are not acceptance receipts."
    }
    precondition {
      condition     = var.storage_kms_key != "" && var.registry_kms_key != ""
      error_message = "NO_START: verified existing CMEK references are required before any resource creation."
    }
  }
}

resource "google_project_service" "required" {
  for_each = toset([
    "artifactregistry.googleapis.com",
    "cloudtasks.googleapis.com",
    "cloudkms.googleapis.com",
    "iam.googleapis.com",
    "storage.googleapis.com",
  ])
  project                    = var.project_id
  service                    = each.value
  disable_on_destroy         = false
  disable_dependent_services = false
  depends_on                 = [terraform_data.readiness]
}

resource "google_service_account" "runtime" {
  for_each     = local.identities
  project      = var.project_id
  account_id   = "psi-preview-${each.key}"
  display_name = "PSI preview ${each.key}"
  description  = "Sanitized preview identity shell. No keys, token creation, or project-wide runtime grants."
  depends_on   = [google_project_service.required]
}

resource "google_storage_bucket" "preview" {
  for_each                    = local.buckets
  project                     = var.project_id
  name                        = "${var.project_id}-${each.key}"
  location                    = var.region
  storage_class               = "STANDARD"
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  force_destroy               = false
  labels                      = local.labels

  encryption {
    default_kms_key_name = var.storage_kms_key
  }
  soft_delete_policy {
    retention_duration_seconds = 604800
  }
  lifecycle_rule {
    condition {
      age = each.value
    }
    action {
      type = "Delete"
    }
  }
  lifecycle {
    prevent_destroy = true
  }
  depends_on = [google_project_service.required]
}

resource "google_project_iam_custom_role" "objects" {
  for_each    = local.object_roles
  project     = var.project_id
  role_id     = "psiPreviewObject${title(each.key)}"
  title       = "PSI preview object ${each.key}"
  description = "Bound to one preview bucket; excludes list, update, delete and IAM."
  permissions = each.value
  depends_on  = [google_project_service.required]
}

resource "google_storage_bucket_iam_member" "objects" {
  for_each = local.object_grants
  bucket   = google_storage_bucket.preview[each.value.bucket].name
  role     = google_project_iam_custom_role.objects[each.value.role].name
  member   = "serviceAccount:${google_service_account.runtime[each.value.identity].email}"
}

resource "google_cloud_tasks_queue" "dispatch" {
  project         = var.project_id
  name            = "psi-preview-dispatch"
  location        = var.region
  desired_state   = "PAUSED"
  deletion_policy = "PREVENT"
  rate_limits {
    max_concurrent_dispatches = 1
    max_dispatches_per_second = 1
  }
  retry_config {
    max_attempts       = 5
    max_retry_duration = "3600s"
    min_backoff        = "10s"
    max_backoff        = "300s"
    max_doublings      = 4
  }
  stackdriver_logging_config {
    sampling_ratio = 0
  }
  # No enqueue, fullView, purge/run, OIDC impersonation or public IAM grants.
  # Authentication/target pinning and reconciler are a later reviewed layer.
  depends_on = [google_project_service.required]
}

resource "google_artifact_registry_repository" "images" {
  project       = var.project_id
  location      = var.region
  repository_id = "psi-preview-images"
  description   = "Private PSI preview images; no writer or compute access yet."
  format        = "DOCKER"
  kms_key_name  = var.registry_kms_key
  labels        = local.labels
  docker_config {
    immutable_tags = true
  }
  lifecycle {
    prevent_destroy = true
  }
  depends_on = [google_project_service.required]
}
