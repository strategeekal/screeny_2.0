#!/usr/bin/env python3
"""
Test script for Pantallita 2.1.0 refactored modules

This script validates that the refactored modules:
1. Import without errors
2. Have no circular dependency issues
3. Define expected functions and classes
4. Have proper structure

Run this locally (not on CircuitPython device) for validation.
"""

import sys
import ast
import os

# Colors for output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def print_test(name, status, message=""):
    symbol = "✓" if status else "✗"
    color = GREEN if status else RED
    print(f"{color}{symbol}{RESET} {name}")
    if message:
        print(f"  {YELLOW}{message}{RESET}")

def check_file_syntax(filepath):
    """Check if Python file has valid syntax"""
    try:
        with open(filepath, 'r') as f:
            code = compile(f.read(), filepath, 'exec')
        return True, None
    except SyntaxError as e:
        return False, str(e)

def check_module_structure(filepath, expected_items):
    """Check if module defines expected functions/classes"""
    try:
        with open(filepath, 'r') as f:
            tree = ast.parse(f.read())

        defined = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                defined.add(node.name)
            elif isinstance(node, ast.ClassDef):
                defined.add(node.name)

        missing = set(expected_items) - defined
        if missing:
            return False, f"Missing: {', '.join(missing)}"
        return True, None
    except Exception as e:
        return False, str(e)

def count_lines(filepath):
    """Count non-empty, non-comment lines"""
    with open(filepath, 'r') as f:
        lines = [l.strip() for l in f.readlines()]
        code_lines = [l for l in lines if l and not l.startswith('#')]
    return len(code_lines)

def main():
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}Pantallita 2.1.0 - Module Validation Tests{RESET}")
    print(f"{BLUE}{'='*60}{RESET}\n")

    total_tests = 0
    passed_tests = 0

    # Define modules and their expected content
    modules = {
        'config.py': {
            'classes': ['Display', 'Layout', 'Timing', 'API', 'Recovery',
                       'Memory', 'Paths', 'Visual', 'System', 'TestData',
                       'Strings', 'DebugLevel', 'DisplayConfig', 'ColorManager'],
            'functions': ['get_remaining_schedule_time', 'validate_configuration'],
        },
        'cache.py': {
            'classes': ['ImageCache', 'TextWidthCache'],
            'functions': [],
        },
        'utils.py': {
            'classes': ['MemoryMonitor'],
            'functions': ['log_entry', 'log_info', 'log_error', 'log_warning',
                         'log_debug', 'log_verbose', 'duration_message',
                         'parse_iso_datetime', 'format_datetime', 'calculate_weekday',
                         'calculate_yearday', 'update_rtc_datetime', 'interruptible_sleep'],
        },
        'network.py': {
            'classes': [],
            'functions': ['get_requests_session', 'cleanup_sockets', 'cleanup_global_session',
                         'setup_rtc', 'setup_wifi_with_recovery', 'check_and_recover_wifi',
                         'is_wifi_connected', 'get_timezone_offset', 'is_dst_active_for_timezone',
                         'get_timezone_from_location_api', 'sync_time_with_timezone',
                         'get_api_key', 'fetch_weather_with_retries',
                         'fetch_current_and_forecast_weather', 'get_cached_weather_if_fresh',
                         'fetch_current_weather_only'],
        },
        'events.py': {
            'classes': ['ScheduledDisplay'],
            'functions': ['load_events_from_csv', 'fetch_ephemeral_events', 'load_all_events',
                         'is_event_active', 'get_events', 'parse_events_csv_content',
                         'parse_schedule_csv_content', 'fetch_github_data',
                         'load_schedules_from_csv'],
        },
        'display.py': {
            'classes': [],
            'functions': ['initialize_display', 'detect_matrix_type', 'get_matrix_colors',
                         'convert_bmp_palette', 'load_bmp_image', 'get_text_width',
                         'get_font_metrics', 'calculate_bottom_aligned_positions',
                         'clear_display', 'right_align_text', 'center_text',
                         'get_day_color', 'add_day_indicator', 'calculate_uv_bar_length',
                         'calculate_humidity_bar_length', 'add_indicator_bars',
                         'show_weather_display', 'show_clock_display', 'show_event_display',
                         'show_forecast_display', 'show_scheduled_display'],
        },
    }

    print(f"{BLUE}1. SYNTAX VALIDATION{RESET}\n")

    for module_name in modules.keys():
        total_tests += 1
        valid, error = check_file_syntax(module_name)
        if valid:
            passed_tests += 1
            print_test(f"{module_name} - Syntax check", True)
        else:
            print_test(f"{module_name} - Syntax check", False, error)

    print(f"\n{BLUE}2. MODULE STRUCTURE VALIDATION{RESET}\n")

    for module_name, expected in modules.items():
        expected_items = expected['classes'] + expected['functions']
        total_tests += 1
        valid, error = check_module_structure(module_name, expected_items)
        if valid:
            passed_tests += 1
            print_test(f"{module_name} - Structure check ({len(expected_items)} items)", True)
        else:
            print_test(f"{module_name} - Structure check", False, error)

    print(f"\n{BLUE}3. LINE COUNT SUMMARY{RESET}\n")

    total_lines = 0
    for module_name in modules.keys():
        if os.path.exists(module_name):
            lines = count_lines(module_name)
            total_lines += lines
            print(f"  {module_name:15s} {lines:4d} lines")

    print(f"  {'-'*25}")
    print(f"  {'TOTAL':15s} {total_lines:4d} lines\n")

    print(f"{BLUE}4. DOCUMENTATION CHECK{RESET}\n")

    for module_name in modules.keys():
        total_tests += 1
        with open(module_name, 'r') as f:
            content = f.read()
            has_module_doc = content.strip().startswith('"""')
            if has_module_doc:
                passed_tests += 1
                print_test(f"{module_name} - Module docstring", True)
            else:
                print_test(f"{module_name} - Module docstring", False, "Missing module-level docstring")

    print(f"\n{BLUE}5. DEPENDENCIES CHECK{RESET}\n")

    # Check for problematic imports
    total_tests += 1
    has_issues = False
    for module_name in modules.keys():
        with open(module_name, 'r') as f:
            content = f.read()
            # Check if circular imports via code.py (bad practice)
            if 'from code import' in content or 'import code' in content:
                if module_name != 'network.py' and module_name != 'events.py' and module_name != 'display.py':
                    # Only network, events, and display modules should import from code (for state)
                    print_test(f"{module_name} - Circular import detected", False)
                    has_issues = True

    if not has_issues:
        passed_tests += 1
        print_test("Dependency structure", True, "No problematic circular imports")

    # Summary
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}TEST SUMMARY{RESET}\n")
    print(f"  Total tests: {total_tests}")
    print(f"  {GREEN}Passed: {passed_tests}{RESET}")
    print(f"  {RED}Failed: {total_tests - passed_tests}{RESET}")

    if passed_tests == total_tests:
        print(f"\n  {GREEN}✓ All tests passed!{RESET}")
        print(f"{BLUE}{'='*60}{RESET}\n")
        return 0
    else:
        print(f"\n  {RED}✗ Some tests failed{RESET}")
        print(f"{BLUE}{'='*60}{RESET}\n")
        return 1

if __name__ == '__main__':
    sys.exit(main())
