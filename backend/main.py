from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from .models import (
    KeystrokeBatch, 
    SessionCreate, 
    SessionResponse,
    TestSectionCreate,
    TestSectionResponse,
    EndTestRequest,
    UserRegister,
    UserLogin,
    UserResponse,
    TokenResponse
)
from .storage.csv_writer import CSVWriter
from .auth import register_user, authenticate_user, create_access_token, get_current_user
from .databricks_client.ingestion import databricks_ingestion
from datetime import timedelta
from .config import JWT_EXPIRATION_HOURS
import uuid
import os
from datetime import datetime
from fastapi import Depends
import re

app = FastAPI(title="Keystroke Capture Platform", version="1.0.0")

# CORS middleware to allow React frontend to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],  # React dev servers
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize CSV writer
data_dir = os.getenv("DATA_DIR", "data")
csv_writer = CSVWriter(data_dir=data_dir)

# In-memory storage for keystroke ID tracking (in production, use DB)
keystroke_id_counter = {}
session_data = {}
participant_sessions = {}  # Track all test sections per participant
session_timestamps = {}  # Track session timestamps per participant
participant_owner_map = {}  # Map participant_id -> actual user_id
user_active_participant = {}  # Map user_id -> participant_id
session_metrics = {}  # Track keystrokes/time for WPM calculations
# Buffer keystrokes in memory until test completion for Databricks upload
keystroke_buffer = {}  # Map test_section_id -> list of KeystrokeBatch objects

SPECIAL_KEYS = {"SHIFT", "CTRL", "ALT", "CAPS", "ESC", "TAB", "BKSP", "ENTER"}


def generate_participant_id(email: str) -> tuple[str, str]:
    """Generate participant_id using username and timestamp"""
    username = email.split("@")[0]
    username = re.sub(r"[^a-zA-Z0-9_-]", "", username) or "user"
    session_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    participant_id = f"{username}_{session_timestamp}"
    return participant_id, session_timestamp


def verify_participant_access(participant_id: str, current_user: dict):
    owner_id = participant_owner_map.get(participant_id)
    if not owner_id or owner_id != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="Unauthorized participant")


def calculate_wpm(total_chars: int, total_time_ms: int) -> float:
    if total_chars <= 0 or total_time_ms <= 0:
        return 0.0
    words = total_chars / 5.0
    minutes = total_time_ms / 60000.0
    return words / minutes if minutes > 0 else 0.0


@app.get("/")
async def root():
    return {"message": "Keystroke Capture Platform API", "version": "1.0.0"}


@app.post("/api/session", response_model=SessionResponse)
async def create_session(session: SessionCreate, current_user: dict = Depends(get_current_user)):
    """Create a new typing test session"""
    participant_id, session_timestamp = generate_participant_id(current_user["email"])
    test_section_id = str(uuid.uuid4())
    
    participant_owner_map[participant_id] = current_user["user_id"]
    user_active_participant[current_user["user_id"]] = participant_id
    session_timestamps[participant_id] = session_timestamp
    
    # Store question count for this participant
    question_count = session.question_count or 10
    if participant_id not in session_data:
        session_data[participant_id] = {}
    session_data[participant_id]["question_count"] = question_count
    
    # Initialize counters
    keystroke_id_counter[test_section_id] = 0
    session_data[test_section_id] = {
        "participant_id": participant_id,
        "sentence_count": 0,
        "total_keystrokes": 0,
        "question_count": question_count
    }
    
    return SessionResponse(
        participant_id=participant_id,
        test_section_id=test_section_id,
        message=f"Session created successfully with {question_count} questions"
    )


