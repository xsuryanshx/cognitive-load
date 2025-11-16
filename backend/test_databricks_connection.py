#!/usr/bin/env python3
"""
Quick diagnostic script to test Databricks connection with timeouts and detailed error messages.
"""

import sys
import os
import socket
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.config import DATABRICKS_SERVER_HOSTNAME, DATABRICKS_HTTP_PATH, DATABRICKS_ACCESS_TOKEN

def test_network_connectivity():
    """Test if we can reach the Databricks server"""
    print("=" * 60)
    print("STEP 1: Testing Network Connectivity")
    print("=" * 60)
    
    hostname = DATABRICKS_SERVER_HOSTNAME
    print(f"Server hostname: {hostname}")
    
    try:
        # Extract hostname (remove protocol if present)
        if "://" in hostname:
            hostname = hostname.split("://")[1]
        
        # Try DNS resolution
        print(f"Resolving DNS for {hostname}...")
        ip = socket.gethostbyname(hostname)
        print(f"✓ DNS resolution successful: {hostname} -> {ip}")
        
        # Try TCP connection on port 443 (HTTPS)
        print(f"Testing TCP connection to {hostname}:443...")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)  # 5 second timeout
        result = sock.connect_ex((hostname, 443))
        sock.close()
        
        if result == 0:
            print(f"✓ TCP connection to port 443 successful")
            return True
        else:
            print(f"✗ TCP connection to port 443 failed (error code: {result})")
            return False
            
    except socket.gaierror as e:
        print(f"✗ DNS resolution failed: {e}")
        return False
    except socket.timeout:
        print(f"✗ Connection timeout - server may be unreachable")
        return False
    except Exception as e:
        print(f"✗ Network test failed: {e}")
        return False

def test_credentials():
    """Check if credentials are configured"""
    print("\n" + "=" * 60)
    print("STEP 2: Checking Credentials")
    print("=" * 60)
    
    print(f"Server Hostname: {DATABRICKS_SERVER_HOSTNAME}")
    print(f"HTTP Path: {DATABRICKS_HTTP_PATH}")
    
    if DATABRICKS_ACCESS_TOKEN:
        token_preview = DATABRICKS_ACCESS_TOKEN[:4] + "..." + DATABRICKS_ACCESS_TOKEN[-4:] if len(DATABRICKS_ACCESS_TOKEN) > 8 else "****"
        print(f"Access Token: {token_preview} (length: {len(DATABRICKS_ACCESS_TOKEN)})")
        return True
    else:
        print("✗ Access Token: NOT SET")
        print("\nPlease set DATABRICKS_ACCESS_TOKEN in your .env file")
        return False

