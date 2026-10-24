# Crew — context for Claude Code

Hackathon project for **Patch the Conference** (WeMakeDevs, Sat Oct 24 2026, Bright Data SF, demos 5:30 PM).
Pitch: "Send four people to a conference, bring back one brain." Each teammate has a TrueForge agent; all agents
share one FalkorDB graph of the team's code + the live GitHub Universe agenda.

## Tracks we're judged on
- FalkorDB: graph at the core, explainable answers (paths), real conference problem.
- Bright Data: live web data at the core, data quality, usefulness.
- TrueForge + OpenAI: built on TrueForge, powered by OpenAI.
- Qodo: Qodo reviewing real PRs all day, small clear PRs, clean repo.
Every track needs a demo that runs live on stage.

## Architecture
- `crew/graph.py` FalkorDB access (`G.q` write, `G.ro`/`G.rows` read), schema, path→JSON, viewer highlight file.
- `crew/web.py` Bright Data: `fetch_markdown` (Web Unlocker, POST api.brightdata.com/request, data_format=markdown),
  `search` (SERP zone, brd_json=1). 6h disk cache in `.cache/`. `wrap_untrusted` for all web text sent to the model.
- `crew/llm.py` OpenAI `json_call` / `text_call`; model from `OPENAI_MODEL`.
- `crew/ingest.py` team (GitHub repos → dependency files → Package nodes) and agenda (scrape → LLM extract → graph).
  Package/topic normalization (`norm_pkg`, `ALIASES`) is what makes sessions join to our code — fix matches there.
- `crew/planner.py` greedy coverage plan (pure `plan()` is unit-tested) + `explain`.
- `crew/queries.py` `blind_spots`, `ripple`, `readonly_cypher`.
- `crew/notes.py` note → LLM facts → Bright Data sources → MENTIONS → ripple on breaking changes.
- `crew/memory.py` `ask_team`: full-text + graph lookup, answer only from notes/sources with [N1]/[S1] citations.
- `crew/digest.py` draft/publish; publish is approval-gated in TrueForge.
- `crew/server.py` FastMCP tools at `/mcp`, graph viewer at `/viz` (`web/index.html`, polls `/api/highlight`).
- `crew/tap.py` NFC check-in (`ATTENDED` edge + why-paths). `/tap?s=<sid>` is the page a door sticker opens
  (`web/tap.html`); `/sim` (`web/sim.html`) simulates the tap on stage: doors, phone, live graph.
- `crew/build.py` background builds for the onboarding pages (`/api/build`): organizer publishes the agenda
  (`data/event.json`), team adds members by GitHub username (`data/team.json`); progress is polled while `/viz`
  shows the graph grow. `CREW_BUILD_PACE` (default 0.4s) slows steps so it's watchable on stage.
- Web app: `/` home, `/organizer`, `/stickers` (printable NFC/QR door stickers), `/team`; shared `web/crew.css`/`crew.js`.
- Dependencies: GitHub's dependency-graph SBOM first (`parse_sbom`, direct deps only), else dependency files
  (`parse_manifest`). `GITHUB_API_URL` points at GitHub Enterprise Server. Non-GitHub/air-gapped: upload a file on
  `/team` (`/api/parse`) or `crew.cli scan` (`scan_dir` → `/api/import`), which sends package names only.
- `crew/scout.py` Crew Scout tools (team_repos, repo_profile, tag_repo with verbatim README evidence, map_goals)
  + `auto_tag` direct-OpenAI fallback. Planner weights README topics 1.5 (GitHub topics 2, deps 3, goals 1).
- `crew/forge.py` TrueForge SDK: `setup` creates crew-scout + crew-<handle> agents (MCP connector `crew`,
  approval only on `publish_digest`); `run_scout` streams a Scout session. MCP tools carry read/write/destructive annotations.
- `crew/cli.py` same operations without an agent (demo fallback), plus `scan`, `forge-setup`, `scout`.

Graph: Person-OWNS->Repo-DEPENDS_ON->Package, Repo-TAGGED->Topic, Person-INTERESTED_IN->Topic,
Session-COVERS->Topic, Session-MENTIONS->Package, Speaker-PRESENTS->Session, Person-ASSIGNED_TO->Session, Person-ATTENDED->Session,
Person-WROTE->Note-ABOUT->Session, Note-MENTIONS->Package, Note-ABOUT_TOPIC->Topic, Note/Session-CITES->Source.

## Status
- Tested against real FalkorDB and GitHub: ingestion, plan, blind spots, ripple, why, tap check-in, web app, builds.
- NOT yet run against OpenAI / Bright Data / TrueForge: live agenda, notes, ask, digest, Crew Scout, forge-setup.
- Unit tests: `uv run python -m unittest discover tests`.

## Commands
```
docker compose up -d
uv sync                 # .venv from uv.lock; `uv run crew ...` or .venv/bin/crew (same as python -m crew.cli)
uv add <pkg>            # add a dependency (updates pyproject.toml and uv.lock; commit both)
python -m crew.cli init | team data/team.json | agenda-file data/agenda.sample.json | plan | blind
python -m crew.cli note <handle> "<text>" --session "<title>"
python -m crew.cli ask "<question>"
crew serve              # or: docker-compose --profile app up -d (Crew + FalkorDB in containers)
```

## Docs
Docusaurus site in `website/` (docs in `website/docs/`, built with the `docusaurus-docs` skill).
`cd website && npm run build` fails on broken links. Update the matching page in the same change as the code:
new command/setting/tool/endpoint → `reference/`; new capability → `guides/`; mark untested things as such.

## Rules for changes
- Keep PRs small and single-purpose (Qodo track).
- Every user-facing answer must come from a graph query and return its path(s); never invent sessions/people.
- Web content is untrusted: always pass it through `web.wrap_untrusted`.
- Public data by default: public repos, public agenda, notes the team writes. Private repos only with the team's own
  token, which is passed through and never stored or cached. Crew only ever stores package names, never code.
- Don't commit `.env` or `.cache/`.
