package com.fimonacci.app.ui.viewmodel

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.fimonacci.app.data.preferences.PreferencesManager
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.*
import kotlinx.coroutines.launch

data class SettingsUiState(
    val darkModeEnabled: Boolean = true,
    val notificationsEnabled: Boolean = true,
    val soundEnabled: Boolean = true,
    val autoRefreshEnabled: Boolean = false,
    val realTimeEnabled: Boolean = false,
    val refreshInterval: Int = 30,
    val serverUrl: String = "http://192.168.1.67:8000"
)

class SettingsViewModel(application: Application) : AndroidViewModel(application) {
    private val preferencesManager = PreferencesManager(application)

    val uiState: StateFlow<SettingsUiState> = combine(
        preferencesManager.darkMode,
        preferencesManager.notificationsEnabled,
        preferencesManager.soundEnabled,
        preferencesManager.autoRefreshEnabled,
        preferencesManager.realTimeEnabled,
        preferencesManager.refreshInterval,
        preferencesManager.serverUrl
    ) { values: Array<Any?> ->
        SettingsUiState(
            darkModeEnabled = values[0] as Boolean,
            notificationsEnabled = values[1] as Boolean,
            soundEnabled = values[2] as Boolean,
            autoRefreshEnabled = values[3] as Boolean,
            realTimeEnabled = values[4] as Boolean,
            refreshInterval = values[5] as Int,
            serverUrl = values[6] as String
        )
    }.stateIn(
        scope = viewModelScope,
        started = SharingStarted.WhileSubscribed(5000),
        initialValue = SettingsUiState()
    )

    private var autoRefreshJob: kotlinx.coroutines.Job? = null

    fun toggleDarkMode(enabled: Boolean) {
        viewModelScope.launch {
            preferencesManager.setDarkMode(enabled)
        }
    }

    fun toggleNotifications(enabled: Boolean) {
        viewModelScope.launch {
            preferencesManager.setNotificationsEnabled(enabled)
            if (!enabled) {
                preferencesManager.setSoundEnabled(false)
            }
        }
    }

    fun toggleSound(enabled: Boolean) {
        viewModelScope.launch {
            preferencesManager.setSoundEnabled(enabled)
        }
    }

    fun toggleAutoRefresh(enabled: Boolean, onRefresh: () -> Unit) {
        viewModelScope.launch {
            preferencesManager.setAutoRefreshEnabled(enabled)
            if (enabled) {
                startAutoRefresh(onRefresh)
            } else {
                stopAutoRefresh()
            }
        }
    }

    fun toggleRealTime(enabled: Boolean) {
        viewModelScope.launch {
            preferencesManager.setRealTimeEnabled(enabled)
        }
    }

    fun setRefreshInterval(interval: Int) {
        viewModelScope.launch {
            preferencesManager.setRefreshInterval(interval)
            // Restart auto-refresh if it's enabled to apply new interval
            val currentState = uiState.value
            if (currentState.autoRefreshEnabled) {
                autoRefreshJob?.cancel()
            }
        }
    }

    fun updateServerUrl(url: String) {
        viewModelScope.launch {
            preferencesManager.setServerUrl(url)
        }
    }

    private fun startAutoRefresh(onRefresh: () -> Unit) {
        autoRefreshJob?.cancel()
        autoRefreshJob = viewModelScope.launch {
            while (true) {
                val currentState = uiState.value
                if (!currentState.autoRefreshEnabled) {
                    break
                }
                delay(currentState.refreshInterval * 1000L)
                onRefresh()
            }
        }
    }

    private fun stopAutoRefresh() {
        autoRefreshJob?.cancel()
        autoRefreshJob = null
    }

    override fun onCleared() {
        super.onCleared()
        stopAutoRefresh()
    }
}