def test_databricks_connection():
    """Test actual Databricks SQL connection with timeout"""
    print("\n" + "=" * 60)
    print("STEP 3: Testing Databricks SQL Connection")
    print("=" * 60)
    
    try:
        from databricks import sql
        import signal
        
        # Set up timeout handler
        def timeout_handler(signum, frame):
            raise TimeoutError("Connection attempt timed out after 30 seconds")
        
        # Set 30 second timeout
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(30)
        
        try:
            print("Attempting to connect...")
            print(f"  Server: {DATABRICKS_SERVER_HOSTNAME}")
            print(f"  HTTP Path: {DATABRICKS_HTTP_PATH}")
            
            connection = sql.connect(
                server_hostname=DATABRICKS_SERVER_HOSTNAME,
                http_path=DATABRICKS_HTTP_PATH,
                access_token=DATABRICKS_ACCESS_TOKEN,
                timeout=30  # 30 second timeout
            )
            
            signal.alarm(0)  # Cancel timeout
            
            print("✓ Connection established successfully!")
            
            # Try a simple query
            print("\nTesting query execution...")
            cursor = connection.cursor()
            cursor.execute("SELECT 1 as test")
            result = cursor.fetchone()
            
            if result:
                print(f"✓ Query executed successfully: {result}")
            
            cursor.close()
            connection.close()
            print("✓ Connection closed successfully")
            
            return True
            
        except TimeoutError as e:
            signal.alarm(0)
            print(f"✗ {e}")
            print("\nPossible issues:")
            print("  - Network connectivity problem")
            print("  - Firewall blocking connection")
            print("  - Incorrect server hostname or HTTP path")
            print("  - Databricks SQL warehouse may be stopped")
            return False
            
        except Exception as e:
            signal.alarm(0)
            print(f"✗ Connection failed: {type(e).__name__}: {e}")
            
            # Provide specific error guidance
            error_str = str(e).lower()
            if "authentication" in error_str or "unauthorized" in error_str or "401" in error_str:
                print("\n→ Authentication Error:")
                print("  - Check if your access token is valid")
                print("  - Token may have expired")
                print("  - Verify token has proper permissions")
            elif "not found" in error_str or "404" in error_str:
                print("\n→ Resource Not Found:")
                print("  - Check if HTTP path is correct")
                print("  - Verify SQL warehouse exists and is running")
            elif "timeout" in error_str or "timed out" in error_str:
                print("\n→ Timeout Error:")
                print("  - Network connectivity issue")
                print("  - Firewall may be blocking")
                print("  - SQL warehouse may be stopped")
            elif "ssl" in error_str or "certificate" in error_str:
                print("\n→ SSL/Certificate Error:")
                print("  - SSL certificate validation issue")
                print("  - Check system certificates")
            
            return False
            
    except ImportError as e:
        print(f"✗ Failed to import databricks-sql-connector: {e}")
        print("  Run: pip install databricks-sql-connector")
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all diagnostic tests"""
    print("\n" + "=" * 60)
    print("DATABRICKS CONNECTION DIAGNOSTIC TOOL")
    print("=" * 60)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Step 1: Check credentials
    if not test_credentials():
        print("\n" + "=" * 60)
        print("✗ DIAGNOSIS: Credentials not configured")
        print("=" * 60)
        print("\nTo fix:")
        print("1. Create a .env file in the backend/ directory")
        print("2. Add your Databricks credentials:")
        print("   DATABRICKS_SERVER_HOSTNAME=your-server-hostname")
        print("   DATABRICKS_HTTP_PATH=/sql/1.0/warehouses/your-warehouse-id")
        print("   DATABRICKS_ACCESS_TOKEN=your-access-token")
        sys.exit(1)
    
    # Step 2: Test network connectivity
    if not test_network_connectivity():
        print("\n" + "=" * 60)
        print("✗ DIAGNOSIS: Network connectivity issue")
        print("=" * 60)
        print("\nPossible solutions:")
        print("  - Check your internet connection")
        print("  - Verify firewall settings")
        print("  - Check if you're behind a VPN/proxy")
        print("  - Verify server hostname is correct")
        sys.exit(1)
    
    # Step 3: Test Databricks connection
    if not test_databricks_connection():
        print("\n" + "=" * 60)
        print("✗ DIAGNOSIS: Databricks connection failed")
        print("=" * 60)
        print("\nNext steps:")
        print("1. Verify your access token is valid:")
        print("   - Go to Databricks workspace")
        print("   - User Settings > Access Tokens")
        print("   - Create a new token if needed")
        print("\n2. Verify SQL warehouse is running:")
        print("   - Go to SQL Warehouses in Databricks")
        print("   - Ensure warehouse is started")
        print("   - Copy the correct HTTP path")
        print("\n3. Check server hostname format:")
        print("   - Should be: dbc-xxxxx-xxxx.cloud.databricks.com")
        print("   - No https:// prefix needed")
        sys.exit(1)
    
    print("\n" + "=" * 60)
    print("✓ ALL TESTS PASSED!")
    print("=" * 60)
    print("\nYour Databricks connection is working correctly!")
    print("You can now run the full test script: python -m backend.test_databricks")

if __name__ == "__main__":
    main()

