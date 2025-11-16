#!/usr/bin/env python3
"""
Standalone script to upload CSV data to Databricks
Usage: python upload_csv_to_databricks.py <path_to_keystrokes.csv>
"""

import sys
import csv
from pathlib import Path
from datetime import datetime
from databricks import sql
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Databricks Configuration
# These must be set in .env file - no defaults to prevent exposing secrets
DATABRICKS_SERVER_HOSTNAME = os.getenv("DATABRICKS_SERVER_HOSTNAME")
if not DATABRICKS_SERVER_HOSTNAME:
    raise ValueError("DATABRICKS_SERVER_HOSTNAME must be set in .env file")

DATABRICKS_HTTP_PATH = os.getenv("DATABRICKS_HTTP_PATH")
if not DATABRICKS_HTTP_PATH:
    raise ValueError("DATABRICKS_HTTP_PATH must be set in .env file")

DATABRICKS_ACCESS_TOKEN = os.getenv("DATABRICKS_ACCESS_TOKEN")
if not DATABRICKS_ACCESS_TOKEN:
    raise ValueError("DATABRICKS_ACCESS_TOKEN must be set in .env file")


def connect_to_databricks():
    """Establish connection to Databricks"""
    try:
        connection = sql.connect(
            server_hostname=DATABRICKS_SERVER_HOSTNAME,
            http_path=DATABRICKS_HTTP_PATH,
            access_token=DATABRICKS_ACCESS_TOKEN
        )
        print("✓ Connected to Databricks successfully")
        return connection
    except Exception as e:
        print(f"✗ Failed to connect to Databricks: {e}")
        return None


def create_tables(cursor):
    """Create Delta tables if they don't exist"""
    keystrokes_table = """
    CREATE TABLE IF NOT EXISTS keystrokes (
        participant_id STRING,
        test_section_id STRING,
        sentence STRING,
        user_input STRING,
        keystroke_id BIGINT,
        press_time BIGINT,
        release_time BIGINT,
        letter STRING,
        keycode INT,
        session_timestamp STRING,
        created_at TIMESTAMP
    ) USING DELTA
    """
    
    sessions_table = """
    CREATE TABLE IF NOT EXISTS sessions (
        participant_id STRING,
        test_section_id STRING,
        created_at TIMESTAMP,
        sentence_count INT,
        total_keystrokes INT,
        average_wpm DOUBLE,
        session_timestamp STRING
    ) USING DELTA
    """
    
    try:
        cursor.execute(keystrokes_table)
        print("✓ Keystrokes table ready")
        cursor.execute(sessions_table)
        print("✓ Sessions table ready")
        return True
    except Exception as e:
        print(f"✗ Failed to create tables: {e}")
        return False


def read_csv_file(csv_path):
    """Read CSV file and return data"""
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        print(f"✓ Read {len(rows)} rows from CSV file")
        return rows
    except Exception as e:
        print(f"✗ Failed to read CSV file: {e}")
        return None


