import csv
import os
from datetime import datetime
from pathlib import Path
from typing import List
import threading

try:
    from backend.models import KeystrokeBatch, KeystrokeEvent
except ImportError:
    from models import KeystrokeBatch, KeystrokeEvent


class CSVWriter:
    """Thread-safe CSV writer for keystroke data with per-session folders"""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        self.lock = threading.Lock()
        self._session_folders = {}  # Track session folders
        
    def _get_session_folder(self, participant_id: str, session_timestamp: str) -> Path:
        """Get or create session folder: data/{participant_id}/{session_timestamp}/"""
        session_folder = self.data_dir / participant_id / session_timestamp
        session_folder.mkdir(parents=True, exist_ok=True)
        return session_folder
    
    def _ensure_files_exist(self, session_folder: Path):
        """Ensure CSV files exist with headers in session folder"""
        keystrokes_file = session_folder / "keystrokes.csv"
        sessions_file = session_folder / "sessions.csv"
        
        # Create keystrokes file with headers if it doesn't exist
        if not keystrokes_file.exists():
            with open(keystrokes_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'PARTICIPANT_ID',
                    'TEST_SECTION_ID',
                    'SENTENCE',
                    'USER_INPUT',
                    'KEYSTROKE_ID',
                    'PRESS_TIME',
                    'RELEASE_TIME',
                    'LETTER',
                    'KEYCODE'
                ])
        
        # Create sessions file with headers if it doesn't exist
        if not sessions_file.exists():
            with open(sessions_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'PARTICIPANT_ID',
                    'TEST_SECTION_ID',
                    'CREATED_AT',
                    'SENTENCE_COUNT',
                    'TOTAL_KEYSTROKES',
                    'AVERAGE_WPM'
                ])
        
        return keystrokes_file, sessions_file
    
    def write_keystrokes(self, batch: KeystrokeBatch, keystroke_id_start: int = 0, 
                        session_timestamp: str = None):
        """Write keystroke batch to CSV file in session folder"""
        if session_timestamp is None:
            session_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        with self.lock:
            session_folder = self._get_session_folder(batch.participant_id, session_timestamp)
            keystrokes_file, _ = self._ensure_files_exist(session_folder)
            
            with open(keystrokes_file, 'a', newline='') as f:
                writer = csv.writer(f)
                for idx, keystroke in enumerate(batch.keystrokes):
                    writer.writerow([
                        batch.participant_id,
                        batch.test_section_id,
                        batch.sentence,
                        batch.user_input,
                        keystroke_id_start + idx,
                        keystroke.press_time,
                        keystroke.release_time,
                        keystroke.letter,
                        keystroke.keycode
                    ])
    
    def write_session(self, participant_id: str, test_section_id: str, 
                     sentence_count: int = 0, total_keystrokes: int = 0,
                     average_wpm: float = 0.0,
                     session_timestamp: str = None):
        """Write session summary to CSV file in session folder"""
        if session_timestamp is None:
            session_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        with self.lock:
            session_folder = self._get_session_folder(participant_id, session_timestamp)
            _, sessions_file = self._ensure_files_exist(session_folder)
            
            with open(sessions_file, 'a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    participant_id,
                    test_section_id,
                    datetime.now().isoformat(),
                    sentence_count,
                    total_keystrokes,
                    round(average_wpm, 2)
                ])

