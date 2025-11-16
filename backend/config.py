import os
from dotenv import load_dotenv

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

# JWT Configuration
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

# Database (for users - using JSON file for simplicity, can be replaced with real DB)
USERS_DB_PATH = os.getenv("USERS_DB_PATH", "users.json")

