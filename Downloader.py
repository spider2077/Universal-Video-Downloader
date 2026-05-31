# Location: Universal-Video-Downloader/Downloader.py
# Script: Downloader.py

import os
import re
import tkinter as tk
from tkinter import messagebox, filedialog, ttk
import yt_dlp
from yt_dlp.networking.impersonate import ImpersonateTarget
import requests
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import sys
import subprocess
import threading
import configparser
import webbrowser

APP_VERSION = "2.0.3"
COMPANY_NAME = "Spiders Tech SRL"
COMPANY_LOCATION = "Dolj, Romania"
COMPANY_WEBSITE = "https://www.s-tech.pm"

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
    """Print without crashing on Windows cp1252 console."""
    try:
        print(*args, **kwargs)
    except UnicodeEncodeError:
        print(*[transliterate_text(str(a)) for a in args], **kwargs)

PLATFORM_COOKIE_FILES = {
    'youtube': ['www.youtube.com_cookies.txt'],
    'instagram': ['www.instagram.com_cookies.txt'],
    'facebook': ['www.facebook.com_cookies.txt'],
    'twitter': ['www.twitter.com_cookies.txt', 'x.com_cookies.txt'],
    'tiktok': ['www.tiktok.com_cookies.txt'],
    'reddit': ['www.reddit.com_cookies.txt'],
    'soundcloud': ['www.soundcloud.com_cookies.txt', 'soundcloud.com_cookies.txt'],
    'threads': ['www.threads.net_cookies.txt'],
    'bluesky': ['bsky.app_cookies.txt'],
    'pornhub': ['www.pornhub.com_cookies.txt'],
}

SUPPORTED_PLATFORMS = list(PLATFORM_COOKIE_FILES.keys())

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

def apply_impersonate(opts):
    """Set browser impersonation for Facebook/Instagram (yt-dlp 2026 API)."""
    if has_curl_cffi():
        opts['impersonate'] = ImpersonateTarget.from_str('chrome')

def format_error_message(error, platform=None):
    """Return a user-friendly error string for the status bar."""
    if isinstance(error, UnicodeEncodeError):
        return "Special characters in title — retry download (fixed in v2.0.2)"
    msg = str(error).strip() or type(error).__name__
    if platform == 'facebook':
        if 'Cannot parse data' in msg:
            return (
                "Facebook: re-export fresh cookies from facebook.com "
                "(see Cookie Instructions)"
            )
        if not msg or msg == 'AssertionError':
            return "Internal yt-dlp error — run update_dependencies.bat"
    if 'ffmpeg' in msg.lower():
        return "FFmpeg not found — install FFmpeg and add it to PATH"
    if len(msg) > 120:
        return msg[:117] + '...'
    return msg

def has_curl_cffi():
    """Check if curl-cffi is installed (required for Facebook browser impersonation)."""
    try:
        import curl_cffi  # noqa: F401
        return True
    except ImportError:
        return False

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

def get_video_format(has_ffmpeg, is_audio):
    """Pick a yt-dlp format string based on ffmpeg availability."""
    if is_audio:
        return 'bestaudio/best'
    if has_ffmpeg:
        return 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'
    return 'best[ext=mp4]/best'

