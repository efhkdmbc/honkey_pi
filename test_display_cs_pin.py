#!/usr/bin/env python3
"""
Test suite for display cs_pin configuration
Verifies that the chip select pin can be configured to avoid GPIO8 conflicts
"""

import unittest
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from display import InkyDisplay
from main import HonkeyPi
import yaml


class TestDisplayCSPin(unittest.TestCase):
    """Test cases for display chip select pin configuration"""

    def test_default_cs_pin(self):
        """Test that default cs_pin is 7 (GPIO7/CE1)"""
        display = InkyDisplay()
        self.assertEqual(display.cs_pin, 7, "Default cs_pin should be 7 (CE1)")

    def test_custom_cs_pin(self):
        """Test that custom cs_pin can be set"""
        display = InkyDisplay(cs_pin=8)
        self.assertEqual(display.cs_pin, 8, "Custom cs_pin should be 8")
        
        display2 = InkyDisplay(cs_pin=25)
        self.assertEqual(display2.cs_pin, 25, "Custom cs_pin should be 25")

    def test_config_yaml_has_cs_pin(self):
        """Test that config.yaml contains cs_pin setting"""
        config_path = Path(__file__).parent / "config.yaml"
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        self.assertIn('display', config, "Config should have display section")
        self.assertIn('cs_pin', config['display'], "Display config should have cs_pin")
        self.assertEqual(config['display']['cs_pin'], 7, "Default cs_pin in config should be 7")

    def test_main_reads_cs_pin_from_config(self):
        """Test that HonkeyPi reads cs_pin from configuration"""
        # Create a temporary config with writable data directory
        import tempfile
        import os
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Read original config
            config_path = Path(__file__).parent / "config.yaml"
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            # Modify to use temporary directory
            config['logging']['data_directory'] = tmpdir
            
            # Write temporary config
            temp_config_path = os.path.join(tmpdir, 'test_config.yaml')
            with open(temp_config_path, 'w') as f:
                yaml.dump(config, f)
            
            # Test with temporary config
            app = HonkeyPi(config_path=temp_config_path)
            
            # Verify display was initialized with correct cs_pin
            self.assertEqual(app.display.cs_pin, 7, "HonkeyPi should initialize display with cs_pin from config")

    def test_default_config_has_cs_pin(self):
        """Test that default configuration includes cs_pin"""
        # Create a temporary config to test default config loading
        import tempfile
        import os
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Test with non-existent config to trigger default config
            temp_config_path = os.path.join(tmpdir, 'nonexistent_config.yaml')
            
            # Mock the config loading to access default config
            app = HonkeyPi.__new__(HonkeyPi)
            default_config = app._get_default_config()
            
            self.assertIn('display', default_config, "Default config should have display section")
            self.assertIn('cs_pin', default_config['display'], "Default display config should have cs_pin")
            self.assertEqual(default_config['display']['cs_pin'], 7, "Default cs_pin should be 7")

    def test_display_dimensions_still_work(self):
        """Test that display dimensions are still properly detected"""
        display = InkyDisplay(cs_pin=7)
        
        # Should have valid dimensions
        self.assertIsInstance(display.width, int, "Width should be an integer")
        self.assertIsInstance(display.height, int, "Height should be an integer")
        self.assertGreater(display.width, 0, "Width should be positive")
        self.assertGreater(display.height, 0, "Height should be positive")
        
        # Default dimensions for Inky pHAT
        self.assertEqual(display.width, 212, "Default width should be 212")
        self.assertEqual(display.height, 104, "Default height should be 104")


class TestCSPinDocumentation(unittest.TestCase):
    """Test that documentation properly covers the cs_pin feature"""

    def test_readme_mentions_cs_pin(self):
        """Test that README.md mentions cs_pin configuration"""
        readme_path = Path(__file__).parent / "README.md"
        with open(readme_path, 'r') as f:
            readme_content = f.read()
        
        self.assertIn('cs_pin', readme_content, "README should mention cs_pin")
        self.assertIn('GPIO8', readme_content, "README should mention GPIO8 conflict")
        self.assertIn('GPIO7', readme_content, "README should mention GPIO7 solution")

    def test_hardware_setup_mentions_cs_pin(self):
        """Test that HARDWARE_SETUP.md mentions cs_pin configuration"""
        hardware_path = Path(__file__).parent / "HARDWARE_SETUP.md"
        with open(hardware_path, 'r') as f:
            hardware_content = f.read()
        
        self.assertIn('cs_pin', hardware_content, "HARDWARE_SETUP should mention cs_pin")
        self.assertIn('GPIO8', hardware_content, "HARDWARE_SETUP should mention GPIO8 conflict")
        self.assertIn('CE1', hardware_content, "HARDWARE_SETUP should mention CE1")


def main():
    """Run all tests"""
    print("=" * 60)
    print("Testing Display CS Pin Configuration")
    print("=" * 60)
    print()
    
    # Run tests
    suite = unittest.TestLoader().loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print()
    print("=" * 60)
    if result.wasSuccessful():
        print("All CS Pin tests passed!")
        return 0
    else:
        print(f"Some tests failed: {len(result.failures)} failures, {len(result.errors)} errors")
        return 1


if __name__ == "__main__":
    sys.exit(main())
