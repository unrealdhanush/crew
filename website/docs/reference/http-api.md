---
title: HTTP API and pages
sidebar_position: 4
description: The web pages and JSON endpoints served by crew serve.
---

All on the same server as the MCP endpoint (default `http://127.0.0.1:8765`). Responses are JSON; errors are
`{"error": "..."}`.

:::danger Set an access token before exposing Crew
Without `CREW_ACCESS_TOKEN`, none of these endpoints check who's calling, including `/api/reset`, which deletes the
graph. Keep Crew on `127.0.0.1` unless it's set (see [Configuration](./configuration.md)).
:::

## Pages

| Path | Page |
|---|---|
| `/` | Home: the pitch, live counts, clear graph |
| `/organizer` | Publish the agenda |
| `/stickers` | Printable NFC/QR door stickers |
| `/team` | Team onboarding and live build |
| `/viz` | Live graph view; highlights the latest answer's paths. Shows bridges only by default, with a toggle for everything |
| `/tap?s=<session id>` | What a door sticker opens: check-in and note |
| `/sim` | Tap simulator for demos |

## Graph and status

| Method | Path | Description |
|---|---|---|
| GET | `/api/graph?focus=1` | Edges and nodes for the viewer (up to 2,000 edges), plus `total` counts. By default (`focus=1`) only bridges are kept: people, repos, notes, the packages and topics linking them to sessions, those sessions, and the sources notes cite; the current highlight always stays. `focus=0` returns everything |
| GET | `/api/highlight` | The paths behind the latest answer: `{title, paths, at}` |
| GET | `/api/health` | `{"ok": true}`, or 503 when FalkorDB is unreachable. Open even with `CREW_ACCESS_TOKEN` set |
| GET | `/api/stats` | Counts: `persons`, `repos`, `packages`, `sessions`, `notes`, `bridges` |
| GET | `/api/setup` | Saved `team`, `event`, and the `github` API address in use |
| GET | `/api/doors` | People and sessions, for the tap pages and stickers |

## Builds

| Method | Path | Body / query | Description |
|---|---|---|---|
| POST | `/api/build` | `{"kind": "event" \| "team", "payload": {...}}` | Start a background build. One at a time |
| GET | `/api/build?since=N` | | Progress events after index `N`, `state` (`running`, `done`, `error`), `result` |
| POST | `/api/reset` | `{"confirm": "reset"}` | Delete the graph |

Event payload: `{"name", "urls": [...], "sample": bool}`.
Team payload: `{"team", "members": [{"handle", "name", "goals": [...], "repos": [...], "uploads": [...]}], "token"?, "scout"?}`.
The token is used for that build only and not saved.

## GitHub and dependency lists

| Method | Path | Description |
|---|---|---|
| GET | `/api/github/repos?user=U&org=O` | A user's public repos, plus the org's (private too with an `X-GitHub-Token` header) |
| POST | `/api/parse` | `{"filename", "text"}` → `{"deps", "dev_deps"}`. The file isn't kept |
| POST | `/api/import` | Where `crew scan` sends `{"handle", "name", "deps", "dev_deps", "via"}` |

## Tap flow

| Method | Path | Body | Description |
|---|---|---|---|
| POST | `/api/tap` | `{"handle", "session"}` | Check in; returns the session, who's assigned, and why-paths |
| POST | `/api/note` | `{"handle", "text", "session"?}` | Save a note (see [Notes](../guides/notes-and-digest.md)) |
