"""
Test runner and configuration for unit tests.

This module provides utilities for running tests and generating coverage reports.
"""

import unittest
import sys
import os
from pathlib import Path

# Add project root to Python path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def run_all_tests():
    """Run all unit tests and return results."""
    # Discover and run all tests
    loader = unittest.TestLoader()
    start_dir = Path(__file__).parent
    suite = loader.discover(start_dir, pattern='test_*.py')
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result


def run_specific_test_module(module_name):
    """Run a specific test module."""
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromName(module_name)
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result


def generate_coverage_report():
    """Generate coverage report for tests."""
    try:
        import coverage
        
        # Create coverage object
        cov = coverage.Coverage()
        cov.start()
        
        # Run tests
        result = run_all_tests()
        
        # Stop coverage and generate report
        cov.stop()
        cov.save()
        
        print("\n" + "="*60)
        print("COVERAGE REPORT")
        print("="*60)
        cov.report()
        
        # Generate HTML report
        cov.html_report(directory='tests/coverage_html')
        print(f"\nHTML coverage report generated in: tests/coverage_html/")
        
        return result
        
    except ImportError:
        print("Coverage package not installed. Install with: pip install coverage")
        return run_all_tests()


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Run unit tests for Agentic Quote')
    parser.add_argument('--module', '-m', help='Run specific test module')
    parser.add_argument('--coverage', '-c', action='store_true', help='Generate coverage report')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    if args.coverage:
        result = generate_coverage_report()
    elif args.module:
        result = run_specific_test_module(args.module)
    else:
        result = run_all_tests()
    
    # Exit with appropriate code
    sys.exit(0 if result.wasSuccessful() else 1)
