# Infrastructure (Terraform)

Two layers, each doing what it is good at:

| Layer | Tool | What it does |
|---|---|---|
| The cloud pieces | Terraform (`infra/terraform`) | Creates the network, firewall, server and (optionally) the DNS record. Recreate everything, or move to another provider, with one command. |
| What runs on the server | `scripts/setup-ubuntu-server.sh` + Docker Compose | Installs Docker, opens the web ports and starts the site. Runs automatically on first boot through cloud-init, or by hand on any Linux server. |

The site itself never depends on the cloud: if Oracle ever stops suiting the chapter, point Terraform (or
a person) at another Ubuntu server and restore the latest backup there.

## 1. Create the server on Oracle Cloud (free)

Oracle's Always Free tier includes ARM servers with up to 4 cores and 24 GB of memory, which is far more than
this site needs. Choose the Johannesburg region (`af-johannesburg-1`) for the shortest distance to East Africa.

One-time on your computer:

1. Install [Terraform](https://developer.hashicorp.com/terraform/install) and the
   [OCI command line](https://docs.oracle.com/en-us/iaas/Content/API/SDKDocs/cliinstall.htm).
2. Create an Oracle Cloud account, then run `oci setup config` and upload the API key it creates
   (Profile → API keys). This writes `~/.oci/config`, which Terraform uses. Keys never go in this repository.
3. Make the repository readable by the server: either make it public, or put a read-only deploy token in
   `repo_url` (for example `https://<token>@github.com/cskimaru/mmm-africa.git`).

Then:

```sh
cd infra/terraform/oracle
cp terraform.tfvars.example terraform.tfvars   # fill in: compartment, SSH key, domain, email
terraform init
terraform plan        # shows what will be created
terraform apply
```

Terraform prints the server's IP address and next steps. On first boot (about 10 minutes) the server clones
the repository, runs the setup script, and starts the site in **private preview**. Follow progress with:

```sh
ssh ubuntu@<ip> tail -f bootstrap.log
```

Then on the server: `cd mmm-africa && make create-owner email=you@example.com name="Your Name"`, and copy
`secrets/backup_passphrase` somewhere safe.

## 2. Point the domain at the server

* **Domain on Cloudflare** (nameservers point at Cloudflare): use the small DNS module.

  ```sh
  cd infra/terraform/cloudflare-dns
  export CLOUDFLARE_API_TOKEN=...      # a token with Zone → DNS → Edit
  terraform init
  terraform apply -var zone_id=<zone id> -var server_ip=<ip from step 1>
  ```

* **Any other registrar** (for example a `.org` or `.co.ke` registrar): add an `A` record for the domain
  pointing at the server's IP in the registrar's DNS settings.

Caddy fetches the HTTPS certificate by itself once the domain points at the server.

## State

Terraform remembers what it created in `terraform.tfstate` inside each folder. It is git-ignored because it
can contain sensitive values. Keep a copy somewhere safe (for example alongside the backup passphrase), or
move it to a shared backend later if several people will run Terraform.

## Other clouds

`infra/terraform/cloud-init.yaml.tftpl` is plain cloud-init that works on any provider. To use another cloud,
add a folder next to `oracle/` with that provider's network, firewall and server resources, and pass the same
template as the server's user data. Everything above the server (the site, backups, monitoring) is unchanged.
