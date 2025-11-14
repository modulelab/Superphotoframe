#!/bin/bash
# Raspiframe完全セットアップスクリプト

echo "========================================="
echo "Raspiframe Complete Setup"
echo "========================================="

# 現在のユーザー名とホームディレクトリを取得
CURRENT_USER="$USER"
CURRENT_HOME="$HOME"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Installing for user: $CURRENT_USER"
echo "Home directory: $CURRENT_HOME"
echo "Script directory: $SCRIPT_DIR"

# 1. 必要なパッケージをインストール
echo ""
echo "Step 1: Installing required packages..."
sudo apt-get update
sudo apt-get install -y \
    avahi-utils \
    cifs-utils \
    python3-pip \
    chromium-browser \
    x11-xserver-utils \
    unclutter

# 2. Pythonパッケージのインストール
echo ""
echo "Step 2: Installing Python packages..."
pip3 install -r "${SCRIPT_DIR}/requirements.txt"

# 3. ディレクトリ作成
echo ""
echo "Step 3: Creating directories..."
sudo mkdir -p /mnt/dlna /mnt/usb
sudo chmod 777 /mnt/dlna /mnt/usb

sudo mkdir -p /var/log
sudo touch /var/log/raspiframe_startup.log
sudo chmod 666 /var/log/raspiframe_startup.log

# 4. sudoers設定（マウント権限）を動的生成
echo ""
echo "Step 4: Configuring sudoers for mount/umount..."
cat > /tmp/raspiframe-sudoers << EOF
# Raspiframe: ${CURRENT_USER}ユーザーがパスワードなしでマウント/アンマウントできるようにする
${CURRENT_USER} ALL=(ALL) NOPASSWD: /bin/mount
${CURRENT_USER} ALL=(ALL) NOPASSWD: /bin/umount
EOF
sudo cp /tmp/raspiframe-sudoers /etc/sudoers.d/raspiframe
sudo chmod 440 /etc/sudoers.d/raspiframe
sudo visudo -c
rm /tmp/raspiframe-sudoers

# 5. systemdサービスを動的生成してインストール
echo ""
echo "Step 5: Installing systemd services..."

# raspiframe.service
cat > /tmp/raspiframe.service << EOF
[Unit]
Description=Raspiframe Photo Frame Service
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=${CURRENT_USER}
WorkingDirectory=${SCRIPT_DIR}
Environment="PATH=/usr/local/bin:/usr/bin:/bin"
ExecStart=/usr/bin/python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
sudo cp /tmp/raspiframe.service /etc/systemd/system/
rm /tmp/raspiframe.service

# raspiframe-kiosk.service
cat > /tmp/raspiframe-kiosk.service << EOF
[Unit]
Description=Raspiframe Kiosk Mode Startup
After=raspiframe.service graphical.target
Wants=raspiframe.service

[Service]
Type=oneshot
User=${CURRENT_USER}
Environment="DISPLAY=:0"
Environment="XAUTHORITY=${CURRENT_HOME}/.Xauthority"
ExecStart=${SCRIPT_DIR}/startup_pipeline.sh
RemainAfterExit=yes

[Install]
WantedBy=graphical.target
EOF
sudo cp /tmp/raspiframe-kiosk.service /etc/systemd/system/
rm /tmp/raspiframe-kiosk.service

sudo systemctl daemon-reload
sudo systemctl enable raspiframe.service
sudo systemctl enable raspiframe-kiosk.service

# 6. ディスプレイ設定（オプション）
echo ""
echo "Step 6: Configure display settings..."

# config.txtのパスを判定
if [ -f /boot/firmware/config.txt ]; then
    CONFIG_FILE="/boot/firmware/config.txt"
else
    CONFIG_FILE="/boot/config.txt"
fi

# 画面回転設定
echo ""
echo "Configure display rotation?"
echo "  0 = 0° (landscape)"
echo "  1 = 90° right (portrait)"
echo "  2 = 180° (upside down)"
echo "  3 = 270° right (portrait, left)"
echo "  [Enter] = skip"
read -r rotation
if [[ "$rotation" =~ ^[0-3]$ ]]; then
    sudo sed -i '/display_hdmi_rotate/d' "$CONFIG_FILE"
    echo "display_hdmi_rotate=$rotation" | sudo tee -a "$CONFIG_FILE" > /dev/null
    echo "✓ Display rotation set to $rotation"
