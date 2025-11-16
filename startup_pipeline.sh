#!/bin/bash
# Raspiframe起動パイプライン
# 1. WiFi設定（USBから）
# 2. サービス起動
# 3. QR生成待機
# 4. Kioskモード起動

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="/var/log/raspiframe_startup.log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

log "========================================="
log "Raspiframe Startup Pipeline"
log "========================================="

# 1. WiFi設定（USBから）
log "Step 1: WiFi Setup from USB"
if [ -f "$SCRIPT_DIR/setup_wifi_from_usb.py" ]; then
    if sudo python3 "$SCRIPT_DIR/setup_wifi_from_usb.py" >> "$LOG_FILE" 2>&1; then
        log "WiFi setup completed successfully"
    else
        log "WiFi setup failed or skipped (USB not found)"
        log "Continuing with existing network configuration..."
    fi
else
    log "WiFi setup script not found, skipping"
fi

# 2. サービス起動待機
log "Step 2: Waiting for Raspiframe service..."
max_wait=30
count=0
while [ $count -lt $max_wait ]; do
    if systemctl is-active --quiet raspiframe; then
        log "Raspiframe service is running"
        break
    fi
    sleep 1
    count=$((count + 1))
done

if [ $count -ge $max_wait ]; then
    log "WARNING: Raspiframe service did not start within ${max_wait}s"
fi

# 3. ネットワーク接続確認
log "Step 3: Checking network connection..."
max_wait=30
count=0
while [ $count -lt $max_wait ]; do
    if ping -c 1 -W 1 8.8.8.8 > /dev/null 2>&1; then
        log "Network connection confirmed"
        break
    fi
    sleep 1
    count=$((count + 1))
done

if [ $count -ge $max_wait ]; then
    log "WARNING: No network connection detected"
fi

# 4. QRコード生成確認（サービスが生成するのを待つ）
log "Step 4: Waiting for QR code generation..."
QR_FILE="$SCRIPT_DIR/static/qr2.png"
max_wait=10
count=0
while [ $count -lt $max_wait ]; do
    if [ -f "$QR_FILE" ]; then
        log "QR code found: $QR_FILE"
        break
    fi
    sleep 1
    count=$((count + 1))
done

# 5. Kioskモード起動
log "Step 5: Starting Kiosk mode..."

# 環境変数設定
export DISPLAY=:0
export XAUTHORITY="$HOME/.Xauthority"

# Chromiumでkioskモード起動
if command -v chromium-browser > /dev/null 2>&1; then
    log "Starting Chromium in kiosk mode..."
    
    # 既存のChromiumプロセスを終了
    pkill -f chromium-browser || true
    sleep 2
    
    # Chromiumの設定ファイルで翻訳機能を無効化
    CHROMIUM_PREFS_DIR="$HOME/.config/chromium/Default"
    CHROMIUM_PREFS_FILE="$CHROMIUM_PREFS_DIR/Preferences"
    if [ ! -d "$CHROMIUM_PREFS_DIR" ]; then
        mkdir -p "$CHROMIUM_PREFS_DIR"
    fi
    
    # Preferencesファイルが存在する場合は編集、存在しない場合は作成
    if [ -f "$CHROMIUM_PREFS_FILE" ]; then
        # PythonでJSONを編集（より安全）
        python3 << EOF
import json
import os

prefs_file = "$CHROMIUM_PREFS_FILE"
try:
    with open(prefs_file, 'r', encoding='utf-8') as f:
        prefs = json.load(f)
except (FileNotFoundError, json.JSONDecodeError):
    prefs = {}

# 翻訳機能を完全に無効化
if 'translate' not in prefs:
    prefs['translate'] = {}
prefs['translate']['enabled'] = False
prefs['translate']['denied_count'] = {}
prefs['translate']['denied_count']['ja'] = 999999
prefs['translate']['accepted_count'] = {}

# 言語設定
if 'intl' not in prefs:
    prefs['intl'] = {}
prefs['intl']['selected_languages'] = 'ja'
prefs['intl']['accept_languages'] = 'ja,ja-JP'

# 翻訳UIを無効化
if 'translate_denied_count' not in prefs:
    prefs['translate_denied_count'] = {}
prefs['translate_denied_count']['ja'] = 999999

# 設定を保存
with open(prefs_file, 'w', encoding='utf-8') as f:
    json.dump(prefs, f, ensure_ascii=False, indent=2)
EOF
        log "Chromium preferences updated to disable translate"
    else
        # 新規作成
        python3 << EOF
import json
import os

prefs_file = "$CHROMIUM_PREFS_FILE"
os.makedirs(os.path.dirname(prefs_file), exist_ok=True)

prefs = {
    'translate': {
        'enabled': False,
        'denied_count': {'ja': 999999},
        'accepted_count': {}
    },
    'intl': {
        'selected_languages': 'ja',
        'accept_languages': 'ja,ja-JP'
    },
    'translate_denied_count': {'ja': 999999}
}

with open(prefs_file, 'w', encoding='utf-8') as f:
    json.dump(prefs, f, ensure_ascii=False, indent=2)
EOF
        log "Chromium preferences created with translate disabled"
    fi
    
    # Kioskモードで起動（より強力なフラグを追加）
    chromium-browser \
        --kiosk \
        --noerrdialogs \
        --disable-infobars \
        --no-first-run \
        --fast \
        --fast-start \
        --disable-features=TranslateUI,Translate,TranslateNewUX \
        --disable-translate \
        --disable-component-extensions-with-background-pages \
        --lang=ja \
        --accept-lang=ja,ja-JP \
        --disk-cache-dir=/dev/null \
        --password-store=basic \
        --disable-background-networking \
        http://localhost:8000/static/start.html \
        >> "$LOG_FILE" 2>&1 &
    
    log "Kiosk mode started (PID: $!)"
else
    log "WARNING: chromium-browser not found"
fi

log "========================================="
log "Startup pipeline complete"
log "========================================="

