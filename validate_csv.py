#!/usr/bin/env python3
"""
CLI tool for validating CSV log files against the required format.
"""

import argparse
import sys
from pathlib import Path
from csv_format import validate_csv_format, validate_1hz_timing


def main():
    """Main entry point for CSV validation tool"""
    parser = argparse.ArgumentParser(
        description="Validate Honkey Pi CSV log files for format compliance and timing"
    )
    parser.add_argument(
        "csv_file",
        help="Path to CSV file to validate"
    )
    parser.add_argument(
        "--skip-timing",
        action="store_true",
        help="Skip 1 Hz timing validation"
    )
    parser.add_argument(
        "--timing-tolerance",
        type=float,
        default=0.2,
        help="Tolerance for 1 Hz timing in seconds (default: 0.2)"
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Verbose output"
    )
    
    args = parser.parse_args()
    
    # Check file exists
    csv_path = Path(args.csv_file)
    if not csv_path.exists():
        print(f"Error: File not found: {csv_path}", file=sys.stderr)
        return 1
    
    print(f"Validating CSV file: {csv_path}")
    print("=" * 60)
    
    # Validate format
    print("\n1. Checking CSV format compliance...")
    format_valid, format_errors = validate_csv_format(str(csv_path))
    
    if format_valid:
        print("   ✓ CSV format is valid")
        if args.verbose:
            print("   - Column count: 181")
            print("   - Column names match reference")
            print("   - Version line present")
    else:
        print("   ✗ CSV format validation FAILED")
        for error in format_errors:
            print(f"     - {error}")
    
    # Validate timing
    timing_valid = True
    if not args.skip_timing:
        print("\n2. Checking 1 Hz logging frequency...")
        timing_valid, timing_errors = validate_1hz_timing(
            str(csv_path),
            tolerance=args.timing_tolerance
        )
        
        if timing_valid:
            print("   ✓ 1 Hz timing is valid")
            if args.verbose:
                print(f"   - Tolerance: ±{args.timing_tolerance}s")
        else:
            print("   ✗ 1 Hz timing validation FAILED")
            for error in timing_errors:
                print(f"     - {error}")
    else:
        print("\n2. Skipping 1 Hz timing validation (--skip-timing)")
    
    # Summary
    print("\n" + "=" * 60)
    if format_valid and timing_valid:
        print("✓ All validations PASSED")
        return 0
    else:
        print("✗ Validation FAILED")
        if not format_valid:
            print("  - CSV format issues detected")
        if not timing_valid:
            print("  - 1 Hz timing issues detected")
        return 1


if __name__ == "__main__":
    sys.exit(main())
