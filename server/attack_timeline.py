"""
Attack Timeline Generation
Builds chronological timelines of related security events
"""

import json
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional
from flask import current_app

from . import db
from .database import FileIntegrity, Client


class AttackTimelineGenerator:
    """Generate attack timelines from file integrity alerts"""
    
    def __init__(self):
        self.time_window_hours = 24  # Group events within 24 hours
        self.similarity_threshold = 0.7  # Threshold for grouping related events
    
    def generate_timeline(self, client_id: Optional[int] = None, 
                          start_time: Optional[datetime] = None,
                          end_time: Optional[datetime] = None) -> List[Dict]:
        """
        Generate attack timeline from alerts
        
        Args:
            client_id: Optional client ID to filter by
            start_time: Start time for timeline
            end_time: End time for timeline
            
        Returns:
            List of timeline events grouped by attack patterns
        """
        try:
            # Build query
            query = FileIntegrity.query
            
            if client_id:
                query = query.filter_by(client_id=client_id)
            
            if start_time:
                query = query.filter(FileIntegrity.timestamp >= start_time)
            
            if end_time:
                query = query.filter(FileIntegrity.timestamp <= end_time)
            
            # Get all alerts ordered by timestamp
            alerts = query.order_by(FileIntegrity.timestamp.asc()).all()
            
            if not alerts:
                return []
            
            # Group alerts into attack sequences
            attack_sequences = self._group_into_sequences(alerts)
            
            # Build timeline
            timeline = []
            for sequence in attack_sequences:
                timeline_event = {
                    "id": f"attack_{sequence[0].id}",
                    "start_time": sequence[0].timestamp.isoformat(),
                    "end_time": sequence[-1].timestamp.isoformat(),
                    "duration_seconds": (sequence[-1].timestamp - sequence[0].timestamp).total_seconds(),
                    "event_count": len(sequence),
                    "client_id": sequence[0].client_id,
                    "client_hostname": sequence[0].client.hostname if sequence[0].client else None,
                    "affected_paths": list(set([a.path for a in sequence])),
                    "alert_types": list(set([a.alert_type for a in sequence])),
                    "risk_score": self._calculate_sequence_risk(sequence),
                    "events": [self._format_event(a) for a in sequence],
                    "attack_pattern": self._detect_attack_pattern(sequence),
                    "indicators": self._extract_indicators(sequence)
                }
                timeline.append(timeline_event)
            
            return sorted(timeline, key=lambda x: x['start_time'], reverse=True)
            
        except Exception as e:
            current_app.logger.error(f"Timeline generation failed: {e}")
            return []
    
    def _group_into_sequences(self, alerts: List[FileIntegrity]) -> List[List[FileIntegrity]]:
        """Group alerts into related attack sequences"""
        sequences = []
        current_sequence = []
        
        for alert in alerts:
            if not current_sequence:
                current_sequence = [alert]
            else:
                last_alert = current_sequence[-1]
                
                # Check if alert is related to current sequence
                if self._are_related(last_alert, alert):
                    current_sequence.append(alert)
                else:
                    # Start new sequence
                    if len(current_sequence) > 0:
                        sequences.append(current_sequence)
                    current_sequence = [alert]
        
        if current_sequence:
            sequences.append(current_sequence)
        
        return sequences
    
    def _are_related(self, alert1: FileIntegrity, alert2: FileIntegrity) -> bool:
        """Check if two alerts are related"""
        # Time window check
        time_diff = abs((alert2.timestamp - alert1.timestamp).total_seconds())
        if time_diff > (self.time_window_hours * 3600):
            return False
        
        # Same client
        if alert1.client_id != alert2.client_id:
            return False
        
        # Path similarity (same directory or related paths)
        path1_parts = alert1.path.split('/')
        path2_parts = alert2.path.split('/')
        
        # Check if paths share common directory structure
        common_parts = 0
        min_len = min(len(path1_parts), len(path2_parts))
        for i in range(min_len):
            if path1_parts[i] == path2_parts[i]:
                common_parts += 1
            else:
                break
        
        # If paths share at least 2 levels, consider related
        if common_parts >= 2:
            return True
        
        # Same process
        if alert1.process_name and alert2.process_name:
            if alert1.process_name == alert2.process_name:
                return True
        
        # Same user
        if alert1.owner_user and alert2.owner_user:
            if alert1.owner_user == alert2.owner_user:
                return True
        
        return False
    
    def _calculate_sequence_risk(self, sequence: List[FileIntegrity]) -> float:
        """Calculate overall risk score for a sequence"""
        if not sequence:
            return 0.0
        
        # Base risk from individual alerts
        risk_scores = []
        for alert in sequence:
            if alert.ai_risk_score:
                risk_scores.append(alert.ai_risk_score)
            else:
                # Default risk based on alert type
                risk_map = {
                    'created': 30,
                    'modified': 50,
                    'deleted': 70,
                    'hash_mismatch': 80,
                    'magic_byte_mismatch': 90
                }
                risk_scores.append(risk_map.get(alert.alert_type, 50))
        
        avg_risk = sum(risk_scores) / len(risk_scores) if risk_scores else 50
        
        # Increase risk for multiple events
        event_multiplier = min(1.0 + (len(sequence) - 1) * 0.1, 1.5)
        
        # Increase risk for magic byte mismatches
        if any(a.magic_byte_mismatch for a in sequence):
            event_multiplier *= 1.2
        
        return min(avg_risk * event_multiplier, 100.0)
    
    def _detect_attack_pattern(self, sequence: List[FileIntegrity]) -> str:
        """Detect attack pattern from sequence"""
        if not sequence:
            return "unknown"
        
        alert_types = [a.alert_type for a in sequence]
        
        # Mass deletion
        if alert_types.count('deleted') > 5:
            return "mass_deletion"
        
        # Ransomware pattern (many files modified quickly)
        if alert_types.count('modified') > 10 and len(sequence) <= 60:  # 60 seconds
            return "ransomware_suspected"
        
        # File type spoofing
        if any(a.magic_byte_mismatch for a in sequence):
            return "file_type_spoofing"
        
        # Privilege escalation (files owned by different users)
        owners = set([a.owner_user for a in sequence if a.owner_user])
        if len(owners) > 2:
            return "privilege_escalation_suspected"
        
        # Lateral movement (files in different directories)
        paths = [a.path for a in sequence]
        dirs = set(['/'.join(p.split('/')[:-1]) for p in paths])
        if len(dirs) > 5:
            return "lateral_movement"
        
        return "suspicious_activity"
    
    def _extract_indicators(self, sequence: List[FileIntegrity]) -> List[str]:
        """Extract security indicators from sequence"""
        indicators = []
        
        # Magic byte mismatches
        if any(a.magic_byte_mismatch for a in sequence):
            indicators.append("File type spoofing detected")
        
        # Unusual processes
        processes = [a.process_name for a in sequence if a.process_name]
        if processes:
            unique_processes = set(processes)
            if len(unique_processes) > 3:
                indicators.append(f"Multiple processes involved: {', '.join(list(unique_processes)[:3])}")
        
        # Rapid changes
        if len(sequence) > 5:
            time_span = (sequence[-1].timestamp - sequence[0].timestamp).total_seconds()
            if time_span < 60:  # Less than a minute
                indicators.append("Rapid file changes detected")
        
        # High-risk file types
        exe_files = [a for a in sequence if a.file_extension in ['.exe', '.dll', '.bat', '.ps1']]
        if exe_files:
            indicators.append("Executable files modified")
        
        return indicators
    
    def _format_event(self, alert: FileIntegrity) -> Dict:
        """Format individual alert for timeline"""
        return {
            "id": alert.id,
            "timestamp": alert.timestamp.isoformat(),
            "alert_type": alert.alert_type,
            "path": alert.path,
            "process_name": alert.process_name,
            "process_id": alert.process_id,
            "owner_user": alert.owner_user,
            "magic_byte_mismatch": alert.magic_byte_mismatch,
            "ai_risk_score": alert.ai_risk_score
        }
    
    def get_timeline_for_client(self, client_id: int, hours: int = 24) -> List[Dict]:
        """Get timeline for specific client"""
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(hours=hours)
        return self.generate_timeline(client_id=client_id, start_time=start_time, end_time=end_time)


# Global instance
timeline_generator = AttackTimelineGenerator()

