"""
Display module for Inky pHAT e-ink display
Shows boat metrics and system information
"""

import psutil
from datetime import datetime
from pathlib import Path
from typing import Dict

INKY_AVAILABLE = False

try:
    from inky.auto import auto
    from PIL import Image, ImageDraw, ImageFont
    INKY_AVAILABLE = True
except ImportError:
    pass  # Display will be simulated if hardware not available


class InkyDisplay:
    """Manages the Inky pHAT e-ink display"""

    def __init__(self, color: str = "red", rotation: int = 0):
        """
        Initialize the Inky pHAT display.
        
        Args:
            color: Display color variant (red, yellow, black)
            rotation: Display rotation (0, 90, 180, 270)
        """
        self.color = color
        self.rotation = rotation
        self.display = None
        
        if INKY_AVAILABLE:
            try:
                self.display = auto(ask_user=False)
                self.display.set_border(self.display.WHITE)
                if self.rotation:
                    self.display.set_rotation(self.rotation)
                print(f"Initialized Inky pHAT display: {self.display.resolution}")
            except Exception as e:
                print(f"Error initializing display: {e}")
                self.display = None
        else:
            print("Warning: Inky library not available. Display will be simulated.")
        
        # Display dimensions (Inky pHAT is 212x104)
        self.width = 212
        self.height = 104

    def _get_storage_info(self, data_directory: str) -> tuple:
        """
        Get storage information.
        
        Args:
            data_directory: Path to data directory
            
        Returns:
            Tuple of (used_gb, total_gb, percent_used)
        """
        try:
            usage = psutil.disk_usage(data_directory)
            used_gb = usage.used / (1024 ** 3)
            total_gb = usage.total / (1024 ** 3)
            percent = usage.percent
            return used_gb, total_gb, percent
        except Exception as e:
            print(f"Error getting storage info: {e}")
            return 0, 0, 0

    def _get_data_directory_size(self, data_directory: str) -> float:
        """
        Get size of data directory in MB.
        
        Args:
            data_directory: Path to data directory
            
        Returns:
            Size in MB
        """
        try:
            total_size = 0
            data_path = Path(data_directory)
            if data_path.exists():
                for file in data_path.rglob('*'):
                    if file.is_file():
                        total_size += file.stat().st_size
            return total_size / (1024 ** 2)
        except Exception as e:
            print(f"Error calculating directory size: {e}")
            return 0

    def update_display(self, stats: Dict, data_directory: str) -> None:
        """
        Update the display with current metrics.
        
        Args:
            stats: Dictionary with statistics (max_speed, messages_logged, etc.)
            data_directory: Path to data directory for storage info
        """
        # Create image
        img = Image.new("P", (self.width, self.height), 255)
        draw = ImageDraw.Draw(img)
        
        # Try to use a better font, fall back to default
        try:
            font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 16)
            font_medium = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
            font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10)
        except OSError:
            font_large = ImageFont.load_default()
            font_medium = ImageFont.load_default()
            font_small = ImageFont.load_default()
        
        # Get data
        max_speed = stats.get('max_speed', 0)
        messages = stats.get('messages_logged', 0)
        used_gb, total_gb, percent = self._get_storage_info(data_directory)
        data_size_mb = self._get_data_directory_size(data_directory)
        
        # Layout
        y_offset = 5
        line_height = 15
        
        # Title
        draw.text((5, y_offset), "NMEA2000 Logger", 0, font=font_large)
        y_offset += 20
        
        # Top Speed
        speed_text = f"Top Speed: {max_speed:.1f} kn"
        draw.text((5, y_offset), speed_text, 0, font=font_medium)
        y_offset += line_height
        
        # Messages logged
        msg_text = f"Messages: {messages:,}"
        draw.text((5, y_offset), msg_text, 0, font=font_small)
        y_offset += line_height
        
        # Data storage
        data_text = f"Data: {data_size_mb:.1f} MB"
        draw.text((5, y_offset), data_text, 0, font=font_small)
        y_offset += line_height
        
        # Disk usage
        disk_text = f"Disk: {used_gb:.1f}/{total_gb:.1f} GB ({percent:.0f}%)"
        draw.text((5, y_offset), disk_text, 0, font=font_small)
        y_offset += line_height
        
        # Timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        draw.text((5, y_offset), timestamp, 0, font=font_small)
        
        # Update display or save simulation
        if self.display and INKY_AVAILABLE:
            try:
                self.display.set_image(img)
                self.display.show()
                print("Display updated successfully")
            except Exception as e:
                print(f"Error updating display: {e}")
        else:
            # Save to file for simulation/debugging
            img_path = Path("/tmp/inky_display_simulation.png")
            img.save(img_path)
            print(f"Display simulation saved to {img_path}")

    def clear_display(self) -> None:
        """Clear the display"""
        if self.display and INKY_AVAILABLE:
            try:
                img = Image.new("P", (self.width, self.height), 255)
                self.display.set_image(img)
                self.display.show()
                print("Display cleared")
            except Exception as e:
                print(f"Error clearing display: {e}")
