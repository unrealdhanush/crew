# Crew

**Send four people to a conference, bring back one brain.**

Each teammate gets their own agent. All the agents share one FalkorDB graph built from the team's real code
(repos → dependencies → topics) and the live conference agenda (sessions → speakers → packages). Crew splits the
conference so every session that touches your code has someone in the room, turns two-line notes into cited
knowledge, and tells the people who stayed home what changes for them.

| Sponsor | Role in Crew |
|---|---|
| FalkorDB | The shared team graph. Every answer is a multi-hop path you can see. |
| Bright Data | Scrapes the live agenda; fetches the docs and release notes every note mentions (Web Unlocker + SERP). |
| TrueForge + OpenAI | One agent per teammate, all on the Crew MCP server; digest publishing sits behind an approval gate. |
| Qodo | Reviews every PR. |

## The queries only a graph answers

- **Blind spots** — sessions about something our code depends on, with nobody assigned:
  `Person -OWNS-> Repo -DEPENDS_ON-> Package <-MENTIONS- Session` with no `ASSIGNED_TO`. An empty result is proof.
- **Ripple** — "breaking change in X": `Package <-DEPENDS_ON- Repo <-OWNS- Person`, plus the note and source that said so.
- **Why** — the path from a teammate's code or goals to a session.
- **Team memory** — "what did we learn about X?", answered only from notes and their cited sources.

## Setup (about 10 minutes)

```bash
docker compose up -d                        # FalkorDB on :6379, FalkorDB Browser on :3000
uv sync                                     # .venv with Python 3.11, deps from uv.lock, the `crew` command
cp .env.example .env                        # add OpenAI + Bright Data keys
cp data/team.example.json data/team.json    # put your real handles and repos in
```

Bright Data: in the control panel create a **Web Unlocker** zone and a **SERP API** zone and put their names in `.env`.

Load data and check it works without any agent:

```bash
python -m crew.cli init
python -m crew.cli team data/team.json
python -m crew.cli agenda \
  https://github.blog/news-insights/company-news/your-guide-to-github-universe-2026-is-here-the-schedule-just-launched/ \
  https://github.blog/news-insights/company-news/10-technical-talks-im-excited-about-at-github-universe-2026/
                                              # live via Bright Data; offline: agenda-file data/agenda.sample.json
python -m crew.cli plan
python -m crew.cli blind
python -m crew.cli note dhanush "Speaker said fastmcp 3 drops SSE, migrate to http" --session "MCP"
python -m crew.cli ask "what did we learn about MCP?"
python -m unittest discover tests            # pure-logic tests, no services needed
```

## Run it

```bash
crew serve                  # app: http://127.0.0.1:8765/   MCP: /mcp   graph view: /viz
                            # tap demo: /sim

The app has two sides. **Organizers** publish the agenda at `/organizer` (scraped live with Bright Data) and print
door stickers at `/stickers` (NFC + QR, each opens `/tap?s=<session>`). **Teams** add teammates by GitHub username at
`/team`, pick repos, and watch the graph build next to the form, then get the coverage plan.
npx @truefoundry/trueforge@latest
```

