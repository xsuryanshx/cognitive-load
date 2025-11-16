#!/usr/bin/env python3
"""
Test Databricks HTTP endpoint directly to verify connectivity.
"""

import sys
import os
import requests
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.config import DATABRICKS_SERVER_HOSTNAME, DATABRICKS_HTTP_PATH, DATABRICKS_ACCESS_TOKEN

def test_http_endpoint():
    """Test the HTTP endpoint directly"""
    print("=" * 60)
    print("Testing Databricks HTTP Endpoint Directly")
    print("=" * 60)
    
    # Build the full URL
    base_url = f"https://{DATABRICKS_SERVER_HOSTNAME}{DATABRICKS_HTTP_PATH}"
    
    print(f"\nEndpoint URL: {base_url}")
    print(f"HTTP Path: {DATABRICKS_HTTP_PATH}")
    print(f"Access Token: {DATABRICKS_ACCESS_TOKEN[:4]}...{DATABRICKS_ACCESS_TOKEN[-4:]}")
    
    # Try a simple HTTP request
    headers = {
        "Authorization": f"Bearer {DATABRICKS_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    
    try:
        print("\nAttempting HTTP GET request...")
        response = requests.get(
            base_url,
            headers=headers,
            timeout=10,
            verify=True
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            print("✓ HTTP endpoint is accessible!")
            return True
        elif response.status_code == 401:
            print("✗ Authentication failed (401)")
            print("  - Check if access token is valid")
            return False
        elif response.status_code == 404:
            print("✗ Endpoint not found (404)")
            print("  - Check if HTTP path is correct")
            print("  - Verify SQL warehouse is running")
            return False
        else:
            print(f"✗ Unexpected status code: {response.status_code}")
            print(f"  Response: {response.text[:200]}")
            return False
            
    except requests.exceptions.Timeout:
        print("✗ Request timed out")
        print("  - SQL warehouse may be stopped")
        print("  - Network connectivity issue")
        return False
    except requests.exceptions.ConnectionError as e:
        print(f"✗ Connection error: {e}")
        return False
    except Exception as e:
        print(f"✗ Error: {type(e).__name__}: {e}")
        return False

def test_sql_connection_simple():
    """Try the simplest possible SQL connection"""
    print("\n" + "=" * 60)
    print("Testing Simple SQL Connection")
    print("=" * 60)
    
    try:
        from databricks import sql
        
        print("\nAttempting connection (simplest method)...")
        connection = sql.connect(
            server_hostname=DATABRICKS_SERVER_HOSTNAME,
            http_path=DATABRICKS_HTTP_PATH,
            access_token=DATABRICKS_ACCESS_TOKEN
        )
        
        print("✓ Connection successful!")
        
        cursor = connection.cursor()
        cursor.execute("SELECT current_catalog(), current_schema()")
        result = cursor.fetchone()
        print(f"✓ Current catalog: {result[0]}, schema: {result[1]}")
        
        cursor.close()
        connection.close()
        return True
        
    except Exception as e:
        print(f"✗ Connection failed: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("\n" + "=" * 60)
    print("DATABRICKS HTTP ENDPOINT TEST")
    print("=" * 60)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Test HTTP endpoint
    if test_http_endpoint():
        print("\n✓ HTTP endpoint is accessible!")
        print("\nTrying SQL connection...")
        if test_sql_connection_simple():
            print("\n" + "=" * 60)
            print("✓ ALL TESTS PASSED!")
            print("=" * 60)
            return
    
    print("\n" + "=" * 60)
    print("✗ CONNECTION FAILED")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Go to Databricks workspace")
    print("2. Check SQL Warehouses - ensure warehouse is STARTED")
    print("3. Verify HTTP path matches the connection details")
    print("4. Check access token is valid")
    
    sys.exit(1)

if __name__ == "__main__":
    main()

