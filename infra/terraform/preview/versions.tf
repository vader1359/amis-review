terraform {
  required_version = "= 1.13.5"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "= 7.45.0"
    }
  }

  # Configure only from the reviewed, separately bootstrapped state receipt.
  # Credentials and backend state must never enter this directory.
  backend "gcs" {}
}

provider "google" {
  project = var.project_id
  region  = var.region
}
