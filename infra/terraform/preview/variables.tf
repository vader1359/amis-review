variable "project_id" {
  description = "Exact isolated preview project; other projects require source review."
  type        = string
  default     = "amis-psi-preview-20260905"
  validation {
    condition     = var.project_id == "amis-psi-preview-20260905"
    error_message = "Only amis-psi-preview-20260905 is allowed; never use an existing production project."
  }
}

variable "region" {
  description = "Preview data residency; a change requires explicit source review."
  type        = string
  default     = "asia-southeast1"
  validation {
    condition     = var.region == "asia-southeast1"
    error_message = "The reviewed preview region is asia-southeast1."
  }
}

variable "bootstrap_readiness" {
  description = "Operator assertions, NOT generated evidence. All must remain false until the external gates in README pass."
  type = object({
    preview_project_verified           = bool
    billing_and_budget_reviewed        = bool
    remote_state_recovery_verified     = bool
    cmek_lifecycle_and_grants_verified = bool
    guarded_execution_ready            = bool
    sanitized_data_only                = bool
  })
  default = {
    preview_project_verified           = false
    billing_and_budget_reviewed        = false
    remote_state_recovery_verified     = false
    cmek_lifecycle_and_grants_verified = false
    guarded_execution_ready            = false
    sanitized_data_only                = false
  }
  nullable = false
}

variable "storage_kms_key" {
  description = "Existing reviewed regional CMEK resource name; never a key value. Creation/lifecycle verification is separate."
  type        = string
  default     = ""
  validation {
    condition = var.storage_kms_key == "" || can(regex(
      "^projects/amis-psi-preview-20260905/locations/asia-southeast1/keyRings/[a-zA-Z0-9_-]+/cryptoKeys/[a-zA-Z0-9_-]+$",
      var.storage_kms_key
    ))
    error_message = "Storage CMEK must belong to the exact preview project and region."
  }
}

variable "registry_kms_key" {
  description = "Existing reviewed Artifact Registry CMEK resource name. No secret material."
  type        = string
  default     = ""
  validation {
    condition = var.registry_kms_key == "" || can(regex(
      "^projects/amis-psi-preview-20260905/locations/asia-southeast1/keyRings/[a-zA-Z0-9_-]+/cryptoKeys/[a-zA-Z0-9_-]+$",
      var.registry_kms_key
    ))
    error_message = "Registry CMEK must belong to the exact preview project and region."
  }
}
