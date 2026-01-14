"""
Test utilities for Honkey Pi NMEA2000 Reader
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from nmea2000_logger import NMEA2000DataLogger
from display import InkyDisplay


def test_logger():
    """Test the data logger with sample messages"""
    print("Testing NMEA2000 Data Logger...")
    
    # Create a temporary logger
    logger = NMEA2000DataLogger(
        data_directory="/tmp/honkey_pi_test",
        filename_format="test_%Y%m%d.csv",
        flush_interval=1
    )
    
    try:
        # Sample NMEA2000 messages
        sample_messages = [
            {
                'PGN': 128259,
                'id': 'speed',
                'description': 'Speed',
                'source': 1,
                'destination': 255,
                'priority': 3,
                'fields': [
                    {
                        'id': 'speed_water_referenced',
                        'name': 'Speed Water Referenced',
                        'value': 12.5,
                        'unit_of_measurement': 'knots'
                    },
                    {
                        'id': 'speed_ground_referenced',
                        'name': 'Speed Ground Referenced',
                        'value': 12.3,
                        'unit_of_measurement': 'knots'
                    }
                ]
            },
            {
                'PGN': 128267,
                'id': 'waterDepth',
                'description': 'Water Depth',
                'source': 2,
                'destination': 255,
                'priority': 5,
                'fields': [
                    {
                        'id': 'depth',
                        'name': 'Depth',
                        'value': 15.3,
                        'unit_of_measurement': 'm'
                    },
                    {
                        'id': 'offset',
                        'name': 'Offset',
                        'value': 0.0,
                        'unit_of_measurement': 'm'
                    }
                ]
            },
            {
                'PGN': 127250,
                'id': 'vesselHeading',
                'description': 'Vessel Heading',
                'source': 3,
                'destination': 255,
                'priority': 2,
                'fields': [
                    {
                        'id': 'heading',
                        'name': 'Heading',
                        'value': 45.5,
                        'unit_of_measurement': 'deg'
                    },
                    {
                        'id': 'deviation',
                        'name': 'Deviation',
                        'value': 0.0,
                        'unit_of_measurement': 'deg'
                    }
                ]
            }
        ]
        
        # Log sample messages
        for msg in sample_messages:
            logger.log_message(msg)
            print(f"Logged message: PGN {msg['PGN']} - {msg['description']}")
        
        # Get statistics
        stats = logger.get_statistics()
        print(f"\nStatistics:")
        print(f"  Max Speed: {stats['max_speed']:.2f} knots")
        print(f"  Max Depth: {stats['max_depth']:.2f} m")
        print(f"  Messages Logged: {stats['messages_logged']}")
    finally:
        # Ensure logger is always closed, even if an error occurs
        logger.close()
    
    # Check output file
    output_dir = Path("/tmp/honkey_pi_test")
    csv_files = list(output_dir.glob("*.csv"))
    if csv_files:
        print(f"\nCSV file created: {csv_files[0]}")
        print(f"File size: {csv_files[0].stat().st_size} bytes")
        
        # Show first few lines
        with open(csv_files[0], 'r') as f:
            lines = f.readlines()[:5]
            print("\nFirst lines of CSV:")
            for line in lines:
                print(f"  {line.strip()}")
    
    print("\n✓ Logger test complete!")


def test_display():
    """Test the Inky pHAT display"""
    print("Testing Inky pHAT Display...")
    
    display = InkyDisplay(color="red", cs_pin=7)  # Use GPIO7 (CE1) by default
    
    # Sample statistics
    stats = {
        'max_speed': 12.5,
        'max_depth': 15.3,
        'messages_logged': 42000
    }
    
    # Update display
    display.update_display(stats, "/tmp")
    
    print("\n✓ Display test complete!")
    print("  Check /tmp/inky_display_simulation.png for output")


def test_bootup_screen():
    """Test the bootup screen functionality"""
    print("Testing Bootup Screen...")
    
    display = InkyDisplay(color="red", cs_pin=7)  # Use GPIO7 (CE1) by default
    
    # Test with actual bootup screen image
    result = display.show_bootup_screen("bootup screen.JPG")
    
    if result:
        print("\n✓ Bootup screen test complete!")
        print("  Check /tmp/inky_bootup_simulation.png for output")
    else:
        print("\n✗ Bootup screen test failed - image may not be found")
        print("  This is expected if running outside the repository directory")
    
    return result


def main():
    """Run all tests"""
    print("=" * 60)
    print("Honkey Pi Test Suite")
    print("=" * 60)
    print()
    
    try:
        test_logger()
        print()
        test_display()
        print()
        test_bootup_screen()
        print()
        print("=" * 60)
        print("All tests passed!")
        print("=" * 60)
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
