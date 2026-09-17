# WORKLOG — Universal Video Downloader

> **Rule:** Update this file after every code, config, or documentation change.  
> **Language:** English only. Never log cookie values, tokens, or personal paths.  
> Append a new dated section at the top (newest first).

---

## 2026-09-17 — v2.0.5: Review fixes (TLS, platform detection, Threads, JS runtime, UI threading)

### Summary
Full review of v2.0.4 found no regressions, but five pre-existing problems, all fixed here.
1. **TLS verification was disabled** (`no_check_certificate: True`) for every request, including ones carrying login cookies. Removed from both yt-dlp option sets.
2. **Platform detection used substring tests**, so `'x.com' in url` classified `netflix.com` and `dropbox.com` as Twitter (and the clipboard watcher auto-pasted them). `detect_platform()` now parses the hostname and matches it, or a subdomain of it, against `PLATFORM_DOMAINS`. Added `threads.com`, `redd.it`, `tiktokv.com`, `youtube-nocookie.com`.
3. **Threads was broken since v2.0.2**: the refactor dropped the call to `download_threads_video()`, and yt-dlp has no Threads extractor, so every Threads link failed. Routing restored in `download_media()` (video only; audio reports "not supported"). The scraper itself was also stale: Threads no longer uses `<article>`, so every selector timed out (~50 s), and the page-source fallback used an HTML-escaped URL (`&amp;`) that the signed CDN rejected with 403. Now matches a bare `<video>` first, unescapes fallback URLs, and takes the title from the document title. Removed the unneeded `--disable-web-security` Chrome flag.
4. **YouTube JS runtime**: yt-dlp enables only deno by default and warned "No supported JavaScript runtime" even with Node.js installed. `get_js_runtimes()` now also enables node/bun when found on PATH. No formats were actually missing yet, but yt-dlp has deprecated extraction without a runtime.
5. **Tkinter was driven from the download thread** (widget updates and message boxes). Workers now receive `ThreadSafeWidget` proxies and use `ui_call()`; the main thread drains a queue every 50 ms. Updates are dropped once the window is closed, so a download that outlives the window finishes cleanly. The two download handlers were merged into `start_download(is_audio)`, which disables both buttons while a download runs — parallel downloads shared one `temp/` folder and deleted each other's files.

### Changes
- `Downloader.py`: items 1–5 above; `APP_VERSION` 2.0.5
- `requirements.txt`: selenium documented as required for Threads; dropped stale beautifulsoup4 note
- `README.md`: platform table (Threads, redd.it), troubleshooting rows (Threads, JS runtime, certificate errors)
- `AGENTS.md`, `CLAUDE.md`: version bump, architecture / code map updated
- `build_exe.bat`: version bump

### Verification
- Offline harness against the real module: 77 checks pass (platform detection incl. former false positives, option building, TikTok selector on synthetic format lists, settings round-trip, UI marshalling on a real Tk root, Threads routing).
- Live, through `download_media()` without cookies: TikTok video ×2 and audio, YouTube video and audio (log shows `[jsc:node] Solving JS challenges using node`), Threads video ×2 on `threads.com` (9 s each, H.264 + AAC). All pass with certificate verification enabled.
- Live with the local cookie files, through `download_media()`: Facebook video (VP9 + AAC) and MP3, Facebook Reel, Instagram reels in both `/reel/<id>/` and `/<user>/reel/<id>/` forms (VP9 + AAC) and MP3, X video, Reddit video, SoundCloud MP3, Bluesky video. All pass.
- Several yt-dlp sample posts (one Facebook Reel, three Instagram posts, one Reddit post) produced video-only files. Verified these sources are genuinely silent: yt-dlp lists no audio format for them and even the progressive files contain no audio stream. Not an app fault.
- Dead sample links (not app faults): one Facebook video ("Cannot parse data"), one X Amplify video (HTTP 500), one Instagram TV post (HTTP 400).
- Known, not fixed: titles are not unique on some platforms (every Instagram reel from one account is "Video by <account>"), and an existing output file with the same name is overwritten.

