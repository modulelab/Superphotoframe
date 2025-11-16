# SuperPhotoframe - デジタルフォトフレーム
SuperPhotoframeはRaspberry Pi ベースの高速・安定・ミニマルを追求したデジタルフォトフレーム。  
IoTプロダクトでありがちな接続切れや認証エラーのストレスを排除、エディトリアルのような美しいレイアウトの写真を日常に溶け込ませ、静かな写真体験を提供します。  

世界中で調達可能な汎用部品だけで低コストでDIYが可能です(≒ $2~300)    
※資材詳細はbuild guideを参照


## ライセンス
このプロジェクトは **CC BY-NC 4.0**（Creative Commons Attribution-NonCommercial 4.0 International）ライセンスの下で公開されています。

- ✅ 個人利用、改変・再配布OK（非営利目的）での使用は自由
- ✅ クレジット表示が必要
- ❌ 商用利用は禁止
詳細: https://creativecommons.org/licenses/by-nc/4.0/

**© 2025 MODULE LAB** — Open Source under CC BY-NC 4.0  
github.com/modulelab/Superphotoframe  
商用利用をご希望の場合は、作者までお問い合わせください。  
  
## システム要件

- **ハードウェア**: Raspberry Pi 4（推奨: 4GB以上）
- **OS**: Raspberry Pi OS Bookworm legasy 64bit（Wayland/labwc）
- **Python**: 3.11 付属（システム）または同等
- **ストレージ**: 32GB以上のmicroSDカード
- **ネットワーク**: WiFi

## 主な機能

### 💡 想定ユースケース
- リビングやキッチンに静かに写真を流したい人
- 店舗のサイネージ代わりのミニマルなフォトフレーム用途
- NAS・USB・クラウドの写真を日常で自然に楽しみたい人

### 📸 写真表示
- 自動スライドショー
- フェードイン/アウト効果
- Ken Burns効果（ズーム）
- キャプション表示（機種名・日付）
- 日付スクラブ機能(ロータリーエンコーダー)
- ネイティブ解像度表示<small>（1024×600 など、Wayland上で `wlr-randr` により設定）</small>

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
#### 1-1.RaspberryPi OSのダウンロード
```bash
https://downloads.raspberrypi.com/raspios_oldstable_arm64/images/raspios_oldstable_arm64-2025-10-02/2025-10-01-raspios-bookworm-arm64.img.xz
```

#### 1-2. Raspberry Pi Imager でOSをSDカードに書き込む
  - RaspberryPiデバイスはPi4を選択
  - OSでUSE custom Image > １でダウンロードしたimgを選択
  - 書き込み先のSDを選択  
  
#### 1-3. 「設定を編集する」
   - Host名：raspiframe
   - User:jd 
   - Password:任意
   - Wi-Fi SSID・パスワード
   サービスタブへ移動
   - SSH 有効化にチェック（パスワード認証）  
     

#### 1-4. SD カードへ書き込み完了後、安全に取り外す。  


<br>

### 2. メディア／ネットワーク準備
- USBメモリをfat32,exFATでフォーマット
- USB メモリに `wifi.txt`, `credentials.txt`, 「Photo」フォルダ を配置。  
  <small>※USB.zipにテンプレートがあるため、これを解凍しそのままUSBの1階層目に配置ください。</small>
- 「Photo」フォルダに写真をフォルダ分けして格納、20xx、など年度のフォルダ分け推奨  
　 <small>※格納する写真は長辺1500px程度にリサイズください。写真が大きいと動作が重くなることがあります。</small>
- 以降写真を追加したい場合適宜追加可能。
- NAS / DLNA を利用する場合のみ `credentials.txt` に認証情報を設定。  
<small>適宜Nas設定からDLNAアクセス用のユーザーを作るなどし情報を入力してください。</small>

<br>

### 3. 本体の組み立て
 - build guideを見て筐体を組み立ててください。
 - １で作ったSDを挿入。USBメモリを差し込み（ブルーのポート）

<br>

### 4. SuperPhotoframeのインストール
 - PCのターミナルからSSH接続を行い、ターミナルからPi4を操作、必要なソフトウェアを導入します。
 - ターミナルで以下を入力し実行、SSH接続するPi4のIPを特定します（IPは「192.168.xx.xx」のような形式)
<br>
```bash
 ping raspiframe.local
```
 - 以下をターミナルで実行、特定したIPに対してSSH接続を行います。
```bash
ssh jd@192.168.xx.xx
```
<br>
SSH接続できた状態で以下を順に実行していきます。  
<small>※ターミナルでユーザー名、コマンド入力蘭が出ている状態が次のコマンドを実行できる状態です。</small>
<br>
```bash
sudo apt install -y git python3 python3-venv python3-pip
```

```bash
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs
```

```bash
sudo reboot
```
<br>
#再起動を待ってGUIのデスクトップが表示されたら再度SSH接続する
<br>
```bash
cd ~
git clone https://github.com/modulelab/Superphotoframe.git
cd Superphotoframe
git checkout v1.0.0
```

```bash
python3 -m venv ~/raspiframe-venv
source ~/raspiframe-venv/bin/activate
pip install -r requirements.txt
```

```bash
chmod +x setup_dlna.sh
./setup_dlna.sh
```
<br>
上記実行中にコマンドラインに質問が表示されます。以下のように回答。  
- Install rotary encoder service? (y/n) :y enter
- Configure display rotation? :enter(skip)
- Force HDMI hotplug detection? (recommended for photo frames) (y/n): y enter
- Configure auto-login? (y/n) :y enter
<br>

```bash
sudo raspi-config
```
- PCのBIOSのような設定画面が立ち上がります。system setting > s7 splash screen に進み「no」を選択後 > 「finish」へ進む  
※カーソルキーでメニューを移動してenterで確定
<br>
```bash
sudo reboot
```
これで全て完了です🎉  
<br>
- 起動後表示されるQRコードをスマホで読み込み、設定画面に入ります。
- 設定画面から表示したいフォルダを選択、保存。スライドショーが始まります。
- 必要に応じてマージン、１枚の秒数など表示設定を行なって保存してください。

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

```bash
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