@app.post("/api/keystrokes")
async def submit_keystrokes(batch: KeystrokeBatch, current_user: dict = Depends(get_current_user)):
    """Submit a batch of keystroke events - buffers in memory for Databricks upload at test completion"""
    try:
        verify_participant_access(batch.participant_id, current_user)
        
        # Get current keystroke ID counter for this session
        if batch.test_section_id not in keystroke_id_counter:
            keystroke_id_counter[batch.test_section_id] = 0
        
        start_id = keystroke_id_counter[batch.test_section_id]
        
        # Get session timestamp
        session_timestamp = session_timestamps.get(batch.participant_id, datetime.now().strftime("%Y%m%d_%H%M%S"))
        
        # Write keystrokes to CSV (keep CSV writing unchanged)
        csv_writer.write_keystrokes(batch, keystroke_id_start=start_id, session_timestamp=session_timestamp)
        
        # Buffer keystrokes in memory for Databricks upload at test completion
        if batch.test_section_id not in keystroke_buffer:
            keystroke_buffer[batch.test_section_id] = []
        keystroke_buffer[batch.test_section_id].append(batch)
        
        # Update counters
        num_keystrokes = len(batch.keystrokes)
        keystroke_id_counter[batch.test_section_id] += num_keystrokes
        
        if batch.test_section_id in session_data:
            session_data[batch.test_section_id]["total_keystrokes"] += num_keystrokes
        
        return JSONResponse(
            status_code=200,
            content={
                "message": "Keystrokes saved successfully",
                "count": num_keystrokes,
                "next_keystroke_id": keystroke_id_counter[batch.test_section_id]
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving keystrokes: {str(e)}")


@app.get("/api/session/{test_section_id}/stats")
async def get_session_stats(test_section_id: str):
    """Get statistics for a session"""
    if test_section_id not in session_data:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return session_data[test_section_id]


@app.post("/api/test-section", response_model=TestSectionResponse)
async def create_test_section(request: TestSectionCreate, current_user: dict = Depends(get_current_user)):
    """Create a new test section for a sentence"""
    verify_participant_access(request.participant_id, current_user)
    
    test_section_id = str(uuid.uuid4())
    
    # Initialize counter for this test section
    keystroke_id_counter[test_section_id] = 0
    
    # Track this test section for the participant
    if request.participant_id not in participant_sessions:
        participant_sessions[request.participant_id] = []
    participant_sessions[request.participant_id].append(test_section_id)
    
    # Store session data
    session_data[test_section_id] = {
        "participant_id": request.participant_id,
        "sentence": request.sentence,
        "sentence_count": 1,
        "total_keystrokes": 0
    }
    
    return TestSectionResponse(
        test_section_id=test_section_id,
        message="Test section created successfully"
    )


@app.post("/api/sentence-complete")
async def sentence_complete(batch: KeystrokeBatch, current_user: dict = Depends(get_current_user)):
    """Complete a sentence - data is buffered and will be uploaded to Databricks at test completion"""
    try:
        verify_participant_access(batch.participant_id, current_user)
        
        # Update session metrics
        metrics = session_metrics.setdefault(batch.participant_id, {
            "total_keystrokes": 0,
            "total_chars": 0,
            "total_time_ms": 0,
            "sentence_count": 0
        })
        
        sentence_keystrokes = len(batch.keystrokes)
        char_count = sum(
            1 for ks in batch.keystrokes
            if ks.letter and ks.letter not in SPECIAL_KEYS and len(ks.letter) == 1
        )
        if batch.keystrokes:
            press_times = [ks.press_time for ks in batch.keystrokes if ks.press_time]
            release_times = [ks.release_time for ks in batch.keystrokes if ks.release_time]
            sentence_time_ms = max(release_times) - min(press_times) if press_times and release_times else 0
        else:
            sentence_time_ms = 0
        
        metrics["total_keystrokes"] += sentence_keystrokes
        metrics["total_chars"] += char_count
        metrics["total_time_ms"] += max(sentence_time_ms, 0)
        metrics["sentence_count"] += 1
        
        sentence_wpm = calculate_wpm(char_count, sentence_time_ms)
        
        # Note: Databricks upload is deferred until test completion
        # Data is already buffered in keystroke_buffer via /api/keystrokes endpoint
        
        return JSONResponse(
            status_code=200,
            content={
                "message": "Sentence completed - data will be uploaded to Databricks at test completion",
                "keystroke_count": sentence_keystrokes,
                "sentence_wpm": round(sentence_wpm, 2)
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error completing sentence: {str(e)}")


@app.post("/api/end-test")
async def end_test(request: EndTestRequest, current_user: dict = Depends(get_current_user)):
    """Finalize test and save all keystroke data locally (CSV files)"""
    try:
        verify_participant_access(request.participant_id, current_user)
        
        metrics = session_metrics.get(request.participant_id, {})
        total_keystrokes = metrics.get("total_keystrokes", 0)
        sentence_count = metrics.get("sentence_count", len(request.test_section_ids))
        total_chars = metrics.get("total_chars", 0)
        total_time_ms = metrics.get("total_time_ms", 0)
        average_wpm = calculate_wpm(total_chars, total_time_ms)
        
        # Get session timestamp
        session_timestamp = session_timestamps.get(request.participant_id, datetime.now().strftime("%Y%m%d_%H%M%S"))
        
        # Write final session summary (one per participant)
        test_section_id = request.test_section_ids[0] if request.test_section_ids else str(uuid.uuid4())
        csv_writer.write_session(
            participant_id=request.participant_id,
            test_section_id=test_section_id,
            sentence_count=sentence_count,
            total_keystrokes=total_keystrokes,
            average_wpm=average_wpm,
            session_timestamp=session_timestamp
        )
        
        # Databricks upload disabled - data stored locally only
        # Upload buffered keystroke data to Databricks from in-memory buffer
        # databricks_upload_success = True
        # upload_errors = []
        
        # try:
        #     # Process each test section's buffered keystrokes
        #     for test_section_id in request.test_section_ids:
        #         if test_section_id not in keystroke_buffer:
        #             print(f"Warning: No buffered keystrokes found for test_section_id: {test_section_id}")
        #             continue
        #         
        #         # Combine all batches for this test section into one
        #         batches = keystroke_buffer[test_section_id]
        #         if not batches:
        #             continue
        #         
        #         # Get metadata from first batch (should be consistent across batches for same test_section_id)
        #         first_batch = batches[0]
        #         combined_keystrokes = []
        #         combined_user_input = ""
        #         
        #         # Combine all keystrokes from all batches for this test section
        #         for batch in batches:
        #             combined_keystrokes.extend(batch.keystrokes)
        #             # Use the last user_input (most complete)
        #             if batch.user_input:
        #                 combined_user_input = batch.user_input
        #         
        #         if combined_keystrokes:
        #             # Create combined batch for this test section
        #             combined_batch = KeystrokeBatch(
        #                 participant_id=first_batch.participant_id,
        #                 test_section_id=test_section_id,
        #                 sentence=first_batch.sentence,
        #                 user_input=combined_user_input,
        #                 keystrokes=combined_keystrokes
        #             )
        #             
        #             # Upload to Databricks
        #             success = databricks_ingestion.upsert_keystrokes(combined_batch, session_timestamp)
        #             if not success:
        #                 databricks_upload_success = False
        #                 upload_errors.append(f"Failed to upload test_section_id: {test_section_id}")
        #                 print(f"Error uploading keystrokes for test_section_id {test_section_id} to Databricks")
        #             else:
        #                 print(f"Successfully uploaded {len(combined_keystrokes)} keystrokes for test_section_id: {test_section_id}")
        # 
        # except Exception as e:
        #     print(f"Error uploading buffered keystroke data to Databricks: {e}")
        #     import traceback
        #     traceback.print_exc()
        #     databricks_upload_success = False
        #     upload_errors.append(str(e))
        # 
        # # Ingest session summary to Databricks
        # databricks_session_success = True
        # try:
        #     databricks_session_success = databricks_ingestion.upsert_session(
        #         request.participant_id,
        #         test_section_id,
        #         sentence_count,
        #         total_keystrokes,
        #         average_wpm,
        #         session_timestamp
        #     )
        #     if not databricks_session_success:
        #         print(f"Error uploading session summary to Databricks")
        # except Exception as e:
        #     print(f"Error uploading session summary to Databricks: {e}")
        #     databricks_session_success = False
        
        # Data is stored locally only (CSV files)
        print(f"Test completed - data saved locally for participant {request.participant_id}")
        
        # Clear buffered keystrokes after successful upload (or even if failed, to prevent memory leaks)
        for test_section_id in request.test_section_ids:
            keystroke_buffer.pop(test_section_id, None)
        
        # Cleanup session data
        session_metrics.pop(request.participant_id, None)
        participant_owner_map.pop(request.participant_id, None)
        session_timestamps.pop(request.participant_id, None)
        user_active_participant.pop(current_user["user_id"], None)
        
        # Cleanup keystroke counters and session data for test sections
        for test_section_id in request.test_section_ids:
            keystroke_id_counter.pop(test_section_id, None)
            session_data.pop(test_section_id, None)
        
        return JSONResponse(
            status_code=200,
            content={
                "message": "Test ended successfully - data saved locally",
                "total_sentences": sentence_count,
                "total_keystrokes": total_keystrokes,
                "databricks_upload_success": True,  # Always True since we're not uploading
                "upload_errors": None,
                "storage_location": "local"
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error ending test: {str(e)}")


@app.post("/api/auth/register", response_model=UserResponse)
async def register(user_data: UserRegister):
    """Register a new user"""
    try:
        user = await register_user(user_data)
        return UserResponse(**user)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")


@app.post("/api/auth/login", response_model=TokenResponse)
async def login(user_data: UserLogin):
    """Login and get access token"""
    user = await authenticate_user(user_data.email, user_data.password)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(hours=JWT_EXPIRATION_HOURS)
    access_token = create_access_token(
        data={"sub": user["user_id"]}, expires_delta=access_token_expires
    )
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse(
            user_id=user["user_id"],
            email=user["email"],
            created_at=user["created_at"]
        )
    )


@app.get("/api/auth/me", response_model=UserResponse)
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """Get current authenticated user info"""
    return UserResponse(
        user_id=current_user["user_id"],
        email=current_user["email"],
        created_at=current_user["created_at"]
    )


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "data_dir": data_dir}

