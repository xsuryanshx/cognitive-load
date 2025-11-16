from databricks import sql
import os
from typing import Optional
from datetime import datetime

try:
    from backend.config import DATABRICKS_SERVER_HOSTNAME, DATABRICKS_HTTP_PATH, DATABRICKS_ACCESS_TOKEN
except ImportError:
    from config import DATABRICKS_SERVER_HOSTNAME, DATABRICKS_HTTP_PATH, DATABRICKS_ACCESS_TOKEN


class DatabricksClient:
    """Databricks SQL connector client"""
    
    def __init__(self):
        self.connection = None
        self.cursor = None
    
    def connect(self):
        """Establish connection to Databricks"""
        try:
            self.connection = sql.connect(
                server_hostname=DATABRICKS_SERVER_HOSTNAME,
                http_path=DATABRICKS_HTTP_PATH,
                access_token=DATABRICKS_ACCESS_TOKEN
            )
            self.cursor = self.connection.cursor()
            return True
        except Exception as e:
            print(f"Failed to connect to Databricks: {e}")
            return False
    
    def disconnect(self):
        """Close connection"""
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.connection.close()
    
    def execute(self, query: str, params: Optional[tuple] = None):
        """Execute a SQL query"""
        if not self.connection:
            if not self.connect():
                raise Exception("Failed to connect to Databricks")
        
        try:
            # Databricks SQL connector doesn't support standard parameterized queries
            # We need to use string formatting with proper escaping
            if params:
                # Process parameters - escape strings and format datetimes
                processed_params = []
                for param in params:
                    if isinstance(param, datetime):
                        # Format datetime for SQL TIMESTAMP
                        processed_params.append(f"'{param.strftime('%Y-%m-%d %H:%M:%S')}'")
                    elif isinstance(param, str):
                        # Escape single quotes in string parameters
                        escaped = param.replace("'", "''")
                        processed_params.append(f"'{escaped}'")
                    else:
                        processed_params.append(str(param))
                
                # Replace ? placeholders with formatted values
                formatted_query = query
                for param_value in processed_params:
                    formatted_query = formatted_query.replace('?', param_value, 1)
                
                self.cursor.execute(formatted_query)
            else:
                self.cursor.execute(query)
            
            # Use fetchall_arrow() to avoid pandas/numpy compatibility issues
            try:
                arrow_table = self.cursor.fetchall_arrow()
                if arrow_table:
                    # Convert Arrow table to list of tuples
                    return [tuple(row) for row in arrow_table.to_pylist()]
                return []
            except Exception:
                # Fallback to regular fetchall if Arrow fails
                return self.cursor.fetchall()
        except Exception as e:
            print(f"Query execution failed: {e}")
            raise
    
    def execute_many(self, query: str, params_list: list):
        """Execute a query with multiple parameter sets"""
        if not self.connection:
            if not self.connect():
                raise Exception("Failed to connect to Databricks")
        
        try:
            # Format query for each param set using string formatting
            for params in params_list:
                # Process parameters - escape strings and format datetimes
                processed_params = []
                for param in params:
                    if isinstance(param, datetime):
                        # Format datetime for SQL TIMESTAMP
                        processed_params.append(f"'{param.strftime('%Y-%m-%d %H:%M:%S')}'")
                    elif isinstance(param, str):
                        # Escape single quotes in string parameters
                        escaped = param.replace("'", "''")
                        processed_params.append(f"'{escaped}'")
                    else:
                        processed_params.append(str(param))
                
                # Replace ? placeholders with formatted values
                formatted_query = query
                for param_value in processed_params:
                    formatted_query = formatted_query.replace('?', param_value, 1)
                
                self.cursor.execute(formatted_query)
            return True
        except Exception as e:
            print(f"Batch execution failed: {e}")
            raise
    
    def create_tables(self):
        """Create Delta tables if they don't exist"""
        # Note: Databricks Delta doesn't support PRIMARY KEY constraint in CREATE TABLE
        # We'll use composite key logic in queries instead
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
            self.execute(keystrokes_table)
            self.execute(sessions_table)
            print("Tables created successfully")
            return True
        except Exception as e:
            print(f"Failed to create tables: {e}")
            return False


# Singleton instance
databricks_client = DatabricksClient()

