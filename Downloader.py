import os
import re
import tkinter as tk
from tkinter import messagebox, filedialog, ttk
import youtube_dl
import requests
from bs4 import BeautifulSoup
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import json
import wx

# Function to determine platform based on URL
def detect_platform(url):
    patterns = {
        'facebook': r'facebook\.com',
        'youtube': r'youtube\.com|youtu\.be',
        'tiktok': r'tiktok\.com',
        'bluesky': r'bsky\.app',
        'threads': r'threads\.net',
        'instagram': r'instagram\.com',
        'x': r'twitter\.com|x\.com',
    }

    for platform, pattern in patterns.items():
        if re.search(pattern, url):
            return platform
    return None

# Function to download video
def download_video(url, progress_bar):
    platform = detect_platform(url)
    if not platform:
        messagebox.showerror("Error", "Unsupported or invalid URL")
        return

    output_dir = "Output"
    os.makedirs(output_dir, exist_ok=True)

    if platform == 'threads':
        # Use the fallback Threads video downloader
        progress_bar['value'] = 0
        result_message = download_threads_video(url, output_dir)
        messagebox.showinfo("Result", result_message)
        progress_bar['value'] = 100
    else:
        ydl_opts = {
            'outtmpl': f'{output_dir}/%(title)s_{platform}.%(ext)s',
            'format': 'mp4',  # Download as mp4 format
            'progress_hooks': [lambda d: update_progress_bar(d, progress_bar)],
        }

        try:
            with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                result = ydl.extract_info(url, download=True)
                title = result.get('title', 'unknown')
                messagebox.showinfo("Success", f"Video '{title}' downloaded successfully to {output_dir}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to download video: {e}")

# Update progress bar
def update_progress_bar(d, progress_bar):
    if d['status'] == 'downloading':
        percent_str = d.get('_percent_str', '0.0%').strip('%')
        try:
            progress_bar['value'] = float(percent_str)
        except ValueError:
            progress_bar['value'] = 0
    elif d['status'] == 'finished':
        progress_bar['value'] = 100

# Add the new Threads download function
def download_threads_video(url, output_dir):
    try:
        # Set up Chrome options
        chrome_options = Options()
        chrome_options.add_argument('--headless')  # Run in headless mode
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument(f'user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')

        # Initialize the driver
        driver = webdriver.Chrome(options=chrome_options)
        
        try:
            # Load the page
            driver.get(url)
            
            # Wait for video element to be present
            wait = WebDriverWait(driver, 10)
            video_element = wait.until(EC.presence_of_element_located((By.TAG_NAME, "video")))
            
            # Get video source
            video_url = video_element.get_attribute('src')
            
            if not video_url:
                # Try finding video URL in network requests
                logs = driver.execute_script("return window.performance.getEntries();")
                for log in logs:
                    if isinstance(log, dict) and 'name' in log:
                        if '.mp4' in log['name']:
                            video_url = log['name']
                            break

            if video_url:
                # Download the video
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                    'Referer': url
                }
                video_response = requests.get(video_url, headers=headers, stream=True)
                video_response.raise_for_status()

                # Generate filename with timestamp
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                file_path = os.path.join(output_dir, f"Threads_Video_{timestamp}.mp4")
                
                # Save the video
                with open(file_path, 'wb') as f:
                    for chunk in video_response.iter_content(chunk_size=8192):
                        f.write(chunk)

                return f"Video downloaded successfully to {file_path}"
            else:
                return "No video URL found in the Threads post"
                
        finally:
            driver.quit()
            
    except Exception as e:
        return f"Failed to download Threads video: {str(e)}"

# GUI Setup
def create_gui():
    root = tk.Tk()
    root.title("Multi-Platform Video Downloader")
    root.geometry("400x250")
    icon = wx.Icon('icons/icon48.png')
    root.SetIcon(icon)

    # Input field label
    tk.Label(root, text="Enter Video URL:").pack(pady=10)

    # Input field for the video URL
    url_entry = tk.Entry(root, width=50)
    url_entry.pack(pady=5)

    # Progress bar
    progress_bar = ttk.Progressbar(root, orient="horizontal", length=300, mode="determinate")
    progress_bar.pack(pady=10)

    # Download button
    def handle_download():
        url = url_entry.get().strip()
        if not url:
            messagebox.showwarning("Warning", "Please enter a video URL")
        else:
            progress_bar['value'] = 0
            download_video(url, progress_bar)

    tk.Button(root, text="Download", command=handle_download).pack(pady=20)

    # Output folder button
    def open_output_folder():
        folder_path = os.path.abspath("Output")
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
        # Open the folder in file explorer
        if os.name == 'nt':  # For Windows
            os.startfile(folder_path)
        elif os.name == 'posix':  # For macOS and Linux
            import subprocess
            subprocess.Popen(['xdg-open', folder_path])  # Linux
            # subprocess.Popen(['open', folder_path])  # macOS

    tk.Button(root, text="Open Output Folder", command=open_output_folder).pack(pady=5)

    root.mainloop()

if __name__ == "__main__":
    create_gui()
