# Optional: manage the domain's DNS record on Cloudflare (free plan is enough).
# Use this if the domain's nameservers point at Cloudflare; otherwise add the A record at your registrar.
terraform {
  required_version = ">= 1.6"
  required_providers {
    cloudflare = {
      source  = "cloudflare/cloudflare"
      version = "~> 5.28"
    }
  }
}

# The token comes from the CLOUDFLARE_API_TOKEN environment variable (Zone: DNS: Edit permission).
provider "cloudflare" {}

variable "zone_id" {
  description = "Cloudflare zone ID of the domain (shown on the domain's overview page)."
  type        = string
}

variable "name" {
  description = "Record name: \"@\" for the bare domain, or a subdomain such as \"africa\"."
  type        = string
  default     = "@"
}

variable "server_ip" {
  description = "The server's public IP (the public_ip output of the oracle module)."
  type        = string
}

resource "cloudflare_record" "site" {
  zone_id = var.zone_id
  name    = var.name
  type    = "A"
  content = var.server_ip
  ttl     = 300
  # Caddy gets its own certificate, so traffic goes straight to the server.
  proxied = false
}

output "record" {
  value = cloudflare_record.site.hostname
}
