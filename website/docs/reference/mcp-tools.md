---
title: MCP tools
sidebar_position: 3
description: The tools Crew's MCP server exposes to agents, and how each is labelled for approvals.
---

The MCP endpoint is `http://<crew>:8765/mcp` (streamable HTTP, no auth). Every tool returns JSON; errors come back
as `{"error": "..."}` instead of failing the agent's turn. Answers include `paths`: agents should show them, since
they're the explanation.

The **label** is the MCP annotation TrueForge uses for approvals: read-only tools never pause, and
`publish_digest` is destructive.

## Planning

| Tool | Label | Arguments | Returns |
|---|---|---|---|
| `plan_coverage` | write | `max_sessions_per_person?` | Each person's schedule with reasons, sessions missed due to clashes |
| `explain_session` | read-only | `handle`, `session` | Paths from the person's code and goals to the session, who's assigned |
| `find_blind_spots` | read-only | | Unassigned sessions touching our code, dependencies the conference doesn't cover |
| `ripple` | read-only | `package` | Affected repos and owners, notes about it, sessions mentioning it |
| `check_in` | write | `handle`, `session` | Same as an NFC tap: records attendance, returns why it matters |

## Notes and memory

| Tool | Label | Arguments | Returns |
|---|---|---|---|
| `add_note` | write | `handle`, `note`, `session?` | Packages, topics, fetched sources, breaking changes with ripple |
| `ask_team` | read-only | `question` | An answer citing `[N1]`/`[S1]`, the citations and paths |
| `draft_digest` | read-only | | The draft Markdown. Sends nothing |
| `publish_digest` | **destructive** | | Saves the digest and posts to Slack if configured. Needs approval |

## Crew Scout

| Tool | Label | Arguments | Returns |
|---|---|---|---|
| `team_repos` | read-only | | Repos and people, which Scout has done, the agenda's topic names |
| `repo_profile` | read-only | `repo` | Description, dependencies, README excerpt (untrusted), owner goals, agenda topics |
| `tag_repo` | write | `repo`, `topics[]`, `evidence` | Tagged topics and new paths to sessions. Rejects evidence that isn't a full sentence (5+ words) from the README |
| `map_goals` | write | `handle`, `topics[]` | Mapped topics and new paths to sessions |

## Setup and escape hatch

| Tool | Label | Arguments | Returns |
|---|---|---|---|
| `ingest_agenda` | write | `urls[]`, `fresh?` | Sessions loaded per page |
| `ingest_team` | write | `team_file?` (default `data/team.json`) | Members, repos and packages loaded |
| `graph_query` | read-only | `cypher` | Rows from a read-only Cypher query (writes are rejected) |
