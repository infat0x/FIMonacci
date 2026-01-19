package com.fimonacci.app

import android.Manifest
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.core.content.ContextCompat
import androidx.lifecycle.lifecycleScope
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.compose.rememberNavController
import com.fimonacci.app.data.preferences.PreferencesManager
import com.fimonacci.app.navigation.AppScaffold
import com.fimonacci.app.ui.screen.SplashScreen
import com.fimonacci.app.ui.theme.FIMonacciTheme
import com.fimonacci.app.ui.viewmodel.DashboardViewModel
import com.fimonacci.app.ui.viewmodel.SettingsViewModel
import com.fimonacci.app.utils.NotificationHelper
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.launch

class MainActivity : ComponentActivity() {
    private val preferencesManager by lazy { PreferencesManager(this) }

    private val requestPermissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { isGranted: Boolean ->
        lifecycleScope.launch {
            // Enable notifications in settings if permission granted
            preferencesManager.setNotificationsEnabled(isGranted)
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        // Create notification channel
        NotificationHelper.createNotificationChannel(this)

        // Request notification permission on first launch (Android 13+)
        requestNotificationPermissionIfNeeded()
        
        setContent {
            val settingsViewModel: SettingsViewModel = viewModel(
                factory = androidx.lifecycle.ViewModelProvider.AndroidViewModelFactory.getInstance(application)
            )
            val darkMode by settingsViewModel.uiState.collectAsState()
            
            FIMonacciTheme(darkTheme = darkMode.darkModeEnabled) {
                Surface(
                    modifier = Modifier.fillMaxSize(),
                    color = MaterialTheme.colorScheme.background
                ) {
                    var showSplash by remember { mutableStateOf(true) }
                    val navController = rememberNavController()
                    val dashboardViewModel: DashboardViewModel = viewModel(
                        factory = androidx.lifecycle.ViewModelProvider.AndroidViewModelFactory.getInstance(application)
                    )

                    if (showSplash) {
                        SplashScreen(
                            onNavigateToMain = { showSplash = false }
                        )
                    } else {
                        AppScaffold(
                            navController = navController,
                            viewModel = dashboardViewModel,
                            settingsViewModel = settingsViewModel
                        )
                    }
                }
            }
        }
    }

    private fun requestNotificationPermissionIfNeeded() {
        // Only request permission on Android 13 (API 33) and above
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            when {
                ContextCompat.checkSelfPermission(
                    this,
                    Manifest.permission.POST_NOTIFICATIONS
                ) == PackageManager.PERMISSION_GRANTED -> {
                    // Permission already granted, ensure notifications are enabled in settings
                    lifecycleScope.launch {
                        val notificationsEnabled = preferencesManager.notificationsEnabled.first()
                        if (!notificationsEnabled) {
                            preferencesManager.setNotificationsEnabled(true)
                        }
                    }
                }
                else -> {
                    // Request permission
                    requestPermissionLauncher.launch(Manifest.permission.POST_NOTIFICATIONS)
                }
            }
        } else {
            // For Android 12 and below, notifications are enabled by default
            lifecycleScope.launch {
                preferencesManager.setNotificationsEnabled(true)
            }
        }
    }
}

