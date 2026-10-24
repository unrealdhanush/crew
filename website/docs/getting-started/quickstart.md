---
title: Quickstart
sidebar_position: 2
description: From an empty graph to a coverage plan and a tap check-in, using the sample agenda.
---

This walks through the whole flow with the sample agenda, so it works without OpenAI or Bright Data keys. It takes
about five minutes once [Crew is installed](./installation.md) and `crew serve` is running.

<Steps>
<Step title="Publish the agenda">

Open `http://127.0.0.1:8765/organizer`, enter an event name and click **Use sample agenda**. The progress feed
lists four sessions as they're written, and they appear in the graph on the right.

</Step>
<Step title="Add your team">

Open `http://127.0.0.1:8765/team`. For each teammate, type their GitHub username and click **Find repos** (the two
most recently updated are ticked), then add goals such as `agents, evals, github-actions`. Click **Build our graph**.

Crew reads each repo's dependencies while the graph grows beside the form. At the end you see the **bridges**, where
your code meets the agenda, and each person's schedule with a reason for every session.

:::tip
Untick **Crew Scout reads READMEs and goals** if OpenAI and TrueForge aren't set up yet. Scout only adds topics.
:::

</Step>
<Step title="Ask why">

```bash
crew why <handle> "MCP"
```

```text
dhanush -OWNS-> openai/openai-agents-python -DEPENDS_ON-> mcp <-MENTIONS- SAMPLE: Shipping MCP servers to production
```

The graph view at `/viz` highlights the same path.

</Step>
<Step title="Tap in at a session">

Open `http://127.0.0.1:8765/sim`, pick whose phone it is, and click a door (or press 1–9). The phone checks in and
shows why the session matters, and the graph lights up the check-in.

</Step>
</Steps>

## Next steps

- Use a real agenda: [Publish an event](../guides/organizer.md)
- Private or enterprise repos: [Private repos](../guides/private-repos.md)
- Agents: [TrueForge agents](../guides/trueforge.md)
