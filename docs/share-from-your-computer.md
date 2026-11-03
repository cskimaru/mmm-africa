# Host MMM Africa from your own computer at a nabec.co.ke address

The whole site runs on your computer, and a free Cloudflare tunnel publishes it at a permanent address on the
NABEC domain, for example **https://mmmafrica.nabec.co.ke**. This is the same setup as the Martha memorial
(`martha.nabec.co.ke`), and the two run side by side: MMM Africa uses port 8081 on your computer, Martha 8080.

**Limits to know:**

* The site is online only while your computer is on, awake and connected, with `make share` running.
* Chapters, leaders, events and messages are stored on your computer. Backups run every day; they move to a
  real server later with a backup and restore (see the end).

## 1. Tools (already installed if Martha runs on this computer)

Docker Desktop (with WSL 2 on Windows, running commands in the **Ubuntu** app), `make` and `git`.

## 2. Get the code (once)

```sh
cd ~
git clone https://github.com/cskimaru/mmm-africa.git
cd mmm-africa
```

If the repository is private, sign in with your GitHub username and a personal access token
(GitHub → Settings → Developer settings → Fine-grained tokens, access to `mmm-africa`, *Contents: Read-only*).

## 3. Create the tunnel for the new address (once)

nabec.co.ke is already on Cloudflare (Martha uses it), so there is nothing to buy.

1. In Cloudflare open **Zero Trust** → **Networks** → **Tunnels** → **Create a tunnel** → **Cloudflared** →
   name it `mmm-africa`. On the install page, copy the long **token** (the text after `--token`). You don't
   need to run that command.
2. In the tunnel's **Public hostname** (also called *Published application routes*) add: subdomain
   `mmmafrica`, domain `nabec.co.ke`, type **HTTP**, URL `caddy:80`. Save. Cloudflare creates the DNS record.

Use a separate tunnel from Martha's: each site's `caddy:80` lives in its own Docker network.

## 4. Configure and start

```sh
make init                    # creates .env
nano .env                    # set the lines below, save with Ctrl+O, Enter, Ctrl+X
```

```
SITE_DOMAIN=mmmafrica.nabec.co.ke
PUBLIC_HOSTNAME=mmmafrica.nabec.co.ke
CLOUDFLARE_TUNNEL_TOKEN=eyJhIjoi...the long token...
CONTACT_EMAIL=...            # shown in the footer
SITE_PREVIEW=true            # password-protected until the committee approves
```

Then:

```sh
make share
```

The first time this builds everything (several minutes). It ends with:

```
The site is shared at:      https://mmmafrica.nabec.co.ke
Preview login:             user 'preview', password '…'
On this computer:          http://localhost:8081
```

Create the first officer account (yours), then sign in at https://mmmafrica.nabec.co.ke/officers:

```sh
make create-owner email=you@example.com name="Your Name"
```

From the officers' area, invite the African Chapter officers and add leaders, chapters and events.

## Every day

| Task | Command |
|---|---|
| Start, or update after `git pull` (same address) | `make share` |
| Stop | `make share-stop` |
| See what's running | `make ps` |
| Something looks wrong | `make logs s=web` (or `directory`, `auth`, `caddy`, `cloudflared`) |
| Get the latest version from GitHub | `git pull`, then `make share` |
| Take a backup | `make backup-now` |

## Launching publicly

While `SITE_PREVIEW=true`, visitors need the preview login, and a bar at the top lets reviewers try the four
colour schemes. When the committee has chosen:

1. In `.env` set `SITE_PALETTE=` to the chosen scheme (`sunrise`, `coast`, `highlands` or `evening`) and
   `SITE_PREVIEW=false`.
2. `make share`.

## Moving to its own domain or a real server later

* **Own domain** (e.g. `mmmafrica.org`): add the domain to Cloudflare, add a second public hostname to the same
  tunnel, then change `SITE_DOMAIN` and `PUBLIC_HOSTNAME` in `.env` and run `make share`.
* **Real server:** `make backup-now`, keep `.env`, the `secrets/` folder and the newest file in
  `backups/archive/`, then follow [infrastructure.md](infrastructure.md) and restore that backup on the server
  ([runbook.md](runbook.md#backups-and-restore)). Everything the officers added comes across.

Keep the tunnel token private: anyone who has it can put a site on that address.
