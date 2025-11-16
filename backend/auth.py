from datetime import datetime, timedelta
from typing import Optional
import json
import os
from pathlib import Path
import uuid
from jose import JWTError, jwt
import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from .config import JWT_SECRET_KEY, JWT_ALGORITHM, JWT_EXPIRATION_HOURS, USERS_DB_PATH
from .models import UserRegister, UserLogin, UserResponse

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


class UserDB:
    """Simple JSON-based user database"""
    
    def __init__(self, db_path: str = USERS_DB_PATH):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.db_path.exists():
            self._init_db()
    
    def _init_db(self):
        """Initialize empty database"""
        with open(self.db_path, 'w') as f:
            json.dump({"users": []}, f)
    
    def _load_db(self):
        """Load database from file"""
        try:
            with open(self.db_path, 'r') as f:
                return json.load(f)
        except:
            return {"users": []}
    
    def _save_db(self, data):
        """Save database to file"""
        with open(self.db_path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def create_user(self, email: str, password_hash: str) -> str:
        """Create a new user and return user_id"""
        db = self._load_db()
        user_id = str(uuid.uuid4())
        
        # Check if email already exists
        for user in db["users"]:
            if user["email"] == email:
                raise ValueError("Email already registered")
        
        user = {
            "user_id": user_id,
            "email": email,
            "password_hash": password_hash,
            "created_at": datetime.now().isoformat()
        }
        
        db["users"].append(user)
        self._save_db(db)
        return user_id
    
    def get_user_by_email(self, email: str) -> Optional[dict]:
        """Get user by email"""
        db = self._load_db()
        for user in db["users"]:
            if user["email"] == email:
                return user
        return None
    
    def get_user_by_id(self, user_id: str) -> Optional[dict]:
        """Get user by user_id"""
        db = self._load_db()
        for user in db["users"]:
            if user["user_id"] == user_id:
                return user
        return None


user_db = UserDB()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash"""
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception:
        return False


def get_password_hash(password: str) -> str:
    """Hash a password"""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt


async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    """Get current authenticated user from JWT token"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = user_db.get_user_by_id(user_id)
    if user is None:
        raise credentials_exception
    return user


async def register_user(user_data: UserRegister) -> dict:
    """Register a new user"""
    password_hash = get_password_hash(user_data.password)
    try:
        user_id = user_db.create_user(user_data.email, password_hash)
        user = user_db.get_user_by_id(user_id)
        return {
            "user_id": user_id,
            "email": user["email"],
            "created_at": user["created_at"]
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


async def authenticate_user(email: str, password: str) -> Optional[dict]:
    """Authenticate user and return user data if valid"""
    user = user_db.get_user_by_email(email)
    if not user:
        return None
    if not verify_password(password, user["password_hash"]):
        return None
    return user

