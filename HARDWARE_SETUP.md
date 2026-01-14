# Hardware Setup Guide

This guide covers the physical setup and wiring for the Honkey Pi NMEA2000 Reader.

## Components

1. **Raspberry Pi Zero** (W or WH recommended for WiFi)
2. **Waveshare USB-CAN-A** interface
3. **Inky pHAT** e-ink display (any color: red, yellow, or black)
4. **MicroSD card** (16GB or larger)
5. **Micro USB cable** for power
6. **NMEA 2000 drop cable** (M12 5-pin connector to bare wires)

## Step 1: Raspberry Pi Zero Setup

1. Flash Raspberry Pi OS Lite (or Desktop) to the microSD card using [Raspberry Pi Imager](https://www.raspberrypi.com/software/)
2. Enable SSH during imaging (in Advanced Options)
3. Configure WiFi during imaging if using Pi Zero W/WH
4. Insert microSD card into Pi Zero and power on
5. SSH into the Pi: `ssh pi@raspberrypi.local` (default password: raspberry)
6. Update the system:
   ```bash
   sudo apt update && sudo apt upgrade -y
   ```

## Step 2: Inky pHAT Installation

1. **Power off** the Raspberry Pi Zero
2. Align the Inky pHAT with the GPIO header on the Pi Zero
3. Press firmly to seat all 40 pins
4. The display should sit flush on top of the Pi

The Inky pHAT uses:
- GPIO pins for communication (SPI, I2C)
- No additional power supply needed

## Step 3: USB-CAN-A Connection

### Physical Connection

1. Connect the USB-CAN-A to the Raspberry Pi Zero via a **Micro USB OTG adapter**
   - Pi Zero has a micro USB port, so you'll need an OTG adapter
   - Or use a micro USB to USB-A cable with OTG support

### NMEA 2000 Network Connection

The USB-CAN-A has a DB9 connector. You'll need to wire it to your boat's NMEA 2000 network:

**DB9 Pin to NMEA 2000 Mapping:**

| DB9 Pin | Signal    | NMEA 2000 Wire Color | M12 Pin |
|---------|-----------|----------------------|---------|
| 2       | CAN_L     | White                | 4       |
| 7       | CAN_H     | Blue                 | 5       |
| 3       | GND       | Black (Shield)       | 3       |
| 9       | +12V*     | Red                  | 1       |

*Note: The +12V connection is optional. The USB-CAN-A is powered via USB, but connecting to the NMEA 2000 power ensures proper CAN bus termination and grounding.

### Wiring Steps

1. Obtain an NMEA 2000 drop cable or T-connector
2. Strip the wires if using bare cable
3. Create or purchase a DB9 to NMEA 2000 adapter cable with the pinout above
4. Connect to an available drop point on your NMEA 2000 backbone

**Important:**
- Ensure proper polarity (CAN_H to blue, CAN_L to white)
- Connect the ground/shield for noise immunity
- Do not reverse CAN_H and CAN_L (the network won't work)

## Step 4: CAN Interface Configuration

After booting the Pi with the USB-CAN-A connected:

```bash
# Check if the device is detected
lsusb | grep CAN

# Check for can0 interface
ip link show can0

# If not present, configure it
sudo ip link set can0 type can bitrate 250000
sudo ip link set can0 up

# Verify it's up
ip link show can0
```

The install script (`install.sh`) automates this configuration.

## Step 5: Test the Hardware

### Test CAN Interface

With the USB-CAN-A connected to the NMEA 2000 network:

```bash
# Listen for raw CAN messages
candump can0

# You should see messages like:
# can0  09F10D00   [8]  FF FF FF FF FF 00 A0 FC
```

If you see messages, the CAN interface is working!

### Test Inky Display

```bash
cd /home/pi/honkey_pi
python3 main.py --test-display
```

The display should update with test data. If nothing happens, check:
- SPI and I2C are enabled in `raspi-config`
- Inky pHAT is properly seated on GPIO pins
- Run `sudo i2cdetect -y 1` to see if I2C devices are detected

## Step 6: Run the Application

```bash
# Start manually (for testing)
cd /home/pi/honkey_pi
python3 main.py

# Or start as a service
sudo systemctl start honkey_pi
sudo systemctl status honkey_pi
```

## Troubleshooting

### USB-CAN-A Not Detected

```bash
# Check USB devices
lsusb

# Check kernel messages
dmesg | grep -i usb
dmesg | grep -i can

# Install CAN utilities if missing
sudo apt install can-utils
```

### CAN Interface Shows No Messages

1. Check physical connections (CAN_H, CAN_L, GND)
2. Verify NMEA 2000 network is powered on
3. Check bitrate is set to 250000 (NMEA 2000 standard)
4. Try swapping CAN_H and CAN_L if you see nothing (incorrect polarity)

### Inky Display Not Working

```bash
# Enable SPI and I2C
sudo raspi-config
# Interface Options -> SPI -> Enable
# Interface Options -> I2C -> Enable

# Reboot
sudo reboot

# Test I2C
sudo i2cdetect -y 1

# Check GPIO access
sudo usermod -a -G gpio,spi,i2c pi
```

### Power Issues

- Pi Zero needs at least 5V 1A power supply
- USB-CAN-A draws minimal power from USB
- Inky pHAT draws minimal power (only during updates)
- If experiencing crashes, check power supply quality

## Enclosure Recommendations

For boat installation, consider:
- **Waterproof case** with cable glands for connections
- **Ventilation** (passive is fine, minimal heat)
- **Secure mounting** to handle boat movement
- **Cable strain relief** for USB and NMEA connections
- **UV-resistant** if exposed to sunlight

Suggested enclosures:
- Hammond 1554 series (IP65 rated)
- Takachi TWN series (clear lid to see display)
- 3D printed custom enclosure with viewing window for Inky display

## Power Consumption

Typical power draw:
- Raspberry Pi Zero: ~100-150 mA (0.5-0.75W)
- Inky pHAT: ~2 mA idle, ~40 mA during update
- USB-CAN-A: ~50 mA

**Total: ~200 mA at 5V = 1W continuous**

Can be powered from:
- USB power bank
- 12V to 5V USB converter (from boat power)
- Solar panel with USB output

## Next Steps

After hardware setup is complete:
1. Follow the [software installation guide](README.md#quick-start)
2. Configure `config.yaml` for your preferences
3. Enable the systemd service for auto-start
4. Monitor data collection in `/home/pi/honkey_pi_data/`

## Diagrams

### System Overview
```
NMEA 2000 Network (boat)
        |
        | (M12 cable)
        |
[USB-CAN-A] -----(USB)----> [Raspberry Pi Zero]
                                    |
                                    | (GPIO)
                                    |
                              [Inky pHAT]
```

### GPIO Pin Usage
```
Inky pHAT uses these pins:
- 3.3V Power (Pin 1, 17)
- GND (Pin 6, 9, 14, 20, 25, 30, 34, 39)
- SPI: MOSI, MISO, SCLK, CE0 (Pins 19, 21, 23, 24)
- I2C: SDA, SCL (Pins 3, 5)
- Additional GPIO for reset and DC

USB-CAN-A uses:
- USB port (micro USB OTG on Pi Zero)

Do not use conflicting GPIO pins for other purposes.
```
