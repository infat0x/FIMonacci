"""
Database optimization: Add missing indexes for performance
Run this once to speed up queries
"""
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

# Connect to PostgreSQL
conn = psycopg2.connect(os.getenv('DATABASE_URL'))
cur = conn.cursor()

print("Adding database indexes for performance optimization...")

try:
    # Add index on timestamp for ORDER BY performance
    print("Creating index on file_integrity.timestamp...")
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_file_integrity_timestamp
        ON file_integrity(timestamp DESC);
    """)

    # Composite index for alert_type + timestamp (very common query pattern)
    print("Creating composite index on file_integrity(alert_type, timestamp)...")
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_file_integrity_alert_timestamp
        ON file_integrity(alert_type, timestamp DESC);
    """)

    # Index for client connection queries
    print("Creating composite index on file_integrity(client_id, alert_type, timestamp)...")
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_file_integrity_client_alert_timestamp
        ON file_integrity(client_id, alert_type, timestamp DESC);
    """)

    conn.commit()
    print("\n[SUCCESS] All indexes created successfully!")
    print("\nYou can verify with:")
    print("  psql $DATABASE_URL -c \"\\d file_integrity\"")

except Exception as e:
    print(f"\n[ERROR] Error: {e}")
    conn.rollback()
finally:
    cur.close()
    conn.close()