### Files changed
- `Downloader.py`, `requirements.txt`, `README.md`, `AGENTS.md`, `CLAUDE.md`, `build_exe.bat`, `WORKLOG.md`

---

## 2026-09-17 — v2.0.4: Fix silent TikTok downloads

### Summary
TikTok videos were saved without an audio track. TikTok serves single-file MP4s; the highest-bitrate ones are HEVC (`bytevc1`, reported by yt-dlp as `h265`), and some of those files contain no audio stream at all (yt-dlp issues #16622 / #17372). yt-dlp's default sort prefers h265 over h264 at equal resolution, so the generic `best[ext=mp4]` selector picked the silent file. Only yt-dlp 2026.08.19 labels those files as video-only, and with that version the old `bestvideo+bestaudio` selector would instead merge the silent video with TikTok's *background music track* (the only separate audio format TikTok exposes), still losing the real soundtrack. The app now uses TikTok-specific format strings that prefer the muxed H.264 MP4, which always carries audio and plays on stock Windows players. "Download Audio" for TikTok now extracts MP3 from that same file instead of the music track.

### Changes
- `Downloader.py`: `get_video_format()` takes a `platform` argument; new `TIKTOK_VIDEO_FORMAT` / `TIKTOK_AUDIO_FORMAT` constants; `APP_VERSION` 2.0.4
- `requirements.txt`: yt-dlp minimum raised to 2026.8.19 (carries the TikTok extractor fix)
- `README.md`: troubleshooting row for silent TikTok videos
- `AGENTS.md`, `CLAUDE.md`, `build_exe.bat`: version bump

### Verification
Offline: fed yt-dlp 2026.08.19's format selector synthetic TikTok format lists (both the pre-fix labelling and the current labelling); the new selector chooses the H.264 muxed file in both cases, while the old selector chose the silent HEVC file or the HEVC+music merge. Live TikTok test not possible from the development container (network blocked); user should re-test with a real URL after rebuilding.

### Files changed
- `Downloader.py`, `requirements.txt`, `README.md`, `AGENTS.md`, `CLAUDE.md`, `build_exe.bat`, `WORKLOG.md`

---

## 2026-05-31 — Batch scripts exit cleanly (no pause)

### Summary
Removed trailing `pause` from all project `.bat` files so they exit when finished instead of waiting for a keypress (which blocked Cursor/automation and looked like background processes).

### Files
- `build_exe.bat`, `publish_release.bat`, `install_dependencies.bat`, `update_dependencies.bat`

---

## 2026-05-31 — GitHub Release v2.0.3 published

### Summary
Published GitHub Release with Windows binaries attached to tag `v2.0.3`.

### Assets
- `Universal_Video_Downloader.exe` (~34 MB)
- `Universal_Video_Downloader_v2.0.3_Win64.zip` (exe + config templates)

### Release URL
https://github.com/spider2077/Universal-Video-Downloader/releases/tag/v2.0.3

---

## 2026-05-31 — Rewrite git history: single author (GitHub)

### Summary
Rewrote all commits to `Spider2077 <spider2077@gmail.com>` and force-pushed to fix accidental contributor identities (s-tech.pm contact email, old legal name).

### Notes
- GitHub commits use `spider2077@gmail.com` only
- `spider2077@s-tech.pm` remains website contact, not git author
- Force push: `main` rewritten on origin

---

### Summary
Added About dialog with company info and website link. Updated LICENSE and README copyright to Spiders Tech SRL.

### Follow-up
- [x] Tag `v2.0.3` pushed to GitHub
- [x] Exe rebuilt; zip at `dist/Universal_Video_Downloader_v2.0.3_Win64.zip`
- [x] GitHub Release v2.0.3 published with exe + zip assets

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