def extract_session_timestamp(csv_path):
    """Extract session timestamp from path"""
    path_parts = Path(csv_path).parts
    # Path format: .../participant_id_timestamp/timestamp/keystrokes.csv
    for part in path_parts:
        if '_' in part and part.count('_') >= 3:
            # Extract timestamp from format like: akankshamattoo_20251115_183835
            parts = part.split('_')
            if len(parts) >= 3:
                return f"{parts[-2]}_{parts[-1]}"
    
    # Fallback to timestamp folder name
    if len(path_parts) >= 2:
        return path_parts[-2]
    
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def insert_keystrokes(cursor, rows, session_timestamp):
    """Insert keystroke data into Databricks"""
    if not rows:
        print("✗ No data to insert")
        return False
    
    try:
        insert_query = """
        INSERT INTO keystrokes 
        (participant_id, test_section_id, sentence, user_input, keystroke_id, 
         press_time, release_time, letter, keycode, session_timestamp, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        inserted_count = 0
        batch_size = 100
        
        for i in range(0, len(rows), batch_size):
            batch = rows[i:i + batch_size]
            
            for row in batch:
                # Escape single quotes in string fields
                participant_id = row.get('PARTICIPANT_ID', '').replace("'", "''")
                test_section_id = row.get('TEST_SECTION_ID', '').replace("'", "''")
                sentence = row.get('SENTENCE', '').replace("'", "''")
                user_input = row.get('USER_INPUT', '').replace("'", "''")
                keystroke_id = int(row.get('KEYSTROKE_ID', 0))
                press_time = int(row.get('PRESS_TIME', 0))
                release_time = int(row.get('RELEASE_TIME', 0))
                letter = row.get('LETTER', '').replace("'", "''")
                keycode = int(row.get('KEYCODE', 0))
                created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
                # Format query with values (Databricks SQL connector limitation)
                formatted_query = f"""
                INSERT INTO keystrokes 
                (participant_id, test_section_id, sentence, user_input, keystroke_id, 
                 press_time, release_time, letter, keycode, session_timestamp, created_at)
                VALUES ('{participant_id}', '{test_section_id}', '{sentence}', '{user_input}', {keystroke_id}, 
                        {press_time}, {release_time}, '{letter}', {keycode}, '{session_timestamp}', '{created_at}')
                """
                
                cursor.execute(formatted_query)
                inserted_count += 1
            
            print(f"  Inserted {min(i + batch_size, len(rows))}/{len(rows)} rows...")
        
        print(f"✓ Successfully inserted {inserted_count} keystrokes")
        return True
        
    except Exception as e:
        print(f"✗ Failed to insert keystrokes: {e}")
        import traceback
        traceback.print_exc()
        return False


def calculate_session_stats(rows):
    """Calculate session statistics from keystroke data"""
    if not rows:
        return None
    
    participant_id = rows[0].get('PARTICIPANT_ID', '')
    test_section_id = rows[0].get('TEST_SECTION_ID', '')
    total_keystrokes = len(rows)
    
    # Count unique sentences
    sentences = set(row.get('SENTENCE', '') for row in rows)
    sentence_count = len(sentences)
    
    # Calculate WPM (simplified - using first and last keystroke)
    try:
        first_press = int(rows[0].get('PRESS_TIME', 0))
        last_release = int(rows[-1].get('RELEASE_TIME', 0))
        time_diff_ms = last_release - first_press
        
        # Count characters (excluding special keys)
        special_keys = ['SHIFT', 'CTRL', 'ALT', 'CAPS', 'ESC', 'TAB', 'BKSP', 'ENTER', 'SPACE']
        char_count = sum(1 for row in rows if row.get('LETTER', '') not in special_keys)
        
        if time_diff_ms > 0 and char_count > 0:
            words = char_count / 5.0
            minutes = time_diff_ms / 60000.0
            average_wpm = words / minutes if minutes > 0 else 0
        else:
            average_wpm = 0.0
    except:
        average_wpm = 0.0
    
    return {
        'participant_id': participant_id,
        'test_section_id': test_section_id,
        'sentence_count': sentence_count,
        'total_keystrokes': total_keystrokes,
        'average_wpm': round(average_wpm, 2)
    }


def insert_session(cursor, stats, session_timestamp):
    """Insert session summary into Databricks"""
    if not stats:
        return False
    
    try:
        created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        formatted_query = f"""
        INSERT INTO sessions 
        (participant_id, test_section_id, created_at, sentence_count, 
         total_keystrokes, average_wpm, session_timestamp)
        VALUES ('{stats['participant_id']}', '{stats['test_section_id']}', 
                '{created_at}', {stats['sentence_count']}, 
                {stats['total_keystrokes']}, {stats['average_wpm']}, '{session_timestamp}')
        """
        
        cursor.execute(formatted_query)
        print(f"✓ Inserted session summary (WPM: {stats['average_wpm']}, Keystrokes: {stats['total_keystrokes']})")
        return True
        
    except Exception as e:
        print(f"✗ Failed to insert session: {e}")
        return False


def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("Usage: python upload_csv_to_databricks.py <path_to_keystrokes.csv>")
        print("\nExample:")
        print("  python upload_csv_to_databricks.py ../data/user_20251115_183835/20251115_183835/keystrokes.csv")
        sys.exit(1)
    
    csv_path = sys.argv[1]
    
    print(f"\n{'='*70}")
    print(f"Uploading CSV to Databricks")
    print(f"{'='*70}\n")
    print(f"CSV File: {csv_path}")
    
    # Check if file exists
    if not Path(csv_path).exists():
        print(f"✗ File not found: {csv_path}")
        sys.exit(1)
    
    # Extract session timestamp
    session_timestamp = extract_session_timestamp(csv_path)
    print(f"Session Timestamp: {session_timestamp}\n")
    
    # Read CSV data
    rows = read_csv_file(csv_path)
    if not rows:
        sys.exit(1)
    
    # Connect to Databricks
    connection = connect_to_databricks()
    if not connection:
        sys.exit(1)
    
    cursor = connection.cursor()
    
    try:
        # Create tables
        if not create_tables(cursor):
            sys.exit(1)
        
        print()
        
        # Insert keystrokes
        if not insert_keystrokes(cursor, rows, session_timestamp):
            sys.exit(1)
        
        # Calculate and insert session stats
        stats = calculate_session_stats(rows)
        if stats:
            insert_session(cursor, stats, session_timestamp)
        
        print(f"\n{'='*70}")
        print("✓ Upload completed successfully!")
        print(f"{'='*70}\n")
        
    finally:
        cursor.close()
        connection.close()
        print("✓ Connection closed")


if __name__ == "__main__":
    main()

