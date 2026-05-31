# WORKLOG — Universal Video Downloader

> **Rule:** Update this file after every code, config, or documentation change.  
> **Language:** English only. Never log cookie values, tokens, or personal paths.  
> Append a new dated section at the top (newest first).

---

## 2026-05-31 — v2.0.3: About window, Spiders Tech SRL branding

### Summary
Added About dialog with company info and website link. Updated LICENSE and README copyright to Spiders Tech SRL.

### Files changed
- `Downloader.py`, `LICENSE`, `README.md`, `build_exe.bat`, `AGENTS.md`, `CLAUDE.md`

---

### Summary
Committed and pushed source to `origin/main` at https://github.com/spider2077/Universal-Video-Downloader. No cookies, settings.ini, or dist/ included.

### Commit
- `d96020a` — Release v2.0.2: Facebook fixes, security docs, GitHub-ready source

### Security verified before push
- Staged files: source, docs, `cookies/template.txt` only
- Ignored: all `*_cookies.txt`, `settings.ini`, `dist/`
- Removed absolute local paths from script headers

### Follow-up
- [ ] Create GitHub Release `v2.0.2` and attach `dist/Universal_Video_Downloader.exe` manually
- [ ] User: run `git config --global --add safe.directory` for this folder if git warns about ownership

---

### Summary
Updated all agent and project docs for public GitHub safety. Added SECURITY.md, strengthened `.gitignore`, removed personal paths from code, translated UI error strings to English.

### Changes
- `SECURITY.md` (new) — never commit cookies, settings, dist; rotation guidance
- `AGENTS.md`, `CLAUDE.md` — security rules, language policy, GitHub update section
- `README.md` — publishing to public repo, security checklist
- `.gitignore` — broader secret patterns
- `Downloader.py` — English errors; removed hardcoded user path from cookie dialog
- `WORKLOG.md` — cleaned up structure; all entries in English

### Files changed
- `SECURITY.md`, `AGENTS.md`, `CLAUDE.md`, `README.md`, `WORKLOG.md`, `.gitignore`, `Downloader.py`

---

## 2026-05-31 — v2.0.2 exe build (PyInstaller)

### Summary
Built `Universal_Video_Downloader.exe` with yt-dlp 2026, curl-cffi, impersonate fix, Unicode fix. Updated `build_exe.bat`, added `generate_icons.py`.

### Output (local only — not for git)
- `dist/Universal_Video_Downloader.exe`
- `dist/settings.ini.example`, `dist/cookies/template.txt`

### Files changed
- `build_exe.bat`, `generate_icons.py`, `icons/` (generated)

---

## 2026-05-31 — v2.0.2: Unicode/charmap fix (Romanian titles)

### Summary
Fixed `'charmap' codec can't encode character'` when Facebook titles contained diacritics. Added UTF-8 console, `safe_print`, ASCII-safe FFmpeg metadata.

### Files changed
- `Downloader.py`

---

## 2026-05-31 — v2.0.1: Fix impersonate crash

### Summary
Facebook downloads showed only "Error" because `impersonate: 'chrome'` string is invalid in yt-dlp 2026 API. Fixed with `ImpersonateTarget.from_str('chrome')`.

### Files changed
- `Downloader.py`

---

## 2026-05-31 — v2.0.0: Facebook fix, GitHub prep, agent docs

### Summary
Major revision: Facebook downloads via curl-cffi + impersonation, cookie path fixes, GitHub hygiene, agent documentation.

### Files changed
- `Downloader.py`, `requirements.txt`, `*.bat`, `README.md`, `.gitignore`, `LICENSE`, `settings.ini.example`, `cookies/template.txt`, `AGENTS.md`, `CLAUDE.md`

---

## Entry template

```markdown
## YYYY-MM-DD — Short title

### Summary
One paragraph (English only; no secrets).

### Changes
- Bullet list

### Files changed
- `file.py`
```
