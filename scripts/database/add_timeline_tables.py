"""
Database migration script to add timeline analysis and Wazuh event cache tables
Run this once to update your existing database schema
"""

import os
from sqlalchemy import create_engine, text

# Get database URL from environment or use default
DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql://postgres:EHtEAUYCdQmcklxsujwGlcYwihgVrWIV@centerbeam.proxy.rlwy.net:53769/railway')

def migrate():
    """Add timeline_analysis and wazuh_event_cache tables"""
    engine = create_engine(DATABASE_URL)

    with engine.connect() as conn:
        print("[INFO] Creating timeline analysis tables...")

        # Create TimelineAnalysis table
        print("  - Creating timeline_analysis table...")
        timeline_query = text("""
            CREATE TABLE IF NOT EXISTS timeline_analysis (
                id SERIAL PRIMARY KEY,
                created_at TIMESTAMP NOT NULL DEFAULT (NOW() AT TIME ZONE 'utc'),
                alert_ids TEXT,
                client_id INTEGER REFERENCES client(id),
                start_time TIMESTAMP,
                end_time TIMESTAMP,
                fim_events_count INTEGER DEFAULT 0,
                wazuh_events_count INTEGER DEFAULT 0,
                analysis_result_json TEXT,
                overall_risk VARCHAR(20),
                confidence INTEGER,
                attack_type VARCHAR(255),
                mitre_techniques TEXT,
                status VARCHAR(50) DEFAULT 'completed' NOT NULL,
                error_message TEXT
            );
        """)
        conn.execute(timeline_query)
        conn.commit()

        # Create indexes for timeline_analysis
        print("  - Creating indexes for timeline_analysis...")
        indexes_query = text("""
            CREATE INDEX IF NOT EXISTS idx_timeline_analysis_created_at ON timeline_analysis(created_at);
            CREATE INDEX IF NOT EXISTS idx_timeline_analysis_client_id ON timeline_analysis(client_id);
            CREATE INDEX IF NOT EXISTS idx_timeline_analysis_overall_risk ON timeline_analysis(overall_risk);
        """)
        conn.execute(indexes_query)
        conn.commit()

        # Create WazuhEventCache table
        print("  - Creating wazuh_event_cache table...")
        wazuh_cache_query = text("""
            CREATE TABLE IF NOT EXISTS wazuh_event_cache (
                id SERIAL PRIMARY KEY,
                client_id INTEGER REFERENCES client(id),
                agent_ip VARCHAR(45),
                agent_id VARCHAR(100),
                query_start_time TIMESTAMP NOT NULL,
                query_end_time TIMESTAMP NOT NULL,
                events_json TEXT,
                event_count INTEGER DEFAULT 0,
                unique_event_count INTEGER DEFAULT 0,
                cached_at TIMESTAMP NOT NULL DEFAULT (NOW() AT TIME ZONE 'utc'),
                expires_at TIMESTAMP,
                query_hash VARCHAR(64)
            );
        """)
        conn.execute(wazuh_cache_query)
        conn.commit()

        # Create indexes for wazuh_event_cache
        print("  - Creating indexes for wazuh_event_cache...")
        wazuh_indexes_query = text("""
            CREATE INDEX IF NOT EXISTS idx_wazuh_cache_client_id ON wazuh_event_cache(client_id);
            CREATE INDEX IF NOT EXISTS idx_wazuh_cache_agent_ip ON wazuh_event_cache(agent_ip);
            CREATE INDEX IF NOT EXISTS idx_wazuh_cache_agent_id ON wazuh_event_cache(agent_id);
            CREATE INDEX IF NOT EXISTS idx_wazuh_cache_query_start ON wazuh_event_cache(query_start_time);
            CREATE INDEX IF NOT EXISTS idx_wazuh_cache_query_end ON wazuh_event_cache(query_end_time);
            CREATE INDEX IF NOT EXISTS idx_wazuh_cache_cached_at ON wazuh_event_cache(cached_at);
            CREATE INDEX IF NOT EXISTS idx_wazuh_cache_expires_at ON wazuh_event_cache(expires_at);
            CREATE INDEX IF NOT EXISTS idx_wazuh_cache_query_hash ON wazuh_event_cache(query_hash);
        """)
        conn.execute(wazuh_indexes_query)
        conn.commit()

        print("[OK] Migration completed successfully!")
        print("  - Created table: timeline_analysis")
        print("  - Created table: wazuh_event_cache")
        print("  - Created all required indexes")

if __name__ == "__main__":
    try:
        migrate()
    except Exception as e:
        print(f"[ERROR] Migration failed: {e}")
        import traceback
        traceback.print_exc()
