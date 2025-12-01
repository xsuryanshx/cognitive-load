# Keystroke Capture Platform

A Python + React platform for collecting typing speed and keystroke data, designed to replicate the data collection methodology from the [136 Million Keystrokes](https://github.com/aalto-ui/136m-keystrokes) project.

## 📌 Demo  
The frontend used for keystroke data collection looks like this:

https://github.com/user-attachments/assets/d020e31e-364e-41d1-817e-ff5cca92b600

---

## 📊 Collected Data 
Each keystroke is captured with fine-grained timing and metadata.  
The dataset includes the following fields:

- **PARTICIPANT_ID** — Unique identifier for each participant.  
- **TEST_SECTION_ID** — The test or section during which data was recorded.  
- **SENTENCE** — The sentence the participant was instructed to type.  
- **KEYSTROKE_ID** — Sequential index of each keystroke.  
- **PRESS_TIME** — Timestamp of when a key was pressed.  
- **RELEASE_TIME** — Timestamp of when a key was released.  
- **LETTER** — The typed character or key (e.g., letters, SHIFT, BKSP).  
- **KEYCODE** — Numerical keycode for the corresponding physical key.

---

<img width="1066" height="400" alt="Screenshot 2025-11-21 at 4 56 00 PM" src="https://github.com/user-attachments/assets/0c25b554-68c3-49b8-bc0f-dd187720ee4e" />


## Overview

This platform captures detailed keystroke metrics including:
- Key press and release timestamps
- Key codes and character values
- Typing patterns and inter-key intervals
- Session and participant tracking

Data is stored both locally in CSV files (organized by user and session) and in Databricks Delta tables for real-time analytics and ML model training.

## Architecture

- **Backend**: FastAPI (Python) - REST API with JWT authentication for receiving and storing keystroke data
- **Frontend**: React - Typing test interface with keystroke event capture
- **Storage**: 
  - CSV files organized by user and session: `data/{user_id}/{timestamp}/`
  - Databricks Delta tables for real-time ingestion and analytics
- **Authentication**: JWT-based user authentication with secure password hashing

## Project Structure

```
cognitive-load/
├── backend/                      # Python FastAPI backend
│   ├── main.py                  # API endpoints
│   ├── models.py                 # Pydantic data models
│   ├── config.py                 # Configuration (loads from .env)
│   ├── auth.py                   # JWT authentication logic
│   ├── databricks_client/        # Databricks integration
│   │   ├── client.py            # Databricks SQL client
│   │   └── ingestion.py         # Data ingestion pipeline
│   ├── storage/
│   │   └── csv_writer.py        # CSV persistence layer
│   ├── test/                    # Test scripts
│   │   ├── test_databricks_connection.py
│   │   ├── test_data_insertion.py
│   │   └── ...
│   ├── upload_csv_to_databricks.py  # Standalone CSV upload script
│   ├── .env.example             # Environment variables template
│   ├── requirements.txt         # Python dependencies
│   └── run.sh                   # Backend startup script
└── frontend/                     # React frontend
    ├── src/
    │   ├── components/
    │   │   ├── Auth.js          # Authentication component
    │   │   └── TypingTest.js    # Main typing test component
    │   └── App.js
    └── package.json
```

**Note**: The following directories are created at runtime and are not tracked in git:
- `data/` - CSV data files organized by user and session
- `users.json` - User database file
- `venv/` - Python virtual environment

## Setup Instructions

### Prerequisites

- Python 3.8+
- Node.js 16+ and npm
- Databricks account (for real-time data ingestion)

### Backend Setup

1. Navigate to the backend directory:
```bash
cd backend
```

2. Create a virtual environment (recommended):
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. **Configure environment variables** (required):
   
   Create a `.env` file in the `backend/` directory:
   ```bash
   cp .env.example .env
   ```
   
   Edit `.env` and add your Databricks credentials:
   ```bash
   # Databricks Configuration (REQUIRED)
   DATABRICKS_SERVER_HOSTNAME=your-databricks-server-hostname.cloud.databricks.com
   DATABRICKS_HTTP_PATH=/sql/1.0/warehouses/your-warehouse-id
   DATABRICKS_ACCESS_TOKEN=your-databricks-access-token
   
   # JWT Configuration
   JWT_SECRET_KEY=your-secret-key-change-in-production
   
   # Optional: Data directory (defaults to ../data)
   DATA_DIR=../data
   
   # Optional: Users database path (defaults to users.json)
   USERS_DB_PATH=users.json
   ```
   
   **Important**: Never commit the `.env` file to version control. It's already in `.gitignore`.

5. Run the backend server (from project root):
```bash
cd ..  # Return to project root
uvicorn backend.main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`

API documentation: `http://localhost:8000/docs`

**Note**: The backend will fail to start if Databricks credentials are not set in `.env`. See `SETUP_DATABRICKS.md` for detailed Databricks setup instructions.

### Frontend Setup

1. Navigate to the frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

3. Set environment variables (optional):
```bash
export REACT_APP_API_URL=http://localhost:8000
```

4. Start the development server:
```bash
npm start
```

The frontend will be available at `http://localhost:3000`

## Usage

### Running a Typing Test

1. Start the backend server (see Backend Setup above)
2. Start the frontend server (see Frontend Setup above)
3. Open `http://localhost:3000` in your browser
4. **Register or Login**: Create an account or login with existing credentials
5. Read and accept the consent form
6. Click "Start Test" to begin
7. Type the displayed sentences
8. Complete all sentences to finish the test

**Note**: All API endpoints (except registration) require authentication. Users must register/login before starting a test.

### Viewing Collected Data

CSV data files are automatically created in the `data/` directory during test sessions, organized by user and session timestamp.

### Data Files

CSV files are organized by user and session in the `data/` directory:

```
data/
  {user_id_1}/
    20241115_143022/
      keystrokes.csv
      sessions.csv
    20241115_150145/
      keystrokes.csv
      sessions.csv
  {user_id_2}/
    20241115_160000/
      keystrokes.csv
      sessions.csv
```

Each session creates a unique timestamped folder containing:
- **keystrokes.csv**: Individual keystroke events for that session
- **sessions.csv**: Session summary statistics

This organization allows for:
- Per-user data isolation
- Easy session tracking
- Simple batch uploads to Databricks

## Data Schema

### Keystroke Events

Each keystroke event includes:
- `PARTICIPANT_ID`: Unique participant identifier
- `TEST_SECTION_ID`: Unique session identifier
- `SENTENCE`: Target sentence being typed
- `USER_INPUT`: Actual user input at capture time
- `KEYSTROKE_ID`: Sequential keystroke identifier
- `PRESS_TIME`: Key press timestamp (milliseconds)
- `RELEASE_TIME`: Key release timestamp (milliseconds)
- `LETTER`: Character or key name (e.g., 'a', 'SHIFT', 'BKSP')
- `KEYCODE`: JavaScript keyCode value

## API Endpoints

### Authentication Endpoints

#### POST `/api/auth/register`
Register a new user account.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "secure-password"
}
```

**Response:**
```json
{
  "user_id": "uuid-here",
  "email": "user@example.com",
  "created_at": "2024-01-15T10:30:00"
}
```

#### POST `/api/auth/login`
Login and receive JWT access token.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "secure-password"
}
```

