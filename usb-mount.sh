#!/bin/bash
# USBメモリを /mnt/usb にマウントするスクリプト

DEVICE="/dev/$1"
MOUNT_POINT="/mnt/usb"

# マウントポイントを作成
mkdir -p "$MOUNT_POINT"

# 既にマウントされている場合はスキップ
if mountpoint -q "$MOUNT_POINT"; then
    exit 0
fi

# ファイルシステムタイプを検出
FS_TYPE=$(blkid -o value -s TYPE "$DEVICE" 2>/dev/null)

# マウント（ファイルシステムに応じてオプション変更）
case "$FS_TYPE" in
    vfat|exfat)
        mount -t "$FS_TYPE" -o rw,uid=1000,gid=1000,umask=0000 "$DEVICE" "$MOUNT_POINT"
        ;;
    ntfs)
        mount -t ntfs-3g -o rw,uid=1000,gid=1000,umask=0000 "$DEVICE" "$MOUNT_POINT"
        ;;
    ext*)
        mount -t "$FS_TYPE" -o rw "$DEVICE" "$MOUNT_POINT"
        ;;
    *)
        mount "$DEVICE" "$MOUNT_POINT"
        ;;
esac

# 成功したらログ
if mountpoint -q "$MOUNT_POINT"; then
    logger "USB device $DEVICE mounted at $MOUNT_POINT (type: $FS_TYPE)"
fi

