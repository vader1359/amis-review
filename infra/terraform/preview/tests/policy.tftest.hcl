mock_provider "google" {}

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

run "reject_other_project" {
  command = plan
  variables {
    project_id = "temp-nanohome"
  }
  expect_failures = [var.project_id]
}

run "reject_other_region" {
  command = plan
  variables {
    region = "us-central1"
  }
  expect_failures = [var.region]
}

run "reject_foreign_storage_key" {
  command = plan
  variables {
    storage_kms_key = "projects/production/locations/asia-southeast1/keyRings/k/cryptoKeys/k"
  }
  expect_failures = [var.storage_kms_key]
}

run "reject_foreign_registry_key" {
  command = plan
  variables {
    registry_kms_key = "projects/production/locations/asia-southeast1/keyRings/k/cryptoKeys/k"
  }
  expect_failures = [var.registry_kms_key]
}

run "reject_missing_keys" {
  command = plan
  variables {
    storage_kms_key  = ""
    registry_kms_key = ""
  }
  expect_failures = [terraform_data.readiness]
}

run "reject_missing_preview_project_verified" {
  command = plan
  variables {
    bootstrap_readiness = {
      preview_project_verified           = false
      billing_and_budget_reviewed        = true
      remote_state_recovery_verified     = true
      cmek_lifecycle_and_grants_verified = true
      guarded_execution_ready            = true
      sanitized_data_only                = true
    }
  }
  expect_failures = [terraform_data.readiness]
}

run "reject_missing_billing_and_budget_reviewed" {
  command = plan
  variables {
    bootstrap_readiness = {
      preview_project_verified           = true
      billing_and_budget_reviewed        = false
      remote_state_recovery_verified     = true
      cmek_lifecycle_and_grants_verified = true
      guarded_execution_ready            = true
      sanitized_data_only                = true
    }
  }
  expect_failures = [terraform_data.readiness]
}

run "reject_missing_remote_state_recovery_verified" {
  command = plan
  variables {
    bootstrap_readiness = {
      preview_project_verified           = true
      billing_and_budget_reviewed        = true
      remote_state_recovery_verified     = false
      cmek_lifecycle_and_grants_verified = true
      guarded_execution_ready            = true
      sanitized_data_only                = true
    }
  }
  expect_failures = [terraform_data.readiness]
}

run "reject_missing_cmek_lifecycle_and_grants_verified" {
  command = plan
  variables {
    bootstrap_readiness = {
      preview_project_verified           = true
      billing_and_budget_reviewed        = true
      remote_state_recovery_verified     = true
      cmek_lifecycle_and_grants_verified = false
      guarded_execution_ready            = true
      sanitized_data_only                = true
    }
  }
  expect_failures = [terraform_data.readiness]
}

run "reject_missing_guarded_execution_ready" {
  command = plan
  variables {
    bootstrap_readiness = {
      preview_project_verified           = true
      billing_and_budget_reviewed        = true
      remote_state_recovery_verified     = true
      cmek_lifecycle_and_grants_verified = true
      guarded_execution_ready            = false
      sanitized_data_only                = true
    }
  }
  expect_failures = [terraform_data.readiness]
}

run "reject_missing_sanitized_data_only" {
  command = plan
  variables {
    bootstrap_readiness = {
      preview_project_verified           = true
      billing_and_budget_reviewed        = true
      remote_state_recovery_verified     = true
      cmek_lifecycle_and_grants_verified = true
      guarded_execution_ready            = true
      sanitized_data_only                = false
    }
  }
  expect_failures = [terraform_data.readiness]
}
