from datetime import datetime
from .client import databricks_client

try:
    from backend.models import KeystrokeBatch
except ImportError:
    from models import KeystrokeBatch


class DatabricksIngestion:
    """Real-time ingestion pipeline for Databricks"""
    
    def __init__(self):
        self.client = databricks_client
    
    def upsert_keystrokes(self, batch: KeystrokeBatch, session_timestamp: str):
        """Upsert keystroke data to Databricks (replace if exists)"""
        if not self.client.connection:
            if not self.client.connect():
                print("Failed to connect to Databricks, skipping ingestion")
                return False
        
        try:
            # Create tables if they don't exist
            self.client.create_tables()
            
            # Delete existing data for this test_section_id (upsert behavior)
            delete_query = """
            DELETE FROM keystrokes 
            WHERE participant_id = ? AND test_section_id = ?
            """
            self.client.execute(delete_query, (batch.participant_id, batch.test_section_id))
            
            # Insert new keystroke data
            insert_query = """
            INSERT INTO keystrokes 
            (participant_id, test_section_id, sentence, user_input, keystroke_id, 
             press_time, release_time, letter, keycode, session_timestamp, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            
            params_list = []
            for idx, keystroke in enumerate(batch.keystrokes):
                params_list.append((
                    batch.participant_id,
                    batch.test_section_id,
                    batch.sentence,
                    batch.user_input,
                    idx,
                    keystroke.press_time,
                    keystroke.release_time,
                    keystroke.letter,
                    keystroke.keycode,
                    session_timestamp,
                    datetime.now()
                ))
            
            if params_list:
                self.client.execute_many(insert_query, params_list)
            
            return True
        except Exception as e:
            print(f"Failed to upsert keystrokes: {e}")
            return False
    
    def upsert_session(self, participant_id: str, test_section_id: str,
                      sentence_count: int, total_keystrokes: int,
                      average_wpm: float, session_timestamp: str):
        """Upsert session data to Databricks"""
        if not self.client.connection:
            if not self.client.connect():
                print("Failed to connect to Databricks, skipping ingestion")
                return False
        
        try:
            # Create tables if they don't exist
            self.client.create_tables()
            
            # Delete existing session data (upsert behavior)
            delete_query = """
            DELETE FROM sessions 
            WHERE participant_id = ? AND test_section_id = ?
            """
            self.client.execute(delete_query, (participant_id, test_section_id))
            
            # Insert new session data
            insert_query = """
            INSERT INTO sessions 
            (participant_id, test_section_id, created_at, sentence_count, 
             total_keystrokes, average_wpm, session_timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """
            
            self.client.execute(insert_query, (
                participant_id,
                test_section_id,
                datetime.now(),
                sentence_count,
                total_keystrokes,
                float(round(average_wpm, 2)),
                session_timestamp
            ))
            
            return True
        except Exception as e:
            print(f"Failed to upsert session: {e}")
            return False
    
    def ingest_sentence_completion(self, batch: KeystrokeBatch, session_timestamp: str):
        """Ingest data after sentence completion"""
        return self.upsert_keystrokes(batch, session_timestamp)


# Singleton instance
databricks_ingestion = DatabricksIngestion()

