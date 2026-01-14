# Honkey Pi - Implementation Summary

## Project Overview

This repository contains a complete software stack for the Raspberry Pi Zero that reads NMEA 2000 data from a boat's CAN network and displays real-time metrics.

## What Was Implemented

### Core Functionality
1. **NMEA 2000 Data Reader** (`nmea2000_logger.py`)
   - Interfaces with Waveshare USB-CAN-A device
   - Uses the nmea2000 Python library for CAN bus communication
   - Decodes NMEA 2000 messages using canboat database
   - Logs all data to timestamped CSV files
   - Tracks statistics (max speed, depth, message counts)

2. **Inky pHAT Display Module** (`display.py`)
   - Updates e-ink display with current metrics
   - Shows: top speed, message count, storage usage, disk space, timestamp
   - Configurable update interval (default: 30 seconds)
   - Graceful fallback when hardware not available

3. **Main Application** (`main.py`)
   - Coordinates all components
   - Loads configuration from YAML file
   - Handles signals for graceful shutdown
   - Runs display updates in background thread
   - Command-line interface with test mode

### Configuration & Deployment
4. **Configuration File** (`config.yaml`)
   - CAN interface settings (channel, bitrate)
   - Data logging parameters (directory, filename format, flush interval)
   - Display settings (color, rotation, update interval)
   - Metrics configuration

5. **Installation Script** (`install.sh`)
   - Installs system dependencies
   - Configures CAN interface
   - Sets up network interfaces
   - Installs Python dependencies
   - Deploys systemd service
   - Creates data directory

6. **Systemd Service** (`honkey_pi.service`)
   - Auto-start on boot
   - Automatic restart on failure
   - Runs as pi user
   - Logs to system journal

### Documentation
7. **README.md** - Comprehensive user guide with:
   - Hardware requirements
   - Quick start guide
   - Configuration options
   - Data format specification
   - Architecture overview
   - Troubleshooting guide

8. **HARDWARE_SETUP.md** - Detailed hardware guide with:
   - Physical setup instructions
   - Wiring diagrams and pinouts
   - CAN bus connection guide
   - Testing procedures
   - Enclosure recommendations
   - Power consumption specs

### Testing & Examples
9. **Test Utilities** (`test_utilities.py`)
   - Logger testing with sample messages
   - Display testing with mock data
   - CSV output verification

10. **Example Data** (`example_data.csv`)
    - Sample CSV format showing expected output
    - Includes various NMEA 2000 message types

## CSV Data Format

The logged CSV files contain:
- **timestamp**: ISO 8601 format
- **pgn**: NMEA 2000 PGN (Parameter Group Number)
- **id**: Message identifier (e.g., "speed", "waterDepth")
- **description**: Human-readable description
- **source**: Source address on CAN bus
- **destination**: Destination address
- **priority**: Message priority
- **Field columns**: Dynamic columns for each field in the message
  - Field values
  - Unit columns (e.g., "speed_water_referenced_unit")

Example:
```csv
timestamp,pgn,id,description,source,destination,priority,speed_water_referenced,speed_water_referenced_unit
2021-11-14T12:00:00.000000,128259,speed,Speed,1,255,3,12.5,knots
```

## Architecture

```
┌─────────────────────┐
│  NMEA 2000 Network  │
│   (Boat CAN Bus)    │
└──────────┬──────────┘
           │
           │ M12 Cable
           │
┌──────────▼──────────┐
│  Waveshare          │
│  USB-CAN-A          │
└──────────┬──────────┘
           │
           │ USB
           │
┌──────────▼──────────┐
│  Raspberry Pi Zero  │
│                     │
│  ┌───────────────┐  │
│  │ Main App      │  │
│  │ (main.py)     │  │
│  └───┬───────┬───┘  │
│      │       │      │
│  ┌───▼────┐ ┌▼────┐ │
│  │ Logger │ │Disp │ │
│  └───┬────┘ └┬────┘ │
│      │       │      │
│  ┌───▼────┐ ┌▼────┐ │
│  │ CSV    │ │Inky │ │
│  │ Files  │ │pHAT │ │
│  └────────┘ └─────┘ │
└─────────────────────┘
```

## Key Technical Decisions

1. **NMEA2000 Library Choice**: Used tomer-w/nmea2000 for:
   - USB-CAN device support
   - Complete canboat database integration
   - Fast message handling
   - Active maintenance

2. **CSV Format**: Flattened structure for:
   - Easy import into analytics tools
   - Human readability
   - Compatibility with existing analytics workflows

3. **E-ink Display**: Inky pHAT chosen for:
   - Low power consumption
   - Excellent sunlight readability
   - No flickering
   - Information persistence without power

4. **Systemd Service**: Ensures:
   - Automatic startup on boot
   - Automatic restart on failure
   - Proper logging via journald
   - Clean shutdown handling

## Security

- All dependencies checked for vulnerabilities
- Pillow updated to 10.2.0 (from 9.0.0) to fix:
  - Path traversal vulnerability
  - Arbitrary code execution vulnerability
  - libwebp OOB write vulnerability
- No hardcoded credentials or secrets
- Data stored locally (no network transmission)
- CodeQL security scan passed with 0 alerts

## Usage

### Basic Usage
```bash
# Start the service
sudo systemctl start honkey_pi

# View logs
sudo journalctl -u honkey_pi -f

# Stop the service
sudo systemctl stop honkey_pi
```

### Manual Testing
```bash
# Test display
python3 main.py --test-display

# Run with custom config
python3 main.py -c /path/to/config.yaml
```

### Data Access
CSV files are stored in `/home/pi/honkey_pi_data/` (configurable).

Each file is named with a timestamp: `2021Nov14_120000.csv`

## Dependencies

### Python Packages
- nmea2000 >= 0.1.0 - NMEA 2000 encoding/decoding
- inky >= 1.5.0 - Inky pHAT display driver
- python-can >= 4.0.0 - CAN bus interface
- psutil >= 5.9.0 - System monitoring
- PyYAML >= 6.0 - Configuration file parsing
- Pillow >= 10.2.0 - Image processing (security hardened)

### System Packages
- python3-pip, python3-dev, python3-venv
- can-utils - CAN bus utilities
- git - Version control

## Maintenance

### Log Rotation
CSV files are not automatically rotated. Consider implementing:
- Cron job to compress old files
- Script to archive to external storage
- Size-based rotation policy

### Updates
```bash
cd /home/pi/honkey_pi
git pull
sudo systemctl restart honkey_pi
```

### Monitoring
```bash
# Check service status
sudo systemctl status honkey_pi

# View recent logs
sudo journalctl -u honkey_pi -n 100

# Check disk usage
df -h /home/pi/honkey_pi_data

# Monitor CAN bus
candump can0
```

## Future Enhancements

Potential improvements:
1. Web interface for viewing data
2. Real-time plotting of metrics
3. Alert system (low battery, high temperature, etc.)
4. WiFi data synchronization
5. GPS tracking visualization
6. Integration with boat automation systems
7. Machine learning for anomaly detection
8. Mobile app companion
9. Multi-display support
10. Cloud backup option

## Credits

- nmea2000 library: https://github.com/tomer-w/nmea2000
- canboat project: https://canboat.github.io/canboat/canboat.html
- Inky library: https://github.com/pimoroni/inky

## License

MIT License - See LICENSE file for details.
