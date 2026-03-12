#!/usr/bin/env python3
"""
Database setup script for creating referral state manager tables.

This script creates the necessary tables in the PostgreSQL database.
It uses SQLAlchemy to create tables safely without affecting existing ones.

Usage:
    python setup_database.py

Environment variables:
    DATABASE_URL: PostgreSQL connection string
        Format: postgresql://user:password@host:port/database
        Example: postgresql://postgres:password@localhost:5432/referrral_intel

    Or set individual variables:
    - DB_HOST (default: localhost)
    - DB_PORT (default: 5432)
    - DB_USER (default: postgres)
    - DB_PASSWORD (required)
    - DB_NAME (default: referrral_intel)
"""

import os
import sys
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

# Add the NBA directory to the path so we can import db_models
sys.path.insert(0, str(Path(__file__).parent))

from referral_workflow.db_models import Base


def get_database_url() -> str:
    """Construct database URL from environment variables or DATABASE_URL."""
    # Check if DATABASE_URL is set directly
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return database_url

    # Otherwise, construct from individual components
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "5432")
    user = os.getenv("DB_USER", "postgres")
    password = os.getenv("DB_PASSWORD")
    database = os.getenv("DB_NAME", "referrral_intel")

    if not password:
        print("ERROR: DB_PASSWORD environment variable is required")
        print("\nPlease set one of:")
        print("  - DATABASE_URL=postgresql://user:password@host:port/database")
        print("  - DB_PASSWORD=your_password (and optionally DB_HOST, DB_PORT, DB_USER, DB_NAME)")
        sys.exit(1)

    return f"postgresql://{user}:{password}@{host}:{port}/{database}"


def create_tables() -> None:
    """Create all tables defined in db_models."""
    try:
        database_url = get_database_url()
        print(f"Connecting to database: {database_url.split('@')[1] if '@' in database_url else '***'}")

        # Create engine
        engine = create_engine(database_url, echo=False)

        # Test connection
        print("Testing database connection...")
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version();"))
            version = result.fetchone()[0]
            print(f"✓ Connected to PostgreSQL: {version.split(',')[0]}")

        # Create tables
        print("\nCreating tables...")
        print("  - referral_state_manager")
        print("  - referral_state_history")

        Base.metadata.create_all(engine, checkfirst=True)

        print("\n✓ Tables created successfully!")
        print("\nCreated tables:")
        print("  ✓ referral_state_manager (main referral records)")
        print("  ✓ referral_state_history (state transition audit trail)")

        # Verify tables exist
        print("\nVerifying tables...")
        with engine.connect() as conn:
            result = conn.execute(
                text(
                    """
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name IN ('referral_state_manager', 'referral_state_history')
                    ORDER BY table_name;
                    """
                )
            )
            tables = [row[0] for row in result]
            if len(tables) == 2:
                print(f"✓ Verified: {', '.join(tables)}")
            else:
                print(f"⚠ Warning: Expected 2 tables, found {len(tables)}")

    except SQLAlchemyError as e:
        print(f"\n✗ Database error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    print("=" * 60)
    print("Referral State Manager - Database Setup")
    print("=" * 60)
    print("\nThis script will create the following tables:")
    print("  - referral_state_manager")
    print("  - referral_state_history")
    print("\n⚠ Note: This will NOT modify or delete existing tables.")
    print("=" * 60)
    print()

    create_tables()

    print("\n" + "=" * 60)
    print("Setup complete!")
    print("=" * 60)
