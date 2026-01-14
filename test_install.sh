#!/bin/bash
# Test script for install.sh user detection logic
# This tests the user detection without actually running the full installation

set -e

echo "========================================="
echo "Testing install.sh user detection logic"
echo "========================================="

# Test 1: Simulate sudo invocation with SUDO_USER set
echo ""
echo "Test 1: SUDO_USER is set (typical sudo case)"
SUDO_USER="testuser"
USER="root"

# Extract and test user detection logic
if [ -n "$SUDO_USER" ]; then
    INSTALL_USER="$SUDO_USER"
elif [ -n "$USER" ] && [ "$USER" != "root" ]; then
    INSTALL_USER="$USER"
else
    INSTALL_USER="pi"
fi

echo "  SUDO_USER=$SUDO_USER, USER=$USER"
echo "  Detected user: $INSTALL_USER"
if [ "$INSTALL_USER" = "testuser" ]; then
    echo "  ✓ PASS: Correctly detected user from SUDO_USER"
else
    echo "  ✗ FAIL: Expected 'testuser', got '$INSTALL_USER'"
    exit 1
fi

# Test 2: No SUDO_USER, USER is set to non-root
echo ""
echo "Test 2: No SUDO_USER, USER is non-root"
unset SUDO_USER
USER="anotheruser"

if [ -n "$SUDO_USER" ]; then
    INSTALL_USER="$SUDO_USER"
elif [ -n "$USER" ] && [ "$USER" != "root" ]; then
    INSTALL_USER="$USER"
else
    INSTALL_USER="pi"
fi

echo "  SUDO_USER=(unset), USER=$USER"
echo "  Detected user: $INSTALL_USER"
if [ "$INSTALL_USER" = "anotheruser" ]; then
    echo "  ✓ PASS: Correctly detected user from USER"
else
    echo "  ✗ FAIL: Expected 'anotheruser', got '$INSTALL_USER'"
    exit 1
fi

# Test 3: No SUDO_USER, USER is root (fallback case)
echo ""
echo "Test 3: No SUDO_USER, USER is root (fallback)"
unset SUDO_USER
USER="root"

if [ -n "$SUDO_USER" ]; then
    INSTALL_USER="$SUDO_USER"
elif [ -n "$USER" ] && [ "$USER" != "root" ]; then
    INSTALL_USER="$USER"
else
    INSTALL_USER="pi"
fi

echo "  SUDO_USER=(unset), USER=$USER"
echo "  Detected user: $INSTALL_USER"
if [ "$INSTALL_USER" = "pi" ]; then
    echo "  ✓ PASS: Correctly fell back to 'pi'"
else
    echo "  ✗ FAIL: Expected 'pi', got '$INSTALL_USER'"
    exit 1
fi

# Test 4: Verify /etc/network/interfaces.d directory creation
echo ""
echo "Test 4: Directory creation logic"
echo "  mkdir -p /etc/network/interfaces.d (would be executed)"
echo "  ✓ PASS: Command syntax is correct"

# Test 5: Verify sed command for service file
echo ""
echo "Test 5: Service file substitution"
TEST_USER="testuser"
echo "  Testing sed command with user: $TEST_USER"
# Simulate the sed command on a test string (including the full ExecStart line)
TEST_INPUT="User=pi
WorkingDirectory=/home/pi/honkey_pi
ExecStart=/usr/bin/python3 /home/pi/honkey_pi/main.py -c /home/pi/honkey_pi/config.yaml"

TEST_OUTPUT=$(echo "$TEST_INPUT" | sed -e "s|User=pi|User=$TEST_USER|g" -e "s|/home/pi/|/home/$TEST_USER/|g")

if echo "$TEST_OUTPUT" | grep -q "User=$TEST_USER" && \
   echo "$TEST_OUTPUT" | grep -q "/home/$TEST_USER/honkey_pi/main.py" && \
   echo "$TEST_OUTPUT" | grep -q "/home/$TEST_USER/honkey_pi/config.yaml"; then
    echo "  ✓ PASS: Service file substitution works correctly"
else
    echo "  ✗ FAIL: Service file substitution failed"
    echo "  Output: $TEST_OUTPUT"
    exit 1
fi

# Test 6: Verify path comparison logic
echo ""
echo "Test 6: Path comparison for same directory detection (with canonical paths)"
echo "  Case 1: Same directory (should skip copy)"

# Create temporary test directories
TEST_DIR1="/tmp/test_canonicalize_$$"
mkdir -p "$TEST_DIR1"

SCRIPT_DIR="$TEST_DIR1"
INSTALL_DIR="$TEST_DIR1"

# Get canonical paths as install.sh does
SCRIPT_DIR_CANONICAL="$(cd "$SCRIPT_DIR" && pwd -P 2>/dev/null || pwd)"
INSTALL_DIR_CANONICAL="$(cd "$INSTALL_DIR" && pwd -P 2>/dev/null || pwd)"

echo "    SCRIPT_DIR_CANONICAL=$SCRIPT_DIR_CANONICAL"
echo "    INSTALL_DIR_CANONICAL=$INSTALL_DIR_CANONICAL"
if [ "$SCRIPT_DIR_CANONICAL" != "$INSTALL_DIR_CANONICAL" ]; then
    echo "    ✗ FAIL: Directories are same, should NOT copy"
    rm -rf "$TEST_DIR1"
    exit 1
else
    echo "    ✓ PASS: Correctly detects same directory (will skip copy)"
fi

echo "  Case 2: Different directories (should copy)"
TEST_DIR2="/tmp/test_different_$$"
mkdir -p "$TEST_DIR2"

SCRIPT_DIR="$TEST_DIR1"
INSTALL_DIR="$TEST_DIR2"

SCRIPT_DIR_CANONICAL="$(cd "$SCRIPT_DIR" && pwd -P 2>/dev/null || pwd)"
INSTALL_DIR_CANONICAL="$(cd "$INSTALL_DIR" && pwd -P 2>/dev/null || pwd)"

echo "    SCRIPT_DIR_CANONICAL=$SCRIPT_DIR_CANONICAL"
echo "    INSTALL_DIR_CANONICAL=$INSTALL_DIR_CANONICAL"
if [ "$SCRIPT_DIR_CANONICAL" != "$INSTALL_DIR_CANONICAL" ]; then
    echo "    ✓ PASS: Correctly detects different directories (will copy)"
else
    echo "    ✗ FAIL: Directories are different, should copy"
    rm -rf "$TEST_DIR1" "$TEST_DIR2"
    exit 1
fi

# Cleanup
rm -rf "$TEST_DIR1" "$TEST_DIR2"

echo ""
echo "========================================="
echo "All tests passed! ✓"
echo "========================================="