fi

# HDMI強制検出（ディスプレイなしでも起動）
echo ""
echo "Force HDMI hotplug detection? (recommended for photo frames) (y/n)"
read -r response
if [[ "$response" =~ ^[Yy]$ ]]; then
    sudo sed -i '/hdmi_force_hotplug/d' "$CONFIG_FILE"
    echo "hdmi_force_hotplug=1" | sudo tee -a "$CONFIG_FILE" > /dev/null
    echo "✓ HDMI force hotplug enabled"
fi

# オーバースキャン無効化（画面いっぱいに表示）
if ! grep -q "^disable_overscan=1" "$CONFIG_FILE"; then
    echo ""
    echo "Disable overscan? (recommended - prevents black borders) (y/n)"
    read -r response
    if [[ "$response" =~ ^[Yy]$ ]]; then
        sudo sed -i '/disable_overscan/d' "$CONFIG_FILE"
        echo "disable_overscan=1" | sudo tee -a "$CONFIG_FILE" > /dev/null
        echo "✓ Overscan disabled"
    fi
fi

echo "Display configuration complete (reboot required to apply)"

# 7. 自動ログイン設定（オプション）
echo ""
echo "Step 7: Configure auto-login? (y/n)"
read -r response
if [[ "$response" =~ ^[Yy]$ ]]; then
    sudo raspi-config nonint do_boot_behaviour B4
    echo "Auto-login to desktop enabled"
fi

# 8. USB自動マウント設定
echo ""
echo "Step 8: Setting up USB auto-mount..."
sudo cp usb-mount.sh /usr/local/bin/
sudo cp usb-unmount.sh /usr/local/bin/
sudo chmod +x /usr/local/bin/usb-mount.sh
sudo chmod +x /usr/local/bin/usb-unmount.sh
sudo cp 99-usb-mount.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules
sudo udevadm trigger

# 9. スクリーンセーバー・通知の無効化
echo ""
echo "Step 9: Disabling screensaver and notifications..."
mkdir -p ~/.config/lxsession/LXDE-pi
cat > ~/.config/lxsession/LXDE-pi/autostart << 'EOF'
@lxpanel --profile LXDE-pi
@pcmanfm --desktop --profile LXDE-pi
@xscreensaver -no-splash
@point-rpi
@xset s off
@xset -dpms
@xset s noblank
@unclutter -idle 0.1 -root
EOF

# 通知サービスを無効化
echo "Disabling notification daemon..."
mkdir -p ~/.config/lxsession/LXDE-pi
cat > ~/.config/lxsession/LXDE-pi/desktop.conf << 'EOF'
[Session]
window_manager=openbox-lxde-pi
disable_autostart=no

[GTK]
sNet/ThemeName=PiXflat
sNet/IconThemeName=PiXflat
sGtk/FontName=PibotoLt 12
iGtk/ToolbarStyle=3
iGtk/ButtonImages=1
iGtk/MenuImages=1
iGtk/CursorThemeSize=24
iXft/Antialias=1
iXft/Hinting=1
sXft/HintStyle=hintslight
sXft/RGBA=rgb

[Mouse]
AccFactor=20
AccThreshold=10
Lefthanded=0

[Keyboard]
Delay=500
Interval=30
Beep=1

[State]
guess_default=true

[Dbus]
lxde-pi/SessionManager=true

[Environment]
menu_prefix=lxde-pi-
EOF

# 通知デーモンのプロセスをキル（必要に応じて）
killall notification-daemon 2>/dev/null || true
killall notify-osd 2>/dev/null || true

# WiFi再接続ポップアップを無効化（lxplug-network）
echo "Disabling WiFi popup notifications..."
mkdir -p ~/.config/lxpanel/LXDE-pi/panels
if [ -f ~/.config/lxpanel/LXDE-pi/panels/panel ]; then
  # lxplug-networkを無効化
  sed -i 's/^Plugin {$/&\n  type = dhcpcdui\n  Config {\n    HideIfNoWireless=1\n  }\n}/g' ~/.config/lxpanel/LXDE-pi/panels/panel 2>/dev/null || true
