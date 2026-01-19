package com.fimonacci.app.ui.screen

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.Refresh
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.fimonacci.app.data.model.Alert
import com.fimonacci.app.ui.components.AlertListItem
import com.fimonacci.app.ui.theme.*

/**
 * AlertsScreen - GitHub "Issues" Style List
 *
 * Displays a scrollable list of security alerts with:
 * - Header with title and refresh button
 * - Scrollable list of AlertListItem cards
 * - Empty state when no alerts
 * - Loading state
 */
@Composable
fun AlertsScreen(
    alerts: List<Alert>,
    isLoading: Boolean,
    onAlertClick: (Alert) -> Unit,
    onRefresh: () -> Unit,
    modifier: Modifier = Modifier
) {
    Column(
        modifier = modifier
            .fillMaxSize()
            .background(GitHubBackground)
    ) {
        // Header
        Surface(
            color = GitHubSurface,
            shadowElevation = 2.dp
        ) {
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(16.dp),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Column {
                    Text(
                        text = "Security Alerts",
                        fontSize = 24.sp,
                        fontWeight = FontWeight.Bold,
                        color = GitHubText
                    )
                    Text(
                        text = "${alerts.size} alerts",
                        fontSize = 14.sp,
                        color = GitHubTextSecondary
                    )
                }

                IconButton(onClick = onRefresh) {
                    Icon(
                        imageVector = Icons.Outlined.Refresh,
                        contentDescription = "Refresh",
                        tint = PrimaryAccent
                    )
                }
            }
        }

        // Content
        when {
            isLoading -> {
                Box(
                    modifier = Modifier.fillMaxSize(),
                    contentAlignment = Alignment.Center
                ) {
                    Column(
                        horizontalAlignment = Alignment.CenterHorizontally,
                        verticalArrangement = Arrangement.Center
                    ) {
                        CircularProgressIndicator(
                            color = PrimaryAccent,
                            modifier = Modifier.size(48.dp)
                        )
                        Spacer(modifier = Modifier.height(16.dp))
                        Text(
                            text = "Loading alerts...",
                            color = GitHubTextSecondary,
                            fontSize = 14.sp
                        )
                    }
                }
            }
            alerts.isEmpty() -> {
                EmptyAlertsState()
            }
            else -> {
                LazyColumn(
                    modifier = Modifier.fillMaxSize(),
                    contentPadding = PaddingValues(vertical = 8.dp)
                ) {
                    items(
                        items = alerts,
                        key = { it.id }
                    ) { alert ->
                        AlertListItem(
                            alert = alert,
                            onClick = { onAlertClick(alert) }
                        )
                    }
                }
            }
        }
    }
}

/**
 * Empty state when no alerts exist
 */
@Composable
private fun EmptyAlertsState() {
    Box(
        modifier = Modifier.fillMaxSize(),
        contentAlignment = Alignment.Center
    ) {
        Column(
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.Center
        ) {
            Icon(
                imageVector = Icons.Outlined.Refresh,
                contentDescription = null,
                tint = GitHubTextSecondary,
                modifier = Modifier.size(64.dp)
            )
            Spacer(modifier = Modifier.height(16.dp))
            Text(
                text = "No alerts found",
                fontSize = 18.sp,
                fontWeight = FontWeight.Medium,
                color = GitHubText
            )
            Text(
                text = "Your system is secure",
                fontSize = 14.sp,
                color = GitHubTextSecondary
            )
        }
    }
}
