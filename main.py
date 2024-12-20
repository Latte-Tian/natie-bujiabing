from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
import yt_dlp
import os
import time
from datetime import datetime
import json

app = FastAPI()

# 配置静态文件和模板
app.mount("/downloads", StaticFiles(directory="downloads"), name="downloads")
templates = Jinja2Templates(directory="templates")

# 存储下载记录
DOWNLOAD_DIR = "downloads"
DOWNLOAD_HISTORY_FILE = "download_history.json"

# 存储下载进度
download_progress = {}

def progress_hook(d):
    if d['status'] == 'downloading':
        download_progress['current'] = {
            'downloaded_bytes': d.get('downloaded_bytes', 0),
            'total_bytes': d.get('total_bytes', 0),
            'speed': d.get('speed', 0),
            'eta': d.get('eta', 0),
            'status': 'downloading'
        }
    elif d['status'] == 'finished':
        download_progress['current'] = {'status': 'finished'}

def load_download_history():
    if os.path.exists(DOWNLOAD_HISTORY_FILE):
        with open(DOWNLOAD_HISTORY_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def save_download_history(history):
    with open(DOWNLOAD_HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

async def download_video(url: str):
    ydl_opts = {
        'format': 'best',
        'outtmpl': os.path.join(DOWNLOAD_DIR, '%(title)s.%(ext)s'),
        'nocheckcertificate': True,
        'progress_hooks': [progress_hook],
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=True)
            video_info = {
                'title': info['title'],
                'duration': str(int(info['duration'])) + "秒",
                'uploader': info['uploader'],
                'description': info['description'],
                'filename': ydl.prepare_filename(info),
                'file_size': os.path.getsize(ydl.prepare_filename(info)),
                'download_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'local_path': ydl.prepare_filename(info)
            }
            
            history = load_download_history()
            history.append(video_info)
            save_download_history(history)
            
            return video_info
        except Exception as e:
            return {"error": str(e)}

@app.get("/")
async def home(request: Request):
    history = load_download_history()
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "videos": history}
    )

@app.post("/download")
async def download(url: str, background_tasks: BackgroundTasks):
    background_tasks.add_task(download_video, url)
    return {"message": "下载已开始"}

@app.get("/history")
async def get_history():
    return load_download_history()

@app.get("/progress")
async def get_progress():
    return download_progress.get('current', {})

if __name__ == "__main__":
    import uvicorn
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    uvicorn.run(app, host="0.0.0.0", port=8003) 