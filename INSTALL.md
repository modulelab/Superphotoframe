# インストールクイックガイド

新しいRaspberry Piへのインストール手順

## 📋 前提条件

- Raspberry Pi 3/4/5
- Raspberry Pi OS (Debian 11 Bullseye以降)
- インターネット接続（初回セットアップ時）
- USBメモリ

## 🚀 インストール手順

### 1. リポジトリをクローン

```bash
git clone https://github.com/your-username/raspiframe.git
cd raspiframe
```

### 2. セットアップスクリプトを実行

```bash
chmod +x setup_dlna.sh
./setup_dlna.sh
```

**対話式で以下を設定：**
- 画面回転（0=横向き、1=縦向き右、2=上下逆、3=縦向き左）
- HDMI強制検出（推奨: y）
- オーバースキャン無効化（推奨: y）
- 自動ログイン（推奨: y）

### 3. USBメモリを準備

USBメモリのルートに以下のファイルを作成：

#### `wifi.txt`（必須）
```
ssid=YourWiFiNetworkName
password=YourWiFiPassword
country=JP
```

#### `credentials.txt`（NAS使用時のみ）
```
username=your_nas_username
password=your_nas_password
```

#### `Photo/`（オプション）
USBに直接写真を保存する場合はこのフォルダを作成

### 4. リブート

```bash
sudo reboot
```

## ✅ 動作確認

リブート後：
1. WiFiに自動接続される
2. 画面にQRコードが表示される
3. スマホでQRを読み取り、設定画面を開く
4. フォルダを選択して保存

## 🔧 トラブルシューティング

### サービス状態確認
```bash
sudo systemctl status raspiframe
sudo systemctl status raspiframe-kiosk
```

### ログ確認
```bash
# 起動ログ
tail -50 /var/log/raspiframe_startup.log

# サービスログ
sudo journalctl -u raspiframe -n 50
sudo journalctl -u raspiframe-kiosk -n 50
```

### USB確認
```bash
# USBマウント確認
ls -la /mnt/usb

# WiFi設定確認
cat /mnt/usb/wifi.txt
```

### NASマウント確認
```bash
# マウント状態確認
mount | grep dlna

# 手動マウントテスト
sudo mount -t cifs //192.168.1.100/share /mnt/dlna/test \
  -o username=user,password=pass
```

## 📞 サポート

問題が発生した場合は、以下の情報を添えてIssueを作成してください：
- Raspberry Piのモデル
- Raspberry Pi OSのバージョン（`cat /etc/os-release`）
- エラーログ

