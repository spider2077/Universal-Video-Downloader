# Security & Privacy

This repository is **public**. Follow these rules to protect yourself and anyone who uses the app.

## Never commit or upload

| Item | Why |
|------|-----|
| `cookies/*.txt` (except `template.txt`) | Contains live login sessions (`c_user`, `xs`, etc.) |
| `settings.ini` | May contain personal folder paths |
| `dist/` folder | May contain exe + local cookies copied during build |
| `Output/` | Downloaded media |
| `.env` / API keys | Credentials |

## Before every `git push`

1. Run `git status` — confirm no cookie or settings files are staged.
2. Run `git diff` — scan for session tokens, emails, or personal paths.
3. Do **not** paste real cookie contents into issues, PRs, docs, or work logs.

## If secrets were ever pushed to GitHub

1. **Rotate sessions immediately** — log out and back in on affected sites; re-export cookies locally only.
2. Remove files from git history ([BFG Repo-Cleaner](https://rtyley.github.io/bfg-repo-cleaner/) or `git filter-repo`).
3. Assume compromised tokens are public forever until rotated.

## Releases

- Publish **source code** on the default branch.
- Attach `.exe` via **GitHub Releases** only — do not commit `dist/*.exe` to the repo.
- Release packages must not include cookie files or `settings.ini`.

## For AI agents

See [AGENTS.md](AGENTS.md) — Security & language rules are mandatory for all changes.
