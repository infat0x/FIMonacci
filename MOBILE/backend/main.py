"""
FIMonacci Backend - Real-Time Database Scanner with FastAPI
"""
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool
from pydantic import BaseModel
from typing import List, Optional, Dict
from datetime import datetime
import asyncio
import threading
from collections import deque
import time

# Database URL
DATABASE_URL = "postgresql://postgres:EHtEAUYCdQmcklxsujwGlcYwihgVrWIV@centerbeam.proxy.rlwy.net:53769/railway"

# Create FastAPI app
app = FastAPI(title="FIMonacci API", version="1.0.0")

# Enable CORS for Android app
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create engine with proper pooling and timeouts
engine = create_engine(
    DATABASE_URL,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=3600,
    connect_args={
        'connect_timeout': 10,
        'keepalives': 1,
        'keepalives_idle': 30,
        'keepalives_interval': 10,
        'keepalives_count': 5,
    }
)

# Real-time scanner state
scanner_state = {
    "is_scanning": False,
    "last_scan_time": None,
    "scan_interval": 2.0,  # Scan every 2 seconds
    "cached_alerts": [],
    "cached_stats": None,
    "new_alerts_count": 0,
    "total_scans": 0,
    "last_error": None
}

# WebSocket connections manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
    
    async def broadcast(self, message: dict):
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                disconnected.append(connection)
        
        for conn in disconnected:
            self.active_connections.remove(conn)

manager = ConnectionManager()


# Pydantic models for response
class Alert(BaseModel):
    id: int
    filename: str
    agent_name: str
    severity: str
    event_type: str
    timestamp: datetime
    old_hash: Optional[str] = None
    new_hash: Optional[str] = None
    file_path: str

    class Config:
        from_attributes = True


class Stats(BaseModel):
    modified: int
    deleted: int
    created: int
    accessed: int
    critical: int
    high: int
    medium: int
    low: int


class AlertsResponse(BaseModel):
    alerts: List[Alert]
    scan_time: Optional[datetime] = None
    new_alerts: int = 0

class ScannerStatus(BaseModel):
    is_scanning: bool
    last_scan_time: Optional[datetime]
    scan_interval: float
    total_scans: int
    new_alerts_count: int
    last_error: Optional[str] = None

class Agent(BaseModel):
    id: int
    hostname: str
    last_seen: Optional[datetime] = None
    alert_count: int = 0
    status: str = "offline"

class AgentFile(BaseModel):
    id: int
    filename: str
    file_path: str
    alert_type: str
    severity: str
    timestamp: datetime
    old_hash: Optional[str] = None
    new_hash: Optional[str] = None

class AgentDetailResponse(BaseModel):
    agent: Agent
    files: List[AgentFile]


