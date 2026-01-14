"""
Tests for CSV format compliance and 1 Hz logging.
"""

import csv
import os
import sys
import time
import unittest
from pathlib import Path
from datetime import datetime, timezone

from csv_format import (
    COLUMN_NAMES, DEFAULT_BOAT_ID,
    create_empty_row, datetime_to_excel_serial, excel_serial_to_datetime,
    validate_csv_format, validate_1hz_timing
)
from nmea2000_logger import NMEA2000DataLogger


class TestCSVFormatSpecification(unittest.TestCase):
    """Test CSV format specification module"""
    
    def test_column_count(self):
        """Test that we have exactly 181 columns"""
        self.assertEqual(len(COLUMN_NAMES), 181)
    
    def test_column_names_match_reference(self):
        """Test that column names match the reference CSV"""
        # Load reference CSV header
        reference_file = Path(__file__).parent / 'data_examples' / '2021Nov14 (1).csv'
        with open(reference_file, 'r', encoding='utf-8') as f:
            header = f.readline().strip()
            reference_columns = header.split(',')
        
        # Compare each column
        self.assertEqual(len(COLUMN_NAMES), len(reference_columns))
        for i, (expected, actual) in enumerate(zip(reference_columns, COLUMN_NAMES)):
            self.assertEqual(expected, actual, f"Column {i} mismatch")
    
    def test_datetime_to_excel_serial(self):
        """Test datetime to Excel serial conversion"""
        # Test known value from reference CSV
        # 2021-11-14 00:59:54.931200 ≈ 44514.041608
        dt = datetime(2021, 11, 14, 0, 59, 54, 931200, tzinfo=timezone.utc)
        serial = datetime_to_excel_serial(dt)
        self.assertAlmostEqual(serial, 44514.041608, places=5)
    
    def test_excel_serial_to_datetime(self):
        """Test Excel serial to datetime conversion"""
        serial = 44514.041608
        dt = excel_serial_to_datetime(serial)
        self.assertEqual(dt.year, 2021)
        self.assertEqual(dt.month, 11)
        self.assertEqual(dt.day, 14)
    
    def test_create_empty_row(self):
        """Test empty row creation"""
        row = create_empty_row()
        
        # Check all columns present
        self.assertEqual(len(row), 181)
        for col in COLUMN_NAMES:
            self.assertIn(col, row)
        
        # Check boat ID and UTC are set
        self.assertEqual(row['Boat'], DEFAULT_BOAT_ID)
        self.assertIsInstance(row['Utc'], float)
        
        # Check other fields are empty strings
        for col in COLUMN_NAMES:
            if col not in ['Boat', 'Utc']:
                self.assertEqual(row[col], "")
    
    def test_validate_csv_format_with_reference(self):
        """Test format validation with reference CSV"""
        reference_file = Path(__file__).parent / 'data_examples' / '2021Nov14 (1).csv'
        is_valid, errors = validate_csv_format(str(reference_file))
        self.assertTrue(is_valid, f"Reference CSV validation failed: {errors}")
        self.assertEqual(len(errors), 0)


