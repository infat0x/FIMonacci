package com.fimonacci.app.ui.screen

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.Edit
import androidx.compose.material.icons.filled.FileCopy
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.outlined.Wifi
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.viewmodel.compose.viewModel
import com.fimonacci.app.data.model.Alert
import com.fimonacci.app.data.model.Severity
import com.fimonacci.app.ui.theme.*
import com.fimonacci.app.ui.viewmodel.DashboardViewModel
import kotlinx.coroutines.delay
import androidx.compose.foundation.Canvas
import androidx.compose.animation.core.*
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import kotlin.math.cos
import kotlin.math.sin

@Composable
fun DashboardScreen(
    onAlertClick: (Alert) -> Unit,
    viewModel: DashboardViewModel
) {
    val uiState by viewModel.uiState.collectAsState()

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(GitHubBackground)
            .padding(16.dp)
    ) {
        // Header with status indicator
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text(
                text = "FIMonacci",
                fontSize = 24.sp,
                fontWeight = FontWeight.Bold,
                color = GitHubText,
                modifier = Modifier.padding(bottom = 8.dp)
            )

            // Right side status indicators
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                // Status indicator based on settings
                StatusIndicator(viewModel)

                IconButton(onClick = { viewModel.refresh() }) {
                    Icon(
                        imageVector = Icons.Default.Refresh,
                        contentDescription = "Refresh",
                        tint = GitHubText
                    )
                }
            }
        }

        if (uiState.isLoading) {
            Box(
                modifier = Modifier.fillMaxSize(),
                contentAlignment = Alignment.Center
            ) {
                CircularProgressIndicator(color = GitHubText)
            }
        } else if (uiState.error != null) {
            Box(
                modifier = Modifier.fillMaxSize(),
                contentAlignment = Alignment.Center
            ) {
                Column(horizontalAlignment = Alignment.CenterHorizontally) {
                    Text(
                        text = "Error: ${uiState.error}",
                        color = SeverityHigh
                    )
                    Spacer(modifier = Modifier.height(16.dp))
                    Button(onClick = { viewModel.refresh() }) {
                        Text("Retry")
                    }
                }
            }
        } else {
            // Stats Cards
            uiState.stats?.let { stats ->
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(bottom = 16.dp),
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    StatCard("Modified", stats.modified, EventModify, modifier = Modifier.weight(1f))
                    StatCard("Deleted", stats.deleted, EventDelete, modifier = Modifier.weight(1f))
                }
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(bottom = 16.dp),
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    StatCard("Created", stats.created, EventCreate, modifier = Modifier.weight(1f))
                    StatCard("Accessed", stats.accessed, EventAccess, modifier = Modifier.weight(1f))
                }

                // Animated Statistics Chart
                AnimatedStatsChart(stats = stats, modifier = Modifier.padding(bottom = 16.dp))
            }

            // Recent Activity
            Text(
                text = "Recent Activity",
                fontSize = 18.sp,
                fontWeight = FontWeight.SemiBold,
                color = GitHubText,
                modifier = Modifier.padding(bottom = 12.dp)
            )

            LazyColumn(
                verticalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                items(uiState.alerts) { alert ->
                    AlertListItem(alert = alert, onClick = { onAlertClick(alert) })
                }
            }
        }
    }
}

@Composable
fun StatCard(
    label: String,
    value: Int,
    color: Color,
    modifier: Modifier = Modifier
) {
    Card(
        modifier = modifier
            .height(80.dp)
            .border(1.dp, GitHubBorder, RoundedCornerShape(8.dp)),
        colors = CardDefaults.cardColors(containerColor = GitHubSurface),
        shape = RoundedCornerShape(8.dp)
    ) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(12.dp),
            verticalArrangement = Arrangement.SpaceBetween
        ) {
            Text(
                text = label,
                fontSize = 12.sp,
                color = GitHubTextSecondary
            )
            Text(
                text = value.toString(),
                fontSize = 24.sp,
                fontWeight = FontWeight.Bold,
                color = color
            )
        }
    }
}

