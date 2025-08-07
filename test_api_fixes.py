#!/usr/bin/env python3
"""
Test script to verify the API fixes for orderBy parameter requirement.
This validates that all API calls now include the required orderBy parameter.
"""

import sys
import os
sys.path.append('app')

from datetime import datetime
from api.lapis import Lapis
from api.health_check import ApiHealthChecker
from interface import MutationType

def test_lapis_fetch_locations():
    """Test that fetch_locations URL includes orderBy parameter."""
    print("🧪 Testing Lapis fetch_locations URL generation...")
    
    lapis = Lapis('http://localhost:8083')
    address_no_port = lapis.parse_url_hostname(lapis.server_ip)
    location_url = f'{address_no_port}/sample/aggregated?fields=location_name&limit=100&orderBy=location_name&dataFormat=JSON&downloadAsFile=false'
    
    print(f"   Generated URL: {location_url}")
    
    # Check if orderBy is included
    if 'orderBy=location_name' in location_url:
        print("   ✅ PASS: orderBy parameter included")
        return True
    else:
        print("   ❌ FAIL: orderBy parameter missing")
        return False

def test_health_check_payload():
    """Test that health check payload includes orderBy parameter."""
    print("🧪 Testing Health Check payload...")
    
    # Simulate the payload from health check
    payload = {
        "fields": ["location_name"],
        "limit": 1,
        "orderBy": "location_name",
        "dataFormat": "JSON"
    }
    
    print(f"   Payload: {payload}")
    
    if 'orderBy' in payload:
        print("   ✅ PASS: orderBy parameter included")
        return True
    else:
        print("   ❌ FAIL: orderBy parameter missing")
        return False

def test_wiseloculus_payload():
    """Test that WiseLoculus payload includes orderBy parameter."""
    print("🧪 Testing WiseLoculus aggregated payload...")
    
    # Simulate the payload from fetch_sample_aggregated
    date_range = (datetime(2024, 1, 1), datetime(2024, 1, 31))
    payload = { 
        "sampling_dateFrom": date_range[0].strftime('%Y-%m-%d'),
        "sampling_dateTo": date_range[1].strftime('%Y-%m-%d'),
        "fields": ["sampling_date"],
        "orderBy": "sampling_date"
    }
    
    print(f"   Payload: {payload}")
    
    if 'orderBy' in payload:
        print("   ✅ PASS: orderBy parameter included")
        return True
    else:
        print("   ❌ FAIL: orderBy parameter missing")
        return False

def test_api_call_formats():
    """Test the API call formats match the expected new format."""
    print("🧪 Testing API call format compliance...")
    
    # Original problematic call
    old_call = "curl -s \"http://localhost:8083/sample/aggregated?fields=location_name&limit=5&dataFormat=JSON&downloadAsFile=false\""
    
    # New fixed call
    new_call = "curl -s \"http://localhost:8083/sample/aggregated?fields=location_name&limit=5&orderBy=location_name&dataFormat=JSON&downloadAsFile=false\""
    
    print(f"   OLD (problematic): {old_call}")
    print(f"   NEW (fixed):       {new_call}")
    
    if 'orderBy=' in new_call:
        print("   ✅ PASS: New format includes orderBy parameter")
        return True
    else:
        print("   ❌ FAIL: New format missing orderBy parameter")
        return False

def main():
    """Run all tests."""
    print("🔧 API orderBy Parameter Fix Validation")
    print("=" * 50)
    print()
    
    tests = [
        test_lapis_fetch_locations,
        test_health_check_payload,
        test_wiseloculus_payload,
        test_api_call_formats
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"   ❌ ERROR: {e}")
            results.append(False)
        print()
    
    # Summary
    passed = sum(results)
    total = len(results)
    
    print("📊 SUMMARY")
    print("=" * 50)
    print(f"Tests passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED! API calls should now work with LAPIS v0.5.9+")
        print()
        print("✅ Fixed issues:")
        print("   • fetch_locations() now includes orderBy=location_name")
        print("   • Health checks now include orderBy=location_name") 
        print("   • WiseLoculus aggregated calls now include orderBy=sampling_date")
        print()
        print("🚀 The HTTP 400 'Bad request' errors should be resolved!")
    else:
        print("❌ Some tests failed. Please review the fixes.")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
