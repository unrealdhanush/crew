---
title: TrueForge agents
sidebar_position: 5
description: Run Crew's agents in TrueForge on OpenAI models, including Crew Scout and the digest approval.
---

[TrueForge](https://trueforge.dev) is TrueFoundry's open-source agent harness. Crew's agents run in it on OpenAI
models and use Crew through its MCP server:

- **`crew-<handle>`**: one per teammate. Plans, "why am I here?", check-ins, notes, ripple, team memory, digest.
- **`crew-scout`**: reads each repo's README and each person's goals and maps them onto the agenda's topics.

:::note Verification
Tested in TrueForge on Oct 24 with `openai/gpt-5-4-mini`: `crew forge-setup` created and updated the agents, Scout
tagged real repos from inside TrueForge (also as a hand-off from the `/team` build), and a teammate agent drafted
the digest freely but paused for approval on `publish_digest`.
:::

## One-time setup

1. Start TrueForge and open `http://localhost:8790`. TrueForge blocks outbound requests to local addresses, so
   allow Crew's address explicitly (a JSON array; everything else stays blocked):

   ```bash
   OUTBOUND_URL_ALLOWED_HOSTS='["127.0.0.1"]' npx @truefoundry/trueforge@latest
   ```

   Without it, adding the connector fails with `Outbound URL blocked for host "127.0.0.1"`.

2. **Settings → Models:** add OpenAI and paste your key.
3. **Settings → Connectors → Add MCP Server:** name `crew`, URL `http://127.0.0.1:8765/mcp`, no auth. (The SDK
   can't register connectors, so this one step is in the UI.)
4. Build your team on `/team`, then create the agents:

   ```bash
   crew forge-setup
   ```

   It creates or updates `crew-scout` and a `crew-<handle>` agent per teammate. They use `CREW_FORGE_MODEL`, which
   must be a model TrueForge lists (e.g. `openai/gpt-5-4-mini`); it defaults to `openai/$OPENAI_MODEL`. Crew's
   tools are preloaded, so agents call them directly. Re-run it after the team changes.

## Crew Scout

Dependencies show what code is exposed to. Scout adds what a repo is about and what people want to learn, in the
agenda's own words. It can use only these four MCP tools (its agent spec enables nothing else):

| Tool | What it does |
|---|---|
| `team_repos` | Lists repos and people, which are done, and the agenda's topic names |
| `repo_profile` | A repo's description, dependencies, README excerpt (marked untrusted) and the agenda topics |
| `tag_repo` | Records 1–6 topics. `evidence` must be a full sentence (5+ words, not a heading) copied from the README, or it's rejected |
| `map_goals` | Maps a teammate's stated goals onto 1–6 topics |

Each result is a graph edge carrying its evidence, so a plan reason reads
`unrealdhanush/openmemore's README is about agents` and the quote is one click away. README topics weigh 1.5 in the
plan, below dependencies (3) and GitHub topics (2); see [The graph](../concepts/graph.md).

Scout runs:
- from the team build, when **Crew Scout reads READMEs and goals** is ticked; the feed shows each tool call,
- with `crew scout`,
- without TrueForge: if TrueForge isn't reachable or fails, the same job runs as direct OpenAI calls
  (`crew scout --direct` forces this). If that fails too, the build carries on without Scout.

## Approvals

TrueForge pauses for approval on tools the server marks as write or destructive. Every Crew tool is labelled (see
[MCP tools](../reference/mcp-tools.md)), and `crew forge-setup` sets approval on **`publish_digest` only**, so
agents don't stop at every note and check-in but can't send the digest to the team without a human clicking
**Allow**.
