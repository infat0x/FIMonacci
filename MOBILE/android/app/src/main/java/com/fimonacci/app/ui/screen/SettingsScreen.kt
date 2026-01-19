package com.fimonacci.app.ui.screen

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.viewmodel.compose.viewModel
import com.fimonacci.app.ui.theme.*
import com.fimonacci.app.ui.viewmodel.SettingsViewModel

/**
 * SettingsScreen - App configuration and preferences
 */
@Composable
fun SettingsScreen(
    modifier: Modifier = Modifier,
    onRefreshTriggered: () -> Unit = {},
    actualViewModel: SettingsViewModel? = null
) {
    val viewModel: SettingsViewModel = actualViewModel ?: run {
        val context = androidx.compose.ui.platform.LocalContext.current
        androidx.lifecycle.viewmodel.compose.viewModel(
            factory = androidx.lifecycle.ViewModelProvider.AndroidViewModelFactory.getInstance(
                context.applicationContext as android.app.Application
            )
        )
    }
    val uiState by viewModel.uiState.collectAsState()
    var showServerDialog by remember { mutableStateOf(false) }
    var showAboutDialog by remember { mutableStateOf(false) }
    var editServerUrl by remember { mutableStateOf("") }

    // Auto-refresh effect
    LaunchedEffect(uiState.autoRefreshEnabled, uiState.refreshInterval) {
        if (uiState.autoRefreshEnabled) {
            while (true) {
                kotlinx.coroutines.delay(uiState.refreshInterval * 1000L)
                onRefreshTriggered()
            }
        }
    }

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
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = "Settings",
                    fontSize = 24.sp,
                    fontWeight = FontWeight.Bold,
                    color = GitHubText
                )
            }
        }

        // Settings List
        LazyColumn(
            modifier = Modifier.fillMaxSize(),
            contentPadding = PaddingValues(vertical = 8.dp)
        ) {
            item {
                SettingsSectionHeader("Appearance")
            }
            item {
                SettingsSwitchItem(
                    icon = Icons.Outlined.Brightness4,
                    title = "Dark Mode",
                    subtitle = "Use dark theme",
                    checked = uiState.darkModeEnabled,
                    onCheckedChange = { viewModel.toggleDarkMode(it) }
                )
            }

            item {
                SettingsSectionHeader("Notifications")
            }
            item {
                SettingsSwitchItem(
                    icon = Icons.Outlined.Notifications,
                    title = "Enable Notifications",
                    subtitle = "Receive alert notifications",
                    checked = uiState.notificationsEnabled,
                    onCheckedChange = { viewModel.toggleNotifications(it) }
                )
            }
            item {
                SettingsSwitchItem(
                    icon = Icons.Outlined.Notifications,
                    title = "Sound",
                    subtitle = "Play sound for alerts",
                    checked = uiState.soundEnabled,
                    onCheckedChange = { viewModel.toggleSound(it) },
                    enabled = uiState.notificationsEnabled
                )
            }

            item {
                SettingsSectionHeader("Data Refresh")
            }
            item {
                SettingsSwitchItem(
                    icon = Icons.Outlined.Refresh,
                    title = "Auto Refresh",
                    subtitle = "Automatically refresh alerts every ${uiState.refreshInterval}s",
                    checked = uiState.autoRefreshEnabled,
                    onCheckedChange = { viewModel.toggleAutoRefresh(it, onRefreshTriggered) }
                )
            }
            item {
                SettingsSliderItem(
                    icon = Icons.Outlined.Schedule,
                    title = "Refresh Interval",
                    subtitle = "${uiState.refreshInterval} seconds",
                    value = uiState.refreshInterval.toFloat(),
                    onValueChange = { viewModel.setRefreshInterval(it.toInt()) },
                    valueRange = 10f..120f,
                    enabled = uiState.autoRefreshEnabled
                )
            }
            item {
                SettingsSwitchItem(
                    icon = Icons.Outlined.Wifi,
                    title = "Real-Time Updates",
                    subtitle = "Receive instant alerts via WebSocket",
                    checked = uiState.realTimeEnabled,
                    onCheckedChange = { viewModel.toggleRealTime(it) }
                )
            }

            item {
                SettingsSectionHeader("Connection")
            }
            item {
                SettingsItem(
                    icon = Icons.Outlined.Settings,
                    title = "Server Configuration",
                    subtitle = uiState.serverUrl,
                    onClick = {
                        editServerUrl = uiState.serverUrl
                        showServerDialog = true
                    }
                )
            }
            item {
                SettingsItem(
                    icon = Icons.Outlined.CheckCircle,
                    title = "Connection Status",
                    subtitle = "Connected",
                    onClick = {}
                )
            }

            item {
                SettingsSectionHeader("Security")
            }
            item {
                SettingsItem(
                    icon = Icons.Outlined.Lock,
                    title = "Data Encryption",
                    subtitle = "Enabled (TLS 1.3)",
                    onClick = {}
                )
            }
            item {
                SettingsItem(
                    icon = Icons.Outlined.VerifiedUser,
                    title = "Authentication",
                    subtitle = "Token-based auth",
                    onClick = {}
                )
            }

            item {
                SettingsSectionHeader("Storage")
            }
            item {
                SettingsItem(
                    icon = Icons.Outlined.Folder,
                    title = "Cache Size",
                    subtitle = "12.4 MB",
                    onClick = {}
                )
            }
            item {
                SettingsItem(
                    icon = Icons.Outlined.Delete,
                    title = "Clear Cache",
                    subtitle = "Free up storage space",
                    onClick = {}
                )
            }

            item {
                SettingsSectionHeader("About")
            }
            item {
                SettingsItem(
                    icon = Icons.Outlined.Info,
                    title = "Version",
                    subtitle = "FIMonacci v1.0.0",
                    onClick = { showAboutDialog = true }
                )
            }
            item {
                SettingsItem(
                    icon = Icons.Outlined.Build,
                    title = "Build",
                    subtitle = "Debug (December 2025)",
                    onClick = {}
                )
            }
            item {
                SettingsItem(
                    icon = Icons.Outlined.Refresh,
                    title = "Check for Updates",
                    subtitle = "You're up to date",
                    onClick = {}
                )
            }
        }
    }

    // Dialogs
    if (showServerDialog) {
        AlertDialog(
            onDismissRequest = { showServerDialog = false },
            icon = { Icon(Icons.Outlined.Settings, contentDescription = null) },
            title = { Text("Server Configuration") },
            text = {
                Column {
                    Text("Server URL:", fontWeight = FontWeight.Medium)
                    Spacer(modifier = Modifier.height(8.dp))
                    OutlinedTextField(
                        value = editServerUrl,
                        onValueChange = { editServerUrl = it },
                        label = { Text("URL") },
                        placeholder = { Text("http://192.168.1.67:8000") },
                        singleLine = true,
                        modifier = Modifier.fillMaxWidth()
                    )
                    Spacer(modifier = Modifier.height(8.dp))
                    Text(
                        "Note: Server URL changes require app restart to take effect.",
                        fontSize = 12.sp,
                        color = GitHubTextSecondary
                    )
                }
            },
            confirmButton = {
                TextButton(
                    onClick = {
                        if (editServerUrl.isNotBlank()) {
                            viewModel.updateServerUrl(editServerUrl)
                        }
                        showServerDialog = false
                    }
                ) {
                    Text("Save")
                }
            },
            dismissButton = {
                TextButton(onClick = { showServerDialog = false }) {
                    Text("Cancel")
                }
            }
        )
    }

    if (showAboutDialog) {
        AlertDialog(
            onDismissRequest = { showAboutDialog = false },
            icon = { Icon(Icons.Outlined.Info, contentDescription = null) },
            title = { Text("About FIMonacci") },
            text = {
                Column {
                    Text("FIMonacci File Integrity Monitor", fontWeight = FontWeight.Bold)
                    Spacer(modifier = Modifier.height(8.dp))
                    Text("Version 1.0.0")
                    Spacer(modifier = Modifier.height(4.dp))
                    Text("Build: Debug")
                    Spacer(modifier = Modifier.height(12.dp))
                    Text(
                        "A comprehensive file integrity monitoring solution for tracking and analyzing file system changes.",
                        fontSize = 14.sp,
                        color = GitHubTextSecondary
                    )
                }
            },
            confirmButton = {
                TextButton(onClick = { showAboutDialog = false }) {
                    Text("Close")
                }
            }
        )
    }
}

