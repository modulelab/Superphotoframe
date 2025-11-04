# SuperPhotoframe - Digital Photo Frame

![代替テキスト](https://raw.githubusercontent.com/modulelab/Superphotoframe/refs/heads/main/readme.jpg?token=GHSAT0AAAAAADMPKRYRNXXB37GWPSZ7KN4U2IKEUXQ)

[日本語版はこちら / Japanese version](README_ja.md)

A Raspberry Pi-based digital photo frame system with advanced features.

## System Requirements

- **Hardware**: Raspberry Pi 3/4/5
- **OS**: Raspberry Pi OS (Debian 11 Bullseye or later recommended)
- **Python**: 3.9 or higher
- **Display**: HDMI-compatible monitor
- **Storage**: 8GB+ microSD card
- **Network**: WiFi or Ethernet

## Key Features

### 📸 Photo Display
- Automatic slideshow
- Fade in/out effects
- Ken Burns effect (zoom & pan)
- EXIF information display (camera model, date, exposure)
- Date scrubbing functionality

### 🌐 Network Features
- **DLNA/SMB auto-discovery and mount**
- **USB WiFi auto-configuration**
- Web-based settings interface
- QR code access for easy setup

### 💾 Photo Sources
1. **USB Drive** - Direct loading from `Photo/` folder
2. **NAS/DLNA** - Network media server
3. **Local Storage** - Fixed paths

### 🎮 Control Methods
- Rotary encoder (rotate/push)
- Keyboard (arrow keys, space)
- Web interface

## Setup

### 0. Clone Repository

```bash
git clone https://github.com/tolab125/Superphotoframe.git
cd Superphotoframe
```

### 1. Run Setup Script

```bash
chmod +x setup_dlna.sh
./setup_dlna.sh
```

This script will:
- Install required system packages (avahi-utils, cifs-utils, chromium-browser, etc.)
- Install Python libraries (from `requirements.txt`)
- Configure USB auto-mount (udev rules)
- Register and enable systemd services
- Disable screensaver and notifications

Interactive configuration during setup:
- Display rotation (0=landscape, 1=portrait right, 2=upside down, 3=portrait left)
- HDMI force hotplug (recommended: y)
- Disable overscan (recommended: y)
- Auto-login (recommended: y)

### 2. Prepare USB Drive

**Important**: After setup, USB drives will automatically mount to `/mnt/usb` (user-independent)

Create the following files on the USB drive root:

#### `wifi.txt` - WiFi Configuration (Required)
```
ssid=YourWiFiNetworkName
password=YourWiFiPassword
country=JP
```

#### `credentials.txt` - NAS Credentials (NAS use only)
```
username=your_nas_username
password=your_nas_password
```

#### `Photo/` - Photo Folder (Optional)
Create this folder and place images if storing photos directly on USB

### 3. Startup

```bash
# Reboot (recommended)
sudo reboot

# Or manual start
sudo systemctl start raspiframe
sudo systemctl start raspiframe-kiosk
```

## Startup Sequence

1. **WiFi Setup** - Reads `wifi.txt` from USB and auto-connects
2. **Service Start** - Raspiframe backend launches
3. **QR Generation** - Generates QR code for settings page access
4. **Kiosk Mode** - Full-screen display via Chromium

## Usage

### Initial Setup
1. Prepare USB drive (wifi.txt required)
2. Insert into Raspberry Pi and boot
3. After WiFi connection, QR code appears on screen
4. Scan QR code with smartphone to open settings page

### Loading Photos from NAS
1. Check "ENABLE DLNA ON NAS" in settings
2. Click "CHECK DISK" button to discover NAS
3. Select detected NAS and click "MOUNT"
4. Enter shared folder name (e.g., `Multimedia`)
5. Browse and select folders, click "ADD THIS FOLDER"
6. Click "SAVE" to apply

### Loading Photos from USB
1. Create `Photo/` folder on USB drive
2. Place images in folder
3. Click "CHECK USB PHOTO" in settings
4. Folders are automatically detected
5. Click "SAVE" to apply

### Display Settings
- **Display (ms)**: Duration for each photo
- **Fade (ms)**: Fade effect duration
- **Margin %**: Screen margins
- **Ken Burns**: Zoom effect ON/OFF
- **Caption**: EXIF information display ON/OFF
- **Timezone**: Timezone setting

## Controls

### Keyboard
- `←/→` - Previous/Next photo
- `Space` - Pause/Resume
- `O` - Toggle date overlay

### Rotary Encoder
- Rotate (left/right) - Scrub by date
- Push - Display QR code

## API Specification

### DLNA Endpoints
- `GET /api/dlna/discover` - Discover DLNA services
- `GET /api/dlna/status` - Check mount status
- `POST /api/dlna/mount` - Mount share
- `POST /api/dlna/unmount` - Unmount share

### USB Endpoints
- `GET /api/usb/photo` - USB photo folder information

### Settings Endpoints
- `GET /api/config` - Get configuration
- `POST /api/config` - Save configuration
- `GET /api/selection` - Get selected folders
- `POST /api/selection` - Save selected folders

### Playlist
- `GET /api/playlist` - Get image list
- `GET /api/events` - SSE event stream

## File Structure

```
Superphotoframe/
├── app/
│   └── main.py              # Main application
├── static/
│   ├── player.html          # Player screen
│   ├── settings.html        # Settings screen
│   ├── logo.png             # Logo image
│   ├── settinglogo.png      # Settings logo
│   └── qr2.png             # QR code (auto-generated)
├── data/
│   ├── config.json.sample  # Configuration sample
│   └── selection.json.sample # Selection sample
├── rotary.py               # Rotary encoder handler
├── setup_dlna.sh           # Setup script
├── setup_wifi_from_usb.py  # WiFi configuration script
├── startup_pipeline.sh     # Startup pipeline
├── usb-mount.sh            # USB auto-mount script
├── usb-unmount.sh          # USB auto-unmount script
├── 99-usb-mount.rules      # udev rules
├── requirements.txt        # Python dependencies
├── wifi.txt.sample         # WiFi configuration sample
├── credentials.txt.sample  # Credentials sample
└── README.md               # This file
```

**Note**: 
- `raspiframe.service` and `raspiframe-kiosk.service` are auto-generated by `setup_dlna.sh`
- `data/config.json` and `data/selection.json` are auto-generated on first run

## Troubleshooting

### WiFi Connection Failed
```bash
# Check logs
tail -f /var/log/raspiframe_startup.log

# Manual setup
sudo python3 setup_wifi_from_usb.py
```

### NAS Mount Failed
```bash
# Check service logs
sudo journalctl -u raspiframe -f

# Verify credentials
cat /mnt/usb/credentials.txt

# Test manual mount
sudo mount -t cifs //192.168.1.100/share /mnt/dlna/test \
  -o username=user,password=pass
```

### Display Not Showing
```bash
# Check kiosk service
sudo systemctl status raspiframe-kiosk

# Check Chromium process
ps aux | grep chromium

# Manual start
DISPLAY=:0 chromium-browser --kiosk http://localhost:8000/static/player.html
```

### QR Code Not Displaying
```bash
# Check QR file
ls -la ~/raspiframe/static/qr2.png

# Restart service
sudo systemctl restart raspiframe
```

## Security Notice

⚠️ **Important**: 
- `wifi.txt` and `credentials.txt` are stored in plain text
- Keep USB drive physically secure
- Consider encryption for production use
- Recommend removing USB drive after setup

## License

This project is licensed under **CC BY-NC 4.0** (Creative Commons Attribution-NonCommercial 4.0 International).

- ✅ Free for personal and family use
- ✅ Modification and redistribution allowed (non-commercial)
- ✅ Attribution required
- ❌ Commercial use prohibited

Details: https://creativecommons.org/licenses/by-nc/4.0/

For commercial use inquiries, please contact the author.

## Author

**TO-Lab** (github.com/tolab125/Superphotoframe)

©2025 TO-Lab Open Source

## Changelog

### v1.0 (2025-10)
- DLNA auto-discovery and mount
- USB WiFi auto-configuration
- USB photo folder support
- NAS ON/OFF toggle
- Startup pipeline implementation
- iOS-like UI design
- Portrait mode support
- Notification disabling
- Initial release
