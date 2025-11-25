# ~/raspiframe/app/main.py
import os
import json
import asyncio
import random

from pathlib import Path
import socket
import qrcode

from typing import List, Dict, Any, Optional

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles


# ==== QR 生成ユーティリティ ==========================================

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"  # ← rasipframe/static を指す
QR_PATH = STATIC_DIR / "qr2.png"

_QR_PORT = 8000          # サーバのポートを使っている値に合わせる

def _current_ip() -> str:
    """現在のローカルIPを取得（失敗時は127.0.0.1）"""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        try:
            s.close()
        except Exception:
            pass
    return ip

def _generate_qr_png(page: str = "/static/settings.html", port: int = _QR_PORT) -> str:
    """ 現在IPでURLを組み立てて static/qr2.png に保存して返す """
    from pathlib import Path
    global STATIC_DIR, QR_PATH
    if isinstance(STATIC_DIR, str):
        STATIC_DIR = Path(STATIC_DIR)
    if isinstance(QR_PATH, str):
        QR_PATH = Path(QR_PATH)

    STATIC_DIR.mkdir(parents=True, exist_ok=True)

    url = f"http://{_current_ip()}:{port}{page}"
    img = qrcode.make(url)
    img.save(QR_PATH, format="PNG")
    return url

# =====================================================================









# ---- playlist cache ----
PLAYLIST_CACHE = None
PLAYLIST_CACHE_KEY = None


def _current_playlist_key():
    """
    selection の選択フォルダ + TZ をキーにして、
    これが変わったらプレイリストを作り直す。
    """
    sel = load_json(SEL_FILE, {"folders": []})
    folders = tuple(sorted(sel.get("folders", [])))

    cfg = load_json(CONFIG_FILE, {"tz": "Asia/Tokyo"})
    tz = cfg.get("tz", "Asia/Tokyo")

    return (folders, tz)







# 画像拡張子（必要なら増やしてOK）
_IMG_EXTS = {".jpg",".jpeg",".png",".webp",".tif",".tiff",".gif",".heic",".bmp"}

def _iter_all_images_from_selection():
    """selection.json の folders を再帰で走査してフルパスを yield"""
    sel = load_json(SEL_FILE, {"folders": []})
    for root in sel.get("folders", []):
        if not os.path.isdir(root):
            continue
        for dirpath, _, filenames in os.walk(root):
            for name in filenames:
                if os.path.splitext(name)[1].lower() in _IMG_EXTS:
                    yield os.path.join(dirpath, name)

def _rebuild_playlist():
    """TZを効かせて day_key を作り直し、キャッシュを更新"""
    global PLAYLIST_CACHE, PLAYLIST_CACHE_KEY
    key = _current_playlist_key()

    # TZ名
    cfg = load_json(CONFIG_FILE, {"tz": "Asia/Tokyo"})
    tzname = cfg.get("tz", "Asia/Tokyo")

    images = []
    for path in _iter_all_images_from_selection():
        ts, day_key = _ts_and_day_from_exif_or_mtime(path, tzname)
        images.append({"path": path, "ts": ts, "day_key": day_key})
    images.sort(key=lambda x: x["ts"])

    PLAYLIST_CACHE = {"images": images}
    PLAYLIST_CACHE_KEY = key

def _get_playlist():
    """キーが変わってたら再構築してから返す"""
    key = _current_playlist_key()
    if PLAYLIST_CACHE is None or PLAYLIST_CACHE_KEY != key:
        _rebuild_playlist()
    return PLAYLIST_CACHE






app = FastAPI()


