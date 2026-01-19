# FIMonacci Mobile

Real-time File Integrity Monitoring System - Mobile Application

## Overview

FIMonacci Mobile is an Android application that provides real-time monitoring of file integrity alerts from the FIMonacci security monitoring system. The app connects to a backend server to display critical security alerts, statistics, and monitored agent information with live updates via WebSocket.

## Features

- **Real-Time Monitoring**: WebSocket-based live updates for instant alert notifications
- **Dashboard**: Visual statistics with animated charts showing alert types and severity levels
- **Alerts Management**: Browse and filter file integrity alerts with severity indicators
- **Agent Monitoring**: Track status of all monitored computers/endpoints
- **Push Notifications**: Instant notifications for critical security alerts
- **Dark Theme**: Material Design 3 with dark theme support
- **Offline Support**: Graceful handling of network connectivity issues

## Screenshots

### Dashboard
- Real-time statistics with animated bar and pie charts
- Connection status indicator
- Quick overview of file activity (modified, deleted, created, accessed)
- Severity breakdown (critical, high, medium, low)

### Alerts Screen
- List of recent file integrity alerts
- Color-coded severity levels:
  - 🔴 **CRITICAL** (red) - Risk score ≥ 0.8
  - 🟠 **HIGH** (orange) - Risk score ≥ 0.6
  - 🟡 **MEDIUM** (yellow) - Risk score ≥ 0.4
  - 🟢 **LOW** (green) - Risk score < 0.4
- Pull-to-refresh functionality

### Agents Screen
- List of monitored computers
- Online/offline status indicators
- Alert count per agent
- Last seen timestamp

## Tech Stack

### Android Application
- **Language**: Kotlin
- **UI Framework**: Jetpack Compose
- **Architecture**: MVVM (Model-View-ViewModel)
- **Networking**: Retrofit 2 + OkHttp
- **WebSocket**: OkHttp WebSocket
- **Async**: Kotlin Coroutines + Flow
- **DI**: Manual dependency injection
- **Charts**: Custom Compose charts
- **Min SDK**: Android 8.0 (API 26)
- **Target SDK**: Android 14 (API 34)

### Backend Server
- **Language**: Python 3.x
- **Framework**: FastAPI
- **Database**: PostgreSQL
- **Real-time**: WebSocket
- **CORS**: Enabled for cross-origin requests

## Project Structure

```
MOBILE/
├── android/                          # Android application
│   ├── app/
│   │   ├── src/main/
│   │   │   ├── java/com/fimonacci/app/
│   │   │   │   ├── data/
│   │   │   │   │   ├── api/
│   │   │   │   │   │   ├── ApiService.kt          # REST API endpoints
│   │   │   │   │   │   └── RetrofitClient.kt      # HTTP client setup
│   │   │   │   │   ├── model/
│   │   │   │   │   │   ├── Alert.kt               # Alert data model
│   │   │   │   │   │   ├── Stats.kt               # Statistics model
│   │   │   │   │   │   ├── Agent.kt               # Agent model
│   │   │   │   │   │   └── AgentFile.kt           # Agent file model
│   │   │   │   │   ├── preferences/
│   │   │   │   │   │   └── PreferencesManager.kt  # Settings storage
│   │   │   │   │   └── websocket/
│   │   │   │   │       └── WebSocketManager.kt    # Real-time updates
│   │   │   │   ├── ui/
│   │   │   │   │   ├── screen/
│   │   │   │   │   │   ├── DashboardScreen.kt     # Main dashboard
│   │   │   │   │   │   ├── AlertsScreen.kt        # Alerts list
│   │   │   │   │   │   ├── AlertDetailScreen.kt   # Alert details
│   │   │   │   │   │   ├── AgentsScreen.kt        # Agents list
│   │   │   │   │   │   ├── AgentDetailScreen.kt   # Agent details
│   │   │   │   │   │   ├── SettingsScreen.kt      # App settings
│   │   │   │   │   │   └── SplashScreen.kt        # Launch screen
│   │   │   │   │   ├── components/
│   │   │   │   │   │   └── AlertListItem.kt       # Reusable components
│   │   │   │   │   ├── viewmodel/
│   │   │   │   │   │   ├── DashboardViewModel.kt  # Main logic
│   │   │   │   │   │   └── SettingsViewModel.kt   # Settings logic
│   │   │   │   │   └── theme/
│   │   │   │   │       ├── Color.kt               # App colors
│   │   │   │   │       ├── Theme.kt               # Material theme
│   │   │   │   │       └── Type.kt                # Typography
│   │   │   │   ├── utils/
│   │   │   │   │   └── NotificationManager.kt     # Push notifications
│   │   │   │   ├── navigation/
│   │   │   │   │   └── NavGraph.kt                # Navigation setup
│   │   │   │   └── MainActivity.kt                # Entry point
│   │   │   └── res/
│   │   │       ├── drawable/                      # Icons & images
│   │   │       ├── mipmap/                        # App icons
│   │   │       └── values/                        # Strings, colors
│   │   └── build.gradle.kts                       # App dependencies
│   ├── build.gradle.kts                           # Project config
│   ├── settings.gradle.kts                        # Module settings
│   └── build-apk.bat                              # Build script
│
├── backend/                          # Backend server
│   ├── main.py                       # FastAPI server
│   ├── requirements.txt              # Python dependencies
│   ├── server-info.txt              # Server connection details
│   ├── connect-server.bat           # Server connection script
│   └── ssh.pem                      # SSH key (keep secure!)
│
├── CODE_DOCUMENTATION.md            # Technical documentation
└── README.md                        # This file
```

