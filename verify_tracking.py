#!/usr/bin/env python3
"""
Verification script for StateTracker refactoring
Run this before deploying to MatrixPortal S3 hardware
"""

import re
import sys

def check_syntax():
    """Verify Python syntax"""
    print("=" * 60)
    print("1. SYNTAX CHECK")
    print("=" * 60)
    try:
        import py_compile
        py_compile.compile('code.py', doraise=True)
        print("✅ PASS: Python syntax valid")
        return True
    except SyntaxError as e:
        print(f"❌ FAIL: Syntax error: {e}")
        return False

def check_statetracker_exists():
    """Verify StateTracker class exists"""
    print("\n" + "=" * 60)
    print("2. STATETRACKER CLASS CHECK")
    print("=" * 60)
    with open('code.py', 'r') as f:
        content = f.read()

    if 'class StateTracker:' in content:
        print("✅ PASS: StateTracker class found")
        return True
    else:
        print("❌ FAIL: StateTracker class not found")
        return False

def check_initialization():
    """Verify all tracking fields are initialized"""
    print("\n" + "=" * 60)
    print("3. FIELD INITIALIZATION CHECK")
    print("=" * 60)

    required_fields = [
        'api_call_count',
        'current_api_calls',
        'forecast_api_calls',
        'consecutive_failures',
        'last_successful_weather',
        'wifi_reconnect_attempts',
        'last_wifi_attempt',
        'system_error_count',
        'in_extended_failure_mode',
        'scheduled_display_error_count',
        'consecutive_display_errors',
        'has_permanent_error'
    ]

    with open('code.py', 'r') as f:
        content = f.read()

    # Find StateTracker __init__
    init_match = re.search(r'class StateTracker:.*?def __init__\(self\):(.*?)(?=\n\tdef |\nclass )', content, re.DOTALL)

    if not init_match:
        print("❌ FAIL: Could not find StateTracker.__init__")
        return False

    init_code = init_match.group(1)

    missing = []
    found = []
    for field in required_fields:
        if f'self.{field}' in init_code:
            found.append(field)
        else:
            missing.append(field)

    print(f"Found {len(found)}/{len(required_fields)} required fields:")
    for field in found:
        print(f"  ✓ {field}")

    if missing:
        print(f"\n❌ FAIL: Missing fields:")
        for field in missing:
            print(f"  ✗ {field}")
        return False

    print("\n✅ PASS: All tracking fields initialized")
    return True

def check_tracker_usage():
    """Verify state.tracker is used instead of direct state access"""
    print("\n" + "=" * 60)
    print("4. TRACKER USAGE CHECK")
    print("=" * 60)

    with open('code.py', 'r') as f:
        lines = f.readlines()

    # Fields that should go through tracker
    tracking_fields = [
        'api_call_count',
        'current_api_calls',
        'forecast_api_calls',
        'consecutive_failures',
        'last_successful_weather',
        'wifi_reconnect_attempts',
        'system_error_count',
        'in_extended_failure_mode',
        'has_permanent_error',
        'scheduled_display_error_count',
        'consecutive_display_errors',
        'last_wifi_attempt'
    ]

    violations = []
    for line_num, line in enumerate(lines, 1):
        # Skip class definitions and comments
        if 'class StateTracker' in line or 'class WeatherDisplayState' in line:
            continue
        if line.strip().startswith('#'):
            continue

        # Look for direct state access (not through tracker)
        for field in tracking_fields:
            # Match state.field but not state.tracker.field
            pattern = rf'\bstate\.{field}\b'
            tracker_pattern = rf'\bstate\.tracker\.{field}\b'

            if re.search(pattern, line) and not re.search(tracker_pattern, line):
                # Exclude lines inside class definitions
                if 'self.' not in line:
                    violations.append((line_num, line.strip(), field))

    if violations:
        print(f"❌ FAIL: Found {len(violations)} direct state access (should use state.tracker):")
        for line_num, line, field in violations[:10]:  # Show first 10
            print(f"  Line {line_num}: {field}")
            print(f"    {line[:80]}")
        if len(violations) > 10:
            print(f"  ... and {len(violations) - 10} more")
        return False

    print("✅ PASS: All tracking access goes through state.tracker")
    return True

