# FIMonacci - Main Functions Documentation

---

## BACKEND (Python/FastAPI)

**File:** `backend/main.py`

### 1. **scan_database()**
**What it does:** Runs a database scan every 2 seconds to detect new file integrity alerts

```python
def scan_database():
    """Scan database for new alerts and stats"""
    try:
        # Get 50 most recent alerts with risk scores
        # Calculate statistics (modified, deleted, created, accessed)
        # Detect new alerts by comparing with cache
        # Update scanner state with new data
        # Queue broadcasts for WebSocket clients
```

---

### 2. **scanner_loop()**
**What it does:** Background thread that continuously scans the database with timeout protection

```python
def scanner_loop():
    """Background scanner loop"""
    while True:
        try:
            # Set 10 second timeout alarm
            signal.alarm(10)
            
            # Run scan
            scan_database()
            
            # Sleep for scan_interval (2 seconds)
            time.sleep(scanner_state["scan_interval"])
```

---

### 3. **broadcast_handler()**
**What it does:** Async task that handles WebSocket broadcasts to all connected mobile clients

```python
async def broadcast_handler():
    """Handle broadcasts from scanner thread"""
    while True:
        # Check if there are pending stats updates
        # Check if there are pending new alerts
        # Send messages via WebSocket to all connected clients
        await asyncio.sleep(0.3)  # Check every 300ms
```

---

### 4. **get_alerts()**
**Endpoint:** `GET /alerts`  
**What it does:** Returns the 50 most recent file integrity alerts with severity levels

```python
@app.get("/alerts", response_model=AlertsResponse)
async def get_alerts():
    """Get recent alerts - queries database directly"""
    # Connect to PostgreSQL
    # Query file_integrity table
    # Join with client table to get hostname
    # Calculate severity from ai_risk_score:
    #   >= 0.8 = CRITICAL (🔴)
    #   >= 0.6 = HIGH (🟠)
    #   >= 0.4 = MEDIUM (🟡)
    #   < 0.4  = LOW (🟢)
    # Return up to 50 alerts
```

**Response Model:**
```python
class Alert(BaseModel):
    id: int
    filename: str
    agent_name: str
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW
    event_type: str  # CREATED, MODIFIED, DELETED
    timestamp: datetime
    old_hash: Optional[str]  # Previous file hash
    new_hash: Optional[str]  # Current file hash
    file_path: str
```

---

### 5. **get_stats()**
**Endpoint:** `GET /stats`  
**What it does:** Returns dashboard statistics (count of different alert types and severity levels)

```python
@app.get("/stats", response_model=Stats)
async def get_stats():
    """Get dashboard statistics"""
    # Query file_integrity table
    # Count alerts by type:
    #   - modified (LIKE '%modif%' OR '%write%' OR '%change%')
    #   - deleted (LIKE '%delet%')
    #   - created (LIKE '%creat%')
    #   - accessed (LIKE '%access%' OR '%read%')
    # Count alerts by severity:
    #   - critical (ai_risk_score >= 0.8)
    #   - high (ai_risk_score >= 0.6 AND < 0.8)
    #   - medium (ai_risk_score >= 0.4 AND < 0.6)
    #   - low (ai_risk_score < 0.4)
```

**Response Model:**
```python
class Stats(BaseModel):
    modified: int
    deleted: int
    created: int
    accessed: int
    critical: int
    high: int
    medium: int
    low: int
```

---

### 6. **get_agents()**
**Endpoint:** `GET /agents`  
**What it does:** Returns list of all monitored computers (agents)

```python
@app.get("/agents")
async def get_agents():
    """Get all agents grouped by hostname"""
    # Query client table
    # For each agent, count their associated alerts
    # Determine status: online (seen in last 5 min) or offline
    # Return hostname, last_seen timestamp, alert count, status
```

**Response:**
```json
{
  "agents": [
    {
      "id": 1,
      "hostname": "LAPTOP-001",
      "last_seen": "2024-12-18T14:32:45Z",
      "alert_count": 15,
      "status": "online"
    }
  ]
}
```

---

### 7. **get_agent_detail(agent_id)**
**Endpoint:** `GET /agents/{agent_id}`  
**What it does:** Returns detailed information about a specific agent and all its file alerts

```python
@app.get("/agents/{agent_id}", response_model=AgentDetailResponse)
async def get_agent_detail(agent_id: int):
    """Get agent details with all associated files"""
    # Get hostname for the agent
    # Query all alerts for agents with that hostname
    # Group by hostname (handles multiple instances)
    # Return agent info + list of up to 100 files with alerts
```