@app.on_event("startup")
async def _on_startup_generate_qr():
    try:
        url = _generate_qr_png("/static/settings.html", _QR_PORT)
        print(f"[QR] generated: {url} -> {QR_PATH}")
    except Exception as e:
        print("[QR] generate failed:", e)
    
    # DLNA自動マウント（USBマウントを待つためリトライ付き）
    dlna_config = CONFIG.get("dlna", {})
    if dlna_config.get("auto_mount") and dlna_config.get("address"):
        print("[DLNA] Auto-mount enabled, attempting to mount...")
        
        # USBがマウントされるまで待つ（最大30秒、5秒間隔）
        creds = None
        for attempt in range(6):
            if attempt > 0:
                print(f"[DLNA] Waiting for USB mount... (attempt {attempt + 1}/6)")
                await asyncio.sleep(5)
            
            creds = load_usb_credentials()
            if creds:
                break
        
        if creds:
            address = dlna_config.get("address")
            name = dlna_config.get("name", "DLNA")
            share = dlna_config.get("share", "photo_resized")
            
            safe_name = re.sub(r'[^a-zA-Z0-9_-]', '_', name)
            mount_point = os.path.join(DLNA_MOUNT_BASE, safe_name)
            
            try:
                os.makedirs(mount_point, exist_ok=True)
                
                mount_cmd = [
                    'sudo', 'mount', '-t', 'cifs',
                    f'//{address}/{share}',
                    mount_point,
                    '-o', f'username={creds["username"]},password={creds["password"]},vers=3.0'
                ]
                
                result = await asyncio.to_thread(
                    subprocess.run, mount_cmd,
                    capture_output=True, text=True, timeout=10
                )
                
                if result.returncode == 0:
                    CONFIG["dlna"]["mount_point"] = mount_point
                    print(f"[DLNA] Auto-mounted {address}/{share} to {mount_point}")
                else:
                    print(f"[DLNA] Auto-mount failed: {result.stderr}")
            except Exception as e:
                print(f"[DLNA] Auto-mount exception: {e}")
        else:
            print("[DLNA] Auto-mount failed: credentials not found in USB after 30 seconds")


# ==== TimeZone Helper ==========================================================
from datetime import datetime
try:
    # Python 3.9+ 標準ライブラリ
    from zoneinfo import ZoneInfo
except Exception:
    ZoneInfo = None
    import pytz  # fallback 用（zoneinfoがない環境向け）



def _system_tz_name() -> str:
    """システムのタイムゾーン名を取得"""
    try:
        with open("/etc/timezone", "r") as f:
            return f.read().strip() or "UTC"
    except Exception:
        return "UTC"

def _current_tz() -> ZoneInfo:
    """config.jsonのtzを優先し、なければシステムTZを使う"""
    tzname = (CONFIG.get("tz") or "").strip() or _system_tz_name()
    try:
        return ZoneInfo(tzname)
    except Exception:
        return ZoneInfo("UTC")




def _tz_from_name(name: str):
    """TZ名からZoneInfo/pytzオブジェクトを取得（失敗時はUTCにフォールバック）"""
    if not name:
        name = "UTC"
    if ZoneInfo is not None:
        try:
            return ZoneInfo(name)
        except Exception:
            return ZoneInfo("UTC")
    else:
        try:
            return pytz.timezone(name)
        except Exception:
            return pytz.UTC

def _localize_naive(dt_naive: datetime, tz):
    """naive datetime に tz を付与（zoneinfo/pytz 両対応）"""
    # zoneinfo の場合
    if ZoneInfo is not None and isinstance(tz, ZoneInfo):
        return dt_naive.replace(tzinfo=tz)
    # pytz の場合
    try:
        return tz.localize(dt_naive)
    except Exception:
        return dt_naive


# ==== パス設定 ================================================================
BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR   = os.path.dirname(BASE_DIR)
DATA_DIR   = os.path.join(ROOT_DIR, "data")
STATIC_DIR = os.path.join(ROOT_DIR, "static")
os.makedirs(DATA_DIR, exist_ok=True)

CONFIG_FILE = os.path.join(DATA_DIR, "config.json")
SEL_FILE    = os.path.join(DATA_DIR, "selection.json")

# USB/DLNA関連パス
USB_MOUNT_POINTS = [
    "/mnt/usb",       # 固定マウントポイント（推奨・配布用）
    "/media/usb", 
    "/media/pi",
]
DLNA_MOUNT_BASE = "/mnt/dlna"
USB_CREDENTIALS_FILE = "credentials.txt"
USB_PHOTO_FOLDER = "Photo"

