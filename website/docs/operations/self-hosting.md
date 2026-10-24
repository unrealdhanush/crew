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
