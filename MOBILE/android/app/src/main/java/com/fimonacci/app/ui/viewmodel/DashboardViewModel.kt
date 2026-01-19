package com.fimonacci.app.ui.viewmodel

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.fimonacci.app.data.api.RetrofitClient
import com.fimonacci.app.data.model.Agent
import com.fimonacci.app.data.model.Alert
import com.fimonacci.app.data.model.Stats
import com.fimonacci.app.data.preferences.PreferencesManager
import com.fimonacci.app.data.websocket.WebSocketManager
import com.fimonacci.app.utils.NotificationHelper
import kotlinx.coroutines.flow.*
import kotlinx.coroutines.launch
import kotlinx.coroutines.delay
import android.util.Log

data class DashboardUiState(
    val stats: Stats? = null,
    val alerts: List<Alert> = emptyList(),
    val agents: List<Agent> = emptyList(),
    val isLoading: Boolean = false,
    val isSyncing: Boolean = false,
    val error: String? = null,
    val realTimeConnected: Boolean = false
)

class DashboardViewModel(application: Application) : AndroidViewModel(application) {
    private val _uiState = MutableStateFlow(DashboardUiState())
    val uiState: StateFlow<DashboardUiState> = _uiState.asStateFlow()
    
    private val preferencesManager = PreferencesManager(application)
    private var webSocketManager: WebSocketManager? = null
    private var previousAlertsCount = 0
    private var webSocketCollectionJobs = mutableListOf<kotlinx.coroutines.Job>()

    init {
        loadData()
        observeRealTimeSetting()
    }
    
    private fun observeRealTimeSetting() {
        viewModelScope.launch {
            preferencesManager.realTimeEnabled.collect { enabled ->
                if (enabled) {
                    startRealTimeUpdates()
                } else {
                    stopRealTimeUpdates()
                }
            }
        }
        
        // Observe notifications setting for showing notifications
        viewModelScope.launch {
            preferencesManager.notificationsEnabled.collect {
                // Setting changed, will be used when new alerts arrive
            }
        }
    }
    
    private fun startRealTimeUpdates() {
        // Stop any existing connection first
        stopRealTimeUpdates()
        
        viewModelScope.launch {
            try {
                val serverUrl = preferencesManager.serverUrl.first()
                if (serverUrl.isBlank()) {
                    Log.e("DashboardViewModel", "Server URL is blank")
                    return@launch
                }
                
                Log.d("DashboardViewModel", "Starting real-time updates with URL: $serverUrl")
                webSocketManager = WebSocketManager(serverUrl)
                
                // Connect WebSocket
                webSocketManager?.connect()
                
                // Wait a bit for connection to establish
                delay(1000)
                
                // Periodic fallback refresh every 10 seconds (in case WebSocket misses updates)
                val fallbackJob = launch {
                    while (true) {
                        delay(10000) // 10 seconds
                        if (_uiState.value.realTimeConnected) {
                            Log.d("DashboardViewModel", "Periodic fallback refresh")
                            loadData(showLoadingSpinner = false)
                        } else {
                            break
                        }
                    }
                }
                webSocketCollectionJobs.add(fallbackJob)
                
                // Observe WebSocket connection state in separate coroutine
                val connectionJob = launch {
                    try {
                        webSocketManager?.connectionState?.collect { state ->
                            _uiState.value = _uiState.value.copy(
                                realTimeConnected = state is WebSocketManager.ConnectionState.Connected
                            )
                        }
                    } catch (e: Exception) {
                        Log.e("DashboardViewModel", "Error collecting connection state", e)
                    }
                }
                webSocketCollectionJobs.add(connectionJob)
                
                // Observe new alerts from WebSocket in separate coroutine
                val alertsJob = launch {
                    try {
                        var lastSignalId = -1L
                        webSocketManager?.newAlerts?.collect { alerts ->
                            if (alerts.isNotEmpty() && alerts.first().id == -1) {
                                val currentTime = System.currentTimeMillis()
                                // Only process if we haven't seen this signal recently (avoid duplicates)
                                if (currentTime - lastSignalId > 500) {
                                    Log.d("DashboardViewModel", "WebSocket signal received, refreshing data...")
                                    lastSignalId = currentTime
                                    // Refresh data when new alerts arrive (id == -1 is the refresh signal)
                                    loadData(showLoadingSpinner = false)
                                }
                            }
                        }
                    } catch (e: Exception) {
                        Log.e("DashboardViewModel", "Error collecting new alerts", e)
                    }
                }
                webSocketCollectionJobs.add(alertsJob)
                
                // Observe stats updates in separate coroutine
                val statsJob = launch {
                    try {
                        var lastStatsHash: Int? = null
                        webSocketManager?.statsUpdate?.collect { statsUpdate ->
                            statsUpdate?.let {
                                // Create a hash to detect actual changes
                                val statsHash = (it.modified * 1000 + it.deleted * 100 + it.created * 10 + it.accessed).hashCode()
                                
                                if (statsHash != lastStatsHash) {
                                    Log.d("DashboardViewModel", "Stats update received: modified=${it.modified}, deleted=${it.deleted}, created=${it.created}, accessed=${it.accessed}")
                                    lastStatsHash = statsHash

                                    // Update stats
                                    val currentState = _uiState.value
                                    _uiState.value = currentState.copy(
                                        stats = Stats(
                                            modified = it.modified,
                                            deleted = it.deleted,
                                            created = it.created,
                                            accessed = it.accessed,
                                            critical = it.critical,
                                            high = it.high,
                                            medium = it.medium,
                                            low = it.low
                                        )
                                    )
                                    
                                    // Also refresh alerts when stats change (indicates new data)
                                    Log.d("DashboardViewModel", "Stats changed, refreshing alerts...")
                                    loadData()
                                }
                            }
                        }
                    } catch (e: Exception) {
                        Log.e("DashboardViewModel", "Error collecting stats update", e)
                    }
                }
                webSocketCollectionJobs.add(statsJob)
            } catch (e: Exception) {
                Log.e("DashboardViewModel", "Error starting real-time updates", e)
                _uiState.value = _uiState.value.copy(
                    error = "Failed to start real-time updates: ${e.message}",
                    realTimeConnected = false
                )
            }
        }
    }
    
