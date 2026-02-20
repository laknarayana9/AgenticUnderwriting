#!/usr/bin/env python3
"""
Simple test script for the Agentic Quote-to-Underwrite API.
"""

import requests
import json
import time

API_BASE = "http://localhost:8000"

def test_health():
    """Test health endpoint."""
    print("Testing health endpoint...")
    response = requests.get(f"{API_BASE}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    print()

def test_quote_processing():
    """Test quote processing endpoint."""
    print("Testing quote processing...")
    
    # Test data
    test_quote = {
        "submission": {
            "applicant_name": "John Doe",
            "address": "123 Main St, Los Angeles, CA 90210",
            "property_type": "single_family",
            "coverage_amount": 500000,
            "construction_year": 1985,
            "square_footage": 2000,
            "roof_type": "asphalt_shingle",
            "foundation_type": "concrete"
        },
        "use_agentic": True
    }
    
    print("Sending quote...")
    response = requests.post(f"{API_BASE}/quote/run", json=test_quote)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"Run ID: {result['run_id']}")
        print(f"Decision: {result['decision']['decision']}")
        print(f"Rationale: {result['decision']['rationale']}")
        
        if result['premium']:
            print(f"Premium: ${result['premium']['total_premium']}")
        
        if result['citations']:
            print(f"Citations: {result['citations']}")
        
        # Test getting run details
        print(f"\nTesting run details for {result['run_id']}...")
        time.sleep(1)  # Brief pause
        
        detail_response = requests.get(f"{API_BASE}/runs/{result['run_id']}")
        print(f"Detail Status: {detail_response.status_code}")
        
        if detail_response.status_code == 200:
            details = detail_response.json()
            print(f"Run Status: {details['status']}")
            print(f"Created: {details['created_at']}")
        
        # Test audit trail
        print(f"\nTesting audit trail for {result['run_id']}...")
        audit_response = requests.get(f"{API_BASE}/runs/{result['run_id']}/audit")
        print(f"Audit Status: {audit_response.status_code}")
        
        if audit_response.status_code == 200:
            audit = audit_response.json()
            print(f"Tool calls: {len(audit['tool_calls'])}")
            print(f"Node outputs: {list(audit['node_outputs'].keys())}")
    
    else:
        print(f"Error: {response.text}")
    
    print()

def test_stats():
    """Test statistics endpoint."""
    print("Testing statistics endpoint...")
    response = requests.get(f"{API_BASE}/stats")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    print()

def test_runs_list():
    """Test runs list endpoint."""
    print("Testing runs list endpoint...")
    response = requests.get(f"{API_BASE}/runs")
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"Total runs: {data['total_count']}")
        for run in data['runs'][:3]:  # Show first 3
            print(f"  - {run['run_id'][:8]}... ({run['status']}) - {run['created_at']}")
    
    print()

def main():
    """Run all tests."""
    print("=== Agentic Quote-to-Underwrite API Test ===\n")
    
    try:
        test_health()
        test_stats()
        test_runs_list()
        test_quote_processing()
        test_runs_list()  # Check updated runs list
        
        print("=== All tests completed ===")
        
    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to API. Make sure the server is running on localhost:8000")
    except Exception as e:
        print(f"Unexpected error: {e}")

if __name__ == "__main__":
    main()
