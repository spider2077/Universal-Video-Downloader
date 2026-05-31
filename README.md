# Universal Video Downloader

A lightweight Windows desktop app for downloading videos and audio from popular social platforms. Built with **Python 3.12+**, **Tkinter**, and **yt-dlp**.

> **Disclaimer:** For personal, quick downloads only — not intended as a professional media tool. Respect copyright and platform terms of service.

## Supported platforms

| Platform | URL patterns | Cookies usually required? |
|----------|--------------|---------------------------|
| YouTube | `youtube.com`, `youtu.be` | Sometimes (age-restricted) |
| Facebook | `facebook.com`, `fb.watch`, Reels, share links | **Yes — almost always** |
| Instagram | `instagram.com` | Often |
| X / Twitter | `twitter.com`, `x.com` | Sometimes |
| TikTok | `tiktok.com` | Sometimes |
| Reddit | `reddit.com` | Sometimes |
| SoundCloud | `soundcloud.com` | Sometimes |
| Threads | `threads.net` | Sometimes |
| Bluesky | `bsky.app` | Rare |
| Other | Generic yt-dlp extractors | Varies |

## Quick start

### 1. Install dependencies

```bat
install_dependencies.bat
```

Requires **Python 3.12+** and **FFmpeg** on PATH.

### 2. Configure cookies (Facebook, Instagram, etc.)

1. Install the Chrome extension [**Get cookies.txt**](https://chromewebstore.google.com/detail/get-cookiestxt/bgaddhkoddajcdgocldbbfleckgcbcid) (by ikimasho).
2. Log in to the target site (e.g. facebook.com).
3. Export cookies and save into the `cookies/` folder next to the app:

| Platform | Filename |
|----------|----------|
| Facebook | `www.facebook.com_cookies.txt` |
| YouTube | `www.youtube.com_cookies.txt` |
| Instagram | `www.instagram.com_cookies.txt` |
| X / Twitter | `x.com_cookies.txt` or `www.twitter.com_cookies.txt` |
| TikTok | `www.tiktok.com_cookies.txt` |
| Reddit | `www.reddit.com_cookies.txt` |
| SoundCloud | `soundcloud.com_cookies.txt` |

See `cookies/template.txt` for the Netscape cookie format.

### 3. Run the app

```bat
run_downloader.bat
```

Or directly:

```bat
python Downloader.py
```

### 4. Download

1. Paste or copy a video URL (clipboard auto-fills when the window is focused).
2. Click **Download Video** or **Download Audio**.
3. Files save to the **Output** folder (configurable).

## Configuration

Copy `settings.ini.example` to `settings.ini`:

```ini
[Paths]
output_folder = Output
```

**Change output folder:** long-press (5 seconds) **Open Output Folder**, or edit `settings.ini`.

## Update yt-dlp (important for Facebook)

Facebook frequently changes; keep yt-dlp current:

```bat
update_dependencies.bat
```

This installs `yt-dlp[default,curl-cffi]` — **curl-cffi** enables browser impersonation required for Facebook since 2025.

## Build executable

```bat
build_exe.bat
```

Output: `dist/Universal_Video_Downloader.exe` (~34 MB). Icons are auto-generated if missing.

**Do not commit `dist/` to git** — publish the exe via GitHub Releases instead.

## Publishing to GitHub (public repo)

If an older version already exists on GitHub:

| What you push | What happens |
|---------------|--------------|
| Source files (`Downloader.py`, docs, etc.) | Updates code on the default branch |
| Old Release `.exe` | Unchanged until you upload a new Release |
| `cookies/`, `settings.ini`, `dist/` | **Never push** — security risk |

**Before every push:**

1. Run `git status` — no cookie or settings files staged.
2. Read [SECURITY.md](SECURITY.md).
3. If cookies were ever committed in the past, rotate all social sessions.

**Recommended:** tag `v2.0.2`, attach exe to GitHub Releases only.

## Project structure

```
Universal-Video-Downloader/
├── Downloader.py           # Main application (GUI + download logic)
├── requirements.txt
├── settings.ini.example
├── cookies/template.txt
├── install_dependencies.bat
├── update_dependencies.bat
├── run_downloader.bat
├── build_exe.bat
├── AGENTS.md               # AI agent documentation
├── CLAUDE.md               # Claude / AI assistant guide
├── WORKLOG.md              # Change history (update on every edit)
├── SECURITY.md             # Never commit cookies, settings, dist
├── README.md
└── LICENSE
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Facebook: "Cannot parse data" | Export **fresh** cookies from facebook.com; run `update_dependencies.bat` |
| Facebook: no download starts | Add `cookies/www.facebook.com_cookies.txt` |
| Audio download fails | Install FFmpeg and add to PATH |
| Long / emoji titles fail on Windows | Fixed in v2.0 — titles truncated to 100 chars |
| Cookies not detected in `.exe` | Place `cookies/` next to the `.exe`, not in source folder |

## License

MIT — see [LICENSE](LICENSE).
