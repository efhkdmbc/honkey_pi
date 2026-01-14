"""
NMEA 2000 Data Logger for Raspberry Pi Zero
Reads NMEA 2000 data from USB-CAN-A and logs to CSV format
with 1 Hz sampling rate and fixed column format.
"""

import csv
import errno
import getpass
import os
import time
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict

try:
    from nmea2000.usb_client import USBClient
except ImportError:
    # Allow module to load for testing without hardware
    USBClient = None

from csv_format import (
    COLUMN_NAMES, FORMAT_VERSION, DEFAULT_BOAT_ID,
    create_empty_row, datetime_to_excel_serial
)


class NMEA2000DataLogger:
    """Logs NMEA 2000 data to CSV files with 1 Hz sampling and fixed format"""

    def __init__(self, data_directory: str, filename_format: str = "%Y%b%d_%H%M%S.csv",
                 flush_interval: int = 10, boat_id: str = DEFAULT_BOAT_ID):
        """
        Initialize the data logger.
        
        Args:
            data_directory: Directory to store CSV files
            filename_format: strftime format for CSV filename
            flush_interval: How often to flush data to disk (seconds)
            boat_id: Boat identifier for CSV data
        
        Raises:
            PermissionError: If the data directory cannot be created due to insufficient permissions
        """
        self.data_directory = Path(data_directory)
        try:
            self.data_directory.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            # Catch permission-related errors
            is_permission_error = (
                e.errno in (errno.EACCES, errno.EPERM) or 
                isinstance(e, PermissionError)
            )
            
            if is_permission_error:
                try:
                    current_user = getpass.getuser()
                except Exception:
                    current_user = 'current user'
                error_msg = (
                    f"\n{'='*70}\n"
                    f"ERROR: Cannot create data directory: {self.data_directory}\n"
                    f"{'='*70}\n"
                    f"Permission denied. The service does not have write access to create\n"
                    f"or access the configured data directory.\n\n"
                    f"Possible solutions:\n"
                    f"  1. Change the data_directory in config.yaml to a writable location\n"
                    f"     (e.g., /tmp/honkey_pi_data or a directory owned by the service user)\n"
                    f"  2. Create the directory manually with proper permissions:\n"
                    f"     sudo mkdir -p {self.data_directory}\n"
                    f"     sudo chown {current_user} {self.data_directory}\n"
                    f"  3. If running as a systemd service, ensure the service user has\n"
                    f"     write permissions to the configured directory\n"
                    f"{'='*70}\n"
                )
                raise PermissionError(error_msg) from e
            else:
                # Re-raise other OSErrors
                raise
        self.filename_format = filename_format
        self.flush_interval = flush_interval
        self.boat_id = boat_id
        
        self.csv_file = None
        self.csv_writer = None
        self.last_flush_time = time.time()
        self.message_count = 0
        
        # Data buffer for 1 Hz sampling
        self.data_buffer = create_empty_row(boat_id)
        self.buffer_lock = threading.Lock()
        self.last_log_time = time.time()
        
        # 1 Hz logging thread
        self.logging_active = False
        self.logging_thread = None
        
        # Statistics tracking
        self.stats = {
            'max_speed': 0.0,
            'max_depth': 0.0,
            'total_distance': 0.0,
            'messages_logged': 0,
            'timing_errors': 0
        }

    def _open_new_csv_file(self) -> None:
        """Open a new CSV file with timestamp-based filename and write header"""
        if self.csv_file:
            self.csv_file.close()
        
        filename = datetime.now().strftime(self.filename_format)
        filepath = self.data_directory / filename
        
        self.csv_file = open(filepath, 'w', newline='', encoding='utf-8')
        self.csv_writer = csv.DictWriter(
            self.csv_file,
            fieldnames=COLUMN_NAMES,
            extrasaction='ignore'
        )
        
        # Write header and version line
        self.csv_writer.writeheader()
        self.csv_file.write(FORMAT_VERSION + '\n')
        
        print(f"Opened new CSV file: {filepath}")

    def _map_nmea_to_csv(self, message: Dict) -> None:
        """
        Map NMEA2000 message fields to CSV columns and update buffer.
        
        Args:
            message: Decoded NMEA2000 message
        """
        with self.buffer_lock:
            pgn = message.get('PGN')
            fields = message.get('fields', [])
            
            # Map common NMEA2000 PGNs to CSV columns
            # This is a simplified mapping - expand as needed for your specific PGNs
            
            # PGN 128259 - Speed
            if pgn == 128259:
                for field in fields:
                    if field.get('id') == 'speed_water_referenced':
                        value = field.get('value')
                        if isinstance(value, (int, float)):
                            self.data_buffer['BSP'] = value
            
            # PGN 128267 - Water Depth  
            elif pgn == 128267:
                for field in fields:
                    if field.get('id') == 'depth':
                        value = field.get('value')
                        if isinstance(value, (int, float)):
                            self.data_buffer['Depth'] = value
            
            # PGN 127250 - Vessel Heading
            elif pgn == 127250:
                for field in fields:
                    if field.get('id') == 'heading':
                        value = field.get('value')
                        if isinstance(value, (int, float)):
                            self.data_buffer['HDG'] = value
            
            # PGN 130306 - Wind Data
            elif pgn == 130306:
                for field in fields:
                    field_id = field.get('id')
                    value = field.get('value')
                    if isinstance(value, (int, float)):
                        if field_id == 'wind_speed':
                            self.data_buffer['AWS'] = value
                        elif field_id == 'wind_angle':
                            self.data_buffer['AWA'] = value
            
            # PGN 129025 - Position Rapid Update
            elif pgn == 129025:
                for field in fields:
                    field_id = field.get('id')
                    value = field.get('value')
                    if isinstance(value, (int, float)):
                        if field_id == 'latitude':
                            self.data_buffer['Lat'] = value
                        elif field_id == 'longitude':
                            self.data_buffer['Lon'] = value
            
            # PGN 129026 - COG & SOG Rapid Update
            elif pgn == 129026:
                for field in fields:
                    field_id = field.get('id')
                    value = field.get('value')
                    if isinstance(value, (int, float)):
                        if field_id == 'cog':
                            self.data_buffer['COG'] = value
                        elif field_id == 'sog':
                            self.data_buffer['SOG'] = value
            
            # PGN 127257 - Attitude
            elif pgn == 127257:
                for field in fields:
                    field_id = field.get('id')
                    value = field.get('value')
                    if isinstance(value, (int, float)):
                        if field_id == 'roll':
                            self.data_buffer['Heel'] = value
                        elif field_id == 'pitch':
                            self.data_buffer['Trim'] = value
            
            # PGN 130311 - Environmental Parameters
            elif pgn == 130311:
                # Collect temperature value and source separately, as they are
                # typically provided as distinct fields in the NMEA2000 message.
                temp_value = None
                temp_source = None

                for field in fields:
                    field_id = field.get('id')
                    value = field.get('value')

                    # Temperature value
                    if field_id == 'temperature' and isinstance(value, (int, float)):
                        temp_value = value

                    # Temperature source is usually a separate field
                    elif field_id == 'temperature_source' and isinstance(value, str):
                        temp_source = value

                    # Atmospheric pressure mapping (unchanged behaviour)
                    elif field_id == 'atmospheric_pressure' and isinstance(value, (int, float)):
                        self.data_buffer['Baro'] = value

                # Fallback: if source not found as its own field, try to read it
                # as an attribute on the temperature field (for compatibility with
                # decoders that attach it this way).
                if temp_value is not None and temp_source is None:
                    for field in fields:
                        if field.get('id') == 'temperature':
                            attr_source = field.get('temperature_source')
                            if isinstance(attr_source, str) and attr_source:
                                temp_source = attr_source
                            break

                # Map temperature value into appropriate CSV column based on source.
                if temp_value is not None and temp_source:
                    if temp_source == 'Sea Temperature':
                        self.data_buffer['SeaTemp'] = temp_value
                    elif temp_source == 'Outside Temperature':
                        self.data_buffer['AirTemp'] = temp_value
            
            # PGN 127245 - Rudder
            elif pgn == 127245:
                for field in fields:
                    if field.get('id') == 'position':
                        value = field.get('value')
                        if isinstance(value, (int, float)):
                            self.data_buffer['Rudder'] = value
            
            # Add more PGN mappings as needed based on your specific NMEA2000 data
    
    def _logging_loop(self) -> None:
        """Background thread that logs data at 1 Hz"""
        start_time = time.time()
        iteration = 0
        
        while self.logging_active:
            try:
                # Calculate target time to prevent drift accumulation
                iteration += 1
                target_time = start_time + iteration
                
                # Create row with current timestamp
                with self.buffer_lock:
                    now = datetime.now(timezone.utc)
                    excel_time = datetime_to_excel_serial(now)
                    
                    row = self.data_buffer.copy()
                    row['Utc'] = excel_time
                
                # Write row to CSV
                if self.csv_file is None:
                    self._open_new_csv_file()
                
                self.csv_writer.writerow(row)
                self.stats['messages_logged'] += 1
                
                # Flush periodically
                current_time = time.time()
                if current_time - self.last_flush_time >= self.flush_interval:
                    self.csv_file.flush()
                    self.last_flush_time = current_time
                
                # Sleep until next 1Hz cycle
                sleep_time = target_time - time.time()
                if sleep_time > 0:
                    time.sleep(sleep_time)
                else:
                    # Timing error - we're running behind
                    self.stats['timing_errors'] += 1
                    if self.stats['timing_errors'] % 10 == 0:
                        print(f"Warning: Timing errors detected ({self.stats['timing_errors']} total)")
            
            except Exception as e:
                print(f"Error in logging loop: {e}")
                time.sleep(1.0)  # Prevent tight loop on error

    def log_message(self, message: Dict) -> None:
        """
        Process a single NMEA2000 message and update the data buffer.
        
        Args:
            message: Decoded NMEA2000 message
        """
        self.message_count += 1
        
        # Map message to CSV columns
        self._map_nmea_to_csv(message)
        
        # Update statistics
        self._update_statistics(message)
    
    def start_logging(self) -> None:
        """Start the 1 Hz logging thread"""
        if self.logging_active:
            print("Logging already active")
            return
        
        self.logging_active = True
        self.logging_thread = threading.Thread(target=self._logging_loop, daemon=True)
        self.logging_thread.start()
        print("Started 1 Hz logging thread")
    
    def stop_logging(self) -> None:
        """Stop the 1 Hz logging thread"""
        if not self.logging_active:
            return
        
        self.logging_active = False
        if self.logging_thread:
            self.logging_thread.join(timeout=2.0)
            self.logging_thread = None
        print("Stopped 1 Hz logging thread")

    def _update_statistics(self, message: Dict) -> None:
        """Update statistics from message data"""
        pgn = message.get('PGN')
        fields = message.get('fields', [])
        
        # Track speed (PGN 128259 - Speed)
        if pgn == 128259:
            for field in fields:
                if field.get('id') == 'speed_water_referenced':
                    speed = field.get('value', 0)
                    if isinstance(speed, (int, float)) and speed > self.stats['max_speed']:
                        self.stats['max_speed'] = speed
        
        # Track depth (PGN 128267 - Water Depth)
        if pgn == 128267:
            for field in fields:
                if field.get('id') == 'depth':
                    depth = field.get('value', 0)
                    if isinstance(depth, (int, float)) and depth > self.stats['max_depth']:
                        self.stats['max_depth'] = depth

    def get_statistics(self) -> Dict:
        """Return current statistics"""
        return self.stats.copy()

    def close(self) -> None:
        """Close the logger and stop logging thread"""
        self.stop_logging()
        
        if self.csv_file:
            self.csv_file.close()
            self.csv_file = None
            self.csv_writer = None


class NMEA2000Reader:
    """Reads NMEA 2000 data from USB-CAN-A interface"""

    def __init__(self, channel: str = "can0", bitrate: int = 250000):
        """
        Initialize the NMEA2000 reader.
        
        Args:
            channel: CAN channel name
            bitrate: CAN bitrate (NMEA2000 standard is 250000)
        """
        self.channel = channel
        self.bitrate = bitrate
        self.usb_client = None

    def start(self, callback) -> None:
        """
        Start reading NMEA2000 data.
        
        Args:
            callback: Function to call with each decoded message
        """
        if USBClient is None:
            raise ImportError("nmea2000 library not available. Install with: pip install nmea2000")
        
        try:
            self.usb_client = USBClient(self.channel, self.bitrate)
            self.usb_client.set_receive_callback(callback)
            print(f"Started NMEA2000 reader on {self.channel} at {self.bitrate} baud")
        except Exception as e:
            print(f"Error starting NMEA2000 reader: {e}")
            raise

    def stop(self) -> None:
        """Stop reading NMEA2000 data"""
        if self.usb_client:
            self.usb_client.close()
            self.usb_client = None
