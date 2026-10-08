<div align="center">

<img src="client/logo.png" alt="FIMonacci Logo" width="280"/>

# FIMonacci

### Advanced File Integrity Monitoring System

<p align="center">
  <em>High-performance File Integrity Monitoring (FIM) system with real-time alerts, AI-powered analysis, SIEM integration, and comprehensive security monitoring.</em>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.8+-blue.svg" alt="Python Version"/>
  <img src="https://img.shields.io/badge/PostgreSQL-12+-blue.svg" alt="PostgreSQL"/>
  <img src="https://img.shields.io/badge/Flask-2.3+-green.svg" alt="Flask"/>
  <img src="https://img.shields.io/badge/AI-Powered-purple.svg" alt="AI Powered"/>
  <img src="https://img.shields.io/badge/License-Proprietary-red.svg" alt="License"/>
</p>

</div>

---

## Table of Contents
- [Features](#features)
- [Quick Start](#quick-start)
- [Installation](#installation)
  - [Server Setup](#server-setup)
  - [Client Setup](#client-setup)
- [Configuration](#configuration)
- [Usage Guide](#usage-guide)
  - [Admin Dashboard](#admin-dashboard)
  - [File Monitoring](#file-monitoring)
  - [AI Timeline Analysis](#ai-timeline-analysis)
  - [Wazuh SIEM Integration](#wazuh-siem-integration)
- [Advanced Features](#advanced-features)
- [Troubleshooting](#troubleshooting)
- [Scripts Usage](#scripts-usage)
  - [Database Scripts](#database-scripts)
  - [Testing Scripts](#testing-scripts)
  - [Utility Scripts](#utility-scripts)
- [Project Structure](#project-structure)
- [Developer Documentation](#developer-documentation)

---

## Features

### Core Monitoring
-  **Real-time File Monitoring** - Continuous monitoring using watchdog with instant event detection
-  **MD5 Hash Verification** - Fast integrity checks with automatic mismatch detection
-  **File Rename Detection** - Single "renamed" event (not delete+create)
-  **Hidden File Detection** - Detects Windows hidden attribute and Unix dot-files
-  **Magic Byte Analysis** - File type detection and mismatch alerts (bidirectional)
-  **Entropy Calculation** - Detects encrypted/compressed files (threshold: 7.5 for encryption)

### Security Intelligence
-  **Process Tree Tracking** - Full process hierarchy and actor information
-  **PII Detection** - Automatic detection of sensitive data (SSN, credit cards, etc.)
-  **Authentication Logs** - Windows Security Event Log integration (requires admin)
-  **Security Event Correlation** - Tracks system security events alongside file changes

### AI-Powered Analysis
-  **AI Timeline Analysis** - Mistral/Grok AI analysis of FIM + SIEM data
-  **Attack Reconstruction** - Identifies suspicious event sequences
-  **MITRE ATT&CK Mapping** - Automatic technique identification
-  **Risk Assessment** - Confidence scoring and severity levels
- ✅ **Performance Optimized** - Filters data to essential fields (5-15s analysis time)

### SIEM Integration
- ✅ **Wazuh Integration** - Query SIEM events by agent IP and timeframe
- ✅ **Event Correlation** - Combine FIM alerts with SIEM data
- ✅ **Configurable IP Address** - Dynamic agent IP input in UI
- ✅ **Event Deduplication** - Removes duplicate SIEM events

### Modern Admin Dashboard
- ✅ **Real-time Alerts** - WebSocket-powered live notifications
- ✅ **Dark/Light Mode** - Automatic theme switching
- ✅ **Multi-Client Management** - Monitor multiple agents from one dashboard
- ✅ **Advanced Filtering** - Search, sort, and filter alerts by type, severity, client
- ✅ **Alert Details** - Comprehensive modal with all file metadata
- ✅ **Analysis Reports** - Historical timeline analysis archive
- ✅ **Click-Outside-to-Close** - All modals support intuitive closing

### Client Features
- ✅ **Standalone Agent** - No server dependencies for monitoring
- ✅ **Executable Build** - PyInstaller-based Windows .exe
- ✅ **Multiple Folder Monitoring** - Monitor any number of paths
- ✅ **Automatic Reconnection** - Resilient to network interruptions
- ✅ **Low Resource Usage** - Efficient watchdog-based monitoring

---

## Quick Start

### Prerequisites
- **Server**: Python 3.8+, PostgreSQL 12+
- **Client**: Python 3.8+ (or use pre-built .exe)
- **Admin Privileges**: Required for authentication log collection on Windows

### Installation

#### 1. Clone Repository
```bash
git clone <repository-url>
cd FIMonacci-main
```

#### 2. Server Setup
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment (copy and edit .env file)
cp env.example .env
# Edit .env with your database credentials and settings

# Initialize database and create admin user
python scripts/database/setup_db.py

# Run server
python run.py
```

Server runs at `http://0.0.0.0:5000`

#### 3. Client Setup

**Option A: Run Python Script**
```bash
cd client

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run client
python client.py -u http://SERVER_IP:5000 -p C:\path\to\monitor --continuous
```

**Option B: Build Executable (Windows)**
```bash
cd client
build.bat  # Creates client\dist\FIMonacci_Agent.exe
```

Then right-click `FIMonacci_Agent.exe` → **Run as administrator**

---

## Configuration

### Environment Variables (.env file)

#### Database
```bash
DATABASE_URL=postgresql://user:password@host:port/database
SECRET_KEY=your-secret-key-here
```

#### Monitoring
```bash
FIMONACCI_PATHS=./monitored
DISABLE_MONITORING=0  # Set to 1 to disable server-side monitoring
```

#### Alerts
```bash
AUTO_ALERTS_ENABLED=true
EMAIL_ALERTS_ENABLED=false
SLACK_ALERTS_ENABLED=false
TELEGRAM_ALERTS_ENABLED=false
```

#### AI Analysis (Recommended)
```bash
AI_ANALYSIS_ENABLED=true
AI_PROVIDER=mistral  # or 'grok'
MISTRAL_API_KEY=your_mistral_api_key_here
MISTRAL_MODEL=mistral-small-latest
```

#### Wazuh SIEM Integration (Optional)
```bash
WAZUH_ENABLED=true
WAZUH_MANAGER_URL=https://YOUR_WAZUH_IP:55000
WAZUH_INDEXER_URL=https://YOUR_WAZUH_IP:9200
WAZUH_API_USER=wazuh-wui
WAZUH_API_PASSWORD=your_wazuh_password
WAZUH_INDEXER_USER=admin
WAZUH_INDEXER_PASSWORD=your_indexer_password
```

#### Telegram Bot (Optional)
```bash
TELEGRAM_BOT_TOKEN=your_bot_token_here
```

### Client Configuration

**Edit `client/dist/app_config.json`:**
```json
{
  "server_url": "http://YOUR_SERVER_IP:5000",
  "paths_to_monitor": [
    "C:\\Users\\YourUser\\Documents",
    "C:\\ImportantFiles"
  ],
  "check_interval": 60
}
```

---

## Usage Guide

### Admin Dashboard

#### 1. Login
Navigate to `http://SERVER_IP:5000` and login with admin credentials:
- Default username: `admin`
- Password: Set during `scripts/database/setup_db.py`

#### 2. Dashboard Overview
- **Overview Tab** - System stats, client count, recent alerts, activity charts
- **Alerts Tab** - All file integrity alerts with advanced filtering
- **Timeline Analysis Tab** - AI-powered attack reconstruction
- **Analysis Reports Tab** - Historical analysis archive
- **Agents Tab** - Connected client agents and their status

#### 3. Viewing Alerts
**Filter Alerts:**
- By event type: Created, Modified, Deleted, Renamed
- By severity: Critical, High, Medium, Low
- By client/hostname
- By time range
- Search by filename or path

**Alert Details:**
- Click any alert to see comprehensive details
- View all file metadata (hash, entropy, magic bytes, etc.)
- See process information (name, PID, command line)
- Check authentication logs (if running as admin)
- View security events correlation

#### 4. Dark/Light Mode
- Click profile icon (top-right) → Toggle theme
- Automatically saves preference

---

### File Monitoring

#### Starting the Client

**Windows (Recommended):**
```bash
# Right-click → Run as administrator
FIMonacci_Agent.exe
```

**Linux/Mac:**
```bash
cd client
sudo python client.py -u http://SERVER_IP:5000 -p /path/to/monitor --continuous
```

**Client Options:**
| Flag | Description | Example |
|------|-------------|---------|
| `-u, --url` | Server URL (required) | `-u http://10.0.0.5:5000` |
| `-p, --path` | Path to monitor (multiple allowed) | `-p C:\Docs -p C:\Code` |
| `-c, --continuous` | Continuous monitoring mode | `-c` |
| `-i, --interval` | Scan interval in seconds | `-i 30` |

#### What Gets Monitored

**Events Detected:**
- ✅ File created
- ✅ File modified (content changed)
- ✅ File deleted
- ✅ File renamed (single event with old/new path)

**Metadata Collected:**
- MD5 hash
- File size
- File extension
- Magic bytes (file signature)
- Entropy (encryption detection)
- Hidden attribute
- File owner
- Timestamps (created, modified, accessed)
- Process information (name, PID, user)
- Process tree (parent/child hierarchy)
- Authentication logs (last 15 events)
- Security logs (last 10 events)

**Alerts Triggered:**
- Hash mismatch (file modified)
- Magic byte mismatch (extension doesn't match file type)
- High entropy (>= 7.5, likely encrypted)
- Hidden file operations
- PII detected in file

---

### AI Timeline Analysis

#### Prerequisites
1. Set `AI_ANALYSIS_ENABLED=true` in `.env`
2. Configure Mistral API key or Grok API key
3. Restart server

#### Creating Analysis

**Step 1: Select FIM Alerts**
- Go to **Alerts** tab
- Select checkbox for alerts you want to analyze (1-20 recommended)

**Step 2: Query Wazuh SIEM (Optional but Recommended)**
- Click "Request SIEM Data" button
- Enter agent IP address (e.g., `192.168.1.100`)
- Select start and end time
- Click "Query SIEM Data"
- Wait for results (shows event summary)

**Step 3: Run AI Analysis**
- Click **"AI Analysis"** button
- Wait 5-15 seconds for processing
- View summary in modal:
  - Risk Level (Low/Medium/High/Critical)
  - Confidence percentage
  - Attack Type
  - Key Findings
  - Events analyzed count

**Step 4: View Full Report**
- Click **"View in Analysis Reports"** button
- Opens new tab with comprehensive analysis

#### Analysis Report Sections

**Summary:**
- Attack Type identification
- Key Findings list
- Analysis Metadata (AI model, event counts, timestamp)

**Suspicious Sequences:**
- Attack chain reconstruction
- Severity rating
- Rationale explanation
- MITRE ATT&CK techniques
- Recommended next steps

**Suspicious Events:**
- Individual suspicious file operations
- Event rationale

**Benign or Uncertain Events:**
- Normal system activity filtered out
- Context for understanding

**Assumptions & Data Gaps:**
- Analysis limitations
- What data was missing
- Transparency about AI assumptions

**Detailed Summary:**
- Verbose narrative explanation
- Complete timeline reconstruction

---

### Wazuh SIEM Integration

#### Prerequisites
1. Wazuh server installed and running
2. Configure Wazuh settings in `.env`
3. Ensure network connectivity to Wazuh Manager (port 55000) and Indexer (port 9200)

#### Querying SIEM Data

**From Alerts Tab:**
1. Select one or more FIM alerts
2. Click **"Request SIEM Data from Wazuh"** button
3. Modal opens with:
   - Agent IP Address field (auto-filled if client has IP)
   - Start Time (datetime picker)
   - End Time (datetime picker)

**Query Options:**
- **Manual IP Entry**: Type any agent IP address
- **Time Range**: Select specific timeframe for correlation
- **Event Limit**: System automatically limits to 50 most relevant events

**Results Display:**
- Total events found
- Unique events (after deduplication)
- Event summary (top 10) with:
  - Severity level (L1-L15)
  - Rule description
  - Repeat count

**Actions After Query:**
- **AI Analysis**: Analyze FIM + SIEM together
- **Timeline**: View events in timeline (legacy)
- **Download**: Export raw JSON

#### SIEM Event Types Captured

From Wazuh Indexer, the system captures:
- Authentication events (login success/failure)
- Privilege escalation
- System configuration changes
- Service/daemon modifications
- Network connections
- Process execution
- File system changes (from Wazuh FIM)

---

## Advanced Features

### Magic Byte Mismatch Detection

**Bidirectional Detection:**
- **Binary → Text**: `.png` file that's actually a JPEG
- **Text → Binary**: `.txt` file that's actually a JPEG (NEW!)

**How It Works:**
1. Reads first 32 bytes of file
2. Detects file type from magic bytes
3. Compares with file extension
4. Flags mismatch if:
   - Binary extension but different magic bytes
   - Text extension but has binary magic bytes

**Supported Formats:**
- Images: PNG, JPEG, GIF, BMP, ICO
- Documents: PDF
- Archives: ZIP, GZIP, BZIP2
- Executables: EXE, DLL
- Media: MP3, MP4, WAV, AVI

### Entropy-Based Encryption Detection

**Entropy Thresholds:**
- **< 4.0**: Plain text
- **4.0 - 7.5**: Compressed
- **≥ 7.5**: Encrypted (ALERT!)

**Use Cases:**
- Ransomware detection
- Unauthorized encryption
- Compressed archives
- Steganography

### Hidden File Detection

**Windows:**
- Checks FILE_ATTRIBUTE_HIDDEN flag (0x2)
- Checks dot-file naming convention (`.filename`)

**Linux/Mac:**
- Checks if filename starts with `.`

**Alerts:**
- Hidden file created
- Hidden file modified
- Existing file marked as hidden

### Authentication Log Collection

**Requirements:**
- Client must run as Administrator (Windows)
- Or run with sudo (Linux)

**Windows Events Collected:**
- Event ID 4624: Successful logon
- Event ID 4625: Failed logon

**What's Captured:**
- Last 15 authentication events
- Event timestamp
- Source/username
- Event type (success/failure)

**Troubleshooting:**
If no auth logs appear:
1. Verify client is running as Administrator
2. Run `scripts/testing/test_auth_logs.py` to diagnose
3. Check Event Viewer manually (eventvwr.msc)
4. Ensure Windows auditing is enabled

---

## Troubleshooting

### Client Issues

**No authentication logs collected**
- **Cause**: Not running as Administrator
- **Fix**: Right-click .exe → Run as administrator
- **Test**: Run `python scripts/testing/test_auth_logs.py` as admin

**"Magic Mismatch: No" but extension is wrong**
- **Cause**: Old client version (before bidirectional fix)
- **Fix**: Rebuild client with `build.bat`

**Hidden file not detected**
- **Cause**: Old client version (before hidden file fix)
- **Fix**: Rebuild client with `build.bat`

**Rename shows as delete + create**
- **Cause**: Old client version (before rename fix)
- **Fix**: Rebuild client with `build.bat`

### Server Issues

**AI Analysis takes too long (>30 seconds)**
- **Cause**: Too many events or slow API
- **Fix**: Latest version filters to 50 events max (should be 5-15s)
- **Solution**: Restart server to apply optimizations

**AI Analysis redirects to broken link**
- **Cause**: Old version with auto-redirect
- **Fix**: Refresh browser (latest version shows summary instead)

**Wazuh query fails**
- **Check**: Network connectivity to Wazuh server
- **Check**: Credentials in `.env` file
- **Check**: Wazuh Manager and Indexer are running
- **Test**: `curl -k https://WAZUH_IP:55000` (should respond)

**Icons hard to see in dark mode**
- **Cause**: Old version without dark mode icon fixes
- **Fix**: Refresh browser (latest version has proper CSS variables)

### Database Issues

**Migration errors**
- **Solution**: No migrations needed for latest features (renamed events, hidden files, etc.)
- **Database schema**: Supports all new fields without changes

**Slow alert loading**
- **Cause**: Too many alerts in database
- **Fix**: Use filtering and pagination
- **Optimize**: Add database indexes (already included)

---

## Scripts Usage

### Database Scripts

All database management scripts are located in `scripts/database/`:

**Initial Setup:**
```bash
# Create database tables and admin user (default password: admin123)
python scripts/database/setup_db.py
```

**Migrations:**
```bash
# Add entropy, high_entropy, is_hidden columns (if upgrading from older version)
python scripts/database/migrate_db.py

# Add IP address column to client table
python scripts/database/add_ip_address_column.py

# Create timeline analysis and Wazuh cache tables
python scripts/database/add_timeline_tables.py

# Add performance indexes
python scripts/database/add_indexes.py
```

### Testing Scripts

All testing and diagnostic tools are located in `scripts/testing/`:

**Authentication Log Testing:**
```bash
# Test if Windows authentication logs can be collected (must run as admin)
python scripts/testing/test_auth_logs.py
```

**Entropy Testing:**
```bash
# Test entropy calculation directly
python scripts/testing/test_entropy_directly.py

# Create test files with different entropy levels
python scripts/testing/create_test_files.py

# PowerShell version (Windows only)
powershell -ExecutionPolicy Bypass -File scripts/testing/create_entropy_test_files.ps1
```

### Utility Scripts

All utility scripts are located in `scripts/utilities/`:

**Database Data Management:**
```bash
# Clear all monitoring data (interactive - asks for confirmation)
python scripts/utilities/clear_data.py

# Clear all monitoring data (auto-confirm - no prompts)
python scripts/utilities/clear_data_auto.py
```

**Note:** All scripts require the `.env` file to be configured with database credentials.

---

## Project Structure

```
FIMonacci-main/
├── server/                      # Flask backend
│   ├── __init__.py             # App factory & initialization
│   ├── admin.py                # Admin panel routes & API
│   ├── auth.py                 # Authentication & user management
│   ├── database.py             # SQLAlchemy models (Clients, Alerts, etc.)
│   ├── routes.py               # Main API endpoints (upload, events)
│   ├── monitor.py              # Server-side FIM monitoring
│   ├── alert_system.py         # Alert pipeline & notifications
│   ├── ai_analysis.py          # AI provider interface (Mistral/Grok)
│   ├── ai_timeline_analysis.py # Timeline analysis engine
│   ├── wazuh_integration.py    # Wazuh SIEM integration
│   ├── telegram_bot.py         # Telegram bot integration (optional)
│   └── templates/              # HTML templates
│       ├── admin.html          # Admin dashboard (dark/light mode)
│       └── login.html          # Login page
├── client/                      # Standalone client agent
│   ├── client.py               # Client monitoring script
│   ├── build.py                # PyInstaller build script
│   ├── build.bat               # Windows build script
│   ├── requirements.txt        # Client dependencies
│   └── dist/                   # Built executables
│       ├── FIMonacci_Agent.exe # Windows executable
│       └── app_config.json     # Client configuration
├── telegram_bot/               # Telegram bot (optional)
│   ├── bot.py
│   ├── requirements.txt
│   └── start.sh
├── scripts/                    # Utility scripts
│   ├── database/               # Database management scripts
│   │   ├── setup_db.py         # Initialize database and create admin user
│   │   ├── migrate_db.py       # Add entropy, high_entropy, is_hidden columns
│   │   ├── add_indexes.py      # Performance optimization indexes
│   │   ├── add_ip_address_column.py  # Add IP address column to client table
│   │   └── add_timeline_tables.py    # Create timeline analysis tables
│   ├── testing/                # Testing and diagnostic tools
│   │   ├── test_auth_logs.py   # Test Windows authentication log collection
│   │   ├── test_entropy_directly.py  # Test entropy calculation
│   │   ├── create_test_files.py      # Create entropy test files
│   │   └── create_entropy_test_files.ps1  # PowerShell entropy test script
│   └── utilities/              # Utility scripts
│       ├── clear_data.py       # Clear database data (interactive)
│       └── clear_data_auto.py  # Clear database data (auto-confirm)
├── docs/                       # Developer documentation
│   └── CODE_REFERENCE.md       # Comprehensive code reference & snippets
├── run.py                      # Server entry point
├── requirements.txt            # Server dependencies
├── .env                        # Environment configuration
├── README.md                   # Main documentation
└── RUN_AS_ADMIN.md            # Administrator access guide
```

---

## Technologies

### Backend
- **Framework**: Flask 2.3.x
- **Database**: PostgreSQL 12+, SQLAlchemy 2.0.x
- **Real-time**: Flask-SocketIO (WebSockets)
- **Auth**: Flask-Login

### Monitoring
- **File Watching**: watchdog
- **Process Info**: psutil
- **Hashing**: hashlib (MD5)
- **File Analysis**: python-magic (magic bytes)

### AI/ML
- **AI Provider**: Mistral AI (mistral-small-latest)
- **Alternative**: Grok API
- **Analysis**: Timeline reconstruction, attack classification

### SIEM
- **Integration**: Wazuh REST API + Elasticsearch/OpenSearch
- **Protocols**: HTTPS, Basic Auth
- **Event Deduplication**: Built-in

### Frontend
- **UI**: HTML5, CSS3 (CSS Variables for theming)
- **JavaScript**: Vanilla ES6+
- **Charts**: Chart.js
- **Icons**: FontAwesome 6
- **Real-time**: Socket.IO client

### Client
- **Packaging**: PyInstaller 5.x
- **Platform**: Cross-platform (Windows, Linux, Mac)
- **Dependencies**: Minimal (requests, watchdog, psutil)

---

## API Documentation

### Client API (Public)

#### Register Client
```http
POST /api/client/register
Content-Type: application/json

{
  "client_id": "unique-client-id",
  "hostname": "DESKTOP-ABC123"
}
```

#### Upload File Hashes
```http
POST /api/upload/hashes
X-Client-ID: unique-client-id
X-Hostname: DESKTOP-ABC123
Content-Type: application/json

[
  {
    "path": "/path/to/file.txt",
    "hash_md5": "abc123...",
    "file_size": 1024,
    ...
  }
]
```

#### Upload Alert
```http
POST /api/upload/event
X-Client-ID: unique-client-id
X-Hostname: DESKTOP-ABC123
Content-Type: application/json

{
  "path": "/path/to/file.txt",
  "alert_type": "hash_mismatch",
  "initial_hash": "old_hash",
  "current_hash": "new_hash",
  "metadata": {...}
}
```

### Admin API (Authenticated)

#### List Clients
```http
GET /admin/api/clients
Cookie: session=...
```

#### Get Client Alerts
```http
GET /admin/api/client/<client_id>/alerts
Cookie: session=...
```

#### Query Wazuh
```http
POST /admin/api/wazuh/query
Cookie: session=...
Content-Type: application/json

{
  "agent_ip": "192.168.1.100",
  "start_time": "2025-12-19T10:00:00",
  "end_time": "2025-12-19T12:00:00"
}
```

#### AI Analysis
```http
POST /api/timeline/analyze
Cookie: session=...
Content-Type: application/json

{
  "alert_ids": [1, 2, 3],
  "include_wazuh": true,
  "wazuh_events": [...],
  "agent_ip": "192.168.1.100",
  "start_time": "...",
  "end_time": "..."
}
```

---

## Security Considerations

### Authentication
- ✅ Password hashing with Werkzeug
- ✅ Session-based authentication
- ✅ Admin-only routes protected
- ✅ CSRF protection (Flask defaults)

### Network Security
- ⚠️ Use HTTPS in production (configure reverse proxy)
- ⚠️ Firewall: Restrict port 5000 to trusted networks
- ⚠️ Wazuh: Use HTTPS with certificate verification

### Data Privacy
- ✅ PII detection prevents sensitive data leakage
- ✅ Content cache respects PII flags
- ✅ Auth logs encrypted in transit (HTTPS)

### Client Security
- ✅ Admin privileges required for full functionality
- ✅ Unique client IDs prevent impersonation
- ✅ Heartbeat mechanism detects offline agents

---

## Performance Optimization

### Server
- **Database Indexes**: Created on foreign keys, timestamps, alert types
- **WebSocket**: Efficient real-time updates (no polling)
- **Pagination**: Alerts loaded in batches
- **Caching**: Static assets cached

### Client
- **Watchdog**: Event-driven (no polling of filesystem)
- **Batch Uploads**: Groups metadata uploads
- **Retry Logic**: Exponential backoff for failed uploads
- **Low CPU**: <1% CPU usage during idle monitoring

### AI Analysis
- **Data Filtering**: Only essential fields sent to AI
- **Event Limiting**: Max 50 SIEM + 20 FIM events
- **Fast Model**: Uses mistral-small-latest (5-15s response)
- **Token Optimization**: 70-90% smaller payload vs raw JSON

---

## Developer Documentation

For detailed code reference, function definitions, and development guidelines, see:

📖 **[Code Reference Documentation](docs/CODE_REFERENCE.md)**

This comprehensive guide includes:
- **Client-Side Code**: FIMonacciClient class, file monitoring, security analysis functions
- **Server-Side Code**: API endpoints, AI timeline analysis, Wazuh integration
- **Database Models**: FileIntegrity, TimelineAnalysis, Client models
- **Utility Functions**: Hash calculation, PII detection, process tree walking
- **Code Snippets**: Ready-to-use examples for common operations
- **Best Practices**: Error handling, database transactions, API patterns

**Quick Links:**
- [FIMonacciClient Class](docs/CODE_REFERENCE.md#fimonacciclient-class) - Main client implementation
- [File Metadata Collection](docs/CODE_REFERENCE.md#1-file-metadata-collection) - Comprehensive metadata gathering
- [Entropy Calculation](docs/CODE_REFERENCE.md#2-entropy-calculation) - Encryption detection
- [Magic Byte Detection](docs/CODE_REFERENCE.md#3-magic-byte-detection) - File type verification
- [PII Detection](docs/CODE_REFERENCE.md#4-pii-detection) - Sensitive data scanning
- [AI Timeline Analysis](docs/CODE_REFERENCE.md#ai-timeline-analysis) - AI-powered attack reconstruction
- [API Endpoints](docs/CODE_REFERENCE.md#api-endpoints) - Server API reference
- [Database Models](docs/CODE_REFERENCE.md#database-models) - Data structures

---

## License

Proprietary software.

---

## Support & Contribution

For issues, bugs, or feature requests, please contact the development team.

**Version**: 2.0.0
**Last Updated**: December 2025
