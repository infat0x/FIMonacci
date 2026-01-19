package com.fimonacci.app.data.model

import com.google.gson.annotations.SerializedName

data class AgentFile(
    val id: Int,
    val filename: String,
    @SerializedName("file_path")
    val filePath: String,
    @SerializedName("alert_type")
    private val _alertType: String,
    @SerializedName("severity")
    private val _severity: String,
    val timestamp: String,
    @SerializedName("old_hash")
    val oldHash: String?,
    @SerializedName("new_hash")
    val newHash: String?
) {
    val severity: Severity
        get() = Severity.fromString(_severity)

    val eventAction: EventAction
        get() = EventAction.fromString(_alertType)

    val alertType: String
        get() = _alertType
}

data class AgentDetailResponse(
    val agent: Agent,
    val files: List<AgentFile>
)
