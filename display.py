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
    from inky import eeprom
    INKY_AVAILABLE = True
except ImportError:
    pass  # Display will be simulated if hardware not available

# Get module-specific logger
logger = logging.getLogger(__name__)


class InkyDisplay:
    """Manages the Inky pHAT e-ink display"""

    def _initialize_display(self):
        """
        Initialize the Inky display with auto-detection and custom cs_pin support.
        
        For Inky v2/v3 displays (UC8159 driver), this method allows using a custom
        chip select pin to avoid GPIO8/CE0 conflicts with other SPI devices.
        
        Returns:
            Initialized Inky display object or None on failure
        """
        # Local import of UC8159 driver to avoid import errors if not available
        try:
            from inky.inky_uc8159 import Inky as InkyUC8159
        except ImportError:
            InkyUC8159 = None
        
        # Display variant to resolution mapping for UC8159 displays
        UC8159_VARIANTS = {
            14: (600, 448),  # Impressions 5.7"
            15: (640, 400),  # Impressions 7.3"
            16: (640, 400),  # Impressions 7.3" (alternate)
        }
        
        try:
            # First, try to detect the display type via EEPROM
            _eeprom = eeprom.read_eeprom()
            
            if _eeprom is not None:
                display_variant = _eeprom.display_variant
                
                # For Inky v2/v3 displays (UC8159), manually instantiate with custom cs_pin
                if InkyUC8159 and display_variant in UC8159_VARIANTS:
                    resolution = UC8159_VARIANTS[display_variant]
                    print(f"Detected Inky UC8159 display (variant {display_variant}, resolution {resolution})")
                    return InkyUC8159(resolution=resolution, cs_pin=self.cs_pin)
                else:
                    # For other display types, use auto() which doesn't support cs_pin
                    # These older displays don't have the cs_pin conflict issue
                    print(f"Detected Inky display (variant {display_variant}), using auto-detection")
                    return auto(ask_user=False)
            else:
                # No EEPROM detected, try auto() as fallback
                print("No EEPROM detected, attempting auto-detection")
                return auto(ask_user=False)
                
        except Exception as e:
            print(f"Error during display initialization: {e}")
            # Try auto() as last resort
            try:
                return auto(ask_user=False)
            except Exception as e2:
                print(f"Auto-detection also failed: {e2}")
                return None

    def __init__(self, color: str = "red", rotation: int = 0, cs_pin: int = 7):
        """
        Initialize the Inky pHAT display.
        
        Args:
            color: Display color variant (red, yellow, black)
            rotation: Display rotation (0, 90, 180, 270)
            cs_pin: SPI Chip Select GPIO pin (default: 7 for CE1 to avoid GPIO8/CE0 conflict)
        """
        self.color = color
        self.rotation = rotation
        self.cs_pin = cs_pin
        self.display = None
        
        # Default dimensions (fallback for Inky pHAT 212x104)
        self.width = 212
        self.height = 104
        
        if INKY_AVAILABLE:
            try:
                # Try to auto-detect the display using EEPROM
                self.display = self._initialize_display()
                if self.display:
                    self.display.set_border(self.display.WHITE)
                    if self.rotation:
                        self.display.set_rotation(self.rotation)
                    # Use auto-detected resolution instead of hard-coded values
                    detected_width, detected_height = self.display.resolution
                    # Validate that resolution values are positive integers
                    if detected_width > 0 and detected_height > 0:
                        self.width = detected_width
                        self.height = detected_height
                        print(f"Initialized Inky display: {self.display.resolution} ({self.display.colour})")
                    else:
                        print(f"Warning: Invalid display resolution detected: {self.display.resolution}")
                        print(f"Using default dimensions: {self.width}x{self.height}")
            except Exception as e:
                print(f"Error initializing display: {e}")
                print(f"Falling back to simulated display with default dimensions: {self.width}x{self.height}")
                self.display = None
        else:
            print("Warning: Inky library not available. Display will be simulated.")
            print(f"Using default dimensions: {self.width}x{self.height}")

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