**Response:**
```python
class AgentDetailResponse(BaseModel):
    agent: Agent  # hostname, last_seen, alert_count, status
    files: List[AgentFile]  # 100 most recent file changes
```

---

### 8. **websocket_endpoint()**
**Endpoint:** `WebSocket /ws`  
**What it does:** Establishes real-time WebSocket connection for mobile app

```python
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates"""
    # Accept WebSocket connection
    # Add to connection manager's active connections list
    # Send initial scanner status
    # Keep connection alive
    # Receive keep-alive ping messages
    # Handle client disconnect
```

**Messages sent to client:**
- `{"type": "connected", "scanner_status": {...}}` - Initial connection
- `{"type": "new_alerts", "count": 5, "timestamp": "..."}` - New alerts available
- `{"type": "stats_update", "stats": {...}, "timestamp": "..."}` - Stats updated

---

### 9. **ConnectionManager class**
**What it does:** Manages WebSocket connections for broadcasting

```python
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        """Accept new WebSocket connection"""
        await websocket.accept()
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        """Remove disconnected client"""
        self.active_connections.remove(websocket)
    
    async def broadcast(self, message: dict):
        """Send message to all connected clients"""
        for connection in self.active_connections:
            await connection.send_json(message)
```

---

## ANDROID (Kotlin)

**Base Package:** `com.fimonacci.app`

---

### 1. **WebSocketManager.kt**
**File:** `android/app/src/main/java/com/fimonacci/app/data/websocket/WebSocketManager.kt`

#### Function: `connect()`
**What it does:** Establishes WebSocket connection to backend server

```kotlin
fun connect() {
    try {
        // Check if already connected
        // Convert HTTP URL to WebSocket (http:// → ws://, https:// → wss://)
        // Add /ws endpoint
        // Create OkHttp request
        // Create WebSocket listener
        // Update connection state to CONNECTING
        // Establish connection
    }
}
```

---

#### Function: `disconnect()`
**What it does:** Closes WebSocket connection and cleans up resources

```kotlin
fun disconnect() {
    // Cancel reconnect job
    // Close WebSocket with code 1000
    // Set connection state to DISCONNECTED
}
```

---

#### Function: `createWebSocketListener()`
**What it does:** Creates listener for WebSocket events (open, message, close, error)

```kotlin
private fun createWebSocketListener() = object : WebSocketListener() {
    override fun onOpen(webSocket: WebSocket, response: Response) {
        // Connection established
        // Update state to CONNECTED
    }
    
    override fun onMessage(webSocket: WebSocket, text: String) {
        // Message received from server
        // Parse JSON
        // Handle "new_alerts" message type
        // Handle "stats_update" message type
        // Emit signals to listeners
    }
    
    override fun onFailure(webSocket: WebSocket, t: Throwable, response: Response?) {
        // Connection failed
        // Update state to DISCONNECTED
        // Schedule reconnection attempt
    }
}
```

---

### 2. **DashboardViewModel.kt**
**File:** `android/app/src/main/java/com/fimonacci/app/ui/viewmodel/DashboardViewModel.kt`

#### Function: `loadData(showLoadingSpinner: Boolean = true)`
**What it does:** Fetches dashboard data (stats, alerts, agents) from backend API

```kotlin
fun loadData(showLoadingSpinner: Boolean = true) {
    viewModelScope.launch {
        _uiState.value = _uiState.value.copy(
            isLoading = showLoadingSpinner,
            isSyncing = !showLoadingSpinner
        )
        try {
            val serverUrl = preferencesManager.serverUrl.first()
            val apiService = RetrofitClient.getApiService(serverUrl)
            
            // Fetch from API
            val stats = apiService.getStats()
            val alertsResponse = apiService.getAlerts()
            val agentsResponse = apiService.getAgents()
            
            // Check for new alerts and send notifications
            // Update UI state
        }
    }
}
```

---

#### Function: `startRealTimeUpdates()`
**What it does:** Establishes real-time connection and sets up data listeners

```kotlin
private fun startRealTimeUpdates() {
    viewModelScope.launch {
        // Get server URL from preferences
        val serverUrl = preferencesManager.serverUrl.first()
        
        // Create WebSocketManager
        webSocketManager = WebSocketManager(serverUrl)
        
        // Connect WebSocket
        webSocketManager?.connect()
        
        // Set up fallback refresh (every 10 seconds)
        // Observe WebSocket connection state
        // Observe new alerts signal from WebSocket
        // Observe stats updates from WebSocket
        
        // Auto-refresh data when signals received
    }
}
```

---

#### Function: `stopRealTimeUpdates()`
**What it does:** Closes real-time connection and cleans up resources

