output "public_ip" {
  description = "Point the domain's A record here (or use the cloudflare-dns module)."
  value       = oci_core_instance.server.public_ip
}

output "ssh" {
  description = "Log in to the server."
  value       = "ssh ${local.admin_user}@${oci_core_instance.server.public_ip}"
}

output "next_steps" {
  value = <<-EOT
    1. Point ${var.site_domain} at ${oci_core_instance.server.public_ip} (A record).
    2. Wait about 10 minutes, then check progress: ssh ${local.admin_user}@${oci_core_instance.server.public_ip} tail -f bootstrap.log
    3. On the server, create the first officer: cd mmm-africa && make create-owner email=you@example.com name="Your Name"
    4. Copy secrets/backup_passphrase somewhere safe, away from the server.
  EOT
}
