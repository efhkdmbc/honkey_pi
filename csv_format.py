"""
CSV format specification for Honkey Pi data logging.
This module defines the exact format required to match the reference CSV file.
"""

import datetime
from typing import Dict, Any, Optional

# Exact column names and order from reference CSV (2021Nov14 (1).csv)
# Total of 181 columns
COLUMN_NAMES = [
    "Boat", "Utc", "BSP", "AWA", "AWS", "TWA", "TWS", "TWD", "RudderFwd", "Leeway",
    "Set", "Drift", "HDG", "AirTemp", "SeaTemp", "Baro", "Depth", "Heel", "Trim", "Rudder",
    "Tab", "Forestay", "Downhaul", "MastAng", "FStayLen", "MastButt", "Load S", "Load P", "Rake", "Volts",
    "ROT", "GpQual", "PDOP", "GpsNum", "GpsAge", "Altitude", "GeoSep", "GpsMode", "Lat", "Lon",
    "COG", "SOG", "DiffStn", "Error", "RunnerS", "RunnerP", "Vang", "Trav", "Main", "KeelAng",
    "KeelHt", "Board", "EngOilPres", "RPM 1", "RPM 2", "Board P", "Board S", "DistToLn", "RchTmToLn", "RchDtToLn",
    "GPS time", "TWD+90", "TWD-90", "Downhaul2", "Mk Lat", "Mk Lon", "Port lat", "Port lon", "Stbd lat", "Stbd lon",
    "HPE", "RH", "Lead P", "Lead S", "BackStay", "User 0", "User 1", "User 2", "User 3", "User 4",
    "User 5", "User 6", "User 7", "User 8", "User 9", "User 10", "User 11", "User 12", "User 13", "User 14",
    "User 15", "User 16", "User 17", "User 18", "User 19", "User 20", "User 21", "User 22", "User 23", "User 24",
    "User 25", "User 26", "User 27", "User 28", "User 29", "User 30", "User 31", "TmToGun", "TmToLn", "Burn",
    "BelowLn", "GunBlwLn", "WvSigHt", "WvSigPd", "WvMaxHt", "WvMaxPd", "Slam", "Heave", "MWA", "MWS",
    "Boom", "Twist", "TackLossT", "TackLossD", "TrimRate", "HeelRate", "DeflectorP", "RudderP", "RudderS", "RudderToe",
    "BspTr", "FStayInner", "DeflectorS", "Bobstay", "Outhaul", "D0 P", "D0 S", "D1 P", "D1 S", "V0 P",
    "V0 S", "V1 P", "V1 S", "BoomAng", "Cunningham", "FStayInHal", "JibFurl", "JibH", "MastCant", "J1",
    "J2", "J3", "J4", "Foil P", "Foil S", "Reacher", "Blade", "Staysail", "Solent", "Tack",
    "TackP", "TackS", "DeflectU", "DeflectL", "WinchP", "WinchS", "SpinP", "SpinS", "MainH", "Mast2",
    "DepthAft", "Burn%", "GunBspTarg%", "GunBspPol%", "EngTemp", "EngOilTemp", "TranOilTemp", "TranOilPres", "FuelLevel", "Amps",
    "Charge%"
]

# Format version string (appears as second line in CSV)
FORMAT_VERSION = "!v11.10.18"

# Boat identifier (appears as first column value in all data rows)
DEFAULT_BOAT_ID = "0"


def datetime_to_excel_serial(dt: datetime.datetime) -> float:
    """
    Convert datetime to Excel serial date number (days since 1899-12-30).
    
    Args:
        dt: Datetime to convert
        
    Returns:
        Excel serial date number
    """
    base = datetime.datetime(1899, 12, 30, tzinfo=dt.tzinfo)
    delta = dt - base
    return delta.total_seconds() / 86400.0


