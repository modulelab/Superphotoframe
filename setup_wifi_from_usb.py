#!/usr/bin/env python3
"""
USBメモリからWIFI設定を読み込んで接続するスクリプト

wifi.txtフォーマット:
ssid=MyWiFiNetwork
password=MyPassword123
country=JP
"""

import os
import sys
import subprocess
import time
from pathlib import Path

# USBマウントポイント候補
USB_MOUNT_POINTS = ["/media/usb", "/mnt/usb", "/media/pi"]
WIFI_CONFIG_FILE = "wifi.txt"

def find_usb_mount():
    """USBメモリのマウントポイントを検出"""
    for mount_point in USB_MOUNT_POINTS:
        if os.path.exists(mount_point) and os.path.isdir(mount_point):
            try:
                if os.listdir(mount_point):
                    return mount_point
            except Exception:
                continue
    return None

def load_wifi_config(usb_path):
    """USBからwifi.txtを読み込み"""
    wifi_file = os.path.join(usb_path, WIFI_CONFIG_FILE)
    
    if not os.path.exists(wifi_file):
        return None
    
    config = {}
    try:
        with open(wifi_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if '=' in line and not line.startswith('#'):
                    key, val = line.split('=', 1)
                    config[key.strip().lower()] = val.strip()
        
        # 必須項目チェック
        if 'ssid' in config and 'password' in config:
            if 'country' not in config:
                config['country'] = 'JP'  # デフォルト
            return config
    except Exception as e:
        print(f"Error reading wifi.txt: {e}", file=sys.stderr)
    
    return None

def configure_wifi(ssid, password, country='JP'):
    """wpa_supplicant.confを設定してWIFI接続"""
    
    # 1. 国コード設定
    try:
        subprocess.run(['sudo', 'raspi-config', 'nonint', 'do_wifi_country', country], 
                      check=True, capture_output=True)
        print(f"Set WiFi country to {country}")
    except Exception as e:
        print(f"Warning: Failed to set country code: {e}", file=sys.stderr)
    
    # 2. wpa_supplicant.conf生成
    wpa_conf = f'''country={country}
ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1

network={{
    ssid="{ssid}"
    psk="{password}"
    key_mgmt=WPA-PSK
}}
'''
    
    conf_path = '/etc/wpa_supplicant/wpa_supplicant.conf'
    
    try:
        # 既存の設定をバックアップ
        if os.path.exists(conf_path):
            subprocess.run(['sudo', 'cp', conf_path, f'{conf_path}.bak'], check=True)
        
        # 新しい設定を書き込み
        with open('/tmp/wpa_supplicant.conf', 'w') as f:
            f.write(wpa_conf)
        
        subprocess.run(['sudo', 'mv', '/tmp/wpa_supplicant.conf', conf_path], check=True)
        subprocess.run(['sudo', 'chmod', '600', conf_path], check=True)
        
        print(f"WiFi configuration written to {conf_path}")
        
        # 3. wpa_supplicantを再起動
        subprocess.run(['sudo', 'wpa_cli', '-i', 'wlan0', 'reconfigure'], check=True)
        print("WiFi reconfigured")
        
        # 4. 接続待機（最大30秒）
        print("Waiting for WiFi connection...", end='', flush=True)
        for i in range(30):
            try:
                result = subprocess.run(['iwgetid', '-r'], 
                                      capture_output=True, 
                                      text=True, 
                                      timeout=2)
                if result.returncode == 0 and result.stdout.strip() == ssid:
                    print(f"\nConnected to {ssid}!")
                    return True
            except Exception:
                pass
            
            print('.', end='', flush=True)
            time.sleep(1)
        
        print("\nConnection timeout")
        return False
        
    except Exception as e:
        print(f"Error configuring WiFi: {e}", file=sys.stderr)
        return False

def main():
    print("=" * 60)
    print("WiFi Setup from USB")
    print("=" * 60)
    
    # USBメモリを検出
    print("\nSearching for USB drive...")
    usb_path = find_usb_mount()
    
    if not usb_path:
        print("ERROR: No USB drive found")
        print("Please insert USB drive with wifi.txt")
        sys.exit(1)
    
    print(f"Found USB drive: {usb_path}")
    
    # wifi.txtを読み込み
    print(f"\nReading {WIFI_CONFIG_FILE}...")
    wifi_config = load_wifi_config(usb_path)
    
    if not wifi_config:
        print(f"ERROR: {WIFI_CONFIG_FILE} not found or invalid")
        print(f"Please create {WIFI_CONFIG_FILE} in USB root with:")
        print("  ssid=YourNetworkName")
        print("  password=YourPassword")
        print("  country=JP")
        sys.exit(1)
    
    ssid = wifi_config['ssid']
    password = wifi_config['password']
    country = wifi_config.get('country', 'JP')
    
    print(f"SSID: {ssid}")
    print(f"Password: {'*' * len(password)}")
    print(f"Country: {country}")
    
    # WiFi設定
    print("\nConfiguring WiFi...")
    success = configure_wifi(ssid, password, country)
    
    if success:
        print("\n" + "=" * 60)
        print("WiFi setup complete!")
        print("=" * 60)
        sys.exit(0)
    else:
        print("\n" + "=" * 60)
        print("WiFi setup failed")
        print("=" * 60)
        sys.exit(1)

if __name__ == "__main__":
    main()

