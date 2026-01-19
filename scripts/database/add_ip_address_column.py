"""
Database migration script to add ip_address column to client table
Run this once to update your existing database schema
"""

import os
from sqlalchemy import create_engine, text

# Get database URL from environment or use default
DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql://postgres:EHtEAUYCdQmcklxsujwGlcYwihgVrWIV@centerbeam.proxy.rlwy.net:53769/railway')

def migrate():
    """Add ip_address column to client table"""
    engine = create_engine(DATABASE_URL)

    with engine.connect() as conn:
        # Check if column already exists
        check_query = text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name='client' AND column_name='ip_address'
        """)

        result = conn.execute(check_query)
        exists = result.fetchone()

        if exists:
            print("[OK] Column 'ip_address' already exists in 'client' table")
            return

        # Add the column
        print("Adding 'ip_address' column to 'client' table...")
        alter_query = text("""
            ALTER TABLE client
            ADD COLUMN ip_address VARCHAR(45);
        """)

        conn.execute(alter_query)
        conn.commit()

        # Create index for performance
        print("Creating index on 'ip_address' column...")
        index_query = text("""
            CREATE INDEX IF NOT EXISTS idx_client_ip_address
            ON client(ip_address);
        """)

        conn.execute(index_query)
        conn.commit()

        print("[OK] Migration completed successfully!")
        print("  - Added column: client.ip_address (VARCHAR(45))")
        print("  - Created index: idx_client_ip_address")

if __name__ == "__main__":
    try:
        migrate()
    except Exception as e:
        print(f"[ERROR] Migration failed: {e}")
        import traceback
        traceback.print_exc()
