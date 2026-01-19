import secrets
import json
from datetime import datetime, timezone

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from . import db


class User(UserMixin, db.Model):
    """Admin users only - for accessing admin panel"""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    
    api_tokens = db.relationship('ApiToken', backref='user', lazy=True, cascade='all, delete-orphan')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def as_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "is_admin": self.is_admin,
            "created_at": self.created_at.isoformat() + 'Z' if self.created_at else None,
        }


class Client(db.Model):
    """Anonymous clients - identified by unique ID and hostname"""
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.String(64), unique=True, nullable=False, index=True)  # Unique random ID
    hostname = db.Column(db.String(255), nullable=True, index=True)
    ip_address = db.Column(db.String(45), nullable=True, index=True)  # IPv4 or IPv6
    first_seen = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    last_seen = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    file_hashes = db.relationship('FileHash', backref='client', lazy=True, cascade='all, delete-orphan')
    monitored_folders = db.relationship('MonitoredFolder', backref='client', lazy=True, cascade='all, delete-orphan')
    alerts = db.relationship('FileIntegrity', backref='client', lazy=True, cascade='all, delete-orphan')

    @staticmethod
    def generate_client_id():
        """Generate a unique client ID"""
        return secrets.token_urlsafe(32)  # 43 characters, URL-safe

    def as_dict(self):
        return {
            "id": self.id,
            "client_id": self.client_id,
            "hostname": self.hostname,
            "ip_address": self.ip_address,
            "first_seen": self.first_seen.isoformat() + 'Z' if self.first_seen else None,
            "last_seen": self.last_seen.isoformat() + 'Z' if self.last_seen else None,
        }


class FileHash(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=True, index=True)  # Nullable for migration
    path = db.Column(db.String, nullable=False, index=True)
    hash_md5 = db.Column(db.String(32), nullable=False)
    file_size = db.Column(db.Integer)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Enhanced metadata fields
    owner_user = db.Column(db.String(255), nullable=True)
    owner_user_id = db.Column(db.String(255), nullable=True)  # UID or SID
    owner_group = db.Column(db.String(255), nullable=True)
    owner_group_id = db.Column(db.String(255), nullable=True)  # GID
    permissions = db.Column(db.String(50), nullable=True)  # e.g., 0o755
    created_at = db.Column(db.DateTime, nullable=True)
    modified_at = db.Column(db.DateTime, nullable=True)
    accessed_at = db.Column(db.DateTime, nullable=True)
    magic_bytes = db.Column(db.String(32), nullable=True)  # Hex string of first bytes
    detected_file_type = db.Column(db.String(50), nullable=True)
    file_extension = db.Column(db.String(20), nullable=True)
    magic_byte_mismatch = db.Column(db.Boolean, default=False, nullable=False)
    process_name = db.Column(db.String(255), nullable=True)
    process_id = db.Column(db.String(50), nullable=True)
    process_user = db.Column(db.String(255), nullable=True)

    # New fields for enhanced monitoring
    entropy = db.Column(db.Float, nullable=True)  # Shannon entropy (0.0 - 8.0)
    high_entropy = db.Column(db.Boolean, default=False, nullable=False)  # Flag for encrypted/compressed files
    is_hidden = db.Column(db.Boolean, default=False, nullable=False)  # Hidden file flag

    metadata_json = db.Column(db.Text, nullable=True)  # Store full metadata as JSON for flexibility
    
    def as_dict(self):
        result = {
            "id": self.id,
            "client_id": self.client_id,
            "path": self.path,
            "hash_md5": self.hash_md5,
            "file_size": self.file_size,
            "timestamp": self.timestamp.isoformat() + 'Z' if self.timestamp else None,
            "owner_user": self.owner_user,
            "owner_user_id": self.owner_user_id,
            "owner_group": self.owner_group,
            "owner_group_id": self.owner_group_id,
            "permissions": self.permissions,
            "created_at": self.created_at.isoformat() + 'Z' if self.created_at else None,
            "modified_at": self.modified_at.isoformat() + 'Z' if self.modified_at else None,
            "accessed_at": self.accessed_at.isoformat() + 'Z' if self.accessed_at else None,
            "magic_bytes": self.magic_bytes,
            "detected_file_type": self.detected_file_type,
            "file_extension": self.file_extension,
            "magic_byte_mismatch": self.magic_byte_mismatch,
            "process_name": self.process_name,
            "process_id": self.process_id,
            "process_user": self.process_user,
            "entropy": self.entropy,
            "high_entropy": self.high_entropy,
            "is_hidden": self.is_hidden,
        }
        # Parse and include full metadata if available
        if self.metadata_json:
            try:
                metadata_obj = json.loads(self.metadata_json)
                result["metadata"] = metadata_obj
            except Exception:
                pass
        return result