@Composable
private fun SettingsSectionHeader(title: String) {
    Text(
        text = title,
        fontSize = 12.sp,
        fontWeight = FontWeight.Bold,
        color = GitHubTextSecondary,
        modifier = Modifier.padding(horizontal = 16.dp, vertical = 12.dp)
    )
}

@Composable
private fun SettingsItem(
    icon: ImageVector,
    title: String,
    subtitle: String,
    onClick: () -> Unit
) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 16.dp, vertical = 4.dp)
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
            Icon(
                imageVector = icon,
                contentDescription = null,
                tint = PrimaryAccent,
                modifier = Modifier.size(24.dp)
            )

            Spacer(modifier = Modifier.width(16.dp))

            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = title,
                    fontSize = 16.sp,
                    fontWeight = FontWeight.Medium,
                    color = GitHubText
                )
                Text(
                    text = subtitle,
                    fontSize = 13.sp,
                    color = GitHubTextSecondary
                )
            }

            Icon(
                imageVector = Icons.Outlined.ChevronRight,
                contentDescription = null,
                tint = GitHubTextSecondary,
                modifier = Modifier.size(20.dp)
            )
        }
    }
}

@Composable
private fun SettingsSwitchItem(
    icon: ImageVector,
    title: String,
    subtitle: String,
    checked: Boolean,
    onCheckedChange: (Boolean) -> Unit,
    enabled: Boolean = true
) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 16.dp, vertical = 4.dp)
            .border(1.dp, GitHubBorder, RoundedCornerShape(8.dp)),
        colors = CardDefaults.cardColors(
            containerColor = if (enabled) GitHubSurface else GitHubSurface.copy(alpha = 0.5f)
        ),
        shape = RoundedCornerShape(8.dp)
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Icon(
                imageVector = icon,
                contentDescription = null,
                tint = if (enabled) PrimaryAccent else GitHubTextSecondary,
                modifier = Modifier.size(24.dp)
            )

            Spacer(modifier = Modifier.width(16.dp))

            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = title,
                    fontSize = 16.sp,
                    fontWeight = FontWeight.Medium,
                    color = if (enabled) GitHubText else GitHubTextSecondary
                )
                Text(
                    text = subtitle,
                    fontSize = 13.sp,
                    color = GitHubTextSecondary
                )
            }

            Switch(
                checked = checked,
                onCheckedChange = onCheckedChange,
                enabled = enabled,
                colors = SwitchDefaults.colors(
                    checkedThumbColor = PrimaryAccent,
                    checkedTrackColor = PrimaryAccent.copy(alpha = 0.5f),
                    uncheckedThumbColor = GitHubTextSecondary,
                    uncheckedTrackColor = GitHubBorder
                )
            )
        }
    }
}