```kotlin
private fun stopRealTimeUpdates() {
    // Cancel all collection jobs
    // Disconnect WebSocket
    // Clear connection state
}
```

---

### 3. **PreferencesManager.kt**
**File:** `android/app/src/main/java/com/fimonacci/app/data/preferences/PreferencesManager.kt`

#### Function: `saveServerUrl(url: String)`
**What it does:** Saves server URL to device preferences

```kotlin
suspend fun saveServerUrl(url: String) {
    // Validate URL format
    // Save to DataStore encrypted storage
    // Notify observers of change
}
```

---

#### Function: `getServerUrl()`
**What it does:** Retrieves server URL from device preferences

```kotlin
val serverUrl: Flow<String> = context.dataStore.data.map { preferences ->
    preferences[SERVER_URL_KEY] ?: ""
}
```

---

### 4. **NotificationManager.kt** (or NotificationHelper)
**File:** `android/app/src/main/java/com/fimonacci/app/utils/NotificationManager.kt`

#### Function: `showNotification(alert: Alert, soundEnabled: Boolean = true)`
**What it does:** Displays push notification for critical alerts

```kotlin
fun showNotification(context: Context, alert: Alert, soundEnabled: Boolean) {
    // Create notification channel (if Android 8+)
    // Set title based on alert severity
    // Set icon and color based on severity
    // Set sound and vibration if enabled
    // Show notification with NotificationManager
    // Make notification tappable to open AlertDetailScreen
}
```

---

### 5. **AlertsScreen.kt** (Composable)
**File:** `android/app/src/main/java/com/fimonacci/app/ui/screen/AlertsScreen.kt`

#### Function: `AlertsScreen(viewModel: DashboardViewModel, onAlertClick: (Alert) -> Unit)`
**What it does:** Displays list of all file integrity alerts

```kotlin
@Composable
fun AlertsScreen(
    viewModel: DashboardViewModel,
    onAlertClick: (Alert) -> Unit = {}
) {
    // Collect alerts from ViewModel
    val alerts = viewModel.uiState.collectAsState().value.alerts
    
    // Display as LazyColumn
    LazyColumn {
        items(alerts) { alert ->
            AlertListItem(
                alert = alert,
                onClick = { onAlertClick(alert) }
            )
        }
    }
    
    // Pull-to-refresh functionality
    // Loading spinner during data fetch
}
```

---

### 6. **DashboardScreen.kt** (Composable)
**File:** `android/app/src/main/java/com/fimonacci/app/ui/screen/DashboardScreen.kt`

#### Function: `DashboardScreen(viewModel: DashboardViewModel)`
**What it does:** Displays main dashboard with charts and stats

```kotlin
@Composable
fun DashboardScreen(viewModel: DashboardViewModel) {
    // Collect UI state
    val uiState = viewModel.uiState.collectAsState().value
    
    // Display:
    // 1. Real-time connection indicator
    // 2. Animated bar chart (modified, deleted, created, accessed)
    // 3. Animated pie chart (critical, high, medium, low)
    // 4. Quick stats cards
    // 5. Recent alerts preview
    
    // Pull-to-refresh to reload data
    // Error message if API fails
}
```

---

### 7. **AgentsScreen.kt** (Composable)
**File:** `android/app/src/main/java/com/fimonacci/app/ui/screen/AgentsScreen.kt`

#### Function: `AgentsScreen(viewModel: DashboardViewModel, onAgentClick: (Agent) -> Unit)`
**What it does:** Displays list of monitored computers/agents

```kotlin
@Composable
fun AgentsScreen(
    viewModel: DashboardViewModel,
    onAgentClick: (Agent) -> Unit = {}
) {
    // Collect agents from ViewModel
    val agents = viewModel.uiState.collectAsState().value.agents
    
    // Display as LazyColumn
    LazyColumn {
        items(agents) { agent ->
            AgentItem(
                agent = agent,
                isOnline = agent.status == "online",
                onClick = { onAgentClick(agent) }
            )
        }
    }
}
```

---

### 8. **AlertDetailScreen.kt** (Composable)
**File:** `android/app/src/main/java/com/fimonacci/app/ui/screen/AlertDetailScreen.kt`

#### Function: `AlertDetailScreen(alert: Alert, onBackClick: () -> Unit)`
**What it does:** Shows detailed information about a single alert

```kotlin
@Composable
fun AlertDetailScreen(
    alert: Alert,
    onBackClick: () -> Unit = {}
) {
    // Display:
    // 1. File name and full path
    // 2. Event type (CREATED, MODIFIED, DELETED)
    // 3. Severity with color (RED/ORANGE/YELLOW/GREEN)
    // 4. Timestamp of change
    // 5. Agent/Computer name
    // 6. Old hash (previous version)
    // 7. New hash (current version)
    // 8. Before/after comparison
}
```

