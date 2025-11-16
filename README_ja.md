# SuperPhotoframe - デジタルフォトフレーム

Raspberry Pi ベースのシンプルで高速なデジタルフォトフレーム

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

## システム要件

- **ハードウェア**: Raspberry Pi 4/5（推奨: 4GB以上）
- **OS**: Raspberry Pi OS Bookworm legasy 64bit（Wayland/labwc）
- **Python**: 3.11 付属（システム）または同等
- **ストレージ**: 32GB以上のmicroSDカード
- **ネットワーク**: WiFi

## 主な機能

### 📸 写真表示
- 自動スライドショー
- フェードイン/アウト効果
- Ken Burns効果（ズーム）
- キャプション表示（機種名・日付）
- 日付スクラブ機能(ロータリーエンコーダー)
- ネイティブ解像度表示（1024×600 など、Wayland上で `wlr-randr` により設定）

### 🌐 ネットワーク機能
- **DLNA/SMB 自動検出とマウント**
- **USBメモリからの Wi‑Fi 自動設定**
- Web設定画面
- QRコード経由の設定画面アクセス

### 💾 写真ソース
1. **USBメモリ** - `Photo/`フォルダから直接読み込み
2. **NAS/DLNA** - ネットワーク上のメディアサーバー

### 🎮 操作方法
- ロータリーエンコーダー（回転/押し込み）
- ハプティックフィードバック（DRV2605L／I2C）

## セットアップ

### 1. OS イメージの準備
#### 1.RaspberryPi OSのダウンロード
```bash
https://downloads.raspberrypi.com/raspios_oldstable_arm64/images/raspios_oldstable_arm64-2025-10-02/2025-10-01-raspios-bookworm-arm64.img.xz
```

#### 2. Raspberry Pi Imager でOSをSDカードに書き込む
 　- RaspberryPiデバイス：Pi4
  - OS:USE custom Image、１でダウンロードしたimgを選択
  - 書き込み先のSDを選択

#### 3. 「設定を編集する」
   - ホスト名：raspiframe
   - user:jd pass:任意
   - Wi-Fi SSID・パスワード
   -サービスタブへ移動
   - SSH 有効化（パスワード認証）
#### 4. SD カードへ書き込み完了後、安全に取り外す。

### 2. メディア／ネットワーク準備
- USBメモリをfat32,exFATでフォーマット
- USB メモリに `wifi.txt`, `credentials.txt`, 「Photo」フォルダ を配置。
- 「Photo」フォルダに写真をフォルダ分けして格納、20xx、など年度のフォルダ分け推奨
　　※格納する写真は長辺1500px程度にリサイズください。
- NAS / DLNA を利用する場合は `credentials.txt` に認証情報を設定。


## 起動シーケンス

1. **WiFi設定** - USBから`wifi.txt`を読み込み、自動接続
2. **サービス起動** - バックエンド/API が起動（uvicorn）
3. **表示設定** - Wayland上で 1024×600/縦回転 を適用（wlr-randr）
4. **Kioskモード** - Chromium が `static/start.html` を全画面表示
5. **プレーヤー** - `static/player.html` に遷移してスライド開始


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
Superphotoframe/
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
└── README_ja.md            # このファイル
```


## セキュリティに関する注意

⚠️ **重要**: 
- `wifi.txt`と`credentials.txt`は平文で保存されます
-  ゲスト用ネットワークなどの利用をお勧めします

## 更新履歴
### v1.0.0 / v1.0.0-dev.1
- Wayland/labwc 環境に最適化、1024×600 ネイティブ表示
- Chromium 翻訳パネルの恒久無効化
- ロータリー回転・押下および DRV2605L ハプティック対応
- セットアップの一括自動化（仮想環境・systemd・I2C）

