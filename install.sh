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

# Detect the user who invoked sudo (or fall back to current user)
if [ -n "$SUDO_USER" ]; then
    INSTALL_USER="$SUDO_USER"
elif [ -n "$USER" ] && [ "$USER" != "root" ]; then
    INSTALL_USER="$USER"
else
    # Default to 'pi' if we can't determine the user
    INSTALL_USER="pi"
    echo "Warning: Could not detect invoking user, defaulting to 'pi'"
fi

echo "Installing for user: $INSTALL_USER"

# Install system dependencies
echo "Installing system dependencies..."
apt-get update
apt-get install -y python3-pip python3-dev python3-venv git can-utils

# Note: USB-CAN-A is a USB device and does not require device tree overlays.
# The CAN interface will be created automatically by the USB kernel driver
# when the device is connected. No Raspberry Pi-specific configuration needed.

# Ensure network interfaces directory exists
echo "Ensuring /etc/network/interfaces.d directory exists..."
mkdir -p /etc/network/interfaces.d

# Configure CAN network interface
cat > /etc/network/interfaces.d/can0 <<EOF
auto can0
iface can0 inet manual
    pre-up /sbin/ip link set can0 type can bitrate 250000
    up /sbin/ifconfig can0 up
    down /sbin/ifconfig can0 down
EOF

# Create installation directory
INSTALL_DIR="/home/$INSTALL_USER/honkey_pi"
echo "Creating installation directory: $INSTALL_DIR"
mkdir -p "$INSTALL_DIR"

# Get the absolute path of the current directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Copy files only if we're not already in the installation directory
if [ "$SCRIPT_DIR" != "$INSTALL_DIR" ]; then
    echo "Copying application files from $SCRIPT_DIR to $INSTALL_DIR..."
    cp "$SCRIPT_DIR/main.py" "$INSTALL_DIR"/
    cp "$SCRIPT_DIR/nmea2000_logger.py" "$INSTALL_DIR"/
    cp "$SCRIPT_DIR/display.py" "$INSTALL_DIR"/
    cp "$SCRIPT_DIR/config.yaml" "$INSTALL_DIR"/
    cp "$SCRIPT_DIR/requirements.txt" "$INSTALL_DIR"/
    cp "$SCRIPT_DIR/honkey_pi.service" "$INSTALL_DIR"/
else
    echo "Already in installation directory, skipping file copy..."
fi

# Set ownership
chown -R "$INSTALL_USER":"$INSTALL_USER" "$INSTALL_DIR"

# Install Python dependencies
echo "Installing Python dependencies..."
su - "$INSTALL_USER" -c "cd \"$INSTALL_DIR\" && pip3 install -r requirements.txt"

# Install systemd service
echo "Installing systemd service..."
# Update service file with the correct user and paths
sed -e "s|User=pi|User=$INSTALL_USER|g" \
    -e "s|/home/pi/|/home/$INSTALL_USER/|g" \
    "$INSTALL_DIR/honkey_pi.service" > /etc/systemd/system/honkey_pi.service
systemctl daemon-reload

# Create data directory
DATA_DIR="/home/$INSTALL_USER/honkey_pi_data"
mkdir -p "$DATA_DIR"
chown "$INSTALL_USER":"$INSTALL_USER" "$DATA_DIR"

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