**Response:**
```json
{
  "access_token": "jwt-token-here",
  "token_type": "bearer",
  "user": {
    "user_id": "uuid-here",
    "email": "user@example.com",
    "created_at": "2024-01-15T10:30:00"
  }
}
```

#### GET `/api/auth/me`
Get current authenticated user info (requires Bearer token in Authorization header).

### Test Management Endpoints

All test endpoints require authentication (Bearer token in Authorization header).

#### POST `/api/session`
Create a new typing test session.

**Request:**
```json
{
  "question_count": 10  // Number of sentences in the test
}
```

**Response:**
```json
{
  "participant_id": "uuid-here",
  "test_section_id": "uuid-here",
  "message": "Session created successfully with 10 questions"
}
```

#### POST `/api/test-section`
Create a new test section for a sentence.

**Request:**
```json
{
  "participant_id": "uuid",
  "sentence": "The quick brown fox..."
}
```

#### POST `/api/keystrokes`
Submit a batch of keystroke events.

**Request:**
```json
{
  "participant_id": "uuid",
  "test_section_id": "uuid",
  "sentence": "The quick brown fox...",
  "user_input": "The quick brown fox...",
  "keystrokes": [
    {
      "press_time": 1473284537607,
      "release_time": 1473284537771,
      "keycode": 84,
      "letter": "T"
    }
  ]
}
```

