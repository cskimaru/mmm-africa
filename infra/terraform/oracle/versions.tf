terraform {
  required_version = ">= 1.6"
  required_providers {
    oci = {
      source  = "oracle/oci"
      version = "~> 9.11"
    }
  }
}

# Credentials come from ~/.oci/config (create it with `oci setup config`), never from this repository.
provider "oci" {
  region              = var.region
  config_file_profile = var.oci_profile
}
