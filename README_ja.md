# Raspiframe - デジタルフォトフレーム

Raspberry Piベースのデジタルフォトフレームシステム

## システム要件

- **ハードウェア**: Raspberry Pi 3/4/5
- **OS**: Raspberry Pi OS (Debian 11 Bullseye以降推奨)
- **Python**: 3.9以上
- **ディスプレイ**: HDMI接続可能なモニター
- **ストレージ**: 8GB以上のmicroSDカード
- **ネットワーク**: WiFiまたは有線LAN

## 主な機能

### 📸 写真表示
- 自動スライドショー
- フェードイン/アウト効果
- Ken Burns効果（ズーム）
- EXIF情報表示（カメラ機種、日付、露出）
- 日付スクラブ機能

### 🌐 ネットワーク機能
- **DLNA/SMB自動検出とマウント**
- **USBメモリからのWIFI自動設定**
- Web設定画面
- QRコード経由の簡単アクセス

### 💾 写真ソース
1. **USBメモリ** - `Photo/`フォルダから直接読み込み
2. **NAS/DLNA** - ネットワーク上のメディアサーバー
3. **ローカルストレージ** - 固定パス

### 🎮 操作方法
- ロータリーエンコーダー（回転/押し込み）
- キーボード（矢印キー、スペース）
- Webインターフェース

## セットアップ

### 0. リポジトリのクローン

```bash
# SSHまたはHTTPSでクローン
git clone https://github.com/modulelab/Superphotoframe.git
cd Superphotoframe
```

### 1. セットアップスクリプトの実行

```bash
chmod +x setup_dlna.sh
./setup_dlna.sh
```

このスクリプトは以下を実行します：
- 必要なシステムパッケージのインストール（avahi-utils, cifs-utils, chromium-browser等）
- Pythonライブラリのインストール（`requirements.txt`から）
- USB自動マウント設定（udevルール）
- systemdサービスの登録と自動起動設定
- スクリーンセーバーの無効化

### 2. USBメモリの準備

**重要**: セットアップ後、USBメモリは自動的に`/mnt/usb`にマウントされます（ユーザー名非依存）

USBメモリのルートに以下のファイルを作成：

#### `wifi.txt` - WiFi設定（必須）
```
ssid=YourWiFiNetworkName
password=YourWiFiPassword
country=JP
```

#### `credentials.txt` - NAS認証情報（NAS使用時のみ）
```
username=your_nas_username
password=your_nas_password
```

#### `Photo/` - 写真フォルダ（オプション）
USBメモリに直接写真を保存する場合は`Photo`フォルダを作成して画像を配置

### 3. 起動

```bash
# 再起動（推奨）
sudo reboot

# または手動起動
sudo systemctl start raspiframe
sudo systemctl start raspiframe-kiosk
```

## 起動シーケンス

1. **WiFi設定** - USBから`wifi.txt`を読み込み、自動接続
2. **サービス起動** - Raspiframeバックエンドが起動
3. **QR生成** - 設定画面へのQRコードを生成
4. **Kioskモード** - Chromiumで全画面表示

## 使い方

### 初回セットアップ
1. USBメモリを準備（wifi.txt必須）
2. Raspberry Piに挿入して起動
3. WiFi接続後、QRコードが表示される
4. スマホでQRを読み取り、設定画面を開く

### NASからの写真読み込み
1. 設定画面で「ENABLE NAS/DLNA」をチェック
2. 「DISCOVER」ボタンでNASを検出
3. 検出されたNASを選択して「MOUNT」
4. 共有フォルダ名を入力（例：`photo_resized`）
5. フォルダを選択して「Add This Folder」
6. 「Save」で保存

### USBメモリからの写真読み込み
1. USBメモリに`Photo/`フォルダを作成
2. 写真を配置
3. 設定画面で「CHECK USB PHOTO」をクリック
4. 「ADD TO SELECTION」で追加
5. 「Save」で保存

### 表示設定
- **Display (ms)**: 各写真の表示時間
- **Fade (ms)**: フェード効果の時間
- **Margin %**: 画面の余白
- **Ken Burns**: ズーム効果のON/OFF
- **Caption**: EXIF情報表示のON/OFF
- **Timezone**: タイムゾーン設定

## 操作方法

### キーボード
- `←/→` - 前/次の写真
- `Space` - 一時停止/再生
- `O` - 日付オーバーレイ表示

