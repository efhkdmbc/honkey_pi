# Honkey Pi - NMEA2000 Data Logger

Integrated NMEA 2000 reader for boat analytics with Raspberry Pi Zero, USB-CAN-A interface, and Inky pHAT display.

## Overview

Honkey Pi is a complete software stack for the Raspberry Pi Zero that:
- Reads NMEA 2000 data from your boat's network via Waveshare USB-CAN-A interface
- Logs all network data to CSV files for later analysis
- Displays real-time metrics on an Inky pHAT e-ink display (storage used, top boat speed, message count, etc.)
- Runs as a background service with automatic startup

## Hardware Requirements

- **Raspberry Pi Zero** (or Zero W/WH)
- **Waveshare USB-CAN-A** interface for NMEA 2000 connectivity
- **Inky pHAT** e-ink display (red, yellow, or black variant)
- MicroSD card (16GB+ recommended for data storage)
- Power supply for Raspberry Pi

## Software Requirements

- Raspberry Pi OS (Bullseye or later recommended)
- Python 3.7+
- Internet connection for initial setup

## Quick Start

### 1. Clone the Repository

```bash
cd /home/pi
git clone https://github.com/efhkdmbc/honkey_pi.git
cd honkey_pi
```

### 2. Run Installation Script

```bash
sudo bash install.sh
```

The installation script will:
- Install system dependencies (Python, CAN utilities)
- Configure the CAN interface for NMEA 2000 (250kbps)
- Install Python dependencies (nmea2000, inky, psutil, etc.)
- Set up the systemd service for auto-start
- Create data directory for CSV logs

### 3. Configure (Optional)

Edit `config.yaml` to customize settings:

```bash
nano /home/pi/honkey_pi/config.yaml
```

Key configuration options:
- CAN interface settings (channel, bitrate)
- Data logging directory and format
- Display update interval and color
- Metrics to track (speed, depth, distance)

### 4. Start the Service

```bash
# Start immediately
sudo systemctl start honkey_pi

# Enable auto-start on boot
sudo systemctl enable honkey_pi

# Check status
sudo systemctl status honkey_pi

# View logs
sudo journalctl -u honkey_pi -f
```

### 5. Test the Display

Test the Inky pHAT display with sample data:

```bash
cd /home/pi/honkey_pi
python3 main.py --test-display
```

## Data Format

CSV files are logged to `/home/pi/honkey_pi_data/` (configurable) with the following format:

- **Filename**: `YYYYMMMDD_HHMMSS.csv` (e.g., `2021Nov14_120000.csv`)
- **Columns**: timestamp, pgn, id, description, source, destination, priority, plus all decoded fields from each message

Example row:
```csv
timestamp,pgn,id,description,source,destination,priority,speed_water_referenced,speed_water_referenced_unit
2021-11-14T12:00:00,128259,speed,Speed,1,255,3,12.5,knots
```

This format is compatible with the honkey-analytics repository for further analysis.

## Display Information

The Inky pHAT display shows:
- **Top Speed**: Maximum boat speed recorded (in knots)
- **Messages**: Total number of NMEA 2000 messages logged
- **Data**: Size of data directory (CSV files)
- **Disk**: Overall disk usage on the system
- **Timestamp**: Last update time

The display updates every 30 seconds (configurable).

## Architecture

### Components

1. **nmea2000_logger.py**: Handles NMEA 2000 data reception and CSV logging
   - `NMEA2000Reader`: Interfaces with USB-CAN-A via nmea2000 library
   - `NMEA2000DataLogger`: Writes decoded messages to CSV files
   - Statistics tracking for metrics

2. **display.py**: Manages Inky pHAT e-ink display
   - `InkyDisplay`: Updates display with current statistics
   - Graceful fallback if display is not connected (simulation mode)

3. **main.py**: Main application coordinator
   - `HonkeyPi`: Orchestrates all components
   - Configuration loading
   - Signal handling for graceful shutdown
   - Display update thread

4. **config.yaml**: Configuration file
   - CAN interface settings
   - Data logging parameters
   - Display settings
   - Metrics configuration

5. **honkey_pi.service**: Systemd service unit
   - Auto-start on boot
   - Automatic restart on failure
   - Log to system journal

## NMEA 2000 Data Source

This project uses the [nmea2000](https://github.com/tomer-w/nmea2000) Python library by tomer-w, which provides:
- Decoding of NMEA 2000 frames based on the canboat database
- Support for USB CAN devices (like Waveshare USB-CAN-A)
- Handling of fast messages split across multiple frames
- PGN-specific parsing for various message types

## Troubleshooting

### CAN Interface Not Found

If `can0` interface is not available:

```bash
# Check if interface exists
ip link show can0

# Bring up manually
sudo ip link set can0 type can bitrate 250000
sudo ip link set can0 up

# Check for errors
dmesg | grep -i can
```

### Display Not Working

If Inky pHAT is not displaying:

```bash
# Check I2C and SPI are enabled
sudo raspi-config
# Navigate to Interface Options -> I2C/SPI and enable

# Test display
cd /home/pi/honkey_pi
python3 main.py --test-display
```

### No Data Being Logged

Check if NMEA 2000 messages are being received:

```bash
# Monitor raw CAN bus traffic
candump can0

# Check service logs
sudo journalctl -u honkey_pi -n 100
```

### Permission Issues

Ensure the pi user has necessary permissions:

```bash
# Add pi user to required groups
sudo usermod -a -G gpio,spi,i2c pi

# Fix ownership of installation directory
sudo chown -R pi:pi /home/pi/honkey_pi
sudo chown -R pi:pi /home/pi/honkey_pi_data
```

## Development

### Running Manually (for testing)

```bash
cd /home/pi/honkey_pi
python3 main.py -c config.yaml
```

### Simulating Without Hardware

The code gracefully handles missing hardware:
- If Inky display is not available, it saves a PNG to `/tmp/inky_display_simulation.png`
- If CAN interface is not available, it will report an error but not crash

## Dependencies

Core dependencies (automatically installed by install.sh):
- **nmea2000** - NMEA 2000 encoding/decoding and USB CAN client
- **inky** - Inky pHAT display driver
- **python-can** - CAN bus interface
- **psutil** - System and process utilities
- **PyYAML** - YAML configuration file support
- **Pillow** - Image processing for display

## License

MIT License - See LICENSE file for details

## Contributing

Contributions welcome! Please open an issue or pull request.

## Acknowledgments

- [nmea2000 library](https://github.com/tomer-w/nmea2000) by tomer-w
- [canboat project](https://canboat.github.io/canboat/canboat.html) for NMEA 2000 message definitions
- [Inky library](https://github.com/pimoroni/inky) by Pimoroni

