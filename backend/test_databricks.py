#!/usr/bin/env python3
"""
Test script to verify Databricks connection and data insertion.
This script will:
1. Test connection to Databricks
2. Create tables if they don't exist
3. Insert test data
4. Query the data back to verify
5. Clean up test data
"""

import sys
import os
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.databricks_client.client import databricks_client
from backend.databricks_client.ingestion import databricks_ingestion
from backend.models import KeystrokeBatch, KeystrokeEvent

def test_connection():
    """Test basic connection to Databricks"""
    print("=" * 60)
    print("Testing Databricks Connection...")
    print("=" * 60)
    
    try:
        if databricks_client.connect():
            print("✓ Successfully connected to Databricks!")
            return True
        else:
            print("✗ Failed to connect to Databricks")
            return False
    except Exception as e:
        print(f"✗ Connection error: {e}")
        return False

def test_table_creation():
    """Test creating tables"""
    print("\n" + "=" * 60)
    print("Testing Table Creation...")
    print("=" * 60)
    
    try:
        if databricks_client.create_tables():
            print("✓ Tables created/verified successfully!")
            return True
        else:
            print("✗ Failed to create tables")
            return False
    except Exception as e:
        print(f"✗ Table creation error: {e}")
        return False

def test_data_insertion():
    """Test inserting data into Databricks"""
    print("\n" + "=" * 60)
    print("Testing Data Insertion...")
    print("=" * 60)
    
    # Create test data
    test_participant_id = "test_user_123"
    test_section_id = f"test_section_{int(datetime.now().timestamp())}"
    test_sentence = "The quick brown fox jumps over the lazy dog."
    test_user_input = "The quick brown fox jumps over the lazy dog."
    session_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Create test keystrokes
    test_keystrokes = [
        KeystrokeEvent(
            press_time=1000 + i * 50,
            release_time=1000 + i * 50 + 20,
            keycode=65 + i,  # A, B, C, etc.
            letter=chr(65 + i) if i < 26 else " "
        )
        for i in range(10)  # 10 test keystrokes
    ]
    
    test_batch = KeystrokeBatch(
        participant_id=test_participant_id,
        test_section_id=test_section_id,
        sentence=test_sentence,
        user_input=test_user_input,
        keystrokes=test_keystrokes
    )
    
    try:
        # Test keystroke insertion
        print(f"Inserting test keystrokes for participant: {test_participant_id}")
        print(f"Test section ID: {test_section_id}")
        
        result = databricks_ingestion.upsert_keystrokes(test_batch, session_timestamp)
        
        if result:
            print("✓ Keystroke data inserted successfully!")
        else:
            print("✗ Failed to insert keystroke data")
            return False, test_participant_id, test_section_id
        
        # Test session insertion
        print(f"\nInserting test session data...")
        session_result = databricks_ingestion.upsert_session(
            participant_id=test_participant_id,
            test_section_id=test_section_id,
            sentence_count=1,
            total_keystrokes=len(test_keystrokes),
            average_wpm=45.5,
            session_timestamp=session_timestamp
        )
        
        if session_result:
            print("✓ Session data inserted successfully!")
        else:
            print("✗ Failed to insert session data")
            return False, test_participant_id, test_section_id
        
        return True, test_participant_id, test_section_id
        
    except Exception as e:
        print(f"✗ Data insertion error: {e}")
        import traceback
        traceback.print_exc()
        return False, test_participant_id, test_section_id