@Composable
fun AlertListItem(
    alert: Alert,
    onClick: () -> Unit
) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .clickable(onClick = onClick)
            .border(1.dp, GitHubBorder, RoundedCornerShape(8.dp)),
        colors = CardDefaults.cardColors(containerColor = GitHubSurface),
        shape = RoundedCornerShape(8.dp)
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(12.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            // Icon based on event type
            Icon(
                imageVector = when (alert.eventType) {
                    "DELETE" -> Icons.Default.Delete
                    "MODIFY" -> Icons.Default.Edit
                    "CREATE" -> Icons.Default.FileCopy
                    else -> Icons.Default.FileCopy
                },
                contentDescription = alert.eventType,
                tint = when (alert.eventType) {
                    "DELETE" -> EventDelete
                    "MODIFY" -> EventModify
                    "CREATE" -> EventCreate
                    else -> EventAccess
                },
                modifier = Modifier.size(24.dp)
            )

            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = alert.filename,
                    fontSize = 14.sp,
                    fontWeight = FontWeight.Medium,
                    color = GitHubText,
                    maxLines = 1
                )
                Spacer(modifier = Modifier.height(4.dp))
                Text(
                    text = alert.agentName,
                    fontSize = 12.sp,
                    color = GitHubTextSecondary
                )
            }

            // Severity badge
            val severityColor = when (alert.severity) {
                Severity.HIGH, Severity.CRITICAL -> SeverityHigh
                Severity.MEDIUM -> SeverityMedium
                else -> SeverityLow
            }
            val surfaceColor = when (alert.severity) {
                Severity.HIGH, Severity.CRITICAL -> SeverityHigh.copy(alpha = 0.2f)
                Severity.MEDIUM -> SeverityMedium.copy(alpha = 0.2f)
                else -> SeverityLow.copy(alpha = 0.2f)
            }

            Surface(
                color = surfaceColor,
                shape = RoundedCornerShape(4.dp)
            ) {
                Text(
                    text = alert.severity.name,
                    fontSize = 10.sp,
                    fontWeight = FontWeight.Bold,
                    color = severityColor,
                    modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp)
                )
            }
        }
    }
}

@Composable
fun StatusIndicator(viewModel: DashboardViewModel) {
    val uiState by viewModel.uiState.collectAsState()

    // Get settings from viewModel's preferencesManager
    val context = androidx.compose.ui.platform.LocalContext.current
    val preferencesManager = remember { com.fimonacci.app.data.preferences.PreferencesManager(context) }
    val realTimeEnabled by preferencesManager.realTimeEnabled.collectAsState(initial = false)
    val autoRefreshEnabled by preferencesManager.autoRefreshEnabled.collectAsState(initial = false)
    val refreshInterval by preferencesManager.refreshInterval.collectAsState(initial = 30)

    when {
        // Real-time updates enabled - show persistent syncing indicator
        realTimeEnabled && uiState.realTimeConnected -> {
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(6.dp)
            ) {
                Icon(
                    imageVector = Icons.Outlined.Wifi,
                    contentDescription = "Real-time connected",
                    tint = SuccessColor,
                    modifier = Modifier.size(14.dp)
                )
                Text(
                    text = "Syncing",
                    fontSize = 12.sp,
                    color = SuccessColor,
                    fontWeight = FontWeight.Medium
                )
            }
        }
        // Auto-refresh enabled - show countdown timer
        autoRefreshEnabled -> {
            CircularCountdownTimer(refreshInterval)
        }
    }
}

@Composable
fun CircularCountdownTimer(intervalSeconds: Int) {
    var secondsRemaining by remember { mutableStateOf(intervalSeconds) }

    // Countdown timer
    LaunchedEffect(intervalSeconds) {
        secondsRemaining = intervalSeconds
        while (true) {
            delay(1000L)
            secondsRemaining = if (secondsRemaining > 0) secondsRemaining - 1 else intervalSeconds
        }
    }

    Box(
        modifier = Modifier.size(32.dp),
        contentAlignment = Alignment.Center
    ) {
        // Circular progress background
        Canvas(modifier = Modifier.size(32.dp)) {
            val progress = secondsRemaining.toFloat() / intervalSeconds.toFloat()

            // Background circle
            drawCircle(
                color = Color.Gray.copy(alpha = 0.3f),
                radius = size.minDimension / 2,
                style = Stroke(width = 3.dp.toPx())
            )

            // Progress arc
            drawArc(
                color = Color(0xFF58A6FF), // GitHub blue
                startAngle = -90f,
                sweepAngle = 360f * progress,
                useCenter = false,
                style = Stroke(
                    width = 3.dp.toPx(),
                    cap = StrokeCap.Round
                )
            )
        }

        // Countdown number
        Text(
            text = "$secondsRemaining",
            fontSize = 10.sp,
            fontWeight = FontWeight.Bold,
            color = GitHubText
        )
    }
}

