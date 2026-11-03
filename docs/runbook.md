# Runbook

Commands run from the repository folder on the server.

## Everyday

| Task | Command |
|---|---|
| See what's running | `make ps` |
| Follow logs | `make logs s=directory` (any service name) |
| Restart one service | `docker compose restart directory` |
| Take a backup now | `make backup-now` |
| Check the public site | `make smoke url=https://<domain>` |

## First-time setup checklist

- [ ] `make init`, edit `.env`, `make init` again
- [ ] `make up`, then `make create-owner email=... name=...`
- [ ] Sign in at `/officers`, invite the other officers (the invite link is shown once; send it privately)
- [ ] Officers' area → Leaders: add the African Chapter's officers
- [ ] Officers' area → Chapters: check MMMK's details, add any other national chapters
- [ ] Copy `secrets/backup_passphrase` to a password manager or printed copy kept by two officers
- [ ] Set `OFFSITE_S3_*` and the two `secrets/offsite_s3_*` files so backups also leave the server
- [ ] Set `ALERT_EMAIL_TO`, `SMTP_*` and `secrets/smtp_password` so alerts are emailed; `make init && make up`
- [ ] Restore drill: restore last night's backup on a spare machine (below) and check the site

## Private preview, then launch

New installs start in **private preview** (`SITE_PREVIEW=true` in `.env`): every page asks for a password and
search engines are told not to index the site. A bar at the top says the site is not public yet.

1. `make init` prints the preview login: user `preview`, password in `secrets/preview_password`.
2. Send reviewers the address and that login.
3. Reviewers who should edit content also need an officer account: invite them from `/officers`
   (Officer accounts tab). They sign in as usual, behind the preview password.

To launch: set `SITE_PREVIEW=false` in `.env`, then `make init && make up`. The password and the preview bar
disappear and the site is public. To return to preview later, set it back to `true` and run the same commands.

## Monitoring

Dashboards are only reachable from the server itself. From your computer:

```sh
ssh -L 3000:localhost:3000 -L 9090:localhost:9090 -L 9093:localhost:9093 you@server
```

Then open http://localhost:3000 (Grafana; user `admin`, password in `secrets/grafana_admin_password`),
http://localhost:9093 (current alerts).

| Alert | What to do |
|---|---|
| SiteDown / ServiceDown | `make ps`, `make logs s=<service>`; `docker compose up -d` restarts anything stopped |
| BackupMissing | `make logs s=backup`; then `make backup-now` |
| CertificateExpiringSoon | `make logs s=caddy`; check DNS still points at the server and port 80 is open |
| DiskFillingUp | `docker system prune`; lower `BACKUP_KEEP_DAYS`; grow the disk |

## Deploying a new version

Every push to `main` is tested, scanned and published as images tagged with the commit SHA.

1. GitHub → Actions → **Deploy** → Run workflow, with the commit SHA.
2. A reviewer approves the `production` environment.
3. The workflow takes a backup, switches to the new images, waits for every health check, runs the smoke
   test, and **rolls back automatically** if anything fails.

One-time GitHub setup: repository secrets `DEPLOY_HOST`, `DEPLOY_USER`, `DEPLOY_SSH_KEY`, `DEPLOY_KNOWN_HOSTS`
(and `PREVIEW_PASSWORD` while the site is in private preview);
variables `SITE_DOMAIN`, `DEPLOY_PATH`; an environment named `production` with required reviewers; and on the
server, `docker login ghcr.io` with a token that can read packages.

By hand on the server: `NEW_TAG=<sha> REGISTRY=ghcr.io/<owner>/<repo> ./scripts/deploy.sh`.

## Backups and restore

Every night at `BACKUP_HOUR_UTC` the backup container dumps each database, encrypts everything with the backup passphrase, keeps `BACKUP_KEEP_DAYS` days locally, and copies each archive
off-site if configured. The `BackupMissing` alert fires if a night is missed.

To restore (this replaces current data):

```sh
ls backups/archive/
make restore file=backups/archive/20261021T000000Z.tar.gz.gpg
```

On a fresh server: clone, `make init`, put back the **same** `secrets/backup_passphrase`, copy the archive
into `backups/archive/`, `make up`, then `make restore file=...`.

Off-site copies go to any S3-compatible storage (`OFFSITE_S3_*`) or any rclone remote such as Google Drive,
pCloud or Dropbox (`OFFSITE_REMOTE`, with its config in `secrets/rclone.conf`).

## Rotating secrets

* JWT keys (signs everyone out): delete `secrets/jwt_*.pem`, `make init`, `docker compose up -d`.
* Database passwords: change the role password in Postgres first (`ALTER ROLE ... PASSWORD`), update
  `secrets/pg_<service>_password`, `make init` (regenerates the connection strings), `docker compose up -d`.

