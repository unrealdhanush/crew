---
title: Set up your team
sidebar_position: 2
description: Add teammates and repos, build the graph and get the coverage plan.
---

## Before you start

Publish the agenda first ([Publish an event](./organizer.md)). You can build a team without it, but there's nothing
to plan until sessions exist.

## Steps

1. Open `/team` and enter a team name.
2. For each teammate:
   - **GitHub username**, then **Find repos**: their public repos, most recently pushed first, without forks or
     archived repos. Tick the ones they work on.
   - **Add a repo by name** (`owner/repo`) for anything not listed.
   - **Upload a dependency file** for code that isn't on GitHub (see [Private repos](./private-repos.md)).
   - **Name** and **Goals**, comma separated, e.g. `agents, evals, supply-chain-security`.
3. Leave **Crew Scout reads READMEs and goals** ticked to add README topics (see [TrueForge agents](./trueforge.md)).
4. Click **Build our graph**.

The build runs on the server. For each repo Crew reads GitHub's dependency graph (direct dependencies only), or
falls back to `requirements.txt`, `pyproject.toml`, `package.json` and `go.mod`. The feed reports which source it
used:

```text
· Reading unrealdhanush/openmemore on GitHub
· unrealdhanush/openmemore: 8 dependencies from dependency files
✓ 6 bridges between your code and the agenda: fastmcp, mcp, agents, evals, github-actions, supply-chain-security
✓ Plan ready: 4 of 4 relevant sessions covered
```

Steps are slowed slightly (`CREW_BUILD_PACE`, 0.4 s) so the graph visibly grows on a projector.

## The result

- **Bridges:** where your code and goals meet the agenda.
- **Coverage plan:** each person's sessions, each with a reason, e.g.
  `jlowin/wmata_mcp depends on fastmcp`.

The team is saved to `data/team.json` (only repos that could be read), so the CLI and a rebuild use the same team.

## Troubleshooting

**"Skipped owner/repo: Repo not found (private repos need a token)"**: the repo doesn't exist or is private. Add a
token, see [Private repos](./private-repos.md).

**"GitHub rate limit reached"**: anonymous GitHub access allows 60 requests an hour. Set `GITHUB_TOKEN`. Responses
are cached for 6 hours, so rehearsals with the same repos don't use the limit again.

**"No bridges yet"**: nothing in your code matches the agenda by name. Run Crew Scout, add goals, or check
normalization in `crew/ingest.py` (`ALIASES`).
