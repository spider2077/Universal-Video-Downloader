# Location: Universal-Video-Downloader/Downloader.py
# Script: Downloader.py

import os
import re
import sys
import json
import html
import time
import queue
import shutil
import subprocess
import threading
import configparser
import webbrowser
from urllib.parse import urlparse

import tkinter as tk
from tkinter import messagebox, filedialog
import customtkinter as ctk
import yt_dlp
from yt_dlp.networking.impersonate import ImpersonateTarget
import requests

APP_VERSION = "2.1.0"
COMPANY_NAME = "Spiders Tech SRL"
COMPANY_LOCATION = "Dolj, Romania"
COMPANY_WEBSITE = "https://www.s-tech.pm"

ACCENT = "#6366f1"        # matches the app icon
ACCENT_HOVER = "#4f46e5"
ACCENT_DARK = "#8b5cf6"

def configure_console_encoding():
    """Use UTF-8 on Windows console to avoid charmap errors with Romanian titles."""
    if sys.platform == 'win32':
        for stream in (sys.stdout, sys.stderr):
            if stream and hasattr(stream, 'reconfigure'):
                try:
                    stream.reconfigure(encoding='utf-8', errors='replace')
                except (AttributeError, OSError, ValueError):
                    pass

def transliterate_text(text):
    """Replace Romanian diacritics and other special chars for safe output."""
    if not text:
        return text
    for old, new in (
        ('ă', 'a'), ('â', 'a'), ('î', 'i'), ('ș', 's'), ('ț', 't'),
        ('Ă', 'A'), ('Â', 'A'), ('Î', 'I'), ('Ș', 'S'), ('Ț', 'T'),
    ):
        text = text.replace(old, new)
    return text

def safe_print(*args, **kwargs):
    """Print without crashing on Windows cp1252 console (or with no console at all)."""
    try:
        print(*args, **kwargs)
    except UnicodeEncodeError:
        print(*[transliterate_text(str(a)) for a in args], **kwargs)
    except (OSError, ValueError, AttributeError):
        pass

PLATFORM_COOKIE_FILES = {
    'youtube': ['www.youtube.com_cookies.txt'],
    'instagram': ['www.instagram.com_cookies.txt'],
    'facebook': ['www.facebook.com_cookies.txt'],
    'twitter': ['www.twitter.com_cookies.txt', 'x.com_cookies.txt'],
    'tiktok': ['www.tiktok.com_cookies.txt'],
    'reddit': ['www.reddit.com_cookies.txt'],
    'soundcloud': ['www.soundcloud.com_cookies.txt', 'soundcloud.com_cookies.txt'],
    'threads': ['www.threads.net_cookies.txt', 'www.threads.com_cookies.txt'],
    'bluesky': ['bsky.app_cookies.txt'],
    'pornhub': ['www.pornhub.com_cookies.txt'],
}

SUPPORTED_PLATFORMS = list(PLATFORM_COOKIE_FILES.keys())

# Matched against the URL's hostname (exact or subdomain), never as a substring:
# a plain "'x.com' in url" test also matches netflix.com, dropbox.com, etc.
PLATFORM_DOMAINS = {
    'youtube': ('youtube.com', 'youtu.be', 'youtube-nocookie.com'),
    'facebook': ('facebook.com', 'fb.watch'),
    'instagram': ('instagram.com',),
    'twitter': ('twitter.com', 'x.com'),
    'threads': ('threads.net', 'threads.com'),
    'tiktok': ('tiktok.com', 'tiktokv.com'),
    'reddit': ('reddit.com', 'redd.it'),
    'soundcloud': ('soundcloud.com',),
    'bluesky': ('bsky.app', 'bluesky.app'),
    'pornhub': ('pornhub.com',),
}

# Tkinter is not thread-safe. Download threads never touch widgets directly:
# they queue UI work here and the main thread drains it (see App).
_ui_queue = queue.Queue()
_ui_state = 'inline'  # 'inline' (no GUI loop) -> 'queued' (mainloop running) -> 'closed'

def ui_call(func, *args, **kwargs):
    """Run func on the Tk main thread; run it inline when no GUI loop is active."""
    if threading.current_thread() is threading.main_thread() or _ui_state == 'inline':
        func(*args, **kwargs)
    elif _ui_state == 'queued':
        _ui_queue.put((func, args, kwargs))

class ThreadSafeWidget:
    """Proxy that forwards widget updates from worker threads to the main thread.

    Exposes the small interface the download code uses: .config(text=...) for the
    status label and ['value'] = 0..100 for the progress bar.
    """
    def __init__(self, widget):
        self._widget = widget

    def config(self, **kwargs):
        ui_call(self._widget.config, **kwargs)

    configure = config

    def __setitem__(self, key, value):
        ui_call(self._widget.__setitem__, key, value)

class ProgressAdapter:
    """Lets the download code drive a CTkProgressBar with the old ['value'] = percent API."""
    def __init__(self, bar):
        self._bar = bar

    def __setitem__(self, key, value):
        if key == 'value':
            self._bar.set(max(0.0, min(100.0, float(value))) / 100.0)

    def config(self, **kwargs):
        style = kwargs.get('style', '')
        if 'Red' in style:
            self._bar.configure(progress_color='#ef4444')
        elif 'Green' in style:
            self._bar.configure(progress_color='#22c55e')
        else:
            self._bar.configure(progress_color=(ACCENT, ACCENT_DARK))

    configure = config

def get_js_runtimes():
    """JavaScript runtimes yt-dlp may use for YouTube (it only enables deno by default).

    Node 22+ is supported; Bun support is deprecated upstream, so it is not enabled.
    """
    runtimes = {'deno': {}}
    if shutil.which('node'):
        runtimes['node'] = {}
    return runtimes

def get_app_dir():
    """Return the directory where the app or script lives (works with PyInstaller)."""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

def get_cookies_dir():
    """Get the directory for storing cookies."""
    cookies_dir = os.path.join(get_app_dir(), "cookies")
    os.makedirs(cookies_dir, exist_ok=True)
    return cookies_dir

def has_curl_cffi():
    """Check if curl-cffi is installed (required for Facebook browser impersonation)."""
    try:
        import curl_cffi  # noqa: F401
        return True
    except ImportError:
        return False

