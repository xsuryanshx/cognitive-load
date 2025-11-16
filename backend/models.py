from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class KeystrokeEvent(BaseModel):
    """Individual keystroke event matching 136m-keystrokes schema"""
    press_time: int = Field(..., description="Timestamp when key was pressed (milliseconds)")
    release_time: int = Field(..., description="Timestamp when key was released (milliseconds)")
    keycode: int = Field(..., description="JavaScript keyCode of the pressed key")
    letter: str = Field(..., description="Character or key name (e.g., 'a', 'SHIFT', 'BKSP')")


class KeystrokeBatch(BaseModel):
    """Batch of keystroke events from frontend"""
    participant_id: str = Field(..., description="Unique identifier for the participant")
    test_section_id: str = Field(..., description="Unique identifier for the test session/section")
    sentence: str = Field(..., description="Target sentence the user was typing")
    user_input: str = Field(..., description="Actual user input at the time of capture")
    keystrokes: List[KeystrokeEvent] = Field(..., description="List of keystroke events")


class SessionCreate(BaseModel):
    """Request to create a new typing test session"""
    participant_id: Optional[str] = Field(None, description="Optional participant ID, will be generated if not provided")
    question_count: Optional[int] = Field(10, description="Number of questions/sentences to ask in the test", ge=1, le=50)


class SessionResponse(BaseModel):
    """Response with session information"""
    participant_id: str
    test_section_id: str
    message: str


class TestSectionCreate(BaseModel):
    """Request to create a new test section for a sentence"""
    participant_id: str = Field(..., description="Participant ID")
    sentence: str = Field(..., description="The sentence for this test section")


class TestSectionResponse(BaseModel):
    """Response with test section information"""
    test_section_id: str
    message: str


class EndTestRequest(BaseModel):
    """Request to end the test"""
    participant_id: str = Field(..., description="Participant ID")
    test_section_ids: List[str] = Field(..., description="List of all test section IDs in this test")


class UserRegister(BaseModel):
    """User registration request"""
    email: str = Field(..., description="User email address")
    password: str = Field(..., min_length=6, description="User password")


class UserLogin(BaseModel):
    """User login request"""
    email: str = Field(..., description="User email address")
    password: str = Field(..., description="User password")


class UserResponse(BaseModel):
    """User response model"""
    user_id: str
    email: str
    created_at: str


class TokenResponse(BaseModel):
    """Token response model"""
    access_token: str
    token_type: str
    user: UserResponse