class TestNMEA2000Logger(unittest.TestCase):
    """Test NMEA2000 logger with 1 Hz sampling"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.test_dir = Path("/tmp/honkey_pi_test_csv")
        self.test_dir.mkdir(parents=True, exist_ok=True)
        
        # Clean up any existing CSV files
        for csv_file in self.test_dir.glob("*.csv"):
            csv_file.unlink()
    
    def tearDown(self):
        """Clean up test files"""
        for csv_file in self.test_dir.glob("*.csv"):
            csv_file.unlink()
    
    def test_logger_creates_correct_format(self):
        """Test that logger creates CSV with correct format"""
        logger = NMEA2000DataLogger(
            data_directory=str(self.test_dir),
            filename_format="test_%Y%m%d.csv",
            flush_interval=1
        )
        
        try:
            # Start logging
            logger.start_logging()
            
            # Send some test messages
            test_messages = [
                {
                    'PGN': 128259,
                    'description': 'Speed',
                    'fields': [{'id': 'speed_water_referenced', 'value': 10.5}]
                },
                {
                    'PGN': 128267,
                    'description': 'Water Depth',
                    'fields': [{'id': 'depth', 'value': 15.0}]
                }
            ]
            
            for msg in test_messages:
                logger.log_message(msg)
            
            # Wait for at least 2 seconds to get 2 log entries
            time.sleep(2.5)
            
        finally:
            logger.close()
        
        # Find the created CSV file
        csv_files = list(self.test_dir.glob("*.csv"))
        self.assertEqual(len(csv_files), 1, "Should create exactly one CSV file")
        
        csv_file = csv_files[0]
        
        # Validate format
        is_valid, errors = validate_csv_format(str(csv_file))
        self.assertTrue(is_valid, f"CSV format validation failed: {errors}")
        
        # Check header
        with open(csv_file, 'r', encoding='utf-8') as f:
            header = f.readline().strip()
            header_columns = header.split(',')
            self.assertEqual(len(header_columns), 181)
            
            # Check version line
            version_line = f.readline().strip()
            self.assertTrue(version_line.startswith('!v'))
            
            # Check we have data rows
            data_lines = f.readlines()
            self.assertGreaterEqual(len(data_lines), 2, "Should have at least 2 data rows")
    
    def test_1hz_logging_frequency(self):
        """Test that logging occurs at 1 Hz"""
        logger = NMEA2000DataLogger(
            data_directory=str(self.test_dir),
            filename_format="test_timing_%Y%m%d.csv",
            flush_interval=1
        )
        
        try:
            # Start logging
            logger.start_logging()
            
            # Let it run for 5 seconds to collect data
            time.sleep(5.5)
            
        finally:
            logger.close()
        
        # Find the created CSV file
        csv_files = list(self.test_dir.glob("test_timing*.csv"))
        self.assertEqual(len(csv_files), 1)
        
        csv_file = csv_files[0]
        
        # Validate 1 Hz timing
        is_valid, errors = validate_1hz_timing(str(csv_file), tolerance=0.2)
        self.assertTrue(is_valid, f"1 Hz timing validation failed: {errors}")
        
        # Check we have approximately 5 rows (±1)
        with open(csv_file, 'r', encoding='utf-8') as f:
            # Skip header and version
            f.readline()
            f.readline()
            data_rows = f.readlines()
            
            self.assertGreaterEqual(len(data_rows), 4, "Should have at least 4 data rows")
            self.assertLessEqual(len(data_rows), 6, "Should have at most 6 data rows")
    
    def test_data_mapping(self):
        """Test that NMEA2000 fields map correctly to CSV columns"""
        logger = NMEA2000DataLogger(
            data_directory=str(self.test_dir),
            filename_format="test_mapping_%Y%m%d.csv",
            flush_interval=1
        )
        
        try:
            # Start logging first
            logger.start_logging()
            
            # Wait 0.2 s (~20% of the 1 s logging interval) so the first empty row is logged
            time.sleep(0.2)
            
            # Now send messages with known values
            logger.log_message({
                'PGN': 128259,
                'fields': [{'id': 'speed_water_referenced', 'value': 12.5}]
            })
            
            logger.log_message({
                'PGN': 128267,
                'fields': [{'id': 'depth', 'value': 20.3}]
            })
            
            logger.log_message({
                'PGN': 127250,
                'fields': [{'id': 'heading', 'value': 45.0}]
            })
            
            # Wait for at least one more logging cycle to capture the values.
            # 1.5 seconds ensures at least one full 1 Hz logging interval completes
            # after the messages are sent, with some extra margin.
            time.sleep(1.5)
            
            # Manually flush to ensure data is written
            if logger.csv_file:
                logger.csv_file.flush()
            
            # Find CSV file before closing
            csv_files = list(self.test_dir.glob("test_mapping*.csv"))
            self.assertEqual(len(csv_files), 1, "Should create exactly one CSV file")
            csv_file = csv_files[0]
            
            # Read and check values before closing logger
            with open(csv_file, 'r', encoding='utf-8') as f:
                # Skip header line
                header = f.readline().strip()
                # Skip version line
                _ = f.readline().strip()
                
                # Read all remaining lines
                data_lines = f.readlines()
                self.assertGreater(len(data_lines), 1, "Should have at least two data rows")
                
                # Create reader with header
                reader = csv.DictReader([header] + data_lines)
                
                # Skip first row (may be empty/before messages)
                next(reader)
                
                # Read second data row (should have our values)
                row = next(reader)
                
                # Check mapped values (they should exist and not be empty strings)
                self.assertNotEqual(row['BSP'], '', "BSP should have a value")
                self.assertEqual(float(row['BSP']), 12.5, "BSP should be mapped from speed")
                self.assertNotEqual(row['Depth'], '', "Depth should have a value")
                self.assertEqual(float(row['Depth']), 20.3, "Depth should be mapped")
                self.assertNotEqual(row['HDG'], '', "HDG should have a value")
                self.assertEqual(float(row['HDG']), 45.0, "Heading should be mapped")
            
        finally:
            logger.close()
    
    def test_timing_error_detection(self):
        """Test that timing errors are detected and reported"""
        logger = NMEA2000DataLogger(
            data_directory=str(self.test_dir),
            filename_format="test_errors_%Y%m%d.csv",
            flush_interval=1
        )
        
        try:
            logger.start_logging()
            time.sleep(2.0)
            
            # Check if any timing errors occurred
            stats = logger.get_statistics()
            # We expect very few or no timing errors under normal conditions
            self.assertLess(stats['timing_errors'], 5, 
                          "Should have minimal timing errors")
            
        finally:
            logger.close()
    
    def test_permission_error_handling(self):
        """Test that permission errors are caught and reported with helpful message"""
        # Try to create logger in a directory we can't write to
        # On Unix systems, /root is typically not writable by normal users
        # Skip test if running as root/administrator
        if sys.platform == 'win32':
            # On Windows, skip this test as it's difficult to test permissions portably
            self.skipTest("Permission test not applicable on Windows")
        elif hasattr(os, 'geteuid') and os.geteuid() == 0:
            self.skipTest("Test requires non-root user")
        
        unwritable_dir = "/root/honkey_pi_test_permission"
        
        with self.assertRaises(PermissionError) as context:
            logger = NMEA2000DataLogger(
                data_directory=unwritable_dir,
                filename_format="test_%Y%m%d.csv",
                flush_interval=1
            )
        
        # Check that error message contains helpful information
        error_message = str(context.exception)
        self.assertIn("Cannot create data directory", error_message)
        self.assertIn("Possible solutions", error_message)
        self.assertIn("config.yaml", error_message)


def run_tests():
    """Run all tests"""
    # Create test suite
    suite = unittest.TestLoader().loadTestsFromModule(__import__(__name__))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    exit(run_tests())