def apply_impersonate(opts):
    """Set browser impersonation for Facebook/Instagram (yt-dlp 2026 API)."""
    if has_curl_cffi():
        opts['impersonate'] = ImpersonateTarget.from_str('chrome')

def format_error_message(error, platform=None):
    """Return a user-friendly error string for the status bar."""
    if isinstance(error, UnicodeEncodeError):
        return "Special characters in title — retry download"
    msg = str(error).strip() or type(error).__name__
    # yt-dlp prefixes its messages; keep only the useful part
    msg = re.sub(r'^ERROR:\s*', '', msg)
    if platform == 'facebook':
        if 'Cannot parse data' in msg or 'login' in msg.lower():
            return (
                "Facebook: re-export fresh cookies from facebook.com "
                "(see Cookie Instructions)"
            )
        if not msg or msg == 'AssertionError':
            return "Internal yt-dlp error — run update_dependencies.bat"
    if platform == 'instagram' and ('login' in msg.lower() or 'rate-limit' in msg.lower()):
        return "Instagram: re-export fresh cookies from instagram.com (see Cookie Instructions)"
    if 'ffmpeg' in msg.lower() or 'ffprobe' in msg.lower():
        return "FFmpeg not found — install FFmpeg and add it to PATH"
    if 'CERTIFICATE_VERIFY_FAILED' in msg:
        return "HTTPS certificate error — check the PC clock or antivirus HTTPS scanning"
    if 'Unsupported URL' in msg:
        return "This link is not supported"
    if len(msg) > 120:
        return msg[:117] + '...'
    return msg

def get_cookie_file(platform):
    """Get the cookie file path for a specific platform."""
    candidates = PLATFORM_COOKIE_FILES.get(platform, [])
    cookies_dir = get_cookies_dir()
    for filename in candidates:
        cookie_file = os.path.join(cookies_dir, filename)
        if os.path.exists(cookie_file) and os.path.getsize(cookie_file) > 0:
            return cookie_file
    if candidates:
        return os.path.join(cookies_dir, candidates[0])
    return None

def normalize_url(url, platform):
    """Normalize URLs for better extractor compatibility."""
    url = url.strip()
    if platform == 'facebook':
        url = re.sub(r'[?&]share_url=[^&]+', '', url)
        url = re.sub(r'[?&]rdid=[^&]+', '', url)
        url = url.rstrip('?&')
    return url

def extract_url(text):
    """Pull the first http(s) link out of free text (shared messages carry words around the link)."""
    if not text:
        return None
    match = re.search(r'https?://\S+', text, re.IGNORECASE)
    return match.group(0).rstrip('.,)]"\'') if match else None

# --- Format selection -------------------------------------------------------
#
# WhatsApp, iMessage, Telegram and stock players only accept H.264 video + AAC audio
# in MP4. yt-dlp's default "best" happily picks VP9 or AV1 inside an .mp4 (YouTube,
# Facebook, Instagram), which is why some downloads could not be sent. The selectors
# below ask for H.264/AAC first and only fall back to other codecs when the site has
# nothing else; finalize_media() then re-encodes whatever still is not H.264/AAC.
H264 = "vcodec~='^(avc1|h264)'"
AAC = "acodec~='^(mp4a|aac)'"

COMPAT_VIDEO_FORMAT = (
    f"bestvideo[ext=mp4][{H264}]+bestaudio[ext=m4a][{AAC}]"
    f"/best[ext=mp4][{H264}][{AAC}]"
    f"/bestvideo[{H264}]+bestaudio[{AAC}]"
    f"/bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"
)
COMPAT_VIDEO_FORMAT_NO_FFMPEG = f"best[ext=mp4][{H264}][{AAC}]/best[ext=mp4]/best"
BEST_VIDEO_FORMAT = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"
BEST_VIDEO_FORMAT_NO_FFMPEG = "best[ext=mp4]/best"

# TikTok serves single-file MP4s. Its highest-bitrate ones are HEVC ("bytevc1",
# reported by yt-dlp as vcodec=h265) and some of those carry no audio track at
# all (yt-dlp issues #16622 / #17372). The only separate audio format TikTok
# exposes is the background *music track*, not the video's own soundtrack, so a
# bestvideo+bestaudio merge must be avoided. Prefer the H.264 muxed file.
TIKTOK_VIDEO_FORMAT = 'best[ext=mp4][vcodec=h264]/best[ext=mp4][vcodec!=h265]/best[ext=mp4]/best'
TIKTOK_AUDIO_FORMAT = 'best[ext=mp4][vcodec=h264]/best[ext=mp4]/bestaudio/best'

def get_video_format(has_ffmpeg, is_audio, platform=None, compat=True):
    """Pick a yt-dlp format string based on ffmpeg availability, platform and compatibility mode."""
    if platform == 'tiktok':
        return TIKTOK_AUDIO_FORMAT if is_audio else TIKTOK_VIDEO_FORMAT
    if is_audio:
        return 'bestaudio/best'
    if compat:
        return COMPAT_VIDEO_FORMAT if has_ffmpeg else COMPAT_VIDEO_FORMAT_NO_FFMPEG
    return BEST_VIDEO_FORMAT if has_ffmpeg else BEST_VIDEO_FORMAT_NO_FFMPEG

def build_ydl_opts(platform, cookie_file, has_ffmpeg, is_audio, temp_output, progress_hook, compat=True):
    """Build yt-dlp options with platform-specific settings."""
    opts = {
        'format': get_video_format(has_ffmpeg, is_audio, platform, compat),
        'outtmpl': temp_output + '.%(ext)s',
        'progress_hooks': [progress_hook],
        'restrictfilenames': True,
        'windowsfilenames': True,
        'nooverwrites': False,
        'overwrites': True,
        'ignoreerrors': False,
        'noplaylist': True,
        'js_runtimes': get_js_runtimes(),
        'force_generic_extractor': platform == 'generic',
        'writethumbnail': False,
        'merge_output_format': 'mp4',
        'retries': 10,
        'fragment_retries': 10,
        'socket_timeout': 30,
    }

    if cookie_file and os.path.exists(cookie_file):
        opts['cookiefile'] = cookie_file

    if is_audio and has_ffmpeg:
        opts['postprocessors'] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }]

    if platform in ('facebook', 'instagram') and has_curl_cffi():
        apply_impersonate(opts)

    return opts

