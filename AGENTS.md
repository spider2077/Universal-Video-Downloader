# AGENTS.md — Universal Video Downloader

> **Purpose:** Guide for AI coding agents (Cursor, Copilot, etc.) working on this repository.  
> **Always update:** [WORKLOG.md](WORKLOG.md) and relevant sections here when you change code, docs, or behavior.

---

## Language policy (mandatory)

- **All repository documentation must be written in English** — even when the user writes in another language.
- Applies to: `README.md`, `AGENTS.md`, `CLAUDE.md`, `WORKLOG.md`, `SECURITY.md`, user-facing error strings, and commit/PR descriptions.
- Code comments: English preferred.

---

## Security & privacy (mandatory)

This is a **public** GitHub repository. See [SECURITY.md](SECURITY.md).

**Never commit, upload, or document:**

- Cookie files (`cookies/*_cookies.txt`) — live session tokens
- `settings.ini` — personal output paths
- `dist/`, `Output/`, downloaded media, `.exe` in the repo
- Real cookie values, user IDs, emails, or machine-specific paths in docs or work logs

**Before any git push:** run `git status` and `git diff`; confirm no secrets are staged.

**If secrets were ever pushed:** tell the user to rotate all affected sessions immediately.

**Agents must not:** copy local cookies into tracked files, paste user paths into docs, or include personal data in WORKLOG entries.

---

## Project summary

| Field | Value |
|-------|-------|
| Name | Universal Video Downloader |
| Version | 2.0.2 (see `APP_VERSION` in `Downloader.py`) |
| Language | Python 3.12+ |
| GUI | Tkinter / ttk |
| Download engine | [yt-dlp](https://github.com/yt-dlp/yt-dlp) ≥ 2026.3.17 with **curl-cffi** |
| Post-processing | FFmpeg (metadata, audio MP3, merge) |
| Platform | Windows (primary) |
| License | MIT |

Single-file app: **`Downloader.py`**. No tests, no CI yet.

---

## Updating the public GitHub repository

An older version may already exist on GitHub (uploaded manually). Pushing this project **updates source files** on the default branch; it does **not** automatically replace old Release binaries.

| Action | Effect |
|--------|--------|
| Push source (`Downloader.py`, docs, etc.) | Replaces old source on `main` — users clone latest code |
| Old `.exe` on Releases | Stays until you upload a new Release (e.g. tag `v2.0.2`) |
| Old repo contained `cookies/` or `dist/` | **Critical** — secrets may be in git history; rotate sessions + clean history |
| This repo's `.gitignore` | Prevents future accidental commits of secrets |

**Recommended release flow:**

1. Verify `git status` — no cookies, settings, or `dist/`.
2. Commit and push source only.
3. Create GitHub Release `v2.0.2` with `Universal_Video_Downloader.exe` attached (built locally, not committed).

---

## Architecture

```
User (Tkinter GUI)
       │
       ▼
handle_download / handle_audio_download  (threading.Thread)
       │
       ▼
download_media(url, output_dir, progress_bar, status_label, is_audio)
       │
       ├── detect_platform(url)
       ├── normalize_url(url, platform)
       ├── get_cookie_file(platform)  → cookies/*.txt (local only)
       ├── build_info_ydl_opts()      → yt-dlp extract_info
       └── build_ydl_opts()           → yt-dlp download
                │
                ├── add_metadata_to_file()  (ffmpeg)
                └── rename → Output/
```

### Key functions (`Downloader.py`)

| Function | Role |
|----------|------|
| `get_app_dir()` | Script dir or exe dir (PyInstaller) |
| `get_cookies_dir()` | `{app_dir}/cookies/` |
| `get_cookie_file(platform)` | Cookie path; aliases for x.com, soundcloud |
| `apply_impersonate(opts)` | `ImpersonateTarget.from_str('chrome')` for FB/IG |
| `transliterate_text()` / `safe_print()` | Windows Unicode-safe logging |
| `build_ydl_opts()` / `build_info_ydl_opts()` | Central yt-dlp config |
| `download_media(...)` | Main download pipeline |
| `sanitize_filename(...)` | Windows-safe ASCII filenames |

---

## Supported platforms & cookies

Cookie files live in **`cookies/`** next to the app or exe. **Never commit real cookie files.**

| Platform | Cookie filenames |
|----------|------------------|
| facebook | `www.facebook.com_cookies.txt` |
| youtube | `www.youtube.com_cookies.txt` |
| instagram | `www.instagram.com_cookies.txt` |
| twitter | `www.twitter.com_cookies.txt`, `x.com_cookies.txt` |
| tiktok | `www.tiktok.com_cookies.txt` |
| reddit | `www.reddit.com_cookies.txt` |
| soundcloud | `www.soundcloud.com_cookies.txt`, `soundcloud.com_cookies.txt` |

---

## Facebook requirements (critical)

1. Fresh Netscape cookies from facebook.com  
2. `yt-dlp[default,curl-cffi]` installed  
3. `ImpersonateTarget.from_str('chrome')` in yt-dlp opts  

---

## Development rules for agents

1. **Minimal diffs** — match existing style.
2. **English only** — all docs and user-facing strings.
3. **Update WORKLOG.md** — every session; no secrets in entries.
4. **Update AGENTS.md / CLAUDE.md** — when architecture or rules change.
5. **Update README.md** — user-visible changes.
6. **Never commit secrets** — see SECURITY.md.
7. **Version bump** — increment `APP_VERSION` for releases.
8. **No git commits** unless the user explicitly asks.

---

## GitHub readiness checklist

- [x] `.gitignore` — cookies, settings, dist, binaries
- [x] `LICENSE` (MIT), `settings.ini.example`, `cookies/template.txt`
- [x] `README.md`, `AGENTS.md`, `CLAUDE.md`, `WORKLOG.md`, `SECURITY.md`
- [x] `icons/` via `generate_icons.py`
- [ ] User: verify old GitHub history has no leaked cookies
- [ ] User: push source + optional Release `v2.0.2`

---

## Work log

See **[WORKLOG.md](WORKLOG.md)**. Append a dated entry after every task.
