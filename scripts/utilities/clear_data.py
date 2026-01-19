"""
Safe database data clearing script
Clears all data from tables while preserving table structure and admin users
"""
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

def clear_database_data():
    """
    Safely clear all monitoring data from database
    Preserves: User table (admin accounts), table structure, indexes
    Clears: FileIntegrity, FileHash, Client, MonitoredFolder, ApiToken
    """
    conn = None
    try:
        conn = psycopg2.connect(os.getenv('DATABASE_URL'))
        cur = conn.cursor()

        print("=" * 60)
        print("DATABASE DATA CLEARING SCRIPT")
        print("=" * 60)
        print("\nThis will clear all monitoring data while preserving:")
        print("  - Admin user accounts")
        print("  - Table structures")
        print("  - Indexes and constraints")
        print("\nData to be cleared:")
        print("  - All file integrity alerts")
        print("  - All file hashes")
        print("  - All client records")
        print("  - All monitored folder records")
        print("  - All API tokens")
        print("\n" + "=" * 60)

        # Get row counts before clearing
        print("\nCurrent data counts:")
        tables_to_clear = [
            ('file_integrity', 'File Integrity Alerts'),
            ('file_hash', 'File Hashes'),
            ('client', 'Clients'),
            ('monitored_folder', 'Monitored Folders'),
            ('api_token', 'API Tokens'),
        ]

        total_rows = 0
        for table_name, display_name in tables_to_clear:
            cur.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cur.fetchone()[0]
            total_rows += count
            print(f"  {display_name}: {count:,} rows")

        print(f"\nTotal rows to delete: {total_rows:,}")

        if total_rows == 0:
            print("\n[INFO] No data to clear. Database is already empty.")
            return

        # Confirm before proceeding
        print("\n" + "=" * 60)
        response = input("\nType 'YES' to proceed with data clearing: ")

        if response.strip().upper() != 'YES':
            print("\n[CANCELLED] Operation cancelled by user.")
            return

        print("\n" + "=" * 60)
        print("Clearing data...\n")

        # Disable foreign key checks temporarily for faster deletion
        cur.execute("SET session_replication_role = 'replica';")

        # Clear tables in order (respecting foreign key dependencies)
        # FileIntegrity and FileHash depend on Client, so clear them first

        print("[1/5] Clearing file integrity alerts...")
        cur.execute("TRUNCATE TABLE file_integrity CASCADE")
        print("      [OK] File integrity alerts cleared")

        print("[2/5] Clearing file hashes...")
        cur.execute("TRUNCATE TABLE file_hash CASCADE")
        print("      [OK] File hashes cleared")

        print("[3/5] Clearing monitored folders...")
        cur.execute("TRUNCATE TABLE monitored_folder CASCADE")
        print("      [OK] Monitored folders cleared")

        print("[4/5] Clearing API tokens...")
        cur.execute("TRUNCATE TABLE api_token CASCADE")
        print("      [OK] API tokens cleared")

        print("[5/5] Clearing client records...")
        cur.execute("TRUNCATE TABLE client CASCADE")
        print("      [OK] Client records cleared")

        # Re-enable foreign key checks
        cur.execute("SET session_replication_role = 'origin';")

        # Commit all changes
        conn.commit()

        print("\n" + "=" * 60)
        print("[SUCCESS] All data cleared successfully!")
        print("=" * 60)

        # Verify tables are empty
        print("\nVerifying data cleared:")
        for table_name, display_name in tables_to_clear:
            cur.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cur.fetchone()[0]
            print(f"  {display_name}: {count} rows")

        # Show preserved data
        print("\nPreserved data:")
        cur.execute("SELECT COUNT(*) FROM \"user\"")
        user_count = cur.fetchone()[0]
        print(f"  Admin Users: {user_count} accounts")

        print("\n" + "=" * 60)
        print("Database is ready for fresh monitoring data!")
        print("=" * 60)

    except psycopg2.Error as e:
        print(f"\n[ERROR] Database error: {e}")
        if conn:
            conn.rollback()
        return 1

    except KeyboardInterrupt:
        print("\n\n[CANCELLED] Operation cancelled by user.")
        if conn:
            conn.rollback()
        return 1

    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        if conn:
            conn.rollback()
        return 1

    finally:
        if conn:
            cur.close()
            conn.close()
            print("\nDatabase connection closed.")

    return 0


if __name__ == "__main__":
    import sys
    sys.exit(clear_database_data())
