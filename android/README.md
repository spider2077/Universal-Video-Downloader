# Universal Video Downloader — Android

Android version of the desktop app, kept in the same repository. Paste or **share** a link, tap
**Download Video** or **Download Audio**.

> **Sideload only.** Google Play does not allow YouTube downloaders, so this app is distributed as an
> APK (GitHub Releases), never through the Play Store.

## How it works

| Piece | Desktop (`Downloader.py`) | Android |
|-------|---------------------------|---------|
| Engine | yt-dlp (pip) | [youtubedl-android](https://github.com/yausername/youtubedl-android) — bundles Python, yt-dlp, FFmpeg and QuickJS inside the APK |
| yt-dlp updates | `update_dependencies.bat` | Automatic on first run, then weekly; **Update yt-dlp** button |
| YouTube JS runtime | deno / node | Bundled QuickJS |
| Threads | Selenium + headless Chrome | Hidden `WebView` (`ThreadsExtractor.kt`) |
| Facebook / Instagram | `curl-cffi` impersonation | Not available on Android; public posts work without it |
| Cookies | `cookies/*.txt` next to the app | **Import cookies** → app-private storage |
| Output | `Output/` | `Movies/UniversalVideoDownloader`, `Music/UniversalVideoDownloader` |
| WhatsApp-compatible output | `finalize_media()` (libx264) | `DownloadEngine.reencode()` — bundled `ffprobe` checks the file, bundled `ffmpeg` converts with the phone's hardware encoder (`h264_mediacodec`), `libx264` as fallback. Always on |
| File names | Title | Title + `[video id]` (titles are not unique, e.g. Instagram) |

`Platforms.kt` is a line-for-line port of the platform detection, cookie-file names and format
selection in `Downloader.py` (including the TikTok H.264 rule). **Change both together.**
`PlatformsTest.kt` mirrors the desktop checks.

## Build

Requirements: Android Studio (provides the JDK and SDK). No other setup.

```bat
android\build_apk.bat
```

Output: `dist\Universal_Video_Downloader.apk` (git-ignored, ~76 MB, arm64 only).

Or open the `android/` folder in Android Studio and press Run.

## Install

```bat
adb install -r dist\Universal_Video_Downloader.apk
```

Or copy the APK to the phone, open it, and allow "install unknown apps". Requires Android 10+.

## Cookies on Android

Export Netscape cookie files on a PC exactly as for the desktop app, copy them to the phone, then
**Import cookies** and select them (several at once is fine). The app recognises the site from the
file name, or from the domains inside the file if it was saved as e.g. `cookies.txt`.

Cookie files are login sessions. They are stored in app-private storage, excluded from Android
backups and device transfers, and removed by **How? → Remove all cookies** or by uninstalling.

## Security

Same rules as [SECURITY.md](../SECURITY.md). Additionally **never commit**: `local.properties`
(contains a local path), signing keystores (`*.jks`, `*.keystore`, `keystore.properties`), APKs.

The debug APK is signed with the local Android debug key. That is fine for your own phones; to hand
the app to other people, create a release keystore (kept out of git) and build a signed release.

## Limitations

- A download runs inside the app, not in a background service: keep the app open until it finishes
  (the screen is kept on while downloading).
- One download at a time.
- Threads: video only, as on desktop.
