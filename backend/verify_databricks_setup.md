# How to Verify Your Databricks Setup

## Issue: Connection Timeout

Your connection is timing out. Here's how to verify your setup:

## Step 1: Verify SQL Warehouse is Running

1. Log into your Databricks workspace (use your workspace URL from .env)
2. Go to **SQL Warehouses** (in the left sidebar)
3. Find your warehouse (ID from DATABRICKS_HTTP_PATH in your .env file)
4. **Make sure it's STARTED** (green status)
   - If it's stopped, click "Start" and wait for it to be ready
   - This can take 1-2 minutes

## Step 2: Verify HTTP Path

1. In SQL Warehouses, click on your warehouse
2. Go to the **Connection Details** tab
3. Look for **Serverless** or **Classic** connection string
4. Copy the **HTTP Path** - it should look like:
   - `/sql/1.0/warehouses/your-warehouse-id` (standard format)
   - Or `/sql/protocolv1/o/xxxxx/xxxx-xxxx-xxxx` (alternative format)

## Step 3: Verify Access Token

1. Go to **User Settings** (top right) > **Access Tokens**
2. Find your token (check last 4 chars to identify it)
3. Check if it's still valid (not expired)
4. If expired, create a new token:
   - Click "Generate new token"
   - Copy it immediately (you won't see it again)
   - Update your `.env` file with the new token

## Step 4: Check Token Permissions

Your token needs permissions to:
- Access SQL warehouses
- Query data
- Write to Delta tables

If you created the token recently, it should have these by default.

## Step 5: Test Connection Again

After verifying the above, run:
```bash
cd /Users/suryanshrawat/Documents/github/databricks_hack
source backend/venv/bin/activate
python -m backend.test_databricks_connection
```

## Common Issues:

### Warehouse is Stopped
- **Symptom**: Connection timeout
- **Fix**: Start the warehouse in Databricks UI

### Wrong HTTP Path
- **Symptom**: Connection timeout or 404 error
- **Fix**: Copy the correct HTTP path from warehouse connection details

### Token Expired
- **Symptom**: Authentication error (401)
- **Fix**: Generate new token and update `.env`

### Network/Firewall
- **Symptom**: Connection timeout (but basic connectivity works)
- **Fix**: Check if you're behind a corporate firewall/VPN that blocks Databricks

