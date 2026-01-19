package com.fimonacci.app.ui.screen

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
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
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.fimonacci.app.data.model.Alert
import com.fimonacci.app.data.model.Severity
import com.fimonacci.app.ui.theme.*

/**
 * AlertDetailScreen - GitHub "PR Diff" Style
 *
 * Professional security-focused detail view with:
 * - File header with severity badge
 * - Metadata grid (Agent, User, Process, Time)
 * - Hash comparison diff view (BEFORE/AFTER with color coding)
 */
@Composable
fun AlertDetailScreen(
    alert: Alert,
    onBackClick: () -> Unit
) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(GitHubBackground)
            .verticalScroll(rememberScrollState())
    ) {
        // Top App Bar
        Surface(
            color = GitHubSurface,
            shadowElevation = 2.dp
        ) {
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(16.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                IconButton(onClick = onBackClick) {
                    Icon(
                        imageVector = Icons.Default.ArrowBack,
                        contentDescription = "Back",
                        tint = GitHubText
                    )
                }
                Text(
                    text = "Alert Details",
                    fontSize = 20.sp,
                    fontWeight = FontWeight.Bold,
                    color = GitHubText,
                    modifier = Modifier.padding(start = 8.dp)
                )
            }
        }

        Spacer(modifier = Modifier.height(16.dp))

        // Header: Filename + Severity Badge
        Card(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 16.dp, vertical = 8.dp)
                .border(1.dp, GitHubBorder, RoundedCornerShape(8.dp)),
            colors = CardDefaults.cardColors(containerColor = GitHubSurface),
            shape = RoundedCornerShape(8.dp)
        ) {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(16.dp)
            ) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        text = alert.filename,
                        fontSize = 24.sp,
                        fontWeight = FontWeight.Bold,
                        color = GitHubText,
                        fontFamily = FontFamily.Monospace,
                        modifier = Modifier.weight(1f)
                    )

                    SeverityBadgeLarge(severity = alert.severity)
                }

                Spacer(modifier = Modifier.height(8.dp))

                Text(
                    text = alert.filePath,
                    fontSize = 13.sp,
                    fontFamily = FontFamily.Monospace,
                    color = GitHubTextSecondary
                )
            }
        }

        // Metadata Grid Section
        Card(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 16.dp, vertical = 8.dp)
                .border(1.dp, GitHubBorder, RoundedCornerShape(8.dp)),
            colors = CardDefaults.cardColors(containerColor = GitHubSurface),
            shape = RoundedCornerShape(8.dp)
        ) {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(16.dp)
            ) {
                Text(
                    text = "Event Information",
                    fontSize = 14.sp,
                    fontWeight = FontWeight.Bold,
                    color = GitHubText,
                    modifier = Modifier.padding(bottom = 16.dp)
                )

                // Grid layout for metadata
                Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                    MetadataRowWithIcon(
                        icon = Icons.Outlined.Computer,
                        label = "Agent",
                        value = alert.agentName
                    )
                    MetadataRowWithIcon(
                        icon = Icons.Outlined.Person,
                        label = "User",
                        value = alert.user ?: "system"
                    )
                    MetadataRowWithIcon(
                        icon = Icons.Outlined.Settings,
                        label = "Process",
                        value = alert.processID ?: "N/A"
                    )
                    MetadataRowWithIcon(
                        icon = Icons.Outlined.Schedule,
                        label = "Time",
                        value = formatTimestamp(alert.timestamp)
                    )
                }
            }
        }

        // The Diff Section - Integrity Check (SHA256)
        if (alert.oldHash != null || alert.newHash != null) {
            Card(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 16.dp, vertical = 8.dp)
                    .border(1.dp, GitHubBorder, RoundedCornerShape(8.dp)),
                colors = CardDefaults.cardColors(containerColor = GitHubSurface),
                shape = RoundedCornerShape(8.dp)
            ) {
                Column(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(16.dp)
                ) {
                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        modifier = Modifier.padding(bottom = 12.dp)
                    ) {
                        Icon(
                            imageVector = Icons.Outlined.Fingerprint,
                            contentDescription = null,
                            tint = PrimaryAccent,
                            modifier = Modifier.size(20.dp)
                        )
                        Spacer(modifier = Modifier.width(8.dp))
                        Text(
                            text = "Integrity Check (SHA256)",
                            fontSize = 14.sp,
                            fontWeight = FontWeight.Bold,
                            color = GitHubText
                        )
                    }

                    // Warning if hashes don't match
                    if (alert.oldHash != null && alert.newHash != null && alert.oldHash != alert.newHash) {
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .background(DangerAlert.copy(alpha = 0.1f), RoundedCornerShape(6.dp))
                                .border(1.dp, DangerAlert.copy(alpha = 0.3f), RoundedCornerShape(6.dp))
                                .padding(12.dp),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Icon(
                                imageVector = Icons.Outlined.Warning,
                                contentDescription = null,
                                tint = DangerAlert,
                                modifier = Modifier.size(18.dp)
                            )
                            Spacer(modifier = Modifier.width(8.dp))
                            Text(
                                text = "File integrity compromised",
                                fontSize = 12.sp,
                                fontWeight = FontWeight.Medium,
                                color = DangerAlert
                            )
                        }
                        Spacer(modifier = Modifier.height(12.dp))
                    }

                    // BEFORE Hash (Red tint)
                    if (alert.oldHash != null) {
                        Column {
                            Text(
                                text = "BEFORE",
                                fontSize = 11.sp,
                                fontWeight = FontWeight.Bold,
                                color = GitHubTextSecondary,
                                letterSpacing = 0.5.sp,
                                modifier = Modifier.padding(bottom = 6.dp)
                            )
                            Row(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .background(
                                        EventDelete.copy(alpha = 0.12f),
                                        RoundedCornerShape(6.dp)
                                    )
                                    .border(
                                        1.dp,
                                        EventDelete.copy(alpha = 0.3f),
                                        RoundedCornerShape(6.dp)
                                    )
                                    .padding(12.dp),
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                Text(
                                    text = "−",
                                    fontSize = 16.sp,
                                    fontFamily = FontFamily.Monospace,
                                    fontWeight = FontWeight.Bold,
                                    color = EventDelete,
                                    modifier = Modifier.padding(end = 8.dp)
                                )
                                Text(
                                    text = alert.oldHash,
                                    fontSize = 11.sp,
                                    fontFamily = FontFamily.Monospace,
                                    color = GitHubText,
                                    lineHeight = 16.sp
                                )
                            }
                        }
                        Spacer(modifier = Modifier.height(12.dp))
                    }

                    // AFTER Hash (Green tint)
                    if (alert.newHash != null) {
                        Column {
                            Text(
                                text = "AFTER",
                                fontSize = 11.sp,
                                fontWeight = FontWeight.Bold,
                                color = GitHubTextSecondary,
                                letterSpacing = 0.5.sp,
                                modifier = Modifier.padding(bottom = 6.dp)
                            )
                            Row(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .background(
                                        EventCreate.copy(alpha = 0.12f),
                                        RoundedCornerShape(6.dp)
                                    )
                                    .border(
                                        1.dp,
                                        EventCreate.copy(alpha = 0.3f),
                                        RoundedCornerShape(6.dp)
                                    )
                                    .padding(12.dp),
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                Text(
                                    text = "+",
                                    fontSize = 16.sp,
                                    fontFamily = FontFamily.Monospace,
                                    fontWeight = FontWeight.Bold,
                                    color = EventCreate,
                                    modifier = Modifier.padding(end = 8.dp)
                                )
                                Text(
                                    text = alert.newHash,
                                    fontSize = 11.sp,
                                    fontFamily = FontFamily.Monospace,
                                    color = GitHubText,
                                    lineHeight = 16.sp
                                )
                            }
                        }
                    }
                }
            }
        }

        Spacer(modifier = Modifier.height(24.dp))
    }
}