## Installation & Setup

### Prerequisites

1. **Android Studio** (latest version)
   - Download: https://developer.android.com/studio
   - Kotlin plugin installed

2. **Android Device or Emulator**
   - Android 8.0 (API 26) or higher
   - Enable "Unknown Sources" for manual APK installation

3. **Backend Server**
   - Python 3.8+
   - PostgreSQL database
   - Server must be accessible from mobile device

### Backend Setup

1. Navigate to backend directory:
```bash
cd MOBILE/backend
```

2. Install Python dependencies:
```bash
pip install -r requirements.txt
```

3. Configure database connection in `main.py`:
```python
DB_CONFIG = {
    "host": "your-database-host",
    "port": 5432,
    "database": "your-database-name",
    "user": "your-username",
    "password": "your-password"
}
```

4. Start the server:
```bash
python main.py
```

The server will start on `http://0.0.0.0:8000`

### Android App Setup

#### Option 1: Build from Source

1. Open Android Studio

2. Open the project:
   - File → Open → Select `MOBILE/android` directory

3. Wait for Gradle sync to complete

4. Configure server URL in `RetrofitClient.kt` (or use Settings screen in app):
```kotlin
private const val DEFAULT_BASE_URL = "http://your-server-ip:8000/"
```

5. Build the app:
   - Build → Build Bundle(s) / APK(s) → Build APK(s)
   - Or use the build script: `build-apk.bat`

6. Install on device:
   - Transfer APK to device and install
   - Or run directly from Android Studio

#### Option 2: Install Pre-built APK

1. Use the build script:
```bash
cd MOBILE/android
build-apk.bat
```

2. APK will be generated at:
```
android/app/build/outputs/apk/debug/app-debug.apk
```

3. Transfer to device and install

## Configuration

### First Launch Setup

1. Open the app
2. Navigate to **Settings** (gear icon)
3. Configure:
   - **Server URL**: Your backend server address (e.g., `http://192.168.1.100:8000`)
   - **Notifications**: Enable/disable push notifications
   - **Notification Sound**: Enable/disable alert sounds

### Server Connection

The app requires network access to your backend server:

- **Local Network**: Use local IP (e.g., `http://192.168.1.100:8000`)
- **Public Server**: Use domain or public IP (e.g., `http://your-domain.com:8000`)
- **HTTPS**: Supported for secure connections (e.g., `https://your-domain.com`)

**Note**: Ensure your firewall allows connections on port 8000 (or your configured port).

## API Endpoints

The mobile app communicates with the following endpoints:

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Health check |
| `GET` | `/alerts` | Fetch recent alerts (50 max) |
| `GET` | `/stats` | Get statistics dashboard |
| `GET` | `/agents` | List all monitored agents |
| `GET` | `/agents/{id}` | Get specific agent details |
| `WebSocket` | `/ws` | Real-time update stream |

## Real-Time Updates

The app uses WebSocket for instant notifications:

### Connection Flow
1. App connects to `ws://server:8000/ws`
2. Server sends connection confirmation
3. App listens for update messages
4. On new alerts → Auto-refresh alerts list
5. On stats update → Auto-refresh dashboard

### WebSocket Messages

**From Server:**
```json
{
  "type": "new_alerts",
  "count": 5,
  "timestamp": "2024-12-18T14:32:45Z"
}
```

