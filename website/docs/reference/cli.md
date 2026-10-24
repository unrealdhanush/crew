---
title: CLI
sidebar_position: 1
description: Every crew command and its arguments.
---

`uv sync` in a checkout (or `pipx install` for the CLI alone) installs `crew`. `python -m crew.cli` is the same thing. Commands print JSON.

## On a teammate's machine

These only talk to the Crew server, set with `CREW_SERVER` or `--server`, and don't need FalkorDB.

### `crew scan`

Send a project's dependency names to Crew. Only dependency files are opened; source code is never read.

```bash
crew scan <handle> [path] [--name NAME] [--server URL] [--dry-run]
```

| Argument | Default | Description |
|---|---|---|
| `handle` | (required) | The teammate's handle (their GitHub username) |
| `path` | `.` | Folder to scan, up to 4 levels deep |
| `--name` | the folder name | Project name, shown as `local:<handle>/<name>` |
| `--server` | `CREW_SERVER` | Crew server address |
| `--dry-run` | off | Print what would be sent; send nothing |

### `crew open`

Open the team's Crew in the browser.

```bash
crew open [--server URL]
```

## On the machine hosting Crew

These read and write the graph directly, so FalkorDB must be reachable.

| Command | What it does |
|---|---|
| `crew serve` | Run the web app, graph view and MCP endpoint |
| `crew init` | Create the graph's indexes (safe to repeat) |
| `crew reset` | **Delete the whole graph** and recreate the indexes |
| `crew team <file>` | Load a team file, e.g. `data/team.json` |
| `crew agenda <url>... [--fresh]` | Scrape agenda pages with Bright Data (`--fresh` skips the cache) |
| `crew agenda-file <file>` | Load sessions from JSON, e.g. `data/agenda.sample.json` |
| `crew plan` | Compute the coverage plan |
| `crew blind` | Blind spots, and dependencies the conference doesn't cover |
| `crew ripple <package>` | Repos and owners affected by a change to a package |
| `crew why <handle> <session>` | Paths explaining why a session matters to someone (`session` = id or part of the title) |
| `crew note <handle> "<text>" [--session S]` | Save a note |
| `crew ask "<question>"` | Answer from the team's notes, with citations |
| `crew digest` | Draft the team digest (doesn't send it) |
| `crew forge-setup [--server URL]` | Create or update Crew's agents in TrueForge (`--server`: read the team from a deployed Crew) |
| `crew scout [--direct]` | Run Crew Scout in TrueForge (`--direct`: call OpenAI instead) |
