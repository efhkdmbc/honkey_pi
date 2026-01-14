"""
NMEA 2000 Data Logger for Raspberry Pi Zero
Reads NMEA 2000 data from USB-CAN-A and logs to CSV format
"""

import csv
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from nmea2000.decoder import NMEA2000Decoder
from nmea2000.usb_client import USBClient


class NMEA2000DataLogger:
    """Logs NMEA 2000 data to CSV files"""

    def __init__(self, data_directory: str, filename_format: str = "%Y%b%d_%H%M%S.csv",
                 flush_interval: int = 10):
        """
        Initialize the data logger.
        
        Args:
            data_directory: Directory to store CSV files
            filename_format: strftime format for CSV filename
            flush_interval: How often to flush data to disk (seconds)
        """
        self.data_directory = Path(data_directory)
        self.data_directory.mkdir(parents=True, exist_ok=True)
        self.filename_format = filename_format
        self.flush_interval = flush_interval
        
        self.csv_file = None
        self.csv_writer = None
        self.fieldnames = None
        self.last_flush_time = time.time()
        self.message_count = 0
        
        # Statistics tracking
        self.stats = {
            'max_speed': 0.0,
            'max_depth': 0.0,
            'total_distance': 0.0,
            'messages_logged': 0
        }

    def _open_new_csv_file(self) -> None:
        """Open a new CSV file with timestamp-based filename"""
        if self.csv_file:
            self.csv_file.close()
        
        filename = datetime.now().strftime(self.filename_format)
        filepath = self.data_directory / filename
        
        self.csv_file = open(filepath, 'w', newline='')
        self.csv_writer = None  # Will be initialized on first write
        print(f"Opened new CSV file: {filepath}")

    def _get_csv_row(self, message: Dict) -> Dict:
        """
        Convert NMEA2000 message to CSV row format.
        
        Args:
            message: Decoded NMEA2000 message
            
        Returns:
            Dictionary with flattened message data
        """
        row = {
            'timestamp': datetime.now().isoformat(),
            'pgn': message.get('PGN', ''),
            'id': message.get('id', ''),
            'description': message.get('description', ''),
            'source': message.get('source', ''),
            'destination': message.get('destination', ''),
            'priority': message.get('priority', '')
        }
        
        # Add field values
        fields = message.get('fields', [])
        for field in fields:
            field_id = field.get('id', '')
            value = field.get('value', '')
            unit = field.get('unit_of_measurement', '')
            
            if field_id:
                row[field_id] = value
                if unit:
                    row[f"{field_id}_unit"] = unit
        
        return row

    def log_message(self, message: Dict) -> None:
        """
        Log a single NMEA2000 message to CSV.
        
        Args:
            message: Decoded NMEA2000 message
        """
        if self.csv_file is None:
            self._open_new_csv_file()
        
        row = self._get_csv_row(message)
        
        # Initialize CSV writer with fieldnames from first message
        if self.csv_writer is None:
            self.fieldnames = list(row.keys())
            self.csv_writer = csv.DictWriter(
                self.csv_file, 
                fieldnames=self.fieldnames,
                extrasaction='ignore'
            )
            self.csv_writer.writeheader()
        
        # Write row, adding missing fields if needed
        if set(row.keys()) != set(self.fieldnames):
            # New fields appeared, need to close and reopen with extended fieldnames
            self.fieldnames = list(set(self.fieldnames) | set(row.keys()))
            # Note: In production, you might want to handle this differently
        
        self.csv_writer.writerow(row)
        self.message_count += 1
        self.stats['messages_logged'] += 1
        
        # Update statistics
        self._update_statistics(message)
        
        # Flush periodically
        current_time = time.time()
        if current_time - self.last_flush_time >= self.flush_interval:
            self.csv_file.flush()
            self.last_flush_time = current_time

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
        """Close the CSV file"""
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
        self.decoder = NMEA2000Decoder()
        self.usb_client = None

    def start(self, callback) -> None:
        """
        Start reading NMEA2000 data.
        
        Args:
            callback: Function to call with each decoded message
        """
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