fi

# dhcpcd-gtkを無効化（WiFiアイコンのポップアップを無効）
sudo systemctl disable dhcpcd-gtk 2>/dev/null || true
killall dhcpcd-gtk 2>/dev/null || true

# NetworkManagerのポップアップも無効化
gsettings set org.gnome.nm-applet disable-disconnected-notifications true 2>/dev/null || true
gsettings set org.gnome.nm-applet disable-connected-notifications true 2>/dev/null || true


# 10. 起動後のディスプレイ回転・解像度制御設定
echo ""
echo "Step 10: Configure display auto-rotation for labwc..."

AUTOSTART_DIR="$HOME/.config/labwc/autostart"

mkdir -p "$AUTOSTART_DIR"

cat > "$AUTOSTART_DIR/rotate-portrait.sh" << 'EOF'
#!/usr/bin/env bash

set -e

LOG="$HOME/.local/share/raspiframe-rotate.log"
mkdir -p "$(dirname "$LOG")"
echo "==== $(date) rotate start ====" >>"$LOG"

# GUI（labwc）が立ち上がり切るのを少し待つ
sleep 2

# Wayland ソケットを自動検出
export XDG_RUNTIME_DIR="/run/user/$(id -u)"
WAY_SOCK="$(ls "$XDG_RUNTIME_DIR"/wayland-* 2>/dev/null | head -n1 || true)"
if [ -n "$WAY_SOCK" ]; then
    export WAYLAND_DISPLAY="$(basename "$WAY_SOCK")"
fi
echo "ENV WAYLAND_DISPLAY=$WAYLAND_DISPLAY XDG_RUNTIME_DIR=$XDG_RUNTIME_DIR" >>"$LOG"

# 解像度優先順位
MODE1="1024x600"
MODE2="1280x720"

if command -v wlr-randr >/dev/null 2>&1; then
    # 接続されてる出力名を1つ取得（例: HDMI-A-1）
    OUT="$(wlr-randr | awk '/ connected/{print $1; exit}')"
    [ -z "$OUT" ] && OUT="HDMI-A-1"

    echo "[wayland] out=$OUT" >>"$LOG"

    # ① 1024x600 + 左90°
    if wlr-randr --output "$OUT" --mode "$MODE1" --transform 90; then
        echo "[wayland] set $MODE1 & rotated 90°" >>"$LOG"

    # ② ダメなら 1280x720 + 左90°
    elif wlr-randr --output "$OUT" --mode "$MODE2" --transform 90; then
        echo "[wayland] fallback: $MODE2 & rotated 90°" >>"$LOG"

    # ③ それもダメなら回転だけ
    elif wlr-randr --output "$OUT" --transform 90; then
        echo "[wayland] fallback: rotated 90° only" >>"$LOG"

    else
        echo "[wayland] all wlr-randr attempts failed" >>"$LOG"
    fi
else
    echo "[wayland] wlr-randr not found" >>"$LOG"
fi

exit 0
EOF

chmod +x "$AUTOSTART_DIR/rotate-portrait.sh"
echo "  - Created $AUTOSTART_DIR/rotate-portrait.sh (left 90°, 1024x600→1280x720 fallback)"


echo ""
echo "========================================="
echo "Setup complete!"
echo "========================================="
echo ""
echo "USB Preparation:"
echo "1. Create credentials.txt (see credentials.txt.sample)"
echo "2. Create wifi.txt (see wifi.txt.sample)"
echo "3. Optionally create Photo/ folder with images"
echo ""
echo "Next steps:"
echo "1. Insert prepared USB drive"
echo "2. Reboot: sudo reboot"
echo "   or"
echo "3. Start services manually:"
echo "   sudo systemctl start raspiframe"
echo "   sudo systemctl start raspiframe-kiosk"
echo ""
echo "Check status:"
echo "  sudo systemctl status raspiframe"
echo "  sudo systemctl status raspiframe-kiosk"
echo "  tail -f /var/log/raspiframe_startup.log"
echo ""

