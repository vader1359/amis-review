output "inventory" {
  description = "Resource identifiers only; this is not a deployment or acceptance receipt."
  value = {
    project          = var.project_id
    region           = var.region
    buckets          = { for name, bucket in google_storage_bucket.preview : name => bucket.name }
    service_accounts = { for name, account in google_service_account.runtime : name => account.email }
    paused_queue     = google_cloud_tasks_queue.dispatch.id
    image_repository = google_artifact_registry_repository.images.id
    data_class       = "SANITIZED_ONLY"
    acceptance       = "PREPARATION_ONLY_NOT_TODO_6"
  }
}
