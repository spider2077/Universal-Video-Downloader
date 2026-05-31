# CLAUDE.md — Universal Video Downloader

> Companion guide for Claude and other AI assistants.  
> **Mirror of [AGENTS.md](AGENTS.md).** Update [WORKLOG.md](WORKLOG.md) after every change.

---

## Language policy (mandatory)

Write **all documentation in English**, even if the user writes in Romanian or another language. This includes WORKLOG entries, README updates, error messages, and agent instructions.

---

## Security & privacy (mandatory)

Public repo — read [SECURITY.md](SECURITY.md).

**Never commit or log:** cookie files, `settings.ini`, `dist/`, personal paths, session tokens.

**Before suggesting `git push`:** remind user to run `git status` and confirm no secrets.

**If old GitHub repo had cookies:** user must rotate Facebook/social sessions.

---

## What this project is

Windows desktop app — paste a URL, download MP4/MP3 via **yt-dlp**. Main code: **`Downloader.py`**.

**Version:** 2.0.3  
**Publisher:** Spiders Tech SRL — [s-tech.pm](https://www.s-tech.pm)

---

## Updating public GitHub (older version already online)

- Pushing this repo **updates source code** on the default branch.
- Old manually uploaded `.exe` on Releases **stays** until a new Release is created.
- **Do not push** `dist/`, `cookies/*.txt`, or `settings.ini`.
- Attach new exe via **GitHub Releases** (`v2.0.2`), not git commits.
- If secrets were in old commits, history cleanup + session rotation required.

---

## How to run

```bat
install_dependencies.bat
run_downloader.bat
update_dependencies.bat
build_exe.bat
```

---

## Code map

| Step | Function |
|------|----------|
| Startup | `create_gui()` → `load_settings()` → `announce_cookies()` |
| Download | `download_media()` via background thread |
| Facebook | cookies + `curl-cffi` + `ImpersonateTarget.from_str('chrome')` |
| Unicode | `safe_print()`, `transliterate_text()` |

---

## Instructions for AI assistants

1. Read `Downloader.py` and [WORKLOG.md](WORKLOG.md) first.
2. Smallest correct change; **English only** in docs.
3. Append **WORKLOG.md** (no secrets).
4. Update **AGENTS.md** / **CLAUDE.md** if rules or architecture change.
5. Bump `APP_VERSION` for releases.
6. No git commits unless user asks.

---

## Files you may edit

| File | When |
|------|------|
| `Downloader.py` | Logic, GUI |
| `requirements.txt`, `*.bat` | Deps, scripts |
| `README.md`, `AGENTS.md`, `CLAUDE.md`, `WORKLOG.md`, `SECURITY.md` | Docs |

**Do not commit:** `settings.ini`, `cookies/*_cookies.txt`, `dist/`, `Output/`.

---

## Work log

All changes: **[WORKLOG.md](WORKLOG.md)**.