---

### 9. **AgentDetailScreen.kt** (Composable)
**File:** `android/app/src/main/java/com/fimonacci/app/ui/screen/AgentDetailScreen.kt`

#### Function: `AgentDetailScreen(agentId: Int, onBackClick: () -> Unit)`
**What it does:** Shows all file alerts for a specific agent

```kotlin
@Composable
fun AgentDetailScreen(
    agentId: Int,
    onBackClick: () -> Unit = {}
) {
    // Display agent info:
    // - Hostname
    // - Status (online/offline)
    // - Last seen timestamp
    // - Total alert count
    
    // Display list of files with alerts (up to 100)
    // Each file shows:
    // - Filename
    // - Event type
    // - Severity
    // - Timestamp
}
```

---

## DATA MODELS

### Backend Models (Python Pydantic)

```python
class Alert:
    id: int
    filename: str
    agent_name: str
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW
    event_type: str
    timestamp: datetime
    old_hash: Optional[str]
    new_hash: Optional[str]
    file_path: str

class Stats:
    modified: int
    deleted: int
    created: int
    accessed: int
    critical: int
    high: int
    medium: int
    low: int

class Agent:
    id: int
    hostname: str
    last_seen: Optional[datetime]
    alert_count: int
    status: str  # "online" or "offline"

class AgentFile:
    id: int
    filename: str
    file_path: str
    alert_type: str
    severity: str
    timestamp: datetime
    old_hash: Optional[str]
    new_hash: Optional[str]
```

### Android Models (Kotlin Data Classes)

```kotlin
data class Alert(
    val id: Int,
    val filename: String,
    val agentName: String,
    val _severity: String,  // CRITICAL, HIGH, MEDIUM, LOW
    val _eventType: String,  // CREATED, MODIFIED, DELETED
    val timestamp: String,  // ISO format
    val oldHash: String?,
    val newHash: String?,
    val filePath: String
)

data class Stats(
    val modified: Int,
    val deleted: Int,
    val created: Int,
    val accessed: Int,
    val critical: Int = 0,
    val high: Int = 0,
    val medium: Int = 0,
    val low: Int = 0
)

data class Agent(
    val id: Int,
    val hostname: String,
    val lastSeen: String?,
    val alertCount: Int = 0,
    val status: String = "offline"
)
```

---

## API ENDPOINTS SUMMARY

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/` | Server health check |
| GET | `/alerts` | Get 50 most recent alerts |
| GET | `/stats` | Get statistics (counts by type/severity) |
| GET | `/scanner/status` | Get scanner state and metrics |
| POST | `/scanner/scan` | Manually trigger database scan |
| GET | `/agents` | List all monitored agents |
| GET | `/agents/{agent_id}` | Get agent details and file alerts |
| WebSocket | `/ws` | Real-time updates (alerts, stats) |

---

## REAL-TIME FLOW

### Mobile App (Consumer)
1. **Connect** → WebSocket `/ws`
2. **Receive** → `{"type": "connected"}`
3. **Listen** → For WebSocket messages
4. **On new_alerts** → Fetch `/alerts` to get fresh data
5. **On stats_update** → Fetch `/stats` for fresh stats
6. **Show notification** → If CRITICAL severity

### Backend (Producer)
1. **Scanner runs** → Every 2 seconds
2. **Detect changes** → Compare database state
3. **Calculate severity** → Based on ai_risk_score
4. **Queue broadcast** → Store in scanner_state
5. **Broadcast handler** → Sends to all WebSocket clients
6. **Mobile receives** → Updates UI and shows notification

---

## KEY FUNCTIONS SUMMARY TABLE

| Function | File | Purpose | Runs |
|----------|------|---------|------|
| `scan_database()` | main.py | Get alerts and stats from DB | Every 2s |
| `scanner_loop()` | main.py | Background scanning thread | Continuous |
| `broadcast_handler()` | main.py | WebSocket broadcasting | Continuous |
| `get_alerts()` | main.py | API endpoint for alerts | On request |
| `get_stats()` | main.py | API endpoint for stats | On request |
| `get_agents()` | main.py | API endpoint for agents | On request |
| `websocket_endpoint()` | main.py | Real-time WebSocket | On connection |
| `connect()` | WebSocketManager.kt | Establish WS connection | On demand |
| `loadData()` | DashboardViewModel.kt | Fetch API data | On demand |
| `startRealTimeUpdates()` | DashboardViewModel.kt | Start listening to WebSocket | On settings change |
| `showNotification()` | NotificationManager.kt | Show alert notification | On new CRITICAL alert |

