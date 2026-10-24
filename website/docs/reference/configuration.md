---
title: Configuration
sidebar_position: 2
description: Every environment variable Crew reads, with defaults, and the files it keeps.
---

Settings come from the environment, and from a `.env` file in Crew's home folder (the repo checkout, or `~/.crew`
when installed as a CLI). Real environment variables win over `.env`.

## Server

| Variable | Default | Description |
|---|---|---|
| `CREW_HOST` | `127.0.0.1` | Address to listen on. Use `0.0.0.0` so phones on the network can reach `/tap` |
| `CREW_PORT` | `8765` | Port |
| `CREW_HOME` | repo checkout, else `~/.crew` | Folder holding `.env`, `data/` and `.cache/` |
| `CREW_ACCESS_TOKEN` | (none) | If set, every request needs it: `Authorization: Bearer <token>`, or open a page once with `?token=<token>` (sets a cookie). `/api/health` stays open |
| `CREW_DATA_DIR` | `$CREW_HOME/data` | Where `team.json`, `event.json` and digests are kept (point it at a persistent disk when deployed) |
| `CREW_BUILD_PACE` | `0.4` | Seconds between build steps so the graph visibly grows; `0` for full speed |

## Graph

| Variable | Default | Description |
|---|---|---|
| `FALKORDB_HOST` | `localhost` | FalkorDB host |
| `FALKORDB_PORT` | `6379` | FalkorDB port |
| `CREW_GRAPH` | `crew` | Graph name inside FalkorDB |

## OpenAI

| Variable | Default | Description |
|---|---|---|
| `OPENAI_API_KEY` | (none) | Read by the OpenAI SDK |
| `OPENAI_MODEL` | `gpt-4.1-mini` | Model for extraction, notes, memory, digest and direct Scout |

## Bright Data

| Variable | Default | Description |
|---|---|---|
| `BRIGHTDATA_API_KEY` | (none) | API key |
| `BRIGHTDATA_UNLOCKER_ZONE` | `web_unlocker1` | Web Unlocker zone, for agenda pages and sources |
| `BRIGHTDATA_SERP_ZONE` | `serp_api1` | SERP zone, for finding a note's sources |
| `WEB_CACHE_SECONDS` | `21600` (6 h) | How long scraped pages and GitHub responses are reused |

## GitHub

| Variable | Default | Description |
|---|---|---|
| `GITHUB_TOKEN` | (none) | Server-wide token: raises the limit to 5,000/hour and can read private repos it has access to |
| `GITHUB_API_URL` | `https://api.github.com` | GitHub Enterprise Server: `https://<host>/api/v3` |

## TrueForge

| Variable | Default | Description |
|---|---|---|
| `TRUEFORGE_BASE_URL` | `http://localhost:8790` | TrueForge server |
| `CREW_FORGE_MCP` | `crew` | Name of Crew's connector in TrueForge |
| `CREW_FORGE_MODEL` | `openai/$OPENAI_MODEL` | Model for Crew's agents; must be one TrueForge lists, e.g. `openai/gpt-5-4-mini` |

## CLI and integrations

| Variable | Default | Description |
|---|---|---|
| `CREW_SERVER` | `http://$CREW_HOST:$CREW_PORT` | Where `crew scan` and `crew open` find the server |
| `SLACK_WEBHOOK_URL` | (none) | If set, `publish_digest` also posts to Slack |

## Files

| Path | Contents |
|---|---|
| `data/team.json` | The team: members, goals, repos, uploads. Written by builds. Git-ignored |
| `data/event.json` | The published event: name, agenda URLs. Git-ignored |
| `data/agenda.sample.json` | Four made-up sessions for testing |
| `data/digests/` | Published digests |
| `.cache/` | Scraped pages, GitHub responses, the viewer highlight, the digest draft |
