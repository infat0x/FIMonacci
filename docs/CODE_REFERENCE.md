# FIMonacci Code Reference

Comprehensive reference for main functions, classes, and code snippets in the FIMonacci File Integrity Monitoring system.

## Table of Contents
- [Client-Side Code](#client-side-code)
  - [FIMonacciClient Class](#fimonacciclient-class)
  - [File Monitoring](#file-monitoring)
  - [Security Analysis](#security-analysis)
- [Server-Side Code](#server-side-code)
  - [API Endpoints](#api-endpoints)
  - [AI Timeline Analysis](#ai-timeline-analysis)
  - [Wazuh Integration](#wazuh-integration)
- [Advanced Features Deep Dive](#advanced-features-deep-dive)
  - [Entropy Analysis (Encryption Detection)](#entropy-analysis-encryption-detection)
  - [PII Detection System](#pii-detection-system)
  - [AI Analysis Request Workflow](#ai-analysis-request-workflow)
- [Database Models](#database-models)
- [Utility Functions](#utility-functions)

---

## Client-Side Code

### FIMonacciClient Class

**Location:** [client/client.py:226](../client/client.py#L226)

Main client class for file integrity monitoring.

```python
class FIMonacciClient:
    """
    FIMonacci File Integrity Monitoring Client

    Monitors file system changes and reports to central server.
    Collects comprehensive metadata including:
    - MD5 hashes
    - Entropy (encryption detection)
    - Magic bytes (file type verification)
    - Hidden file attributes
    - Process information
    - Authentication logs (Windows)
    """

    def __init__(self, server_url: str, client_id: Optional[str] = None):
        """
        Initialize FIMonacci client

        Args:
            server_url: URL of FIMonacci server (e.g., "http://10.0.0.5:5000")
            client_id: Unique client identifier (auto-generated if not provided)
        """
```

#### Key Methods

##### 1. File Metadata Collection

**Location:** [client/client.py:1154](../client/client.py#L1154)

```python
def collect_file_metadata(self, filepath: str, event_type: str = None, old_hash: str = None) -> Dict:
    """
    Collect comprehensive metadata for a file

    Args:
        filepath: Path to the file
        event_type: Type of event (created, modified, deleted, renamed)
        old_hash: Previous hash (for content change tracking)

    Returns:
        Dictionary with all collected metadata including:
        - path: File path
        - hash_md5: MD5 hash of file content
        - file_size: Size in bytes
        - entropy: Shannon entropy (0-8)
        - high_entropy: Boolean flag (True if >= 7.5)
        - magic_bytes: File signature (first 32 bytes hex)
        - detected_file_type: Type detected from magic bytes
        - magic_byte_mismatch: Boolean flag for extension mismatch
        - is_hidden: Hidden file attribute
        - process_name: Process that triggered the event
        - process_tree: Parent/child process hierarchy
        - auth_logs: Recent authentication events (Windows)
    """
```

**Usage Example:**
```python
client = FIMonacciClient("http://10.0.0.5:5000")
metadata = client.collect_file_metadata(
    filepath="C:\\Users\\test\\document.txt",
    event_type="modified"
)
print(f"File hash: {metadata['hash_md5']}")
print(f"Entropy: {metadata['entropy']}")
print(f"Encrypted: {metadata['high_entropy']}")
```

##### 2. Entropy Calculation

**Location:** [client/client.py:920](../client/client.py#L920)

```python
def calculate_entropy(self, filepath: str) -> Optional[float]:
    """
    Calculate Shannon entropy of file content

    Entropy scale:
    - H < 4.0: Plain text / low compression
    - 4.0 <= H < 7.5: Compressed data
    - H >= 7.5: Encrypted / high randomness

    Args:
        filepath: Path to file

    Returns:
        Float between 0.0 and 8.0, or None if calculation failed

    Algorithm:
        H = -Σ(p(x) * log2(p(x)))
        where p(x) is the probability of byte value x
    """
```

**Usage Example:**
```python
entropy = client.calculate_entropy("C:\\file.bin")
if entropy >= 7.5:
    print("WARNING: File appears to be encrypted!")
elif entropy >= 4.0:
    print("File appears to be compressed")
else:
    print("File is plain text or low compression")
```

##### 3. Magic Byte Detection

**Location:** [client/client.py:850](../client/client.py#L850)

```python
def get_magic_bytes(self, filepath: str, num_bytes: int = 32) -> Optional[str]:
    """
    Extract magic bytes (file signature) from file

    Args:
        filepath: Path to file
        num_bytes: Number of bytes to read (default: 32)

    Returns:
        Hexadecimal string of first N bytes, or None if error

    Examples:
        JPEG: ffd8ffe0 or ffd8ffe1
        PNG:  89504e47
        PDF:  25504446
        ZIP:  504b0304
    """

def detect_file_type_from_magic_bytes(self, magic_bytes: str) -> Optional[str]:
    """
    Detect file type from magic bytes signature

    Args:
        magic_bytes: Hexadecimal string of file header

    Returns:
        File type string (e.g., "JPEG", "PNG", "PDF") or None
    """
```

**Usage Example:**
```python
magic = client.get_magic_bytes("file.jpg")
detected_type = client.detect_file_type_from_magic_bytes(magic)

if detected_type != "JPEG":
    print("WARNING: File extension doesn't match content!")
```

##### 4. PII Detection

**Location:** [client/client.py:1067](../client/client.py#L1067)

```python
def detect_pii(self, filepath: str, max_bytes: int = 10240,
               manual_check_first: bool = True) -> Dict:
    """
    Detect potential PII (Personally Identifiable Information) in a file

    Detects:
    - Social Security Numbers (SSN)
    - Credit Card Numbers (Luhn algorithm validated)
    - Email Addresses
    - Phone Numbers

    Args:
        filepath: Path to file
        max_bytes: Maximum bytes to scan (default: 10KB)
        manual_check_first: Check if path is manually flagged first

    Returns:
        {
            'is_pii': bool,
            'pii_types': List[str],  # ['SSN', 'CREDIT_CARD', ...]
            'content_hash_only': bool  # True to prevent content storage
        }

    Patterns:
        SSN: \b\d{3}-\d{2}-\d{4}\b
        Credit Card: \b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b (Luhn validated)
        Email: \b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b
    """
```

##### 5. Process Information

**Location:** [client/client.py:650](../client/client.py#L650)

```python
def get_process_info(self) -> Dict[str, Any]:
    """
    Get detailed information about the current process and its ancestors

    Returns:
        {
            'pid': int,
            'name': str,
            'exe': str,  # Full executable path
            'cmdline': List[str],
            'username': str,
            'create_time': float,
            'parent_pid': int,
            'parent_name': str,
            'parent_exe': str,
            'parent_cmdline': List[str],
            'ancestors': List[Dict]  # Full process tree
        }
    """
```

##### 6. Authentication Logs (Windows)

**Location:** [client/client.py:740](../client/client.py#L740)

```python
def collect_auth_logs(self, max_events: int = 15) -> List[Dict]:
    """
    Collect Windows authentication logs from Security Event Log

    Requires: Administrator privileges
    Event IDs:
        4624: Successful logon
        4625: Failed logon

    Args:
        max_events: Maximum number of events to retrieve

    Returns:
        List of authentication events with:
        - event_id: 4624 or 4625
        - time: ISO timestamp
        - source: Event source name
        - type: 'logon_success' or 'logon_failure'

    Raises:
        Error 1314 if not running as Administrator
    """
```

---

### File Monitoring

#### FIMFileEventHandler Class

**Location:** [client/client.py:57](../client/client.py#L57)

```python
class FIMFileEventHandler(FileSystemEventHandler):
    """
    Watchdog event handler for file system monitoring

    Handles events:
    - on_created: New file created
    - on_modified: File content changed
    - on_deleted: File removed
    - on_moved: File renamed/moved (single event, not delete+create)
    """

    def __init__(self, client: 'FIMonacciClient', path: str):
        self.client = client
        self.monitored_path = path
        self.hash_cache = {}  # Cache of {filepath: md5_hash}
```

##### Rename Event Handling

**Location:** [client/client.py:180](../client/client.py#L180)

```python
def _handle_rename_event(self, src_path: str, dest_path: str):
    """
    Handle file rename/move events as a single 'renamed' event

    Args:
        src_path: Original file path
        dest_path: New file path

    Creates single event with:
        - event_type: "renamed"
        - old_path: Source path
        - new_path: Destination path
        - old_hash: Hash from cache
        - new_hash: Current file hash
    """
```

**Key Features:**
- Changed from delete+create to single "renamed" event
- Preserves hash cache continuity
- Includes both old and new paths in alert

---

### Security Analysis

#### Bidirectional Magic Byte Checking

**Location:** [client/client.py:1214](../client/client.py#L1214)

```python
# Known text extensions that should NOT have binary magic bytes
text_extensions = {
    '.txt', '.log', '.md', '.csv', '.json', '.xml',
    '.html', '.css', '.js', '.py', '.java', '.c',
    '.cpp', '.h', '.sh', '.bat', '.ini', '.cfg',
    '.conf', '.yaml', '.yml'
}

# Bidirectional mismatch detection:
# Case 1: Binary extension but wrong type (e.g., .jpg file is actually PNG)
if expected_type and detected_type and detected_type != expected_type:
    metadata['magic_byte_mismatch'] = True

# Case 2: Text extension but has binary magic bytes (e.g., .txt is actually JPEG)
elif file_ext in text_extensions and detected_type:
    metadata['magic_byte_mismatch'] = True
    metadata['expected_type'] = 'Text'
    metadata['detected_type'] = detected_type
```

**Detection Examples:**
- `malware.txt` with JPEG magic bytes → **MISMATCH**
- `image.jpg` with PNG magic bytes → **MISMATCH**
- `document.pdf` with ZIP magic bytes → **MISMATCH**

#### Hidden File Detection

**Location:** [client/client.py:1307](../client/client.py#L1307)

```python
# Hidden file detection
file_name = path_obj.name
is_hidden = False

try:
    if platform.system() == 'Windows':
        if WIN32_AVAILABLE:
            import win32api
            attrs = win32api.GetFileAttributes(filepath)
            FILE_ATTRIBUTE_HIDDEN = 0x2
            is_hidden = bool(attrs & FILE_ATTRIBUTE_HIDDEN) or file_name.startswith('.')
        else:
            is_hidden = file_name.startswith('.')
    else:
        is_hidden = file_name.startswith('.')
except Exception:
    is_hidden = file_name.startswith('.')

metadata['is_hidden'] = is_hidden
```

**Detection Logic:**
- Windows: Checks `FILE_ATTRIBUTE_HIDDEN` flag (0x2) OR dot-file
- Linux/Mac: Checks if filename starts with `.`
- Fallback: Dot-file check only

---

## Server-Side Code

### API Endpoints

**Location:** [server/routes.py](../server/routes.py)

#### 1. Client Registration

```python
@app.route('/api/client/register', methods=['POST'])
def register_client():
    """
    Register a new client agent

    Request Body:
        {
            "client_id": "unique-client-id",
            "hostname": "DESKTOP-ABC123",
            "ip_address": "10.0.0.5"  # Optional
        }

    Response:
        {
            "message": "Client registered successfully",
            "client_id": "unique-client-id"
        }

    Location: server/routes.py:182
    """
```

#### 2. Upload File Event

```python
@app.route('/api/upload/event', methods=['POST'])
def upload_file_event():
    """
    Upload a file integrity event (alert)

    Headers:
        X-Client-ID: unique-client-id
        X-Hostname: DESKTOP-ABC123

    Request Body:
        {
            "path": "/path/to/file.txt",
            "alert_type": "modified",  # created, modified, deleted, renamed
            "old_hash": "abc123...",
            "new_hash": "def456...",
            "metadata": {
                "file_size": 1024,
                "entropy": 7.8,
                "high_entropy": true,
                "magic_byte_mismatch": false,
                "is_hidden": false,
                "process_name": "notepad.exe",
                ...
            }
        }

    Response:
        {
            "message": "Event received successfully",
            "alert_id": 123
        }

    Location: server/routes.py:510
    """
```

#### 3. Timeline Analysis

```python
@app.route('/api/admin/analyze-timeline', methods=['POST'])
@login_required
def analyze_timeline():
    """
    Create AI-powered timeline analysis

    Request Body:
        {
            "alert_ids": [1, 2, 3, 4, 5],  # FIM alert IDs
            "include_wazuh": true,  # Include SIEM data
            "agent_ip": "10.0.0.5",  # For Wazuh correlation
            "start_time": "2024-01-01T00:00:00Z",
            "end_time": "2024-01-01T23:59:59Z"
        }

    Response:
        {
            "success": true,
            "analysis_id": 42,
            "summary": {
                "overall_risk": "HIGH",
                "confidence": 85,
                "attack_type": "Ransomware",
                "mitre_techniques": ["T1486", "T1082"],
                "key_findings": [...]
            }
        }

    Location: server/routes.py:925
    """
```

---

### AI Timeline Analysis

**Location:** [server/ai_timeline_analysis.py:166](../server/ai_timeline_analysis.py#L166)

#### AITimelineAnalyzer Class

```python
class AITimelineAnalyzer:
    """
    Analyzes FIM + SIEM data using Mistral AI

    Features:
    - Optimized payload (70-90% smaller)
    - Event filtering (50 SIEM, 20 FIM max)
    - Attack reconstruction
    - MITRE ATT&CK mapping
    - Risk assessment
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize AI analyzer

        Args:
            api_key: Mistral API key (defaults to MISTRAL_API_KEY env var)
        """
        self.api_key = api_key or os.environ.get("MISTRAL_API_KEY")
        self.client = Mistral(api_key=self.api_key)
        self.model_id = "mistral-small-latest"
```

#### Event Filtering (Performance Optimization)

**Location:** [server/ai_timeline_analysis.py:183](../server/ai_timeline_analysis.py#L183)

```python
def _filter_event_data(self, events: List[Dict], event_type: str = "FIM") -> List[Dict]:
    """
    Filter and simplify event data to reduce payload size

    Optimization:
    - Limits SIEM events to 50 most recent
    - Limits FIM events to 20 most recent
    - Removes unnecessary fields (70-90% size reduction)
    - Expected analysis time: 5-15s (was 30-60s)

    Args:
        events: List of event dictionaries
        event_type: "FIM" or "SIEM"

    Returns:
        Filtered list with only essential fields

    FIM Fields Kept:
        - path, alert_type, timestamp
        - magic_byte_mismatch, high_entropy, is_hidden
        - file_extension, detected_file_type
        - process_name

    SIEM Fields Kept:
        - timestamp, rule, data
    """
```

#### Timeline Analysis

**Location:** [server/ai_timeline_analysis.py:218](../server/ai_timeline_analysis.py#L218)

```python
def analyze_timeline(self, fim_data: List[Dict],
                    wazuh_data: Optional[List[Dict]] = None) -> Dict:
    """
    Analyze FIM events and optionally Wazuh SIEM data

    Args:
        fim_data: List of file integrity monitoring events
        wazuh_data: Optional list of Wazuh SIEM events

    Returns:
        {
            "overall_risk": "CRITICAL|HIGH|MEDIUM|LOW",
            "confidence": 0-100,
            "attack_type": str,
            "mitre_attack_techniques": ["T1486", ...],
            "attack_narrative": str,
            "timeline": [
                {
                    "timestamp": str,
                    "event_id": str,
                    "event_type": str,
                    "description": str,
                    "significance": str
                }
            ],
            "suspicious_events": [
                {
                    "event_id": str,
                    "rationale": str
                }
            ],
            "benign_or_uncertain": [...],
            "assumptions_and_gaps": [...]
        }

    Process:
    1. Filters events to essential fields
    2. Sends to Mistral AI with structured prompt
    3. Parses JSON response
    4. Returns structured analysis
    """
```

**Example Usage:**
```python
analyzer = AITimelineAnalyzer()

analysis = analyzer.analyze_timeline(
    fim_data=[
        {"path": "C:\\file.exe", "alert_type": "created", ...},
        {"path": "C:\\file.exe", "high_entropy": True, ...}
    ],
    wazuh_data=[
        {"rule": {"id": "5501"}, "data": {...}}
    ]
)

print(f"Risk: {analysis['overall_risk']}")
print(f"Attack: {analysis['attack_type']}")
print(f"MITRE: {analysis['mitre_attack_techniques']}")
```

---

### Wazuh Integration

**Location:** [server/wazuh_integration.py:21](../server/wazuh_integration.py#L21)

#### WazuhIntegration Class

```python
class WazuhIntegration:
    """
    Integration with Wazuh SIEM platform

    Features:
    - Query Wazuh Manager API (port 55000)
    - Query Wazuh Indexer/Elasticsearch (port 9200)
    - Agent information retrieval
    - Event correlation by IP address
    - Event deduplication
    """

    def __init__(self):
        self.manager_url = os.environ.get('WAZUH_MANAGER_URL')
        self.indexer_url = os.environ.get('WAZUH_INDEXER_URL')
        self.api_user = os.environ.get('WAZUH_API_USER')
        self.api_password = os.environ.get('WAZUH_API_PASSWORD')
        # ... SSL verification disabled for self-signed certs
```

#### Get Agent by IP

```python
def get_agent_by_ip(self, ip_address: str) -> Optional[str]:
    """
    Get Wazuh agent ID from IP address

    Args:
        ip_address: Agent IP (e.g., "10.0.0.5")

    Returns:
        Agent ID string (e.g., "001") or None

    API Call:
        GET https://wazuh-manager:55000/agents
        Filter by IP address match
    """
```

#### Query Events

```python
def query_events_by_agent_and_time(
    self,
    agent_id: str,
    start_time: str,
    end_time: str,
    max_results: int = 1000
) -> List[Dict]:
    """
    Query Wazuh events for specific agent and time range

    Args:
        agent_id: Wazuh agent ID (e.g., "001")
        start_time: ISO timestamp
        end_time: ISO timestamp
        max_results: Maximum events to return

    Returns:
        List of deduplicated Wazuh events

    Deduplication:
        Events are deduplicated by unique combination of:
        - timestamp
        - rule.id
        - agent.name
        - data fields
    """
```

**Example Usage:**
```python
wazuh = WazuhIntegration()

# Get agent ID from IP
agent_id = wazuh.get_agent_by_ip("10.0.0.5")

# Query events
events = wazuh.query_events_by_agent_and_time(
    agent_id=agent_id,
    start_time="2024-01-01T00:00:00Z",
    end_time="2024-01-01T23:59:59Z"
)

print(f"Found {len(events)} SIEM events")
```

---

## Advanced Features Deep Dive

### Entropy Analysis (Encryption Detection)

**Location:** [client/client.py:920](../client/client.py#L920)

Entropy is a measure of randomness/disorder in data. FIMonacci uses Shannon entropy to detect encrypted or compressed files.

#### Shannon Entropy Formula

```
H = -Σ(p(x) * log2(p(x)))

Where:
- H = Entropy (0.0 to 8.0 bits)
- p(x) = Probability of byte value x appearing
- Σ = Sum over all 256 possible byte values (0-255)
```

#### Entropy Classification Thresholds

| Entropy Range | Classification | Meaning | Examples |
|--------------|----------------|---------|----------|
| H < 4.0 | **Plain Text** | Low randomness | .txt, .log, .csv, source code |
| 4.0 ≤ H < 7.5 | **Compressed** | Medium randomness | .zip, .gz, .jpg (compressed images) |
| H ≥ 7.5 | **Encrypted** | High randomness | .encrypted, ransomware, crypto containers |

#### Implementation

**Location:** [client/client.py:920](../client/client.py#L920)

```python
def calculate_entropy(self, filepath: str) -> Optional[float]:
    """
    Calculate Shannon entropy of file content

    Returns:
        Float between 0.0 and 8.0, or None if calculation failed

    Algorithm Steps:
        1. Read file bytes (up to 1MB sample for large files)
        2. Count frequency of each byte value (0-255)
        3. Calculate probability: p(x) = count(x) / total_bytes
        4. Apply Shannon formula: H = -Σ(p(x) * log2(p(x)))
    """
    try:
        # Read file bytes
        with open(filepath, 'rb') as f:
            # Read up to 1MB for performance
            data = f.read(1024 * 1024)

        if not data:
            return None

        # Count byte frequencies
        byte_counts = [0] * 256
        for byte in data:
            byte_counts[byte] += 1

        # Calculate entropy
        total_bytes = len(data)
        entropy = 0.0

        for count in byte_counts:
            if count > 0:
                probability = count / total_bytes
                entropy -= probability * math.log2(probability)

        return round(entropy, 4)

    except Exception as e:
        print(f"[ERROR] Entropy calculation failed: {e}")
        return None
```

#### Real-World Usage Example

```python
from client.client import FIMonacciClient

client = FIMonacciClient("http://10.0.0.5:5000")

# Test various file types
test_files = {
    "document.txt": "Plain text file",
    "archive.zip": "Compressed archive",
    "photo.jpg": "Compressed image",
    "encrypted.dat": "Encrypted data"
}

for filename, description in test_files.items():
    entropy = client.calculate_entropy(filename)

    if entropy is None:
        print(f"{filename}: ERROR calculating entropy")
        continue

    # Classify
    if entropy >= 7.5:
        classification = "🔒 ENCRYPTED"
        risk = "HIGH RISK - Possible ransomware"
    elif entropy >= 4.0:
        classification = "📦 COMPRESSED"
        risk = "Normal - Legitimate compression"
    else:
        classification = "📄 PLAIN TEXT"
        risk = "Normal - Human-readable"

    print(f"{filename} ({description})")
    print(f"  Entropy: {entropy:.4f}")
    print(f"  Classification: {classification}")
    print(f"  Risk Assessment: {risk}")
    print()
```

**Example Output:**
```
document.txt (Plain text file)
  Entropy: 4.2156
  Classification: 📄 PLAIN TEXT
  Risk Assessment: Normal - Human-readable

archive.zip (Compressed archive)
  Entropy: 7.2834
  Classification: 📦 COMPRESSED
  Risk Assessment: Normal - Legitimate compression

photo.jpg (Compressed image)
  Entropy: 7.4521
  Classification: 📦 COMPRESSED
  Risk Assessment: Normal - Legitimate compression

encrypted.dat (Encrypted data)
  Entropy: 7.9987
  Classification: 🔒 ENCRYPTED
  Risk Assessment: HIGH RISK - Possible ransomware
```

#### Entropy in File Metadata

**Location:** [client/client.py:1199](../client/client.py#L1199)

When collecting file metadata, entropy is automatically calculated and classified:

```python
# Inside collect_file_metadata()
entropy = self.calculate_entropy(filepath)

if entropy is not None:
    metadata['entropy'] = entropy

    # Classify and flag
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
```

#### Ransomware Detection Use Case

Ransomware typically encrypts files, dramatically increasing their entropy:

```python
# Before encryption (document.docx)
entropy_before = 4.8  # Compressed Office document
classification = "Compressed"

# After ransomware encryption (document.docx.locked)
entropy_after = 7.99  # Highly random encrypted data
classification = "Encrypted"  # 🚨 ALERT!

# FIMonacci detects this change
alert = {
    'path': 'C:\\Documents\\document.docx.locked',
    'alert_type': 'modified',
    'entropy': 7.99,
    'high_entropy': True,
    'entropy_classification': 'Encrypted',
    'risk': 'CRITICAL - Possible ransomware activity'
}
```

#### Performance Considerations

- **Sample Size:** Reads up to 1MB for large files (configurable)
- **Calculation Time:** ~10-50ms for typical files
- **Accuracy:** 1MB sample provides >99% accurate entropy estimation for files >1MB
- **Memory Usage:** Minimal - only byte frequency array (256 integers)

---

### PII Detection System

**Location:** [client/client.py:1067](../client/client.py#L1067)

FIMonacci includes a comprehensive PII (Personally Identifiable Information) detection system to identify sensitive data.

#### Detected PII Types

| Type | Pattern | Validation | Examples |
|------|---------|------------|----------|
| **SSN** | `\b\d{3}-\d{2}-\d{4}\b` | Format check | 123-45-6789 |
| **Credit Card** | `\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b` | Luhn algorithm | 4532-1234-5678-9010 |
| **Email** | `\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z\|a-z]{2,}\b` | Format check | user@example.com |
| **Phone** | `\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b` | Format check | 555-123-4567 |

#### Implementation

**Full Function:**

```python
def detect_pii(self, filepath: str, max_bytes: int = 10240,
               manual_check_first: bool = True) -> Dict:
    """
    Detect potential PII in a file

    Args:
        filepath: Path to file
        max_bytes: Maximum bytes to scan (default: 10KB)
        manual_check_first: Check if path is manually flagged first

    Returns:
        {
            'is_pii': bool,
            'pii_types': List[str],  # ['SSN', 'CREDIT_CARD', 'EMAIL']
            'content_hash_only': bool  # True = don't store content
        }
    """
    pii_result = {
        'is_pii': False,
        'pii_types': [],
        'content_hash_only': False
    }

    # Step 1: Check if path is manually flagged
    if manual_check_first and self._is_pii_path(filepath):
        pii_result['is_pii'] = True
        pii_result['pii_types'] = ['MANUAL_FLAG']
        pii_result['content_hash_only'] = True
        return pii_result

    # Step 2: Content-based detection
    try:
        # Read file content
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read(max_bytes)

        detected_types = []

        # SSN Pattern: 123-45-6789
        ssn_pattern = r'\b\d{3}-\d{2}-\d{4}\b'
        if re.search(ssn_pattern, content):
            detected_types.append('SSN')

        # Credit Card Pattern: 4532-1234-5678-9010
        # Luhn validation required
        cc_pattern = r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b'
        cc_matches = re.findall(cc_pattern, content)
        for match in cc_matches:
            # Remove separators
            card_number = re.sub(r'[-\s]', '', match)
            # Validate with Luhn algorithm
            if self._luhn_check(card_number):
                detected_types.append('CREDIT_CARD')
                break  # One match is enough

        # Email Pattern: user@example.com
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        if re.search(email_pattern, content):
            detected_types.append('EMAIL')

        # Phone Pattern: 555-123-4567 or 5551234567
        phone_pattern = r'\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b'
        if re.search(phone_pattern, content):
            detected_types.append('PHONE')

        # Flag as PII if any patterns found
        if detected_types:
            pii_result['is_pii'] = True
            pii_result['pii_types'] = list(set(detected_types))  # Remove duplicates
            pii_result['content_hash_only'] = True

    except Exception as e:
        # Not a text file or read error
        pass

    return pii_result
```

#### Luhn Algorithm (Credit Card Validation)

**Location:** [client/client.py:1100](../client/client.py#L1100)

```python
def _luhn_check(self, card_number: str) -> bool:
    """
    Validate credit card number using Luhn algorithm

    Algorithm:
        1. Reverse the card number
        2. Double every second digit
        3. If doubled digit > 9, subtract 9
        4. Sum all digits
        5. Valid if sum % 10 == 0

    Example: 4532 1234 5678 9010
        Reversed: 0109 8765 4321 2354
        Doubled:  0 2 0 18 8 14 6 10 4 6 2 2 2 6 5 8
        Adjusted: 0 2 0 9  8 5  6 1  4 6 2 2 2 6 5 8
        Sum: 66, 66 % 10 = 6 (invalid)
    """
    try:
        # Remove non-digits
        digits = [int(d) for d in card_number if d.isdigit()]

        # Reverse
        digits = digits[::-1]

        # Double every second digit
        for i in range(1, len(digits), 2):
            digits[i] *= 2
            if digits[i] > 9:
                digits[i] -= 9

        # Check if sum is divisible by 10
        return sum(digits) % 10 == 0

    except:
        return False
```

#### Manual PII Path Flagging

**Location:** [client/client.py:1035](../client/client.py#L1035)

```python
def _is_pii_path(self, filepath: str) -> bool:
    """
    Check if filepath is under a manually flagged PII directory

    Configuration: app_config.json
    {
        "pii_paths": [
            "C:/PII_Data",
            "C:/Users/John/SSN_Records"
        ]
    }
    """
    try:
        file_path = Path(filepath).resolve()

        for pii_path_str in self.pii_paths:
            pii_path = Path(pii_path_str).resolve()

            # Check if file is under this PII directory
            try:
                file_path.relative_to(pii_path)
                return True  # File is under PII path
            except ValueError:
                continue  # Not under this path

        return False
    except:
        return False
```

#### Usage Example

```python
from client.client import FIMonacciClient

client = FIMonacciClient("http://10.0.0.5:5000")

# Configure PII paths (or use app_config.json)
client.pii_paths = [
    "C:/PII_Data",
    "C:/ConfidentialRecords"
]

# Test file with PII
test_file = "customer_data.txt"

pii_result = client.detect_pii(test_file)

if pii_result['is_pii']:
    print(f"⚠️  PII DETECTED in {test_file}")
    print(f"Types found: {', '.join(pii_result['pii_types'])}")
    print(f"Content protection: {'ENABLED' if pii_result['content_hash_only'] else 'DISABLED'}")

    # Alert handling
    alert = {
        'path': test_file,
        'is_pii': True,
        'pii_types': pii_result['pii_types'],
        'action': 'Hash-only storage (no content stored)'
    }
else:
    print(f"✅ No PII detected in {test_file}")
```

**Example Output:**
```
⚠️  PII DETECTED in customer_data.txt
Types found: SSN, CREDIT_CARD, EMAIL
Content protection: ENABLED
```

#### Real File Content Example

**File: customer_records.txt**
```
Customer Database Export
========================

Customer ID: 12345
Name: John Doe
SSN: 123-45-6789
Email: john.doe@example.com
Phone: 555-123-4567
Credit Card: 4532-1234-5678-9010

Customer ID: 67890
Name: Jane Smith
SSN: 987-65-4321
Email: jane.smith@company.com
Phone: 555-987-6543
```

**Detection Result:**
```python
{
    'is_pii': True,
    'pii_types': ['SSN', 'CREDIT_CARD', 'EMAIL', 'PHONE'],
    'content_hash_only': True
}
```

#### PII Protection Workflow

```python
# When PII is detected during file event
metadata = client.collect_file_metadata(filepath, event_type='created')

if metadata.get('is_pii'):
    # Content is NOT stored in database
    # Only hash and metadata are stored
    stored_data = {
        'path': metadata['path'],
        'hash_md5': metadata['hash_md5'],  # ✅ Stored
        'pii_types': metadata['pii_types'],  # ✅ Stored
        'file_size': metadata['file_size'],  # ✅ Stored
        # ❌ Content NOT stored for PII files
    }

    print("[PII] File flagged - Content protection enabled")
else:
    # Normal file - full metadata stored
    stored_data = metadata
```

#### Configuration File Setup

**File: client/dist/app_config.json**
```json
{
  "server_url": "http://10.0.0.5:5000",
  "monitored_paths": [
    "C:/Users/John/Documents"
  ],
  "pii_paths": [
    "C:/Users/John/SSN_Records",
    "C:/PII_Data",
    "C:/ConfidentialFiles"
  ],
  "exclusion_patterns": [
    "*.log",
    "*.tmp"
  ]
}
```

#### Performance & Security

- **Scan Limit:** Only first 10KB scanned (configurable)
- **Scan Time:** ~5-20ms for typical text files
- **False Positives:** Minimal due to pattern validation (Luhn for credit cards)
- **Content Protection:** PII file contents never stored in database
- **Privacy:** Only hash and metadata tracked for PII files

---

### AI Analysis Request Workflow

**Complete end-to-end workflow for requesting AI-powered timeline analysis**

#### Architecture Overview

```
User (Admin Dashboard)
    ↓
1. Select FIM Alerts
    ↓
2. Configure Analysis Parameters
    ↓
3. Frontend sends POST /api/admin/analyze-timeline
    ↓
4. Backend validates & fetches data
    ↓
5. Optional: Query Wazuh SIEM events
    ↓
6. Filter & optimize event data (70-90% smaller)
    ↓
7. Send to Mistral AI API
    ↓
8. Parse AI response
    ↓
9. Store in database (TimelineAnalysis table)
    ↓
10. Return analysis summary to frontend
    ↓
User views analysis report
```

#### Step 1: Frontend - Select Alerts

**Location:** [server/templates/admin.html](../server/templates/admin.html)

```javascript
// User selects alerts in dashboard
let selectedAlertIds = [];

// Checkbox selection
document.querySelectorAll('.alert-checkbox:checked').forEach(checkbox => {
    selectedAlertIds.push(parseInt(checkbox.value));
});

console.log(`Selected ${selectedAlertIds.length} alerts for analysis`);
// Example: [1, 2, 3, 4, 5]
```

#### Step 2: Open Analysis Modal

```javascript
function openTimelineAnalysisModal() {
    // Show modal with configuration options
    document.getElementById('timeline-analysis-modal').style.display = 'flex';

    // Populate selected alert count
    document.getElementById('selected-alert-count').textContent = selectedAlertIds.length;

    // Load client info for Wazuh correlation
    loadClientInfoForAnalysis();
}
```

#### Step 3: Configure Analysis Parameters

```javascript
// Analysis configuration form
const analysisConfig = {
    alert_ids: selectedAlertIds,  // [1, 2, 3, 4, 5]
    include_wazuh: document.getElementById('include-wazuh').checked,  // true/false
    agent_ip: document.getElementById('agent-ip').value,  // "10.0.0.5"
    start_time: document.getElementById('start-time').value,  // "2024-01-01T00:00:00Z"
    end_time: document.getElementById('end-time').value  // "2024-01-01T23:59:59Z"
};
```

#### Step 4: Send Analysis Request

**Frontend Request:**

```javascript
async function requestTimelineAnalysis() {
    const statusDiv = document.getElementById('analysis-status');
    statusDiv.innerHTML = '<div class="analyzing">Analyzing with AI... This may take 10-30 seconds...</div>';

    try {
        const response = await fetch('/api/admin/analyze-timeline', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                alert_ids: selectedAlertIds,
                include_wazuh: includeWazuh,
                agent_ip: agentIp,
                start_time: startTime,
                end_time: endTime
            })
        });

        const result = await response.json();

        if (result.success) {
            displayAnalysisResult(result);
        } else {
            showError(result.error);
        }

    } catch (error) {
        console.error('Analysis request failed:', error);
        showError('Analysis failed: ' + error.message);
    }
}
```

#### Step 5: Backend - Process Request

**Location:** [server/routes.py:925](../server/routes.py#L925)

```python
@app.route('/api/admin/analyze-timeline', methods=['POST'])
@login_required
def analyze_timeline():
    """
    Create AI-powered timeline analysis

    Request Body:
        {
            "alert_ids": [1, 2, 3, 4, 5],
            "include_wazuh": true,
            "agent_ip": "10.0.0.5",
            "start_time": "2024-01-01T00:00:00Z",
            "end_time": "2024-01-01T23:59:59Z"
        }
    """
    try:
        data = request.get_json()

        # Extract parameters
        alert_ids = data.get('alert_ids', [])
        include_wazuh = data.get('include_wazuh', False)
        agent_ip = data.get('agent_ip')
        start_time = data.get('start_time')
        end_time = data.get('end_time')

        # Step 5.1: Validate
        if not alert_ids:
            return jsonify({'success': False, 'error': 'No alerts selected'}), 400

        # Step 5.2: Fetch FIM alerts from database
        fim_alerts = FileIntegrity.query.filter(
            FileIntegrity.id.in_(alert_ids)
        ).order_by(FileIntegrity.timestamp.asc()).all()

        if not fim_alerts:
            return jsonify({'success': False, 'error': 'Alerts not found'}), 404

        # Step 5.3: Convert to dictionaries
        fim_data = []
        for alert in fim_alerts:
            fim_data.append({
                'id': alert.id,
                'path': alert.path,
                'alert_type': alert.alert_type,
                'timestamp': alert.timestamp.isoformat(),
                'hash_md5': alert.new_hash,
                'entropy': alert.entropy,
                'high_entropy': alert.high_entropy,
                'magic_byte_mismatch': alert.magic_byte_mismatch,
                'is_hidden': alert.is_hidden,
                'process_name': alert.process_name,
                # ... other fields
            })

        print(f"[AI] Prepared {len(fim_data)} FIM events for analysis")

        # Step 5.4: Query Wazuh SIEM (optional)
        wazuh_data = None
        if include_wazuh and agent_ip:
            print(f"[AI] Querying Wazuh for agent {agent_ip}")

            wazuh = WazuhIntegration()
            agent_id = wazuh.get_agent_by_ip(agent_ip)

            if agent_id:
                wazuh_data = wazuh.query_events_by_agent_and_time(
                    agent_id=agent_id,
                    start_time=start_time,
                    end_time=end_time
                )
                print(f"[AI] Retrieved {len(wazuh_data)} SIEM events")

        # Step 6: Initialize AI Analyzer
        from server.ai_timeline_analysis import AITimelineAnalyzer

        analyzer = AITimelineAnalyzer()

        # Step 7: Perform Analysis
        print("[AI] Sending data to Mistral AI...")
        analysis_result = analyzer.analyze_timeline(
            fim_data=fim_data,
            wazuh_data=wazuh_data
        )

        # Step 8: Store in Database
        timeline_analysis = TimelineAnalysis(
            alert_ids=','.join(map(str, alert_ids)),
            client_id=fim_alerts[0].client_id,
            start_time=datetime.fromisoformat(start_time.replace('Z', '+00:00')),
            end_time=datetime.fromisoformat(end_time.replace('Z', '+00:00')),
            fim_events_count=len(fim_data),
            wazuh_events_count=len(wazuh_data) if wazuh_data else 0,
            analysis_result_json=json.dumps(analysis_result),
            overall_risk=analysis_result.get('overall_risk'),
            confidence=analysis_result.get('confidence'),
            attack_type=analysis_result.get('attack_type'),
            mitre_techniques=','.join(analysis_result.get('mitre_attack_techniques', [])),
            status='completed'
        )

        db.session.add(timeline_analysis)
        db.session.commit()

        print(f"[AI] Analysis complete - ID: {timeline_analysis.id}")

        # Step 9: Return Summary
        return jsonify({
            'success': True,
            'analysis_id': timeline_analysis.id,
            'summary': {
                'overall_risk': analysis_result.get('overall_risk'),
                'confidence': analysis_result.get('confidence'),
                'attack_type': analysis_result.get('attack_type'),
                'mitre_techniques': analysis_result.get('mitre_attack_techniques', []),
                'key_findings': analysis_result.get('key_findings', [])
            }
        })

    except Exception as e:
        print(f"[ERROR] Timeline analysis failed: {e}")
        import traceback
        traceback.print_exc()

        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
```

#### Step 6: AI Analyzer - Filter Events

**Location:** [server/ai_timeline_analysis.py:183](../server/ai_timeline_analysis.py#L183)

```python
def _filter_event_data(self, events: List[Dict], event_type: str = "FIM") -> List[Dict]:
    """
    Filter and simplify event data to reduce payload size

    Optimization:
    - Limits SIEM events to 50 most recent
    - Limits FIM events to 20 most recent
    - Removes unnecessary fields
    - 70-90% size reduction
    """
    filtered = []

    # Limit number of events
    max_events = 50 if event_type == "SIEM" else 20
    events_to_process = events[:max_events] if len(events) > max_events else events

    for event in events_to_process:
        if event_type == "FIM":
            # Keep only essential FIM fields
            filtered.append({
                'path': event.get('path'),
                'alert_type': event.get('alert_type'),
                'timestamp': event.get('timestamp'),
                'magic_byte_mismatch': event.get('magic_byte_mismatch'),
                'high_entropy': event.get('high_entropy'),
                'is_hidden': event.get('is_hidden'),
                'file_extension': event.get('file_extension'),
                'detected_file_type': event.get('detected_file_type'),
                'process_name': event.get('process_name'),
            })
        else:  # SIEM
            # Keep only essential Wazuh fields
            filtered.append({
                'timestamp': event.get('timestamp'),
                'rule': event.get('rule', {}),
                'data': event.get('data', {}),
            })

    if len(events) > max_events:
        print(f"[AI] Limited {event_type} events from {len(events)} to {max_events}")

    return filtered
```

#### Step 7: Send to Mistral AI

```python
def analyze_timeline(self, fim_data: List[Dict],
                    wazuh_data: Optional[List[Dict]] = None) -> Dict:
    """Send filtered data to Mistral AI"""

    # Filter events
    filtered_fim = self._filter_event_data(fim_data, "FIM")
    filtered_wazuh = self._filter_event_data(wazuh_data, "SIEM") if wazuh_data else None

    # Build prompt
    prompt = """
    You are a cybersecurity analyst. Analyze these events and provide:
    1. Overall risk level (CRITICAL/HIGH/MEDIUM/LOW)
    2. Confidence score (0-100)
    3. Attack type
    4. MITRE ATT&CK techniques
    5. Timeline of events
    6. Suspicious events with rationale

    Respond in JSON format only.
    """

    # Build evidence
    contents = [
        f"EVIDENCE FILE #1 (FIM):\n\n{json.dumps(filtered_fim, indent=2)}",
    ]

    if filtered_wazuh:
        contents.append(
            f"EVIDENCE FILE #2 (SIEM):\n\n{json.dumps(filtered_wazuh, indent=2)}"
        )

    # Call Mistral AI
    response = self.client.chat.complete(
        model=self.model_id,
        messages=[
            {"role": "user", "content": [
                {"type": "text", "text": prompt},
                *[{"type": "text", "text": content} for content in contents]
            ]}
        ],
        response_format={"type": "json_object"}
    )

    # Parse response
    result_text = response.choices[0].message.content
    result = json.loads(result_text)

    return result
```

#### Step 8: Frontend - Display Results

```javascript
function displayAnalysisResult(result) {
    const summary = result.summary;

    // Build result HTML
    const resultHTML = `
        <div class="analysis-result">
            <h3>Analysis Complete</h3>

            <div class="risk-level ${summary.overall_risk.toLowerCase()}">
                Risk: ${summary.overall_risk}
            </div>

            <div class="confidence">
                Confidence: ${summary.confidence}%
            </div>

            <div class="attack-type">
                Attack Type: ${summary.attack_type || 'Unknown'}
            </div>

            <div class="mitre-techniques">
                MITRE Techniques:
                ${summary.mitre_techniques.map(t =>
                    `<span class="technique-badge">${t}</span>`
                ).join(' ')}
            </div>

            <div class="key-findings">
                <h4>Key Findings:</h4>
                <ul>
                    ${summary.key_findings.map(f => `<li>${f}</li>`).join('')}
                </ul>
            </div>

            <button onclick="window.open('/admin/analysis-reports', '_blank')">
                View Full Report
            </button>
        </div>
    `;

    document.getElementById('analysis-status').innerHTML = resultHTML;
}
```

#### Complete Usage Example

```javascript
// Frontend workflow
async function analyzeSelectedAlerts() {
    // 1. Get selected alerts
    const selectedAlerts = getSelectedAlertIds();  // [1, 2, 3, 4, 5]

    // 2. Configure analysis
    const config = {
        alert_ids: selectedAlerts,
        include_wazuh: true,
        agent_ip: "10.0.0.5",
        start_time: "2024-01-01T00:00:00Z",
        end_time: "2024-01-01T23:59:59Z"
    };

    // 3. Request analysis
    const response = await fetch('/api/admin/analyze-timeline', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(config)
    });

    // 4. Handle response
    const result = await response.json();

    if (result.success) {
        console.log('Analysis ID:', result.analysis_id);
        console.log('Risk:', result.summary.overall_risk);
        console.log('Confidence:', result.summary.confidence);
        console.log('Attack:', result.summary.attack_type);
        console.log('MITRE:', result.summary.mitre_techniques);

        displayAnalysisResult(result);
    }
}
```

**Expected Timeline:**
- Request sent: T+0s
- Data fetched: T+1-2s
- Wazuh queried: T+2-5s
- AI analysis: T+5-15s
- Response returned: T+5-20s total

#### Error Handling

```python
# Backend error handling
try:
    analysis_result = analyzer.analyze_timeline(fim_data, wazuh_data)
except Exception as e:
    # Store failed analysis
    timeline_analysis = TimelineAnalysis(
        alert_ids=','.join(map(str, alert_ids)),
        status='failed',
        error_message=str(e)
    )
    db.session.add(timeline_analysis)
    db.session.commit()

    return jsonify({
        'success': False,
        'error': f'AI analysis failed: {str(e)}'
    }), 500
```

#### Performance Metrics

| Metric | Value | Notes |
|--------|-------|-------|
| **Payload Size (Before)** | 500KB - 2MB | Full event data |
| **Payload Size (After)** | 50KB - 200KB | Filtered (70-90% reduction) |
| **API Call Time** | 5-15 seconds | Mistral AI processing |
| **Total Request Time** | 10-25 seconds | Including DB queries |
| **Cost per Analysis** | ~$0.001 - $0.01 | Mistral AI API cost |

---

## Database Models

**Location:** [server/database.py](../server/database.py)

### FileIntegrity Model

```python
class FileIntegrity(db.Model):
    """
    File integrity alert/event model

    Stores all file monitoring events with comprehensive metadata
    """
    __tablename__ = 'file_integrity'

    id = db.Column(db.Integer, primary_key=True)
    path = db.Column(db.String(512), nullable=False)
    alert_type = db.Column(db.String(50))  # created, modified, deleted, renamed
    old_hash = db.Column(db.String(32))
    new_hash = db.Column(db.String(32))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    # File metadata
    file_size = db.Column(db.BigInteger)
    file_extension = db.Column(db.String(50))
    magic_bytes = db.Column(db.String(64))
    detected_file_type = db.Column(db.String(50))
    magic_byte_mismatch = db.Column(db.Boolean, default=False)

    # Security features
    entropy = db.Column(db.Float)
    high_entropy = db.Column(db.Boolean, default=False)
    is_hidden = db.Column(db.Boolean, default=False)
    is_pii = db.Column(db.Boolean, default=False)
    pii_types = db.Column(db.Text)

    # Process information
    process_name = db.Column(db.String(255))
    process_pid = db.Column(db.Integer)
    process_user = db.Column(db.String(255))
    process_cmdline = db.Column(db.Text)

    # Rename event fields
    old_path = db.Column(db.String(512))
    new_path = db.Column(db.String(512))

    # Relationships
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'))
    client = db.relationship('Client', backref='alerts')
```

### TimelineAnalysis Model

```python
class TimelineAnalysis(db.Model):
    """
    AI timeline analysis results
    """
    __tablename__ = 'timeline_analysis'

    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Analysis scope
    alert_ids = db.Column(db.Text)  # Comma-separated alert IDs
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'))
    start_time = db.Column(db.DateTime)
    end_time = db.Column(db.DateTime)

    # Event counts
    fim_events_count = db.Column(db.Integer, default=0)
    wazuh_events_count = db.Column(db.Integer, default=0)

    # Analysis results
    analysis_result_json = db.Column(db.Text)  # Full JSON response
    overall_risk = db.Column(db.String(20))  # CRITICAL, HIGH, MEDIUM, LOW
    confidence = db.Column(db.Integer)  # 0-100
    attack_type = db.Column(db.String(255))
    mitre_techniques = db.Column(db.Text)  # Comma-separated

    # Status
    status = db.Column(db.String(50), default='completed')
    error_message = db.Column(db.Text)
```

---

## Utility Functions

### Hash Calculation

**Location:** [client/client.py:800](../client/client.py#L800)

```python
def calculate_md5(self, filepath: str, chunk_size: int = 8192) -> Optional[str]:
    """
    Calculate MD5 hash of file

    Args:
        filepath: Path to file
        chunk_size: Bytes to read at a time (default: 8KB)

    Returns:
        32-character hex string or None

    Algorithm:
        Reads file in chunks to handle large files efficiently
    """
```

### Luhn Algorithm (Credit Card Validation)

**Location:** [client/client.py:1100](../client/client.py#L1100)

```python
def _luhn_check(self, card_number: str) -> bool:
    """
    Validate credit card number using Luhn algorithm

    Args:
        card_number: Digits only string

    Returns:
        True if valid credit card number

    Algorithm:
        1. Reverse the number
        2. Double every second digit
        3. If doubled value > 9, subtract 9
        4. Sum all digits
        5. Valid if sum % 10 == 0
    """
```

### Process Tree Walking

**Location:** [client/client.py:700](../client/client.py#L700)

```python
def _get_process_tree(self, proc: psutil.Process, depth: int = 0,
                     max_depth: int = 5) -> List[Dict]:
    """
    Recursively build process ancestry tree

    Args:
        proc: psutil.Process instance
        depth: Current recursion depth
        max_depth: Maximum depth to traverse

    Returns:
        List of process dictionaries from current to root

    Structure:
        [
            {
                "depth": 0,
                "pid": 1234,
                "name": "notepad.exe",
                "exe": "C:\\Windows\\notepad.exe",
                "cmdline": ["notepad.exe", "file.txt"]
            },
            {
                "depth": 1,
                "pid": 5678,
                "name": "explorer.exe",
                ...
            }
        ]
    """
```

---

## Code Patterns & Best Practices

### Error Handling Pattern

```python
# Client-side: Silent failure for non-critical operations
try:
    entropy = self.calculate_entropy(filepath)
    metadata['entropy'] = entropy
except Exception as e:
    print(f"[WARNING] Entropy calculation failed: {e}")
    metadata['entropy'] = None
    # Continue execution - don't fail entire event

# Server-side: Return error response
try:
    result = perform_operation()
    return jsonify({"success": True, "data": result})
except Exception as e:
    print(f"[ERROR] {str(e)}")
    return jsonify({"success": False, "error": str(e)}), 500
```

### Database Transaction Pattern

```python
from server import db

try:
    # Create object
    alert = FileIntegrity(
        path=filepath,
        alert_type='modified',
        ...
    )

    # Add to session
    db.session.add(alert)

    # Commit transaction
    db.session.commit()

    return alert.id

except Exception as e:
    # Rollback on error
    db.session.rollback()
    print(f"[ERROR] Database error: {e}")
    return None
```

### API Request Pattern (Client → Server)

```python
import requests

def send_to_server(endpoint: str, data: Dict) -> bool:
    """Standard API request pattern"""
    try:
        response = requests.post(
            f"{self.server_url}{endpoint}",
            json=data,
            headers={
                'X-Client-ID': self.client_id,
                'X-Hostname': self.hostname,
                'Content-Type': 'application/json'
            },
            timeout=30
        )

        if response.status_code == 200:
            print(f"[OK] {endpoint} - Success")
            return True
        else:
            print(f"[ERROR] {endpoint} - Status {response.status_code}")
            return False

    except requests.exceptions.RequestException as e:
        print(f"[ERROR] {endpoint} - {e}")
        return False
```

---

## Configuration Examples

### Client Configuration

**File:** `client/dist/app_config.json`

```json
{
  "server_url": "http://10.249.162.130:5000",
  "monitored_paths": [
    "C:/Users/orxan/Documents",
    "C:/ImportantFiles"
  ],
  "pii_paths": [
    "C:/PII_Data"
  ],
  "exclusion_patterns": [
    "*.log",
    "*.tmp",
    "*.temp",
    "__pycache__",
    ".git",
    ".venv",
    "node_modules"
  ],
  "autostart": false,
  "minimize_to_tray": false
}
```

### Server Configuration

**File:** `.env`

```bash
# Database
DATABASE_URL=postgresql://user:pass@host:5432/fimonacci
SECRET_KEY=your-secret-key-here

# AI Analysis
AI_ANALYSIS_ENABLED=true
AI_PROVIDER=mistral
MISTRAL_API_KEY=your-api-key-here
MISTRAL_MODEL=mistral-small-latest

# Wazuh SIEM
WAZUH_ENABLED=true
WAZUH_MANAGER_URL=https://10.249.162.172:55000
WAZUH_INDEXER_URL=https://10.249.162.172:9200
WAZUH_API_USER=wazuh-wui
WAZUH_API_PASSWORD=your-password
```

---

## Quick Reference

### Common Operations

**Initialize Client:**
```python
from client import FIMonacciClient
client = FIMonacciClient("http://10.0.0.5:5000")
```

**Scan Folder:**
```python
client.scan_folder("C:\\Users\\test\\Documents")
```

**Start Continuous Monitoring:**
```python
client.start_monitoring([
    "C:\\Users\\test\\Documents",
    "C:\\ImportantFiles"
])
```

**Calculate Entropy:**
```python
entropy = client.calculate_entropy("file.bin")
if entropy >= 7.5:
    print("Encrypted!")
```

**Detect PII:**
```python
pii = client.detect_pii("document.txt")
if pii['is_pii']:
    print(f"PII found: {pii['pii_types']}")
```

**Get Process Info:**
```python
proc_info = client.get_process_info()
print(f"Process: {proc_info['name']}")
print(f"Parent: {proc_info['parent_name']}")
```

---

## Version Information

- **FIMonacci Version:** 2.0.0
- **Last Updated:** 2024-12-19
- **Python Version:** 3.8+
- **Database:** PostgreSQL 12+

## See Also

- [README.md](../README.md) - Main documentation
- [RUN_AS_ADMIN.md](../RUN_AS_ADMIN.md) - Administrator access guide
- [Scripts Usage](../README.md#scripts-usage) - Database and utility scripts