def scan_database():
    """Scan database for new alerts and stats"""
    try:
        scanner_state["is_scanning"] = True
        scanner_state["last_error"] = None

        # Use timeout for connection
        with engine.connect().execution_options(timeout=5) as connection:
            # Get alerts
            query = text("""
                SELECT
                    fi.id,
                    COALESCE(NULLIF(SPLIT_PART(fi.path, '/', -1), ''), fi.path) as filename,
                    COALESCE(c.hostname, 'Unknown') as agent_name,
                    CASE
                        WHEN fi.ai_risk_score >= 0.8 THEN 'CRITICAL'
                        WHEN fi.ai_risk_score >= 0.6 THEN 'HIGH'
                        WHEN fi.ai_risk_score >= 0.4 THEN 'MEDIUM'
                        ELSE 'LOW'
                    END as severity,
                    COALESCE(fi.alert_type, 'MODIFY') as event_type,
                    fi.timestamp,
                    fi.initial_hash as old_hash,
                    fi.current_hash as new_hash,
                    fi.path as file_path
                FROM file_integrity fi
                LEFT JOIN client c ON fi.client_id = c.id
                WHERE fi.alert_type IS NOT NULL
                  AND fi.alert_type != 'client_connected'
                  AND fi.alert_type != 'client_disconnected'
                ORDER BY fi.timestamp DESC
                LIMIT 50
            """)
            
            result = connection.execute(query)
            rows = result.fetchall()
            
            alerts = []
            for row in rows:
                alerts.append({
                    "id": row[0],
                    "filename": row[1],
                    "agent_name": row[2] or "Unknown",
                    "severity": row[3],
                    "event_type": row[4],
                    "timestamp": row[5].isoformat() if row[5] else None,
                    "old_hash": row[6],
                    "new_hash": row[7],
                    "file_path": row[8]
                })
            
            # Get stats
            stats_query = text("""
                SELECT
                    COUNT(CASE WHEN alert_type LIKE '%modif%' OR alert_type LIKE '%write%' OR alert_type LIKE '%change%' THEN 1 END) as modified,
                    COUNT(CASE WHEN alert_type LIKE '%delet%' THEN 1 END) as deleted,
                    COUNT(CASE WHEN alert_type LIKE '%creat%' THEN 1 END) as created,
                    COUNT(CASE WHEN alert_type LIKE '%access%' OR alert_type LIKE '%read%' THEN 1 END) as accessed
                FROM file_integrity
                WHERE alert_type IS NOT NULL
                  AND alert_type != 'client_connected'
                  AND alert_type != 'client_disconnected'
            """)
            
            stats_result = connection.execute(stats_query)
            stats_row = stats_result.fetchone()
            
            stats = {
                "modified": stats_row[0] or 0,
                "deleted": stats_row[1] or 0,
                "created": stats_row[2] or 0,
                "accessed": stats_row[3] or 0
            }
            
            # Detect new alerts
            new_alerts = 0
            if scanner_state["cached_alerts"]:
                cached_ids = {a["id"] for a in scanner_state["cached_alerts"]}
                new_alerts = len([a for a in alerts if a["id"] not in cached_ids])
            else:
                new_alerts = len(alerts) if alerts else 0
            
            # Update cache
            scanner_state["cached_alerts"] = alerts
            scanner_state["cached_stats"] = stats
            scanner_state["new_alerts_count"] = new_alerts
            scanner_state["last_scan_time"] = datetime.now()
            scanner_state["total_scans"] += 1
            
            # Queue broadcasts for WebSocket (will be sent by async handler)
            # Always broadcast stats update
            scanner_state["pending_stats_broadcast"] = {
                "type": "stats_update",
                "stats": stats,
                "timestamp": scanner_state["last_scan_time"].isoformat()
            }
            
            # Broadcast new alerts if any
            if new_alerts > 0:
                # Store broadcast message in state for async handler
                scanner_state["pending_broadcast"] = {
                    "type": "new_alerts",
                    "count": new_alerts,
                    "timestamp": scanner_state["last_scan_time"].isoformat()
                }
            else:
                # Clear pending broadcast if no new alerts
                scanner_state["pending_broadcast"] = None
            
    except Exception as e:
        scanner_state["last_error"] = str(e)
        print(f"Scanner error: {e}")
    finally:
        scanner_state["is_scanning"] = False


def scanner_loop():
    """Background scanner loop"""
    while True:
        try:
            # Run scan with timeout protection
            import signal

            def timeout_handler(signum, frame):
                raise TimeoutError("Scan timeout")

            # Set timeout alarm (10 seconds max per scan)
            if hasattr(signal, 'SIGALRM'):
                signal.signal(signal.SIGALRM, timeout_handler)
                signal.alarm(10)

            try:
                scan_database()
            finally:
                if hasattr(signal, 'SIGALRM'):
                    signal.alarm(0)  # Cancel alarm

            time.sleep(scanner_state["scan_interval"])
        except TimeoutError:
            print("Scanner timeout - skipping this cycle")
            scanner_state["last_error"] = "Scan timeout"
            scanner_state["is_scanning"] = False
            time.sleep(scanner_state["scan_interval"])
        except Exception as e:
            print(f"Scanner loop error: {e}")
            scanner_state["last_error"] = str(e)
            scanner_state["is_scanning"] = False
            time.sleep(scanner_state["scan_interval"])


