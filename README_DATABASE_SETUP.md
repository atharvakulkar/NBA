# Database Setup Guide

This guide explains how to create the database tables for the Referral State Manager system.

## Tables Created

1. **referral_state_manager** - Main table for referral records
   - Stores referral ID, current state, attributes, mermaid script, and metadata
   - Primary key: `referral_id`

2. **referral_state_history** - Audit trail of state transitions
   - Tracks all state changes with timestamps and user information
   - Primary key: `id` (auto-increment)
   - Foreign key: `referral_id` → `referral_state_manager.referral_id`

## Prerequisites

- PostgreSQL database named `referrral_intel` (already created)
- Python 3.8+ (for Python script method)
- Database connection credentials

## Method 1: Using Python Script (Recommended)

### Step 1: Install Dependencies

```bash
cd NBA
pip install -r requirements.txt
```

### Step 2: Set Environment Variables

Choose one of these options:

**Option A: Set DATABASE_URL directly**
```bash
export DATABASE_URL="postgresql://username:password@localhost:5432/referrral_intel"
```

**Option B: Set individual variables**
```bash
export DB_HOST="localhost"
export DB_PORT="5432"
export DB_USER="postgres"
export DB_PASSWORD="your_password"
export DB_NAME="referrral_intel"
```

### Step 3: Run Setup Script

```bash
python setup_database.py
```

The script will:
- Test database connection
- Create both tables
- Verify tables were created successfully

### Expected Output

```
============================================================
Referral State Manager - Database Setup
============================================================

This script will create the following tables:
  - referral_state_manager
  - referral_state_history

⚠ Note: This will NOT modify or delete existing tables.
============================================================

Connecting to database: localhost:5432/referrral_intel
Testing database connection...
✓ Connected to PostgreSQL: PostgreSQL 15.x

Creating tables...
  - referral_state_manager
  - referral_state_history

✓ Tables created successfully!

Created tables:
  ✓ referral_state_manager (main referral records)
  ✓ referral_state_history (state transition audit trail)

Verifying tables...
✓ Verified: referral_state_history, referral_state_manager

============================================================
Setup complete!
============================================================
```

## Method 2: Using Raw SQL (Alternative)

### Step 1: Connect to Database

```bash
psql -h localhost -U postgres -d referrral_intel
```

### Step 2: Run SQL Script

```bash
psql -h localhost -U postgres -d referrral_intel -f create_tables.sql
```

Or copy and paste the contents of `create_tables.sql` into your psql session.

### Step 3: Verify Tables

```sql
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
AND table_name IN ('referral_state_manager', 'referral_state_history')
ORDER BY table_name;
```

You should see both tables listed.

## Safety Notes

✅ **SAFE**: This script only creates NEW tables
- Does NOT modify existing tables
- Does NOT delete any data
- Does NOT alter existing schemas
- Uses `CREATE TABLE IF NOT EXISTS` to prevent errors if tables already exist

## Troubleshooting

### Connection Error

If you get a connection error:
- Verify PostgreSQL is running
- Check host, port, username, and password
- Ensure database `referrral_intel` exists
- Check firewall settings

### Permission Error

If you get permission errors:
- Ensure your database user has CREATE TABLE permissions
- You may need to run as a superuser or database owner

### Tables Already Exist

If tables already exist:
- The script will skip creation (safe)
- If you need to recreate, drop tables first:
  ```sql
  DROP TABLE IF EXISTS referral_state_history CASCADE;
  DROP TABLE IF EXISTS referral_state_manager CASCADE;
  ```
  Then run the setup script again.

## Next Steps

After creating tables:
1. Update your application to use SQLAlchemy models from `db_models.py`
2. Replace in-memory `ReferralRepository` with database-backed implementation
3. Test API endpoints with database persistence

## Table Schema Details

### referral_state_manager

| Column | Type | Description |
|--------|------|-------------|
| referral_id | VARCHAR(255) | Primary key |
| state | VARCHAR(50) | Current state |
| attributes | JSONB | Flexible referral data |
| mermaid_script | TEXT | Mermaid diagram script |
| metadata | JSONB | Additional metadata |
| created_at | TIMESTAMP | Creation timestamp |
| updated_at | TIMESTAMP | Last update timestamp |
| created_by | VARCHAR(255) | Creator user ID |
| updated_by | VARCHAR(255) | Last updater user ID |

### referral_state_history

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL | Primary key (auto-increment) |
| referral_id | VARCHAR(255) | Foreign key to referral_state_manager |
| from_state | VARCHAR(50) | Previous state (NULL for initial) |
| to_state | VARCHAR(50) | New state |
| transitioned_at | TIMESTAMP | Transition timestamp |
| transitioned_by | VARCHAR(255) | User who triggered transition |
| reason | TEXT | Optional reason for change |
