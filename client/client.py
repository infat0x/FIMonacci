#!/usr/bin/env python3
"""
FIMonacci Client
Standalone client for scanning local file system and uploading to FIMonacci server.
No registration required - uses unique client ID.
"""

import os
import sys
import hashlib
import json
import socket
import argparse
import secrets
import time
import signal
import platform
import threading
import math
from pathlib import Path
from typing import List, Dict, Optional, Set
from datetime import datetime, timezone
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent
from collections import Counter

# Platform-specific imports
if platform.system() != 'Windows':
    # Unix/Linux only
    try:
        import pwd
        import grp
        PWD_AVAILABLE = True
    except ImportError:
        PWD_AVAILABLE = False
else:
    PWD_AVAILABLE = False

# Optional imports for advanced features
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

try:
    import win32security
    import win32api
    WIN32_AVAILABLE = True
except ImportError:
    WIN32_AVAILABLE = False


class FIMFileEventHandler(FileSystemEventHandler):
    """Watchdog event handler for file system events"""
    
    def __init__(self, client, hash_cache: Dict[str, str]):
        """
        Initialize event handler
        
        Args:
            client: FIMonacciClient instance
            hash_cache: Dictionary of path -> hash for tracking file states
        """
        super().__init__()
        self.client = client
        self.hash_cache = hash_cache
        self.known_files: Set[str] = set(hash_cache.keys())
    
    def on_created(self, event):
        """Handle file creation events"""
        if event.is_directory:
            return
        self._handle_file_event(event.src_path, "created")
    
    def on_modified(self, event):
        """Handle file modification events"""
        if event.is_directory:
            return
        self._handle_file_event(event.src_path, "modified")
    
    def on_deleted(self, event):
        """Handle file deletion events"""
        if event.is_directory:
            return
        self._handle_file_event(event.src_path, "deleted")
    
    def on_moved(self, event):
        """Handle file move/rename events"""
        if event.is_directory:
            return
        # Handle as a rename event with both source and destination paths
        if hasattr(event, 'dest_path') and event.dest_path:
            self._handle_rename_event(event.src_path, event.dest_path)
    
    def _handle_file_event(self, filepath: str, event_type: str):
        """Process file system event and send to server"""
        try:
            # For deleted files, we need to get the path before resolving
            # because the file no longer exists
            if event_type == "deleted":
                # Try to get absolute path, but file might not exist
                try:
                    abs_path = str(Path(filepath).resolve())
                except (OSError, ValueError):
                    # File doesn't exist, use path as-is
                    abs_path = str(filepath)
                
                # Get old hash from cache before removing
                old_hash = self.hash_cache.get(abs_path, "unknown")
                
                # Try to collect metadata before deletion (may fail if file already gone)
                metadata = None
                try:
                    if Path(filepath).exists():
                        metadata = self.client.collect_file_metadata(filepath, event_type="deleted")
                except:
                    # File already deleted, create minimal metadata
                    metadata = {
                        'path': abs_path,
                        'event_type': 'deleted',
                        'event_timestamp': datetime.now(timezone.utc).isoformat(),
                        'file_exists': False,
                        'process_info': self.client.get_process_info()
                    }
                
                # Send alert to server
                self.client._send_event_alert(abs_path, old_hash, None, "deleted", metadata=metadata)
                
                # Remove from cache
                if abs_path in self.hash_cache:
                    del self.hash_cache[abs_path]
                if abs_path in self.known_files:
                    self.known_files.remove(abs_path)
                
                return
            
            # For other events, file should exist
            abs_path = str(Path(filepath).resolve())
            
            if event_type == "created":
                # File was created - collect metadata and send
                file_metadata = self.client.collect_file_metadata(abs_path, event_type="created")
                file_hash = file_metadata.get('hash_md5')
                if file_hash:
                    self.client._send_event_alert(abs_path, None, file_hash, "created", metadata=file_metadata)
                    # Update cache
                    self.hash_cache[abs_path] = file_hash
                    self.known_files.add(abs_path)
                    # Also upload metadata to server
                    self.client.upload_files([file_metadata])
            
            elif event_type == "modified":
                # File was modified - collect metadata and compare
                old_hash = self.hash_cache.get(abs_path)
                file_metadata = self.client.collect_file_metadata(abs_path, event_type="modified", old_hash=old_hash)
                new_hash = file_metadata.get('hash_md5')
                if new_hash:
                    if old_hash and old_hash != new_hash:
                        # Hash changed - send alert with metadata
                        self.client._send_event_alert(abs_path, old_hash, new_hash, "hash_mismatch", metadata=file_metadata)
                        # Update cache
                        self.hash_cache[abs_path] = new_hash
                        # Upload metadata to server
                        self.client.upload_files([file_metadata])
                    elif not old_hash:
                        # File not in cache - treat as created
                        file_metadata['event_type'] = 'created'
                        self.client._send_event_alert(abs_path, None, new_hash, "created", metadata=file_metadata)
                        self.hash_cache[abs_path] = new_hash
                        self.known_files.add(abs_path)
                        self.client.upload_files([file_metadata])
        
        except Exception as e:
            print(f"[WARNING]  Error handling event {event_type} for {filepath}: {e}")

    def _handle_rename_event(self, src_path: str, dest_path: str):
        """Handle file rename/move events as a single 'renamed' event"""
        try:
            # Get absolute paths
            try:
                abs_src_path = str(Path(src_path).resolve())
            except (OSError, ValueError):
                abs_src_path = str(src_path)

            try:
                abs_dest_path = str(Path(dest_path).resolve())
            except (OSError, ValueError):
                abs_dest_path = str(dest_path)

            # Get old hash from cache
            old_hash = self.hash_cache.get(abs_src_path, "unknown")

            # Collect metadata for the destination file (new name)
            file_metadata = self.client.collect_file_metadata(dest_path, event_type="renamed")
            new_hash = file_metadata.get('hash_md5')

            # Add rename-specific metadata
            if file_metadata:
                file_metadata['old_path'] = abs_src_path
                file_metadata['new_path'] = abs_dest_path

            # Send renamed event to server
            if new_hash:
                self.client._send_event_alert(abs_dest_path, old_hash, new_hash, "renamed", metadata=file_metadata)

                # Update cache with new path
                if abs_src_path in self.hash_cache:
                    del self.hash_cache[abs_src_path]
                if abs_src_path in self.known_files:
                    self.known_files.remove(abs_src_path)

                self.hash_cache[abs_dest_path] = new_hash
                self.known_files.add(abs_dest_path)

                # Upload metadata to server
                self.client.upload_files([file_metadata])

        except Exception as e:
            print(f"[WARNING]  Error handling rename event from {src_path} to {dest_path}: {e}")


