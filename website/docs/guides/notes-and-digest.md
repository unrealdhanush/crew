---
title: Notes, team memory and the digest
sidebar_position: 6
description: Turn one-line notes into cited knowledge and a digest for the people at home.
---

:::note Verification
Notes, team memory and the digest were tested against OpenAI on Oct 24. Fetching a note's sources needs Bright Data
zones and hasn't been run yet; without them, notes still save, link and ripple, just with no sources.
:::

## Notes

A teammate writes one line, from a door tap, their agent, or the CLI:

```bash
crew note <handle> "fastmcp 3 drops SSE, migrate to streamable http" --session "MCP"
```

Crew then:
1. links the note to its author and the session,
2. extracts the packages and topics it mentions, and any announced breaking changes,
3. fetches sources: links in the note, otherwise a Bright Data search for the official docs or release notes,
   summarized and linked as `Note -CITES-> Source`,
4. for each breaking change, runs **ripple**: which of the team's repos depend on that package, and who owns them.

## Team memory

```bash
crew ask "what did we learn about MCP?"
```

Crew finds notes, sessions and sources with full-text search and graph lookups, and answers **only** from them,
citing items as `[N1]` (notes) and `[S1]` (sources) and naming who captured each point. If nothing matches, it says
"Nobody on the team captured anything about this yet."

## Digest

`draft_digest` writes a short Markdown digest for the people who stayed home ("What changes for us", "Worth
knowing", "Gaps") from the team's notes and the current blind spots. Nothing is sent.

`publish_digest` saves it to `data/digests/digest-<timestamp>.md` and, if `SLACK_WEBHOOK_URL` is set, posts it to
Slack. In TrueForge it waits for human approval (see [TrueForge agents](./trueforge.md#approvals)).
