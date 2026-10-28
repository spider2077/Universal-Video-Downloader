## Universal Video Downloader v2.1.0

Windows desktop app (and a sideloadable Android app) for downloading videos and audio from YouTube, TikTok, Facebook, Instagram, X, Reddit, SoundCloud, Threads and Bluesky.

**Publisher:** [Spiders Tech SRL](https://www.s-tech.pm) — Dolj, Romania  
**License:** MIT

### What's new in v2.1.0

- **Every video can now be sent on WhatsApp.** Some downloads used to be refused by WhatsApp, Telegram or iMessage although they were `.mp4` files: the codec inside was VP9 or AV1. The app now asks every site for H.264/AAC first and converts the file when a site offers nothing else (Facebook and Instagram always). Can be turned off in Settings.
- **New look.** Rebuilt interface with light / dark / system theme, a Settings dialog (output folder, WhatsApp-compatible output, open folder after download), readable cookie instructions and a new icon.
- **Android app** (`Universal_Video_Downloader.apk`, Android 10+, arm64). Share a link from any app, tap Download. Same H.264/AAC rule, cookies importable through the file picker. Sideload only — not on Google Play.
- yt-dlp 2026.10.26; Node.js is used for YouTube when installed.
- Existing files are never overwritten; titles with HTML entities are cleaned; links pasted with text around them are accepted.
- Threads downloads fixed (headless Chrome, current page layout); HTTPS certificates are verified again.

### Download & run (Windows)

1. Download `Universal_Video_Downloader_v2.1.0_Win64.zip` and extract it, or just `Universal_Video_Downloader.exe`
2. Install [FFmpeg](https://ffmpeg.org/download.html) and add it to PATH — required for audio and for the WhatsApp conversion
3. For Facebook/Instagram: export cookies with the **Get cookies.txt LOCALLY** browser extension into a `cookies/` folder next to the exe — see *Cookie Instructions* in the app
4. Double-click the `.exe`. Settings are kept in `settings.ini` next to it

### Install (Android)

Copy `Universal_Video_Downloader.apk` to the phone and open it; allow installing from that source. Play Protect may warn because the app is not from the Play Store.

### Supported platforms

YouTube, Facebook (Reels, videos, share links), Instagram, X/Twitter, TikTok, Reddit, SoundCloud, Threads, Bluesky

### Important

- The output is H.264/AAC MP4 or MP3. In compatibility mode YouTube is limited to 1080p (YouTube has no H.264 above that); turn the setting off for 4K.
- Cookie files are your login sessions. Never share them.
- For personal, quick downloads. Respect copyright and the platforms' terms of service.
