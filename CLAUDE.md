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

**Version:** 2.1.0  
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
| Output format | `COMPAT_VIDEO_FORMAT` prefers H.264/AAC; `finalize_media()` re-encodes anything else (WhatsApp only plays H.264 yuv420p + AAC MP4). Same rule in `android/.../Platforms.kt` + `DownloadEngine.reencode()` — change both |
| GUI | CustomTkinter `App` class; dialogs are `CTkToplevel`; workers never touch widgets (`ThreadSafeWidget`, `ProgressAdapter`) |
| Facebook | cookies + `curl-cffi` + `ImpersonateTarget.from_str('chrome')` |
| Threads | `download_threads_video()` — Selenium, because yt-dlp has no Threads extractor |
| Platform detection | `detect_platform()` matches the hostname against `PLATFORM_DOMAINS` (no substring tests) |
| UI from threads | `ui_call()` / `ThreadSafeWidget` — workers never touch Tk widgets directly |
| YouTube JS | `get_js_runtimes()` enables installed node in addition to deno (bun is deprecated upstream) |
| Unicode | `safe_print()`, `transliterate_text()` |

---

## Android app (`android/`)

Kotlin + Compose app on the `youtubedl-android` library; sideload only (not Play Store). See [android/README.md](android/README.md).

- `Platforms.kt` is a port of `PLATFORM_DOMAINS`, `PLATFORM_COOKIE_FILES`, `normalize_url()` and the format strings in `Downloader.py`. **Any change to those must be made in both files**, and in `PlatformsTest.kt`.
- Build: `android\build_apk.bat` (unit tests + debug APK → `dist/`). JDK comes from Android Studio.
- Never commit `android/local.properties`, keystores, or APKs (`android/.gitignore`).
- Device testing over adb: use only the device the user names; always pass `adb -s <serial>`.

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
