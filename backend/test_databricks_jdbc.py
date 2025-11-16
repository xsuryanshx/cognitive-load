#!/usr/bin/env python3
"""
Test Databricks connection using JDBC-style connection parameters.
"""

import sys
import os
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.config import DATABRICKS_SERVER_HOSTNAME, DATABRICKS_HTTP_PATH, DATABRICKS_ACCESS_TOKEN

def test_jdbc_connection():
    """Test connection using JDBC-style parameters"""
    print("=" * 60)
    print("Testing Databricks Connection via JDBC Method")
    print("=" * 60)
    
    print(f"\nJDBC Connection String:")
    print(f"jdbc:databricks://{DATABRICKS_SERVER_HOSTNAME}:443/default;")
    print(f"transportMode=http;ssl=1;AuthMech=3;")
    print(f"httpPath={DATABRICKS_HTTP_PATH};")
    
    try:
        from databricks import sql
        import signal
        
        def timeout_handler(signum, frame):
            raise TimeoutError("Connection attempt timed out after 30 seconds")
        
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(30)
        
        try:
            print("\nAttempting connection with JDBC-style parameters...")
            print(f"  Server: {DATABRICKS_SERVER_HOSTNAME}")
            print(f"  Port: 443")
            print(f"  HTTP Path: {DATABRICKS_HTTP_PATH}")
            print(f"  Transport: HTTP")
            print(f"  SSL: Enabled")
            print(f"  Auth: Access Token")
            
            # Try connection with JDBC-style parameters
            # Note: databricks-sql-connector doesn't accept port separately
            # Port 443 is default for HTTPS connections
            connection = sql.connect(
                server_hostname=DATABRICKS_SERVER_HOSTNAME,
                http_path=DATABRICKS_HTTP_PATH,
                access_token=DATABRICKS_ACCESS_TOKEN,
                timeout=30,
            )
            
            signal.alarm(0)
            print("✓ Connection established successfully!")
            
            # Test query
            print("\nTesting query execution...")
            cursor = connection.cursor()
            cursor.execute("SELECT 1 as test, current_timestamp() as now")
            result = cursor.fetchone()
            
            if result:
                print(f"✓ Query executed successfully!")
                print(f"  Result: {result}")
            
            # Test table creation/access
            print("\nTesting table access...")
            cursor.execute("SHOW TABLES")
            tables = cursor.fetchall()
            print(f"✓ Found {len(tables)} tables in default schema")
            if tables:
                print("  Tables:", [t[0] for t in tables[:5]])
            
            cursor.close()
            connection.close()
            print("\n✓ Connection closed successfully")
            
            return True
            
        except TimeoutError as e:
            signal.alarm(0)
            print(f"\n✗ {e}")
            print("\nTrying alternative connection method...")
            return test_alternative_connection()
            
        except Exception as e:
            signal.alarm(0)
            print(f"\n✗ Connection failed: {type(e).__name__}: {e}")
            print("\nTrying alternative connection method...")
            return test_alternative_connection()
            
    except ImportError as e:
        print(f"✗ Failed to import databricks-sql-connector: {e}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_alternative_connection():
    """Try alternative connection methods"""
    print("\n" + "=" * 60)
    print("Trying Alternative Connection Methods")
    print("=" * 60)
    
    try:
        from databricks import sql
        
        # Method 1: Try without explicit port
        print("\nMethod 1: Connection without explicit port...")
        try:
            connection = sql.connect(
                server_hostname=DATABRICKS_SERVER_HOSTNAME,
                http_path=DATABRICKS_HTTP_PATH,
                access_token=DATABRICKS_ACCESS_TOKEN,
                timeout=15
            )
            cursor = connection.cursor()
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            cursor.close()
            connection.close()
            print("✓ Method 1 succeeded!")
            return True
        except Exception as e:
            print(f"✗ Method 1 failed: {e}")
        
        # Method 2: Try with different timeout
        print("\nMethod 2: Connection with longer timeout...")
        try:
            connection = sql.connect(
                server_hostname=DATABRICKS_SERVER_HOSTNAME,
                http_path=DATABRICKS_HTTP_PATH,
                access_token=DATABRICKS_ACCESS_TOKEN,
                timeout=60
            )
            cursor = connection.cursor()
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            cursor.close()
            connection.close()
            print("✓ Method 2 succeeded!")
            return True
        except Exception as e:
            print(f"✗ Method 2 failed: {e}")
        
        # Method 3: Try with Unity Catalog (default catalog)
        print("\nMethod 3: Connection with Unity Catalog (main catalog)...")
        try:
            connection = sql.connect(
                server_hostname=DATABRICKS_SERVER_HOSTNAME,
                http_path=DATABRICKS_HTTP_PATH,
                access_token=DATABRICKS_ACCESS_TOKEN,
                catalog="main",  # Unity Catalog default catalog
                schema="default",
                timeout=15
            )
            cursor = connection.cursor()
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            cursor.close()
            connection.close()
            print("✓ Method 3 succeeded!")
            return True
        except Exception as e:
            print(f"✗ Method 3 failed: {e}")
        
        return False
        
    except Exception as e:
        print(f"✗ Alternative methods failed: {e}")
        return False

def test_with_pyodbc():
    """Try using pyodbc with ODBC driver (if available)"""
    print("\n" + "=" * 60)
    print("Trying PyODBC Method (if available)")
    print("=" * 60)
    
    try:
        import pyodbc
        
        # Build connection string from JDBC URL
        conn_str = (
            f"DRIVER={{Simba Spark ODBC Driver}};"
            f"HOST={DATABRICKS_SERVER_HOSTNAME};"
            f"PORT=443;"
            f"HTTPPath={DATABRICKS_HTTP_PATH};"
            f"AuthMech=3;"
            f"UID=token;"
            f"PWD={DATABRICKS_ACCESS_TOKEN};"
            f"SSL=1;"
            f"ThriftTransport=2;"
            f"SparkServerType=3;"
        )
        
        print("Attempting PyODBC connection...")
        print("Note: Requires Simba Spark ODBC Driver installed")
        
        connection = pyodbc.connect(conn_str, timeout=15)
        cursor = connection.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        cursor.close()
        connection.close()
        
        print("✓ PyODBC connection succeeded!")
        return True
        
    except ImportError:
        print("✗ PyODBC not installed (optional method)")
        print("  Install with: pip install pyodbc")
        return False
    except Exception as e:
        print(f"✗ PyODBC connection failed: {e}")
        return False

def main():
    """Run JDBC connection test"""
    print("\n" + "=" * 60)
    print("DATABRICKS JDBC CONNECTION TEST")
    print("=" * 60)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Check credentials
    if not DATABRICKS_ACCESS_TOKEN:
        print("✗ Access token not set")
        sys.exit(1)
    
    # Test JDBC connection
    if test_jdbc_connection():
        print("\n" + "=" * 60)
        print("✓ CONNECTION SUCCESSFUL!")
        print("=" * 60)
        print("\nYour Databricks connection is working via JDBC method!")
        return
    
    # Try PyODBC as fallback
    print("\n" + "=" * 60)
    print("Trying PyODBC as Alternative")
    print("=" * 60)
    if test_with_pyodbc():
        print("\n✓ PyODBC connection successful!")
        return
    
    print("\n" + "=" * 60)
    print("✗ ALL CONNECTION METHODS FAILED")
    print("=" * 60)
    print("\nTroubleshooting steps:")
    print("1. Verify SQL warehouse is STARTED in Databricks UI")
    print("2. Check HTTP path is correct in warehouse connection details")
    print("3. Verify access token is valid and not expired")
    print("4. Check network/firewall settings")
    print("5. Try accessing Databricks workspace in browser to verify connectivity")
    
    sys.exit(1)

if __name__ == "__main__":
    main()

