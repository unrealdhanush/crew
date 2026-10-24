---
title: Self-hosting
sidebar_position: 1
description: Run Crew and FalkorDB together with Docker Compose.
---

Crew is one server per event or organization. Teams that want everything inside their network run it themselves.

```bash
cp .env.example .env        # optional: keys are read from it if present
docker-compose --profile app up -d
```

This builds the Crew image and starts it with FalkorDB. The app is on port 8765 (set `CREW_HTTP_PORT` to change
the host port). Without `--profile app`, only FalkorDB starts, for running `crew serve` from a checkout.

| Detail | Value |
|---|---|
| Image | `python:3.11-slim`, Crew installed with pip, runs as user `crew` |
| Volumes | `./data` → `/app/data` (team and event survive rebuilds), `crew-cache` → `/app/.cache` |
| FalkorDB | Reached as `falkordb:6379` inside the network |

## TrueForge from the container

`localhost` inside the container is the container itself. If TrueForge runs on the host, set
`TRUEFORGE_BASE_URL=http://host.docker.internal:8790` in `.env`. For a hackathon demo, `crew serve` on the laptop
is simpler.

## Phones and stickers

Phones must reach the server: bind to all interfaces and use the machine's network address on the stickers.

```bash
CREW_HOST=0.0.0.0 crew serve
```

There's no login (see [HTTP API](../reference/http-api.md)), so only do this on a network you trust.

## Render

`render.yaml` at the repo root is a Render blueprint (New → Blueprint → pick the repo). It creates three services:

| Service | What it is |
|---|---|
| `crew-docs` | This documentation, as a free static site |
| `crew` | The Crew server from the `Dockerfile`, on a paid instance (free ones sleep and take ~1 minute to wake), with a 1 GB disk for the saved team and event |
| `crew-falkordb` | FalkorDB as a private service with a 1 GB disk |

Render asks for `OPENAI_API_KEY`, `BRIGHTDATA_API_KEY` and `GITHUB_TOKEN` when you apply it, and generates
`CREW_ACCESS_TOKEN` (see the `crew` service's Environment). With it set, every request needs the token:

- **Browser or phone:** open `https://<your-crew>.onrender.com/?token=<token>` once; a cookie remembers it. Render's
  generated token is base64; Crew accepts it pasted as-is, but a hex token (`openssl rand -hex 32`) avoids URL encoding.
- **TrueForge:** edit the `crew` connector to `https://<your-crew>.onrender.com/mcp` with header auth
  `Authorization: Bearer <token>`. Then, from your checkout:

  ```bash
  CREW_ACCESS_TOKEN=<token> crew forge-setup --server https://<your-crew>.onrender.com
  ```

  `--server` reads the team from the deployed Crew instead of your local graph.

Render's health check uses `/api/health`, which returns 503 when FalkorDB is unreachable. Set `DOCS_URL` on the docs
site if Render gives it an address other than `https://crew-docs.onrender.com`.

:::note Not yet tested
The blueprint hasn't been applied on Render yet.
:::