def build_info_ydl_opts(platform, cookie_file):
    """Build lightweight yt-dlp options for metadata extraction."""
    opts = {
        'quiet': True,
        'no_warnings': True,
        'noplaylist': True,
        'js_runtimes': get_js_runtimes(),
    }
    if cookie_file and os.path.exists(cookie_file):
        opts['cookiefile'] = cookie_file
    if platform in ('facebook', 'instagram') and has_curl_cffi():
        apply_impersonate(opts)
    return opts

def check_cookies():
    """Check for available cookies and return a list of platforms with cookies."""
    platforms_with_cookies = []
    for platform in SUPPORTED_PLATFORMS:
        cookie_file = get_cookie_file(platform)
        if cookie_file and os.path.exists(cookie_file) and os.path.getsize(cookie_file) > 0:
            platforms_with_cookies.append(platform)
    return platforms_with_cookies

def announce_cookies():
    """Announce which platforms have cookies available."""
    platforms = check_cookies()
    if platforms:
        message = "Cookies available for: " + ", ".join(platform.capitalize() for platform in platforms)
        safe_print(message)
        return message
    return None

def detect_platform(url):
    """Detect the video platform from the URL."""
    if not url:
        return None

    url = url.strip().lower()
    try:
        host = urlparse(url if '://' in url else '//' + url).hostname or ''
    except ValueError:
        return None

    for platform, domains in PLATFORM_DOMAINS.items():
        if any(host == domain or host.endswith('.' + domain) for domain in domains):
            return platform
    return None

def check_ffmpeg():
    """Check if ffmpeg (and ffprobe, used for the compatibility check) is available."""
    return bool(shutil.which('ffmpeg') and shutil.which('ffprobe'))

# --- Output compatibility ---------------------------------------------------

def probe_media(path):
    """Return {'vcodec', 'acodec', 'pix_fmt', 'width', 'height', 'duration'} via ffprobe, or None."""
    try:
        result = subprocess.run(
            ['ffprobe', '-v', 'error', '-show_entries',
             'stream=codec_type,codec_name,pix_fmt,width,height:format=duration',
             '-of', 'json', path],
            capture_output=True, text=True, encoding='utf-8', errors='replace',
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
        )
        data = json.loads(result.stdout or '{}')
    except (OSError, ValueError) as e:
        safe_print(f"ffprobe failed: {e}")
        return None
    info = {'vcodec': None, 'acodec': None, 'pix_fmt': None, 'width': 0, 'height': 0,
            'duration': float(data.get('format', {}).get('duration') or 0)}
    for stream in data.get('streams', []):
        kind = stream.get('codec_type')
        if kind == 'video' and stream.get('codec_name') not in ('mjpeg', 'png') and not info['vcodec']:
            info['vcodec'] = stream.get('codec_name')
            info['pix_fmt'] = stream.get('pix_fmt')
            info['width'] = stream.get('width') or 0
            info['height'] = stream.get('height') or 0
        elif kind == 'audio' and not info['acodec']:
            info['acodec'] = stream.get('codec_name')
    return info

def needs_reencode(probe):
    """True when a video file would be rejected by WhatsApp & co (not H.264 yuv420p + AAC)."""
    if not probe or not probe['vcodec']:
        return False
    video_ok = probe['vcodec'] == 'h264' and (probe['pix_fmt'] or 'yuv420p') == 'yuv420p'
    audio_ok = probe['acodec'] in (None, 'aac')
    return not (video_ok and audio_ok)

def metadata_args(info, platform):
    """ffmpeg -metadata arguments: title, artist (uploader), album (platform), date."""
    args = []
    title = transliterate_text(html.unescape(info.get('title', '') or ''))
    artist = html.unescape(info.get('uploader') or info.get('channel') or info.get('artist') or '')
    if artist.strip() == title.strip():
        artist = None
    if artist:
        artist = sanitize_filename(artist)
        if title.startswith(f"{artist} - "):
            title = title[len(artist) + 3:]
        args += ['-metadata', f'artist={artist}']
    args += ['-metadata', f'title={title}', '-metadata', f'album={platform.capitalize()}']
    upload_date = info.get('upload_date') or ''
    if len(upload_date) == 8:
        args += ['-metadata', f'date={upload_date[:4]}-{upload_date[4:6]}-{upload_date[6:8]}']
    return args

def finalize_media(input_file, output_file, info, platform, compat, status_label=None, progress_bar=None):
    """Write the final file with metadata; re-encode to H.264/AAC first when compatibility mode asks for it.

    Returns a short description of what was done ('copied', 'converted') or None on failure.
    """
    probe = probe_media(input_file)
    convert = compat and needs_reencode(probe)

    cmd = ['ffmpeg', '-y', '-hide_banner', '-loglevel', 'error', '-i', input_file]
    if convert:
        safe_print(f"Converting {probe['vcodec']}/{probe['acodec']} -> H.264/AAC for compatibility")
        if status_label:
            status_label.config(text="Converting to H.264/AAC (WhatsApp compatible)...")
        video_ok = probe['vcodec'] == 'h264' and (probe['pix_fmt'] or 'yuv420p') == 'yuv420p'
        if video_ok:
            cmd += ['-c:v', 'copy']
        else:
            cmd += ['-c:v', 'libx264', '-preset', 'fast', '-crf', '20', '-profile:v', 'high',
                    '-pix_fmt', 'yuv420p', '-vf', 'scale=trunc(iw/2)*2:trunc(ih/2)*2']
        cmd += ['-c:a', 'copy'] if probe['acodec'] in (None, 'aac') else ['-c:a', 'aac', '-b:a', '160k']
        cmd += ['-progress', 'pipe:1', '-nostats']
    else:
        cmd += ['-c', 'copy']
    if output_file.lower().endswith('.mp4'):
        cmd += ['-movflags', '+faststart']
    cmd += metadata_args(info, platform) + [output_file]

    try:
        process = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            encoding='utf-8', errors='replace',
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
        )
        duration = (probe or {}).get('duration') or 0
        if convert:
            for line in process.stdout:
                if line.startswith('out_time_us=') and duration > 0 and progress_bar is not None:
                    try:
                        done = int(line.split('=', 1)[1]) / 1_000_000
                        progress_bar['value'] = min(99.0, done / duration * 100)
                    except ValueError:
                        pass
        _, stderr = process.communicate()
        if process.returncode != 0:
            safe_print(f"ffmpeg failed: {stderr.strip()[-400:]}")
            return None
        return 'converted' if convert else 'copied'
    except OSError as e:
        safe_print(f"Error running ffmpeg: {e}")
        return None

