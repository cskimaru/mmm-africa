variable "region" {
  description = "Oracle Cloud region, e.g. af-johannesburg-1 (closest to East Africa) or uk-london-1."
  type        = string
  default     = "af-johannesburg-1"
}

variable "oci_profile" {
  description = "Profile name in ~/.oci/config."
  type        = string
  default     = "DEFAULT"
}

variable "compartment_ocid" {
  description = "Compartment to create everything in (the tenancy OCID works for a personal account)."
  type        = string
}

variable "ssh_public_key" {
  description = "Your SSH public key (the contents of ~/.ssh/id_ed25519.pub)."
  type        = string
}

variable "site_domain" {
  description = "The African Chapter's domain, e.g. mmmafrica.org."
  type        = string
}

variable "acme_email" {
  description = "Email for Let's Encrypt certificate notices."
  type        = string
}

variable "repo_url" {
  description = "Git URL the server clones. A private repository needs a deploy key or token in the URL."
  type        = string
  default     = "https://github.com/cskimaru/mmm-africa.git"
}

variable "registry" {
  description = "Container registry CI pushes to, e.g. ghcr.io/cskimaru/mmm-africa. Empty: build on the server."
  type        = string
  default     = ""
}

variable "ocpus" {
  description = "ARM cores. Oracle's Always Free allowance is 4 in total."
  type        = number
  default     = 2
}

variable "memory_gb" {
  description = "Memory in GB. Always Free allows 24 GB in total."
  type        = number
  default     = 12
}

variable "boot_volume_gb" {
  description = "Disk size in GB. Always Free allows 200 GB in total."
  type        = number
  default     = 60
}