#### POST `/api/sentence-complete`
Mark a sentence as complete and trigger Databricks ingestion.

#### POST `/api/end-test`
End the test session and finalize all data.

#### GET `/api/session/{test_section_id}/stats`
Get statistics for a session.

#### GET `/api/health`
Health check endpoint (no authentication required).

## Databricks Integration

This platform includes real-time Databricks integration for data ingestion and analytics.

### Features

- **Real-time Ingestion**: Data is automatically sent to Databricks after each sentence completion
- **Delta Tables**: Data is stored in Delta tables (`keystrokes` and `sessions`) for efficient querying
- **Upsert Logic**: Re-running tests replaces existing data (not appends)
- **Automatic Table Creation**: Tables are created automatically on first use

### Setup

1. **Configure Databricks credentials** in `backend/.env` (see Backend Setup above)
2. **Start SQL Warehouse**: Ensure your Databricks SQL warehouse is running
3. **Test Connection**: Run the connection test script:
   ```bash
   cd backend
   python test/test_databricks_connection.py
   ```

### Data Upload Options

#### Option 1: Real-time Ingestion (Automatic)
Data is automatically uploaded to Databricks during the typing test. No manual steps required.

#### Option 2: Manual CSV Upload
Upload existing CSV files using the standalone script:

```bash
cd backend
python upload_csv_to_databricks.py ../data/{user_id}/{timestamp}/keystrokes.csv
```

#### Option 3: Notebook-based Ingestion
You can create a Databricks notebook for batch processing CSV files from the data directory.

### Databricks Tables

**keystrokes table:**
- participant_id, test_section_id, sentence, user_input
- keystroke_id, press_time, release_time, letter, keycode
- session_timestamp, created_at

**sessions table:**
- participant_id, test_section_id, created_at
- sentence_count, total_keystrokes, average_wpm
- session_timestamp

**Troubleshooting Databricks Connection:**
- Ensure your SQL warehouse is running in Databricks
- Verify credentials in `.env` file are correct
- Check firewall/network connectivity to Databricks
- Verify the access token has not expired

## Development

### Running Tests

**Backend Connection Tests:**
```bash
cd backend
# Test Databricks connection
python test/test_databricks_connection.py

# Test data insertion
python test/test_data_insertion.py

# Full integration test
python test/test_databricks.py
```

**Frontend tests:**
```bash
cd frontend
npm test
```

### Code Style

Backend: Follow PEP 8, use Black formatter
Frontend: Follow ESLint rules from react-scripts

## Privacy & Ethics

- Users must provide explicit consent before data collection
- Data collection is transparent and clearly explained
- Participants can decline to participate
- Data should be anonymized before sharing or analysis
- Follow applicable data protection regulations (GDPR, etc.)

## References

- [136 Million Keystrokes Project](https://github.com/aalto-ui/136m-keystrokes)
- [Observations on Typing from 136 Million Keystrokes](https://userinterfaces.aalto.fi/136Mkeystrokes/)

## License

MIT License - See LICENSE file for details

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## Security Notes

- **Environment Variables**: All sensitive credentials (Databricks tokens, JWT secrets) must be stored in `.env` file
- **Never Commit Secrets**: The `.env` file is in `.gitignore` - never commit it to version control
- **Use `.env.example`**: Copy `.env.example` to `.env` and fill in your actual values
- **JWT Secret**: Change the default JWT secret key in production

## Support

For issues or questions, please open an issue on GitHub.

