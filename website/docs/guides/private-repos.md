---
title: Private repos and enterprise Git
sidebar_position: 3
description: Use Crew with private GitHub repos, GitHub Enterprise Server, GitLab or air-gapped code.
---

Crew only needs the **names of your dependencies**. It never reads or stores source code. Pick the option that
matches where your code lives:

| Where the code is | Use |
|---|---|
| Private repos on github.com | A read-only token on the team page |
| GitHub Enterprise Server | `GITHUB_API_URL`, plus a token if repos are private |
| GitLab, Bitbucket, air-gapped, or "nothing leaves our network" | `crew scan` or a file upload |

## Private repos on GitHub

1. Create a fine-grained token with **Contents: read** and **Metadata: read** on the repos (or the org).
2. On `/team`, open **Private repos or GitHub Enterprise** and enter the **GitHub org** and the token.
3. **Find repos** now also lists the org's repos, private ones marked. Build as usual.

The token stays in the page. It's sent with requests and passed through the build, never written to disk, and
nothing fetched with it is cached, so private data can't leak into a later request made without it.

:::warning Not yet verified
Tested with an invalid token (Crew reports "GitHub refused access (401)"), not yet with a real private repo.
:::

## GitHub Enterprise Server

Set the API address before starting Crew:

```bash
GITHUB_API_URL=https://git.example.com/api/v3 crew serve
```

Crew then reads files through the contents API (Enterprise Server has no `raw.githubusercontent.com`). The team
page shows which server it's using. Not yet tested against a real Enterprise Server.

## `crew scan`: from your own machine

Run it in the repo, or in CI. It walks the folder (skipping `node_modules`, `.venv`, `.git`, `vendor`, `dist`,
`build` and hidden folders), opens only dependency files, and sends only package names.

```bash
pipx install <crew repo>          # or: uv sync in a checkout
export CREW_SERVER=http://<crew-host>:8765
crew scan <handle> ./billing-api --dry-run
```

`--dry-run` prints exactly what would be sent and sends nothing:

```json
{
  "read": ["pyproject.toml", "requirements.txt"],
  "would_send": {
    "handle": "dhanush",
    "name": "billing-api",
    "deps": ["falkordb", "fastmcp", "httpx", "openai"],
    "dev_deps": [],
    "via": "crew scan"
  }
}
```

Drop `--dry-run` to send it. The teammate must already be on the team and built. The project appears as
`local:<handle>/<name>` and the plan is recalculated.

## Upload a dependency file

On a teammate's card, **Upload a dependency file** accepts `requirements*.txt`, `package.json`, `pyproject.toml` and
`go.mod`. The browser sends that one file; Crew extracts the package names and doesn't keep the file.