# ==== ユーティリティ ==========================================================
def load_json(path: str, default: Any) -> Any:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

def save_json(path: str, data: Any) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ==== USB認証情報読み込み ======================================================
def find_usb_mount() -> Optional[str]:
    """USBメモリのマウントポイントを検出（ユーザー非依存）"""
    # 固定マウントポイントをチェック
    for mount_point in USB_MOUNT_POINTS:
        if os.path.exists(mount_point) and os.path.isdir(mount_point):
            try:
                contents = os.listdir(mount_point)
                if contents:
                    return mount_point
            except Exception:
                continue
    
    # /media 以下の全マウントポイントを探す（ユーザー非依存）
    media_base = "/media"
    if os.path.exists(media_base):
        try:
            # /media/username を探す
            for username in os.listdir(media_base):
                user_media = os.path.join(media_base, username)
                if os.path.isdir(user_media):
                    # その中のマウントポイントを探す
                    for device in os.listdir(user_media):
                        device_path = os.path.join(user_media, device)
                        if os.path.isdir(device_path) and os.path.ismount(device_path):
                            return device_path
        except Exception:
            pass
    
    return None

def find_usb_photo_folder() -> Optional[str]:
    """USBメモリのPhotoフォルダを検出
    戻り値: /media/usb/Photo のようなパス、または None
    """
    usb_path = find_usb_mount()
    if not usb_path:
        return None
    
    photo_path = os.path.join(usb_path, USB_PHOTO_FOLDER)
    if os.path.exists(photo_path) and os.path.isdir(photo_path):
        return photo_path
    
    return None

