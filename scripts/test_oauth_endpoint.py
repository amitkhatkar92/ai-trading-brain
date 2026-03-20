#!/usr/bin/env python3
"""
OAuth Server Diagnostic Test
Tests if the callback endpoint is working correctly
"""

import urllib.request
import urllib.error
import json
import sys
from urllib.parse import urlencode

def test_oauth_server(host="localhost", port=8000):
    """Test OAuth server endpoints"""
    
    base_url = f"http://{host}:{port}"
    
    # Test 1: Health endpoint
    print("="*60)
    print("TEST 1: Health Endpoint")
    print("="*60)
    try:
        url = f"{base_url}/health"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())
            print(f"✅ Status: {response.status}")
            print(f"✅ Response: {json.dumps(data, indent=2)}")
    except Exception as e:
        print(f"❌ ERROR: {e}")
    
    # Test 2: Callback endpoint with test code
    print("\n" + "="*60)
    print("TEST 2: Callback Endpoint (with test code)")
    print("="*60)
    try:
        url = f"{base_url}/callback?code=test_code_123&state=test"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=5) as response:
            print(f"✅ Status: {response.status}")
            body = response.read().decode()
            print(f"✅ Response length: {len(body)} bytes")
            if "success" in body.lower() or "token" in body.lower():
                print("✅ Response contains success indicators")
            print(f"✅ First 200 chars: {body[:200]}")
    except urllib.error.HTTPError as e:
        print(f"❌ HTTP ERROR {e.code}: {e.reason}")
        try:
            error_body = e.read().decode()
            print(f"❌ Error body: {error_body[:500]}")
        except:
            pass
    except Exception as e:
        print(f"❌ ERROR: {e}")
    
    # Test 3: Root endpoint
    print("\n" + "="*60)
    print("TEST 3: Root Endpoint (/)")
    print("="*60)
    try:
        url = f"{base_url}/?code=test_code_123&state=test"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=5) as response:
            print(f"✅ Status: {response.status}")
            body = response.read().decode()
            print(f"✅ Response: {body[:200]}")
    except Exception as e:
        print(f"❌ ERROR: {e}")

if __name__ == "__main__":
    host = sys.argv[1] if len(sys.argv) > 1 else "localhost"
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 8000
    
    print(f"\nTesting OAuth Server at {host}:{port}\n")
    test_oauth_server(host, port)
    print("\n" + "="*60)