def excel_serial_to_datetime(serial: float) -> datetime.datetime:
    """
    Convert Excel serial date number to datetime.
    
    Args:
        serial: Excel serial date number
        
    Returns:
        Datetime object
    """
    base = datetime.datetime(1899, 12, 30)
    return base + datetime.timedelta(days=serial)


def create_empty_row(boat_id: str = DEFAULT_BOAT_ID, utc_timestamp: Optional[float] = None) -> Dict[str, Any]:
    """
    Create an empty CSV row with all columns initialized to empty strings.
    
    Args:
        boat_id: Boat identifier (default: "0")
        utc_timestamp: UTC timestamp as Excel serial number (default: current time)
        
    Returns:
        Dictionary with all column names as keys, values initialized appropriately
    """
    if utc_timestamp is None:
        utc_timestamp = datetime_to_excel_serial(datetime.datetime.now(datetime.timezone.utc))
    
    row = {col: "" for col in COLUMN_NAMES}
    row["Boat"] = boat_id
    row["Utc"] = utc_timestamp
    return row


def validate_csv_format(csv_file_path: str) -> tuple[bool, list[str]]:
    """
    Validate that a CSV file matches the required format.
    
    Args:
        csv_file_path: Path to CSV file to validate
        
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []
    
    try:
        with open(csv_file_path, 'r', encoding='utf-8') as f:
            # Check header line
            header_line = f.readline().strip()
            header_columns = header_line.split(',')
            
            if len(header_columns) != len(COLUMN_NAMES):
                errors.append(
                    f"Column count mismatch: expected {len(COLUMN_NAMES)}, got {len(header_columns)}"
                )
            
            # Check each column name
            for i, (expected, actual) in enumerate(zip(COLUMN_NAMES, header_columns)):
                if expected != actual:
                    errors.append(
                        f"Column {i} mismatch: expected '{expected}', got '{actual}'"
                    )
            
            # Check version line
            version_line = f.readline().strip()
            if not version_line.startswith('!v'):
                errors.append(
                    f"Version line format error: expected '!v...', got '{version_line}'"
                )
            
    except FileNotFoundError:
        errors.append(f"File not found: {csv_file_path}")
    except Exception as e:
        errors.append(f"Error reading file: {e}")
    
    return len(errors) == 0, errors


def validate_1hz_timing(csv_file_path: str, tolerance: float = 0.2) -> tuple[bool, list[str]]:
    """
    Validate that a CSV file has data logged at approximately 1 Hz.
    
    Args:
        csv_file_path: Path to CSV file to validate
        tolerance: Acceptable deviation from 1.0 second (default: 0.2 seconds)
        
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []
    
    try:
        with open(csv_file_path, 'r', encoding='utf-8') as f:
            # Skip header and version line
            f.readline()
            f.readline()
            
            timestamps = []
            for line in f:
                parts = line.strip().split(',')
                if len(parts) > 1 and parts[1]:
                    try:
                        ts = float(parts[1])
                        timestamps.append(ts)
                    except ValueError:
                        pass
            
            if len(timestamps) < 2:
                errors.append("Insufficient data rows for timing validation")
                return False, errors
            
            # Check intervals between consecutive timestamps
            intervals_outside_tolerance = 0
            for i in range(1, len(timestamps)):
                diff_days = timestamps[i] - timestamps[i-1]
                diff_seconds = diff_days * 86400.0
                
                if abs(diff_seconds - 1.0) > tolerance:
                    intervals_outside_tolerance += 1
            
            if intervals_outside_tolerance > 0:
                percentage = (intervals_outside_tolerance / (len(timestamps) - 1)) * 100
                errors.append(
                    f"Timing validation failed: {intervals_outside_tolerance} out of "
                    f"{len(timestamps) - 1} intervals ({percentage:.1f}%) outside "
                    f"1 Hz ± {tolerance}s tolerance"
                )
        
    except FileNotFoundError:
        errors.append(f"File not found: {csv_file_path}")
    except Exception as e:
        errors.append(f"Error reading file: {e}")
    
    return len(errors) == 0, errors
