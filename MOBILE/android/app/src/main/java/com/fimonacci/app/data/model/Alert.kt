package com.fimonacci.app.data.model

import com.google.gson.annotations.SerializedName

// Event Action Enum
enum class EventAction {
    MODIFIED,
    DELETED,
    CREATED,
    ACCESSED;

    companion object {
        fun fromString(value: String): EventAction {
            return when (value.uppercase()) {
                "MODIFIED", "MODIFY", "WRITE" -> MODIFIED
                "DELETED", "DELETE" -> DELETED
                "CREATED", "CREATE" -> CREATED
                "ACCESSED", "ACCESS", "READ" -> ACCESSED
                else -> MODIFIED
            }
        }
    }
}

// Severity Enum
enum class Severity {
    LOW,
    MEDIUM,
    HIGH,
    CRITICAL;

    companion object {
        fun fromString(value: String): Severity {
            return when (value.uppercase()) {
                "LOW" -> LOW
                "MEDIUM" -> MEDIUM
                "HIGH" -> HIGH
                "CRITICAL" -> CRITICAL
                else -> MEDIUM
            }
        }
    }
}

data class Alert(
    val id: Int,
    val filename: String,
    @SerializedName("agent_name")
    val agentName: String,
    @SerializedName("severity")
    private val _severity: String,
    @SerializedName("event_type")
    private val _eventType: String,
    val timestamp: String,
    @SerializedName("old_hash")
    val oldHash: String?,
    @SerializedName("new_hash")
    val newHash: String?,
    @SerializedName("file_path")
    val filePath: String,
    val user: String? = "system",
    @SerializedName("process_id")
    val processID: String? = "N/A"
) {
    val severity: Severity
        get() = Severity.fromString(_severity)

    val eventAction: EventAction
        get() = EventAction.fromString(_eventType)

    // Helper to get the event type as string for backward compatibility
    val eventType: String
        get() = _eventType
}


