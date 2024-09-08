import os
import re
import string
import subprocess
from yt_dlp import YoutubeDL
import tkinter as tk
from tkinter import messagebox, filedialog
from tkinter.ttk import Progressbar
import threading

def download_youtube_video(video_id_or_url, progress_callback, cookies_file):
    ydl_opts = {
        'format': 'bestvideo+bestaudio/best',
        'outtmpl': '%(title)s.%(ext)s',
        'progress_hooks': [progress_callback],
        'no_color': True,  # カラー出力を無効にする
        'cookiefile': cookies_file  # Cookieファイルを指定
    }

    with YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(video_id_or_url, download=True)
        video_title = info_dict.get('title', None)
        video_description = info_dict.get('description', None)
        video_filename = ydl.prepare_filename(info_dict)

    sanitized_title = sanitize_filename(video_title, is_folder=True)
    if not os.path.exists(sanitized_title):
        os.makedirs(sanitized_title)

    new_video_path = os.path.join(sanitized_title, "original_video.mp4")
    os.rename(video_filename, new_video_path)

    return new_video_path, video_description, sanitized_title


def parse_timestamps(description):
    pattern = r'(\d{2}:\d{2})\s+(.+)'
    timestamps = re.findall(pattern, description)
    return [(time, title.strip()) for time, title in timestamps]


def convert_to_seconds(time_str):
    minutes, seconds = map(int, time_str.split(':'))
    return minutes * 60 + seconds


def sanitize_filename(filename, is_folder=False):
    valid_chars = f"-_.() {string.ascii_letters}{string.digits}"
    additional_chars = "「」『』【】《》〈〉｛｝？！＃＄％＆’（）＊＋，−．／：；＜＝＞＠［］＾＿｀｛｜｝〜、。・"
    sanitized = ''.join(c for c in filename if c in valid_chars or c in additional_chars or ('\u4e00' <= c <= '\u9fff') or ('\u3040' <= c <= '\u30ff'))
    if is_folder:
        sanitized = sanitized.replace(' ', '_')
    return sanitized


def trim_video(video_path, timestamps, output_dir):
    total_steps = len(timestamps)
    for i, (start_time, title) in enumerate(timestamps):
        start_seconds = convert_to_seconds(start_time)
        end_seconds = convert_to_seconds(timestamps[i+1][0]) if i+1 < len(timestamps) else None 
        sanitized_title = sanitize_filename(title)
        output_filename = f"{start_time.replace(':','')}-{timestamps[i+1][0].replace(':','') if i+1 < len(timestamps) else 'end'}_{sanitized_title}.mp4"
        output_filepath = os.path.join(output_dir, output_filename)
        if end_seconds:
            subprocess.run([
                "ffmpeg", "-y", "-i", video_path, "-ss", str(start_seconds), "-to", str(end_seconds), 
                "-c:v", "libx264", "-b:v", "2500k", "-c:a", "aac", "-b:a", "192k", output_filepath
            ], check=True)
        else:
            subprocess.run([
                "ffmpeg", "-y", "-i", video_path, "-ss", str(start_seconds),
                "-c:v", "libx264", "-b:v", "2500k", "-c:a", "aac", "-b:a", "192k", output_filepath
            ], check=True)
        print(f"Created {output_filepath}")
        progress_bar['value'] = (i + 1) / total_steps * 100
        app.update_idletasks()


def start_download():
    video_input = entry_url.get().strip()
    cookies_file = filedialog.askopenfilename(title="Select cookies.txt file", filetypes=[("Text files", "*.txt")])
    
    if not cookies_file:
        messagebox.showerror("エラー", "Cookieファイルを選択してください。")
        return
    
    progress_bar['value'] = 0
    progress_bar.start()
    
    def run_task():
        try:
            def progress_callback(d):
                if d['status'] == 'downloading':
                    # 正規表現でパーセンテージを抽出して、カラーコードを無視する
                    percent_str = d.get('_percent_str', '0.0%')
                    percent_float = float(re.search(r'(\d+\.\d+)', percent_str).group(1))
                    progress_bar['value'] = percent_float
                    app.update_idletasks()

            video_path, description, output_dir = download_youtube_video(video_input, progress_callback, cookies_file)
            timestamps = parse_timestamps(description)
            if not timestamps:
                messagebox.showerror("エラー", "目次が見つかりませんでした。動画の概要欄に目次が含まれていることを確認してください。")
            else:
                trim_video(video_path, timestamps, output_dir)
                messagebox.showinfo("完了", "動画のダウンロードとトリムが完了しました。")
        except Exception as e:
            messagebox.showerror("エラー", f"エラーが発生しました: {str(e)}")
        finally:
            progress_bar.stop()
            progress_bar['value'] = 0

    threading.Thread(target=run_task).start()


# GUIアプリケーションの作成
app = tk.Tk()
app.title("YouTube Video Downloader and Trimmer")

frame = tk.Frame(app)
frame.pack(padx=10, pady=10)

label_url = tk.Label(frame, text="YouTubeの動画URLまたはIDを入力してください:")
label_url.grid(row=0, column=0, sticky="w")

entry_url = tk.Entry(frame, width=50)
entry_url.grid(row=1, column=0)

button_download = tk.Button(frame, text="ダウンロードとトリム", command=start_download)
button_download.grid(row=2, column=0, pady=10)

progress_bar = Progressbar(frame, orient='horizontal', mode='determinate', length=300)
progress_bar.grid(row=3, column=0, pady=10)

app.mainloop()