def build_ydl_opts(platform, cookie_file, has_ffmpeg, is_audio, temp_output, progress_hook):
    """Build yt-dlp options with platform-specific settings."""
    opts = {
        'format': get_video_format(has_ffmpeg, is_audio),
        'outtmpl': temp_output + '.%(ext)s',
        'progress_hooks': [progress_hook],
        'restrictfilenames': True,
        'windowsfilenames': True,
        'nooverwrites': False,
        'overwrites': True,
        'no_check_certificate': True,
        'ignoreerrors': False,
        'force_generic_extractor': platform == 'generic',
        'writethumbnail': has_ffmpeg and not is_audio,
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

    if platform == 'youtube':
        opts.update({
            'extract_flat': False,
            'force_generic_extractor': False,
        })

    if platform in ('facebook', 'instagram') and has_curl_cffi():
        apply_impersonate(opts)

    return opts

def build_info_ydl_opts(platform, cookie_file):
    """Build lightweight yt-dlp options for metadata extraction."""
    opts = {
        'quiet': True,
        'no_warnings': True,
        'no_check_certificate': True,
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

# Function to determine platform based on URL
def detect_platform(url):
    """Detect the video platform from the URL."""
    if not url:
        return None
    
    url = url.lower()
    
    if 'youtube.com' in url or 'youtu.be' in url:
        return 'youtube'
    elif 'facebook.com' in url or 'fb.watch' in url:
        return 'facebook'
    elif 'instagram.com' in url:
        return 'instagram'
    elif 'twitter.com' in url or 'x.com' in url:
        return 'twitter'
    elif 'threads.net' in url:
        return 'threads'
    elif 'tiktok.com' in url:
        return 'tiktok'
    elif 'reddit.com' in url:
        return 'reddit'
    elif 'soundcloud.com' in url:
        return 'soundcloud'
    elif 'bsky.app' in url or 'bluesky.app' in url:
        return 'bluesky'
    elif 'pornhub.com' in url:
        return 'pornhub'
    else:
        return None

def check_ffmpeg():
    """Check if ffmpeg is installed and available."""
    try:
        result = subprocess.run(['ffmpeg', '-version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return result.returncode == 0
    except FileNotFoundError:
        return False

def download_media(url, output_dir, progress_bar, status_label, is_audio=False):
    """Unified download handler for both video and audio with proper metadata."""
    platform = detect_platform(url)
    if platform is None:
        safe_print("No recognized platform; attempting generic extraction.")
        platform = "generic"

    url = normalize_url(url, platform)
    cookie_file = get_cookie_file(platform) if platform != 'generic' else None

    if platform == 'facebook':
        if not cookie_file or not os.path.exists(cookie_file):
            status_label.config(text="Facebook: cookies required — see Cookie Instructions")
            messagebox.showwarning(
                "Facebook Cookies Required",
                "Facebook videos usually require login cookies.\n\n"
                "1. Log in to facebook.com in Chrome\n"
                "2. Export cookies with the 'Get cookies.txt' extension\n"
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

    # Clean up any existing temp files
    for file in os.listdir(temp_dir):
        try:
            os.remove(os.path.join(temp_dir, file))
        except Exception as e:
            safe_print(f"Error removing temp file: {str(e)}")

    # Check for ffmpeg availability
    has_ffmpeg = check_ffmpeg()
    if is_audio and not has_ffmpeg:
        status_label.config(text="FFmpeg required for audio extraction but not found")
        progress_bar.configure(style='Red.Horizontal.TProgressbar')
        messagebox.showerror("Error", "FFmpeg is required for audio extraction but not found.\nPlease install FFmpeg and try again.")
        return False
    elif not has_ffmpeg:
        status_label.config(text="Warning: ffmpeg not found, using single-file formats")
        safe_print("FFmpeg not found. Will use single-file formats only.")

    progress_hook = lambda d: update_progress_bar(d, progress_bar, status_label)

    try:
        info_opts = build_info_ydl_opts(platform, cookie_file)
        with yt_dlp.YoutubeDL(info_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        if not info or 'title' not in info:
            raise Exception(f"Could not retrieve video information from {platform}")

        original_title = info['title']

        artist = None
        if info.get('uploader'):
            artist = info['uploader']
        elif info.get('channel'):
            artist = info['channel']
        elif info.get('artist'):
            artist = info['artist']

        if artist:
            artist = sanitize_filename(artist)
            safe_print(f"Detected artist/uploader: {artist}")

        clean_title = original_title
        if artist and original_title.startswith(f"{artist} - "):
            clean_title = original_title[len(artist) + 3:]
            safe_print(f"Removed artist prefix from title: {clean_title}")

        sanitized_title = sanitize_filename(original_title)

        safe_print(f"{platform.capitalize()} - Original title: {original_title}")
        safe_print(f"{platform.capitalize()} - Sanitized title: {sanitized_title}")

        temp_output = os.path.join(temp_dir, f'temp_{int(time.time())}')
        ydl_opts = build_ydl_opts(platform, cookie_file, has_ffmpeg, is_audio, temp_output, progress_hook)

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

        final_output = os.path.join(output_dir, f'{sanitized_title}{file_ext}')

        if os.path.exists(final_output):
            try:
                os.remove(final_output)
            except Exception as e:
                safe_print(f"Error removing file: {str(e)}")

        if has_ffmpeg:
            status_label.config(text="Adding metadata to file...")
            if not add_metadata_to_file(downloaded_file, final_output, info, platform):
                os.rename(downloaded_file, final_output)
            else:
                os.remove(downloaded_file)
                for thumb_ext in ['.jpg', '.png', '.webp']:
                    thumb_path = temp_output + thumb_ext
                    if os.path.exists(thumb_path):
                        os.remove(thumb_path)
                        break
        else:
            os.rename(downloaded_file, final_output)

        for file in os.listdir(temp_dir):
            try:
                os.remove(os.path.join(temp_dir, file))
            except Exception as e:
                safe_print(f"Error removing temp file: {str(e)}")

        progress_bar['value'] = 100
        progress_bar.configure(style='Green.Horizontal.TProgressbar')

        if artist:
            status_label.config(text=f"{'Audio extracted' if is_audio else 'Downloaded'}: {artist} - {clean_title}")
        else:
            status_label.config(text=f"{'Audio extracted' if is_audio else 'Downloaded'}: {sanitized_title.replace('_', ' ')}")

        return True

    except Exception as e:
        safe_print(f"Download error: {str(e)}")
        progress_bar['value'] = 0
        progress_bar.configure(style='Red.Horizontal.TProgressbar')
        error_msg = format_error_message(e, platform)
        status_label.config(text=f"Error: {error_msg}")
        messagebox.showerror("Download Error", error_msg)

        try:
            for file in os.listdir(temp_dir):
                try:
                    os.remove(os.path.join(temp_dir, file))
                except Exception as cleanup_error:
                    safe_print(f"Error removing temp file: {str(cleanup_error)}")
        except Exception as cleanup_error:
            safe_print(f"Error cleaning up temp directory: {str(cleanup_error)}")

        return False

# Update progress bar
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
        progress_bar.configure(style='Green.Horizontal.TProgressbar')
        status_label.config(text="Download complete, processing file...")
        # No renaming here - will be done manually with button

# Add the new Threads download function
def download_threads_video(url, output_dir, progress_bar, status_label):
    """Download a video from Threads."""
    try:
        # Set up Chrome options
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-web-security')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--disable-notifications')
        chrome_options.add_argument('--disable-popup-blocking')
        chrome_options.add_argument(f'user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

        # Initialize the driver
        driver = webdriver.Chrome(options=chrome_options)
        
        try:
            # If it's a media URL, try to get the actual post URL
            if '/media?' in url:
                # Extract the post ID and username from the media URL
                parts = url.split('/post/')
                if len(parts) > 1:
                    post_id = parts[1].split('/')[0]
                    username = parts[0].split('/')[-1].replace('@', '')
                    url = f"https://www.threads.net/t/{post_id}"
                    safe_print(f"Converted media URL to post URL: {url}")
            
            # Load the page
            driver.get(url)
            time.sleep(5)  # Wait longer for dynamic content to load
            
            # First try to find the video in the post content
            try:
                # Look for video element in the post content with multiple selectors
                video_selectors = [
                    "article video",
                    "article [role='video']",
                    "article div[role='video']",
                    "article div[data-video-url]",
                    "article div[data-media-url]",
                    "article div[data-src]",
                    "article div[class*='video']",
                    "article div[class*='media']"
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
                    except:
                        continue
                
                if not video_element:
                    # Try to find video URL in the page source
                    page_source = driver.page_source
                    video_matches = re.findall(r'https?://[^\s<>"]+?\.(?:mp4|webm)[^\s<>"]*', page_source)
                    if video_matches:
                        video_url = video_matches[0]
                        safe_print(f"Found video URL in page source: {video_url}")
                    else:
                        raise Exception("No video element found in the post")
                else:
                    # Try multiple methods to get the video URL
                    video_url = None
                    
                    # Method 1: Direct src attribute
                    video_url = video_element.get_attribute('src')
                    
                    # Method 2: Data attributes
                    if not video_url:
                        for attr in ['data-src', 'data-video-url', 'data-media-url']:
                            video_url = video_element.get_attribute(attr)
                            if video_url:
                                safe_print(f"Found video URL in data attribute {attr}: {video_url}")
                                break
                    
                    # Method 3: Source elements
                    if not video_url:
                        source_elements = video_element.find_elements(By.TAG_NAME, "source")
                        for source in source_elements:
                            if source.get_attribute('type') == 'video/mp4':
                                video_url = source.get_attribute('src')
                                safe_print(f"Found video URL in source element: {video_url}")
                                break
                    
                    # Method 4: Network requests
                    if not video_url:
                        logs = driver.execute_script("return window.performance.getEntries();")
                        for log in logs:
                            if isinstance(log, dict) and 'name' in log:
                                if '.mp4' in log['name']:
                                    video_url = log['name']
                                    safe_print(f"Found video URL in network requests: {video_url}")
                                    break
                
                if video_url:
                    # Get post title if available
                    try:
                        title_element = driver.find_element(By.CSS_SELECTOR, "article h1, article h2, article h3, article [role='heading'], article div[role='heading']")
                        title = title_element.text.strip()
                        safe_print(f"Found post title: {title}")
                    except:
                        title = f"Threads_Video_{int(time.time())}"
                        safe_print("Using default title")
                    
                    # Sanitize the title
                    title = sanitize_filename(title)
                    
                    # Generate file path
                    file_path = os.path.join(output_dir, f"{title}.mp4")
                    
                    # Download with progress tracking
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                        'Referer': url,
                        'Accept': '*/*',
                        'Accept-Encoding': 'gzip, deflate, br',
                        'Connection': 'keep-alive',
                        'Sec-Fetch-Dest': 'video',
                        'Sec-Fetch-Mode': 'cors',
                        'Sec-Fetch-Site': 'same-origin'
                    }
                    
                    safe_print(f"Downloading video from URL: {video_url}")
                    video_response = requests.get(video_url, headers=headers, stream=True)
                    video_response.raise_for_status()
                    
                    total_size = int(video_response.headers.get('content-length', 0))
                    block_size = 8192
                    downloaded = 0
                    
                    with open(file_path, 'wb') as f:
                        for chunk in video_response.iter_content(chunk_size=block_size):
                            if chunk:
                                f.write(chunk)
                                downloaded += len(chunk)
                                if total_size:
                                    progress = int((downloaded / total_size) * 100)
                                    progress_bar['value'] = progress
                                    status_label.config(text=f"Downloading Threads video: {progress}%")
                    
                    return True
                else:
                    raise Exception("No video URL found in the Threads post")
                    
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
    # Remove or replace invalid characters
    invalid_chars = '<>:"/\\|?*'
    # Replace invalid characters with underscore
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    
    # Replace other problematic characters
    filename = transliterate_text(filename)
    
    # Remove emojis and other special characters
    filename = ''.join(char for char in filename if ord(char) < 128)
    
    # Fix multiple underscores
    filename = re.sub(r'_+', '_', filename)
    
    # Remove leading/trailing underscores
    filename = filename.strip('_')
    
    # Simply truncate to 100 characters if longer
    if len(filename) > 100:
        filename = filename[:100]
    
    # If empty after all filtering, use a timestamp
    if not filename or filename.isspace():
        filename = f"download_{time.strftime('%Y%m%d_%H%M%S')}"
    
    return filename.strip()

def add_metadata_to_file(input_file, output_file, info, platform):
    """Add metadata to the downloaded file."""
    try:
        # Extract metadata information
        title = info.get('title', '')
        
        # Get artist/uploader information from various possible fields
        artist = None
        if 'uploader' in info and info['uploader']:
            artist = info['uploader']
        elif 'channel' in info and info['channel']:
            artist = info['channel']
        elif 'artist' in info and info['artist']:
            artist = info['artist']
        
        # Clean up artist name if found
        if artist:
            artist = sanitize_filename(artist)
            safe_print(f"Detected artist/uploader: {artist}")
        
        # Clean the title to avoid redundancy with artist name
        clean_title = transliterate_text(title)
        if artist and title.startswith(f"{artist} - "):
            # Remove the "ARTIST - " prefix to avoid duplication
            clean_title = transliterate_text(title[len(artist) + 3:])
            safe_print(f"Removed artist prefix from title: {clean_title}")
        
        # Build FFmpeg command for metadata
        ffmpeg_cmd = ['ffmpeg', '-i', input_file, '-c', 'copy']
        
        # Add artist metadata if available
        if artist:
            ffmpeg_cmd.extend(['-metadata', f'artist={artist}'])
        
        # Add title metadata (ASCII-safe for Windows ffmpeg)
        ffmpeg_cmd.extend(['-metadata', f'title={clean_title}'])
        
        # Add platform as album
        ffmpeg_cmd.extend(['-metadata', f'album={platform.capitalize()}'])
        
        # Add date if available
        if 'upload_date' in info:
            upload_date = info['upload_date']
            if len(upload_date) == 8:  # YYYYMMDD format
                formatted_date = f"{upload_date[:4]}-{upload_date[4:6]}-{upload_date[6:8]}"
                ffmpeg_cmd.extend(['-metadata', f'date={formatted_date}'])
        
        # Output file
        ffmpeg_cmd.append(output_file)
        
        # Run FFmpeg to add metadata
        safe_print("Running FFmpeg metadata command for", output_file)
        subprocess.run(ffmpeg_cmd, check=True, capture_output=True)
        return True
    except Exception as e:
        safe_print(f"Error adding metadata: {str(e)}")
        return False

def is_valid_url(url):
    """Check if the URL is valid and from a supported platform."""
    if not url or not isinstance(url, str):
        return False
    
    # Basic URL validation
    if not re.match(r'https?://', url):
        return False
    
    # Check if it's from a supported platform
    platform = detect_platform(url)
    return platform is not None

def check_clipboard(root, url_entry):
    """Check clipboard for valid URLs and populate the entry field."""
    try:
        clipboard_content = root.clipboard_get()
        if is_valid_url(clipboard_content) and url_entry.get() != clipboard_content:
            url_entry.delete(0, tk.END)
            url_entry.insert(0, clipboard_content)
            safe_print(f"URL detected in clipboard: {clipboard_content}")
    except Exception as e:
        # Clipboard might be empty or contain non-text
        safe_print(f"Clipboard check error: {e}")

def show_cookie_instructions():
    """Display instructions for getting cookies using the Get cookies.txt extension."""
    instructions = """
How to Get Cookies for Video Platforms:

1. Install the "Get cookies.txt" extension:
   - Open Chrome Web Store
   - Search for "Get cookies.txt"
   - Install the extension by "ikimasho"

2. Get cookies for each platform:
   - YouTube:
     * Go to youtube.com and log in
     * Click the extension icon
     * Click "Export" to save cookies
     * Rename the file to "www.youtube.com_cookies.txt"
   
   - Instagram:
     * Go to instagram.com and log in
     * Click the extension icon
     * Click "Export" to save cookies
     * Rename the file to "www.instagram.com_cookies.txt"
   
   - Facebook:
     * Go to facebook.com and log in
     * Click the extension icon
     * Click "Export" to save cookies
     * Rename the file to "www.facebook.com_cookies.txt"
   
   - Twitter/X:
     * Go to twitter.com or x.com and log in
     * Click the extension icon
     * Click "Export" to save cookies
     * Rename to "www.twitter.com_cookies.txt" or "x.com_cookies.txt"
   
   - TikTok:
     * Go to tiktok.com and log in
     * Click the extension icon
     * Click "Export" to save cookies
     * Rename the file to "www.tiktok.com_cookies.txt"
   
   - Reddit:
     * Go to reddit.com and log in
     * Click the extension icon
     * Click "Export" to save cookies
     * Rename the file to "www.reddit.com_cookies.txt"
   
   - SoundCloud:
     * Go to soundcloud.com and log in
     * Click the extension icon
     * Click "Export" to save cookies
     * Rename to "www.soundcloud.com_cookies.txt" or "soundcloud.com_cookies.txt"

   - Facebook (important):
     * Most Facebook videos require fresh cookies
     * Export while logged in at facebook.com
     * Re-export if you see "Cannot parse data" errors

3. Save the cookie files:
   - Create a folder named "cookies" next to the app (or next to the .exe)
   - Place all cookie files in that folder
   - The application will automatically detect and use available cookies

   Facebook file MUST be named exactly:
   www.facebook.com_cookies.txt

Note: Cookies help access age-restricted content and improve download quality.
Never share cookie files — they contain your login session.
"""
    messagebox.showinfo("Cookie Instructions", instructions)

def show_about_window(parent):
    """Show About dialog with app and company information."""
    about = tk.Toplevel(parent)
    about.title("About")
    about.resizable(False, False)
    about.transient(parent)
    about.grab_set()

    frame = tk.Frame(about, padx=24, pady=20)
    frame.pack()

    tk.Label(frame, text="Universal Video Downloader", font=("Segoe UI", 12, "bold")).pack(anchor="w")
    tk.Label(frame, text=f"Version {APP_VERSION}", font=("Segoe UI", 10)).pack(anchor="w", pady=(0, 12))

    description = (
        "A lightweight tool for downloading videos and audio from popular "
        "social platforms using yt-dlp.\n\n"
        "For personal, quick downloads — not intended as a professional media tool. "
        "Respect copyright and platform terms of service."
    )
    tk.Label(frame, text=description, wraplength=380, justify="left").pack(anchor="w", pady=(0, 12))

    tk.Label(frame, text=f"Copyright (c) 2026 {COMPANY_NAME}", font=("Segoe UI", 10, "bold")).pack(anchor="w")
    tk.Label(frame, text=COMPANY_LOCATION, font=("Segoe UI", 10)).pack(anchor="w")
    tk.Label(frame, text=COMPANY_WEBSITE, font=("Segoe UI", 10), fg="blue").pack(anchor="w", pady=(0, 12))

    tk.Label(
        frame,
        text="Licensed under the MIT License. See LICENSE in the project folder.",
        wraplength=380,
        justify="left",
        font=("Segoe UI", 9),
    ).pack(anchor="w", pady=(0, 12))

    button_row = tk.Frame(frame)
    button_row.pack(anchor="e")

    def open_website():
        webbrowser.open(COMPANY_WEBSITE)

    tk.Button(button_row, text="Visit Website", command=open_website, width=14).pack(side=tk.LEFT, padx=(0, 8))
    tk.Button(button_row, text="Close", command=about.destroy, width=10).pack(side=tk.LEFT)

    about.update_idletasks()
    x = parent.winfo_x() + (parent.winfo_width() - about.winfo_width()) // 2
    y = parent.winfo_y() + (parent.winfo_height() - about.winfo_height()) // 2
    about.geometry(f"+{x}+{y}")

def load_settings():
    """Load settings from settings.ini file."""
    config = configparser.ConfigParser()
    config_file = os.path.join(get_app_dir(), 'settings.ini')
    
    # Default settings
    default_settings = {
        'Paths': {
            'output_folder': 'Output'
        }
    }
    
    # Always ensure settings.ini exists with default values
    if not os.path.exists(config_file):
        safe_print("Creating settings.ini with default values...")
        config.read_dict(default_settings)
        with open(config_file, 'w') as f:
            config.write(f)
    else:
        # Read existing settings
        config.read(config_file)
        
        # Check and add any missing sections or values
        for section, values in default_settings.items():
            if section not in config:
                config[section] = {}
            for key, value in values.items():
                if key not in config[section]:
                    safe_print(f"Adding missing setting: {section}/{key} = {value}")
                    config[section][key] = value
        
        # Save any missing settings
        with open(config_file, 'w') as f:
            config.write(f)
    
    return config

def save_settings(config):
    """Save settings to settings.ini file."""
    config_file = os.path.join(get_app_dir(), 'settings.ini')
    with open(config_file, 'w') as f:
        config.write(f)

def get_output_folder():
    """Get the output folder path from settings."""
    config = load_settings()
    return config['Paths']['output_folder']

def set_output_folder(path):
    """Set the output folder path in settings."""
    config = load_settings()
    config['Paths']['output_folder'] = path
    save_settings(config)

def open_output_folder():
    """Open the output folder in the default file explorer."""
    output_dir = get_output_folder()
    try:
        # Create the directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Open the folder using the appropriate command for the platform
        if sys.platform == 'win32':
            os.startfile(output_dir)
        elif sys.platform == 'darwin':  # macOS
            subprocess.run(['open', output_dir])
        else:  # Linux and other Unix-like
            subprocess.run(['xdg-open', output_dir])
            
    except Exception as e:
        safe_print(f"Error opening output folder: {e}")
        messagebox.showerror("Error", f"Could not open output folder: {str(e)}")

def change_output_folder():
    """Open a folder browser dialog to change the output folder."""
    current_folder = get_output_folder()
    new_folder = filedialog.askdirectory(
        title="Select Output Folder",
        initialdir=current_folder
    )
    if new_folder:
        set_output_folder(new_folder)
        messagebox.showinfo("Success", f"Output folder changed to:\n{new_folder}")

# GUI Setup
def create_gui():
    configure_console_encoding()
    root = tk.Tk()
    root.title(f"Universal Video Downloader v{APP_VERSION}")
    root.geometry("550x360")
    
    # Load settings at startup
    config = load_settings()
    output_folder = config['Paths']['output_folder']
    safe_print(f"Using output folder: {output_folder}")
    
    # Check and announce available cookies
    cookie_message = announce_cookies()
    if cookie_message:
        status_label = tk.Label(root, text=cookie_message, wraplength=350, fg="green")
        status_label.pack(pady=5)
    
    # URL entry
    url_frame = tk.Frame(root)
    url_frame.pack(pady=20)
    
    tk.Label(url_frame, text="Enter video URL:").grid(row=0, column=0, padx=5)
    
    url_entry = tk.Entry(url_frame, width=40)
    url_entry.grid(row=0, column=1, padx=5)
    
    # Check clipboard on startup
    root.after(500, lambda: check_clipboard(root, url_entry))
    
    # Also check clipboard when window gets focus
    def on_focus(event):
        root.after(100, lambda: check_clipboard(root, url_entry))
    
    root.bind("<FocusIn>", on_focus)
    
    # Status label above progress bar
    status_label = tk.Label(root, text="Ready to download", wraplength=350)
    status_label.pack(pady=5)
    
    # Progress bar
    style = ttk.Style()
    style.configure("Green.Horizontal.TProgressbar", background='green')
    style.configure("Red.Horizontal.TProgressbar", background='red')
    
    progress_bar = ttk.Progressbar(root, orient="horizontal", length=300, mode="determinate", style='Horizontal.TProgressbar')
    progress_bar.pack(pady=5)
    
    # Button frame for multiple buttons
    button_frame = tk.Frame(root)
    button_frame.pack(pady=10)
    
    # Download button
    def handle_download():
        url = url_entry.get().strip()
        if not url:
            messagebox.showerror("Error", "Please enter a URL")
            return
        
        progress_bar['value'] = 0
        progress_bar.configure(style='Horizontal.TProgressbar')
        
        def download_thread():
            result = False
            try:
                # Download video
                result = download_media(url, get_output_folder(), progress_bar, status_label, is_audio=False)
            except Exception as e:
                safe_print(f"Download error: {str(e)}")
                status_label.config(text=f"Error: {str(e)}")
            
            # Open output folder if download was successful
            if result:
                open_output_folder()
        
        threading.Thread(target=download_thread).start()
    
    download_button = tk.Button(button_frame, text="Download Video", command=handle_download, width=15)
    download_button.grid(row=0, column=0, padx=5, pady=3)
    
    # Audio-only download button
    def handle_audio_download():
        url = url_entry.get().strip()
        if not url:
            messagebox.showerror("Error", "Please enter a URL")
            return
        
        progress_bar['value'] = 0
        progress_bar.configure(style='Horizontal.TProgressbar')
        
        def download_thread():
            try:
                # Download audio
                download_media(url, get_output_folder(), progress_bar, status_label, is_audio=True)
            except Exception as e:
                safe_print(f"Audio download error: {str(e)}")
                status_label.config(text=f"Error: {str(e)}")
        
        threading.Thread(target=download_thread).start()
    
    audio_button = tk.Button(button_frame, text="Download Audio", command=handle_audio_download, width=15)
    audio_button.grid(row=0, column=1, padx=5, pady=3)
    
    # Output folder button with long-press functionality
    press_time = 0
    def on_press(event):
        nonlocal press_time
        press_time = time.time()
    
    def on_release(event):
        nonlocal press_time
        if time.time() - press_time >= 5:  # 5 seconds long press
            change_output_folder()
    
    output_button = tk.Button(button_frame, text="Open Output Folder", width=15)
    output_button.grid(row=0, column=2, padx=5, pady=3)
    output_button.bind('<Button-1>', on_press)
    output_button.bind('<ButtonRelease-1>', on_release)
    output_button.bind('<Leave>', lambda e: setattr(output_button, 'press_time', 0))
    output_button.config(command=open_output_folder)
    
    # Cookie instructions button
    cookie_button = tk.Button(button_frame, text="Cookie Instructions", command=show_cookie_instructions, width=15)
    cookie_button.grid(row=0, column=3, padx=5, pady=3)

    about_button = tk.Button(button_frame, text="About", command=lambda: show_about_window(root), width=15)
    about_button.grid(row=1, column=1, columnspan=2, padx=5, pady=(8, 3))
    
    root.mainloop()

if __name__ == "__main__":
    create_gui()