# Contributing

`main` is protected and always demo-ready. Every change goes through a small pull request that Qodo reviews.

## Workflow

1. Start from a fresh main: `git switch main && git pull`
2. Branch per change: `feat/…`, `fix/…`, `docs/…`, `chore/…`. Keep it to one purpose, ideally under ~300 changed lines.
3. Commit, push, open a PR (`gh pr create --fill`). The template asks what, why and how it was tested.
4. Qodo describes and reviews the PR automatically, and again on each push. Apply the suggestions that hold up as new
   commits on the branch; reply with a reason to the ones you decline. All conversations must be resolved to merge.
5. Squash-merge. The branch is deleted automatically.

If main moved while you worked: `git pull --rebase origin main`, then `git push --force-with-lease` (your branch only;
main can't be force-pushed).

## Setup

```bash
uv sync                                   # Python env from uv.lock
docker compose up -d                      # FalkorDB
cp .env.example .env                      # keys: see website/docs/reference/configuration.md
uv run crew serve
uv run python -m unittest discover tests  # before every PR
```