def download_media(url, output_dir, progress_bar, status_label, is_audio=False, compat=True):
    """Unified download handler for both video and audio with proper metadata."""
    platform = detect_platform(url)
    if platform is None:
        safe_print("No recognized platform; attempting generic extraction.")
        platform = "generic"

    url = normalize_url(url, platform)

    # yt-dlp has no Threads extractor, so Threads posts go through the Selenium fallback.
    if platform == 'threads':
        if is_audio:
            progress_bar.configure(style='Red.Horizontal.TProgressbar')
            status_label.config(text="Threads: audio extraction is not supported — use Download Video")
            return False
        os.makedirs(output_dir, exist_ok=True)
        status_label.config(text="Opening Threads post in headless Chrome...")
        result = download_threads_video(url, output_dir, progress_bar, status_label)
        if result:
            progress_bar['value'] = 100
            progress_bar.configure(style='Green.Horizontal.TProgressbar')
            status_label.config(text="Downloaded Threads video")
        else:
            progress_bar['value'] = 0
            progress_bar.configure(style='Red.Horizontal.TProgressbar')
        return result

    cookie_file = get_cookie_file(platform) if platform != 'generic' else None

    if platform == 'facebook':
        if not cookie_file or not os.path.exists(cookie_file):
            status_label.config(text="Facebook: cookies required — see Cookie Instructions")
            ui_call(
                messagebox.showwarning,
                "Facebook Cookies Required",
                "Facebook videos usually require login cookies.\n\n"
                "1. Log in to facebook.com in Chrome\n"
                "2. Export cookies with the 'Get cookies.txt LOCALLY' extension\n"
                "3. Save as cookies/www.facebook.com_cookies.txt\n\n"
                "Click 'Cookie Instructions' for full steps."
            )
        elif not has_curl_cffi():
            safe_print("Warning: curl-cffi not installed — Facebook downloads may fail.")
            status_label.config(text="Tip: run install_dependencies.bat to update yt-dlp")

    # Create output and temp directories
    os.makedirs(output_dir, exist_ok=True)
    temp_dir = os.path.join(output_dir, "temp")
    os.makedirs(temp_dir, exist_ok=True)

    def clean_temp():
        try:
            for file in os.listdir(temp_dir):
                try:
                    os.remove(os.path.join(temp_dir, file))
                except Exception as e:
                    safe_print(f"Error removing temp file: {str(e)}")
        except Exception as e:
            safe_print(f"Error cleaning up temp directory: {str(e)}")

    clean_temp()

    # Check for ffmpeg availability
    has_ffmpeg = check_ffmpeg()
    if is_audio and not has_ffmpeg:
        status_label.config(text="FFmpeg required for audio extraction but not found")
        progress_bar.configure(style='Red.Horizontal.TProgressbar')
        ui_call(messagebox.showerror, "Error", "FFmpeg is required for audio extraction but not found.\nPlease install FFmpeg and try again.")
        return False
    elif not has_ffmpeg:
        status_label.config(text="Warning: ffmpeg not found, using single-file formats")
        safe_print("FFmpeg not found. Will use single-file formats only.")

    progress_hook = lambda d: update_progress_bar(d, progress_bar, status_label)

    try:
        info_opts = build_info_ydl_opts(platform, cookie_file)
        status_label.config(text=f"Reading {platform} info...")
        with yt_dlp.YoutubeDL(info_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        if not info or 'title' not in info:
            raise Exception(f"Could not retrieve video information from {platform}")

        original_title = html.unescape(info['title'])

        artist = info.get('uploader') or info.get('channel') or info.get('artist')
        if artist:
            artist = html.unescape(artist)
        if artist and artist.strip() == original_title.strip():
            artist = None   # Facebook without cookies reports the page title as uploader
        if artist:
            artist = sanitize_filename(artist)
            safe_print(f"Detected artist/uploader: {artist}")

        clean_title = original_title
        if artist and original_title.startswith(f"{artist} - "):
            clean_title = original_title[len(artist) + 3:]

        sanitized_title = sanitize_filename(original_title)

        safe_print(f"{platform.capitalize()} - Original title: {original_title}")
        safe_print(f"{platform.capitalize()} - Sanitized title: {sanitized_title}")

        temp_output = os.path.join(temp_dir, f'temp_{int(time.time())}')
        ydl_opts = build_ydl_opts(platform, cookie_file, has_ffmpeg, is_audio, temp_output, progress_hook, compat)

        if cookie_file and os.path.exists(cookie_file):
            safe_print(f"Using cookies for {platform}: {cookie_file}")

        if is_audio:
            status_label.config(text=f"Extracting audio from {platform} video...")
        else:
            status_label.config(text=f"Downloading from {platform}...")

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        downloaded_file = None
        file_ext = None
        if is_audio:
            if os.path.exists(temp_output + '.mp3'):
                downloaded_file = temp_output + '.mp3'
                file_ext = '.mp3'
        else:
            for ext in ['.mp4', '.webm', '.mkv', '.m4a']:
                candidate = temp_output + ext
                if os.path.exists(candidate):
                    downloaded_file = candidate
                    file_ext = ext
                    break

        if not downloaded_file:
            raise Exception("Download finished but output file was not found. Check cookies and try again.")

        # In compatibility mode everything ends up as .mp4 (webm/mkv get re-encoded)
        if not is_audio and compat and has_ffmpeg:
            file_ext = '.mp4'

        # Titles are not unique (every Instagram reel is "Video by <account>"): never overwrite
        final_output = unique_path(os.path.join(output_dir, f'{sanitized_title}{file_ext}'))

        done = None
        if has_ffmpeg:
            status_label.config(text="Adding metadata to file...")
            done = finalize_media(downloaded_file, final_output, info, platform, compat and not is_audio,
                                  status_label, progress_bar)
        if done:
            os.remove(downloaded_file)
        else:
            if os.path.exists(final_output):
                os.remove(final_output)
            os.rename(downloaded_file, final_output)

        clean_temp()

        progress_bar['value'] = 100
        progress_bar.configure(style='Green.Horizontal.TProgressbar')

        label = 'Audio extracted' if is_audio else ('Downloaded (converted for WhatsApp)' if done == 'converted' else 'Downloaded')
        if artist:
            status_label.config(text=f"{label}: {artist} - {clean_title}")
        else:
            status_label.config(text=f"{label}: {sanitized_title.replace('_', ' ')}")

        return True

    except Exception as e:
        safe_print(f"Download error: {str(e)}")
        progress_bar['value'] = 0
        progress_bar.configure(style='Red.Horizontal.TProgressbar')
        error_msg = format_error_message(e, platform)
        status_label.config(text=f"Error: {error_msg}")
        ui_call(messagebox.showerror, "Download Error", error_msg)
        clean_temp()
        return False

def unique_path(path):
    """Return path, or path with ' (2)', ' (3)', ... before the extension if it already exists."""
    if not os.path.exists(path):
        return path
    base, ext = os.path.splitext(path)
    for n in range(2, 1000):
        candidate = f"{base} ({n}){ext}"
        if not os.path.exists(candidate):
            return candidate
    return path

def update_progress_bar(d, progress_bar, status_label):
    if d['status'] == 'downloading':
        percent_str = d.get('_percent_str', '0.0%').strip('%')
        try:
            progress_bar['value'] = float(percent_str)
            status_label.config(text=f"Downloading: {d.get('_percent_str', '0.0%')} of {d.get('_total_bytes_str', 'unknown size')}")
        except ValueError:
            progress_bar['value'] = 0
    elif d['status'] == 'finished':
        progress_bar['value'] = 100
        status_label.config(text="Download complete, processing file...")

def download_threads_video(url, output_dir, progress_bar, status_label):
    """Download a video from Threads (no yt-dlp extractor exists; uses headless Chrome)."""
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC

        chrome_options = Options()
        chrome_options.add_argument('--headless=new')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--disable-notifications')
        chrome_options.add_argument('--disable-popup-blocking')
        chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

        driver = webdriver.Chrome(options=chrome_options)

        try:
            # If it's a media URL, try to get the actual post URL
            if '/media?' in url:
                parts = url.split('/post/')
                if len(parts) > 1:
                    post_id = parts[1].split('/')[0]
                    host = urlparse(url).netloc or 'www.threads.net'
                    url = f"https://{host}/t/{post_id}"
                    safe_print(f"Converted media URL to post URL: {url}")

            driver.get(url)
            time.sleep(5)  # Wait for dynamic content to load

            try:
                video_selectors = [
                    "video",  # current Threads markup: bare <video src=...>, no <article>
                    "article video",
                    "article [role='video']",
                    "article div[data-video-url]",
                    "article div[data-src]",
                ]

                video_element = None
                for selector in video_selectors:
                    try:
                        video_element = WebDriverWait(driver, 5).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                        )
                        if video_element:
                            safe_print(f"Found video element with selector: {selector}")
                            break
                    except Exception:
                        continue

                video_url = None
                if not video_element:
                    page_source = driver.page_source
                    video_matches = re.findall(r'https?://[^\s<>"]+?\.(?:mp4|webm)[^\s<>"]*', page_source)
                    if video_matches:
                        # Page source is HTML/JSON-escaped; a signed CDN URL returns 403 unless unescaped
                        video_url = html.unescape(video_matches[0]).replace('\\/', '/').replace('\\u0026', '&')
                        safe_print(f"Found video URL in page source: {video_url}")
                    else:
                        raise Exception("No video element found in the post")
                else:
                    video_url = video_element.get_attribute('src')
                    if not video_url:
                        for attr in ['data-src', 'data-video-url', 'data-media-url']:
                            video_url = video_element.get_attribute(attr)
                            if video_url:
                                break
                    if not video_url:
                        for source in video_element.find_elements(By.TAG_NAME, "source"):
                            if source.get_attribute('type') == 'video/mp4':
                                video_url = source.get_attribute('src')
                                break
                    if not video_url:
                        for log in driver.execute_script("return window.performance.getEntries();"):
                            if isinstance(log, dict) and '.mp4' in log.get('name', ''):
                                video_url = log['name']
                                break

                if not video_url:
                    raise Exception("No video URL found in the Threads post")

                # Current Threads pages carry the post text in the document title
                title = (driver.title or '').strip()
                if not title or title.lower().startswith('threads'):
                    title = f"Threads_Video_{int(time.time())}"
                title = sanitize_filename(title)
                file_path = unique_path(os.path.join(output_dir, f"{title}.mp4"))

                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Referer': url,
                    'Accept': '*/*',
                }

                safe_print(f"Downloading video from URL: {video_url}")
                video_response = requests.get(video_url, headers=headers, stream=True, timeout=30)
                video_response.raise_for_status()

                total_size = int(video_response.headers.get('content-length', 0))
                downloaded = 0

                with open(file_path, 'wb') as f:
                    for chunk in video_response.iter_content(chunk_size=65536):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            if total_size:
                                progress = int((downloaded / total_size) * 100)
                                progress_bar['value'] = progress
                                status_label.config(text=f"Downloading Threads video: {progress}%")

                return True

            except Exception as e:
                safe_print(f"Error finding video: {str(e)}")
                raise Exception("Could not find video in the Threads post")

        finally:
            driver.quit()

    except Exception as e:
        safe_print(f"Threads download error: {str(e)}")
        status_label.config(text=f"Error: {str(e)}")
        return False

