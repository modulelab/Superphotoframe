#!/usr/bin/env python3
"""
Generate EDID file for 1024x600@60Hz display
For Raspberry Pi Bookworm with vc4-kms-v3d driver
"""

import struct

def generate_edid_1024x600():
    """
    Generate a basic EDID 1.3 structure for 1024x600@60Hz
    This is a minimal EDID that should work with KMS driver
    """
    edid = bytearray(128)
    
    # EDID Header (8 bytes)
    edid[0:8] = b'\x00\xFF\xFF\xFF\xFF\xFF\xFF\x00'
    
    # Manufacturer ID (2 bytes) - Generic
    edid[8:10] = b'\x00\x00'
    
    # Product Code (2 bytes)
    edid[10:12] = b'\x00\x00'
    
    # Serial Number (4 bytes)
    edid[12:16] = b'\x00\x00\x00\x00'
    
    # Week of manufacture (1 byte)
    edid[16] = 1
    
    # Year of manufacture (1 byte) - 2024
    edid[17] = 2024 - 1990
    
    # EDID Version (1 byte)
    edid[18] = 1  # Version 1
    
    # EDID Revision (1 byte)
    edid[19] = 3  # Revision 3
    
    # Basic Display Parameters (5 bytes)
    edid[20] = 0x80  # Digital input, 8 bits per color
    edid[21] = 0x00  # Screen size: not specified
    edid[22] = 0x00  # Gamma: not specified
    edid[23] = 0x0F  # Features: Standard sRGB, Preferred timing mode
    edid[24] = 0x00  # Color characteristics: not specified
    
    # Color Characteristics (10 bytes) - Standard sRGB
    edid[25:35] = b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
    
    # Established Timings (3 bytes)
    edid[35:38] = b'\x00\x00\x00'
    
    # Standard Timings (16 bytes) - 8 timings, 2 bytes each
    # Timing 1: 1024x600@60Hz (custom)
    edid[38:40] = struct.pack('>HH', 0x0101, 0x0101)[:2]  # Placeholder
    
    # Detailed Timing Blocks (72 bytes) - 4 blocks of 18 bytes each
    
    # Block 1: Preferred Timing (1024x600@60Hz)
    # Pixel Clock: ~50.0 MHz (in 10kHz units = 5000)
    pixel_clock = 5000  # 50.0 MHz
    edid[54:56] = struct.pack('<H', pixel_clock)
    
    # Horizontal Active: 1024 pixels
    h_active = 1024
    h_blank = 256  # Total - Active
    h_sync_off = 48
    h_sync_width = 32
    h_border = 0
    
    edid[56] = h_active & 0xFF
    edid[58] = h_blank & 0xFF
    edid[59] = ((h_active >> 8) << 4) | (h_blank >> 8)
    
    # Vertical Active: 600 lines
    v_active = 600
    v_blank = 24  # Total - Active
    v_sync_off = 3
    v_sync_width = 5
    v_border = 0
    
    edid[57] = v_active & 0xFF
    edid[60] = v_blank & 0xFF
    edid[61] = ((v_active >> 8) << 4) | (v_blank >> 8)
    
    # Sync and timing
    edid[62] = h_sync_off & 0xFF
    edid[63] = h_sync_width & 0xFF
    edid[64] = v_sync_off & 0xFF
    edid[65] = v_sync_width & 0xFF
    edid[66] = ((h_sync_off >> 8) << 6) | ((h_sync_width >> 8) << 4) | \
               ((v_sync_off >> 8) << 2) | (v_sync_width >> 8)
    
    # Image size and pixel aspect ratio
    edid[67] = 0x00  # Horizontal image size (not specified)
    edid[68] = 0x00  # Vertical image size (not specified)
    edid[69] = 0x00  # Pixel aspect ratio (square pixels)
    
    # Features
    edid[70] = 0x1E  # Digital, no stereo, normal display
    
    # Block 2-4: Monitor Name (ASCII)
    edid[72:90] = b'1024x600@60Hz\x00\x00\x00\x00\x00'
    
    # Extension flag and checksum
    edid[126] = 0x00  # No extensions
    edid[127] = 0x00  # Checksum (will be calculated)
    
    # Calculate checksum
    checksum = (256 - sum(edid[0:127])) % 256
    edid[127] = checksum
    
    return bytes(edid)

if __name__ == '__main__':
    edid_data = generate_edid_1024x600()
    
    output_file = '/tmp/edid_1024x600.bin'
    with open(output_file, 'wb') as f:
        f.write(edid_data)
    
    print(f"EDID file generated: {output_file}")
    print(f"Size: {len(edid_data)} bytes")
    print(f"Checksum: 0x{edid_data[127]:02X}")

