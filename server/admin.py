from functools import wraps
from datetime import datetime, timedelta, timezone
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user

from . import db
from .database import User, FileHash, MonitoredFolder, FileIntegrity, Client
from .monitor import _normalize_datetime
from .wazuh_integration import wazuh_integration

admin_bp = Blueprint("admin", __name__)


def admin_required(f):
    """Decorator to require admin access"""
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        # Double check: ensure user is authenticated and is admin
        if not current_user.is_authenticated:
            flash("Please log in to access this page.", "error")
            return redirect(url_for("auth.login"))
        
        # Reload user from database to ensure we have latest admin status
        user = User.query.get(current_user.id)
        if not user or not user.is_admin:
            flash("Access denied. Admin privileges required.", "error")
            return redirect(url_for("main.dashboard"))
        
        return f(*args, **kwargs)
    return decorated_function


@admin_bp.route("/admin")
@admin_required
def admin_panel():
    """Admin panel main page"""
    import time
    import os
    from flask import make_response

    # Pass configuration to template
    config = {
        'AI_PROVIDER': os.environ.get('AI_PROVIDER', 'mistral'),
        'AI_ANALYSIS_ENABLED': os.environ.get('AI_ANALYSIS_ENABLED', 'false')
    }

    # Add cache busting parameter
    response = make_response(render_template("admin.html", cache_bust=int(time.time()), config=config))
    # Force no caching with aggressive headers
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    response.headers['Last-Modified'] = datetime.now(timezone.utc).strftime('%a, %d %b %Y %H:%M:%S GMT')
    return response


@admin_bp.route("/admin/api/clients")
@admin_required
def get_all_clients():
    """Get all clients with statistics"""
    clients = Client.query.order_by(Client.last_seen.desc()).all()
    result = []
    
    for client in clients:
        hash_count = FileHash.query.filter_by(client_id=client.id).count()
        monitored_count = MonitoredFolder.query.filter_by(client_id=client.id, is_active=True).count()
        alerts_count = FileIntegrity.query.filter_by(client_id=client.id).filter(
            FileIntegrity.alert_type != "baseline"
        ).count()
        
        result.append({
            **client.as_dict(),
            "hash_count": hash_count,
            "monitored_folders_count": monitored_count,
            "alerts_count": alerts_count,
        })
    
    return jsonify(result)


@admin_bp.route("/admin/api/client/<int:client_id>/hashes")
@admin_required
def get_client_hashes(client_id):
    """Get all file hashes for a specific client"""
    client = Client.query.get_or_404(client_id)
    hashes = FileHash.query.filter_by(client_id=client_id).order_by(FileHash.timestamp.desc()).all()
    return jsonify({
        "client": client.as_dict(),
        "hashes": [h.as_dict() for h in hashes],
        "count": len(hashes)
    })


@admin_bp.route("/admin/api/client/<int:client_id>/folders")
@admin_required
def get_client_folders(client_id):
    """Get all monitored folders for a specific client"""
    client = Client.query.get_or_404(client_id)
    folders = MonitoredFolder.query.filter_by(client_id=client_id).order_by(MonitoredFolder.created_at.desc()).all()
    return jsonify({
        "client": client.as_dict(),
        "folders": [f.as_dict() for f in folders],
        "count": len(folders)
    })


@admin_bp.route("/admin/api/client/<int:client_id>/alerts")
@admin_required
def get_client_alerts(client_id):
    """Get all alerts for a specific client"""
    client = Client.query.get_or_404(client_id)
    alerts = FileIntegrity.query.filter_by(client_id=client_id).filter(
        FileIntegrity.alert_type != "baseline"
    ).order_by(FileIntegrity.timestamp.desc()).limit(500).all()
    
    return jsonify({
        "client": client.as_dict(),
        "alerts": [a.as_dict() for a in alerts],
        "count": len(alerts)
    })


@admin_bp.route("/admin/api/client/<int:client_id>/stats")
@admin_required
def get_client_stats(client_id):
    """Get comprehensive statistics for a specific client"""
    client = Client.query.get_or_404(client_id)
    
    hash_count = FileHash.query.filter_by(client_id=client_id).count()
    active_folders = MonitoredFolder.query.filter_by(client_id=client_id, is_active=True).count()
    total_folders = MonitoredFolder.query.filter_by(client_id=client_id).count()
    alerts_count = FileIntegrity.query.filter_by(client_id=client_id).filter(
        FileIntegrity.alert_type != "baseline"
    ).count()
    hash_mismatch_count = FileIntegrity.query.filter_by(client_id=client_id).filter_by(
        alert_type="hash_mismatch"
    ).count()
    missing_count = FileIntegrity.query.filter_by(client_id=client_id).filter_by(
        alert_type="missing"
    ).count()
    
    return jsonify({
        "client": client.as_dict(),
        "stats": {
            "total_hashes": hash_count,
            "active_monitored_folders": active_folders,
            "total_monitored_folders": total_folders,
            "total_alerts": alerts_count,
            "hash_mismatch_alerts": hash_mismatch_count,
            "missing_file_alerts": missing_count,
        }
    })


