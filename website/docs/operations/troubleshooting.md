---
title: Troubleshooting
sidebar_position: 2
description: Problems we've actually hit, and the fixes.
---

**`docker: 'compose' is not a docker command`** (macOS with Colima). Usually leftover Docker Desktop shortcuts in
`~/.docker/cli-plugins` pointing into a deleted `Docker.app`. Remove those, `brew install docker-compose`, and add
`"cliPluginsExtraDirs": ["/opt/homebrew/lib/docker/cli-plugins"]` to `~/.docker/config.json`. In the meantime the
standalone `docker-compose up -d` works.

**macOS says `com.docker.vmnetd` "contains malware".** A leftover helper from a Docker Desktop that was deleted by
dragging it to the Trash; its signing certificate was revoked. If you use Colima, remove it:
`sudo launchctl bootout system/com.docker.vmnetd` (and `com.docker.socket`), then delete both from
`/Library/LaunchDaemons/` (`.plist`) and `/Library/PrivilegedHelperTools/`.

**The team build finds nothing to plan.** No agenda has been published, so there are no sessions. Publish one on
`/organizer` (or **Use sample agenda**) and build again.

**"No bridges yet".** Nothing in the team's code or goals matches the agenda by name. Add goals, run Crew Scout, or
add an alias to `ALIASES` in `crew/ingest.py` (e.g. `"gh-actions": "github-actions"`).

**"GitHub rate limit reached".** Set `GITHUB_TOKEN`. Responses are cached for `WEB_CACHE_SECONDS`, so repeat builds
of the same repos don't count.

**"GitHub refused access (401)" or "(403)".** The token is wrong or lacks Contents/Metadata read access.

**Phones can't open the sticker URL.** Crew is listening on `127.0.0.1`. Start it with `CREW_HOST=0.0.0.0` and use
the machine's network address on `/stickers`.

**Team memory finds nothing.** The full-text indexes are created by `crew init` (and on server start). Run
`crew init` once against the graph.

**TrueForge: `Outbound URL blocked for host "127.0.0.1"`.** Start TrueForge with
`OUTBOUND_URL_ALLOWED_HOSTS='["127.0.0.1"]'` so it may call Crew's local MCP endpoint.

**TrueForge doesn't ask before publishing the digest.** Re-run `crew forge-setup`; it sets approval on
`publish_digest`. Agents created by hand in the UI need the shield turned on for that tool.

**A new server process answers with 404 for new pages.** The old process was still holding the port. Stop it
(`pkill -f "crew serve"`), wait until it has exited, then start again.
