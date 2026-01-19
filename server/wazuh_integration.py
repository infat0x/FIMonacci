"""
Wazuh SIEM Integration Module
Bidirectional integration with Wazuh for security event correlation
"""

import os
import json
import requests
import urllib3
from datetime import datetime, timezone, timedelta
from typing import Dict, Optional, List
from flask import current_app

from . import db
from .database import FileIntegrity

# Disable SSL warnings for Wazuh self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class WazuhIntegration:
    """Handle bidirectional integration with Wazuh SIEM"""

    def __init__(self):
        self.wazuh_manager_url = os.environ.get('WAZUH_MANAGER_URL')
        self.wazuh_indexer_url = os.environ.get('WAZUH_INDEXER_URL')
        self.wazuh_api_user = os.environ.get('WAZUH_API_USER')
        self.wazuh_api_password = os.environ.get('WAZUH_API_PASSWORD')
        self.wazuh_indexer_user = os.environ.get('WAZUH_INDEXER_USER', 'admin')
        self.wazuh_indexer_password = os.environ.get('WAZUH_INDEXER_PASSWORD')
        self.wazuh_api_token = None
        self.wazuh_token_expiry = None
        self.enabled = os.environ.get('WAZUH_ENABLED', 'false').lower() == 'true'

        # Validate configuration
        if self.enabled:
            if not all([self.wazuh_manager_url, self.wazuh_api_user, self.wazuh_api_password]):
                print("[WAZUH] Warning: Wazuh Manager credentials are missing in .env file")
                self.enabled = False
            if not all([self.wazuh_indexer_url, self.wazuh_indexer_user, self.wazuh_indexer_password]):
                print("[WAZUH] Warning: Wazuh Indexer credentials are missing in .env file")
                print("[WAZUH] Alert queries require Indexer access")
        
    def _is_token_valid(self) -> bool:
        """Check if current token is valid and not expired"""
        if not self.wazuh_api_token or not self.wazuh_token_expiry:
            return False

        # Refresh token 1 minute before expiry to be safe
        return datetime.now(timezone.utc) < (self.wazuh_token_expiry - timedelta(minutes=1))

    def _get_auth_token(self) -> Optional[str]:
        """Get authentication token from Wazuh API with automatic refresh"""
        if not self.enabled:
            return None

        # Return existing token if still valid
        if self._is_token_valid():
            print(f"[WAZUH] Using cached token (expires in {(self.wazuh_token_expiry - datetime.now(timezone.utc)).seconds // 60} minutes)")
            return self.wazuh_api_token

        # Token expired or doesn't exist, get new one
        try:
            auth_url = f"{self.wazuh_manager_url}/security/user/authenticate"
            print(f"[WAZUH] Requesting new token from: {auth_url}")
            print(f"[WAZUH] Using username: {self.wazuh_api_user}")

            response = requests.post(
                auth_url,
                auth=(self.wazuh_api_user, self.wazuh_api_password),
                verify=False,  # Disable SSL verification
                timeout=10
            )

            print(f"[WAZUH] Auth response status: {response.status_code}")

            if response.status_code == 200:
                self.wazuh_api_token = response.json().get('data', {}).get('token')
                # Wazuh tokens typically expire in 15 minutes
                self.wazuh_token_expiry = datetime.now(timezone.utc) + timedelta(minutes=15)
                print(f"[WAZUH] New token obtained successfully (expires at {self.wazuh_token_expiry.strftime('%H:%M:%S')})")
                return self.wazuh_api_token
            else:
                print(f"[WAZUH] Authentication failed with status {response.status_code}")
                print(f"[WAZUH] Response: {response.text[:500]}")
                return None
        except Exception as e:
            print(f"[WAZUH] Authentication error: {type(e).__name__}: {e}")
            if hasattr(current_app, 'logger'):
                current_app.logger.error(f"Wazuh authentication failed: {e}")
        return None
    
    def send_alert_to_wazuh(self, alert: FileIntegrity) -> Optional[str]:
        """
        Send FIMonacci alert to Wazuh as a custom event
        
        Returns:
            Wazuh alert ID if successful, None otherwise
        """
        if not self.enabled:
            return None
            
        try:
            token = self._get_auth_token()
            if not token:
                return None
            
            # Prepare Wazuh event data
            wazuh_event = {
                "timestamp": alert.timestamp.isoformat(),
                "agent": {
                    "id": "000",  # Manager agent
                    "name": alert.client.hostname if alert.client else "unknown"
                },
                "manager": {
                    "name": "fimonacci"
                },
                "data": {
                    "source": {
                        "program": "FIMonacci",
                        "type": "file_integrity"
                    },
                    "fim": {
                        "path": alert.path,
                        "event": alert.alert_type,
                        "old_hash": alert.initial_hash,
                        "new_hash": alert.current_hash or "",
                        "owner_user": alert.owner_user or "",
                        "owner_group": alert.owner_group or "",
                        "process_name": alert.process_name or "",
                        "process_id": alert.process_id or "",
                        "magic_bytes": alert.magic_bytes or "",
                        "detected_file_type": alert.detected_file_type or "",
                        "magic_byte_mismatch": alert.magic_byte_mismatch
                    },
                    "message": f"File integrity alert: {alert.alert_type} on {alert.path}",
                    "title": f"FIMonacci Alert: {alert.alert_type}"
                },
                "rule": {
                    "id": 55000,  # Custom rule ID
                    "level": self._calculate_severity(alert),
                    "description": f"File integrity monitoring alert: {alert.alert_type}",
                    "groups": ["fim", "file_integrity"]
                }
            }
            
            # Send to Wazuh API
            headers = {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json'
            }
            
            # Use Wazuh's events API or syslog endpoint
            event_url = f"{self.wazuh_manager_url}/events"
            response = requests.post(
                event_url,
                json=wazuh_event,
                headers=headers,
                verify=False,
                timeout=10
            )
            
            if response.status_code in [200, 201]:
                alert_id = response.json().get('data', {}).get('id') or f"wazuh_{alert.id}"
                alert.wazuh_alert_id = alert_id
                alert.wazuh_synced = True
                alert.wazuh_sync_timestamp = datetime.now(timezone.utc)
                db.session.commit()
                return alert_id
            else:
                current_app.logger.warning(f"Wazuh API returned {response.status_code}: {response.text}")
                
        except Exception as e:
            current_app.logger.error(f"Failed to send alert to Wazuh: {e}")
        
        return None
    
    def _calculate_severity(self, alert: FileIntegrity) -> int:
        """Calculate Wazuh severity level based on alert type"""
        severity_map = {
            'created': 5,
            'modified': 7,
            'deleted': 8,
            'hash_mismatch': 10,
            'magic_byte_mismatch': 12  # High severity for type spoofing
        }
        base_severity = severity_map.get(alert.alert_type, 5)
        
        # Increase severity if magic byte mismatch detected
        if alert.magic_byte_mismatch:
            base_severity += 2
        
        return min(base_severity, 15)  # Max Wazuh severity is 15
    
    def receive_wazuh_alerts(self, wazuh_events: List[Dict]) -> int:
        """
        Receive alerts from Wazuh and create corresponding FileIntegrity records
        
        Args:
            wazuh_events: List of Wazuh event dictionaries
            
        Returns:
            Number of alerts processed
        """
        if not self.enabled:
            return 0
        
        processed = 0
        for event in wazuh_events:
            try:
                # Extract relevant data from Wazuh event
                event_data = event.get('data', {})
                fim_data = event_data.get('fim', {})
                
                if not fim_data:
                    continue
                
                # Create FileIntegrity record from Wazuh event
                alert = FileIntegrity(
                    path=fim_data.get('path', ''),
                    initial_hash=fim_data.get('old_hash', 'unknown'),
                    current_hash=fim_data.get('new_hash'),
                    alert_type=fim_data.get('event', 'unknown'),
                    timestamp=datetime.fromisoformat(event.get('timestamp', datetime.now(timezone.utc).isoformat())),
                    owner_user=fim_data.get('owner_user'),
                    owner_group=fim_data.get('owner_group'),
                    process_name=fim_data.get('process_name'),
                    process_id=fim_data.get('process_id'),
                    magic_bytes=fim_data.get('magic_bytes'),
                    detected_file_type=fim_data.get('detected_file_type'),
                    magic_byte_mismatch=fim_data.get('magic_byte_mismatch', False),
                    wazuh_alert_id=event.get('id'),
                    wazuh_synced=True,
                    wazuh_sync_timestamp=datetime.now(timezone.utc)
                )
                
                db.session.add(alert)
                processed += 1
                
            except Exception as e:
                current_app.logger.error(f"Failed to process Wazuh event: {e}")
                continue
        
        db.session.commit()
        return processed
    
    def sync_alert(self, alert: FileIntegrity) -> bool:
        """Sync a single alert to Wazuh if not already synced"""
        if alert.wazuh_synced:
            return True

        alert_id = self.send_alert_to_wazuh(alert)
        return alert_id is not None

    def _deduplicate_events(self, events: List[Dict]) -> List[Dict]:
        """
        Deduplicate events and count occurrences
        Groups identical events and marks with repeat count (x5, x10, etc.)
        """
        # Define noise patterns to filter out
        noise_patterns = [
            'Agent buffer',
            'Logcollector',
            'ossec-analysisd',
            'ossec-monitord',
            'syscheck scan',
            'File integrity monitoring scan',
        ]

        event_map = {}

        for event in events:
            try:
                # Skip noise events
                description = event.get('rule', {}).get('description') or ''
                if description and any(pattern.lower() in description.lower() for pattern in noise_patterns):
                    continue

                # Skip low-level informational events (level < 3)
                if event.get('rule', {}).get('level', 0) < 3:
                    continue

                # Create a unique key for deduplication
                # Based on: rule description + relevant data fields
                rule_desc = event.get('rule', {}).get('description') or ''
                rule_level = event.get('rule', {}).get('level', 0)

                # Create key based on event type
                data = event.get('data', {})

                # For authentication events: user + srcip + status
                if 'authentication' in str(event.get('rule', {}).get('groups', [])):
                    key = f"{rule_desc}|{data.get('srcuser')}|{data.get('srcip')}|{data.get('status')}"

                # For sudo events: command + user
                elif 'sudo' in str(event.get('rule', {}).get('groups', [])):
                    key = f"{rule_desc}|{data.get('command')}|{data.get('user')}"

                # For file changes: path + mode
                elif 'syscheck' in str(event.get('rule', {}).get('groups', [])):
                    key = f"{rule_desc}|{data.get('path')}|{data.get('mode')}"

                # For network events: srcip + dstip + dstport
                elif any(g in str(event.get('rule', {}).get('groups', [])) for g in ['firewall', 'ids', 'netinfo']):
                    key = f"{rule_desc}|{data.get('srcip')}|{data.get('dstip')}|{data.get('dstport')}"

                # For process execution: image + commandLine
                elif 'windows' in str(event.get('rule', {}).get('groups', [])):
                    win_data = data.get('win', {}).get('eventdata', {})
                    key = f"{rule_desc}|{win_data.get('image')}|{win_data.get('commandLine')}"

                # Generic key
                else:
                    key = f"{rule_desc}|{rule_level}"

                # Add to map or increment count
                if key in event_map:
                    event_map[key]['count'] += 1
                    # Keep the latest timestamp
                    if event.get('timestamp', '') > event_map[key]['event'].get('timestamp', ''):
                        event_map[key]['event']['timestamp'] = event.get('timestamp')
                else:
                    event_map[key] = {
                        'event': event,
                        'count': 1
                    }
            except (AttributeError, TypeError, KeyError) as e:
                # Skip malformed events
                print(f"[WAZUH] Skipping malformed event: {e}")
                continue

        # Convert back to list and add repeat_count field
        deduplicated = []
        for item in event_map.values():
            event = item['event']
            count = item['count']

            # Add repeat count to the event
            event['repeat_count'] = count

            deduplicated.append(event)

        # Sort by rule level (highest first), then by timestamp
        deduplicated.sort(
            key=lambda x: (
                -x.get('rule', {}).get('level', 0),
                x.get('timestamp', '')
            ),
            reverse=False
        )

        return deduplicated

    def query_events_by_agent(self, agent_ip: str, start_time: str, end_time: str) -> Dict:
        """
        Query Wazuh events for a specific agent IP within a time frame

        Args:
            agent_ip: IP address of the agent to query
            start_time: Start time in ISO format (e.g., "2025-12-17T10:00:00")
            end_time: End time in ISO format (e.g., "2025-12-17T12:00:00")

        Returns:
            Dictionary containing Wazuh events in JSON format
        """
        try:
            token = self._get_auth_token()
            if not token:
                return {
                    "success": False,
                    "error": "Failed to authenticate with Wazuh",
                    "data": []
                }

            headers = {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json'
            }

            # First, get the agent ID from the IP address
            agents_url = f"{self.wazuh_manager_url}/agents"
            params = {
                'ip': agent_ip,
                'select': 'id,name,ip,status'
            }

            response = requests.get(
                agents_url,
                headers=headers,
                params=params,
                verify=False,
                timeout=10
            )

            if response.status_code != 200:
                return {
                    "success": False,
                    "error": f"Failed to find agent with IP {agent_ip}",
                    "data": []
                }

            agents_data = response.json().get('data', {}).get('affected_items', [])
            if not agents_data:
                return {
                    "success": False,
                    "error": f"No agent found with IP {agent_ip}",
                    "data": []
                }

            agent_id = agents_data[0]['id']
            agent_name = agents_data[0].get('name', 'unknown')

            # Query alerts for this agent within the time frame
            # Standard Wazuh API endpoint for alerts
            print(f"[WAZUH] Querying alerts for agent {agent_id} ({agent_name})")
            print(f"[WAZUH] Time range: {start_time} to {end_time}")

            # Query Wazuh Indexer (OpenSearch/Elasticsearch) for alerts
            print(f"[WAZUH] Querying Wazuh Indexer for alerts")
            debug_log = []

            if not self.wazuh_indexer_url:
                return {
                    "success": False,
                    "error": "Wazuh Indexer URL not configured. Add WAZUH_INDEXER_URL to .env",
                    "data": []
                }

            # Build Elasticsearch query
            indexer_query = {
                "query": {
                    "bool": {
                        "must": [
                            {"match": {"agent.id": agent_id}},
                            {"range": {"timestamp": {"gte": start_time, "lte": end_time}}}
                        ]
                    }
                },
                "sort": [{"timestamp": {"order": "desc"}}],
                "size": 500
            }

            # Try querying the Wazuh Indexer
            indexer_url = f"{self.wazuh_indexer_url}/wazuh-alerts-*/_search"
            debug_log.append(f"Querying Indexer: {indexer_url}")
            print(f"[WAZUH] {debug_log[-1]}")

            try:
                response = requests.post(
                    indexer_url,
                    json=indexer_query,
                    auth=(self.wazuh_indexer_user, self.wazuh_indexer_password),
                    verify=False,
                    timeout=30,
                    headers={'Content-Type': 'application/json'}
                )

                status_log = f"Indexer response status: {response.status_code}"
                print(f"[WAZUH] {status_log}")
                debug_log.append(status_log)

                if response.status_code == 200:
                    print(f"[WAZUH] Successfully queried Wazuh Indexer")
                    debug_log.append("Success! Retrieved alerts from Indexer")

                    indexer_data = response.json()
                    hits = indexer_data.get('hits', {}).get('hits', [])

                    # Extract and filter alert data - only essential fields
                    filtered_alerts = []
                    for hit in hits:
                        source = hit.get('_source', {})

                        # Only extract essential fields
                        filtered_event = {
                            'timestamp': source.get('timestamp'),
                            'rule': {
                                'level': source.get('rule', {}).get('level'),
                                'description': source.get('rule', {}).get('description'),
                                'groups': source.get('rule', {}).get('groups', [])
                            },
                            'agent': {
                                'id': source.get('agent', {}).get('id'),
                                'name': source.get('agent', {}).get('name'),
                                'ip': source.get('agent', {}).get('ip')
                            },
                            'data': {}
                        }

                        # Include specific data fields based on event type
                        event_data = source.get('data', {})
                        rule_groups = source.get('rule', {}).get('groups', [])

                        # Authentication events
                        if 'authentication' in rule_groups:
                            filtered_event['data'] = {
                                'srcuser': event_data.get('srcuser'),
                                'dstuser': event_data.get('dstuser'),
                                'srcip': event_data.get('srcip'),
                                'status': event_data.get('status')
                            }

                        # Privilege escalation
                        elif 'sudo' in rule_groups or 'elevation_of_privilege' in rule_groups:
                            filtered_event['data'] = {
                                'command': event_data.get('command'),
                                'user': event_data.get('user'),
                                'effective_user': event_data.get('effective_user')
                            }

                        # File integrity
                        elif 'syscheck' in rule_groups or 'ossec' in rule_groups:
                            filtered_event['data'] = {
                                'path': event_data.get('path'),
                                'mode': event_data.get('mode'),
                                'size_after': event_data.get('size_after'),
                                'changed_attributes': event_data.get('changed_attributes')
                            }

                        # Network/Firewall
                        elif any(g in rule_groups for g in ['firewall', 'ids', 'netinfo', 'dns']):
                            filtered_event['data'] = {
                                'srcip': event_data.get('srcip'),
                                'dstip': event_data.get('dstip'),
                                'srcport': event_data.get('srcport'),
                                'dstport': event_data.get('dstport'),
                                'protocol': event_data.get('protocol'),
                                'action': event_data.get('action')
                            }

                        # Process execution
                        elif 'windows' in rule_groups or 'sysmon' in rule_groups:
                            filtered_event['data'] = {
                                'win': {
                                    'eventdata': {
                                        'image': event_data.get('win', {}).get('eventdata', {}).get('image'),
                                        'commandLine': event_data.get('win', {}).get('eventdata', {}).get('commandLine'),
                                        'user': event_data.get('win', {}).get('eventdata', {}).get('user'),
                                        'parentImage': event_data.get('win', {}).get('eventdata', {}).get('parentImage')
                                    }
                                }
                            }

                        # Remove empty data fields
                        filtered_event['data'] = {k: v for k, v in filtered_event['data'].items() if v}

                        filtered_alerts.append(filtered_event)

                    print(f"[WAZUH] Filtered {len(hits)} alerts down to {len(filtered_alerts)} with essential fields only")
                    debug_log.append(f"Filtered to {len(filtered_alerts)} events with essential fields")

                    # Deduplicate and count repeated events
                    deduplicated = self._deduplicate_events(filtered_alerts)
                    print(f"[WAZUH] After deduplication: {len(deduplicated)} unique events (from {len(filtered_alerts)} total)")
                    debug_log.append(f"Deduplicated to {len(deduplicated)} unique events")

                    return {
                        "success": True,
                        "agent_id": agent_id,
                        "agent_name": agent_name,
                        "agent_ip": agent_ip,
                        "start_time": start_time,
                        "end_time": end_time,
                        "total_events": len(filtered_alerts),
                        "unique_events": len(deduplicated),
                        "events": deduplicated,
                        "source": "wazuh-indexer"
                    }
                else:
                    error_text = response.text[:300]
                    fail_log = f"Indexer error: {error_text}"
                    print(f"[WAZUH] {fail_log}")
                    debug_log.append(fail_log)

            except Exception as e:
                error_log = f"Indexer query failed: {type(e).__name__}: {str(e)}"
                print(f"[WAZUH] {error_log}")
                debug_log.append(error_log)

            # If Indexer failed, return error with debug info
            return {
                "success": False,
                "error": "Failed to query Wazuh Indexer. See debug log for details.",
                "debug_log": debug_log,
                "data": []
            }

            # Old REST API code removed - alerts are in Indexer, not REST API
            if False:  # Keep for reference
                alerts_data = response.json().get('data', {})
                affected_items = alerts_data.get('affected_items', [])

                return {
                    "success": True,
                    "agent_id": agent_id,
                    "agent_name": agent_name,
                    "agent_ip": agent_ip,
                    "start_time": start_time,
                    "end_time": end_time,
                    "total_events": len(affected_items),
                    "events": affected_items
                }
            else:
                return {
                    "success": False,
                    "error": f"Wazuh API returned status {response.status_code}: {response.text}",
                    "data": []
                }

        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "error": f"Network error connecting to Wazuh: {str(e)}",
                "data": []
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Error querying Wazuh: {str(e)}",
                "data": []
            }


# Global instance
wazuh_integration = WazuhIntegration()