def test_data_retrieval(participant_id: str, test_section_id: str):
    """Test querying data back from Databricks"""
    print("\n" + "=" * 60)
    print("Testing Data Retrieval...")
    print("=" * 60)
    
    try:
        # Query keystrokes
        keystrokes_query = """
        SELECT COUNT(*) as count, 
               MIN(keystroke_id) as min_id, 
               MAX(keystroke_id) as max_id
        FROM keystrokes 
        WHERE participant_id = :1 AND test_section_id = :2
        """
        
        result = databricks_client.execute(keystrokes_query, (participant_id, test_section_id))
        
        if result and len(result) > 0:
            count = result[0][0] if result[0] else 0
            print(f"✓ Found {count} keystrokes in database")
            if count > 0:
                print(f"  Keystroke ID range: {result[0][1]} to {result[0][2]}")
        else:
            print("✗ No keystrokes found")
            return False
        
        # Query sessions
        sessions_query = """
        SELECT sentence_count, total_keystrokes, average_wpm
        FROM sessions 
        WHERE participant_id = :1 AND test_section_id = :2
        """
        
        result = databricks_client.execute(sessions_query, (participant_id, test_section_id))
        
        if result and len(result) > 0:
            session_data = result[0]
            print(f"✓ Found session data:")
            print(f"  Sentence count: {session_data[0]}")
            print(f"  Total keystrokes: {session_data[1]}")
            print(f"  Average WPM: {session_data[2]}")
        else:
            print("✗ No session data found")
            return False
        
        return True
        
    except Exception as e:
        print(f"✗ Data retrieval error: {e}")
        import traceback
        traceback.print_exc()
        return False

def cleanup_test_data(participant_id: str, test_section_id: str):
    """Clean up test data"""
    print("\n" + "=" * 60)
    print("Cleaning Up Test Data...")
    print("=" * 60)
    
    try:
        # Delete keystrokes
        delete_keystrokes = """
        DELETE FROM keystrokes 
        WHERE participant_id = :1 AND test_section_id = :2
        """
        databricks_client.execute(delete_keystrokes, (participant_id, test_section_id))
        print("✓ Test keystrokes deleted")
        
        # Delete sessions
        delete_sessions = """
        DELETE FROM sessions 
        WHERE participant_id = :1 AND test_section_id = :2
        """
        databricks_client.execute(delete_sessions, (participant_id, test_section_id))
        print("✓ Test session data deleted")
        
        return True
    except Exception as e:
        print(f"✗ Cleanup error: {e}")
        return False

def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("DATABRICKS CONNECTION AND DATA INSERTION TEST")
    print("=" * 60)
    
    # Check if credentials are set
    from backend.config import DATABRICKS_ACCESS_TOKEN, DATABRICKS_SERVER_HOSTNAME
    if not DATABRICKS_ACCESS_TOKEN:
        print("\n✗ ERROR: DATABRICKS_ACCESS_TOKEN not set in environment variables")
        print("Please set it in your .env file or environment variables")
        sys.exit(1)
    
    print(f"\nServer: {DATABRICKS_SERVER_HOSTNAME}")
    print(f"Access Token: {'*' * 20}...{DATABRICKS_ACCESS_TOKEN[-4:] if len(DATABRICKS_ACCESS_TOKEN) > 4 else '****'}")
    
    # Run tests
    if not test_connection():
        print("\n✗ Connection test failed. Please check your credentials.")
        sys.exit(1)
    
    if not test_table_creation():
        print("\n✗ Table creation test failed.")
        sys.exit(1)
    
    success, participant_id, test_section_id = test_data_insertion()
    if not success:
        print("\n✗ Data insertion test failed.")
        sys.exit(1)
    
    if not test_data_retrieval(participant_id, test_section_id):
        print("\n✗ Data retrieval test failed.")
        cleanup_test_data(participant_id, test_section_id)
        sys.exit(1)
    
    # Ask if user wants to keep test data
    print("\n" + "=" * 60)
    response = input("Do you want to keep the test data? (y/n): ").strip().lower()
    if response != 'y':
        cleanup_test_data(participant_id, test_section_id)
    else:
        print(f"\nTest data kept with participant_id: {participant_id}, test_section_id: {test_section_id}")
    
    # Disconnect
    databricks_client.disconnect()
    
    print("\n" + "=" * 60)
    print("✓ ALL TESTS PASSED!")
    print("=" * 60)
    print("\nYour Databricks connection is working correctly!")
    print("You can now use the application to ingest real data.")

if __name__ == "__main__":
    main()