@admin_bp.route("/admin/api/make-admin/<int:user_id>", methods=["POST"])
@admin_required
def make_admin(user_id):
    """Make a user admin"""
    user = User.query.get_or_404(user_id)
    user.is_admin = True
    db.session.commit()
    return jsonify({"success": True, "message": f"User {user.username} is now an admin"})


@admin_bp.route("/admin/api/remove-admin/<int:user_id>", methods=["POST"])
@admin_required
def remove_admin(user_id):
    """Remove admin privileges from a user"""
    if user_id == current_user.id:
        return jsonify({"success": False, "message": "Cannot remove admin privileges from yourself"}), 400
    
    user = User.query.get_or_404(user_id)
    user.is_admin = False
    db.session.commit()
    return jsonify({"success": True, "message": f"Admin privileges removed from {user.username}"})


@admin_bp.route("/admin/api/charts/activity")
@admin_required
def get_activity_chart_data():
    """Get system activity data for 24h chart"""
    # Get data for last 24 hours
    now = datetime.now(timezone.utc)
    start_time = now - timedelta(hours=24)
    
    # Get all alerts in last 24 hours
    alerts = FileIntegrity.query.filter(
        FileIntegrity.timestamp >= start_time,
        FileIntegrity.alert_type != "baseline"
    ).order_by(FileIntegrity.timestamp.asc()).all()
    
    # Create 24 hour buckets (1 hour each)
    buckets = {}
    for i in range(24):
        bucket_time = start_time + timedelta(hours=i)
        buckets[bucket_time] = 0
    
    # Count events per hour
    for alert in alerts:
        # Round to nearest hour
        alert_hour = alert.timestamp.replace(minute=0, second=0, microsecond=0)
        if alert_hour in buckets:
            buckets[alert_hour] += 1
    
    # Generate labels and data
    labels = []
    events_data = []
    
    for hour in sorted(buckets.keys()):
        # Format label
        if hour.hour == 0:
            labels.append("00:00")
        elif hour.hour == now.hour and hour.date() == now.date():
            labels.append("Now")
        else:
            labels.append(f"{hour.hour:02d}:00")
        events_data.append(buckets[hour])
    
    # Generate mock CPU data (in real app, this would come from system monitoring)
    # For now, we'll simulate CPU based on events
    cpu_data = [min(80, 40 + (count * 0.5)) for count in events_data]
    
    return jsonify({
        "labels": labels,
        "events": events_data,
        "cpu": cpu_data
    })


@admin_bp.route("/admin/api/charts/distribution")
@admin_required
def get_distribution_chart_data():
    """Get event distribution data for pie chart"""
    # Get data for last 24 hours
    now = datetime.now(timezone.utc)
    start_time = now - timedelta(hours=24)
    
    # Count events by type
    alerts = FileIntegrity.query.filter(
        FileIntegrity.timestamp >= start_time,
        FileIntegrity.alert_type != "baseline"
    ).all()
    
    # Count by type
    event_counts = {
        "Modified": 0,
        "Created": 0,
        "Deleted": 0,
        "Accessed": 0
    }
    
    for alert in alerts:
        alert_type = alert.alert_type
        if alert_type in ["hash_mismatch", "modified"]:
            event_counts["Modified"] += 1
        elif alert_type == "created":
            event_counts["Created"] += 1
        elif alert_type in ["deleted", "missing"]:
            event_counts["Deleted"] += 1
        else:
            # Count as accessed for other types
            event_counts["Accessed"] += 1
    
    # Prepare data for chart
    labels = []
    values = []
    colors = []
    
    # Order: Modified, Accessed, Created, Deleted
    chart_order = [
        ("Modified", "#3b82f6"),  # Blue
        ("Accessed", "#f59e0b"),  # Orange
        ("Created", "#10b981"),   # Green
        ("Deleted", "#ef4444")    # Red
    ]
    
    for label, color in chart_order:
        count = event_counts[label]
        if count > 0:  # Only include if there are events
            labels.append(label)
            values.append(count)
            colors.append(color)
    
    return jsonify({
        "labels": labels,
        "values": values,
        "colors": colors
    })


