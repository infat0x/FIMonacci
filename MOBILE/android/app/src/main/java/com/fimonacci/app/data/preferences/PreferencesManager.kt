package com.fimonacci.app.data.preferences

import android.content.Context
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.*
import androidx.datastore.preferences.preferencesDataStore
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map

private val Context.dataStore: DataStore<Preferences> by preferencesDataStore(name = "settings")

class PreferencesManager(private val context: Context) {
    companion object {
        private val DARK_MODE_KEY = booleanPreferencesKey("dark_mode")
        private val NOTIFICATIONS_ENABLED_KEY = booleanPreferencesKey("notifications_enabled")
        private val SOUND_ENABLED_KEY = booleanPreferencesKey("sound_enabled")
        private val AUTO_REFRESH_ENABLED_KEY = booleanPreferencesKey("auto_refresh_enabled")
        private val REFRESH_INTERVAL_KEY = intPreferencesKey("refresh_interval")
        private val REAL_TIME_ENABLED_KEY = booleanPreferencesKey("real_time_enabled")
        private val SERVER_URL_KEY = stringPreferencesKey("server_url")
    }

    val darkMode: Flow<Boolean> = context.dataStore.data.map { preferences ->
        preferences[DARK_MODE_KEY] ?: true
    }

    val notificationsEnabled: Flow<Boolean> = context.dataStore.data.map { preferences ->
        preferences[NOTIFICATIONS_ENABLED_KEY] ?: true
    }

    val soundEnabled: Flow<Boolean> = context.dataStore.data.map { preferences ->
        preferences[SOUND_ENABLED_KEY] ?: true
    }

    val autoRefreshEnabled: Flow<Boolean> = context.dataStore.data.map { preferences ->
        preferences[AUTO_REFRESH_ENABLED_KEY] ?: false
    }

    val refreshInterval: Flow<Int> = context.dataStore.data.map { preferences ->
        preferences[REFRESH_INTERVAL_KEY] ?: 30
    }

    val realTimeEnabled: Flow<Boolean> = context.dataStore.data.map { preferences ->
        preferences[REAL_TIME_ENABLED_KEY] ?: false
    }

    val serverUrl: Flow<String> = context.dataStore.data.map { preferences ->
        preferences[SERVER_URL_KEY] ?: "http://13.62.224.164:2828"
    }

    suspend fun setDarkMode(enabled: Boolean) {
        context.dataStore.edit { preferences ->
            preferences[DARK_MODE_KEY] = enabled
        }
    }

    suspend fun setNotificationsEnabled(enabled: Boolean) {
        context.dataStore.edit { preferences ->
            preferences[NOTIFICATIONS_ENABLED_KEY] = enabled
        }
    }

    suspend fun setSoundEnabled(enabled: Boolean) {
        context.dataStore.edit { preferences ->
            preferences[SOUND_ENABLED_KEY] = enabled
        }
    }

    suspend fun setAutoRefreshEnabled(enabled: Boolean) {
        context.dataStore.edit { preferences ->
            preferences[AUTO_REFRESH_ENABLED_KEY] = enabled
        }
    }

    suspend fun setRefreshInterval(interval: Int) {
        context.dataStore.edit { preferences ->
            preferences[REFRESH_INTERVAL_KEY] = interval
        }
    }

    suspend fun setRealTimeEnabled(enabled: Boolean) {
        context.dataStore.edit { preferences ->
            preferences[REAL_TIME_ENABLED_KEY] = enabled
        }
    }

    suspend fun setServerUrl(url: String) {
        context.dataStore.edit { preferences ->
            preferences[SERVER_URL_KEY] = url
        }
    }
}
