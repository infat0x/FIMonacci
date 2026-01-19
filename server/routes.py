import os
import json
from pathlib import Path
from datetime import datetime, timezone, timedelta

from flask import Blueprint, render_template, request, jsonify, redirect, url_for, g, flash, send_file
from flask_login import login_required, current_user

from . import db
from .database import FileHash, MonitoredFolder, Client, FileIntegrity
from .monitor import calculate_md5, _record_alert, _normalize_datetime
from .auth import token_required

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    if current_user.is_authenticated:
        if current_user.is_admin:
            return redirect(url_for("admin.admin_panel"))
        else:
            # Regular users should use client script
            return """
            <html>
            <head><title>FIMonacci</title></head>
            <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
                <h1>FIMonacci File Integrity Monitor</h1>
                <p>This interface is for administrators only.</p>
                <p>To upload file hashes, please use the FIMonacci client script.</p>
                <p><a href="/auth/logout">Logout</a></p>
            </body>
            </html>
            """
    return redirect(url_for("auth.login"))


@main_bp.route("/login")
def login_redirect():
    """Redirect /login to /auth/login for backward compatibility"""
    return redirect(url_for("auth.login"))


@main_bp.route("/dashboard")
@login_required
def dashboard():
    # Dashboard is now admin-only, redirect to admin panel
    if not current_user.is_admin:
        flash("Access denied. Admin privileges required.", "error")
        return redirect(url_for("main.index"))
    return redirect(url_for("admin.admin_panel"))


