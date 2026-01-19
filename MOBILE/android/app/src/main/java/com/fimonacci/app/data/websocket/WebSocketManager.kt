package com.fimonacci.app.data.websocket

import android.util.Log
import com.fimonacci.app.data.model.Alert
import kotlinx.coroutines.*
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import okhttp3.*
import okio.ByteString
import org.json.JSONObject
import java.util.concurrent.TimeUnit

class WebSocketManager(private val baseUrl: String) {
    private var webSocket: WebSocket? = null
    private val client = OkHttpClient.Builder()
        .pingInterval(30, TimeUnit.SECONDS)
        .build()

    private val scope = CoroutineScope(Dispatchers.Main + SupervisorJob())
    
    private val _connectionState = MutableStateFlow<ConnectionState>(ConnectionState.Disconnected)
    val connectionState: StateFlow<ConnectionState> = _connectionState.asStateFlow()

    private val _newAlerts = MutableStateFlow<List<Alert>>(emptyList())
    val newAlerts: StateFlow<List<Alert>> = _newAlerts.asStateFlow()

    private val _statsUpdate = MutableStateFlow<StatsUpdate?>(null)
    val statsUpdate: StateFlow<StatsUpdate?> = _statsUpdate.asStateFlow()
    
    private var reconnectJob: Job? = null

    fun connect() {
        try {
            if (webSocket != null && _connectionState.value is ConnectionState.Connected) {
                return
            }

            // Ensure URL ends with / and convert to WebSocket URL
            val cleanUrl = baseUrl.trimEnd('/')
            val wsUrl = cleanUrl.replace("http://", "ws://").replace("https://", "wss://") + "/ws"
            val request = Request.Builder().url(wsUrl).build()
            
            scope.launch {
                _connectionState.value = ConnectionState.Connecting
            }
            webSocket = client.newWebSocket(request, createWebSocketListener())
        } catch (e: Exception) {
            Log.e("WebSocket", "Error connecting", e)
            scope.launch {
                _connectionState.value = ConnectionState.Disconnected
            }
        }
    }

    fun disconnect() {
        reconnectJob?.cancel()
        reconnectJob = null
        try {
            webSocket?.close(1000, "Client disconnect")
        } catch (e: Exception) {
            Log.e("WebSocket", "Error disconnecting", e)
        }
        webSocket = null
        scope.launch {
            _connectionState.value = ConnectionState.Disconnected
        }
    }

    private fun createWebSocketListener() = object : WebSocketListener() {
        override fun onOpen(webSocket: WebSocket, response: Response) {
            Log.d("WebSocket", "Connected")
            scope.launch {
                _connectionState.value = ConnectionState.Connected
            }
        }

        override fun onMessage(webSocket: WebSocket, text: String) {
            Log.d("WebSocket", "Message received: $text")
            try {
                val json = JSONObject(text)
                val messageType = json.getString("type")
                Log.d("WebSocket", "Message type: $messageType")
                
                scope.launch(Dispatchers.Main) {
                    try {
                        when (messageType) {
                            "new_alerts" -> {
                                val count = json.optInt("count", 0)
                                Log.d("WebSocket", "New alerts signal received: $count alerts")
                                // Trigger refresh by emitting a signal - the ViewModel will handle fetching new alerts
                                // We use a dummy alert just to signal that new alerts are available
                                _newAlerts.value = listOf(Alert(
                                    id = -1, // Special ID to indicate refresh signal
                                    filename = "New alerts available",
                                    agentName = "System",
                                    _severity = "MEDIUM", // Alert expects _severity as String
                                    _eventType = "UPDATE", // Alert expects _eventType as String
                                    timestamp = System.currentTimeMillis().toString(),
                                    oldHash = null,
                                    newHash = null,
                                    filePath = ""
                                ))
                                // Clear after processing to allow next trigger
                                delay(300)
                                _newAlerts.value = emptyList()
                            }
                            "stats_update" -> {
                                val stats = json.getJSONObject("stats")
                                Log.d("WebSocket", "Stats update received")
                                _statsUpdate.value = StatsUpdate(
                                    modified = stats.getInt("modified"),
                                    deleted = stats.getInt("deleted"),
                                    created = stats.getInt("created"),
                                    accessed = stats.getInt("accessed"),
                                    critical = stats.getInt("critical"),
                                    high = stats.getInt("high"),
                                    medium = stats.getInt("medium"),
                                    low = stats.getInt("low")
                                )
                            }
                            "connected" -> {
                                Log.d("WebSocket", "Connection confirmed")
                            }
                            else -> {
                                Log.d("WebSocket", "Unknown message type: $messageType")
                            }
                        }
                    } catch (e: Exception) {
                        Log.e("WebSocket", "Error processing message", e)
                    }
                }
            } catch (e: Exception) {
                Log.e("WebSocket", "Error parsing message: ${e.message}", e)
            }
        }

        override fun onMessage(webSocket: WebSocket, bytes: ByteString) {
            onMessage(webSocket, bytes.utf8())
        }

        override fun onClosing(webSocket: WebSocket, code: Int, reason: String) {
            Log.d("WebSocket", "Closing: $code - $reason")
            scope.launch {
                _connectionState.value = ConnectionState.Disconnecting
            }
        }

        override fun onClosed(webSocket: WebSocket, code: Int, reason: String) {
            Log.d("WebSocket", "Closed: $code - $reason")
            scope.launch {
                _connectionState.value = ConnectionState.Disconnected
            }
        }

        override fun onFailure(webSocket: WebSocket, t: Throwable, response: Response?) {
            Log.e("WebSocket", "Failure", t)
            scope.launch {
                _connectionState.value = ConnectionState.Disconnected
            }
            // Auto-reconnect after delay using coroutines
            reconnectJob?.cancel()
            reconnectJob = scope.launch {
                delay(5000)
                if (_connectionState.value !is ConnectionState.Connected) {
                    try {
                        connect()
                    } catch (e: Exception) {
                        Log.e("WebSocket", "Error reconnecting", e)
                    }
                }
            }
        }
    }
    
    fun cleanup() {
        disconnect()
        scope.cancel()
    }

    sealed class ConnectionState {
        object Disconnected : ConnectionState()
        object Connecting : ConnectionState()
        object Connected : ConnectionState()
        object Disconnecting : ConnectionState()
    }

    data class StatsUpdate(
        val modified: Int,
        val deleted: Int,
        val created: Int,
        val accessed: Int,
        val critical: Int,
        val high: Int,
        val medium: Int,
        val low: Int
    )
}
