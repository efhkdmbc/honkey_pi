#!/bin/bash
# Installation script for Honkey Pi NMEA2000 Reader
# Run as: sudo bash install.sh

set -e

echo "========================================="
echo "Honkey Pi NMEA2000 Reader Installation"
echo "========================================="

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "Please run as root (use sudo)"
    exit 1
fi

# Install system dependencies
echo "Installing system dependencies..."
apt-get update
apt-get install -y python3-pip python3-dev python3-venv git can-utils

# Set up CAN interface
echo "Setting up CAN interface..."
if ! grep -q "dtoverlay=mcp2515" /boot/config.txt; then
    echo "dtoverlay=mcp2515-can0,oscillator=16000000,interrupt=25" >> /boot/config.txt
    echo "dtoverlay=spi-bcm2835-overlay" >> /boot/config.txt
fi

# Configure CAN network interface
cat > /etc/network/interfaces.d/can0 <<EOF
auto can0
iface can0 inet manual
    pre-up /sbin/ip link set can0 type can bitrate 250000
    up /sbin/ifconfig can0 up
    down /sbin/ifconfig can0 down
EOF

# Create installation directory
INSTALL_DIR="/home/pi/honkey_pi"
echo "Creating installation directory: $INSTALL_DIR"
mkdir -p $INSTALL_DIR

# Copy files
echo "Copying application files..."
cp main.py $INSTALL_DIR/
cp nmea2000_logger.py $INSTALL_DIR/
cp display.py $INSTALL_DIR/
cp config.yaml $INSTALL_DIR/
cp requirements.txt $INSTALL_DIR/

# Set ownership
chown -R pi:pi $INSTALL_DIR

# Install Python dependencies
echo "Installing Python dependencies..."
su - pi -c "cd $INSTALL_DIR && pip3 install -r requirements.txt"

# Install systemd service
echo "Installing systemd service..."
cp honkey_pi.service /etc/systemd/system/
systemctl daemon-reload

# Create data directory
DATA_DIR="/home/pi/honkey_pi_data"
mkdir -p $DATA_DIR
chown pi:pi $DATA_DIR

echo "========================================="
echo "Installation complete!"
echo ""
echo "To start the service:"
echo "  sudo systemctl start honkey_pi"
echo ""
echo "To enable auto-start on boot:"
echo "  sudo systemctl enable honkey_pi"
echo ""
echo "To view logs:"
echo "  sudo journalctl -u honkey_pi -f"
echo ""
echo "To test the display:"
echo "  cd $INSTALL_DIR && python3 main.py --test-display"
echo ""
echo "Note: You may need to reboot for CAN interface changes to take effect"
echo "========================================="
