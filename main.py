#!/usr/bin/env python3
"""
Main application for Honkey Pi NMEA2000 Reader
Integrates CAN data logging with Inky pHAT display
"""

import argparse
import signal
import sys
import time
import yaml
from pathlib import Path
from threading import Thread, Event

from nmea2000_logger import NMEA2000DataLogger, NMEA2000Reader
from display import InkyDisplay


class HonkeyPi:
    """Main application coordinator"""

    def __init__(self, config_path: str = "config.yaml"):
        """
        Initialize the application.
        
        Args:
            config_path: Path to configuration file
        """
        self.config = self._load_config(config_path)
        self.running = Event()
        
        # Initialize components
        self.logger = NMEA2000DataLogger(
            data_directory=self.config['logging']['data_directory'],
            filename_format=self.config['logging']['csv_filename_format'],
            flush_interval=self.config['logging']['flush_interval']
        )
        
        self.reader = NMEA2000Reader(
            channel=self.config['can']['channel'],
            bitrate=self.config['can']['bitrate']
        )
        
        self.display = InkyDisplay(
            color=self.config['display']['color'],
            rotation=self.config['display']['rotation']
        )
        
        self.display_update_interval = self.config['display']['update_interval']
        
    def _load_config(self, config_path: str) -> dict:
        """Load configuration from YAML file"""
        config_file = Path(config_path)
        if config_file.exists():
            with open(config_file, 'r') as f:
                return yaml.safe_load(f)
        else:
            print(f"Warning: Config file {config_path} not found, using defaults")
            return self._get_default_config()
    
    def _get_default_config(self) -> dict:
        """Return default configuration"""
        return {
            'can': {
                'interface': 'usb',
                'bitrate': 250000,
                'channel': 'can0'
            },
            'logging': {
                'data_directory': '/home/pi/honkey_pi_data',
                'csv_filename_format': '%Y%b%d_%H%M%S.csv',
                'flush_interval': 10
            },
            'display': {
                'type': 'inky_phat',
                'color': 'red',
                'update_interval': 30,
                'rotation': 0,
                'bootup_screen_duration': 30
            },
            'metrics': {
                'track_top_speed': True,
                'track_max_depth': True,
                'track_total_distance': True,
                'speed_unit': 'knots'
            }
        }

    def _handle_message(self, message) -> None:
        """
        Callback for received NMEA2000 messages.
        
        Args:
            message: Decoded NMEA2000 message
        """
        try:
            # Convert message object to dict if needed
            if hasattr(message, 'to_dict'):
                message_dict = message.to_dict()
            elif isinstance(message, dict):
                message_dict = message
            else:
                message_dict = {
                    'PGN': getattr(message, 'pgn', ''),
                    'id': getattr(message, 'id', ''),
                    'description': getattr(message, 'description', ''),
                    'source': getattr(message, 'source', ''),
                    'destination': getattr(message, 'destination', ''),
                    'priority': getattr(message, 'priority', ''),
                    'fields': getattr(message, 'fields', [])
                }
            
            # Log the message
            self.logger.log_message(message_dict)
        except Exception as e:
            print(f"Error handling message: {e}")

    def _display_update_loop(self) -> None:
        """Background thread to update display periodically"""
        while self.running.is_set():
            try:
                stats = self.logger.get_statistics()
                self.display.update_display(
                    stats, 
                    self.config['logging']['data_directory']
                )
            except Exception as e:
                print(f"Error updating display: {e}")
            
            # Wait for next update or shutdown
            self.running.wait(self.display_update_interval)

    def start(self) -> None:
        """Start the application"""
        print("Starting Honkey Pi NMEA2000 Reader...")
        
        # Show bootup screen
        bootup_duration = self.config['display']['bootup_screen_duration']
        print(f"Displaying bootup screen for {bootup_duration} seconds...")
        if self.display.show_bootup_screen():
            time.sleep(bootup_duration)
        else:
            print("Skipping bootup screen delay due to display error")
        
        self.running.set()
        
        # Start display update thread
        display_thread = Thread(target=self._display_update_loop, daemon=True)
        display_thread.start()
        
        # Start NMEA2000 reader (this will block)
        try:
            self.reader.start(self._handle_message)
            print("NMEA2000 reader started successfully")
            
            # Keep main thread alive
            while self.running.is_set():
                time.sleep(1)
                
        except KeyboardInterrupt:
            print("\nShutdown requested...")
        except Exception as e:
            print(f"Error in main loop: {e}")
        finally:
            self.stop()

    def stop(self) -> None:
        """Stop the application"""
        print("Stopping Honkey Pi...")
        self.running.clear()
        
        try:
            self.reader.stop()
        except Exception as e:
            print(f"Error stopping reader: {e}")
        
        try:
            self.logger.close()
        except Exception as e:
            print(f"Error closing logger: {e}")
        
        print("Honkey Pi stopped")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Honkey Pi - NMEA2000 Data Logger with Inky pHAT Display"
    )
    parser.add_argument(
        "-c", "--config",
        default="config.yaml",
        help="Path to configuration file (default: config.yaml)"
    )
    parser.add_argument(
        "--test-display",
        action="store_true",
        help="Test display by showing sample data and exit"
    )
    
    args = parser.parse_args()
    
    # Test display mode
    if args.test_display:
        print("Testing display...")
        display = InkyDisplay()
        test_stats = {
            'max_speed': 12.5,
            'messages_logged': 42000,
            'max_depth': 15.3
        }
        display.update_display(test_stats, "/tmp")
        print("Display test complete")
        return
    
    # Normal operation
    app = HonkeyPi(args.config)
    
    # Set up signal handlers for graceful shutdown
    def signal_handler(sig, frame):
        print("\nReceived shutdown signal")
        app.stop()
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Start the application
    app.start()


if __name__ == "__main__":
    main()