class MonitoredFolder(db.Model):
    """Tracks folders that are actively being monitored"""
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=True, index=True)  # Nullable for migration
    folder_path = db.Column(db.String, nullable=False, index=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    last_scan = db.Column(db.DateTime)
    
    def as_dict(self):
        return {
            "id": self.id,
            "client_id": self.client_id,
            "folder_path": self.folder_path,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() + 'Z' if self.created_at else None,
            "last_scan": self.last_scan.isoformat() + 'Z' if self.last_scan else None,
        }


class FileIntegrity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=True, index=True)  # Nullable for migration
    path = db.Column(db.String, nullable=False, index=True)
    initial_hash = db.Column(db.String(32), nullable=False)
    current_hash = db.Column(db.String(32))
    alert_type = db.Column(db.String, nullable=False, index=True)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    
    # File metadata
    file_size = db.Column(db.BigInteger, nullable=True)
    file_extension = db.Column(db.String(50), nullable=True)
    magic_bytes = db.Column(db.String(64), nullable=True)  # Hex string of first bytes
    detected_file_type = db.Column(db.String(100), nullable=True)
    magic_byte_mismatch = db.Column(db.Boolean, default=False, nullable=False)
    
    # Ownership information
    owner_user = db.Column(db.String(255), nullable=True)  # Username
    owner_user_id = db.Column(db.String(255), nullable=True)  # UID / SID
    owner_group = db.Column(db.String(255), nullable=True)  # Group name
    owner_group_id = db.Column(db.String(255), nullable=True)  # GID
    owner_domain = db.Column(db.String(255), nullable=True)  # Windows domain
    ownership_inherited = db.Column(db.Boolean, nullable=True)  # Inherited permissions
    permissions = db.Column(db.String(50), nullable=True)  # File permissions (e.g., 0755)
    
    # Actor information (who performed the action)
    actor_user = db.Column(db.String(255), nullable=True)  # User who modified/created/deleted
    actor_user_id = db.Column(db.String(255), nullable=True)
    actor_session_id = db.Column(db.String(100), nullable=True)
    actor_privilege_level = db.Column(db.String(50), nullable=True)  # admin, user, system
    actor_auth_method = db.Column(db.String(100), nullable=True)  # password, ssh-key, token, etc.
    
    # Process information
    process_name = db.Column(db.String(255), nullable=True)
    process_id = db.Column(db.String(50), nullable=True)
    process_user = db.Column(db.String(255), nullable=True)
    process_command_line = db.Column(db.Text, nullable=True)
    process_path = db.Column(db.String(512), nullable=True)
    parent_process_id = db.Column(db.String(50), nullable=True)
    parent_process_name = db.Column(db.String(255), nullable=True)
    process_tree_json = db.Column(db.Text, nullable=True)  # Full process tree as JSON
    
    # Timestamps
    file_created_at = db.Column(db.DateTime, nullable=True)
    file_modified_at = db.Column(db.DateTime, nullable=True)
    file_accessed_at = db.Column(db.DateTime, nullable=True)
    
    # PII and content analysis
    is_pii = db.Column(db.Boolean, default=False, nullable=False)  # Contains PII
    pii_types = db.Column(db.String(255), nullable=True)  # Types of PII detected
    content_hash_only = db.Column(db.Boolean, default=False, nullable=False)  # If PII, only hash stored
    content_analysis_json = db.Column(db.Text, nullable=True)  # Content changes if not PII

    # New fields for enhanced monitoring
    entropy = db.Column(db.Float, nullable=True)  # Shannon entropy (0.0 - 8.0)
    high_entropy = db.Column(db.Boolean, default=False, nullable=False)  # Flag for encrypted/compressed files
    is_hidden = db.Column(db.Boolean, default=False, nullable=False)  # Hidden file flag

    # Security logs and auth logs
    auth_logs_json = db.Column(db.Text, nullable=True)  # Last 15 auth logs
    security_logs_json = db.Column(db.Text, nullable=True)  # Recent security events

    # Full metadata as JSON for flexibility
    metadata_json = db.Column(db.Text, nullable=True)

    # AI analysis fields
    ai_analysis = db.Column(db.Text, nullable=True)
    ai_risk_score = db.Column(db.Float, nullable=True)  # 0.0 - 1.0 (used to calculate severity)
    ai_analysis_timestamp = db.Column(db.DateTime, nullable=True)
    
    # Wazuh integration
    wazuh_alert_id = db.Column(db.String(100), nullable=True, index=True)
    wazuh_synced = db.Column(db.Boolean, default=False, nullable=False)
    wazuh_sync_timestamp = db.Column(db.DateTime, nullable=True)

    def as_dict(self):
        # Include client info if available
        client_info = {}
        if self.client_id and self.client:
            client_info = {
                "client_hostname": self.client.hostname,
                "client_id_str": self.client.client_id,
            }
        
        result = {
            "id": self.id,
            "client_id": self.client_id,
            "path": self.path,
            "initial_hash": self.initial_hash,
            "current_hash": self.current_hash,
            "alert_type": self.alert_type,
            "timestamp": self.timestamp.isoformat() + 'Z' if self.timestamp else None,
            # File metadata
            "file_size": self.file_size,
            "file_extension": self.file_extension,
            "magic_bytes": self.magic_bytes,
            "detected_file_type": self.detected_file_type,
            "magic_byte_mismatch": self.magic_byte_mismatch,
            # Ownership
            "owner_user": self.owner_user,
            "owner_user_id": self.owner_user_id,
            "owner_group": self.owner_group,
            "owner_group_id": self.owner_group_id,
            "owner_domain": self.owner_domain,
            "ownership_inherited": self.ownership_inherited,
            "permissions": self.permissions,
            # Actor
            "actor_user": self.actor_user,
            "actor_user_id": self.actor_user_id,
            "actor_session_id": self.actor_session_id,
            "actor_privilege_level": self.actor_privilege_level,
            "actor_auth_method": self.actor_auth_method,
            # Process
            "process_name": self.process_name,
            "process_id": self.process_id,
            "process_user": self.process_user,
            "process_command_line": self.process_command_line,
            "process_path": self.process_path,
            "parent_process_id": self.parent_process_id,
            "parent_process_name": self.parent_process_name,
            # Timestamps (add Z suffix to indicate UTC)
            "file_created_at": self.file_created_at.isoformat() + 'Z' if self.file_created_at else None,
            "file_modified_at": self.file_modified_at.isoformat() + 'Z' if self.file_modified_at else None,
            "file_accessed_at": self.file_accessed_at.isoformat() + 'Z' if self.file_accessed_at else None,
            # PII
            "is_pii": self.is_pii,
            "pii_types": self.pii_types,
            "content_hash_only": self.content_hash_only,
            # Enhanced monitoring
            "entropy": self.entropy,
            "high_entropy": self.high_entropy,
            "is_hidden": self.is_hidden,
            # Severity (computed from ai_risk_score or alert characteristics)
            "severity": self._compute_severity(),
            # AI
            "ai_analysis": self.ai_analysis,
            "ai_risk_score": self.ai_risk_score,
            "ai_analysis_timestamp": self.ai_analysis_timestamp.isoformat() + 'Z' if self.ai_analysis_timestamp else None,
            # Wazuh
            "wazuh_alert_id": self.wazuh_alert_id,
            "wazuh_synced": self.wazuh_synced,
            "wazuh_sync_timestamp": self.wazuh_sync_timestamp.isoformat() + 'Z' if self.wazuh_sync_timestamp else None,
            **client_info,
        }
        
        # Parse JSON fields (but don't overwrite existing fields with critical data)
        for json_field in ['process_tree_json', 'content_analysis_json', 'auth_logs_json', 'security_logs_json', 'metadata_json']:
            value = getattr(self, json_field, None)
            if value:
                try:
                    parsed = json.loads(value)
                    field_name = json_field.replace('_json', '')

                    # For metadata_json, merge without overwriting critical fields
                    if json_field == 'metadata_json' and isinstance(parsed, dict):
                        # Don't overwrite entropy, high_entropy, magic_byte_mismatch, etc.
                        # These are stored as dedicated columns for performance
                        critical_fields = {'entropy', 'high_entropy', 'is_hidden', 'magic_byte_mismatch',
                                         'detected_file_type', 'file_extension', 'magic_bytes', 'is_pii',
                                         'pii_types', 'content_hash_only', 'entropy_classification',
                                         'entropy_note'}
                        # Add metadata fields that don't conflict
                        for key, val in parsed.items():
                            if key not in critical_fields and key not in result:
                                result[key] = val
                    else:
                        result[field_name] = parsed
                except Exception:
                    pass
        
        return result
    
    def as_detail_dict(self):
        """Extended dict for detail view"""
        base = self.as_dict()
        # Add any computed fields
        base['severity'] = self._compute_severity()
        return base
    
    def _compute_severity(self):
        """Compute alert severity based on ai_risk_score or alert characteristics"""
        # Prioritize AI risk score if available (0.0 - 1.0 scale)
        if self.ai_risk_score is not None:
            if self.ai_risk_score >= 0.8:
                return 'critical'
            elif self.ai_risk_score >= 0.6:
                return 'high'
            elif self.ai_risk_score >= 0.4:
                return 'medium'
            else:
                return 'low'

        # Fallback: Compute based on alert characteristics
        if self.alert_type in ['deleted', 'missing']:
            return 'critical'
        if self.high_entropy or (self.entropy and self.entropy >= 7.5):
            return 'critical'
        if self.magic_byte_mismatch:
            return 'high'
        if self.is_pii:
            return 'high'
        if self.alert_type in ['hash_mismatch', 'modified']:
            return 'high'
        if self.alert_type == 'created':
            return 'medium'
        return 'low'