# Background task to handle broadcasts from scanner thread
async def broadcast_handler():
    """Handle broadcasts from scanner thread"""
    while True:
        try:
            # Always broadcast stats update if available
            if "pending_stats_broadcast" in scanner_state and scanner_state["pending_stats_broadcast"]:
                message = scanner_state["pending_stats_broadcast"]
                print(f"Broadcasting stats update: {message}")
                await manager.broadcast(message)
                scanner_state["pending_stats_broadcast"] = None
            
            # Broadcast new alerts if any
            if "pending_broadcast" in scanner_state and scanner_state["pending_broadcast"]:
                message = scanner_state["pending_broadcast"]
                print(f"Broadcasting new alerts: {message}")
                await manager.broadcast(message)
                scanner_state["pending_broadcast"] = None
            
            await asyncio.sleep(0.3)  # Check every 300ms for faster updates
        except Exception as e:
            print(f"Broadcast handler error: {e}")
            import traceback
            traceback.print_exc()
            await asyncio.sleep(1)

@app.on_event("startup")
async def startup_event():
    """Start background tasks on startup"""
    # Start scanner thread
    scanner_thread = threading.Thread(target=scanner_loop, daemon=True)
    scanner_thread.start()
    
    # Start broadcast handler
    asyncio.create_task(broadcast_handler())
    
    # Initial scan
    scan_database()

@app.get("/")
async def root():
    return {
        "message": "FIMonacci API - Real-Time Scanner",
        "status": "running",
        "scanner": {
            "is_scanning": scanner_state["is_scanning"],
            "last_scan": scanner_state["last_scan_time"].isoformat() if scanner_state["last_scan_time"] else None,
            "total_scans": scanner_state["total_scans"]
        }
    }