def sanitize_filename(filename):
    """Sanitize filename by removing invalid characters and limiting length."""
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')

    filename = transliterate_text(filename)

    # Remove emojis and other special characters
    filename = ''.join(char for char in filename if ord(char) < 128)
    filename = re.sub(r'_+', '_', filename)
    filename = filename.strip('_ .')

    if len(filename) > 100:
        filename = filename[:100].rstrip(' .')

    if not filename or filename.isspace() or filename.upper() in WINDOWS_RESERVED_NAMES:
        filename = f"download_{time.strftime('%Y%m%d_%H%M%S')}"

    return filename.strip()

WINDOWS_RESERVED_NAMES = {'CON', 'PRN', 'AUX', 'NUL'} | {f'COM{i}' for i in range(1, 10)} | {f'LPT{i}' for i in range(1, 10)}

def is_valid_url(url):
    """Check if the URL is valid and from a supported platform."""
    if not url or not isinstance(url, str):
        return False
    if not re.match(r'https?://', url):
        return False
    return detect_platform(url) is not None

# --- Settings ---------------------------------------------------------------

DEFAULT_SETTINGS = {
    'Paths': {'output_folder': 'Output'},
    'Options': {
        'whatsapp_compatible': 'true',   # re-encode to H.264/AAC when needed
        'appearance': 'system',          # system | light | dark
        'open_folder_after_download': 'true',
    },
}