/**
 * Metadata row with icon
 */
@Composable
private fun MetadataRowWithIcon(
    icon: ImageVector,
    label: String,
    value: String
) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Icon(
            imageVector = icon,
            contentDescription = null,
            tint = GitHubTextSecondary,
            modifier = Modifier.size(18.dp)
        )
        Spacer(modifier = Modifier.width(12.dp))
        Text(
            text = label,
            fontSize = 13.sp,
            color = GitHubTextSecondary,
            modifier = Modifier.width(80.dp)
        )
        Text(
            text = value,
            fontSize = 13.sp,
            fontWeight = FontWeight.Medium,
            color = GitHubText,
            fontFamily = FontFamily.Monospace
        )
    }
}

/**
 * Large severity badge for header
 */
@Composable
private fun SeverityBadgeLarge(severity: Severity) {
    val (text, color) = when (severity) {
        Severity.CRITICAL -> "CRITICAL" to SeverityCritical
        Severity.HIGH -> "HIGH" to SeverityHigh
        Severity.MEDIUM -> "MEDIUM" to SeverityMedium
        Severity.LOW -> "LOW" to SeverityLow
    }

    Box(
        modifier = Modifier
            .clip(RoundedCornerShape(16.dp))
            .background(color.copy(alpha = 0.15f))
            .border(1.5.dp, color, RoundedCornerShape(16.dp))
            .padding(horizontal = 14.dp, vertical = 6.dp)
    ) {
        Text(
            text = text,
            fontSize = 12.sp,
            fontWeight = FontWeight.Bold,
            color = color,
            letterSpacing = 0.8.sp
        )
    }
}

/**
 * Format timestamp
 */
private fun formatTimestamp(timestamp: String): String {
    return try {
        val parts = timestamp.split("T")
        if (parts.size == 2) {
            val date = parts[0].split("-")
            val time = parts[1].substring(0, 5)
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