@app.get("/alerts", response_model=AlertsResponse)
async def get_alerts():
    """
    Get recent alerts - queries database directly for real-time data
    """
    try:
        # Query database directly for real-time data
        with engine.connect().execution_options(timeout=5) as connection:
            query = text("""
                SELECT
                    fi.id,
                    COALESCE(NULLIF(SPLIT_PART(fi.path, '/', -1), ''), fi.path) as filename,
                    COALESCE(c.hostname, 'Unknown') as agent_name,
                    CASE
                        WHEN fi.ai_risk_score >= 0.8 THEN 'CRITICAL'
                        WHEN fi.ai_risk_score >= 0.6 THEN 'HIGH'
                        WHEN fi.ai_risk_score >= 0.4 THEN 'MEDIUM'
                        ELSE 'LOW'
                    END as severity,
                    COALESCE(fi.alert_type, 'MODIFY') as event_type,
                    fi.timestamp,
                    fi.initial_hash as old_hash,
                    fi.current_hash as new_hash,
                    fi.path as file_path
                FROM file_integrity fi
                LEFT JOIN client c ON fi.client_id = c.id
                WHERE fi.alert_type IS NOT NULL
                  AND fi.alert_type != 'client_connected'
                  AND fi.alert_type != 'client_disconnected'
                ORDER BY fi.timestamp DESC
                LIMIT 50
            """)

            result = connection.execute(query)
            rows = result.fetchall()

            alerts = []
            for row in rows:
                alerts.append(Alert(
                    id=row[0],
                    filename=row[1],
                    agent_name=row[2] or "Unknown",
                    severity=row[3],
                    event_type=row[4],
                    timestamp=row[5],
                    old_hash=row[6],
                    new_hash=row[7],
                    file_path=row[8]
                ))

        # Detect new alerts compared to cache
        cached_ids = {a["id"] for a in scanner_state["cached_alerts"]}
        new_count = len([a for a in alerts if a.id not in cached_ids])

        return AlertsResponse(
            alerts=alerts,
            scan_time=datetime.now(),
            new_alerts=new_count
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting alerts: {str(e)}")


@app.get("/stats", response_model=Stats)
async def get_stats():
    """
    Get dashboard statistics - queries database directly for real-time data
    """
    try:
        # Query database directly for real-time data
        with engine.connect().execution_options(timeout=5) as connection:
            stats_query = text("""
                SELECT
                    COUNT(CASE WHEN alert_type LIKE '%modif%' OR alert_type LIKE '%write%' OR alert_type LIKE '%change%' THEN 1 END) as modified,
                    COUNT(CASE WHEN alert_type LIKE '%delet%' THEN 1 END) as deleted,
                    COUNT(CASE WHEN alert_type LIKE '%creat%' THEN 1 END) as created,
                    COUNT(CASE WHEN alert_type LIKE '%access%' OR alert_type LIKE '%read%' THEN 1 END) as accessed,
                    COUNT(CASE WHEN ai_risk_score >= 0.8 THEN 1 END) as critical,
                    COUNT(CASE WHEN ai_risk_score >= 0.6 AND ai_risk_score < 0.8 THEN 1 END) as high,
                    COUNT(CASE WHEN ai_risk_score >= 0.4 AND ai_risk_score < 0.6 THEN 1 END) as medium,
                    COUNT(CASE WHEN ai_risk_score < 0.4 THEN 1 END) as low
                FROM file_integrity
                WHERE alert_type IS NOT NULL
                  AND alert_type != 'client_connected'
                  AND alert_type != 'client_disconnected'
            """)

            stats_result = connection.execute(stats_query)
            stats_row = stats_result.fetchone()

            return Stats(
                modified=stats_row[0] or 0,
                deleted=stats_row[1] or 0,
                created=stats_row[2] or 0,
                accessed=stats_row[3] or 0,
                critical=stats_row[4] or 0,
                high=stats_row[5] or 0,
                medium=stats_row[6] or 0,
                low=stats_row[7] or 0
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting stats: {str(e)}")

@app.get("/scanner/status", response_model=ScannerStatus)
async def get_scanner_status():
    """
    Get real-time scanner status
    """
    return ScannerStatus(
        is_scanning=scanner_state["is_scanning"],
        last_scan_time=scanner_state["last_scan_time"],
        scan_interval=scanner_state["scan_interval"],
        total_scans=scanner_state["total_scans"],
        new_alerts_count=scanner_state["new_alerts_count"],
        last_error=scanner_state["last_error"]
    )

@app.post("/scanner/scan")
async def trigger_scan():
    """
    Manually trigger a database scan
    """
    scan_database()
    return {"message": "Scan triggered", "last_scan_time": scanner_state["last_scan_time"]}

@app.get("/agents")
async def get_agents():
    """
    Get all agents grouped by hostname with their alert counts
    """
    try:
        with engine.connect().execution_options(timeout=5) as connection:
            query = text("""
                SELECT
                    MIN(c.id) as id,
                    c.hostname,
                    MAX(c.last_seen) as last_seen,
                    COUNT(fi.id) as alert_count,
                    CASE
                        WHEN MAX(c.last_seen) > NOW() - INTERVAL '5 minutes' THEN 'online'
                        ELSE 'offline'
                    END as status
                FROM client c
                LEFT JOIN file_integrity fi ON c.id = fi.client_id
                    AND fi.alert_type IS NOT NULL
                    AND fi.alert_type != 'client_connected'
                    AND fi.alert_type != 'client_disconnected'
                GROUP BY c.hostname
                ORDER BY c.hostname
            """)

            result = connection.execute(query)
            rows = result.fetchall()

            agents = []
            for row in rows:
                agents.append({
                    "id": row[0],
                    "hostname": row[1],
                    "last_seen": row[2].isoformat() if row[2] else None,
                    "alert_count": row[3] or 0,
                    "status": row[4]
                })

            return {"agents": agents}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting agents: {str(e)}")

@app.get("/agents/{agent_id}", response_model=AgentDetailResponse)
async def get_agent_detail(agent_id: int):
    """
    Get agent details with all associated files from all clients with the same hostname
    """
    try:
        with engine.connect().execution_options(timeout=5) as connection:
            # First, get the hostname for this agent ID
            hostname_query = text("""
                SELECT hostname FROM client WHERE id = :agent_id
            """)
            hostname_result = connection.execute(hostname_query, {"agent_id": agent_id})
            hostname_row = hostname_result.fetchone()

            if not hostname_row:
                raise HTTPException(status_code=404, detail="Agent not found")

            hostname = hostname_row[0]

            # Get agent info grouped by hostname
            agent_query = text("""
                SELECT
                    MIN(c.id) as id,
                    c.hostname,
                    MAX(c.last_seen) as last_seen,
                    COUNT(fi.id) as alert_count,
                    CASE
                        WHEN MAX(c.last_seen) > NOW() - INTERVAL '5 minutes' THEN 'online'
                        ELSE 'offline'
                    END as status
                FROM client c
                LEFT JOIN file_integrity fi ON c.id = fi.client_id
                    AND fi.alert_type IS NOT NULL
                    AND fi.alert_type != 'client_connected'
                    AND fi.alert_type != 'client_disconnected'
                WHERE c.hostname = :hostname
                GROUP BY c.hostname
            """)

            agent_result = connection.execute(agent_query, {"hostname": hostname})
            agent_row = agent_result.fetchone()

            if not agent_row:
                raise HTTPException(status_code=404, detail="Agent not found")

            agent = Agent(
                id=agent_row[0],
                hostname=agent_row[1],
                last_seen=agent_row[2],
                alert_count=agent_row[3] or 0,
                status=agent_row[4]
            )

            # Get files for ALL clients with this hostname
            files_query = text("""
                SELECT
                    fi.id,
                    COALESCE(NULLIF(SPLIT_PART(fi.path, '/', -1), ''), fi.path) as filename,
                    fi.path as file_path,
                    COALESCE(fi.alert_type, 'MODIFY') as alert_type,
                    CASE
                        WHEN fi.ai_risk_score >= 0.8 THEN 'CRITICAL'
                        WHEN fi.ai_risk_score >= 0.6 THEN 'HIGH'
                        WHEN fi.ai_risk_score >= 0.4 THEN 'MEDIUM'
                        ELSE 'LOW'
                    END as severity,
                    fi.timestamp,
                    fi.initial_hash as old_hash,
                    fi.current_hash as new_hash
                FROM file_integrity fi
                JOIN client c ON fi.client_id = c.id
                WHERE c.hostname = :hostname
                  AND fi.alert_type IS NOT NULL
                  AND fi.alert_type != 'client_connected'
                  AND fi.alert_type != 'client_disconnected'
                ORDER BY fi.timestamp DESC
                LIMIT 100
            """)

            files_result = connection.execute(files_query, {"hostname": hostname})
            files_rows = files_result.fetchall()

            files = []
            for row in files_rows:
                files.append(AgentFile(
                    id=row[0],
                    filename=row[1],
                    file_path=row[2],
                    alert_type=row[3],
                    severity=row[4],
                    timestamp=row[5],
                    old_hash=row[6],
                    new_hash=row[7]
                ))

            return AgentDetailResponse(agent=agent, files=files)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting agent detail: {str(e)}")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time updates
    """
    await manager.connect(websocket)
    try:
        # Send initial state
        await websocket.send_json({
            "type": "connected",
            "scanner_status": {
                "is_scanning": scanner_state["is_scanning"],
                "last_scan_time": scanner_state["last_scan_time"].isoformat() if scanner_state["last_scan_time"] else None,
                "total_scans": scanner_state["total_scans"]
            }
        })
        
        # Keep connection alive and listen for messages
        while True:
            data = await websocket.receive_text()
            # Echo back or handle client messages
            await websocket.send_json({"type": "pong", "message": "Connection alive"})
    except WebSocketDisconnect:
        manager.disconnect(websocket)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=2828)