class ApiToken(db.Model):
    """API tokens for admin authentication (legacy - not used by clients)"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    token = db.Column(db.String(64), unique=True, nullable=False, index=True)
    name = db.Column(db.String(100), nullable=True)  # Token name/description
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    last_used = db.Column(db.DateTime, nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    # Relationship is defined in User model with backref

    def as_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "token": self.token[:8] + "..." if self.token else None,  # Only show first 8 chars
            "created_at": self.created_at.isoformat() + 'Z' if self.created_at else None,
            "last_used": self.last_used.isoformat() + 'Z' if self.last_used else None,
            "is_active": self.is_active,
        }


class TimelineAnalysis(db.Model):
    """AI-powered timeline analysis reports"""
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)

    # Alert and client context
    alert_ids = db.Column(db.Text, nullable=True)  # Comma-separated alert IDs analyzed
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=True, index=True)

    # Time range analyzed
    start_time = db.Column(db.DateTime, nullable=True)
    end_time = db.Column(db.DateTime, nullable=True)

    # Data sources
    fim_events_count = db.Column(db.Integer, default=0)
    wazuh_events_count = db.Column(db.Integer, default=0)

    # AI Analysis Results (JSON)
    analysis_result_json = db.Column(db.Text, nullable=True)  # Full AI response

    # Quick access fields (extracted from AI result)
    overall_risk = db.Column(db.String(20), nullable=True, index=True)  # Low, Medium, High, Critical
    confidence = db.Column(db.Integer, nullable=True)  # 0-100
    attack_type = db.Column(db.String(255), nullable=True)
    mitre_techniques = db.Column(db.Text, nullable=True)  # Comma-separated

    # Status
    status = db.Column(db.String(50), default='completed', nullable=False)  # completed, failed, in_progress
    error_message = db.Column(db.Text, nullable=True)

    # Relationship
    client = db.relationship('Client', backref='timeline_analyses')

    def as_dict(self):
        result = {
            "id": self.id,
            "created_at": self.created_at.isoformat() + 'Z' if self.created_at else None,
            "client_id": self.client_id,
            "client_hostname": self.client.hostname if self.client else None,
            "alert_ids": self.alert_ids.split(',') if self.alert_ids else [],
            "start_time": self.start_time.isoformat() + 'Z' if self.start_time else None,
            "end_time": self.end_time.isoformat() + 'Z' if self.end_time else None,
            "fim_events_count": self.fim_events_count,
            "wazuh_events_count": self.wazuh_events_count,
            "overall_risk": self.overall_risk,
            "confidence": self.confidence,
            "attack_type": self.attack_type,
            "mitre_techniques": self.mitre_techniques.split(',') if self.mitre_techniques else [],
            "status": self.status,
            "error_message": self.error_message,
        }

        # Parse and include full analysis
        if self.analysis_result_json:
            try:
                result['analysis'] = json.loads(self.analysis_result_json)
            except:
                pass

        return result


class WazuhEventCache(db.Model):
    """Cache of Wazuh SIEM events for timeline analysis"""
    id = db.Column(db.Integer, primary_key=True)

    # Client context
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=True, index=True)
    agent_ip = db.Column(db.String(45), nullable=True, index=True)
    agent_id = db.Column(db.String(100), nullable=True, index=True)

    # Time range
    query_start_time = db.Column(db.DateTime, nullable=False, index=True)
    query_end_time = db.Column(db.DateTime, nullable=False, index=True)

    # Events data (JSON array)
    events_json = db.Column(db.Text, nullable=True)  # Full Wazuh events
    event_count = db.Column(db.Integer, default=0)
    unique_event_count = db.Column(db.Integer, default=0)  # After deduplication

    # Cache metadata
    cached_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    expires_at = db.Column(db.DateTime, nullable=True, index=True)  # Cache expiration (optional)

    # Query parameters hash (for cache lookup)
    query_hash = db.Column(db.String(64), nullable=True, index=True)

    # Relationship
    client = db.relationship('Client', backref='wazuh_event_caches')

    def as_dict(self):
        result = {
            "id": self.id,
            "client_id": self.client_id,
            "client_hostname": self.client.hostname if self.client else None,
            "agent_ip": self.agent_ip,
            "agent_id": self.agent_id,
            "query_start_time": self.query_start_time.isoformat() + 'Z' if self.query_start_time else None,
            "query_end_time": self.query_end_time.isoformat() + 'Z' if self.query_end_time else None,
            "event_count": self.event_count,
            "unique_event_count": self.unique_event_count,
            "cached_at": self.cached_at.isoformat() + 'Z' if self.cached_at else None,
            "expires_at": self.expires_at.isoformat() + 'Z' if self.expires_at else None,
        }

        # Include events if requested
        if self.events_json:
            try:
                result['events'] = json.loads(self.events_json)
            except:
                result['events'] = []

        return result