def load_usb_credentials() -> Optional[Dict[str, str]]:
    """USBメモリからcredentials.txtを読み込み
    フォーマット:
    username=myuser
    password=mypass
    """
    usb_path = find_usb_mount()
    if not usb_path:
        return None
    
    cred_file = os.path.join(usb_path, USB_CREDENTIALS_FILE)
    if not os.path.exists(cred_file):
        return None
    
    try:
        creds = {}
        with open(cred_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if '=' in line and not line.startswith('#'):
                    key, val = line.split('=', 1)
                    creds[key.strip().lower()] = val.strip()
        
        if 'username' in creds and 'password' in creds:
            return creds
    except Exception as e:
        print(f"[USB] Failed to load credentials: {e}")
    
    return None

# ==== DLNA検出・マウント ======================================================
import subprocess
import re

def discover_dlna_services(timeout: int = 5) -> List[Dict[str, str]]:
    """avahi-browseでDLNAサービスを検出
    戻り値: [{"name": "MyNAS", "address": "192.168.1.100"}, ...]
    """
    try:
        # avahi-browse -t _smb._tcp で SMBサービスを検索
        result = subprocess.run(
            ['avahi-browse', '-t', '-p', '-r', '_smb._tcp'],
            capture_output=True,
            text=True,
            timeout=timeout
        )
        
        services = []
        seen = set()
        
        # avahi-browse の出力をパース
        for line in result.stdout.splitlines():
            if line.startswith('='):
                parts = line.split(';')
                if len(parts) >= 8:
                    name = parts[3]
                    address = parts[7]
                    
                    # 重複除外
                    key = f"{name}:{address}"
                    if key not in seen and address:
                        seen.add(key)
                        services.append({
                            "name": name,
                            "address": address
                        })
        
        return services
    except FileNotFoundError:
        print("[DLNA] avahi-browse not found. Install avahi-utils.")
        return []
    except subprocess.TimeoutExpired:
        print("[DLNA] Discovery timeout")
        return []
    except Exception as e:
        print(f"[DLNA] Discovery error: {e}")
        return []

def mount_dlna_service(address: str, name: str, username: str, password: str) -> Dict[str, Any]:
    """DLNAサービスをマウント
    戻り値: {"success": bool, "mount_point": str, "error": str}
    """
    # マウントポイントを作成
    safe_name = re.sub(r'[^a-zA-Z0-9_-]', '_', name)
    mount_point = os.path.join(DLNA_MOUNT_BASE, safe_name)
    
    try:
        os.makedirs(mount_point, exist_ok=True)
        
        # マウントコマンド
        mount_cmd = [
            'sudo', 'mount', '-t', 'cifs',
            f'//{address}/photo_resized',  # 共有フォルダ名（要調整）
            mount_point,
            '-o', f'username={username},password={password},vers=3.0'
        ]
        
        result = subprocess.run(mount_cmd, capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            print(f"[DLNA] Mounted {address} to {mount_point}")
            return {
                "success": True,
                "mount_point": mount_point,
                "error": None
            }
        else:
            error_msg = result.stderr.strip() or result.stdout.strip()
            print(f"[DLNA] Mount failed: {error_msg}")
            return {
                "success": False,
                "mount_point": None,
                "error": error_msg
            }
    
    except Exception as e:
        print(f"[DLNA] Mount exception: {e}")
        return {
            "success": False,
            "mount_point": None,
            "error": str(e)
        }

def unmount_dlna_service(mount_point: str) -> bool:
    """DLNAサービスをアンマウント"""
    try:
        result = subprocess.run(
            ['sudo', 'umount', mount_point],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            print(f"[DLNA] Unmounted {mount_point}")
            # マウントポイントディレクトリを削除
            try:
                os.rmdir(mount_point)
            except Exception:
                pass
            return True
        else:
            print(f"[DLNA] Unmount failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"[DLNA] Unmount exception: {e}")
        return False

# ==== 設定のデフォルト =======================================================
CONFIG: Dict[str, Any] = load_json(CONFIG_FILE, {
    "display_ms": 8000,
    "fade_ms": 3000,
    "margin_rate": "5%",
    "ken_burns": False,
    "order": "date",
    "show_caption": False,
    "timezone": "Asia/Tokyo",   # ★追加
    "dlna": {
        "enabled": False,
        "address": None,
        "name": None,
        "mount_point": None,
        "auto_mount": False
    }
})
# ==== SSE: 購読者キュー ======================================================
subscribers: List[asyncio.Queue] = []

async def _notify_all(message: Dict[str, Any]) -> None:
    """全クライアントにJSONメッセージをブロードキャスト（SSE用）"""
    dead: List[asyncio.Queue] = []
    for q in subscribers:
        try:
            await q.put(message)
        except Exception:
            dead.append(q)
    for q in dead:
        try:
            subscribers.remove(q)
        except ValueError:
            pass

# ==== 設定API ================================================================
@app.get("/api/config")
async def get_config():
    cfg = dict(CONFIG)
    if not cfg.get("tz"):
        cfg["tz"] = _system_tz_name()
    return cfg



@app.post("/api/config")
async def set_config(cfg: Dict[str, Any]):
    incoming = dict(cfg or {})

    # 旧キー 'timezone' → 'tz'
    if "timezone" in incoming and not incoming.get("tz"):
        incoming["tz"] = incoming["timezone"]

    # tz の妥当性チェック（来てる時だけ）
    if "tz" in incoming:
        try:
            _ = ZoneInfo(incoming["tz"])
        except Exception:
            incoming["tz"] = "UTC"

    # 変更前のTZ（現状）
    old_tz = CONFIG.get("tz") or CONFIG.get("timezone")

    # 反映＆保存
    CONFIG.update(incoming)
    save_json(CONFIG_FILE, CONFIG)

    # ★ tz_changed は「今回のリクエストに tz が含まれていて、値が変わった時だけ True」
    tz_changed = ("tz" in incoming) and (old_tz != incoming["tz"])

    try:
        if tz_changed:
            # 同期関数なら to_thread で
            await asyncio.to_thread(_rebuild_playlist)
            # クライアントに再取得を促すイベント
            await _notify_all({"type": "selection_changed"})
        else:
            await _notify_all({"type": "config_changed"})
    except Exception as e:
        # 落ちても 200 返す（UIの "FAILED" を防ぐ）＋ログ出力
        print("[set_config] post-notify error:", repr(e))

    return {"ok": True}


# ==== 選択フォルダAPI ========================================================
@app.get("/api/selection")
async def get_selection():
    sel = load_json(SEL_FILE, {"folders": []})
    
    # 初期状態（foldersが空）の場合、USBのPhoto/sampleフォルダを自動選択
    if not sel.get("folders"):
        photo_path = find_usb_photo_folder()
        if photo_path:
            sample_path = os.path.join(photo_path, "sample")
            if os.path.exists(sample_path) and os.path.isdir(sample_path):
                sel["folders"] = [sample_path]
                save_json(SEL_FILE, sel)
                # プレイリストを再構築
                await asyncio.to_thread(_rebuild_playlist)
    
    return sel

@app.post("/api/selection")
async def save_selection(sel: Dict[str, Any]):
    save_json(SEL_FILE, sel or {"folders": []})
    await _notify_all({"type": "selection_changed"})
    return {"ok": True}

# ==== DLNA API ================================================================
@app.get("/api/dlna/discover")
async def dlna_discover():
    """DLNAサービスを検出"""
    services = await asyncio.to_thread(discover_dlna_services, 5)
    return {"services": services}

@app.get("/api/dlna/status")
async def dlna_status():
    """現在のDLNAマウント状態"""
    dlna_config = CONFIG.get("dlna", {})
    
    # マウントポイントが存在するか確認
    mount_point = dlna_config.get("mount_point")
    is_mounted = False
    
    if mount_point and os.path.exists(mount_point):
        # 実際にマウントされているか確認
        try:
            result = subprocess.run(
                ['mountpoint', '-q', mount_point],
                capture_output=True,
                timeout=2
            )
            is_mounted = (result.returncode == 0)
        except Exception:
            is_mounted = False
    
    return {
        "enabled": dlna_config.get("enabled", False),
        "mounted": is_mounted,
        "address": dlna_config.get("address"),
        "name": dlna_config.get("name"),
        "mount_point": mount_point
    }

@app.post("/api/dlna/mount")
async def dlna_mount(request: Request):
    """DLNAサービスをマウント
    body: {"address": "192.168.1.100", "name": "MyNAS", "share": "photo_resized"}
    """
    try:
        data = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)
    
    address = data.get("address")
    name = data.get("name", "DLNA")
    share = data.get("share", "photo_resized")
    
    if not address:
        return JSONResponse({"error": "address is required"}, status_code=400)
    
    # USB認証情報を読み込み
    creds = load_usb_credentials()
    if not creds:
        return JSONResponse(
            {"error": "Credentials not found in USB. Please insert USB with credentials.txt"},
            status_code=400
        )
    
    # 既存のマウントを解除
    old_mount = CONFIG.get("dlna", {}).get("mount_point")
    if old_mount and os.path.exists(old_mount):
        await asyncio.to_thread(unmount_dlna_service, old_mount)
    
    # マウント実行（共有フォルダ名を指定可能に）
    safe_name = re.sub(r'[^a-zA-Z0-9_-]', '_', name)
    mount_point = os.path.join(DLNA_MOUNT_BASE, safe_name)
    
    try:
        os.makedirs(mount_point, exist_ok=True)
        
        mount_cmd = [
            'sudo', 'mount', '-t', 'cifs',
            f'//{address}/{share}',
            mount_point,
            '-o', f'username={creds["username"]},password={creds["password"]},vers=3.0'
        ]
        
        result = await asyncio.to_thread(
            subprocess.run, mount_cmd,
            capture_output=True, text=True, timeout=10
        )
        
        if result.returncode == 0:
            # 設定を保存
            CONFIG["dlna"] = {
                "enabled": True,
                "address": address,
                "name": name,
                "share": share,
                "mount_point": mount_point,
                "auto_mount": True
            }
            save_json(CONFIG_FILE, CONFIG)
            
            print(f"[DLNA] Mounted {address}/{share} to {mount_point}")
            return {
                "success": True,
                "mount_point": mount_point
            }
        else:
            error_msg = result.stderr.strip() or result.stdout.strip()
            print(f"[DLNA] Mount failed: {error_msg}")
            return JSONResponse(
                {"error": f"Mount failed: {error_msg}"},
                status_code=500
            )
    
    except Exception as e:
        print(f"[DLNA] Mount exception: {e}")
        return JSONResponse(
            {"error": str(e)},
            status_code=500
        )

@app.post("/api/dlna/unmount")
async def dlna_unmount():
    """DLNAサービスをアンマウント"""
    mount_point = CONFIG.get("dlna", {}).get("mount_point")
    
    if not mount_point:
        return {"success": False, "error": "No mount point configured"}
    
    success = await asyncio.to_thread(unmount_dlna_service, mount_point)
    
    if success:
        # 設定を更新
        CONFIG["dlna"]["enabled"] = False
        CONFIG["dlna"]["mount_point"] = None
        save_json(CONFIG_FILE, CONFIG)
        
        return {"success": True}
    else:
        return JSONResponse(
            {"error": "Unmount failed"},
            status_code=500
        )

# ==== USB Photo Folder API ====================================================
@app.get("/api/usb/photo")
async def get_usb_photo_info():
    """USBメモリのPhotoフォルダ情報を取得"""
    photo_path = find_usb_photo_folder()
    
    if photo_path:
        # フォルダ内の画像数をカウント
        image_count = 0
        try:
            for root, _, files in os.walk(photo_path):
                for fn in files:
                    if fn.lower().endswith(IMAGE_EXTS):
                        image_count += 1
        except Exception:
            pass
        
        return {
            "available": True,
            "path": photo_path,
            "image_count": image_count
        }
    else:
        return {
            "available": False,
            "path": None,
            "image_count": 0
        }

# ==== ファイルシステムブラウズ ===============================================
IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".tif", ".tiff", ".heic", ".heif")

@app.get("/api/fs/list")
async def fs_list(path: str = "/mnt/photos"):
    if not os.path.exists(path):
        return {"dirs": [], "images": [], "up": None}
    dirs, images = [], []
    try:
        for entry in os.scandir(path):
            if entry.is_dir():
                dirs.append(entry.path)
            elif entry.is_file():
                if entry.name.lower().endswith(IMAGE_EXTS):
                    images.append(entry.path)
    except Exception as e:
        print("fs_list error:", e)
    up = os.path.dirname(path) if path not in ("/", "") else None
    return {"dirs": dirs, "images": images, "up": up}


# ==== プレイリスト（並び順はサーバ側で確定） ================================
# EXIF → 撮影日優先で ts を作る
from typing import Optional

try:
    from PIL import Image, ExifTags  # Pillow がある場合は EXIF を使う
    _EXIF_TAGS = {v: k for k, v in ExifTags.TAGS.items()}
    _HAS_PIL = True
except Exception:
    _HAS_PIL = False


def _parse_exif_datetime(val: str) -> Optional[float]:
    """
    "YYYY:MM:DD HH:MM:SS" 形式の EXIF 日付文字列を epoch 秒に。
    サブ秒やヌル文字が混ざっていても極力捌く（ローカルタイムとして解釈）。
    """
    if not isinstance(val, str):
        return None
    s = val.strip().split("\x00", 1)[0]        # 末尾のヌル除去
    if "." in s:                               # サブ秒を落とす
        s = s.split(".", 1)[0]
    if len(s) < 19:
        return None
    try:
        import time
        t = time.strptime(s, "%Y:%m:%d %H:%M:%S")
        return float(int(time.mktime(t)))
    except Exception:
        return None




def _ts_and_day_from_exif_or_mtime(path: str, tzname: str) -> tuple[float, str]:
    """
    画像ファイルから (epoch秒, YYYY-MM-DD) を返す。
    EXIF(DateTimeOriginal→CreateDate→Digitized→DateTime) を優先。
    取れない時は mtime を使用。どちらも tzname を適用して day_key を作る。
    """
    # 1) TZ 準備
    try:
        tz = ZoneInfo(tzname)
    except Exception:
        tz = ZoneInfo("UTC")

    # 2) EXIF 優先
    if _HAS_PIL:
        try:
            with Image.open(path) as im:
                exif = im._getexif() or {}
            for key_name in ("DateTimeOriginal", "CreateDate", "DateTimeDigitized", "DateTime"):
                tag_id = _EXIF_TAGS.get(key_name)
                if not tag_id:
                    continue
                val = exif.get(tag_id)
                if isinstance(val, bytes):
                    try:
                        val = val.decode(errors="ignore")
                    except Exception:
                        val = None
                if isinstance(val, str):
                    s = val.strip().split("\x00", 1)[0]
                    if "." in s:
                        s = s.split(".", 1)[0]
                    if len(s) >= 19:
                        try:
                            # EXIFはナイーブ。tz を付与して確定させる
                            dt = datetime.strptime(s, "%Y:%m:%d %H:%M:%S").replace(tzinfo=ZoneInfo("Asia/Tokyo"))
                            dt = dt.astimezone(tz)
                            return (float(dt.timestamp()), dt.strftime("%Y-%m-%d"))
                        except Exception:
                            pass

        except Exception:
            pass


    # 3) フォールバック: mtime（epochはTZ不要、day_key生成だけTZ使用）
    try:
        mtime = float(os.path.getmtime(path))
        dt_local = datetime.fromtimestamp(mtime, tz)
        return (mtime, dt_local.strftime("%Y-%m-%d"))
    except Exception:
        dt_local = datetime.fromtimestamp(0, tz)
        return (0.0, dt_local.strftime("%Y-%m-%d"))





@app.get("/api/playlist")
async def playlist():
    """
    選択フォルダから画像一覧を作成して返す。
    - ts      : UTC基準のepoch秒
    - day_key : 指定TZでの撮影日 (YYYY-MM-DD)
    - model / exposure : EXIF由来の表示用キャプション
    TZの決定: CONFIG["tz"] → CONFIG["timezone"] → システムTZ → UTC
    """
    # ---- TZ 決定（後方互換あり） ----
    tzname = (CONFIG.get("tz") or CONFIG.get("timezone") or _system_tz_name()).strip()
    try:
        _ = ZoneInfo(tzname)   # 妥当性チェック
    except Exception:
        tzname = "UTC"

    sel = load_json(SEL_FILE, {"folders": []})
    items: List[Dict[str, Any]] = []

    for folder in sel.get("folders", []):
        if not os.path.exists(folder):
            continue
        for root, _, files in os.walk(folder):
            for fn in files:
                if not fn.lower().endswith(IMAGE_EXTS):
                    continue
                p = os.path.join(root, fn)

                # ts(UTC) と day_key(TZ適用) を取得
                ts, day_key = _ts_and_day_from_exif_or_mtime(p, tzname)

                model, exposure = _exif_model_and_exposure(p)
                items.append({
                    "path": p,
                    "ts": ts,
                    "day_key": day_key,
                    "model": model,
                    "exposure": exposure,
                })

    # 並び順
    order = (CONFIG.get("order") or "date").lower()
    if order == "random":
        random.shuffle(items)
    else:
        items.sort(key=lambda x: x["ts"])

    return {"images": items}


# ==== キャプション ==========================================================


def _exposure_to_text(val) -> str:
    """
    EXIF ExposureTime なら 1/125s などに、ShutterSpeedValue(APEX) なら近い分数へ。
    """
    try:
        # ExposureTime は (num, den) のタプルで来ることが多い
        if isinstance(val, tuple) and len(val) == 2 and val[1] != 0:
            num, den = int(val[0]), int(val[1])
            # 1秒未満は 1/x 表記、1秒以上は x"s
            if num/den < 1:
                return f"1/{int(round(den/num))}s"
            else:
                return f"{num/den:.1f}s"
        # 既に float の場合
        v = float(val)
        if v < 1:
            return f"1/{int(round(1.0/v))}s"
        return f"{v:.1f}s"
    except Exception:
        return ""

def _exif_model_and_exposure(path: str) -> tuple[str, str]:
    """
    (model_text, exposure_text) を返す。取れなければ空文字。
    """
    if not _HAS_PIL:
        return ("", "")
    try:
        with Image.open(path) as im:
            exif = im._getexif() or {}
        if not exif:
            return ("", "")
        # Model / Make
        model = exif.get(_EXIF_TAGS.get("Model"), "") or ""
        make  = exif.get(_EXIF_TAGS.get("Make"), "") or ""
        model_text = (f"{make} {model}".strip() or model or make).strip()

        # 露出: ExposureTime優先、なければ ShutterSpeedValue(APEX)
        exp = exif.get(_EXIF_TAGS.get("ExposureTime"))
        exposure_text = ""
        if exp is not None:
            exposure_text = _exposure_to_text(exp)
        else:
            # APEX → 秒へ: t = 2^(-APEX)
            sv = exif.get(_EXIF_TAGS.get("ShutterSpeedValue"))
            if sv is not None:
                try:
                    import math
                    if isinstance(sv, tuple) and len(sv) == 2 and sv[1] != 0:
                        apex = float(sv[0]) / float(sv[1])
                    else:
                        apex = float(sv)
                    sec = 2 ** (-apex)
                    exposure_text = _exposure_to_text(sec)
                except Exception:
                    pass

        return (model_text, exposure_text)
    except Exception:
        return ("", "")


# ==== Timestamp & DayKey (TZ適用) =============================================



# ==== 実ファイル配信 =========================================================
@app.get("/files")
async def serve_file(path: str):
    if os.path.exists(path) and os.path.isfile(path):
        return FileResponse(path)
    return JSONResponse({"error": "Not found"}, status_code=404)

# ==== Server-Sent Events (即時反映: 心拍 + 再接続短縮) =======================
@app.get("/api/events")
async def sse(request: Request):
    async def event_stream():
        yield "retry: 1000\n\n"  # 再接続間隔 1s
        q: asyncio.Queue = asyncio.Queue()
        subscribers.append(q)
        try:
            while True:
                try:
                    msg = await asyncio.wait_for(q.get(), timeout=10)
                    yield "data: " + json.dumps(msg, ensure_ascii=False) + "\n\n"
                except asyncio.TimeoutError:
                    # コメント行で心拍（接続維持）
                    yield ": ping\n\n"
                if await request.is_disconnected():
                    break
        finally:
            try:
                subscribers.remove(q)
            except ValueError:
                pass
    headers = {
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    }
    return StreamingResponse(event_stream(), media_type="text/event-stream", headers=headers)

# ==== Rotary 用 WebSocket ====================================================
ws_clients: List[WebSocket] = []

async def _ws_broadcast(text: str) -> None:
    dead: List[WebSocket] = []
    for ws in ws_clients:
        try:
            await ws.send_text(text)
        except Exception:
            dead.append(ws)
    for ws in dead:
        if ws in ws_clients:
            try:
                await ws.close()
            except Exception:
                pass
            ws_clients.remove(ws)

@app.websocket("/ws/rotary")
async def websocket_rotary(ws: WebSocket):
    await ws.accept()
    ws_clients.append(ws)
    try:
        while True:
            # rotary.py からの "rotary_left" / "rotary_right" / "rotary_push" を受信
            msg = await ws.receive_text()
            # 他のクライアント（主に player.html）へ転送
            for client in ws_clients:
                if client is not ws:
                    try:
                        await client.send_text(msg)
                    except Exception:
                        pass
    except WebSocketDisconnect:
        pass
    finally:
        if ws in ws_clients:
            ws_clients.remove(ws)

# ==== 静的ファイルとルート ===================================================
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/")
async def root():
    return FileResponse(os.path.join(STATIC_DIR, "settings.html"))
