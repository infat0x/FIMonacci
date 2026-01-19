"""
Automated Alert System
Sends alerts via multiple channels based on severity and rules
"""

import os
import json
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional
from flask import current_app

from . import db
from .database import FileIntegrity
from .wazuh_integration import wazuh_integration
from .ai_analysis import ai_analysis_engine
from .attack_timeline import timeline_generator


class AutomatedAlertSystem:
    """Automated alerting system with multiple channels"""
    
    def __init__(self):
        self.enabled = os.environ.get('AUTO_ALERTS_ENABLED', 'true').lower() == 'true'
        self.email_enabled = os.environ.get('EMAIL_ALERTS_ENABLED', 'false').lower() == 'true'
        self.slack_enabled = os.environ.get('SLACK_ALERTS_ENABLED', 'false').lower() == 'true'
        self.telegram_enabled = os.environ.get('TELEGRAM_ALERTS_ENABLED', 'false').lower() == 'true'
        
        # Alert thresholds
        self.high_severity_threshold = 70
        self.critical_severity_threshold = 90
        
        # Rate limiting
        self.alert_cooldown_seconds = 300  # 5 minutes between similar alerts
    
    def process_alert(self, alert: FileIntegrity) -> Dict:
        """
        Process a new alert through the automated system
        
        Returns:
            Dictionary with processing results
        """
        if not self.enabled:
            return {"processed": False, "reason": "Alert system disabled"}
        
        results = {
            "processed": True,
            "channels": [],
            "ai_analyzed": False,
            "wazuh_synced": False,
            "timeline_updated": False
        }
        
        try:
            # 1. AI Analysis (if enabled and not already analyzed)
            if not alert.ai_analysis:
                ai_result = ai_analysis_engine.analyze_alert(alert)
                if ai_result:
                    results["ai_analyzed"] = True
                    results["ai_risk_score"] = alert.ai_risk_score
            
            # 2. Determine alert severity
            severity = self._calculate_severity(alert)
            results["severity"] = severity
            
            # 3. Check if alert should be sent (rate limiting, thresholds)
            if not self._should_send_alert(alert, severity):
                results["processed"] = False
                results["reason"] = "Alert filtered by rules"
                return results
            
            # 4. Send to Wazuh (if enabled)
            if wazuh_integration.enabled:
                wazuh_id = wazuh_integration.send_alert_to_wazuh(alert)
                if wazuh_id:
                    results["wazuh_synced"] = True
                    results["wazuh_alert_id"] = wazuh_id
                    results["channels"].append("wazuh")
            
            # 5. Send via communication channels based on severity
            if severity >= self.critical_severity_threshold:
                # Critical alerts - send to all channels
                self._send_critical_alert(alert, results)
            elif severity >= self.high_severity_threshold:
                # High severity - send to configured channels
                self._send_high_severity_alert(alert, results)
            else:
                # Medium/Low - log only or send to specific channels
                self._send_standard_alert(alert, results)
            
            # 6. Update timeline
            # Timeline is generated on-demand, but we mark that new data is available
            results["timeline_updated"] = True
            
            return results
            
        except Exception as e:
            current_app.logger.error(f"Alert processing failed: {e}")
            return {"processed": False, "error": str(e)}
    
    def _calculate_severity(self, alert: FileIntegrity) -> int:
        """Calculate alert severity (0-100)"""
        base_severity = {
            'created': 30,
            'modified': 50,
            'deleted': 70,
            'hash_mismatch': 80,
            'magic_byte_mismatch': 90
        }.get(alert.alert_type, 50)
        
        # Use AI risk score if available
        if alert.ai_risk_score:
            base_severity = int(alert.ai_risk_score)
        
        # Increase severity for magic byte mismatches
        if alert.magic_byte_mismatch:
            base_severity = min(base_severity + 10, 100)
        
        # Increase severity for system files
        system_paths = ['/etc/', '/usr/bin/', '/usr/sbin/', '/system32/', '/windows/']
        if any(alert.path.startswith(sp) for sp in system_paths):
            base_severity = min(base_severity + 15, 100)
        
        return base_severity
    
    def _should_send_alert(self, alert: FileIntegrity, severity: int) -> bool:
        """Check if alert should be sent (rate limiting, filters)"""
        # Always send critical alerts
        if severity >= self.critical_severity_threshold:
            return True
        
        # Check rate limiting - don't send duplicate alerts within cooldown period
        cooldown_time = datetime.now(timezone.utc) - timedelta(seconds=self.alert_cooldown_seconds)
        recent_alert = FileIntegrity.query.filter(
            FileIntegrity.path == alert.path,
            FileIntegrity.alert_type == alert.alert_type,
            FileIntegrity.timestamp > cooldown_time
        ).first()
        
        if recent_alert and severity < self.high_severity_threshold:
            return False
        
        return True
    
    def _send_critical_alert(self, alert: FileIntegrity, results: Dict):
        """Send critical alert via all channels"""
        message = self._format_alert_message(alert, "CRITICAL")
        
        if self.telegram_enabled:
            self._send_telegram_alert(message, alert)
            results["channels"].append("telegram")
        
        if self.slack_enabled:
            self._send_slack_alert(message, alert)
            results["channels"].append("slack")
        
        if self.email_enabled:
            self._send_email_alert(message, alert)
            results["channels"].append("email")
        
        # Log critical alert
        current_app.logger.critical(f"CRITICAL ALERT: {message}")
    
    def _send_high_severity_alert(self, alert: FileIntegrity, results: Dict):
        """Send high severity alert"""
        message = self._format_alert_message(alert, "HIGH")
        
        if self.telegram_enabled:
            self._send_telegram_alert(message, alert)
            results["channels"].append("telegram")
        
        if self.slack_enabled:
            self._send_slack_alert(message, alert)
            results["channels"].append("slack")
        
        current_app.logger.warning(f"HIGH SEVERITY ALERT: {message}")
    
    def _send_standard_alert(self, alert: FileIntegrity, results: Dict):
        """Send standard alert (logging only or low-priority channels)"""
        message = self._format_alert_message(alert, "INFO")
        current_app.logger.info(f"File Integrity Alert: {message}")
    
    def _format_alert_message(self, alert: FileIntegrity, severity: str) -> str:
        """Format alert message"""
        client_info = f"Client: {alert.client.hostname if alert.client else 'Unknown'}"
        process_info = f"Process: {alert.process_name or 'Unknown'}"
        magic_info = "⚠️ MAGIC BYTE MISMATCH" if alert.magic_byte_mismatch else ""
        
        message = f"""
[{severity}] File Integrity Alert

{client_info}
Alert Type: {alert.alert_type.upper()}
File Path: {alert.path}
Timestamp: {alert.timestamp.isoformat()}
{process_info}
Owner: {alert.owner_user or 'Unknown'}
{magic_info}

Risk Score: {alert.ai_risk_score or 'N/A'}
"""
        return message.strip()
    
    def _send_telegram_alert(self, message: str, alert: FileIntegrity):
        """Send alert via Telegram"""
        try:
            from .telegram_bot import send_alert
            send_alert(
                filepath=alert.path,
                alert_type=alert.alert_type,
                client_id=alert.client_id,
                initial_hash=alert.initial_hash,
                current_hash=alert.current_hash,
                client_hostname=alert.client.hostname if alert.client else None
            )
        except Exception as e:
            current_app.logger.error(f"Telegram alert failed: {e}")
    
    def _send_slack_alert(self, message: str, alert: FileIntegrity):
        """Send alert via Slack (placeholder)"""
        # Implement Slack webhook integration
        current_app.logger.info("Slack alerts not yet implemented")
    
    def _send_email_alert(self, message: str, alert: FileIntegrity):
        """Send alert via Email (placeholder)"""
        # Implement email sending
        current_app.logger.info("Email alerts not yet implemented")
    
    def batch_process_alerts(self, alerts: List[FileIntegrity]) -> Dict:
        """Process multiple alerts"""
        results = {
            "processed": 0,
            "failed": 0,
            "channels_used": set()
        }
        
        for alert in alerts:
            result = self.process_alert(alert)
            if result.get("processed"):
                results["processed"] += 1
                results["channels_used"].update(result.get("channels", []))
            else:
                results["failed"] += 1
        
        results["channels_used"] = list(results["channels_used"])
        return results


# Global instance
alert_system = AutomatedAlertSystem()

