package com.fimonacci.app.ui.screen

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Computer
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.fimonacci.app.data.model.Agent
import com.fimonacci.app.ui.theme.*

/**
 * AgentsScreen - Grid display of monitored servers/agents
 */
@Composable
fun AgentsScreen(
    agents: List<Agent>,
    isLoading: Boolean,
    onAgentClick: (Agent) -> Unit,
    modifier: Modifier = Modifier
) {
    Column(
        modifier = modifier
            .fillMaxSize()
            .background(GitHubBackground)
            .padding(16.dp)
    ) {
        // Header
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Column {
                Text(
                    text = "Agents",
                    fontSize = 24.sp,
                    fontWeight = FontWeight.Bold,
                    color = GitHubText
                )
                Text(
                    text = "${agents.count { it.isOnline }} online",
                    fontSize = 14.sp,
                    color = GitHubTextSecondary
                )
            }
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
            agents.isEmpty() -> {
                Box(
                    modifier = Modifier.fillMaxSize(),
                    contentAlignment = Alignment.Center
                ) {
                    Text(
                        text = "No agents found",
                        color = GitHubTextSecondary
                    )
                }
            }
            else -> {
                LazyVerticalGrid(
                    columns = GridCells.Fixed(3),
                    horizontalArrangement = Arrangement.spacedBy(12.dp),
                    verticalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    items(agents) { agent ->
                        AgentGridCard(agent = agent, onClick = { onAgentClick(agent) })
                    }
                }
            }
        }
    }
}

@Composable
fun AgentGridCard(
    agent: Agent,
    onClick: () -> Unit
) {
    val statusColor = if (agent.isOnline) SuccessColor else Color.Gray
    val backgroundColor = if (agent.isOnline) GitHubSurface else GitHubSurface.copy(alpha = 0.6f)

    Card(
        modifier = Modifier
            .size(100.dp)
            .clickable(onClick = onClick)
            .border(1.dp, GitHubBorder, RoundedCornerShape(8.dp)),
        colors = CardDefaults.cardColors(containerColor = backgroundColor),
        shape = RoundedCornerShape(8.dp)
    ) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(8.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.Center
        ) {
            // Icon with status indicator
            Box(contentAlignment = Alignment.TopEnd) {
                Icon(
                    imageVector = Icons.Default.Computer,
                    contentDescription = "Agent",
                    tint = GitHubText,
                    modifier = Modifier.size(32.dp)
                )
                // Status dot
                Box(
                    modifier = Modifier
                        .size(10.dp)
                        .background(statusColor, shape = androidx.compose.foundation.shape.CircleShape)
                )
            }

            Spacer(modifier = Modifier.height(4.dp))

            // Agent hostname
            Text(
                text = agent.hostname,
                fontSize = 11.sp,
                fontWeight = FontWeight.Medium,
                color = GitHubText,
                maxLines = 1
            )

            // Alert count badge
            if (agent.alertCount > 0) {
                Surface(
                    modifier = Modifier
                        .padding(top = 2.dp),
                    color = SeverityHigh.copy(alpha = 0.2f),
                    shape = RoundedCornerShape(4.dp)
                ) {
                    Text(
                        text = "${agent.alertCount}",
                        fontSize = 10.sp,
                        fontWeight = FontWeight.Bold,
                        color = SeverityHigh,
                        modifier = Modifier.padding(horizontal = 6.dp, vertical = 2.dp)
                    )
                }
            }
        }
    }
}
