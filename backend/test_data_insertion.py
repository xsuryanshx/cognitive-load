#!/usr/bin/env python3
"""
Test actual data insertion to Databricks to verify the full pipeline works.
"""

import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.databricks_client.client import databricks_client
from backend.databricks_client.ingestion import databricks_ingestion
from backend.models import KeystrokeBatch, KeystrokeEvent

def test_data_insertion():
    """Test inserting actual data"""
    print("=" * 60)
    print("Testing Data Insertion to Databricks")
    print("=" * 60)
    
    # Create test data
    test_participant_id = "test_user_jdbc"
    test_section_id = f"test_section_{int(datetime.now().timestamp())}"
    test_sentence = "The quick brown fox jumps over the lazy dog."
    test_user_input = "The quick brown fox jumps over the lazy dog."
    session_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Create test keystrokes
    test_keystrokes = [
        KeystrokeEvent(
            press_time=1000 + i * 50,
            release_time=1000 + i * 50 + 20,
            keycode=65 + i if i < 26 else 32,  # A-Z or space
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
        print(f"\nTest Participant ID: {test_participant_id}")
        print(f"Test Section ID: {test_section_id}")
        print(f"Number of keystrokes: {len(test_keystrokes)}")
        
        # Test keystroke insertion
        print("\n1. Inserting keystroke data...")
        result = databricks_ingestion.upsert_keystrokes(test_batch, session_timestamp)
        
        if result:
            print("✓ Keystroke data inserted successfully!")
        else:
            print("✗ Failed to insert keystroke data")
            return False
        
        # Test session insertion
        print("\n2. Inserting session data...")
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
            return False
        
        # Verify data was inserted
        print("\n3. Verifying data insertion...")
        
        # Query keystrokes
        keystrokes_query = """
        SELECT COUNT(*) as count
        FROM keystrokes 
        WHERE participant_id = ? AND test_section_id = ?
        """
        
        result = databricks_client.execute(keystrokes_query, (test_participant_id, test_section_id))
        
        if result and len(result) > 0:
            count = result[0][0] if isinstance(result[0], (list, tuple)) else result[0]
            print(f"✓ Found {count} keystrokes in database")
            if count != len(test_keystrokes):
                print(f"  Warning: Expected {len(test_keystrokes)}, got {count}")
        else:
            print("✗ No keystrokes found")
            return False
        
        # Query sessions
        sessions_query = """
        SELECT sentence_count, total_keystrokes, average_wpm
        FROM sessions 
        WHERE participant_id = ? AND test_section_id = ?
        """
        
        result = databricks_client.execute(sessions_query, (test_participant_id, test_section_id))
        
        if result and len(result) > 0:
            session_data = result[0]
            if isinstance(session_data, (list, tuple)):
                print(f"✓ Found session data:")
                print(f"  Sentence count: {session_data[0]}")
                print(f"  Total keystrokes: {session_data[1]}")
                print(f"  Average WPM: {session_data[2]}")
            else:
                print(f"✓ Found session data: {session_data}")
        else:
            print("✗ No session data found")
            return False
        
        # Cleanup
        print("\n4. Cleaning up test data...")
        cleanup_query_keystrokes = """
        DELETE FROM keystrokes 
        WHERE participant_id = ? AND test_section_id = ?
        """
        cleanup_query_sessions = """
        DELETE FROM sessions 
        WHERE participant_id = ? AND test_section_id = ?
        """
        
        databricks_client.execute(cleanup_query_keystrokes, (test_participant_id, test_section_id))
        databricks_client.execute(cleanup_query_sessions, (test_participant_id, test_section_id))
        print("✓ Test data cleaned up")
        
        return True
        
    except Exception as e:
        print(f"✗ Data insertion test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        databricks_client.disconnect()

def main():
    print("\n" + "=" * 60)
    print("DATABRICKS DATA INSERTION TEST")
    print("=" * 60)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    if test_data_insertion():
        print("\n" + "=" * 60)
        print("✓ ALL TESTS PASSED!")
        print("=" * 60)
        print("\nYour Databricks connection and data insertion are working correctly!")
        print("You can now use your application to ingest real keystroke data.")
    else:
        print("\n" + "=" * 60)
        print("✗ DATA INSERTION TEST FAILED")
        print("=" * 60)
        sys.exit(1)

if __name__ == "__main__":
    main()

