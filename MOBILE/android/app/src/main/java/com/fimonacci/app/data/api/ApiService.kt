package com.fimonacci.app.data.api

import com.fimonacci.app.data.model.AgentDetailResponse
import com.fimonacci.app.data.model.AgentsResponse
import com.fimonacci.app.data.model.AlertsResponse
import com.fimonacci.app.data.model.Stats
import retrofit2.http.GET
import retrofit2.http.Path

interface ApiService {
    @GET("alerts")
    suspend fun getAlerts(): AlertsResponse

    @GET("stats")
    suspend fun getStats(): Stats

    @GET("agents")
    suspend fun getAgents(): AgentsResponse

    @GET("agents/{agentId}")
    suspend fun getAgentDetail(@Path("agentId") agentId: Int): AgentDetailResponse
}


