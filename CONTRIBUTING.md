# Contributing

`main` is protected and always demo-ready. Every change goes through a small pull request that Qodo reviews.

## Workflow

1. Start from a fresh main: `git switch main && git pull`
2. Branch per change: `feat/…`, `fix/…`, `docs/…`, `chore/…`. Keep it to one purpose, ideally under ~300 changed lines.
3. Commit, push, open a PR: `gh pr create --fill`, or the link `git push` prints. The template asks what, why and
   how it was tested.
4. Qodo describes and reviews the PR automatically, and again on each push. Apply the suggestions that hold up as new
   commits on the branch; reply with a reason to the ones you decline. All conversations must be resolved to merge.
5. Squash-merge. The branch is deleted automatically.

If main moved while you worked: `git pull --rebase origin main`, then `git push --force-with-lease` (your branch only;
main can't be force-pushed).

## Setup

Needs [uv](https://docs.astral.sh/uv/), Docker with Compose v2.24+ (the compose file uses `env_file` with
`required: false`), Node.js 20+ for the docs, and optionally the [GitHub CLI](https://cli.github.com/) (`gh`).

```bash
uv sync                                   # Python env from uv.lock
docker compose up -d                      # FalkorDB (or the standalone v2 binary: docker-compose up -d)
cp .env.example .env                      # keys: see website/docs/reference/configuration.md
npm --prefix website install              # docs dependencies, once
uv run crew serve
```

Before every PR:

```bash
uv run python -m unittest discover tests
npm --prefix website run build            # fails on broken links
```
