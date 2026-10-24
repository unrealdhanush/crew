---
title: Installation
sidebar_position: 1
description: Install Crew, FalkorDB and the keys Crew needs.
---

Crew is a Python server (web app, graph view and MCP endpoint) backed by FalkorDB. This page sets up the machine
that hosts it. Teammates who only want the `crew scan` CLI need step 3 alone; see
[Private repos](../guides/private-repos.md).

## Prerequisites

- [uv](https://docs.astral.sh/uv/) (it installs Python 3.11 for you if needed)
- Docker. On macOS with [Colima](https://github.com/abiosoft/colima), use the `docker-compose` command, since
  `docker compose` may not be registered.
- Optional: Node.js 22.14+ for [TrueForge](../guides/trueforge.md)

<Steps>
<Step title="Get the code">

```bash
git clone <your crew repo> crew && cd crew
```

</Step>
<Step title="Start FalkorDB">

```bash
docker-compose up -d
```

FalkorDB listens on 6379 and the FalkorDB Browser on 3000. The Crew container is behind a profile and doesn't start
here; see [Self-hosting](../operations/self-hosting.md).

</Step>
<Step title="Install Crew">

```bash
uv sync
uv run crew --help
```

This creates `.venv` with the exact versions in `uv.lock` and installs the `crew` command (the same as
`python -m crew.cli`). Activate `.venv` (`. .venv/bin/activate`) to type `crew` directly.

</Step>
<Step title="Add keys">

```bash
cp .env.example .env
```

Crew runs without any keys, but some features need them:

| Key | Needed for |
|---|---|
| `OPENAI_API_KEY` | Agenda extraction, notes, team memory, digest, Crew Scout without TrueForge |
| `BRIGHTDATA_API_KEY` (+ zone names) | Scraping the live agenda, fetching the sources notes mention |
| `GITHUB_TOKEN` | Raising GitHub's limit from 60 to 5,000 requests an hour |

Every setting is in [Configuration](../reference/configuration.md).

</Step>
<Step title="Start Crew">

```bash
crew serve
```

```text
Crew app:    http://127.0.0.1:8765/
Graph view:  http://127.0.0.1:8765/viz
Tap demo:    http://127.0.0.1:8765/sim
Crew MCP:    http://127.0.0.1:8765/mcp
```

</Step>
</Steps>

Next: the [Quickstart](./quickstart.md).
