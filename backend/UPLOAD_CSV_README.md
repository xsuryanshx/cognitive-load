# CSV to Databricks Upload Script

This standalone script uploads keystroke CSV data to Databricks.

## Usage

### Basic Usage

```bash
cd /Users/suryanshrawat/Documents/github/databricks_hack/backend
source venv/bin/activate
python upload_csv_to_databricks.py <path_to_keystrokes.csv>
```

### Upload Specific File

```bash
python upload_csv_to_databricks.py ../data/akankshamattoo_20251115_183835/20251115_183835/keystrokes.csv
```

### Upload from Any Location

```bash
python upload_csv_to_databricks.py /Users/suryanshrawat/Documents/github/databricks_hack/data/akankshamattoo_20251115_183835/20251115_183835/keystrokes.csv
```

## What It Does

1. ✓ Connects to Databricks using credentials from `.env` or defaults
2. ✓ Creates `keystrokes` and `sessions` tables if they don't exist
3. ✓ Reads the CSV file
4. ✓ Inserts all keystroke data into Databricks
5. ✓ Calculates and inserts session statistics (WPM, total keystrokes, etc.)

## Requirements

- Python 3.9+
- databricks-sql-connector
- python-dotenv

These are already in your `requirements.txt` and installed in the venv.

## Configuration

The script uses the following Databricks credentials (from `.env` or defaults):

- `DATABRICKS_SERVER_HOSTNAME`: Your Databricks server
- `DATABRICKS_HTTP_PATH`: SQL warehouse HTTP path
- `DATABRICKS_ACCESS_TOKEN`: Your access token

## Output Example

```
======================================================================
Uploading CSV to Databricks
======================================================================

CSV File: ../data/user_20251115_183835/20251115_183835/keystrokes.csv
Session Timestamp: 20251115_183835

✓ Read 620 rows from CSV file
✓ Connected to Databricks successfully
✓ Keystrokes table ready
✓ Sessions table ready

  Inserted 100/620 rows...
  Inserted 200/620 rows...
  ...
✓ Successfully inserted 620 keystrokes
✓ Inserted session summary (WPM: 45.23, Keystrokes: 620)

======================================================================
✓ Upload completed successfully!
======================================================================

✓ Connection closed
```

## Troubleshooting

### Connection Errors
- Verify your Databricks credentials in `.env`
- Check network connectivity
- Ensure the access token is valid

### CSV Format Errors
- Ensure CSV has the correct headers: `PARTICIPANT_ID`, `TEST_SECTION_ID`, etc.
- Check for encoding issues (should be UTF-8)

### Import Errors
- Make sure you've activated the virtual environment: `source venv/bin/activate`
- Verify dependencies are installed: `pip install -r requirements.txt`