### ロータリーエンコーダー
- 回転（左/右） - 日付単位でスクラブ
- 押し込み - QRコード表示

## API仕様

### DLNA関連
- `GET /api/dlna/discover` - DLNAサービス検出
- `GET /api/dlna/status` - マウント状態確認
- `POST /api/dlna/mount` - マウント実行
- `POST /api/dlna/unmount` - アンマウント

### USB関連
- `GET /api/usb/photo` - USBフォトフォルダ情報

### 設定関連
- `GET /api/config` - 設定取得
- `POST /api/config` - 設定保存
- `GET /api/selection` - 選択フォルダ取得
- `POST /api/selection` - 選択フォルダ保存

### プレイリスト
- `GET /api/playlist` - 画像一覧取得
- `GET /api/events` - SSEイベントストリーム

## ファイル構成

```
raspiframe/
├── app/
│   └── main.py              # メインアプリケーション
├── static/
│   ├── player.html          # プレイヤー画面
│   ├── settings.html        # 設定画面
│   ├── logo.png             # ロゴ画像
│   ├── settinglogo.png      # 設定画面ロゴ
│   └── qr2.png             # QRコード（自動生成）
├── data/
│   ├── config.json.sample  # 設定ファイルサンプル
│   └── selection.json.sample # 選択フォルダサンプル
├── rotary.py               # ロータリーエンコーダー
├── setup_dlna.sh           # セットアップスクリプト
├── setup_wifi_from_usb.py  # WiFi設定スクリプト
├── startup_pipeline.sh     # 起動パイプライン
├── usb-mount.sh            # USB自動マウントスクリプト
├── usb-unmount.sh          # USB自動アンマウントスクリプト
├── 99-usb-mount.rules      # udevルール
├── requirements.txt        # Python依存パッケージ
├── wifi.txt.sample         # WiFi設定サンプル
├── credentials.txt.sample  # 認証情報サンプル
└── README.md               # このファイル
```

**注意**: 
- `raspiframe.service`と`raspiframe-kiosk.service`は`setup_dlna.sh`によって自動生成されます
- `data/config.json`と`data/selection.json`は初回起動時に自動生成されます

## トラブルシューティング

### WiFi接続できない
```bash
# ログ確認
tail -f /var/log/raspiframe_startup.log

# 手動設定
sudo python3 setup_wifi_from_usb.py
```

### NASマウント失敗
```bash
# サービスログ確認
sudo journalctl -u raspiframe -f

# credentials.txtの確認
cat /media/usb/credentials.txt

# 手動マウントテスト
sudo mount -t cifs //192.168.1.100/share /mnt/dlna/test \
  -o username=user,password=pass
```

### 画面が表示されない
```bash
# Kioskサービス確認
sudo systemctl status raspiframe-kiosk

# Chromiumプロセス確認
ps aux | grep chromium

# 手動起動
DISPLAY=:0 chromium-browser --kiosk http://localhost:8000/static/player.html
```

### QRコードが表示されない
```bash
# QRファイル確認
ls -la /home/jd/raspiframe/static/qr2.png

# サービス再起動
sudo systemctl restart raspiframe
```

## セキュリティに関する注意

⚠️ **重要**: 
- `wifi.txt`と`credentials.txt`は平文で保存されます
- USBメモリは物理的に安全に保管してください
- 本番環境では暗号化を検討してください
- 使用後はUSBメモリを取り外すことを推奨します

## ライセンス

このプロジェクトは **CC BY-NC 4.0**（Creative Commons Attribution-NonCommercial 4.0 International）ライセンスの下で公開されています。

- ✅ 個人・家族での使用は自由
- ✅ 改変・再配布OK（非営利目的）
- ✅ クレジット表示が必要
- ❌ 商用利用は禁止

詳細: https://creativecommons.org/licenses/by-nc/4.0/

商用利用をご希望の場合は、作者までお問い合わせください。

## 作者

**MODULE LAB** (github.com/modulelab/Superphotoframe)

©2025 MODULE LAB Open Source

## 更新履歴

### v2.0 (2025-10)
- DLNA自動検出機能追加
- USBからのWiFi設定機能追加
- USBフォトフォルダ機能追加
- NAS ON/OFF機能追加
- 起動パイプライン実装

### v1.0
- 初期リリース