```json
{
  "type": "stats_update",
  "stats": {
    "modified": 120,
    "deleted": 15,
    "created": 45,
    "accessed": 230
  },
  "timestamp": "2024-12-18T14:32:45Z"
}
```

### Reconnection Logic
- Auto-reconnect on connection loss
- Exponential backoff (1s, 2s, 4s, 8s, max 30s)
- Status indicator shows connection state

## Notifications

### Alert Notifications
- **CRITICAL alerts** trigger immediate push notifications
- Notifications include:
  - Alert severity and type
  - Filename and agent
  - Timestamp
- Tap notification to view alert details

### Notification Permissions
- Requested on first launch
- Can be enabled/disabled in Settings
- Sound can be toggled separately

## Data Models

### Alert
```kotlin
data class Alert(
    val id: Int,
    val filename: String,           // "system32.dll"
    val agentName: String,          // "LAPTOP-001"
    val severity: String,           // "CRITICAL", "HIGH", "MEDIUM", "LOW"
    val eventType: String,          // "CREATED", "MODIFIED", "DELETED"
    val timestamp: String,          // "2024-12-18T14:32:45Z"
    val oldHash: String?,           // Previous file hash
    val newHash: String?,           // Current file hash
    val filePath: String            // Full file path
)
```

### Stats
```kotlin
data class Stats(
    val modified: Int,              // Files modified
    val deleted: Int,               // Files deleted
    val created: Int,               // Files created
    val accessed: Int,              // Files accessed
    val critical: Int,              // Critical severity count
    val high: Int,                  // High severity count
    val medium: Int,                // Medium severity count
    val low: Int                    // Low severity count
)
```

### Agent
```kotlin
data class Agent(
    val id: Int,
    val hostname: String,           // "LAPTOP-001"
    val lastSeen: String?,          // "2024-12-18T14:32:45Z"
    val alertCount: Int,            // Number of alerts
    val status: String              // "online" or "offline"
)
```

## Troubleshooting

### App Won't Connect
- Verify server is running: `curl http://your-server:8000`
- Check server URL in Settings is correct
- Ensure device is on same network (for local servers)
- Check firewall allows port 8000

### No Real-Time Updates
- WebSocket connection may be blocked
- Check connection indicator on dashboard
- Try manual refresh (pull down on screens)
- Restart app to reconnect

### Notifications Not Working
- Enable notifications in Settings
- Check Android app permissions
- Ensure app has notification permission
- Check "Do Not Disturb" mode is off

### Build Errors
- Ensure JDK 17 or higher is installed
- Run `./gradlew clean` then rebuild
- Update Android Studio to latest version
- Sync Gradle files

## Development

### Prerequisites
- Android Studio Hedgehog or newer
- JDK 17+
- Kotlin 1.9+

### Running in Development
```bash
# Open in Android Studio
cd MOBILE/android

# Or build from command line
./gradlew assembleDebug

# Install on connected device
./gradlew installDebug
```

### Code Style
- Follow Kotlin coding conventions
- Use Jetpack Compose best practices
- MVVM architecture pattern
- Coroutines for async operations

## Security Considerations

⚠️ **Important Security Notes:**

1. **Server URL**: Store securely in encrypted preferences
2. **SSH Keys**: Never commit `ssh.pem` to version control
3. **Network**: Use HTTPS in production
4. **Certificates**: Implement SSL certificate pinning for production
5. **Authentication**: Consider adding user authentication

## Performance

- **Scan Interval**: Backend scans database every 2 seconds
- **API Throttling**: Pull-to-refresh has cooldown
- **WebSocket**: Auto-reconnects with exponential backoff
- **Memory**: Alerts list limited to 50 items
- **Battery**: WebSocket connection managed efficiently

## Future Enhancements

- [ ] User authentication and authorization
- [ ] Multi-server support
- [ ] Alert filtering and search
- [ ] Export alerts to PDF/CSV
- [ ] Custom alert rules
- [ ] Biometric authentication
- [ ] Tablet UI optimization
- [ ] iOS version

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

[Specify your license here]

## Support

For issues, questions, or contributions:
- GitHub Issues: [Link to issues]
- Documentation: `CODE_DOCUMENTATION.md`
- Email: [Your contact email]

## Changelog

### Version 1.0.0 (Current)
- Initial release
- Real-time monitoring via WebSocket
- Dashboard with statistics
- Alert management
- Agent monitoring
- Push notifications
- Settings management

---

**Built with ❤️ using Kotlin & Jetpack Compose**
