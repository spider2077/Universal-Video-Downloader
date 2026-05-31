## Universal Video Downloader v2.0.3

Windows desktop app for downloading videos and audio from Facebook, YouTube, TikTok, Instagram, X, Reddit, SoundCloud, Threads, and Bluesky.

**Publisher:** [Spiders Tech SRL](https://www.s-tech.pm) — Dolj, Romania  
**License:** MIT

### What's new in v2.0.3

- Facebook downloads fixed (yt-dlp 2026, curl-cffi, browser impersonation)
- Unicode-safe titles (Romanian diacritics and special characters)
- About window with company info and website link
- Clearer error messages
- Security-focused repo layout (no cookies in source)

### Download & run

1. Download `Universal_Video_Downloader.exe`
2. Place it in a folder of your choice
3. Copy `settings.ini.example` → `settings.ini` (optional)
4. For Facebook/Instagram: add cookies to a `cookies/` folder — see `cookies/template.txt`
5. Install [FFmpeg](https://ffmpeg.org/download.html) and add to PATH (recommended)
6. Double-click the `.exe`

### Supported platforms

YouTube, Facebook (Reels, videos, share links), Instagram, X/Twitter, TikTok, Reddit, SoundCloud, Threads, Bluesky

### Important

- Facebook videos usually require fresh cookies exported while logged in at facebook.com
- Run `update_dependencies.bat` when using the Python source version to keep yt-dlp current
- For personal use only — respect copyright and platform terms of service