    private fun stopRealTimeUpdates() {
        // Cancel all collection jobs
        webSocketCollectionJobs.forEach { it.cancel() }
        webSocketCollectionJobs.clear()
        
        // Disconnect and cleanup WebSocket
        try {
            webSocketManager?.cleanup()
        } catch (e: Exception) {
            // Ignore cleanup errors
        }
        webSocketManager = null
        _uiState.value = _uiState.value.copy(realTimeConnected = false)
    }

    fun loadData(showLoadingSpinner: Boolean = true) {
        viewModelScope.launch {
            // If real-time is enabled, show syncing indicator instead of loading spinner
            val isRealTimeEnabled = preferencesManager.realTimeEnabled.first()

            if (showLoadingSpinner && !isRealTimeEnabled) {
                _uiState.value = _uiState.value.copy(isLoading = true, error = null)
            } else {
                _uiState.value = _uiState.value.copy(isSyncing = true, error = null)
            }
            try {
                // Get current server URL from settings
                val serverUrl = preferencesManager.serverUrl.first()
                val apiService = RetrofitClient.getApiService(serverUrl)

                val stats = apiService.getStats()
                val alertsResponse = apiService.getAlerts()
                val agentsResponse = apiService.getAgents()

                // Check for new alerts and show notifications for EACH new alert
                if (previousAlertsCount > 0) {
                    val notificationsEnabled = preferencesManager.notificationsEnabled.first()
                    val soundEnabled = preferencesManager.soundEnabled.first()

                    if (notificationsEnabled && alertsResponse.alerts.isNotEmpty()) {
                        // Get the IDs of previously cached alerts
                        val previousAlertIds = _uiState.value.alerts.map { it.id }.toSet()

                        // Find alerts that are new (not in previous cache)
                        val newAlerts = alertsResponse.alerts.filter { it.id !in previousAlertIds }

                        // Send notification for EACH new alert
                        newAlerts.forEach { alert ->
                            NotificationHelper.showNotification(
                                getApplication(),
                                alert,
                                soundEnabled
                            )
                        }
                    }
                }

                previousAlertsCount = alertsResponse.alerts.size

                _uiState.value = _uiState.value.copy(
                    stats = stats,
                    alerts = alertsResponse.alerts,
                    agents = agentsResponse.agents,
                    isLoading = false,
                    isSyncing = false,
                    error = null
                )
            } catch (e: retrofit2.HttpException) {
                val errorMsg = when (e.code()) {
                    500 -> "Server error (500). Please check backend logs."
                    404 -> "API endpoint not found (404)"
                    else -> "HTTP ${e.code()}: ${e.message()}"
                }
                _uiState.value = _uiState.value.copy(
                    isLoading = false,
                    isSyncing = false,
                    error = errorMsg
                )
            } catch (e: java.net.ConnectException) {
                _uiState.value = _uiState.value.copy(
                    isLoading = false,
                    isSyncing = false,
                    error = "Cannot connect to server. Check if backend is running and IP address is correct."
                )
            } catch (e: java.net.SocketTimeoutException) {
                _uiState.value = _uiState.value.copy(
                    isLoading = false,
                    isSyncing = false,
                    error = "Connection timeout. Server is not responding."
                )
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(
                    isLoading = false,
                    isSyncing = false,
                    error = e.message ?: "Unknown error occurred"
                )
            }
        }
    }

    fun refresh() {
        loadData()
    }

    fun refreshAlerts() {
        loadData()
    }
    
    override fun onCleared() {
        super.onCleared()
        stopRealTimeUpdates()
    }
}


