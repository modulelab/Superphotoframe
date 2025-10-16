# DLNA自動検出機能 セットアップガイド

## 概要
Raspiframeは、ネットワーク上のDLNA/SMBサーバーを自動検出してマウントする機能を搭載しています。

## 必要なもの
1. Raspberry Pi（Raspbian/Raspberry Pi OS）
2. DLNA/SMBサーバー（NAS等）
3. USBメモリ（認証情報を保存）

## セットアップ手順

### 1. システムのセットアップ
```bash
cd /home/jd/raspiframe
./setup_dlna.sh
```

このスクリプトは以下を実行します：
- `avahi-utils`と`cifs-utils`のインストール
- `/mnt/dlna`ディレクトリの作成
- systemdサービスの登録

### 2. USB認証情報ファイルの作成

USBメモリのルートに`credentials.txt`を作成：

```
username=your_nas_username
password=your_nas_password
```

**重要**: 
- ファイル名は正確に`credentials.txt`にしてください
- フォーマットは`key=value`（1行1項目）
- `#`で始まる行はコメントとして無視されます

### 3. サービスの起動

```bash
sudo systemctl start raspiframe
sudo systemctl status raspiframe
```

### 4. DLNA検出とマウント

1. ブラウザで設定画面を開く：`http://<raspberry-pi-ip>:8000`
2. 「DISCOVER DLNA」ボタンをクリック
3. 検出されたサービス一覧から選択して「MOUNT」
4. 共有フォルダ名を入力（例：`photo_resized`）
5. マウント成功後、フォルダを選択して写真を追加

## 自動マウント機能

一度マウントに成功すると、次回起動時に自動的にマウントされます：
- USBメモリに`credentials.txt`が必要
- `config.json`に設定が保存される
- 起動時に自動マウント実行

## トラブルシューティング

### DLNAサービスが検出されない
- NASとRaspberry Piが同じネットワークにあるか確認
- avahi-daemonが動作しているか確認：`sudo systemctl status avahi-daemon`
- NASでSMB/CIFS共有が有効になっているか確認

### マウントに失敗する
- credentials.txtの内容が正しいか確認
- 共有フォルダ名が正しいか確認
- ログを確認：`sudo journalctl -u raspiframe -f`

### 権限エラー
- サービスがroot権限で実行されているか確認
- `/mnt/dlna`の権限を確認：`ls -la /mnt/dlna`

## API仕様

### DLNA検出
```
GET /api/dlna/discover
Response: {"services": [{"name": "MyNAS", "address": "192.168.1.100"}]}
```

### マウント
```
POST /api/dlna/mount
Body: {"address": "192.168.1.100", "name": "MyNAS", "share": "photo_resized"}
Response: {"success": true, "mount_point": "/mnt/dlna/MyNAS"}
```

### アンマウント
```
POST /api/dlna/unmount
Response: {"success": true}
```

### 状態確認
```
GET /api/dlna/status
Response: {
  "enabled": true,
  "mounted": true,
  "address": "192.168.1.100",
  "name": "MyNAS",
  "mount_point": "/mnt/dlna/MyNAS"
}
```

## セキュリティについて

⚠️ **注意**: credentials.txtは平文で保存されます。
- USBメモリは物理的に安全に保管してください
- 本番環境では暗号化を検討してください
- 使用後はUSBメモリを取り外すことを推奨します

## 設定ファイル（config.json）

DLNA設定は`data/config.json`に保存されます：

```json
{
  "dlna": {
    "enabled": true,
    "address": "192.168.1.100",
    "name": "MyNAS",
    "share": "photo_resized",
    "mount_point": "/mnt/dlna/MyNAS",
    "auto_mount": true
  }
}
```