def check_methods_exist():
    """Verify StateTracker has required methods"""
    print("\n" + "=" * 60)
    print("5. METHOD EXISTENCE CHECK")
    print("=" * 60)

    required_methods = [
        'record_api_success',
        'get_api_stats',
        'reset_api_counters',
        'record_weather_success',
        'record_weather_failure',
        'record_display_error',
        'reset_display_errors',
        'should_soft_reset',
        'should_hard_reset',
        'should_preventive_restart',
        'should_enter_extended_failure_mode',
        'reset_after_soft_reset'
    ]

    with open('code.py', 'r') as f:
        content = f.read()

    missing = []
    found = []
    for method in required_methods:
        if f'def {method}(self' in content:
            found.append(method)
        else:
            missing.append(method)

    print(f"Found {len(found)}/{len(required_methods)} required methods:")
    for method in found:
        print(f"  ✓ {method}()")

    if missing:
        print(f"\n❌ FAIL: Missing methods:")
        for method in missing:
            print(f"  ✗ {method}()")
        return False

    print("\n✅ PASS: All required methods exist")
    return True

def check_critical_bug_fix():
    """Verify consecutive_display_errors is initialized"""
    print("\n" + "=" * 60)
    print("6. CRITICAL BUG FIX CHECK")
    print("=" * 60)

    with open('code.py', 'r') as f:
        content = f.read()

    # Check if consecutive_display_errors is initialized in StateTracker
    if 'self.consecutive_display_errors = 0' in content:
        print("✅ PASS: consecutive_display_errors properly initialized")
        print("  (This fixes a critical bug that would have caused AttributeError)")
        return True
    else:
        print("❌ FAIL: consecutive_display_errors not initialized")
        return False

def check_removed_dead_code():
    """Verify dead counters were removed"""
    print("\n" + "=" * 60)
    print("7. DEAD CODE REMOVAL CHECK")
    print("=" * 60)

    with open('code.py', 'r') as f:
        content = f.read()

    dead_fields = [
        'http_requests_total',
        'http_requests_success',
        'http_requests_failed',
        'session_cleanup_count',
        'ephemeral_event_count',
        'permanent_event_count',
        'total_event_count'
    ]

    # These are still used for event tracking (not dead)
    still_used = ['ephemeral_event_count', 'permanent_event_count', 'total_event_count']

    removed = []
    still_present = []

    for field in dead_fields:
        if field in still_used:
            # These should still be present
            if f'state.{field}' in content:
                removed.append(field + " (kept - still used)")
        else:
            # These should be removed
            if f'state.{field}' not in content and f'self.{field}' not in content:
                removed.append(field)
            else:
                still_present.append(field)

    if still_present:
        print(f"⚠️  WARNING: {len(still_present)} dead fields still present:")
        for field in still_present:
            print(f"  • {field}")
        print("  (These are unused and could be removed)")
    else:
        print("✅ PASS: Dead HTTP tracking fields removed")

    return True  # Not a critical failure

def main():
    """Run all verification checks"""
    print("\n" + "=" * 60)
    print("STATETRACKER REFACTORING VERIFICATION")
    print("=" * 60)
    print("Verifying code.py before deployment to MatrixPortal S3\n")

    checks = [
        check_syntax,
        check_statetracker_exists,
        check_initialization,
        check_methods_exist,
        check_tracker_usage,
        check_critical_bug_fix,
        check_removed_dead_code
    ]

    results = []
    for check in checks:
        try:
            result = check()
            results.append(result)
        except Exception as e:
            print(f"\n❌ ERROR in {check.__name__}: {e}")
            results.append(False)

    # Summary
    print("\n" + "=" * 60)
    print("VERIFICATION SUMMARY")
    print("=" * 60)
    passed = sum(results)
    total = len(results)

    print(f"\nPassed: {passed}/{total} checks")

    if all(results):
        print("\n✅ ALL CHECKS PASSED")
        print("\nCode is ready for deployment to MatrixPortal S3!")
        print("\nRecommended next steps:")
        print("1. Review TESTING_GUIDE.md for deployment strategy")
        print("2. Deploy to ONE device first")
        print("3. Monitor serial output for 30-60 minutes")
        print("4. If stable, deploy to second device")
        return 0
    else:
        print("\n❌ SOME CHECKS FAILED")
        print("\nPlease review failures above before deploying.")
        print("Do NOT deploy to hardware until all checks pass.")
        return 1

if __name__ == '__main__':
    sys.exit(main())