@main_bp.route("/api/browse")
@login_required
def browse_filesystem():
    # Only admins can browse file system via UI
    if not current_user.is_admin:
        return jsonify({"error": "Admin access required"}), 403
    """Browse file system and return directory structure"""
    path = request.args.get("path", "/")
    
    try:
        path_obj = Path(path).resolve()
        
        # Security: prevent directory traversal
        if not path_obj.exists() or not path_obj.is_dir():
            return jsonify({"error": "Invalid path"}), 400
        
        items = []
        for item in sorted(path_obj.iterdir()):
            try:
                if item.is_dir():
                    items.append({
                        "name": item.name,
                        "path": str(item),
                        "type": "directory",
                        "size": None
                    })
                elif item.is_file():
                    try:
                        size = item.stat().st_size
                    except:
                        size = 0
                    items.append({
                        "name": item.name,
                        "path": str(item),
                        "type": "file",
                        "size": size
                    })
            except PermissionError:
                continue
        
        return jsonify({
            "current_path": str(path_obj),
            "parent_path": str(path_obj.parent) if path_obj.parent != path_obj else None,
            "items": items
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@main_bp.route("/api/upload", methods=["POST"])
@login_required
def upload_folders():
    """Calculate hashes for files in selected folders and store in database (Admin only)"""
    if not current_user.is_admin:
        return jsonify({"error": "Admin access required"}), 403
    data = request.get_json()
    folders = data.get("folders", [])
    
    if not folders:
        return jsonify({"error": "No folders selected"}), 400
    
    results = {
        "processed": 0,
        "errors": [],
        "success": []
    }
    
    for folder_path in folders:
        try:
            folder = Path(folder_path)
            if not folder.exists() or not folder.is_dir():
                results["errors"].append(f"{folder_path}: Folder not found")
                continue
            
            # Recursively process all files in folder
            # Use resolve() to get absolute paths and avoid duplicates
            processed_paths = set()
            for file_path in folder.rglob("*"):
                if file_path.is_file():
                    try:
                        # Get absolute resolved path to avoid duplicates
                        abs_path = str(file_path.resolve())
                        
                        # Skip if already processed in this batch
                        if abs_path in processed_paths:
                            continue
                        processed_paths.add(abs_path)
                        
                        # Verify file still exists and is readable
                        if not file_path.exists() or not file_path.is_file():
                            results["errors"].append(f"{abs_path}: File not found")
                            continue
                        
                        # Calculate hash
                        file_hash = calculate_md5(abs_path)
                        if not file_hash:
                            results["errors"].append(f"{abs_path}: Hash calculation failed (file could not be read)")
                            continue
                        
                        # Get file size
                        try:
                            file_size = file_path.stat().st_size
                        except OSError:
                            file_size = None
                        
                        # Note: This endpoint is deprecated - use /api/upload/hashes instead
                        # This was for admin UI upload, but now clients upload directly
                        # Skipping file processing as it requires client_id
                        results["errors"].append(f"{abs_path}: This endpoint is deprecated. Use client script instead.")
                    except Exception as e:
                        results["errors"].append(f"{file_path}: {str(e)}")
        except Exception as e:
            results["errors"].append(f"{folder_path}: {str(e)}")
    
    return jsonify(results)


@main_bp.route("/api/hashes")
@login_required
def get_hashes():
    """Get all file hashes (Admin only - returns all)"""
    if not current_user.is_admin:
        return jsonify({"error": "Admin access required"}), 403
    hashes = FileHash.query.order_by(FileHash.timestamp.desc()).limit(1000).all()
    return jsonify([h.as_dict() for h in hashes])


@main_bp.route("/api/client/register", methods=["POST"])
def register_client():
    """Register or update a client (no authentication required)"""
    data = request.get_json()
    client_id = data.get("client_id")
    hostname = data.get("hostname", "unknown")
    
    if not client_id:
        return jsonify({"error": "client_id is required"}), 400
    
    from .database import FileIntegrity

    # Get client IP address
    client_ip = request.remote_addr

    # Find or create client
    client = Client.query.filter_by(client_id=client_id).first()
    now = datetime.now(timezone.utc)

    if client:
        # Update existing client
        client.hostname = hostname
        client.ip_address = client_ip
        client.last_seen = now
        db.session.commit()
        
        # Check if there's a disconnect alert more recent than last connect alert
        # This means client was disconnected and is now reconnecting
        last_connect = FileIntegrity.query.filter(
            FileIntegrity.client_id == client.id,
            FileIntegrity.alert_type == "client_connected"
        ).order_by(FileIntegrity.timestamp.desc()).first()
        
        last_disconnect = FileIntegrity.query.filter(
            FileIntegrity.client_id == client.id,
            FileIntegrity.alert_type == "client_disconnected"
        ).order_by(FileIntegrity.timestamp.desc()).first()
        
        # Record connection if: no prior connect, OR last disconnect is more recent than last connect
        should_record_connect = False
        if not last_connect:
            should_record_connect = True
        elif last_disconnect:
            connect_ts = _normalize_datetime(last_connect.timestamp)
            disconnect_ts = _normalize_datetime(last_disconnect.timestamp)
            if disconnect_ts > connect_ts:
                should_record_connect = True
        
        if should_record_connect:
            connection_alert = FileIntegrity(
                client_id=client.id,
                path=client.hostname or "Unknown",
                initial_hash="connected",
                current_hash=None,
                alert_type="client_connected",
                timestamp=now
            )
            db.session.add(connection_alert)
        db.session.commit()
        
        return jsonify(client.as_dict()), 200
    else:
        # Create new client
        client = Client(
            client_id=client_id,
            hostname=hostname,
            ip_address=client_ip
        )
        db.session.add(client)
        db.session.commit()
        
        # Record initial connection event
        connection_alert = FileIntegrity(
            client_id=client.id,
            path=client.hostname or "Unknown",
            initial_hash="connected",
            current_hash=None,
            alert_type="client_connected",
            timestamp=now
        )
        db.session.add(connection_alert)
        db.session.commit()
        
        return jsonify(client.as_dict()), 201


@main_bp.route("/api/client/ping", methods=["POST"])
def client_ping():
    """
    Lightweight heartbeat to keep client last_seen fresh.
    Also records reconnection if client was previously disconnected.
    """
    from .database import FileIntegrity
    
    client_id = request.headers.get('X-Client-ID')
    hostname = request.headers.get('X-Hostname', 'unknown')
    if not client_id:
        return jsonify({"error": "X-Client-ID header is required"}), 400

    client = Client.query.filter_by(client_id=client_id).first()
    now = datetime.now(timezone.utc)

    if client:
        client.hostname = hostname
        client.last_seen = now
        db.session.commit()

        # Check if there's a disconnect alert more recent than last connect alert
        last_connect = FileIntegrity.query.filter(
            FileIntegrity.client_id == client.id,
            FileIntegrity.alert_type == "client_connected"
        ).order_by(FileIntegrity.timestamp.desc()).first()
        
        last_disconnect = FileIntegrity.query.filter(
            FileIntegrity.client_id == client.id,
            FileIntegrity.alert_type == "client_disconnected"
        ).order_by(FileIntegrity.timestamp.desc()).first()
        
        # Record connection if last disconnect is more recent than last connect
        should_record_connect = False
        if not last_connect:
            should_record_connect = True
        elif last_disconnect:
            connect_ts = _normalize_datetime(last_connect.timestamp)
            disconnect_ts = _normalize_datetime(last_disconnect.timestamp)
            if disconnect_ts > connect_ts:
                should_record_connect = True
        
        if should_record_connect:
            connection_alert = FileIntegrity(
                client_id=client.id,
                path=client.hostname or "Unknown",
                initial_hash="connected",
                current_hash=None,
                alert_type="client_connected",
                timestamp=now
            )
            db.session.add(connection_alert)
            db.session.commit()
    else:
        # Create client if ping arrives before explicit register
        client = Client(client_id=client_id, hostname=hostname, last_seen=now, first_seen=now)
        db.session.add(client)
        db.session.commit()
        connection_alert = FileIntegrity(
            client_id=client.id,
            path=client.hostname or "Unknown",
            initial_hash="connected",
            current_hash=None,
            alert_type="client_connected",
            timestamp=now
        )
        db.session.add(connection_alert)
        db.session.commit()

    return jsonify({"success": True, "client": client.as_dict()}), 200


@main_bp.route("/api/upload/hashes", methods=["POST"])
def upload_file_hashes():
    """Upload pre-calculated file hashes from client script (client_id based)"""
    # Get client_id from header
    client_id = request.headers.get('X-Client-ID')
    hostname = request.headers.get('X-Hostname', 'unknown')
    
    if not client_id:
        return jsonify({"error": "X-Client-ID header is required"}), 400
    
    # Find or create client
    client = Client.query.filter_by(client_id=client_id).first()
    if not client:
        client = Client(client_id=client_id, hostname=hostname)
        db.session.add(client)
        db.session.commit()
    else:
        # Update hostname and last_seen
        client.hostname = hostname
        client.last_seen = datetime.now(timezone.utc)
        db.session.commit()
    
    data = request.get_json()
    files = data.get("files", [])
    
    if not files:
        return jsonify({"error": "No files provided"}), 400
    
    results = {
        "processed": 0,
        "errors": [],
        "success": []
    }
    
    for file_data in files:
        try:
            file_path = file_data.get("path")
            file_hash = file_data.get("hash_md5")
            file_size = file_data.get("file_size")
            
            if not file_path or not file_hash:
                results["errors"].append(f"Missing path or hash for file")
                continue
            
            # Store path as-is from client (don't resolve on server side)
            # Client sends absolute paths, so we just normalize separators
            abs_path = file_path.replace('\\', '/')  # Normalize Windows backslashes to forward slashes
            
            # Extract metadata from file_data
            metadata = file_data.get("metadata", {})
            process_info = metadata.get("process_info", {}) if isinstance(metadata, dict) else {}
            
            # Parse timestamps if provided
            created_at = None
            modified_at = None
            accessed_at = None
            if isinstance(metadata, dict):
                if metadata.get("created_at"):
                    try:
                        created_at = datetime.fromisoformat(metadata["created_at"].replace('Z', '+00:00'))
                    except:
                        pass
                if metadata.get("modified_at"):
                    try:
                        modified_at = datetime.fromisoformat(metadata["modified_at"].replace('Z', '+00:00'))
                    except:
                        pass
                if metadata.get("accessed_at"):
                    try:
                        accessed_at = datetime.fromisoformat(metadata["accessed_at"].replace('Z', '+00:00'))
                    except:
                        pass
            
            # Check if hash already exists for this client and path
            existing = FileHash.query.filter_by(
                client_id=client.id,
                path=abs_path
            ).first()
            
            # Check if this is an event-triggered upload (has event_type in request)
            event_type = file_data.get("event_type")  # created, modified, deleted, hash_mismatch
            
            is_new_file = False
            if existing:
                # Update existing record - check if hash changed
                old_hash = existing.hash_md5
                existing.hash_md5 = file_hash
                if file_size is not None:
                    existing.file_size = file_size
                existing.timestamp = datetime.now(timezone.utc)
                
                # Update metadata fields
                if isinstance(metadata, dict):
                    existing.owner_user = metadata.get("owner_user") or existing.owner_user
                    existing.owner_user_id = metadata.get("owner_user_id") or metadata.get("owner_sid") or existing.owner_user_id
                    existing.owner_group = metadata.get("owner_group") or existing.owner_group
                    existing.owner_group_id = metadata.get("owner_group_id") or existing.owner_group_id
                    existing.permissions = metadata.get("permissions") or existing.permissions
                    existing.created_at = created_at or existing.created_at
                    existing.modified_at = modified_at or existing.modified_at
                    existing.accessed_at = accessed_at or existing.accessed_at
                    existing.magic_bytes = metadata.get("magic_bytes") or existing.magic_bytes
                    existing.detected_file_type = metadata.get("detected_file_type") or existing.detected_file_type
                    existing.file_extension = metadata.get("file_extension") or existing.file_extension
                    existing.magic_byte_mismatch = metadata.get("magic_byte_mismatch", False) or existing.magic_byte_mismatch
                    existing.process_name = process_info.get("process_name") or existing.process_name
                    existing.process_id = process_info.get("process_id") or existing.process_id
                    existing.process_user = process_info.get("process_user") or existing.process_user
                    # New fields
                    if metadata.get("entropy") is not None:
                        existing.entropy = metadata.get("entropy")
                    existing.high_entropy = metadata.get("high_entropy", False)
                    existing.is_hidden = metadata.get("is_hidden", False)
                    # Store full metadata as JSON
                    existing.metadata_json = json.dumps(metadata)
                
                # If hash changed and event_type is provided, use it; otherwise default to hash_mismatch
                if old_hash != file_hash:
                    alert_type = event_type if event_type else "hash_mismatch"
                    _record_alert(abs_path, old_hash, file_hash, alert_type, client_id=client.id, metadata=metadata)
            else:
                # Create new record
                is_new_file = True
                file_hash_record = FileHash(
                    client_id=client.id,
                    path=abs_path,
                    hash_md5=file_hash,
                    file_size=file_size,
                    timestamp=datetime.now(timezone.utc),  # Explicit timestamp
                    owner_user=metadata.get("owner_user") if isinstance(metadata, dict) else None,
                    owner_user_id=metadata.get("owner_user_id") or metadata.get("owner_sid") if isinstance(metadata, dict) else None,
                    owner_group=metadata.get("owner_group") if isinstance(metadata, dict) else None,
                    owner_group_id=metadata.get("owner_group_id") if isinstance(metadata, dict) else None,
                    permissions=metadata.get("permissions") if isinstance(metadata, dict) else None,
                    created_at=created_at,
                    modified_at=modified_at,
                    accessed_at=accessed_at,
                    magic_bytes=metadata.get("magic_bytes") if isinstance(metadata, dict) else None,
                    detected_file_type=metadata.get("detected_file_type") if isinstance(metadata, dict) else None,
                    file_extension=metadata.get("file_extension") if isinstance(metadata, dict) else None,
                    magic_byte_mismatch=metadata.get("magic_byte_mismatch", False) if isinstance(metadata, dict) else False,
                    process_name=process_info.get("process_name") if isinstance(process_info, dict) else None,
                    process_id=process_info.get("process_id") if isinstance(process_info, dict) else None,
                    process_user=process_info.get("process_user") if isinstance(process_info, dict) else None,
                    # New fields
                    entropy=metadata.get("entropy") if isinstance(metadata, dict) else None,
                    high_entropy=metadata.get("high_entropy", False) if isinstance(metadata, dict) else False,
                    is_hidden=metadata.get("is_hidden", False) if isinstance(metadata, dict) else False,
                    metadata_json=json.dumps(metadata) if isinstance(metadata, dict) else None
                )
                db.session.add(file_hash_record)
                
                # If event_type is "created", record the alert
                if event_type == "created":
                    _record_alert(abs_path, None, file_hash, "created", client_id=client.id, metadata=metadata)
            
            # Commit after each file to avoid transaction rollback issues
            db.session.commit()
            
            results["processed"] += 1
            results["success"].append(abs_path)
            
        except Exception as e:
            # Rollback on error to allow next file to be processed
            db.session.rollback()
            results["errors"].append(f"{file_data.get('path', 'unknown')}: {str(e)}")
    
    return jsonify(results)


@main_bp.route("/api/upload/event", methods=["POST"])
def upload_file_event():
    """Upload file event alert from client (for deleted files and other events)"""
    # Get client_id from header (same as upload/hashes endpoint)
    client_id = request.headers.get('X-Client-ID')
    hostname = request.headers.get('X-Hostname', 'unknown')
    
    if not client_id:
        return jsonify({"error": "X-Client-ID header is required"}), 400
    
    # Find or create client
    client = Client.query.filter_by(client_id=client_id).first()
    if not client:
        client = Client(client_id=client_id, hostname=hostname)
        db.session.add(client)
        db.session.commit()
    else:
        # Update hostname and last_seen
        client.hostname = hostname
        client.last_seen = datetime.now(timezone.utc)
        db.session.commit()
    
    data = request.get_json()
    filepath = data.get("path")
    initial_hash = data.get("initial_hash")
    current_hash = data.get("current_hash")
    alert_type = data.get("alert_type")
    metadata = data.get("metadata", {})
    
    if not filepath or not alert_type:
        return jsonify({"error": "path and alert_type are required"}), 400
    
    # Normalize path
    abs_path = filepath.replace('\\', '/')
    
    # Record the alert with metadata
    _record_alert(abs_path, initial_hash, current_hash, alert_type, client_id=client.id, metadata=metadata)
    
    # For deleted files, also remove from FileHash if it exists
    if alert_type == "deleted":
        # Try multiple path formats
        file_hash = FileHash.query.filter_by(
            client_id=client.id
        ).filter(
            (FileHash.path == abs_path) |
            (FileHash.path == abs_path.replace('/', '\\')) |
            (FileHash.path == filepath.replace('\\', '/'))
        ).first()
        if file_hash:
            db.session.delete(file_hash)
            db.session.commit()
    
    return jsonify({"success": True, "message": "Event recorded"})


@main_bp.route("/api/monitor/start", methods=["POST"])
@login_required
def start_monitoring_folders():
    """Start active scan for selected folders (Admin only)"""
    if not current_user.is_admin:
        return jsonify({"error": "Admin access required"}), 403
    data = request.get_json()
    folders = data.get("folders", [])
    
    if not folders:
        return jsonify({"error": "No folders selected"}), 400
    
    activated = []
    for folder_path in folders:
        try:
            folder = Path(folder_path)
            abs_folder_path = str(folder.resolve())
            
            if not folder.exists() or not folder.is_dir():
                continue
            
            # Note: Monitoring folders requires client_id, not user_id
            # This endpoint is deprecated - folders should be monitored via client uploads
            # Keeping for backward compatibility but it won't work properly
            pass
        except Exception as e:
            continue
    
    return jsonify({
        "success": True,
        "activated": len(activated),
        "folders": activated
    })


@main_bp.route("/api/monitor/stop", methods=["POST"])
@login_required
def stop_monitoring_folders():
    """Stop active scan for selected folders (Admin only)"""
    if not current_user.is_admin:
        return jsonify({"error": "Admin access required"}), 403
    data = request.get_json()
    folders = data.get("folders", [])
    
    if folders:
        # Deactivate specific folders
        for folder_path in folders:
            abs_folder_path = str(Path(folder_path).resolve())
            # Deactivate by folder path (works for all clients with that path)
            MonitoredFolder.query.filter_by(
                folder_path=abs_folder_path
            ).update({"is_active": False})
    else:
        # Deactivate all folders (admin can deactivate all)
        MonitoredFolder.query.update({"is_active": False})
    
    db.session.commit()
    return jsonify({"success": True})


@main_bp.route("/api/status")
def get_status():
    """Simple health check endpoint for client connection testing (no auth required)"""
    return jsonify({
        "status": "ok",
        "service": "FIMonacci",
        "version": "1.0"
    })


@main_bp.route("/api/monitor/status")
@login_required
def get_monitoring_status():
    """Get active monitoring folders (Admin only - returns all)"""
    if not current_user.is_admin:
        return jsonify({"error": "Admin access required"}), 403
    active_folders = MonitoredFolder.query.filter_by(is_active=True).all()
    
    return jsonify([f.as_dict() for f in active_folders])


@main_bp.route("/api/alerts")
@login_required
def get_alerts():
    """Get all alerts for current user (Admin only)"""
    import time
    start_time = time.time()

    if not current_user.is_admin:
        return jsonify({"error": "Admin access required"}), 403
    from .database import FileIntegrity, Client
    from datetime import timedelta
    from .monitor import _check_and_record_disconnections

    # Skip disconnection check on every alerts request - it's too slow
    # It's still checked periodically by the monitoring thread
    # t1 = time.time()
    # _check_and_record_disconnections()
    # print(f"[TIMER] _check_and_record_disconnections: {(time.time() - t1)*1000:.2f}ms")

    now = datetime.now(timezone.utc)
    # Keep threshold consistent with monitor and frontend (10 seconds)
    disconnect_threshold = timedelta(seconds=10)

    # Get file integrity alerts (including client connection/disconnection events)
    t2 = time.time()
    alerts = FileIntegrity.query.filter(
        FileIntegrity.alert_type != "baseline"
    ).order_by(FileIntegrity.timestamp.desc()).limit(500).all()
    print(f"[TIMER] Query alerts from DB: {(time.time() - t2)*1000:.2f}ms, count: {len(alerts)}")
    
    # Filter out rapid create/delete cycles (already suppressed in _record_alert, but filter here too for safety)
    t3 = time.time()
    alert_dicts = []
    seen_rapid_cycles = set()

    for alert in alerts:
        alert_dict = alert.as_dict()

        # Check if this is part of a rapid cycle we've already seen
        alert_key = f"{alert.client_id}_{alert.path}"
        if alert_key in seen_rapid_cycles:
            continue

        # Check for rapid cycles in the results
        if alert.alert_type == "created":
            # Look for matching delete in results
            matching_delete = next(
                (a for a in alerts if
                 a.client_id == alert.client_id and
                 a.path == alert.path and
                 a.alert_type == "deleted" and
                 _normalize_datetime(a.timestamp) > _normalize_datetime(alert.timestamp) and
                 (_normalize_datetime(a.timestamp) - _normalize_datetime(alert.timestamp)).total_seconds() < 15),
                None
            )
            if matching_delete:
                seen_rapid_cycles.add(alert_key)
                continue  # Skip both create and delete

        alert_dicts.append(alert_dict)
    print(f"[TIMER] Process alerts (as_dict + filtering): {(time.time() - t3)*1000:.2f}ms")
    
    # Also add current connection status for active clients
    # (Disconnection events are now stored in FileIntegrity, but we still show current connections)
    recent_clients = Client.query.filter(
        Client.last_seen >= now - timedelta(hours=1)
    ).order_by(Client.last_seen.desc()).limit(20).all()
    
    # Track which clients we've already added from FileIntegrity alerts
    clients_in_alerts = {alert.client_id for alert in alerts if alert.client_id and alert.alert_type in ["client_connected", "client_disconnected"]}
    
    # Add connection events for currently connected clients (if not already in alerts)
    for client in recent_clients:
        if not client.last_seen:
            continue
        
        # Skip if we already have a recent connection/disconnection event for this client
        if client.id in clients_in_alerts:
            continue
        
        # Normalize client.last_seen to timezone-aware for comparison
        last_seen_normalized = _normalize_datetime(client.last_seen)
        time_since_last_seen = now - last_seen_normalized
        is_connected = time_since_last_seen < disconnect_threshold
        
        if is_connected:
            # Client is currently connected - show connection event
            alert_dicts.append({
                "id": f"client_connected_{client.id}",
                "path": client.hostname or "Unknown",  # Just hostname, event type shown separately
                "alert_type": "client_connected",
                "timestamp": client.last_seen.isoformat(),
                "client_hostname": client.hostname,
                "client_id_str": client.client_id,
                "initial_hash": None,
                "current_hash": None,
            })
    
    # Sort by timestamp (newest first)
    t4 = time.time()
    alert_dicts.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
    print(f"[TIMER] Sort alerts: {(time.time() - t4)*1000:.2f}ms")

    print(f"[TIMER] TOTAL get_alerts: {(time.time() - start_time)*1000:.2f}ms")
    return jsonify(alert_dicts[:500])  # Limit to 500 total


@main_bp.route("/api/timeline")
@login_required
def get_attack_timeline():
    """Get attack timeline (Admin only)"""
    if not current_user.is_admin:
        return jsonify({"error": "Admin access required"}), 403
    
    from .attack_timeline import timeline_generator
    from datetime import timedelta
    
    client_id = request.args.get('client_id', type=int)
    hours = request.args.get('hours', 24, type=int)
    
    if client_id:
        timeline = timeline_generator.get_timeline_for_client(client_id, hours)
    else:
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(hours=hours)
        timeline = timeline_generator.generate_timeline(start_time=start_time, end_time=end_time)
    
    return jsonify(timeline)


@main_bp.route("/api/ai/analyze/<int:alert_id>", methods=["POST"])
@login_required
def analyze_alert_with_ai(alert_id):
    """Trigger AI analysis for a specific alert (Admin only)"""
    if not current_user.is_admin:
        return jsonify({"error": "Admin access required"}), 403
    
    from .ai_analysis import ai_analysis_engine
    from .database import FileIntegrity
    
    alert = FileIntegrity.query.get_or_404(alert_id)
    result = ai_analysis_engine.analyze_alert(alert)
    
    if result:
        return jsonify({
            "success": True,
            "analysis": alert.ai_analysis,
            "risk_score": alert.ai_risk_score,
            "timestamp": alert.ai_analysis_timestamp.isoformat() if alert.ai_analysis_timestamp else None
        })
    else:
        return jsonify({"success": False, "error": "AI analysis failed or not configured"}), 500


@main_bp.route("/api/wazuh/sync/<int:alert_id>", methods=["POST"])
@login_required
def sync_alert_to_wazuh(alert_id):
    """Sync alert to Wazuh (Admin only)"""
    if not current_user.is_admin:
        return jsonify({"error": "Admin access required"}), 403
    
    from .wazuh_integration import wazuh_integration
    from .database import FileIntegrity
    
    alert = FileIntegrity.query.get_or_404(alert_id)
    alert_id = wazuh_integration.send_alert_to_wazuh(alert)
    
    if alert_id:
        return jsonify({
            "success": True,
            "wazuh_alert_id": alert_id,
            "synced": alert.wazuh_synced
        })
    else:
        return jsonify({"success": False, "error": "Wazuh sync failed or not configured"}), 500


@main_bp.route("/api/alert/<int:alert_id>", methods=["GET"])
def get_alert_detail(alert_id):
    """
    Get detailed information about a specific alert
    Includes all extended metadata, actor info, process tree, logs, PII status
    """
    alert = FileIntegrity.query.get_or_404(alert_id)
    
    # Get basic alert data with all fields
    alert_data = alert.as_dict()
    
    # Add computed severity
    alert_data['severity'] = alert._compute_severity() if hasattr(alert, '_compute_severity') else 'medium'
    
    # Get client information
    if alert.client:
        alert_data['agent'] = {
            'id': alert.client.id,
            'client_id': alert.client.client_id,
            'hostname': alert.client.hostname,
            'first_seen': alert.client.first_seen.isoformat() if alert.client.first_seen else None,
            'last_seen': alert.client.last_seen.isoformat() if alert.client.last_seen else None,
        }
        
        # Get agent's recent alerts
        recent_alerts = FileIntegrity.query.filter(
            FileIntegrity.client_id == alert.client_id,
            FileIntegrity.id != alert_id,
            ~FileIntegrity.alert_type.in_(['client_connected', 'client_disconnected', 'baseline'])
        ).order_by(FileIntegrity.timestamp.desc()).limit(10).all()
        
        alert_data['agent_recent_alerts'] = [a.as_dict() for a in recent_alerts]
    
    # Get related alerts for the same file path
    related_alerts = FileIntegrity.query.filter(
        FileIntegrity.path == alert.path,
        FileIntegrity.id != alert_id,
        ~FileIntegrity.alert_type.in_(['baseline'])
    ).order_by(FileIntegrity.timestamp.desc()).limit(20).all()
    
    alert_data['related_alerts'] = [a.as_dict() for a in related_alerts]
    
    # Calculate file history summary
    alert_data['file_history'] = {
        'total_events': len(related_alerts) + 1,
        'modifications': sum(1 for a in related_alerts if a.alert_type in ['hash_mismatch', 'modified']),
        'creations': sum(1 for a in related_alerts if a.alert_type == 'created'),
        'deletions': sum(1 for a in related_alerts if a.alert_type in ['deleted', 'missing']),
    }
    
    # Determine content analysis availability
    if alert.is_pii:
        alert_data['content_analysis'] = {
            'available': False,
            'reason': 'PII detected - content not stored',
            'pii_types': alert.pii_types.split(',') if alert.pii_types else []
        }
    else:
        alert_data['content_analysis'] = {
            'available': True,
            'hash_changed': alert.initial_hash != alert.current_hash if alert.initial_hash and alert.current_hash else None,
        }
    
    return jsonify(alert_data)


@main_bp.route("/api/alert/<int:alert_id>/context", methods=["GET"])
def get_alert_context(alert_id):
    """
    Get additional context for an alert - timeline of events around this alert
    """
    alert = FileIntegrity.query.get_or_404(alert_id)
    
    # Get events within 1 hour before and after this alert
    time_window = timedelta(hours=1)
    alert_time = _normalize_datetime(alert.timestamp)
    start_time = alert_time - time_window
    end_time = alert_time + time_window
    
    # Get events from the same client around this time
    context_events = FileIntegrity.query.filter(
        FileIntegrity.client_id == alert.client_id,
        FileIntegrity.timestamp >= start_time,
        FileIntegrity.timestamp <= end_time,
        ~FileIntegrity.alert_type.in_(['baseline'])
    ).order_by(FileIntegrity.timestamp.asc()).limit(50).all()
    
    return jsonify({
        'alert_id': alert_id,
        'time_window': {
            'start': start_time.isoformat(),
            'end': end_time.isoformat()
        },
        'context_events': [e.as_dict() for e in context_events]
    })


# ═══════════════════════════════════════════════════════════════
# Timeline Analysis & AI-Powered Incident Investigation
# ═══════════════════════════════════════════════════════════════

@main_bp.route("/api/timeline/analyze", methods=["POST"])
@login_required
def analyze_timeline():
    """
    Analyze FIM alerts + Wazuh events with AI
    Request body:
    {
        "alert_ids": [1, 2, 3],  # List of alert IDs to analyze
        "start_time": "2025-12-17T10:00:00",  # Optional, auto-detected from alerts
        "end_time": "2025-12-17T12:00:00",    # Optional, auto-detected from alerts
        "include_wazuh": true,
        "agent_ip": "10.249.162.12",  # Optional, auto-detected from alerts
        "wazuh_events": [...]  # Optional, pass pre-fetched Wazuh events
    }
    """
    if not current_user.is_admin:
        return jsonify({"error": "Admin access required"}), 403

    data = request.get_json()
    alert_ids = data.get('alert_ids', [])
    include_wazuh = data.get('include_wazuh', False)
    agent_ip = data.get('agent_ip')
    wazuh_events = data.get('wazuh_events')

    if not alert_ids:
        return jsonify({"error": "alert_ids required"}), 400

    try:
        from .database import FileIntegrity, Client, TimelineAnalysis, WazuhEventCache
        from .ai_timeline_analysis import AITimelineAnalyzer
        import hashlib

        # Get FIM alerts
        alerts = FileIntegrity.query.filter(FileIntegrity.id.in_(alert_ids)).all()
        if not alerts:
            return jsonify({"error": "No alerts found with provided IDs"}), 404

        # Convert to dict format for AI
        fim_data = [alert.as_dict() for alert in alerts]

        # Determine time range and client
        timestamps = [alert.timestamp for alert in alerts if alert.timestamp]
        if timestamps:
            start_time = data.get('start_time') or min(timestamps).isoformat()
            end_time = data.get('end_time') or max(timestamps).isoformat()
        else:
            return jsonify({"error": "Alerts have no timestamps"}), 400

        # Determine client and agent IP
        client_id = alerts[0].client_id if alerts else None
        if not agent_ip and client_id:
            client = Client.query.get(client_id)
            if client:
                agent_ip = client.ip_address

        # Get or fetch Wazuh events
        wazuh_data = []
        if include_wazuh and (wazuh_events or agent_ip):
            if wazuh_events:
                # Use provided Wazuh events
                wazuh_data = wazuh_events
            elif agent_ip:
                # Check cache first
                query_hash = hashlib.md5(f"{agent_ip}:{start_time}:{end_time}".encode()).hexdigest()
                cached = WazuhEventCache.query.filter_by(query_hash=query_hash).first()

                if cached and cached.events_json:
                    print(f"[TIMELINE] Using cached Wazuh events (cache ID: {cached.id})")
                    wazuh_data = json.loads(cached.events_json)
                else:
                    # Fetch from Wazuh
                    print(f"[TIMELINE] Fetching fresh Wazuh events for {agent_ip}")
                    from .wazuh_integration import wazuh_integration
                    result = wazuh_integration.query_events_by_agent(agent_ip, start_time, end_time)

                    if result.get('success'):
                        wazuh_data = result.get('events', [])

                        # Cache the results
                        cache_entry = WazuhEventCache(
                            client_id=client_id,
                            agent_ip=agent_ip,
                            agent_id=result.get('agent_id'),
                            query_start_time=datetime.fromisoformat(start_time.replace('Z', '+00:00')),
                            query_end_time=datetime.fromisoformat(end_time.replace('Z', '+00:00')),
                            events_json=json.dumps(wazuh_data, default=str),
                            event_count=result.get('total_events', 0),
                            unique_event_count=result.get('unique_events', 0),
                            query_hash=query_hash,
                            expires_at=datetime.now(timezone.utc) + timedelta(hours=24)
                        )
                        db.session.add(cache_entry)
                        db.session.commit()
                        print(f"[TIMELINE] Cached Wazuh events (cache ID: {cache_entry.id})")

        # Run AI analysis
        print(f"[TIMELINE] Starting AI analysis: {len(fim_data)} FIM events, {len(wazuh_data)} Wazuh events")
        analyzer = AITimelineAnalyzer()
        analysis_result = analyzer.analyze_timeline(
            fim_data=fim_data,
            wazuh_data=wazuh_data if wazuh_data else None
        )

        # Store analysis in database
        summary = analysis_result.get('summary', {})
        mitre_techniques = summary.get('mitre_techniques', [])

        timeline_analysis = TimelineAnalysis(
            alert_ids=','.join(map(str, alert_ids)),
            client_id=client_id,
            start_time=datetime.fromisoformat(start_time.replace('Z', '+00:00')),
            end_time=datetime.fromisoformat(end_time.replace('Z', '+00:00')),
            fim_events_count=len(fim_data),
            wazuh_events_count=len(wazuh_data),
            analysis_result_json=json.dumps(analysis_result, default=str),
            overall_risk=summary.get('overall_risk', 'Unknown'),
            confidence=summary.get('confidence', 0),
            attack_type=summary.get('attack_type'),
            mitre_techniques=','.join(mitre_techniques) if isinstance(mitre_techniques, list) else mitre_techniques,
            status='completed'
        )
        db.session.add(timeline_analysis)
        db.session.commit()

        print(f"[TIMELINE] Analysis complete (ID: {timeline_analysis.id})")

        return jsonify({
            "success": True,
            "analysis_id": timeline_analysis.id,
            "summary": summary,
            "analysis": analysis_result
        })

    except Exception as e:
        print(f"[TIMELINE] Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

        # Store failed analysis
        try:
            failed_analysis = TimelineAnalysis(
                alert_ids=','.join(map(str, alert_ids)),
                status='failed',
                error_message=str(e)
            )
            db.session.add(failed_analysis)
            db.session.commit()
        except:
            pass

        return jsonify({"error": str(e)}), 500


@main_bp.route("/api/timeline/<int:analysis_id>", methods=["GET"])
@login_required
def get_timeline_analysis(analysis_id):
    """Get existing timeline analysis by ID"""
    if not current_user.is_admin:
        return jsonify({"error": "Admin access required"}), 403

    from .database import TimelineAnalysis

    analysis = TimelineAnalysis.query.get_or_404(analysis_id)
    return jsonify(analysis.as_dict())


@main_bp.route("/api/timeline/<int:analysis_id>/report/pdf", methods=["GET"])
@login_required
def download_timeline_analysis_pdf(analysis_id):
    """Download a timeline analysis report as PDF (Admin only)."""
    if not current_user.is_admin:
        return jsonify({"error": "Admin access required"}), 403

    from io import BytesIO
    from tempfile import TemporaryDirectory
    from pathlib import Path

    from .database import TimelineAnalysis
    from .report_templates import render_security_incident_report_markdown
    from .md_to_pdf import convert_markdown_file_to_pdf

    analysis = TimelineAnalysis.query.get_or_404(analysis_id)
    analysis_dict = analysis.as_dict()
    if analysis.client and analysis.client.ip_address:
        analysis_dict["ip_address"] = analysis.client.ip_address

    # Map internal status to the report template's status field (no extra context)
    status_map = {
        "completed": "Closed",
        "failed": "Closed",
        "in_progress": "Monitoring",
    }
    report_status = status_map.get((analysis_dict.get("status") or "").lower(), analysis_dict.get("status"))

    prepared_by = getattr(current_user, "username", None)

    md_text = render_security_incident_report_markdown(
        analysis_dict=analysis_dict,
        prepared_by=prepared_by,
        status=report_status,
    )

    date_part = ""
    created_at = analysis_dict.get("created_at")
    if isinstance(created_at, str) and "T" in created_at:
        date_part = created_at.split("T", 1)[0]

    base_name = f"timeline_analysis_{analysis_id}" + (f"_{date_part}" if date_part else "")

    # On Windows, freshly-created PDF files can be briefly locked by AV/indexers.
    # Never fail the download due to temp cleanup issues.
    with TemporaryDirectory(prefix="fimonacci_report_", ignore_cleanup_errors=True) as tmpdir:
        tmp = Path(tmpdir)
        md_path = tmp / f"{base_name}.md"
        pdf_path = tmp / f"{base_name}.pdf"

        md_path.write_text(md_text, encoding="utf-8")
        convert_markdown_file_to_pdf(str(md_path), str(pdf_path))

        # Read into memory before returning to avoid Windows file-lock issues
        # (send_file may keep the file handle open while streaming the response).
        pdf_bytes = pdf_path.read_bytes()
        bio = BytesIO(pdf_bytes)
        bio.seek(0)

        return send_file(
            bio,
            mimetype="application/pdf",
            as_attachment=True,
            download_name=f"{base_name}.pdf",
        )


@main_bp.route("/api/timeline/list", methods=["GET"])
@login_required
def list_timeline_analyses():
    """List all timeline analyses (paginated)"""
    if not current_user.is_admin:
        return jsonify({"error": "Admin access required"}), 403

    from .database import TimelineAnalysis

    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    risk_filter = request.args.get('risk')  # Optional: Low, Medium, High, Critical

    query = TimelineAnalysis.query.order_by(TimelineAnalysis.created_at.desc())

    if risk_filter:
        query = query.filter_by(overall_risk=risk_filter)

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        "analyses": [a.as_dict() for a in pagination.items],
        "total": pagination.total,
        "page": page,
        "per_page": per_page,
        "total_pages": pagination.pages
    })

