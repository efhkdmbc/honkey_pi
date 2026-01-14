"""
Display module for Inky pHAT e-ink display
Shows boat metrics and system information
"""

import logging
import psutil
from datetime import datetime
from pathlib import Path
from typing import Dict

# Always import PIL as it's needed for image processing
try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    Image = None
    ImageDraw = None
    ImageFont = None

INKY_AVAILABLE = False

try:
    from inky.auto import auto
    INKY_AVAILABLE = True
except ImportError:
    pass  # Display will be simulated if hardware not available

# Get module-specific logger
logger = logging.getLogger(__name__)


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
        if Image is None:
            print("Warning: PIL not available, cannot update display")
            return
            
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

    def show_bootup_screen(self, image_path: str = "bootup screen.JPG") -> bool:
        """
        Display bootup screen image on the Inky display.
        
        Args:
            image_path: Path to the bootup image file
            
        Returns:
            True if image was displayed successfully, False otherwise
        """
        if Image is None:
            error_msg = "PIL not available, cannot display bootup screen"
            logger.error(error_msg)
            print(error_msg)
            return False
            
        try:
            # Resolve image path
            img_file = Path(image_path)
            if not img_file.is_absolute():
                # Try relative to current directory
                img_file = Path(__file__).parent / image_path
            
            # Check if image exists
            if not img_file.exists():
                error_msg = f"Bootup image not found: {img_file}"
                logger.error(error_msg)
                print(error_msg)
                return False
            
            # Load and process image
            logger.info(f"Loading bootup screen from: {img_file}")
            img = Image.open(img_file)
            
            # Convert to RGB if necessary
            if img.mode != "RGB":
                img = img.convert("RGB")
            
            # Resize to fit display dimensions while maintaining aspect ratio
            img.thumbnail((self.width, self.height), Image.Resampling.LANCZOS)
            
            # Create a new image with display dimensions and paste the resized image
            display_img = Image.new("RGB", (self.width, self.height), (255, 255, 255))
            # Center the image
            offset_x = (self.width - img.width) // 2
            offset_y = (self.height - img.height) // 2
            display_img.paste(img, (offset_x, offset_y))
            
            # Convert to palette mode for Inky display using a fixed limited palette
            # Define a simple 3-color palette: white, black, and an accent (e.g., red)
            inky_palette = [
                255, 255, 255,  # white
                0, 0, 0,        # black
                255, 0, 0,      # accent (red)
            ]
            # Pad the palette to 256 colors (Pillow requires 768 values for mode "P")
            inky_palette += [0, 0, 0] * (256 - len(inky_palette) // 3)
            
            # Create a palette image and quantize the boot image to this palette
            palette_img = Image.new("P", (1, 1))
            palette_img.putpalette(inky_palette)
            display_img = display_img.quantize(palette=palette_img)
            
            # Display on Inky or save simulation
            if self.display and INKY_AVAILABLE:
                try:
                    self.display.set_image(display_img)
                    self.display.show()
                    logger.info("Bootup screen displayed successfully")
                    print("Bootup screen displayed successfully")
                    return True
                except Exception as e:
                    error_msg = f"Error displaying bootup screen on hardware: {e}"
                    logger.error(error_msg)
                    print(error_msg)
                    return False
            else:
                # Save to file for simulation/debugging
                simulation_path = Path("/tmp/inky_bootup_simulation.png")
                display_img.save(simulation_path)
                logger.info(f"Bootup screen simulation saved to {simulation_path}")
                print(f"Bootup screen simulation saved to {simulation_path}")
                return True
                
        except Exception as e:
            error_msg = f"Error loading bootup screen: {e}"
            logger.error(error_msg)
            print(error_msg)
            return False