@admin_bp.route("/admin/api/charts/agents-activity")
@admin_required
def get_agents_activity_chart_data():
    """Get events per agent for horizontal bar chart"""
    now = datetime.now(timezone.utc)
    start_time = now - timedelta(hours=24)
    
    # Get all clients
    clients = Client.query.all()
    
    agent_data = []
    for client in clients:
        # Count events for this client in last 24h
        event_count = FileIntegrity.query.filter(
            FileIntegrity.client_id == client.id,
            FileIntegrity.timestamp >= start_time,
            FileIntegrity.alert_type != "baseline",
            ~FileIntegrity.alert_type.in_(['client_connected', 'client_disconnected'])
        ).count()
        
        agent_data.append({
            "name": client.hostname or client.client_id[:12],
            "events": event_count,
            "online": (now - _normalize_datetime(client.last_seen)).total_seconds() < 30 if client.last_seen else False
        })
    
    # Sort by events descending
    agent_data.sort(key=lambda x: x["events"], reverse=True)
    
    return jsonify({
        "agents": [a["name"] for a in agent_data[:10]],  # Top 10
        "events": [a["events"] for a in agent_data[:10]],
        "online": [a["online"] for a in agent_data[:10]]
    })


@admin_bp.route("/admin/api/charts/stats-summary")
@admin_required
def get_stats_summary():
    """Get summary statistics for cards"""
    now = datetime.now(timezone.utc)
    start_time_24h = now - timedelta(hours=24)
    start_time_7d = now - timedelta(days=7)
    
    # Total agents
    total_agents = Client.query.count()
    
    # Online agents (seen in last 30 seconds)
    online_agents = 0
    for client in Client.query.all():
        if client.last_seen:
            diff = (now - _normalize_datetime(client.last_seen)).total_seconds()
            if diff < 30:
                online_agents += 1
    
    # Events in last 24h
    events_24h = FileIntegrity.query.filter(
        FileIntegrity.timestamp >= start_time_24h,
        FileIntegrity.alert_type != "baseline",
        ~FileIntegrity.alert_type.in_(['client_connected', 'client_disconnected'])
    ).count()
    
    # Events in last 7 days
    events_7d = FileIntegrity.query.filter(
        FileIntegrity.timestamp >= start_time_7d,
        FileIntegrity.alert_type != "baseline",
        ~FileIntegrity.alert_type.in_(['client_connected', 'client_disconnected'])
    ).count()
    
    # Monitored files total
    monitored_files = FileHash.query.count()
    
    # Critical events (deleted files in 24h)
    critical_events = FileIntegrity.query.filter(
        FileIntegrity.timestamp >= start_time_24h,
        FileIntegrity.alert_type.in_(['deleted', 'missing'])
    ).count()
    
    # Events by type in 24h
    modified_count = FileIntegrity.query.filter(
        FileIntegrity.timestamp >= start_time_24h,
        FileIntegrity.alert_type.in_(['hash_mismatch', 'modified'])
    ).count()
    
    created_count = FileIntegrity.query.filter(
        FileIntegrity.timestamp >= start_time_24h,
        FileIntegrity.alert_type == 'created'
    ).count()
    
    deleted_count = FileIntegrity.query.filter(
        FileIntegrity.timestamp >= start_time_24h,
        FileIntegrity.alert_type.in_(['deleted', 'missing'])
    ).count()
    
    return jsonify({
        "total_agents": total_agents,
        "online_agents": online_agents,
        "events_24h": events_24h,
        "events_7d": events_7d,
        "monitored_files": monitored_files,
        "critical_events": critical_events,
        "modified_count": modified_count,
        "created_count": created_count,
        "deleted_count": deleted_count
    })


