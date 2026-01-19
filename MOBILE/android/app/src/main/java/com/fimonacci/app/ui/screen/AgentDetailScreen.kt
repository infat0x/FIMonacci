package com.fimonacci.app.ui.screen

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.Computer
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.fimonacci.app.data.api.RetrofitClient
import com.fimonacci.app.data.model.AgentFile
import com.fimonacci.app.data.model.AgentDetailResponse
import com.fimonacci.app.ui.theme.*
import kotlinx.coroutines.launch

@Composable
fun AgentDetailScreen(
    agentId: Int,
    onBackClick: () -> Unit
) {
    var agentDetail by remember { mutableStateOf<AgentDetailResponse?>(null) }
    var isLoading by remember { mutableStateOf(true) }
    var error by remember { mutableStateOf<String?>(null) }
    val coroutineScope = rememberCoroutineScope()

    // Load agent details
    LaunchedEffect(agentId) {
        coroutineScope.launch {
            try {
                isLoading = true
                error = null
                val apiService = RetrofitClient.getApiService()
                agentDetail = apiService.getAgentDetail(agentId)
                isLoading = false
            } catch (e: Exception) {
                error = "Failed to load agent details: ${e.message}"
                isLoading = false
            }
        }
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(GitHubBackground)
            .padding(16.dp)
    ) {
        // Header with back button
        Row(
            modifier = Modifier.fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically
        ) {
            IconButton(onClick = onBackClick) {
                Icon(
                    imageVector = Icons.Default.ArrowBack,
                    contentDescription = "Back",
                    tint = GitHubText
                )
            }
            Spacer(modifier = Modifier.width(8.dp))
            Text(
                text = "Agent Details",
                fontSize = 24.sp,
                fontWeight = FontWeight.Bold,
                color = GitHubText
            )
        }

        Spacer(modifier = Modifier.height(16.dp))

        when {
            isLoading -> {
                Box(
                    modifier = Modifier.fillMaxSize(),
                    contentAlignment = Alignment.Center
                ) {
                    CircularProgressIndicator(color = GitHubText)
                }
            }
            error != null -> {
                Box(
                    modifier = Modifier.fillMaxSize(),
                    contentAlignment = Alignment.Center
                ) {
                    Text(text = error!!, color = SeverityHigh)
                }
            }
            agentDetail != null -> {
                val agent = agentDetail!!.agent
                val files = agentDetail!!.files

                // Agent info card
                Card(
                    modifier = Modifier
                        .fillMaxWidth()
                        .border(1.dp, GitHubBorder, RoundedCornerShape(8.dp)),
                    colors = CardDefaults.cardColors(containerColor = GitHubSurface),
                    shape = RoundedCornerShape(8.dp)
                ) {
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(16.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Icon(
                            imageVector = Icons.Default.Computer,
                            contentDescription = "Agent",
                            tint = GitHubText,
                            modifier = Modifier.size(48.dp)
                        )
                        Spacer(modifier = Modifier.width(16.dp))
                        Column {
                            Text(
                                text = agent.hostname,
                                fontSize = 20.sp,
                                fontWeight = FontWeight.Bold,
                                color = GitHubText
                            )
                            Spacer(modifier = Modifier.height(4.dp))
                            Row(
                                verticalAlignment = Alignment.CenterVertically,
                                horizontalArrangement = Arrangement.spacedBy(12.dp),
                                modifier = Modifier.padding(top = 8.dp)
                            ) {
                                // Status
                                Row(
                                    verticalAlignment = Alignment.CenterVertically,
                                    horizontalArrangement = Arrangement.spacedBy(4.dp)
                                ) {
                                    Box(
                                        modifier = Modifier
                                            .size(10.dp)
                                            .background(
                                                if (agent.isOnline) SuccessColor else Color.Gray,
                                                shape = androidx.compose.foundation.shape.CircleShape
                                            )
                                    )
                                    Text(
                                        text = if (agent.isOnline) "Online" else "Offline",
                                        fontSize = 12.sp,
                                        color = GitHubTextSecondary
                                    )
                                }
                                // Alert count
                                Text(
                                    text = "${agent.alertCount} alerts",
                                    fontSize = 12.sp,
                                    color = GitHubTextSecondary
                                )
                            }
                        }
                    }
                }

                Spacer(modifier = Modifier.height(16.dp))

                // Files section
                Text(
                    text = "Associated Files (${files.size})",
                    fontSize = 18.sp,
                    fontWeight = FontWeight.SemiBold,
                    color = GitHubText,
                    modifier = Modifier.padding(bottom = 12.dp)
                )

                if (files.isEmpty()) {
                    Box(
                        modifier = Modifier.fillMaxSize(),
                        contentAlignment = Alignment.Center
                    ) {
                        Text(
                            text = "No file alerts for this agent",
                            color = GitHubTextSecondary
                        )
                    }
                } else {
                    LazyColumn(
                        verticalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        items(files) { file ->
                            AgentFileCard(file = file)
                        }
                    }
                }
            }
        }
    }
}

@Composable
fun AgentFileCard(file: AgentFile) {
    val severityColor = when (file.severity.name) {
        "CRITICAL" -> SeverityCritical
        "HIGH" -> SeverityHigh
        "MEDIUM" -> SeverityMedium
        else -> SeverityLow
    }

    val eventColor = when (file.eventAction.name) {
        "MODIFIED" -> EventModify
        "DELETED" -> EventDelete
        "CREATED" -> EventCreate
        "ACCESSED" -> EventAccess
        else -> EventModify
    }

    Card(
        modifier = Modifier
            .fillMaxWidth()
            .border(1.dp, GitHubBorder, RoundedCornerShape(8.dp)),
        colors = CardDefaults.cardColors(containerColor = GitHubSurface),
        shape = RoundedCornerShape(8.dp)
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(12.dp)
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = file.filename,
                    fontSize = 14.sp,
                    fontWeight = FontWeight.SemiBold,
                    color = GitHubText,
                    modifier = Modifier.weight(1f)
                )
                Surface(
                    color = severityColor.copy(alpha = 0.2f),
                    shape = RoundedCornerShape(4.dp)
                ) {
                    Text(
                        text = file.severity.name,
                        fontSize = 10.sp,
                        fontWeight = FontWeight.Bold,
                        color = severityColor,
                        modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp)
                    )
                }
            }

            Spacer(modifier = Modifier.height(4.dp))

            Text(
                text = file.filePath,
                fontSize = 12.sp,
                color = GitHubTextSecondary
            )

            Spacer(modifier = Modifier.height(8.dp))

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                Surface(
                    color = eventColor.copy(alpha = 0.2f),
                    shape = RoundedCornerShape(4.dp)
                ) {
                    Text(
                        text = file.eventAction.name,
                        fontSize = 10.sp,
                        fontWeight = FontWeight.Bold,
                        color = eventColor,
                        modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp)
                    )
                }

                Text(
                    text = file.timestamp.take(19).replace("T", " "),
                    fontSize = 11.sp,
                    color = GitHubTextSecondary
                )
            }
        }
    }
}
