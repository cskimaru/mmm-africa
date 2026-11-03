# Architecture

```
                         Internet
                            │ 80/443
                      ┌─────▼─────┐   HTTPS, security headers, request size limits,
                      │   Caddy   │   hides /metrics /healthz /docs
                      └─────┬─────┘
          ┌─────────────────┼──────────────────┐
          │/                │/api/auth         │/api/directory
     ┌────▼────┐       ┌────▼────┐       ┌─────▼─────┐
     │   web   │       │  auth   │       │ directory │
     └────┬────┘       └────┬────┘       └─────┬─────┘
          │ reads directory │                  │
          └──────────────── │ ─────────────────┤
                            │  ┌───────────────▼──────────────────┐
                            └─►│ PostgreSQL: one database + login │
                               │ per service                      │
                               └──────────────────────────────────┘
                         Redis (rate limits)
```

## Services

Each service is a small FastAPI application with its own database and its own database login. A service
cannot read another service's data; they talk over HTTP only where needed.

* **auth** owns officer accounts. It is the only service holding the JWT private key. It issues a short-lived
  (15 minute) access token and a rotating refresh token, both in `HttpOnly; Secure; SameSite=Strict` cookies.
  Every other service verifies tokens with the public key only.
* **directory** owns the MMM family structure and what the African Chapter shares with its chapters:
  * `units`: one row per level of the family. `international` (MMM International) → `continental` (the
    African Chapter) → `national` (e.g. MMMK). A unit may only sit under the level directly above it, as in
    the church structure. National units have a country code that colours the map.
  * `officers`: leaders of a unit (name, role, term). Each unit lists only its own leaders.
  * `events`: shared activities such as the Annual Convention, with a host chapter. Whether an event is
    coming up, happening or held is worked out from the date, so the site says "thank you" by itself once it ends.
  * `messages`: the contact form, with a honeypot and a rate limit.
* **web** renders HTML with Jinja (autoescaped). Anonymous page data is cached for 30 seconds and the last
  good copy is served if the directory is down, so the site stays up during an update or a burst of visitors.

## Separate websites, one family

The African Chapter and each national chapter run **separate websites** with separate accounts, leaders and
money. They coordinate where needed:

* This site links up to MMM International and down to each national chapter's own website.
* National chapter pages show what the African Chapter needs (summary, contact, website) and send visitors to
  the chapter's own site for local matters.
* Shared events name their host chapter and link to its site for registration and photos.

## Data and ownership

| Service | Database | Main tables |
|---|---|---|
| auth | `auth` | users, refresh_tokens, invitations, audit_log |
| directory | `directory` | units, officers, events, messages, audit_log |

Schema changes are Alembic migrations in each service's `migrations/` folder. They run automatically when a
service starts; a Postgres advisory lock stops two replicas migrating at once. CI applies, rolls back and
re-applies every migration on real PostgreSQL.

## Why these choices

* **Microservices, but few.** The split follows what matters for safety: accounts and content fail and scale
  independently, and a bug in one cannot touch the other's data. One person can run all of it on one server.
* **One server with Docker Compose** rather than Kubernetes. A chapter website gets bursts of traffic around
  events, not sustained load. Compose with health checks, restart policies, resource limits and automatic
  rollback gives the reliability that matters at a fraction of the cost. The images are ordinary OCI images
  and move to Kubernetes unchanged if that is ever needed.
* **Terraform for the server, a setup script for what runs on it.** Terraform creates the cloud pieces
  (network, firewall, server, DNS) and can recreate them anywhere. On first boot, cloud-init runs the same
  `scripts/setup-ubuntu-server.sh` you would run by hand, so a server built either way is identical.
