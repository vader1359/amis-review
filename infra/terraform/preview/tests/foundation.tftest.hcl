mock_provider "google" {
  override_during = plan
  mock_resource "google_service_account" {
    defaults = { email = "mock@amis-psi-preview-20260905.iam.gserviceaccount.com" }
  }
  mock_resource "google_project_iam_custom_role" {
    defaults = { name = "projects/amis-psi-preview-20260905/roles/psiPreviewObjectMock" }
  }
}

variables {
  storage_kms_key  = "projects/amis-psi-preview-20260905/locations/asia-southeast1/keyRings/mock/cryptoKeys/storage"
  registry_kms_key = "projects/amis-psi-preview-20260905/locations/asia-southeast1/keyRings/mock/cryptoKeys/registry"
  bootstrap_readiness = {
    preview_project_verified           = true
    billing_and_budget_reviewed        = true
    remote_state_recovery_verified     = true
    cmek_lifecycle_and_grants_verified = true
    guarded_execution_ready            = true
    sanitized_data_only                = true
  }
}

run "private_sanitized_foundation" {
  command = plan
  assert {
    condition = alltrue([
      for bucket in google_storage_bucket.preview :
      bucket.uniform_bucket_level_access && bucket.public_access_prevention == "enforced" && !bucket.force_destroy
    ])
    error_message = "Every bucket must deny public/object-ACL access and forced deletion."
  }
  assert {
    condition = alltrue([
      for bucket in google_storage_bucket.preview :
      bucket.encryption[0].default_kms_key_name == var.storage_kms_key &&
      bucket.soft_delete_policy[0].retention_duration_seconds == 604800 &&
      length(bucket.retention_policy) == 0 && length(bucket.cors) == 0
    ])
    error_message = "CMEK and recoverable deletes are required; no lock or browser upload is approved in this layer."
  }
  assert {
    condition = alltrue([
      for name, bucket in google_storage_bucket.preview :
      one(bucket.lifecycle_rule[0].condition).age == { staging = 7, artifacts = 30 }[name]
    ])
    error_message = "Staging deletion eligibility must be exactly 7 days and artifacts exactly 30 days."
  }
  assert {
    condition = (google_cloud_tasks_queue.dispatch.desired_state == "PAUSED" &&
      google_cloud_tasks_queue.dispatch.rate_limits[0].max_concurrent_dispatches == 1 &&
      google_cloud_tasks_queue.dispatch.retry_config[0].max_attempts == 5 &&
    google_cloud_tasks_queue.dispatch.retry_config[0].max_retry_duration == "3600s")
    error_message = "The unconnected queue must remain paused, throttled, and bounded."
  }
  assert {
    condition = (toset(flatten([for role in google_project_iam_custom_role.objects : role.permissions])) ==
    toset(["storage.objects.get", "storage.objects.create"]))
    error_message = "Preview runtime permissions must not add listing, deletion, overwrite, IAM or task privileges."
  }
  assert {
    condition = (length(google_service_account.runtime) == 3 &&
    alltrue([for grant in local.object_grants : grant.identity != "dispatcher"]))
    error_message = "Dispatcher is an unprivileged shell until its authenticated target is reviewed."
  }
  assert {
    condition     = google_artifact_registry_repository.images.docker_config[0].immutable_tags
    error_message = "Container tags must be immutable."
  }
}
