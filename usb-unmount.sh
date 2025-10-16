#!/bin/bash
# USBメモリをアンマウントするスクリプト

MOUNT_POINT="/mnt/usb"

# マウントされている場合のみアンマウント
if mountpoint -q "$MOUNT_POINT"; then
    umount "$MOUNT_POINT"
    logger "USB device unmounted from $MOUNT_POINT"
fi