@Composable
fun AnimatedStatsChart(
    stats: com.fimonacci.app.data.model.Stats,
    modifier: Modifier = Modifier
) {
    val total = stats.critical + stats.high + stats.medium + stats.low

    if (total == 0) return

    val animationProgress = remember { Animatable(0f) }

    LaunchedEffect(stats) {
        animationProgress.animateTo(
            targetValue = 1f,
            animationSpec = tween(durationMillis = 1000, easing = EaseOutCubic)
        )
    }

    Card(
        modifier = modifier
            .fillMaxWidth()
            .height(200.dp)
            .border(1.dp, GitHubBorder, RoundedCornerShape(8.dp)),
        colors = CardDefaults.cardColors(containerColor = GitHubSurface),
        shape = RoundedCornerShape(8.dp)
    ) {
        Row(
            modifier = Modifier
                .fillMaxSize()
                .padding(16.dp),
            horizontalArrangement = Arrangement.spacedBy(24.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            // Donut Chart
            Box(
                modifier = Modifier
                    .size(140.dp),
                contentAlignment = Alignment.Center
            ) {
                Canvas(modifier = Modifier.size(140.dp)) {
                    val strokeWidth = 20.dp.toPx()
                    val radius = (size.minDimension - strokeWidth) / 2
                    val centerX = size.width / 2
                    val centerY = size.height / 2

                    var currentAngle = -90f
                    val animatedProgress = animationProgress.value

                    // Critical
                    if (stats.critical > 0) {
                        val sweepAngle = (stats.critical.toFloat() / total * 360f) * animatedProgress
                        drawArc(
                            color = SeverityCritical,
                            startAngle = currentAngle,
                            sweepAngle = sweepAngle,
                            useCenter = false,
                            topLeft = Offset(centerX - radius, centerY - radius),
                            size = Size(radius * 2, radius * 2),
                            style = Stroke(width = strokeWidth, cap = StrokeCap.Round)
                        )
                        currentAngle += sweepAngle
                    }

                    // High
                    if (stats.high > 0) {
                        val sweepAngle = (stats.high.toFloat() / total * 360f) * animatedProgress
                        drawArc(
                            color = SeverityHigh,
                            startAngle = currentAngle,
                            sweepAngle = sweepAngle,
                            useCenter = false,
                            topLeft = Offset(centerX - radius, centerY - radius),
                            size = Size(radius * 2, radius * 2),
                            style = Stroke(width = strokeWidth, cap = StrokeCap.Round)
                        )
                        currentAngle += sweepAngle
                    }

                    // Medium
                    if (stats.medium > 0) {
                        val sweepAngle = (stats.medium.toFloat() / total * 360f) * animatedProgress
                        drawArc(
                            color = SeverityMedium,
                            startAngle = currentAngle,
                            sweepAngle = sweepAngle,
                            useCenter = false,
                            topLeft = Offset(centerX - radius, centerY - radius),
                            size = Size(radius * 2, radius * 2),
                            style = Stroke(width = strokeWidth, cap = StrokeCap.Round)
                        )
                        currentAngle += sweepAngle
                    }

                    // Low
                    if (stats.low > 0) {
                        val sweepAngle = (stats.low.toFloat() / total * 360f) * animatedProgress
                        drawArc(
                            color = SeverityLow,
                            startAngle = currentAngle,
                            sweepAngle = sweepAngle,
                            useCenter = false,
                            topLeft = Offset(centerX - radius, centerY - radius),
                            size = Size(radius * 2, radius * 2),
                            style = Stroke(width = strokeWidth, cap = StrokeCap.Round)
                        )
                    }
                }

                // Center text
                Column(
                    horizontalAlignment = Alignment.CenterHorizontally
                ) {
                    Text(
                        text = "$total",
                        fontSize = 24.sp,
                        fontWeight = FontWeight.Bold,
                        color = GitHubText
                    )
                    Text(
                        text = "Alerts",
                        fontSize = 12.sp,
                        color = GitHubTextSecondary
                    )
                }
            }

            // Legend - 2x2 Grid
            Column(
                modifier = Modifier.weight(1f),
                verticalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                // First row
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    ChartLegendItem("Critical", stats.critical, SeverityCritical, total, Modifier.weight(1f))
                    ChartLegendItem("High", stats.high, SeverityHigh, total, Modifier.weight(1f))
                }
                // Second row
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    ChartLegendItem("Medium", stats.medium, SeverityMedium, total, Modifier.weight(1f))
                    ChartLegendItem("Low", stats.low, SeverityLow, total, Modifier.weight(1f))
                }
            }
        }
    }
}

@Composable
fun ChartLegendItem(
    label: String,
    value: Int,
    color: Color,
    total: Int,
    modifier: Modifier = Modifier
) {
    Column(
        modifier = modifier,
        verticalArrangement = Arrangement.spacedBy(4.dp)
    ) {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(6.dp)
        ) {
            Box(
                modifier = Modifier
                    .size(10.dp)
                    .background(color, shape = androidx.compose.foundation.shape.CircleShape)
            )
            Text(
                text = label,
                fontSize = 13.sp,
                color = GitHubText,
                fontWeight = FontWeight.SemiBold,
                letterSpacing = 0.5.sp
            )
        }
        Text(
            text = "$value (${if (total > 0) (value * 100 / total) else 0}%)",
            fontSize = 14.sp,
            color = GitHubText,
            fontWeight = FontWeight.Bold,
            letterSpacing = 0.3.sp,
            modifier = Modifier.padding(start = 16.dp)
        )
    }
}