def settings_path():
    return os.path.join(get_app_dir(), 'settings.ini')

def load_settings():
    """Load settings from settings.ini, adding any missing keys with defaults."""
    config = configparser.ConfigParser()
    config_file = settings_path()
    changed = False
    if os.path.exists(config_file):
        config.read(config_file, encoding='utf-8')
    else:
        safe_print("Creating settings.ini with default values...")
        changed = True
    for section, values in DEFAULT_SETTINGS.items():
        if section not in config:
            config[section] = {}
            changed = True
        for key, value in values.items():
            if key not in config[section]:
                config[section][key] = value
                changed = True
    if changed:
        save_settings(config)
    return config

def save_settings(config):
    with open(settings_path(), 'w', encoding='utf-8') as f:
        config.write(f)

def get_output_folder():
    folder = load_settings()['Paths']['output_folder']
    return folder if os.path.isabs(folder) else os.path.join(get_app_dir(), folder)

def set_output_folder(path):
    config = load_settings()
    config['Paths']['output_folder'] = path
    save_settings(config)

def get_option(key):
    return load_settings()['Options'].get(key, DEFAULT_SETTINGS['Options'][key])

def set_option(key, value):
    config = load_settings()
    config['Options'][key] = str(value).lower() if isinstance(value, bool) else str(value)
    save_settings(config)

def open_folder(path):
    """Open a folder in the system file browser."""
    try:
        os.makedirs(path, exist_ok=True)
        if sys.platform == 'win32':
            os.startfile(path)
        elif sys.platform == 'darwin':
            subprocess.run(['open', path])
        else:
            subprocess.run(['xdg-open', path])
    except Exception as e:
        safe_print(f"Error opening folder: {e}")
        messagebox.showerror("Error", f"Could not open folder: {str(e)}")

def open_output_folder():
    open_folder(get_output_folder())

# --- GUI --------------------------------------------------------------------

COOKIE_INSTRUCTIONS = """How to get cookies for video platforms

Some sites only serve videos to a logged-in browser. Facebook almost always,
Instagram often, the others only for private or age-restricted posts.

1. Install the "Get cookies.txt LOCALLY" extension in Chrome or Edge
   (Chrome Web Store, by kairi003). Avoid other "cookies.txt" extensions —
   several of them upload your cookies to third parties.

2. Log in to the site in the browser, open a page on it, click the extension
   icon and choose Export. Save the file into the "cookies" folder next to the
   app with exactly this name:

   YouTube ........ www.youtube.com_cookies.txt
   Instagram ...... www.instagram.com_cookies.txt
   Facebook ....... www.facebook.com_cookies.txt
   X / Twitter .... x.com_cookies.txt
   TikTok ......... www.tiktok.com_cookies.txt
   Reddit ......... www.reddit.com_cookies.txt
   SoundCloud ..... soundcloud.com_cookies.txt
   Bluesky ........ bsky.app_cookies.txt

3. Restart the app. The status line at the top lists the sites that have cookies.

Facebook: if you see "Cannot parse data" or "cookies required", export a fresh
file while logged in — Facebook sessions expire quickly.

Cookie files are your login session. Never share them, never commit them to git.
"""

