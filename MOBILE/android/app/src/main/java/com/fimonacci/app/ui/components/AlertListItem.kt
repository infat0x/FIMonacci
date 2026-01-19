package com.fimonacci.app.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.*
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.fimonacci.app.data.model.Alert
import com.fimonacci.app.data.model.EventAction
import com.fimonacci.app.data.model.Severity
import com.fimonacci.app.ui.theme.*

/**
 * AlertListItem - GitHub Issues Style Card
 *
 * Displays a single alert in the list with:
 * - Left: Action icon with color
 * - Center: File path (truncated, monospace) + metadata
 * - Right: Severity badge
 */
@Composable
fun AlertListItem(
    alert: Alert,
    onClick: () -> Unit,
    modifier: Modifier = Modifier
) {
    Card(
        modifier = modifier
            .fillMaxWidth()
            .padding(horizontal = 16.dp, vertical = 6.dp)
            .border(1.dp, GitHubBorder, RoundedCornerShape(8.dp))
            .clickable(onClick = onClick),
        colors = CardDefaults.cardColors(containerColor = GitHubSurface),
        shape = RoundedCornerShape(8.dp)
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            // Left: Event Action Icon
            EventActionIcon(
                eventAction = alert.eventAction,
                modifier = Modifier.padding(end = 12.dp)
            )

            // Center: File info
            Column(
                modifier = Modifier
                    .weight(1f)
                    .padding(end = 12.dp)
            ) {
                // File path (monospace, truncated)
                Text(
                    text = alert.filePath,
                    fontSize = 14.sp,
                    fontFamily = FontFamily.Monospace,
                    fontWeight = FontWeight.Medium,
                    color = GitHubText,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis
                )

                Spacer(modifier = Modifier.height(4.dp))

                // Subtitle: Agent • Timestamp
                Row(
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Icon(
                        imageVector = Icons.Outlined.Computer,
                        contentDescription = null,
                        tint = GitHubTextSecondary,
                        modifier = Modifier.size(14.dp)
                    )
                    Text(
                        text = " ${alert.agentName}",
                        fontSize = 12.sp,
                        color = GitHubTextSecondary
                    )
                    Text(
                        text = " • ",
                        fontSize = 12.sp,
                        color = GitHubTextSecondary
                    )
                    Text(
                        text = formatTimestamp(alert.timestamp),
                        fontSize = 12.sp,
                        color = GitHubTextSecondary
                    )
                }
            }

            // Right: Severity Badge
            SeverityBadge(severity = alert.severity)
        }
    }
}

/**
 * Event Action Icon - Colored icon based on file operation
 */
@Composable
private fun EventActionIcon(
    eventAction: EventAction,
    modifier: Modifier = Modifier
) {
    val (icon, color) = when (eventAction) {
        EventAction.MODIFIED -> Icons.Outlined.Edit to EventModify
        EventAction.DELETED -> Icons.Outlined.Delete to EventDelete
        EventAction.CREATED -> Icons.Outlined.AddCircleOutline to EventCreate
        EventAction.ACCESSED -> Icons.Outlined.Visibility to EventAccess
    }

    Box(
        modifier = modifier
            .size(40.dp)
            .background(color.copy(alpha = 0.15f), CircleShape),
        contentAlignment = Alignment.Center
    ) {
        Icon(
            imageVector = icon,
            contentDescription = eventAction.name,
            tint = color,
            modifier = Modifier.size(20.dp)
        )
    }
}

/**
 * Severity Badge - Small colored pill badge
 */
@Composable
private fun SeverityBadge(severity: Severity) {
    val (text, color) = when (severity) {
        Severity.CRITICAL -> "CRITICAL" to SeverityCritical
        Severity.HIGH -> "HIGH" to SeverityHigh
        Severity.MEDIUM -> "MEDIUM" to SeverityMedium
        Severity.LOW -> "LOW" to SeverityLow
    }

    Box(
        modifier = Modifier
            .clip(RoundedCornerShape(12.dp))
            .background(color.copy(alpha = 0.15f))
            .border(1.dp, color, RoundedCornerShape(12.dp))
            .padding(horizontal = 10.dp, vertical = 4.dp)
    ) {
        Text(
            text = text,
            fontSize = 10.sp,
            fontWeight = FontWeight.Bold,
            color = color,
            letterSpacing = 0.5.sp
        )
    }
}

/**
 * Format timestamp to human-readable format
 */
private fun formatTimestamp(timestamp: String): String {
    // Simple formatter - in production you'd use proper date parsing
    return try {
        // Assuming format like "2024-12-16T14:30:00"
        val parts = timestamp.split("T")
        if (parts.size == 2) {
            val date = parts[0].split("-")
            val time = parts[1].substring(0, 5) // HH:mm
            "${date[2]} ${getMonthName(date[1].toInt())}, $time"
        } else {
            timestamp
        }
    } catch (e: Exception) {
        timestamp
    }
}

private fun getMonthName(month: Int): String {
    return when (month) {
        1 -> "Jan"; 2 -> "Feb"; 3 -> "Mar"; 4 -> "Apr"
        5 -> "May"; 6 -> "Jun"; 7 -> "Jul"; 8 -> "Aug"
        9 -> "Sep"; 10 -> "Oct"; 11 -> "Nov"; 12 -> "Dec"
        else -> ""
    }
}