class FIMonacciClient:
    """Standalone client for FIMonacci server"""

    def __init__(self, server_url: str, config_path: str = "client_config.json", pii_paths: List[str] = None):
        """
        Initialize the client

        Args:
            server_url: Base URL of the FIMonacci server (e.g., http://localhost:5000)
            config_path: Path to config file for storing client ID
            pii_paths: List of paths manually flagged as containing PII (optional)
        """
        # Ensure URL has a scheme
        if not server_url.startswith('http://') and not server_url.startswith('https://'):
            server_url = f'http://{server_url}'
        self.server_url = server_url.rstrip('/')
        self.config_path = Path(config_path)
        self.session = requests.Session()

        # Store PII paths (manually flagged paths)
        self.pii_paths: Set[str] = set(pii_paths or [])

        # Content cache for tracking changes (stores last known content for non-PII files)
        # Format: {filepath: {'content': str, 'hash': str, 'timestamp': datetime}}
        self.content_cache: Dict[str, Dict] = {}
        self.content_cache_max_size = 100  # Maximum files to cache
        self.content_cache_max_file_size = 51200  # Max 50KB per file

        # Load or create client ID
        self.client_id, self.hostname = self._load_or_create_client_id()
        
        # Set headers
        self.session.headers.update({
            'Content-Type': 'application/json',
            'X-Client-ID': self.client_id,
            'X-Hostname': self.hostname
        })
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Register/update client on server
        self._register_client()
    
    def _get_hostname(self) -> str:
        """Get system hostname"""
        try:
            return socket.gethostname()
        except:
            return "unknown"
    
    def _load_or_create_client_id(self) -> tuple:
        """Load existing client ID or create a new one"""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
                    client_id = config.get('client_id')
                    hostname = config.get('hostname', self._get_hostname())
                    if client_id:
                        return client_id, hostname
            except Exception as e:
                print(f"[WARNING]  Warning: Could not load config: {e}")
        
        # Create new client ID
        client_id = secrets.token_urlsafe(32)  # 43 characters
        hostname = self._get_hostname()
        
        # Save to config
        try:
            config = {
                'client_id': client_id,
                'hostname': hostname,
                'created_at': datetime.now(timezone.utc).isoformat()
            }
            with open(self.config_path, 'w') as f:
                json.dump(config, f, indent=2)
            print(f"[OK] Created new client ID: {client_id[:16]}...")
        except Exception as e:
            print(f"[WARNING]  Warning: Could not save config: {e}")
        
        return client_id, hostname
    
    def _register_client(self):
        """Register or update client on server"""
        try:
            response = self.session.post(
                f"{self.server_url}/api/client/register",
                json={
                    "client_id": self.client_id,
                    "hostname": self.hostname
                },
                timeout=10
            )
            
            if response.status_code in [200, 201]:
                print(f"[OK] Client registered: {self.hostname} ({self.client_id[:16]}...)")
            else:
                print(f"[WARNING]  Warning: Server response {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"[WARNING]  Warning: Could not register client: {e}")

    def _send_heartbeat(self):
        """Send lightweight heartbeat to keep last_seen fresh"""
        try:
            self.session.post(
                f"{self.server_url}/api/client/ping",
                json={},
                timeout=5
            )
        except requests.exceptions.RequestException:
            # Heartbeat is best-effort; suppress noisy errors
            pass
    
    def calculate_md5(self, filepath: str) -> Optional[str]:
        """
        Calculate MD5 hash of a file
        
        Args:
            filepath: Path to the file
            
        Returns:
            MD5 hash as hex string, or None if error
        """
        try:
            path_obj = Path(filepath)
            if not path_obj.exists() or not path_obj.is_file():
                return None
            
            hash_md5 = hashlib.md5()
            with open(filepath, "rb") as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except (PermissionError, IOError, OSError) as e:
            print(f"[WARNING]  Warning: Could not read {filepath}: {e}")
            return None
        except Exception as e:
            print(f"[WARNING]  Warning: Error calculating hash for {filepath}: {e}")
            return None
    
    def get_magic_bytes(self, filepath: str, num_bytes: int = 16) -> Optional[str]:
        """
        Read magic bytes (file signature) from the beginning of a file
        
        Args:
            filepath: Path to the file
            num_bytes: Number of bytes to read (default: 16)
            
        Returns:
            Hex string of magic bytes, or None if error
        """
        try:
            path_obj = Path(filepath)
            if not path_obj.exists() or not path_obj.is_file():
                return None
            
            with open(filepath, "rb") as f:
                magic_bytes = f.read(num_bytes)
                return magic_bytes.hex() if magic_bytes else None
        except (PermissionError, IOError, OSError):
            return None
        except Exception as e:
            return None
    
    def detect_file_type_from_magic_bytes(self, magic_hex: str) -> Optional[str]:
        """
        Detect file type from magic bytes
        
        Args:
            magic_hex: Hex string of magic bytes
            
        Returns:
            Detected file type or None
        """
        if not magic_hex:
            return None
        
        magic_bytes = bytes.fromhex(magic_hex)
        
        # Common file signatures
        signatures = {
            b'\x89PNG\r\n\x1a\n': 'PNG',
            b'\xff\xd8\xff': 'JPEG',
            b'GIF87a': 'GIF87a',
            b'GIF89a': 'GIF89a',
            b'%PDF': 'PDF',
            b'PK\x03\x04': 'ZIP',
            b'\x7fELF': 'ELF',
            b'MZ': 'PE/EXE',
            b'BM': 'BMP',
            b'RIFF': 'WAV/AVI',
            b'\x1f\x8b': 'GZIP',
            b'BZ': 'BZIP2',
            b'\x00\x00\x01\x00': 'ICO',
            b'ftyp': 'MP4',
            b'\x00\x00\x00 ftyp': 'MP4',
            b'ID3': 'MP3',
            b'\x00\x00\x00\x18ftyp': 'MP4',
        }
        
        # Check exact matches first
        for sig, file_type in signatures.items():
            if magic_bytes.startswith(sig):
                return file_type
        
        # Check partial matches for variable-length signatures
        if magic_bytes[:2] == b'MZ':
            return 'PE/EXE'
        if magic_bytes[:3] == b'\xff\xd8\xff':
            return 'JPEG'
        if magic_bytes[:4] == b'RIFF':
            return 'WAV/AVI'
        
        return None
    
    def get_file_owner(self, filepath: str) -> Dict[str, Optional[str]]:
        """
        Get file owner information (user and group)
        
        Args:
            filepath: Path to the file
            
        Returns:
            Dictionary with 'owner_user' and 'owner_group' keys
        """
        owner_info = {
            'owner_user': None,
            'owner_group': None,
            'owner_user_id': None,
            'owner_group_id': None,
            'owner_sid': None,  # Windows SID if available
        }
        
        try:
            path_obj = Path(filepath)
            if not path_obj.exists():
                return owner_info
            
            if platform.system() == 'Windows':
                if WIN32_AVAILABLE:
                    try:
                        sd = win32security.GetFileSecurity(filepath, win32security.OWNER_SECURITY_INFORMATION)
                        owner_sid = sd.GetSecurityDescriptorOwner()
                        owner_name, domain, _ = win32security.LookupAccountSid(None, owner_sid)
                        owner_info['owner_user'] = f"{domain}\\{owner_name}" if domain else owner_name
                        owner_info['owner_sid'] = str(owner_sid)
                        owner_info['owner_user_id'] = owner_info['owner_sid']
                        # Windows doesn't have groups like Unix, but we can try to get group info
                        try:
                            sd_group = win32security.GetFileSecurity(filepath, win32security.GROUP_SECURITY_INFORMATION)
                            group_sid = sd_group.GetSecurityDescriptorGroup()
                            if group_sid:
                                group_name, group_domain, _ = win32security.LookupAccountSid(None, group_sid)
                                owner_info['owner_group'] = f"{group_domain}\\{group_name}" if group_domain else group_name
                                owner_info['owner_group_id'] = str(group_sid)
                        except:
                            pass
                    except:
                        pass
                
                # Fallback: use current user info if we couldn't get file-specific owner
                if not owner_info['owner_user']:
                    try:
                        owner_info['owner_user'] = os.environ.get('USERNAME', 'Unknown')
                        owner_info['owner_user_id'] = os.environ.get('USERDOMAIN', '') + '\\' + os.environ.get('USERNAME', '')
                    except:
                        pass
            else:
                # Unix-like systems
                stat_info = path_obj.stat()
                if PWD_AVAILABLE:
                    try:
                        owner_info['owner_user'] = pwd.getpwuid(stat_info.st_uid).pw_name
                        owner_info['owner_user_id'] = str(stat_info.st_uid)
                    except:
                        owner_info['owner_user'] = str(stat_info.st_uid)
                        owner_info['owner_user_id'] = str(stat_info.st_uid)
                    
                    try:
                        owner_info['owner_group'] = grp.getgrgid(stat_info.st_gid).gr_name
                        owner_info['owner_group_id'] = str(stat_info.st_gid)
                    except:
                        owner_info['owner_group'] = str(stat_info.st_gid)
                        owner_info['owner_group_id'] = str(stat_info.st_gid)
                else:
                    # Fallback if pwd/grp not available
                    owner_info['owner_user'] = str(stat_info.st_uid)
                    owner_info['owner_group'] = str(stat_info.st_gid)
                    owner_info['owner_user_id'] = str(stat_info.st_uid)
                    owner_info['owner_group_id'] = str(stat_info.st_gid)
        except Exception:
            pass
        
        return owner_info
    
    def get_file_timestamps(self, filepath: str) -> Dict[str, Optional[str]]:
        """
        Get detailed file timestamps
        
        Args:
            filepath: Path to the file
            
        Returns:
            Dictionary with timestamp information
        """
        timestamps = {
            'created_at': None,
            'modified_at': None,
            'accessed_at': None
        }
        
        try:
            path_obj = Path(filepath)
            if not path_obj.exists():
                return timestamps
            
            stat_info = path_obj.stat()
            
            # Modified time (always available)
            timestamps['modified_at'] = datetime.fromtimestamp(stat_info.st_mtime).isoformat()
            
            # Accessed time
            timestamps['accessed_at'] = datetime.fromtimestamp(stat_info.st_atime).isoformat()
            
            # Created time (platform dependent)
            if platform.system() == 'Windows':
                # Windows: st_ctime is creation time
                timestamps['created_at'] = datetime.fromtimestamp(stat_info.st_ctime).isoformat()
            else:
                # Unix: st_ctime is metadata change time, try st_birthtime if available
                if hasattr(stat_info, 'st_birthtime'):
                    timestamps['created_at'] = datetime.fromtimestamp(stat_info.st_birthtime).isoformat()
                else:
                    # Fallback to st_ctime
                    timestamps['created_at'] = datetime.fromtimestamp(stat_info.st_ctime).isoformat()
        except Exception:
            pass
        
        return timestamps
    
    def get_process_info(self) -> Dict[str, Optional[str]]:
        """
        Get current process information
        
        Returns:
            Dictionary with process information
        """
        process_info = {
            'process_name': None,
            'process_id': None,
            'parent_process_id': None,
            'process_user': None
        }
        
        try:
            if PSUTIL_AVAILABLE:
                current_process = psutil.Process()
                process_info['process_name'] = current_process.name()
                process_info['process_id'] = str(current_process.pid)
                
                try:
                    parent = current_process.parent()
                    if parent:
                        process_info['parent_process_id'] = str(parent.pid)
                        process_info['parent_process_name'] = parent.name()
                except:
                    pass
                
                try:
                    process_info['process_user'] = current_process.username()
                except:
                    pass
            else:
                # Fallback: basic info
                process_info['process_id'] = str(os.getpid())
                process_info['process_name'] = sys.executable
                try:
                    process_info['process_user'] = os.getlogin()
                except:
                    process_info['process_user'] = os.environ.get('USER', os.environ.get('USERNAME'))
        except Exception:
            pass
        
        return process_info
    
    def get_actor_info(self) -> Dict[str, Optional[str]]:
        """
        Get information about the current actor (user performing the action)
        
        Returns:
            Dictionary with actor information
        """
        actor_info = {
            'actor_user': None,
            'actor_user_id': None,
            'actor_session_id': None,
            'actor_privilege_level': None,
            'actor_auth_method': None,
            'actor_domain': None
        }
        
        try:
            # Get current user
            if platform.system() == 'Windows':
                actor_info['actor_user'] = os.environ.get('USERNAME')
                actor_info['actor_domain'] = os.environ.get('USERDOMAIN')
                
                # Check if running as admin
                try:
                    import ctypes
                    is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
                    actor_info['actor_privilege_level'] = 'admin' if is_admin else 'user'
                except:
                    actor_info['actor_privilege_level'] = 'unknown'
                
                # Get session ID
                try:
                    actor_info['actor_session_id'] = os.environ.get('SESSIONNAME', str(os.getpid()))
                except:
                    pass
                
                # Windows SID
                if WIN32_AVAILABLE:
                    try:
                        import win32api
                        actor_info['actor_user_id'] = win32api.GetUserName()
                    except:
                        pass
            else:
                # Unix/Linux
                actor_info['actor_user'] = os.environ.get('USER', os.environ.get('LOGNAME'))
                actor_info['actor_user_id'] = str(os.getuid()) if hasattr(os, 'getuid') else None
                
                # Check if running as root
                if hasattr(os, 'getuid'):
                    actor_info['actor_privilege_level'] = 'root' if os.getuid() == 0 else 'user'
                
                # Get session info
                try:
                    actor_info['actor_session_id'] = os.environ.get('XDG_SESSION_ID', str(os.getpid()))
                except:
                    pass
                
                # Try to determine auth method
                if os.environ.get('SSH_CLIENT') or os.environ.get('SSH_CONNECTION'):
                    actor_info['actor_auth_method'] = 'ssh'
                elif os.environ.get('DISPLAY'):
                    actor_info['actor_auth_method'] = 'local_gui'
                else:
                    actor_info['actor_auth_method'] = 'local_console'
        except Exception:
            pass
        
        return actor_info
    
    def get_process_tree(self, max_depth: int = 5) -> List[Dict]:
        """
        Get the process tree from current process up to init/system
        
        Args:
            max_depth: Maximum depth to traverse
            
        Returns:
            List of process info dictionaries
        """
        process_tree = []
        
        try:
            if not PSUTIL_AVAILABLE:
                return process_tree
            
            current = psutil.Process()
            depth = 0
            
            while current and depth < max_depth:
                try:
                    proc_info = {
                        'pid': current.pid,
                        'name': current.name(),
                        'cmdline': ' '.join(current.cmdline()[:5]) if current.cmdline() else None,
                        'username': current.username() if hasattr(current, 'username') else None,
                        'create_time': datetime.fromtimestamp(current.create_time()).isoformat()
                    }
                    process_tree.append(proc_info)
                    
                    parent = current.parent()
                    if parent and parent.pid != current.pid:
                        current = parent
                    else:
                        break
                    depth += 1
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    break
        except Exception:
            pass
        
        return process_tree
    
    def get_recent_auth_logs(self, limit: int = 15) -> List[Dict]:
        """
        Get recent authentication logs from the system
        
        Args:
            limit: Maximum number of log entries to return
            
        Returns:
            List of auth log entries
        """
        auth_logs = []
        
        try:
            if platform.system() == 'Windows':
                # Try to read Windows Security Event Log
                if WIN32_AVAILABLE:
                    try:
                        import win32evtlog
                        server = 'localhost'
                        logtype = 'Security'
                        hand = win32evtlog.OpenEventLog(server, logtype)
                        flags = win32evtlog.EVENTLOG_BACKWARDS_READ | win32evtlog.EVENTLOG_SEQUENTIAL_READ
                        
                        events = win32evtlog.ReadEventLog(hand, flags, 0)
                        count = 0
                        # Look for logon events (4624, 4625)
                        for event in events:
                            if event.EventID in [4624, 4625] and count < limit:
                                auth_logs.append({
                                    'event_id': event.EventID,
                                    'time': event.TimeGenerated.isoformat() if event.TimeGenerated else None,
                                    'source': event.SourceName,
                                    'type': 'logon_success' if event.EventID == 4624 else 'logon_failure'
                                })
                                count += 1
                        win32evtlog.CloseEventLog(hand)
                    except Exception as e:
                        # Log auth collection failure (likely permission issue)
                        if "1314" in str(e):
                            # Error 1314 = "A required privilege is not held by the client"
                            # This means not running as Administrator
                            print(f"[WARNING] Cannot collect auth logs: Not running as Administrator")
                        else:
                            print(f"[WARNING] Cannot collect auth logs: {e}")
            else:
                # Unix: Try to read auth.log or secure log
                log_files = ['/var/log/auth.log', '/var/log/secure', '/var/log/messages']
                for log_file in log_files:
                    if os.path.exists(log_file):
                        try:
                            with open(log_file, 'r', errors='ignore') as f:
                                lines = f.readlines()[-limit * 2:]  # Read more lines, filter auth
                                for line in reversed(lines):
                                    if any(kw in line.lower() for kw in ['authentication', 'session', 'login', 'sshd', 'sudo']):
                                        auth_logs.append({
                                            'raw': line.strip()[:200],
                                            'source': log_file
                                        })
                                        if len(auth_logs) >= limit:
                                            break
                            break
                        except PermissionError:
                            continue
        except Exception as e:
            print(f"[WARNING] Error collecting auth logs: {e}")

        if auth_logs:
            print(f"[OK] Collected {len(auth_logs)} authentication log entries")

        return auth_logs[:limit]
    
    def get_security_logs(self, limit: int = 10) -> List[Dict]:
        """
        Get recent security-related logs from the system
        
        Args:
            limit: Maximum number of log entries to return
            
        Returns:
            List of security log entries
        """
        security_logs = []
        
        try:
            if platform.system() == 'Windows' and WIN32_AVAILABLE:
                try:
                    import win32evtlog
                    server = 'localhost'
                    logtype = 'Security'
                    hand = win32evtlog.OpenEventLog(server, logtype)
                    flags = win32evtlog.EVENTLOG_BACKWARDS_READ | win32evtlog.EVENTLOG_SEQUENTIAL_READ
                    
                    events = win32evtlog.ReadEventLog(hand, flags, 0)
                    count = 0
                    for event in events:
                        if count < limit:
                            security_logs.append({
                                'event_id': event.EventID,
                                'time': event.TimeGenerated.isoformat() if event.TimeGenerated else None,
                                'source': event.SourceName,
                                'category': event.EventCategory
                            })
                            count += 1
                    win32evtlog.CloseEventLog(hand)
                except Exception:
                    pass
            else:
                # Unix: Try to read syslog
                log_files = ['/var/log/syslog', '/var/log/messages']
                for log_file in log_files:
                    if os.path.exists(log_file):
                        try:
                            with open(log_file, 'r', errors='ignore') as f:
                                lines = f.readlines()[-limit:]
                                for line in reversed(lines):
                                    security_logs.append({
                                        'raw': line.strip()[:200],
                                        'source': log_file
                                    })
                            break
                        except PermissionError:
                            continue
        except Exception:
            pass
        
        return security_logs[:limit]
    
    def calculate_entropy(self, filepath: str, sample_size: int = 8192) -> Optional[float]:
        """
        Calculate Shannon entropy of a file to detect encryption, compression, or randomness

        Args:
            filepath: Path to the file
            sample_size: Number of bytes to sample (default 8KB)

        Returns:
            Entropy value (0.0 - 8.0), or None if error
        """
        try:
            path_obj = Path(filepath)
            if not path_obj.exists() or not path_obj.is_file():
                return None

            with open(filepath, 'rb') as f:
                data = f.read(sample_size)

            if not data:
                return 0.0

            # Count byte frequencies
            byte_counts = Counter(data)
            data_len = len(data)

            # Calculate Shannon entropy
            entropy = 0.0
            for count in byte_counts.values():
                probability = count / data_len
                entropy -= probability * math.log2(probability)

            return round(entropy, 4)

        except Exception as e:
            print(f"Error calculating entropy for {filepath}: {e}")
            return None

    def get_content_changes(self, filepath: str, old_hash: str, new_hash: str, old_content: str = None, max_size: int = 102400) -> Optional[Dict]:
        """
        Extract content changes for non-PII files with before/after comparison

        Args:
            filepath: Path to the file
            old_hash: Previous hash (for reference)
            new_hash: Current hash
            old_content: Previous content if available (for diff)
            max_size: Maximum file size to analyze (100KB default)

        Returns:
            Dictionary with content change information including before/after diff
        """
        try:
            path_obj = Path(filepath)
            if not path_obj.exists() or not path_obj.is_file():
                return None

            # Check file size
            file_size = path_obj.stat().st_size
            if file_size > max_size:
                return {
                    'change_type': 'size_exceeded',
                    'file_size': file_size,
                    'max_size': max_size,
                    'old_hash': old_hash,
                    'new_hash': new_hash
                }

            # Only analyze text files
            text_extensions = {'.txt', '.csv', '.json', '.xml', '.html', '.log', '.md', '.yaml', '.yml', '.conf', '.ini', '.cfg', '.py', '.js', '.java', '.c', '.cpp', '.h', '.sh', '.bat', '.ps1'}
            if path_obj.suffix.lower() not in text_extensions:
                return {
                    'change_type': 'binary_file',
                    'file_extension': path_obj.suffix,
                    'old_hash': old_hash,
                    'new_hash': new_hash
                }

            # Read new content
            with open(filepath, 'r', errors='ignore') as f:
                new_content = f.read(max_size)

            # Calculate statistics for new content
            new_lines = new_content.split('\n')
            new_words = new_content.split()

            result = {
                'change_type': 'text_modification',
                'old_hash': old_hash,
                'new_hash': new_hash,
                'new_content_size': len(new_content),
                'new_line_count': len(new_lines),
                'new_word_count': len(new_words),
                'new_char_count': len(new_content),
                'new_content_preview': new_content[:500] if len(new_content) > 500 else new_content,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }

            # If we have old content, compute diff
            if old_content:
                old_lines = old_content.split('\n')
                old_words = old_content.split()

                result['old_content_size'] = len(old_content)
                result['old_line_count'] = len(old_lines)
                result['old_word_count'] = len(old_words)
                result['old_char_count'] = len(old_content)
                result['old_content_preview'] = old_content[:500] if len(old_content) > 500 else old_content

                # Calculate simple line diff
                result['lines_added'] = len(new_lines) - len(old_lines)
                result['words_added'] = len(new_words) - len(old_words)
                result['chars_added'] = len(new_content) - len(old_content)

                # Store both versions for frontend diff
                result['has_diff'] = True
            else:
                result['has_diff'] = False

            return result

        except Exception as e:
            return {
                'change_type': 'error',
                'error': str(e),
                'old_hash': old_hash,
                'new_hash': new_hash
            }

    def _update_content_cache(self, filepath: str, file_hash: str):
        """
        Update the content cache for a file (for future diff comparison)

        Args:
            filepath: Path to the file
            file_hash: Current hash of the file
        """
        try:
            path_obj = Path(filepath)
            if not path_obj.exists() or not path_obj.is_file():
                return

            # Only cache text files
            text_extensions = {'.txt', '.csv', '.json', '.xml', '.html', '.log', '.md', '.yaml', '.yml', '.conf', '.ini', '.cfg', '.py', '.js', '.java', '.c', '.cpp', '.h', '.sh', '.bat', '.ps1'}
            if path_obj.suffix.lower() not in text_extensions:
                return

            # Check file size limit
            file_size = path_obj.stat().st_size
            if file_size > self.content_cache_max_file_size:
                return

            # Read and cache content
            with open(filepath, 'r', errors='ignore') as f:
                content = f.read(self.content_cache_max_file_size)

            # Add to cache
            self.content_cache[filepath] = {
                'content': content,
                'hash': file_hash,
                'timestamp': datetime.now(timezone.utc)
            }

            # Limit cache size (remove oldest entries if needed)
            if len(self.content_cache) > self.content_cache_max_size:
                # Sort by timestamp and remove oldest
                sorted_items = sorted(
                    self.content_cache.items(),
                    key=lambda x: x[1].get('timestamp', datetime.min.replace(tzinfo=timezone.utc))
                )
                # Keep only the newest entries
                self.content_cache = dict(sorted_items[-self.content_cache_max_size:])

        except Exception:
            pass  # Silently ignore cache errors

    def _is_pii_path(self, filepath: str) -> bool:
        """
        Check if a filepath is under a manually flagged PII path

        Args:
            filepath: Path to check

        Returns:
            True if the file is under a PII path, False otherwise
        """
        try:
            file_path = Path(filepath).resolve()

            for pii_path_str in self.pii_paths:
                pii_path = Path(pii_path_str).resolve()

                # Check if it's an exact match (file)
                if file_path == pii_path:
                    return True

                # Check if file is under this directory
                try:
                    file_path.relative_to(pii_path)
                    return True
                except ValueError:
                    # Not under this path
                    continue

            return False
        except Exception:
            return False

    def detect_pii(self, filepath: str, max_bytes: int = 10240, manual_check_first: bool = True) -> Dict:
        """
        Detect potential PII (Personally Identifiable Information) in a file

        Args:
            filepath: Path to the file
            max_bytes: Maximum bytes to read for analysis
            manual_check_first: Check manual PII flags first (default: True)

        Returns:
            Dictionary with PII detection results
        """
        import re

        pii_result = {
            'is_pii': False,
            'pii_types': [],
            'content_hash_only': False,
            'manual_flag': False
        }

        try:
            # FIRST: Check if path is manually flagged as PII
            if manual_check_first and self._is_pii_path(filepath):
                pii_result['is_pii'] = True
                pii_result['pii_types'] = ['manual']
                pii_result['content_hash_only'] = True
                pii_result['manual_flag'] = True
                return pii_result

            path_obj = Path(filepath)
            if not path_obj.exists() or not path_obj.is_file():
                return pii_result

            # Try to read file as text - if it's actually text content, analyze it regardless of extension
            # This catches cases where text files are renamed to different extensions (e.g., .txt -> .png)
            text_extensions = {'.txt', '.csv', '.json', '.xml', '.html', '.log', '.md', '.yaml', '.yml', '.conf', '.ini', '.cfg'}
            is_text_extension = path_obj.suffix.lower() in text_extensions

            # Skip large files or known binary types to avoid performance issues
            skip_extensions = {'.exe', '.dll', '.bin', '.so', '.dylib', '.jpg', '.jpeg', '.gif', '.bmp', '.ico', '.mp3', '.mp4', '.wav', '.avi', '.mov', '.wmv', '.flv', '.mkv', '.zip', '.rar', '.7z', '.tar', '.gz', '.bz2', '.xz', '.dmg', '.iso'}
            if path_obj.suffix.lower() in skip_extensions:
                return pii_result

            # Only skip if file is too large and doesn't have a text extension
            file_size = path_obj.stat().st_size
            if file_size > 1024 * 1024 and not is_text_extension:  # 1MB limit for non-text extensions
                return pii_result

            # Try to read file content as text
            try:
                with open(filepath, 'r', errors='ignore') as f:
                    content = f.read(max_bytes)
            except Exception:
                # Can't read as text, skip PII detection
                return pii_result

            # PII patterns with minimum match thresholds to reduce false positives
            # Format: pattern, minimum_matches_required
            patterns = {
                'email': (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', 1),  # Even 1 email is significant
                'phone': (r'\b(?:\+?1[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)?\d{3}[-\s]?\d{4}\b', 2),  # At least 2 phone numbers
                'ssn': (r'\b\d{3}[-\s]\d{2}[-\s]\d{4}\b', 1),  # SSN must have dashes/spaces (stricter)
                'credit_card': (r'\b(?:\d{4}[-\s]){3}\d{4}\b', 1),  # Even 1 credit card is significant
                # Removed 'ip_address' - too many false positives with version numbers
                # Removed 'date_of_birth' - too generic
                # Removed 'passport' - too broad
                # Removed 'national_id' - too broad (catches any long number)
            }

            detected_types = []
            for pii_type, (pattern, min_matches) in patterns.items():
                matches = re.findall(pattern, content)
                # Only flag as PII if minimum threshold is met
                if len(matches) >= min_matches:
                    detected_types.append(pii_type)

            if detected_types:
                pii_result['is_pii'] = True
                pii_result['pii_types'] = detected_types
                pii_result['content_hash_only'] = True  # Don't store content details

        except Exception:
            pass

        return pii_result
    
    def collect_file_metadata(self, filepath: str, event_type: str = None, old_hash: str = None) -> Dict:
        """
        Collect comprehensive metadata for a file

        Args:
            filepath: Path to the file
            event_type: Type of event (created, modified, deleted, etc.)
            old_hash: Previous hash (for content change tracking)

        Returns:
            Dictionary with all collected metadata
        """
        metadata = {
            'path': filepath,
            'event_type': event_type,
            'event_timestamp': datetime.now(timezone.utc).isoformat(),
        }

        try:
            path_obj = Path(filepath)

            # Only collect file-specific metadata if file exists
            if path_obj.exists() and path_obj.is_file():
                # Basic file info
                stat_info = path_obj.stat()
                metadata['file_size'] = stat_info.st_size
                # Permissions (octal string, e.g., 0o755)
                try:
                    metadata['permissions'] = oct(stat_info.st_mode & 0o777)
                except Exception:
                    pass

                # Hash
                file_hash = self.calculate_md5(filepath)
                if file_hash:
                    metadata['hash_md5'] = file_hash

                # Entropy calculation
                print(f"[ENTROPY] Calculating entropy for: {filepath}")
                # Log to file for GUI debugging
                try:
                    with open('entropy_debug.log', 'a') as log:
                        log.write(f"{datetime.now()}: Calculating for: {filepath}\n")
                except: pass

                entropy = self.calculate_entropy(filepath)
                print(f"[ENTROPY] Result: {entropy}")

                try:
                    with open('entropy_debug.log', 'a') as log:
                        log.write(f"{datetime.now()}: Result: {entropy}\n")
                except: pass

                if entropy is not None:
                    metadata['entropy'] = entropy

                    # Classify based on entropy value:
                    # H < 4.0 → Plain text
                    # 4.0 ≤ H < 7.5 → Compressed
                    # H ≥ 7.5 → Encrypted
                    if entropy >= 7.5:
                        metadata['high_entropy'] = True
                        metadata['entropy_classification'] = 'Encrypted'
                        metadata['entropy_note'] = 'High entropy - Likely encrypted'
                        print(f"[ENCRYPTED] HIGH ENTROPY DETECTED: {filepath} - Entropy: {entropy}")
                    elif entropy >= 4.0:
                        metadata['high_entropy'] = False
                        metadata['entropy_classification'] = 'Compressed'
                        metadata['entropy_note'] = 'Medium entropy - Likely compressed'
                        print(f"[COMPRESSED] File detected: {filepath} - Entropy: {entropy}")
                    else:
                        metadata['high_entropy'] = False
                        metadata['entropy_classification'] = 'Plain Text'
                        metadata['entropy_note'] = 'Low entropy - Plain text'
                        print(f"[PLAIN TEXT] File detected: {filepath} - Entropy: {entropy}")
                else:
                    print(f"[WARNING] Entropy calculation returned None for {filepath}")
                    # Don't set any entropy fields if calculation failed
                    metadata['entropy'] = None
                    metadata['high_entropy'] = False

                # Magic bytes and file type detection
                magic_bytes = self.get_magic_bytes(filepath)
                if magic_bytes:
                    metadata['magic_bytes'] = magic_bytes
                    detected_type = self.detect_file_type_from_magic_bytes(magic_bytes)
                    if detected_type:
                        metadata['detected_file_type'] = detected_type

                # File extension (for comparison with detected type)
                file_ext = path_obj.suffix.lower()
                metadata['file_extension'] = file_ext

                # Magic byte verification: check if detected type matches extension
                if file_ext:
                    # Map common extensions to file types
                    ext_to_type = {
                        '.png': 'PNG',
                        '.jpg': 'JPEG', '.jpeg': 'JPEG',
                        '.gif': 'GIF87a',
                        '.pdf': 'PDF',
                        '.zip': 'ZIP',
                        '.exe': 'PE/EXE', '.dll': 'PE/EXE',
                        '.bmp': 'BMP',
                        '.wav': 'WAV/AVI', '.avi': 'WAV/AVI',
                        '.gz': 'GZIP',
                        '.bz2': 'BZIP2',
                        '.ico': 'ICO',
                        '.mp4': 'MP4',
                        '.mp3': 'MP3',
                    }

                    # Known text extensions that should NOT have binary magic bytes
                    text_extensions = {'.txt', '.log', '.md', '.csv', '.json', '.xml', '.html', '.css', '.js', '.py', '.java', '.c', '.cpp', '.h', '.sh', '.bat', '.ini', '.cfg', '.conf', '.yaml', '.yml'}

                    expected_type = ext_to_type.get(file_ext)
                    is_text_extension = file_ext in text_extensions

                    # Check for mismatch (bidirectional):
                    # Case 1: Extension expects a specific binary type but detected type is different or missing
                    # Example: .png file that's actually a JPEG or text file
                    if expected_type:
                        if detected_type and detected_type != expected_type:
                            # Has magic bytes but they don't match extension
                            metadata['magic_byte_mismatch'] = True
                            metadata['expected_type'] = expected_type
                            metadata['detected_type'] = detected_type
                        elif not detected_type:
                            # Extension suggests binary file but no magic bytes detected
                            # This usually means it's not actually that file type
                            metadata['magic_byte_mismatch'] = True
                            metadata['expected_type'] = expected_type
                            metadata['detected_type'] = 'Unknown/Text'
                        else:
                            metadata['magic_byte_mismatch'] = False
                    # Case 2: Extension suggests text file but magic bytes indicate binary content
                    # Example: .txt file that's actually a JPEG
                    elif is_text_extension and detected_type:
                        # Text extension but has binary magic bytes - this is a mismatch!
                        metadata['magic_byte_mismatch'] = True
                        metadata['expected_type'] = 'Text'
                        metadata['detected_type'] = detected_type
                    else:
                        metadata['magic_byte_mismatch'] = False

                # Owner information
                owner_info = self.get_file_owner(filepath)
                metadata.update(owner_info)

                # Timestamps
                timestamps = self.get_file_timestamps(filepath)
                metadata.update(timestamps)

                # Hidden file detection
                file_name = path_obj.name
                is_hidden = False
                try:
                    if platform.system() == 'Windows':
                        if WIN32_AVAILABLE:
                            import win32api
                            import win32con
                            attrs = win32api.GetFileAttributes(filepath)
                            FILE_ATTRIBUTE_HIDDEN = 0x2
                            is_hidden = bool(attrs & FILE_ATTRIBUTE_HIDDEN) or file_name.startswith('.')
                        else:
                            # Fallback: check if filename starts with .
                            is_hidden = file_name.startswith('.')
                    else:
                        # Unix/Linux: hidden files start with .
                        is_hidden = file_name.startswith('.')
                except Exception:
                    # If we can't check, assume not hidden
                    is_hidden = file_name.startswith('.')

                metadata['is_hidden'] = is_hidden
            else:
                # File doesn't exist (deleted)
                metadata['file_exists'] = False

        except Exception as e:
            metadata['metadata_error'] = str(e)

        # Process information (always available)
        process_info = self.get_process_info()
        metadata['process_info'] = process_info

        # Extended metadata collection
        try:
            # Actor information
            actor_info = self.get_actor_info()
            metadata['actor_info'] = actor_info

            # Process tree
            process_tree = self.get_process_tree()
            if process_tree:
                metadata['process_tree'] = process_tree

            # PII detection (only for text files that exist)
            if metadata.get('file_size') and metadata.get('file_extension'):
                pii_result = self.detect_pii(filepath)
                metadata['pii_detection'] = pii_result
                if pii_result.get('is_pii'):
                    metadata['is_pii'] = True
                    metadata['pii_types'] = pii_result.get('pii_types', [])
                    metadata['content_hash_only'] = True
                else:
                    # Not PII - get content changes if this is a modification
                    if event_type in ['modified', 'hash_mismatch'] and old_hash and metadata.get('hash_md5'):
                        new_hash = metadata.get('hash_md5')
                        if old_hash != new_hash:
                            # Try to get old content from cache
                            old_content = None
                            if filepath in self.content_cache:
                                cached = self.content_cache.get(filepath, {})
                                if cached.get('hash') == old_hash:
                                    old_content = cached.get('content')

                            content_changes = self.get_content_changes(filepath, old_hash, new_hash, old_content)
                            if content_changes:
                                metadata['content_changes'] = content_changes

                            # Update cache with new content (for next modification)
                            self._update_content_cache(filepath, new_hash)
                    elif event_type == 'created':
                        # Cache initial content for new files
                        if metadata.get('hash_md5'):
                            self._update_content_cache(filepath, metadata['hash_md5'])

            # Auth and security logs (only collect for significant events)
            if event_type in ['created', 'modified', 'deleted', 'hash_mismatch']:
                try:
                    auth_logs = self.get_recent_auth_logs(15)
                    if auth_logs:
                        metadata['auth_logs'] = auth_logs
                except Exception:
                    pass

                try:
                    security_logs = self.get_security_logs(10)
                    if security_logs:
                        metadata['security_logs'] = security_logs
                except Exception:
                    pass
        except Exception:
            pass

        return metadata
    
    def scan_folder(self, folder_path: str, include_hidden: bool = True) -> List[Dict]:
        """
        Scan a folder and calculate hashes for all files (including hidden files)

        Args:
            folder_path: Path to folder to scan
            include_hidden: Include hidden files (default: True)

        Returns:
            List of dictionaries with file information
        """
        folder = Path(folder_path)
        if not folder.exists() or not folder.is_dir():
            print(f"❌ Error: Folder not found: {folder_path}")
            return []

        print(f"📁 Scanning folder: {folder_path} {'(including hidden files)' if include_hidden else ''}")

        files_data = []
        processed_count = 0
        hidden_count = 0

        try:
            for file_path in folder.rglob("*"):
                if not file_path.is_file():
                    continue

                try:
                    # Check if file is hidden
                    is_hidden = False
                    file_name = file_path.name

                    if platform.system() == 'Windows':
                        # Windows: check hidden attribute
                        try:
                            import stat
                            attrs = file_path.stat().st_file_attributes if hasattr(file_path.stat(), 'st_file_attributes') else 0
                            FILE_ATTRIBUTE_HIDDEN = 0x2
                            is_hidden = bool(attrs & FILE_ATTRIBUTE_HIDDEN) or file_name.startswith('.')
                        except:
                            # Fallback: check if name starts with dot
                            is_hidden = file_name.startswith('.')
                    else:
                        # Unix/Linux/Mac: files starting with dot are hidden
                        is_hidden = file_name.startswith('.')

                    # Skip hidden files if include_hidden is False
                    if is_hidden and not include_hidden:
                        continue

                    if is_hidden:
                        hidden_count += 1

                    abs_path = str(file_path.resolve())

                    print(f"  [FILE] Processing: {file_path.name}{' (hidden)' if is_hidden else ''}", end='\r')

                    # Collect comprehensive metadata
                    file_metadata = self.collect_file_metadata(abs_path, event_type='scan')
                    if file_metadata.get('hash_md5'):
                        file_metadata['is_hidden'] = is_hidden
                        files_data.append(file_metadata)
                        processed_count += 1
                except Exception as e:
                    print(f"\n[WARNING]  Warning: Error processing {file_path}: {e}")
                    continue

            print(f"\n[OK] Scanned {processed_count} files ({hidden_count} hidden)")
            return files_data

        except Exception as e:
            print(f"\n❌ Error scanning folder: {e}")
            return []
    
    def upload_files(self, files_data: List[Dict], batch_size: int = 100) -> Dict:
        """
        Upload file hashes to the server
        
        Args:
            files_data: List of file information dictionaries
            batch_size: Number of files to upload per batch
            
        Returns:
            Response dictionary with results
        """
        if not files_data:
            return {"processed": 0, "errors": [], "success": []}
        
        print(f"\n📤 Uploading {len(files_data)} file hashes to server...")
        
        upload_url = f"{self.server_url}/api/upload/hashes"
        
        results = {
            "processed": 0,
            "errors": [],
            "success": []
        }
        
        # Upload in batches
        total_batches = (len(files_data) + batch_size - 1) // batch_size
        
        for i in range(0, len(files_data), batch_size):
            raw_batch = files_data[i:i + batch_size]
            # Normalize payload to include metadata separately (server expects "metadata" object)
            batch = []
            for item in raw_batch:
                # Make a shallow copy so we don't mutate original
                meta = dict(item) if isinstance(item, dict) else {}
                path = meta.pop("path", None)
                file_hash = meta.pop("hash_md5", None)
                file_size = meta.get("file_size")
                event_type = meta.pop("event_type", None)
                
                payload = {
                    "path": path,
                    "hash_md5": file_hash,
                    "file_size": file_size,
                }
                if event_type:
                    payload["event_type"] = event_type
                # Remaining fields go into metadata
                payload["metadata"] = meta
                batch.append(payload)
            
            batch_num = (i // batch_size) + 1
            
            print(f"  [BOX] Uploading batch {batch_num}/{total_batches} ({len(batch)} files)...", end='\r')
            
            try:
                response = self.session.post(
                    upload_url,
                    json={"files": batch},
                    timeout=300  # 5 minute timeout for large batches
                )
                
                if response.status_code == 200:
                    result = response.json()
                    results["processed"] += result.get("processed", 0)
                    results["errors"].extend(result.get("errors", []))
                    results["success"].extend(result.get("success", []))
                else:
                    error_msg = f"Batch {batch_num}: Server error {response.status_code}"
                    results["errors"].append(error_msg)
                    print(f"\n  ❌ Error uploading batch {batch_num}: {response.status_code}")
                    if response.text:
                        try:
                            error_data = response.json()
                            print(f"     Error: {error_data.get('error', response.text[:200])}")
                        except:
                            print(f"     Response: {response.text[:200]}")
            except requests.exceptions.Timeout:
                error_msg = f"Batch {batch_num}: Upload timeout"
                results["errors"].append(error_msg)
                print(f"\n  ⏱️  Timeout uploading batch {batch_num}")
            except Exception as e:
                error_msg = f"Batch {batch_num}: {str(e)}"
                results["errors"].append(error_msg)
                print(f"\n  ❌ Error uploading batch {batch_num}: {e}")
        
        print(f"\n[OK] Upload complete!")
        print(f"   Processed: {results['processed']} files")
        print(f"   Errors: {len(results['errors'])}")
        print(f"   Success: {len(results['success'])}")
        
        if results["errors"]:
            print(f"\n[WARNING]  First 5 errors:")
            for error in results["errors"][:5]:
                print(f"   - {error}")
        
        return results
    
    def _send_event_alert(self, filepath: str, old_hash: Optional[str], new_hash: Optional[str], event_type: str, metadata: Optional[Dict] = None):
        """
        Send file event alert directly to server
        
        Args:
            filepath: Path to the file
            old_hash: Previous hash (None for created files)
            new_hash: Current hash (None for deleted files)
            event_type: Type of event (created, modified, deleted, hash_mismatch)
            metadata: Optional metadata dictionary to include
        """
        try:
            # For deleted files, we can't resolve the path (file doesn't exist)
            # So we use the path as-is or try to normalize it
            try:
                abs_path = str(Path(filepath).resolve()).replace('\\', '/')
            except (OSError, ValueError):
                # File doesn't exist (deleted), use path as-is
                abs_path = str(filepath).replace('\\', '/')
            
            alert_data = {
                "path": abs_path,
                "initial_hash": old_hash or "unknown",
                "current_hash": new_hash,
                "alert_type": event_type
            }
            
            # Add metadata if provided
            if metadata:
                alert_data["metadata"] = metadata
            
            # Send alert to server via dedicated endpoint
            try:
                response = self.session.post(
                    f"{self.server_url}/api/upload/event",
                    json=alert_data,
                    timeout=10
                )
                
                if response.status_code == 200:
                    try:
                        file_name = Path(filepath).name if Path(filepath).exists() else (Path(abs_path).name if abs_path else "unknown")
                    except:
                        file_name = abs_path.split('/')[-1] if abs_path else "unknown"
                    print(f"  📢 Event: {event_type.upper()} - {file_name}")
                elif response.status_code == 404:
                    # Endpoint not found - might need server restart
                    print(f"  [WARNING]  Failed to send {event_type} event: Endpoint not found (404)")
                    print(f"     Make sure server is running and has been restarted after update")
                    print(f"     URL: {self.server_url}/api/upload/event")
                else:
                    error_msg = response.text[:200] if response.text else f"Status {response.status_code}"
                    print(f"  [WARNING]  Failed to send {event_type} event: {response.status_code} - {error_msg}")
            except requests.exceptions.RequestException as e:
                print(f"  [WARNING]  Error sending {event_type} event to server: {e}")
                print(f"     URL: {self.server_url}/api/upload/event")
        
        except Exception as e:
            print(f"[WARNING]  Error sending alert: {e}")
    
    def _load_hash_cache(self) -> Dict[str, str]:
        """Load local hash cache from file"""
        cache_file = self.config_path.parent / "hash_cache.json"
        if cache_file.exists():
            try:
                with open(cache_file, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def _save_hash_cache(self, cache: Dict[str, str]):
        """Save local hash cache to file"""
        cache_file = self.config_path.parent / "hash_cache.json"
        try:
            with open(cache_file, 'w') as f:
                json.dump(cache, f, indent=2)
        except Exception as e:
            print(f"[WARNING]  Warning: Could not save hash cache: {e}")
    
    def scan_folder_changes(self, folder_path: str, last_hashes: Dict[str, str]) -> tuple:
        """
        Scan folder and return only changed/new files
        
        Args:
            folder_path: Path to folder to scan
            last_hashes: Dictionary of path -> hash from last scan
            
        Returns:
            Tuple of (changed_files_list, current_hashes_dict)
        """
        folder = Path(folder_path)
        if not folder.exists() or not folder.is_dir():
            return [], {}
        
        changed_files = []
        current_hashes = {}
        
        try:
            for file_path in folder.rglob("*"):
                if not file_path.is_file():
                    continue
                
                try:
                    abs_path = str(file_path.resolve())
                    
                    # Collect metadata
                    file_metadata = self.collect_file_metadata(abs_path, event_type='scan')
                    file_hash = file_metadata.get('hash_md5')
                    if not file_hash:
                        continue
                    
                    current_hashes[abs_path] = file_hash
                    
                    # Check if file is new or changed
                    last_hash = last_hashes.get(abs_path)
                    if last_hash != file_hash:
                        changed_files.append(file_metadata)
                except Exception:
                    continue
            
            return changed_files, current_hashes
            
        except Exception as e:
            print(f"[WARNING]  Error scanning folder: {e}")
            return [], {}
    
    def run(self, paths: List[str], continuous: bool = False, interval: int = 60):
        """
        Main method to scan and upload files from specified paths (folders or individual files)

        Args:
            paths: List of file or folder paths to scan
            continuous: If True, run continuously and monitor for changes
            interval: Seconds between scans when running continuously
        """
        print("🚀 FIMonacci Client Starting...\n")
        print(f"🆔 Client ID: {self.client_id[:16]}...")
        print(f"💻 Hostname: {self.hostname}\n")

        if not paths:
            print("❌ Error: No paths specified to scan")
            return

        # Separate files and folders
        folders = []
        individual_files = []

        for path_str in paths:
            path = Path(path_str)
            if path.is_file():
                individual_files.append(str(path.resolve()))
            elif path.is_dir():
                folders.append(str(path.resolve()))
            else:
                print(f"[WARNING]  Warning: Path not found or not accessible: {path_str}")

        if folders:
            print(f"📂 Monitoring folder(s):")
            for folder in folders:
                print(f"   - {folder}")
        if individual_files:
            print(f"[FILE] Monitoring individual file(s):")
            for file in individual_files:
                print(f"   - {file}")
        print()

        # Load hash cache
        hash_cache = self._load_hash_cache()

        # Initial scan and upload
        print("🔍 Performing initial scan...")
        all_files_data = []
        all_current_hashes = {}

        # Scan folders
        for folder in folders:
            files_data = self.scan_folder(folder)
            all_files_data.extend(files_data)
            # Build hash cache from initial scan
            for file_data in files_data:
                all_current_hashes[file_data['path']] = file_data['hash_md5']

        # Scan individual files
        for file_path in individual_files:
            try:
                print(f"  [FILE] Processing file: {Path(file_path).name}")
                file_metadata = self.collect_file_metadata(file_path, event_type='scan')
                if file_metadata.get('hash_md5'):
                    all_files_data.append(file_metadata)
                    all_current_hashes[file_path] = file_metadata['hash_md5']
            except Exception as e:
                print(f"[WARNING]  Warning: Error processing {file_path}: {e}")

        if all_files_data:
            print("\n📤 Uploading initial file hashes...")
            self.upload_files(all_files_data)
            hash_cache.update(all_current_hashes)
            self._save_hash_cache(hash_cache)
        else:
            print("[WARNING]  No files found to upload")

        if not continuous:
            print("\n[OK] Initial scan complete. Use --continuous flag to monitor for changes.")
            return

        # Continuous monitoring with watchdog
        print(f"\n🔄 Starting real-time monitoring with watchdog...")
        print("   Press Ctrl+C to stop\n")

        # Create event handler
        event_handler = FIMFileEventHandler(self, hash_cache)
        observer = Observer()

        # Schedule watching for each folder
        for folder in folders:
            folder_path = Path(folder)
            if folder_path.exists() and folder_path.is_dir():
                observer.schedule(event_handler, str(folder_path), recursive=True)
                print(f"   [EYE]  Watching folder: {folder}")

        # Schedule watching for individual files (watch parent directory)
        watched_parents = set()
        for file_path in individual_files:
            file_obj = Path(file_path)
            if file_obj.exists() and file_obj.is_file():
                parent_dir = file_obj.parent
                if str(parent_dir) not in watched_parents and parent_dir not in [Path(f) for f in folders]:
                    observer.schedule(event_handler, str(parent_dir), recursive=False)
                    watched_parents.add(str(parent_dir))
                    print(f"   [EYE]  Watching file: {file_obj.name}")

        # Start observer
        observer.start()
        print("   [OK] Watchdog started - monitoring file system events in real-time\n")
        
        running = True
        stop_event = threading.Event()
        
        def heartbeat_loop():
            while not stop_event.is_set():
                self._send_heartbeat()
                # Send heartbeat every 5 seconds for fast liveness
                stop_event.wait(5)
        
        def signal_handler(sig, frame):
            nonlocal running
            print("\n\n[WARNING]  Stopping monitor...")
            running = False
            observer.stop()
            stop_event.set()
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Start heartbeat thread
        hb_thread = threading.Thread(target=heartbeat_loop, daemon=True)
        hb_thread.start()
        
        try:
            # Keep running and periodically save cache
            while running:
                time.sleep(10)  # Save cache every 10 seconds
                self._save_hash_cache(hash_cache)
        except KeyboardInterrupt:
            pass
        finally:
            observer.stop()
            observer.join()
            stop_event.set()
            hb_thread.join(timeout=2)
            self._save_hash_cache(hash_cache)
        
        print("\n[OK] Monitoring stopped")




def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="FIMonacci Client - Scan local files and upload to server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Scan specific folder
  python client.py -u http://localhost:5000 -p /path/to/folder
  
  # Scan multiple folders
  python client.py -u http://localhost:5000 -p /home/user/docs -p /home/user/pics
  
  # Remote server
  python client.py -u https://your-server.com -p /var/www/html

Note: 
  - Client ID and hostname are automatically generated and saved
  - No registration or token required - everything is automatic!
        """
    )
    
    parser.add_argument(
        '-u', '--url',
        required=True,
        help='FIMonacci server URL (e.g., http://localhost:5000)'
    )
    
    parser.add_argument(
        '-p', '--path',
        action='append',
        required=True,
        help='File or folder path to monitor (can be used multiple times for multiple paths)'
    )
    
    parser.add_argument(
        '-c', '--continuous',
        action='store_true',
        help='Run continuously and monitor for file changes'
    )
    
    parser.add_argument(
        '-i', '--interval',
        type=int,
        default=60,
        help='Interval in seconds between scans when running continuously (default: 60)'
    )
    
    args = parser.parse_args()
    
    # Validate server URL
    if not args.url:
        print("❌ Error: Server URL is required. Use -u or --url")
        parser.print_help()
        sys.exit(1)
    
    # Ensure URL has a scheme (http:// or https://)
    if not args.url.startswith('http://') and not args.url.startswith('https://'):
        # Auto-add http:// if missing
        args.url = f'http://{args.url}'
        print(f"[WARNING]  URL scheme missing, using: {args.url}")
    
    # Validate paths
    if not args.path:
        print("❌ Error: At least one folder path is required. Use -p or --path")
        parser.print_help()
        sys.exit(1)
    
    # Validate folders exist
    for folder_path in args.path:
        # Normalize Windows paths (handle backslashes in Git Bash)
        if platform.system() == 'Windows':
            # Replace forward slashes with backslashes, or use os.path.normpath
            folder_path = os.path.normpath(folder_path)
        
        folder = Path(folder_path)
        if not folder.exists():
            print(f"❌ Error: Folder does not exist: {folder_path}")
            print(f"   (Tried: {os.path.abspath(folder_path)})")
            sys.exit(1)
        if not folder.is_dir():
            print(f"❌ Error: Not a directory: {folder_path}")
            sys.exit(1)
    
    # Create client and run (automatically creates client ID and registers)
    try:
        print(f"🚀 Connecting to server: {args.url}")
        client = FIMonacciClient(server_url=args.url)
        print(f"[OK] Connected successfully!\n")
    except Exception as e:
        print(f"❌ Error connecting to server: {e}")
        print(f"   Make sure the server is running at {args.url}")
        sys.exit(1)
    
    # Run scan and upload
    try:
        client.run(args.path, continuous=args.continuous, interval=args.interval)
    except KeyboardInterrupt:
        print("\n\n[WARNING]  Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