@Composable
private fun SettingsSliderItem(
    icon: ImageVector,
    title: String,
    subtitle: String,
    value: Float,
    onValueChange: (Float) -> Unit,
    valueRange: ClosedFloatingPointRange<Float>,
    enabled: Boolean = true
) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 16.dp, vertical = 4.dp)
            .border(1.dp, GitHubBorder, RoundedCornerShape(8.dp)),
        colors = CardDefaults.cardColors(
            containerColor = if (enabled) GitHubSurface else GitHubSurface.copy(alpha = 0.5f)
        ),
        shape = RoundedCornerShape(8.dp)
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp)
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Icon(
                    imageVector = icon,
                    contentDescription = null,
                    tint = if (enabled) PrimaryAccent else GitHubTextSecondary,
                    modifier = Modifier.size(24.dp)
                )

                Spacer(modifier = Modifier.width(16.dp))

                Column(modifier = Modifier.weight(1f)) {
                    Text(
                        text = title,
                        fontSize = 16.sp,
                        fontWeight = FontWeight.Medium,
                        color = if (enabled) GitHubText else GitHubTextSecondary
                    )
                    Text(
                        text = subtitle,
                        fontSize = 13.sp,
                        color = GitHubTextSecondary
                    )
                }
            }

            if (enabled) {
                Spacer(modifier = Modifier.height(8.dp))
                Slider(
                    value = value,
                    onValueChange = onValueChange,
                    valueRange = valueRange,
                    steps = ((valueRange.endInclusive - valueRange.start) / 10).toInt() - 1,
                    colors = SliderDefaults.colors(
                        thumbColor = PrimaryAccent,
                        activeTrackColor = PrimaryAccent,
                        inactiveTrackColor = GitHubBorder
                    )
                )
            }
        }
    }
}
