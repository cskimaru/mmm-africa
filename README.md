# MMM Africa: Medical Missionary Movement, African Chapter

The website of the MMM African Chapter. It presents the chapter, its national chapters, its leaders and its
shared events, and gives officers a private area to keep all of that up to date and answer messages.

| MMM level | Website |
|---|---|
| MMM International | medicalmissionarymovement.org |
| **MMM African Chapter** | **this repository** |
| National chapters, e.g. MMM Kenya Chapter (MMMK) | their own sites, e.g. mmmkenya.org |

This site stores **no financial data**: only the chapters, leaders, shared events, website text, pages and
contact messages.

## What's in the box

| Part | What it does |
|---|---|
| `services/web` | Renders every page on the server (fast on phones, good link previews), the officers' area and invitation sign-up |
| `services/auth` | Officer accounts by invitation, sign-in with lockout, rotating sessions, roles (owner, editor) |
| `services/directory` | The family structure (international, continental, national), leaders, events, contact messages, editable website text and officer-written pages |
| `libs/common` | Shared config, logging, auth checks, rate limiting, health and metrics |
| `deploy/` | Caddy gateway (HTTPS), Postgres, encrypted backups, Prometheus, Alertmanager, Grafana |
| `infra/terraform` | Creates the server (Oracle Cloud free tier) and, optionally, the DNS record (Cloudflare) |

Everything is built on open, portable technology: ordinary Docker (OCI) images, Docker Compose, PostgreSQL,
Redis, Caddy and Terraform. Nothing depends on one cloud; the same stack runs on a laptop, any Linux server,
or Kubernetes. Read [docs/architecture.md](docs/architecture.md), [docs/security.md](docs/security.md),
[docs/runbook.md](docs/runbook.md) and [docs/infrastructure.md](docs/infrastructure.md).

## Run it on your computer

Needs Docker with Compose v2.24+.

```sh
make init                 # creates .env; edit it if you like, then run again to generate secrets
make init
make dev                  # http://localhost:8081
make create-owner email=you@example.com name="Your Name"
```

Sign in at http://localhost:8081/officers, invite other officers, and add chapters, leaders and events.

To publish the copy on your computer, `make share` gives a free Cloudflare link, or a permanent address such as
https://mmmafrica.nabec.co.ke: see [docs/share-from-your-computer.md](docs/share-from-your-computer.md).

## Put it on the internet

* **From your own computer at mmmafrica.nabec.co.ke** (current setup, next to the Martha site):
  [docs/share-from-your-computer.md](docs/share-from-your-computer.md).

* **With Terraform** (recommended): [docs/infrastructure.md](docs/infrastructure.md) creates an Oracle Cloud
  free-tier server that installs and starts the site by itself on first boot.
* **On any Linux server you already have**: clone this repository, run `./scripts/setup-ubuntu-server.sh`,
  `make init`, set `SITE_DOMAIN` and `ACME_EMAIL` in `.env`, `make init` again, `make up`, then
  `make create-owner email=... name=...`.

Leaders edit everything visitors read (text, colour scheme, pages, chapters, leaders, events) from the
officers' area at `/officers`. See [docs/share-from-your-computer.md](docs/share-from-your-computer.md#editing-the-website).

After that, deployments go through GitHub Actions: see [docs/runbook.md](docs/runbook.md#deploying-a-new-version).

## Develop

```sh
python3 -m venv .venv && . .venv/bin/activate
pip install -e libs/common -r requirements-dev.txt -r services/<service>/requirements.txt
make test lint
```

Credits: built on the same foundation as the Martha Kemunto Ongosi memorial site. Map of Africa from
[@svg-maps/world](https://github.com/VictorCazanave/svg-maps) by Victor Cazanave, CC BY 4.0.