ABOUT_TEXT = (
    "A lightweight tool for downloading videos and audio from popular social "
    "platforms using yt-dlp.\n\n"
    "Downloads are saved as H.264/AAC MP4 (or MP3), the format WhatsApp, "
    "Telegram and stock players accept.\n\n"
    "For personal, quick downloads — not intended as a professional media tool. "
    "Respect copyright and platform terms of service."
)

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(f"Universal Video Downloader {APP_VERSION}")
        self.geometry("680x520")
        self.minsize(600, 480)
        self._set_icon()

        self.downloading = False
        self._build()
        self._refresh_cookie_line()
        self.after(500, self._check_clipboard)
        self.bind("<FocusIn>", lambda e: self.after(100, self._check_clipboard))
        self.after(50, self._drain_ui_queue)

    # -- layout --------------------------------------------------------------

    def _set_icon(self):
        bundle_dir = getattr(sys, '_MEIPASS', get_app_dir())   # PyInstaller onefile extracts --add-data here
        for candidate in (os.path.join(bundle_dir, 'icons', 'app_icon.ico'),
                          os.path.join(get_app_dir(), 'icons', 'app_icon.ico')):
            if os.path.exists(candidate):
                try:
                    self.iconbitmap(candidate)
                except Exception:
                    pass
                break

    def _build(self):
        self.grid_columnconfigure(0, weight=1)
        pad = {'padx': 24}

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", pady=(20, 4), **pad)
        header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(header, text="Universal Video Downloader",
                     font=ctk.CTkFont(size=22, weight="bold")).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(header, text=f"v{APP_VERSION}  ·  yt-dlp {yt_dlp.version.__version__}",
                     font=ctk.CTkFont(size=12), text_color=("gray40", "gray60")).grid(row=1, column=0, sticky="w")
        self.theme_button = ctk.CTkSegmentedButton(header, values=["System", "Light", "Dark"], width=200,
                                                   command=self._set_appearance)
        self.theme_button.set(get_option('appearance').capitalize())
        self.theme_button.grid(row=0, column=1, rowspan=2, sticky="e")

        self.cookie_label = ctk.CTkLabel(self, text="", font=ctk.CTkFont(size=12), text_color=("gray40", "gray60"))
        self.cookie_label.grid(row=1, column=0, sticky="w", pady=(0, 10), **pad)

        url_row = ctk.CTkFrame(self, fg_color="transparent")
        url_row.grid(row=2, column=0, sticky="ew", **pad)
        url_row.grid_columnconfigure(0, weight=1)
        self.url_entry = ctk.CTkEntry(url_row, placeholder_text="Paste a video link (YouTube, TikTok, Facebook, Instagram, X, Reddit, ...)",
                                      height=40, font=ctk.CTkFont(size=13))
        self.url_entry.grid(row=0, column=0, sticky="ew")
        self.url_entry.bind("<Return>", lambda e: self.start_download(False))
        ctk.CTkButton(url_row, text="Paste", width=70, height=40, command=self._paste,
                      fg_color=("gray75", "gray30"), hover_color=("gray65", "gray40"),
                      text_color=("black", "white")).grid(row=0, column=1, padx=(8, 0))
        ctk.CTkButton(url_row, text="Clear", width=70, height=40, command=lambda: self.url_entry.delete(0, tk.END),
                      fg_color=("gray75", "gray30"), hover_color=("gray65", "gray40"),
                      text_color=("black", "white")).grid(row=0, column=2, padx=(8, 0))

        actions = ctk.CTkFrame(self, fg_color="transparent")
        actions.grid(row=3, column=0, sticky="ew", pady=(14, 0), **pad)
        actions.grid_columnconfigure((0, 1), weight=1)
        self.video_button = ctk.CTkButton(actions, text="Download Video", height=46, font=ctk.CTkFont(size=14, weight="bold"),
                                          fg_color=ACCENT, hover_color=ACCENT_HOVER, command=lambda: self.start_download(False))
        self.video_button.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        self.audio_button = ctk.CTkButton(actions, text="Download Audio (MP3)", height=46, font=ctk.CTkFont(size=14, weight="bold"),
                                          fg_color=ACCENT, hover_color=ACCENT_HOVER, command=lambda: self.start_download(True))
        self.audio_button.grid(row=0, column=1, sticky="ew", padx=(6, 0))

        self.progress = ctk.CTkProgressBar(self, height=14, progress_color=(ACCENT, ACCENT_DARK))
        self.progress.set(0)
        self.progress.grid(row=4, column=0, sticky="ew", pady=(22, 8), **pad)
        self.status_label = ctk.CTkLabel(self, text="Ready to download", font=ctk.CTkFont(size=13),
                                         wraplength=620, justify="left", anchor="w")
        self.status_label.grid(row=5, column=0, sticky="ew", **pad)

        self.grid_rowconfigure(6, weight=1)

        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.grid(row=7, column=0, sticky="ew", pady=(0, 18), **pad)
        footer.grid_columnconfigure((0, 1, 2, 3), weight=1)
        for col, (text, cmd) in enumerate((
            ("Open Output Folder", open_output_folder),
            ("Settings", self.show_settings),
            ("Cookie Instructions", self.show_cookie_instructions),
            ("About", self.show_about),
        )):
            ctk.CTkButton(footer, text=text, height=34, command=cmd,
                          fg_color="transparent", border_width=1, border_color=("gray60", "gray45"),
                          text_color=("gray15", "gray90"), hover_color=("gray85", "gray25")
                          ).grid(row=0, column=col, sticky="ew", padx=4)

        # Worker threads only ever see these proxies (Tkinter is not thread-safe)
        self.safe_status = ThreadSafeWidget(self.status_label)
        self.safe_progress = ThreadSafeWidget(ProgressAdapter(self.progress))

    # -- helpers -------------------------------------------------------------

    def _drain_ui_queue(self):
        # Reschedule first: a queued messagebox blocks this call until it is dismissed
        self.after(50, self._drain_ui_queue)
        while True:
            try:
                func, args, kwargs = _ui_queue.get_nowait()
            except queue.Empty:
                break
            try:
                func(*args, **kwargs)
            except Exception as e:
                safe_print(f"UI update error: {e}")

    def _set_appearance(self, value):
        ctk.set_appearance_mode(value.lower())
        set_option('appearance', value.lower())

    def _refresh_cookie_line(self):
        message = announce_cookies()
        self.cookie_label.configure(text=message or "No cookie files found (needed for Facebook; see Cookie Instructions)")

    def _set_url(self, text):
        self.url_entry.delete(0, tk.END)
        self.url_entry.insert(0, text)

    def _paste(self):
        try:
            url = extract_url(self.clipboard_get())
        except tk.TclError:
            url = None
        if url:
            self._set_url(url)
        else:
            self.status_label.configure(text="Clipboard does not contain a link")

    def _check_clipboard(self):
        """Auto-fill the entry when the clipboard holds a supported link."""
        try:
            url = extract_url(self.clipboard_get())
        except tk.TclError:
            return
        if url and is_valid_url(url) and self.url_entry.get().strip() != url and not self.downloading:
            self._set_url(url)
            safe_print(f"URL detected in clipboard: {url}")

    def _set_buttons(self, enabled):
        state = tk.NORMAL if enabled else tk.DISABLED
        self.video_button.configure(state=state)
        self.audio_button.configure(state=state)

    # -- actions -------------------------------------------------------------

    def start_download(self, is_audio):
        url = extract_url(self.url_entry.get()) or self.url_entry.get().strip()
        if not url:
            messagebox.showerror("Error", "Please enter a URL")
            return
        if self.downloading:
            return
        self.downloading = True
        self.progress.set(0)
        self.progress.configure(progress_color=(ACCENT, ACCENT_DARK))
        # One download at a time: parallel downloads share (and wipe) the same temp folder
        self._set_buttons(False)
        compat = get_option('whatsapp_compatible') == 'true'
        output_dir = get_output_folder()

        def worker():
            result = False
            try:
                result = download_media(url, output_dir, self.safe_progress, self.safe_status, is_audio=is_audio, compat=compat)
            except Exception as e:
                safe_print(f"{'Audio download' if is_audio else 'Download'} error: {str(e)}")
                self.safe_status.config(text=f"Error: {str(e)}")
            finally:
                ui_call(self._finish_download)
            if result and not is_audio and get_option('open_folder_after_download') == 'true':
                ui_call(open_output_folder)

        threading.Thread(target=worker, daemon=True).start()

    def _finish_download(self):
        self.downloading = False
        self._set_buttons(True)

    # -- dialogs -------------------------------------------------------------

    def _dialog(self, title, width, height):
        win = ctk.CTkToplevel(self)
        win.title(title)
        win.geometry(f"{width}x{height}+{self.winfo_x() + (self.winfo_width() - width) // 2}+{self.winfo_y() + (self.winfo_height() - height) // 2}")
        win.resizable(False, False)
        win.transient(self)
        win.after(200, win.grab_set)   # CTkToplevel needs a moment before it can grab
        return win

    def show_settings(self):
        win = self._dialog("Settings", 520, 330)
        win.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(win, text="Settings", font=ctk.CTkFont(size=18, weight="bold")).grid(row=0, column=0, columnspan=3, sticky="w", padx=24, pady=(20, 14))

        ctk.CTkLabel(win, text="Output folder").grid(row=1, column=0, sticky="w", padx=(24, 12))
        folder_entry = ctk.CTkEntry(win)
        folder_entry.insert(0, get_output_folder())
        folder_entry.grid(row=1, column=1, sticky="ew")

        def browse():
            chosen = filedialog.askdirectory(title="Select Output Folder", initialdir=get_output_folder(), parent=win)
            if chosen:
                folder_entry.delete(0, tk.END)
                folder_entry.insert(0, chosen)
        ctk.CTkButton(win, text="Browse", width=80, command=browse).grid(row=1, column=2, padx=(8, 24))

        compat_var = tk.BooleanVar(value=get_option('whatsapp_compatible') == 'true')
        ctk.CTkSwitch(win, text="WhatsApp-compatible output (H.264/AAC MP4, converts when needed)",
                      variable=compat_var).grid(row=2, column=0, columnspan=3, sticky="w", padx=24, pady=(22, 6))
        open_var = tk.BooleanVar(value=get_option('open_folder_after_download') == 'true')
        ctk.CTkSwitch(win, text="Open the output folder after each video download",
                      variable=open_var).grid(row=3, column=0, columnspan=3, sticky="w", padx=24, pady=6)

        ctk.CTkButton(win, text="Open cookies folder", command=lambda: open_folder(get_cookies_dir()),
                      fg_color="transparent", border_width=1, text_color=("gray15", "gray90")
                      ).grid(row=4, column=0, columnspan=3, sticky="w", padx=24, pady=(18, 0))

        def save():
            folder = folder_entry.get().strip() or 'Output'
            set_output_folder(folder)
            set_option('whatsapp_compatible', compat_var.get())
            set_option('open_folder_after_download', open_var.get())
            self._refresh_cookie_line()
            win.destroy()
        ctk.CTkButton(win, text="Save", width=100, fg_color=ACCENT, hover_color=ACCENT_HOVER, command=save
                      ).grid(row=5, column=2, sticky="e", padx=24, pady=(26, 20))

    def show_cookie_instructions(self):
        win = self._dialog("Cookie Instructions", 640, 560)
        box = ctk.CTkTextbox(win, font=ctk.CTkFont(family="Consolas", size=12), wrap="word")
        box.pack(fill="both", expand=True, padx=20, pady=(20, 10))
        box.insert("1.0", COOKIE_INSTRUCTIONS)
        box.configure(state="disabled")
        row = ctk.CTkFrame(win, fg_color="transparent")
        row.pack(fill="x", padx=20, pady=(0, 16))
        ctk.CTkButton(row, text="Open cookies folder", command=lambda: open_folder(get_cookies_dir())).pack(side="left")
        ctk.CTkButton(row, text="Close", width=90, command=win.destroy).pack(side="right")

    def show_about(self):
        win = self._dialog("About", 460, 400)
        frame = ctk.CTkFrame(win, fg_color="transparent")
        frame.pack(fill="both", expand=True, padx=28, pady=24)
        ctk.CTkLabel(frame, text="Universal Video Downloader", font=ctk.CTkFont(size=18, weight="bold")).pack(anchor="w")
        ctk.CTkLabel(frame, text=f"Version {APP_VERSION}  ·  yt-dlp {yt_dlp.version.__version__}",
                     text_color=("gray40", "gray60")).pack(anchor="w", pady=(0, 14))
        ctk.CTkLabel(frame, text=ABOUT_TEXT, wraplength=400, justify="left").pack(anchor="w", pady=(0, 14))
        ctk.CTkLabel(frame, text=f"Copyright (c) 2026 {COMPANY_NAME}", font=ctk.CTkFont(weight="bold")).pack(anchor="w")
        ctk.CTkLabel(frame, text=COMPANY_LOCATION).pack(anchor="w")
        ctk.CTkLabel(frame, text="Licensed under the MIT License.", text_color=("gray40", "gray60")).pack(anchor="w", pady=(10, 0))
        row = ctk.CTkFrame(frame, fg_color="transparent")
        row.pack(fill="x", pady=(18, 0))
        ctk.CTkButton(row, text="Visit Website", command=lambda: webbrowser.open(COMPANY_WEBSITE)).pack(side="left")
        ctk.CTkButton(row, text="Close", width=90, command=win.destroy,
                      fg_color="transparent", border_width=1, text_color=("gray15", "gray90")).pack(side="right")

def create_gui():
    global _ui_state
    configure_console_encoding()
    ctk.set_appearance_mode(get_option('appearance'))
    ctk.set_default_color_theme("blue")
    safe_print(f"Using output folder: {get_output_folder()}")
    app = App()
    _ui_state = 'queued'
    try:
        app.mainloop()
    finally:
        # A download may outlive the window; its UI updates are dropped from here on
        _ui_state = 'closed'

if __name__ == "__main__":
    create_gui()
