#!/usr/bin/env python3
"""
Pytest-powered Master Test Runner for all API tests.

This script uses pytest to discover and run all test suites in the api_tests/ directory.
It provides concise live output and detailed summary reporting.
"""

from dotenv import load_dotenv
import os
import sys
import subprocess
import json
import logging
from typing import Optional


# Standard Project Root Setup
_THIS_SCRIPT_ABSPATH = os.path.abspath(__file__)
_TESTS_DIR = os.path.dirname(_THIS_SCRIPT_ABSPATH)
_BACKEND_DIR = os.path.dirname(_TESTS_DIR)
PROJECT_ROOT = os.path.dirname(_BACKEND_DIR)

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


# Load environment variables
dotenv_path = os.path.join(PROJECT_ROOT, '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path=dotenv_path)

logger = logging.getLogger(__name__)

# Test configuration
API_TESTS_DIR = os.path.join(_TESTS_DIR, "api_tests")
BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

def run_pytest_with_json_report(plugin_status: Optional[dict[str, bool]] = None) -> bool:
    """
    Runs API tests using pytest with optional parallel execution and JSON reporting.
    
    If supported plugins are available, enables parallel test execution and generates a JSON report for detailed result summaries. Ensures a dummy SUPABASE_WEBHOOK_SECRET is set if missing. Streams pytest output in real time, prints a detailed summary if a JSON report is produced, or a basic summary otherwise.
    
    Args:
        plugin_status: Optional dictionary indicating the availability of pytest plugins.
    
    Returns:
        True if all tests pass (pytest exit code 0), otherwise False.
    """
    
    if plugin_status is None:
        plugin_status = check_dependencies()
    
    # Create a temporary file for JSON report
    json_report_path = os.path.join(_TESTS_DIR, "pytest_report.json")
    
    # Set the webhook secret for the test environment
    test_env = os.environ.copy()
    if not test_env.get("SUPABASE_WEBHOOK_SECRET"):
        logger.info("Temporarily setting a dummy SUPABASE_WEBHOOK_SECRET for test run.")
        test_env["SUPABASE_WEBHOOK_SECRET"] = "dummy-secret-for-testing"

    # Base pytest command
    pytest_cmd = [
        sys.executable, "-m", "pytest",
        API_TESTS_DIR,
        "-v",
        "--tb=short",
        "--maxfail=5",  # Stop after 5 failures
        "--durations=10",  # Show 10 slowest tests
    ]
    
    # Add parallel execution if xdist is available
    if plugin_status.get("xdist", False):
        pytest_cmd.extend(["-n", "auto"])  # Parallel execution with pytest-xdist
    
    # Add JSON reporting if available
    if plugin_status.get("json", False):
        pytest_cmd.extend([
            "--json-report",
            f"--json-report-file={json_report_path}",
            "--json-report-summary"
        ])
    
    logger.info("🚀 Starting Pytest-powered API Test Runner...")
    logger.info(f"📁 Test directory: {API_TESTS_DIR}")
    logger.info(f"🌐 Base URL: {BASE_URL}")
    logger.info("=" * 60)

    try:
        # Run pytest with real-time streaming output
        with subprocess.Popen(
            pytest_cmd,
            cwd=PROJECT_ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,  # Merge stderr into stdout
            text=True,
            bufsize=1,  # Line-buffered
            universal_newlines=True,
            env=test_env # Pass the modified environment
        ) as process:
            
            # Stream output line by line in real-time
            if process.stdout:
                for line in iter(process.stdout.readline, ''):
                    if line:
                        print(line.rstrip(), flush=True)  # Print without extra newlines and flush immediately
                    
            # Wait for process to complete
            # Bail out after 5 min to prevent hung runs
            return_code = process.wait(timeout=300)
        
        # Parse JSON report for detailed summary if JSON plugin is available
        if plugin_status.get("json", False) and os.path.exists(json_report_path):
            with open(json_report_path, 'r', encoding='utf-8') as f:
                report_data = json.load(f)

            print_detailed_summary(report_data)

            # Clean up
            os.remove(json_report_path)
        else:
            if not plugin_status.get("json", False):
                logger.warning("⚠️ JSON reporting plugin not available. Using basic summary.")
            else:
                logger.warning("⚠️ JSON report file not found. Using basic summary.")
            print_basic_summary(return_code)

        return return_code == 0

    except subprocess.TimeoutExpired:
        logger.error("❌ Test run timed out after 5 minutes")
        return False
    except Exception as e:
        logger.error(f"❌ Error running pytest: {e}")
        return False


def print_detailed_summary(report_data):
    """
    Prints a detailed summary of pytest results from a JSON report.
    
    Displays per-API and overall statistics, including counts of passed, failed, skipped, and errored tests, as well as pass rates and durations. If detailed test data is unavailable, falls back to summary statistics. Individual test outcomes are shown with icons and durations or reasons for failure/skip.
    """

    summary = report_data.get('summary', {})
    tests = report_data.get('tests', [])

    print("\n" + "=" * 60)
    print("📊 PYTEST-POWERED TEST SUMMARY")
    print("=" * 60)

    # If no tests in JSON report, fall back to summary data
    if not tests:
        logger.warning(
            "⚠️ No detailed test data in JSON report, using summary statistics")

        # Extract totals from summary
        total = summary.get('total', 0)
        passed = summary.get('passed', 0)
        failed = summary.get('failed', 0)
        error = summary.get('error', 0)
        skipped = summary.get('skipped', 0)

        # Combine failed and error
        total_failed = failed + error

        print("\n" + "=" * 30 + " OVERALL SUMMARY " + "=" * 30)

        overall_pass_rate = (passed / total * 100) if total > 0 else 0
        
        if total == 0:
            print("⚠️ No tests were executed!")
        elif skipped == total or (total_failed == 0 and passed == 0):
            print("⏭️ All tests were skipped - likely backend not running or no tests executed")
        elif total_failed == 0 and passed > 0:
            print("✅ All API tests passed!")
        else:
            print("❌ Some API tests failed.")

        print(f"  Total Tests: {total}")
        print(f"  Passed: {passed}")
        print(f"  Failed: {total_failed}")
        print(f"  Skipped: {skipped}")
        print(f"  Overall Pass Rate: {overall_pass_rate:.1f}%")

        # Show duration if available
        duration = summary.get('duration', 0)
        print(f"  Total Duration: {duration:.2f}s")

        print("=" * (60 + len(" OVERALL SUMMARY ")))
        return

    # Group tests by API (extracted from test file names)
    api_groups = {}
    for test in tests:
        # Extract API name from test nodeid (e.g., test_accounting_api.py::TestAccountingAPI::test_get_payments)
        nodeid = test.get('nodeid', '')
        if '::' in nodeid:
            file_part = nodeid.split('::')[0]
            if file_part.startswith('test_') and file_part.endswith('_api.py'):
                api_name = file_part.replace(
                    'test_', '').replace('_api.py', '').upper()
            else:
                api_name = "OTHER"
        else:
            api_name = "UNKNOWN"

        if api_name not in api_groups:
            api_groups[api_name] = {
                'total': 0,
                'passed': 0,
                'failed': 0,
                'skipped': 0,
                'errors': 0,
                'tests': []
            }

        api_groups[api_name]['total'] += 1
        api_groups[api_name]['tests'].append(test)

        outcome = test.get('outcome', 'unknown')
        if outcome == 'passed':
            api_groups[api_name]['passed'] += 1
        elif outcome == 'failed':
            api_groups[api_name]['failed'] += 1
        elif outcome == 'skipped':
            api_groups[api_name]['skipped'] += 1
        elif outcome == 'error':
            api_groups[api_name]['errors'] += 1

    # Print per-API summaries
    overall_totals = {'total': 0, 'passed': 0,
                      'failed': 0, 'skipped': 0, 'errors': 0}

    for api_name, stats in sorted(api_groups.items()):
        total = stats['total']
        passed = stats['passed']
        failed = stats['failed'] + stats['errors']  # Combine failed and errors
        skipped = stats['skipped']

        pass_percentage = (passed / total * 100) if total > 0 else 0
        status_emoji = "✅" if failed == 0 else "❌"

        print(f"\n{status_emoji} {api_name} API Tests:")
        print(
            f"  Tests: {total} | Passed: {passed} | Failed: {failed} | Skipped: {skipped} | Pass Rate: {pass_percentage:.1f}%")

        # Show individual test results (one line each)
        for test in stats['tests']:
            outcome = test.get('outcome', 'unknown')
            test_name = extract_test_name(test.get('nodeid', ''))
            duration = test.get('setup', {}).get(
                'duration', 0) + test.get('call', {}).get('duration', 0)

            if outcome == 'passed':
                print(f"    ✅ {test_name} ({duration:.2f}s)")
            elif outcome == 'failed':
                print(f"    ❌ {test_name} - {get_failure_reason(test)}")
            elif outcome == 'skipped':
                print(f"    ⏭️  {test_name} - {get_skip_reason(test)}")
            elif outcome == 'error':
                print(f"    💥 {test_name} - ERROR")

        # Update overall totals
        for key in overall_totals:
            overall_totals[key] += stats[key]

    # Print overall summary
    print("\n" + "=" * 30 + " OVERALL SUMMARY " + "=" * 30)

    total = overall_totals['total']
    passed = overall_totals['passed']
    failed = overall_totals['failed'] + overall_totals['errors']
    skipped = overall_totals['skipped']

    overall_pass_rate = (passed / total * 100) if total > 0 else 0
    
    if total == 0:
        print("⚠️ No tests were executed!")
    elif skipped == total or (failed == 0 and passed == 0):
        print("⏭️ All tests were skipped - likely backend not running or no tests executed")
    elif failed == 0 and passed > 0:
        print("✅ All API tests passed!")
    else:
        print("❌ Some API tests failed.")

    print(f"  Total Tests: {total}")
    print(f"  Passed: {passed}")
    print(f"  Failed: {failed}")
    print(f"  Skipped: {skipped}")
    print(f"  Overall Pass Rate: {overall_pass_rate:.1f}%")

    # Show summary stats from pytest
    duration = summary.get('duration', 0)
    print(f"  Total Duration: {duration:.2f}s")

    print("=" * (60 + len(" OVERALL SUMMARY ")))


def extract_test_name(nodeid):
    """
    Extracts a human-readable test name from a pytest node ID.
    
    Converts the last component of the node ID to a title-cased string with underscores replaced by spaces and the 'test_' prefix removed.
    """
    if '::' in nodeid:
        parts = nodeid.split('::')
        if len(parts) >= 3:
            # test_accounting_api.py::TestAccountingAPI::test_get_payments -> test_get_payments
            return parts[-1].replace('test_', '').replace('_', ' ').title()
        elif len(parts) >= 2:
            return parts[-1].replace('test_', '').replace('_', ' ').title()
    return nodeid


def get_failure_reason(test):
    """
    Extracts a concise failure reason from a test's call data.
    
    Returns a relevant assertion or error message from the test's failure output, or a default message if unavailable.
    """
    call_data = test.get('call', {})
    if 'longrepr' in call_data:
        # Get the first line of the failure message
        longrepr = call_data['longrepr']
        if isinstance(longrepr, str):
            lines = longrepr.split('\n')
            for line in lines:
                if 'assert' in line.lower() or 'error' in line.lower():
                    return line.strip()[:100] + "..." if len(line) > 100 else line.strip()
        return "Assertion failed"
    return "Unknown failure"


def get_skip_reason(test):
    """
    Extracts the skip reason from a test's setup or call data.
    
    If a specific skip reason is found in the 'longrepr' field containing 'SKIPPED', returns the extracted reason text. Otherwise, returns "Skipped".
    """
    setup_data = test.get('setup', {})
    call_data = test.get('call', {})

    for data in [setup_data, call_data]:
        if 'longrepr' in data:
            longrepr = data['longrepr']
            if isinstance(longrepr, str) and 'SKIPPED' in longrepr:
                # Try to extract the reason
                lines = longrepr.split('\n')
                for line in lines:
                    if 'SKIPPED' in line:
                        return line.split('SKIPPED')[1].strip(' []():')

    return "Skipped"


def print_basic_summary(return_code):
    """
    Prints a basic summary of test results based on the pytest exit code.
    
    Displays a simple success or failure message and the pytest exit code when a JSON report is not available.
    """
    print("\n" + "=" * 60)
    print("📊 BASIC TEST SUMMARY")
    print("=" * 60)

    if return_code == 0:
        print("✅ All tests completed successfully")
    else:
        print("❌ Some tests failed or encountered errors")

    print(f"  Pytest exit code: {return_code}")
    print("=" * 60)


def check_dependencies():
    """
    Checks for the presence of pytest and optional plugins required for enhanced test execution.
    
    Returns:
        A dictionary indicating the availability of pytest and the plugins `pytest-xdist`, `pytest-json-report`, and `pytest-asyncio`.
    """
    plugin_status = {
        "pytest": False,
        "xdist": False,
        "json": False,
        "asyncio": False
    }
    
    try:
        import pytest
        print(f"✅ pytest version: {pytest.__version__}")
        plugin_status["pytest"] = True
    except ImportError:
        logger.error("❌ pytest is not installed. Run: poetry install")
        return plugin_status
    
    # Check for required pytest plugins using import checks
    try:
        import pytest_xdist  # type: ignore
        plugin_status["xdist"] = True
    except ModuleNotFoundError:
        plugin_status["xdist"] = False
    try:
        import pytest_jsonreport  # type: ignore
        plugin_status["json"] = True
    except ModuleNotFoundError:
        plugin_status["json"] = False
    try:
        import pytest_asyncio  # type: ignore
        plugin_status["asyncio"] = True
    except ModuleNotFoundError:
        plugin_status["asyncio"] = False

    missing_features = []
    if not plugin_status["json"]:
        missing_features.append("pytest-json-report (structured reporting)")
    if not plugin_status["xdist"]:
        missing_features.append("pytest-xdist (parallel execution)")
    if not plugin_status["asyncio"]:
        missing_features.append("pytest-asyncio (async support)")

    if missing_features:
        logger.warning("⚠️ Missing optional pytest plugins:")
        for feature in missing_features:
            logger.warning(f"  - {feature}")
        logger.info("Run 'poetry install' to install all dependencies")
        logger.info("Continuing with basic functionality...")
    
    return plugin_status

def main():
    """
    Runs the API test suite, handling environment validation, dependency checks, and test execution.
    
    Returns:
        True if all tests pass, False otherwise.
    """

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    # Check environment
    if not os.path.exists(API_TESTS_DIR):
        logger.error(f"❌ API tests directory not found: {API_TESTS_DIR}")
        return False

    if not os.getenv("SUPABASE_URL") or not os.getenv("SUPABASE_ANON_KEY"):
        logger.error("❌ SUPABASE_URL and/or SUPABASE_ANON_KEY are not set.")
        logger.error(f"Please check your .env file at {dotenv_path}")
        return False

    # Check dependencies
    plugin_status = check_dependencies()
    if not plugin_status["pytest"]:
        logger.error("❌ Dependency check failed")
        return False

    # Run tests
    success = run_pytest_with_json_report(plugin_status)
    
    if success:
        logger.info("\n✅ All tests completed successfully!")
    else:
        logger.error("\n❌ Some tests failed. Check output above for details.")

    return success


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
