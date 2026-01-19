package com.fimonacci.app.data.model

import com.google.gson.annotations.SerializedName

data class Agent(
    val id: Int,
    val hostname: String,
    @SerializedName("last_seen")
    val lastSeen: String?,
    @SerializedName("alert_count")
    val alertCount: Int,
    val status: String
) {
    val isOnline: Boolean
        get() = status == "online"
}

data class AgentsResponse(
    val agents: List<Agent>
)