TrueForge (http://localhost:8790) is the agent harness; the agents run on OpenAI models. One-time, in its UI:
1. **Settings → Models:** add OpenAI with your hackathon credits.
2. **Settings → Connectors → Add MCP Server:** name `crew`, URL `http://127.0.0.1:8765/mcp`, no auth. Optionally
   also Bright Data's remote MCP (`https://mcp.brightdata.com/mcp?token=...`) so agents can browse ad hoc.
3. Build the team on `/team`, then run `crew forge-setup`. It creates `crew-scout` and a `crew-<handle>` agent per
   teammate (prompts in `prompts/`), on `openai/$OPENAI_MODEL`, with approval required on `publish_digest` only.

**Crew Scout** reads each repo's README and each person's goals and maps them onto the agenda's topics
(`tag_repo` must quote the README verbatim, so every inferred reason shows its evidence). The `/team` build hands
off to Scout in TrueForge and streams its tool calls; if TrueForge isn't running it calls OpenAI directly.
`crew scout` runs it on its own (`--direct` skips TrueForge).

Keep the graph view open on the projector: it lights up the path behind whatever any agent just answered.

## Demo (3 minutes)

1. "Universe is in four days, four of us are going, and the team at home usually gets nothing."
2. Scrape the agenda live → `plan_coverage` → each person's schedule with reasons. Blind spot flagged.
3. "Why am I in this one?" → the path lights up.
4. A teammate types one line about a breaking change → Bright Data pulls the release notes → ripple lights up
   the affected repos and owners.
5. "What did we learn this morning?" → answer with citations from the real sponsor workshops.
6. Draft digest → approve in TrueForge → published. Flash a bug Qodo caught.

## Docs

Full documentation lives in `website/` (Docusaurus):

```bash
cd website && npm install && npm run start    # live preview at http://localhost:3000
```

Port 3000 clashes with the FalkorDB Browser; use `npm run start -- --port 3001` while FalkorDB is up.

## Layout

```
crew/graph.py     FalkorDB connection, schema, path → JSON, viewer highlight
crew/web.py       Bright Data Web Unlocker + SERP, cache, prompt-injection guard
crew/llm.py       OpenAI JSON extraction / grounded answers
crew/ingest.py    team (GitHub repos + dependency files) and agenda ingestion
crew/planner.py   coverage plan + explain
crew/queries.py   blind spots, ripple, read-only Cypher
crew/notes.py     notes → live sources → packages → ripple
crew/tap.py       NFC check-in: ATTENDED edge + why-paths
crew/build.py     background builds behind /organizer and /team, with progress
crew/memory.py    ask_team
crew/digest.py    draft / publish (approval-gated)
crew/server.py    FastMCP server + /viz viewer + /tap, /sim
crew/cli.py       CLI fallback
web/home.html     landing page
web/organizer.html, web/stickers.html, web/team.html   onboarding (shared crew.css / crew.js)
web/index.html    graph viewer
web/tap.html      phone page an NFC door sticker opens
web/sim.html      on-stage tap simulator (doors, phone, live graph)
prompts/agent.md  TrueForge agent prompt
scripts/eval_ask.py  memory eval (data/eval.json)
```

## Self-hosting and the CLI

- **Server, self-hosted:** `docker-compose --profile app up -d` runs Crew and FalkorDB together (app on :8765, or set
  `CREW_HTTP_PORT`). Keys come from `.env` if present. `data/` is mounted so the team and event survive rebuilds.
- **CLI, on each teammate's machine:** `pipx install <path or git URL>` gives `crew`. Set `CREW_SERVER=http://<host>:8765`
  (or put it in `~/.crew/.env`), then `crew scan <handle> ./repo` and `crew open`.

## Private repos and GitHub Enterprise

Crew only needs dependency names, never code. It reads GitHub's dependency graph (SBOM, direct dependencies) and falls
back to `requirements.txt`, `pyproject.toml`, `package.json` and `go.mod`.

- **Private repos on GitHub:** on `/team`, open *Private repos or GitHub Enterprise* and add the org plus a fine-grained
  read-only token (Contents + Metadata). The token is sent with requests only, never saved, and nothing fetched with it is cached.
- **GitHub Enterprise Server:** set `GITHUB_API_URL=https://<host>/api/v3`.
- **Anything else (GitLab, air-gapped):** upload a dependency file on a teammate's card, or run on your machine
  `crew scan <handle> ./repo --server http://<crew-host>:8765` (add `--dry-run` to see exactly what
  would be sent: package names only).

## Notes

- Scraped pages are cached for 6 hours in `.cache/` so a bad venue network doesn't kill the demo. Use `--fresh` to force live.
- Web content is treated as untrusted: injection phrases are stripped and it is wrapped before reaching the model.
- Public data by default: public repos, the public agenda, and notes the team writes. Private repos only with the
  team's own token (see above). Only package names are stored, never code.
