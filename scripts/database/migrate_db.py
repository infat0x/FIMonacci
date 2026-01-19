#!/usr/bin/env python3
"""
Database Migration Script for FIMonacci
Adds new fields: entropy, high_entropy, is_hidden to FileHash and FileIntegrity tables
"""
import sys
import os

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

from dotenv import load_dotenv
load_dotenv()

from server import create_app, db
from sqlalchemy import text

app = create_app()

def migrate_database():
    """Add new columns to existing tables"""
    with app.app_context():
        try:
            print("[*] Starting database migration...")

            # Get database engine
            engine = db.engine

            # Check if we're using PostgreSQL or SQLite
            db_type = engine.dialect.name
            print(f"[*] Database type: {db_type}")

            # Migration for FileHash table
            print("\n[*] Migrating FileHash table...")
            try:
                # Add entropy column
                with engine.connect() as conn:
                    conn.execute(text("ALTER TABLE file_hash ADD COLUMN entropy FLOAT"))
                    conn.commit()
                print("  [+] Added column: entropy")
            except Exception as e:
                if "already exists" in str(e).lower() or "duplicate column" in str(e).lower():
                    print("  [i] Column 'entropy' already exists")
                else:
                    print(f"  [!] Error adding entropy: {e}")

            try:
                # Add high_entropy column
                with engine.connect() as conn:
                    if db_type == 'postgresql':
                        conn.execute(text("ALTER TABLE file_hash ADD COLUMN high_entropy BOOLEAN DEFAULT FALSE NOT NULL"))
                    else:  # SQLite
                        conn.execute(text("ALTER TABLE file_hash ADD COLUMN high_entropy BOOLEAN DEFAULT 0 NOT NULL"))
                    conn.commit()
                print("  [+] Added column: high_entropy")
            except Exception as e:
                if "already exists" in str(e).lower() or "duplicate column" in str(e).lower():
                    print("  [i] Column 'high_entropy' already exists")
                else:
                    print(f"  [!] Error adding high_entropy: {e}")

            try:
                # Add is_hidden column
                with engine.connect() as conn:
                    if db_type == 'postgresql':
                        conn.execute(text("ALTER TABLE file_hash ADD COLUMN is_hidden BOOLEAN DEFAULT FALSE NOT NULL"))
                    else:  # SQLite
                        conn.execute(text("ALTER TABLE file_hash ADD COLUMN is_hidden BOOLEAN DEFAULT 0 NOT NULL"))
                    conn.commit()
                print("  [+] Added column: is_hidden")
            except Exception as e:
                if "already exists" in str(e).lower() or "duplicate column" in str(e).lower():
                    print("  [i] Column 'is_hidden' already exists")
                else:
                    print(f"  [!] Error adding is_hidden: {e}")

            # Migration for FileIntegrity table
            print("\n[*] Migrating FileIntegrity table...")
            try:
                # Add entropy column
                with engine.connect() as conn:
                    conn.execute(text("ALTER TABLE file_integrity ADD COLUMN entropy FLOAT"))
                    conn.commit()
                print("  [+] Added column: entropy")
            except Exception as e:
                if "already exists" in str(e).lower() or "duplicate column" in str(e).lower():
                    print("  [i] Column 'entropy' already exists")
                else:
                    print(f"  [!] Error adding entropy: {e}")

            try:
                # Add high_entropy column
                with engine.connect() as conn:
                    if db_type == 'postgresql':
                        conn.execute(text("ALTER TABLE file_integrity ADD COLUMN high_entropy BOOLEAN DEFAULT FALSE NOT NULL"))
                    else:  # SQLite
                        conn.execute(text("ALTER TABLE file_integrity ADD COLUMN high_entropy BOOLEAN DEFAULT 0 NOT NULL"))
                    conn.commit()
                print("  [+] Added column: high_entropy")
            except Exception as e:
                if "already exists" in str(e).lower() or "duplicate column" in str(e).lower():
                    print("  [i] Column 'high_entropy' already exists")
                else:
                    print(f"  [!] Error adding high_entropy: {e}")

            try:
                # Add is_hidden column
                with engine.connect() as conn:
                    if db_type == 'postgresql':
                        conn.execute(text("ALTER TABLE file_integrity ADD COLUMN is_hidden BOOLEAN DEFAULT FALSE NOT NULL"))
                    else:  # SQLite
                        conn.execute(text("ALTER TABLE file_integrity ADD COLUMN is_hidden BOOLEAN DEFAULT 0 NOT NULL"))
                    conn.commit()
                print("  [+] Added column: is_hidden")
            except Exception as e:
                if "already exists" in str(e).lower() or "duplicate column" in str(e).lower():
                    print("  [i] Column 'is_hidden' already exists")
                else:
                    print(f"  [!] Error adding is_hidden: {e}")

            print("\n[SUCCESS] Migration completed successfully!")
            print("\nNew features added:")
            print("  [+] Entropy calculation - detects encrypted/compressed files")
            print("  [+] Hidden file monitoring - tracks hidden files")
            print("  [+] Content change tracking - monitors file content changes (excluding PII)")
            print("  [+] Enhanced PII detection - flags files containing sensitive data")

        except Exception as e:
            print(f"\n[ERROR] Migration failed: {e}")
            import traceback
            traceback.print_exc()
            return False

        return True

if __name__ == "__main__":
    print("=" * 60)
    print("FIMonacci Database Migration")
    print("=" * 60)
    print("\nThis will add the following columns:")
    print("  - entropy (FLOAT)")
    print("  - high_entropy (BOOLEAN)")
    print("  - is_hidden (BOOLEAN)")
    print("\nTo tables: file_hash, file_integrity")
    print("\n[!] Make sure you have a backup of your database before proceeding!")

    response = input("\nProceed with migration? (yes/no): ")
    if response.lower() in ['yes', 'y']:
        success = migrate_database()
        if success:
            print("\n[SUCCESS] Migration successful! You can now use the enhanced monitoring features.")
        else:
            print("\n[ERROR] Migration failed. Please check the errors above.")
    else:
        print("\n[CANCELLED] Migration cancelled.")