@admin_bp.route("/admin/api/charts/hourly-breakdown")
@admin_required
def get_hourly_breakdown():
    """Get detailed hourly breakdown by event type"""
    now = datetime.now(timezone.utc)
    start_time = now - timedelta(hours=24)
    
    # Initialize buckets for each event type
    hourly_data = {
        "modified": [0] * 24,
        "created": [0] * 24,
        "deleted": [0] * 24
    }
    
    labels = []
    for i in range(24):
        bucket_time = start_time + timedelta(hours=i)
        if bucket_time.hour == 0:
            labels.append("00:00")
        elif i == 23:
            labels.append("Now")
        else:
            labels.append(f"{bucket_time.hour:02d}:00")
    
    # Get all events
    alerts = FileIntegrity.query.filter(
        FileIntegrity.timestamp >= start_time,
        FileIntegrity.alert_type != "baseline",
        ~FileIntegrity.alert_type.in_(['client_connected', 'client_disconnected'])
    ).all()
    
    for alert in alerts:
        # Calculate which bucket this falls into
        alert_time = _normalize_datetime(alert.timestamp)
        hours_diff = int((alert_time - start_time).total_seconds() / 3600)
        if 0 <= hours_diff < 24:
            if alert.alert_type in ['hash_mismatch', 'modified']:
                hourly_data["modified"][hours_diff] += 1
            elif alert.alert_type == 'created':
                hourly_data["created"][hours_diff] += 1
            elif alert.alert_type in ['deleted', 'missing']:
                hourly_data["deleted"][hours_diff] += 1
    
    return jsonify({
        "labels": labels,
        "modified": hourly_data["modified"],
        "created": hourly_data["created"],
        "deleted": hourly_data["deleted"]
    })


@admin_bp.route("/admin/api/logs")
@admin_required
def get_logs():
    """Get system logs from FileIntegrity events and client activity"""
    logs = []
    
    # Get file integrity events from last 24 hours
    now = datetime.now(timezone.utc)
    start_time = now - timedelta(hours=24)
    
    alerts = FileIntegrity.query.filter(
        FileIntegrity.timestamp >= start_time
    ).order_by(FileIntegrity.timestamp.desc()).limit(500).all()
    
    for alert in alerts:
        alert_type = alert.alert_type
        
        # Determine log level and message
        if alert_type in ["deleted", "missing"]:
            level = "error"
            message = f"File deleted: {alert.path}"
        elif alert_type == "created":
            level = "success"
            message = f"File created: {alert.path}"
        elif alert_type in ["hash_mismatch", "modified"]:
            level = "warning"
            message = f"File modified: {alert.path} (Hash changed)"
        else:
            level = "info"
            message = f"File event: {alert.path} ({alert_type})"
        
        # Get client hostname if available
        client_info = ""
        if alert.client_id and alert.client:
            client_info = f" [Client: {alert.client.hostname or alert.client.client_id[:8]}]"
        
        logs.append({
            "timestamp": alert.timestamp.isoformat(),
            "level": level,
            "type": "file_event",
            "message": message + client_info
        })
    
    # Get client connection events
    clients = Client.query.filter(
        Client.last_seen >= start_time
    ).order_by(Client.last_seen.desc()).limit(100).all()
    
    for client in clients:
        # Check if this is a recent connection (within last hour)
        # Normalize datetime for comparison
        last_seen = _normalize_datetime(client.last_seen)
        if (now - last_seen).total_seconds() < 3600:
            logs.append({
                "timestamp": client.last_seen.isoformat(),
                "level": "info",
                "type": "client",
                "message": f"Client connected: {client.hostname or 'Unknown'} (ID: {client.client_id[:8]}...)"
            })
    
    # Add system events
    logs.append({
        "timestamp": now.isoformat(),
        "level": "info",
        "type": "system",
        "message": "FIMonacci monitoring system active"
    })
    
    # Sort by timestamp (newest first)
    logs.sort(key=lambda x: x["timestamp"], reverse=True)
    
    return jsonify(logs[:200])  # Return latest 200 logs


@admin_bp.route("/admin/api/logs/clear", methods=["POST"])
@admin_required
def clear_logs():
    """Clear old logs (older than 7 days)"""
    # Delete logs older than 7 days (except baseline)
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)

    deleted_count = FileIntegrity.query.filter(
        FileIntegrity.timestamp < cutoff,
        FileIntegrity.alert_type != "baseline"
    ).delete()

    db.session.commit()

    return jsonify({
        "success": True,
        "message": f"Cleared {deleted_count} old log entries"
    })


@admin_bp.route("/admin/api/wazuh/query", methods=["POST"])
@admin_required
def query_wazuh_events():
    """Query Wazuh SIEM for events by agent IP and time frame"""
    try:
        data = request.get_json()

        agent_ip = data.get("agent_ip")
        start_time = data.get("start_time")
        end_time = data.get("end_time")

        # Validate inputs
        if not agent_ip:
            return jsonify({
                "success": False,
                "error": "Agent IP is required"
            }), 400

        if not start_time or not end_time:
            return jsonify({
                "success": False,
                "error": "Start time and end time are required"
            }), 400

        # Query Wazuh
        result = wazuh_integration.query_events_by_agent(agent_ip, start_time, end_time)

        return jsonify(result)

    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"Server error: {str(e)}"
        }), 500

