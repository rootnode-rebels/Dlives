package com.sanlives.app.data.preferences

import android.content.Context
import android.content.SharedPreferences
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow

class PreferencesManager(context: Context) {
    private val prefs: SharedPreferences =
        context.getSharedPreferences("sanlives_preferences", Context.MODE_PRIVATE)

    private val _themeMode = MutableStateFlow(prefs.getString("theme_mode", "dark") ?: "dark")
    val themeMode: StateFlow<String> = _themeMode.asStateFlow()

    private val _accentName = MutableStateFlow(prefs.getString("accent_name", "sky_blue") ?: "sky_blue")
    val accentName: StateFlow<String> = _accentName.asStateFlow()

    private val _is12HourFormat = MutableStateFlow(prefs.getBoolean("is_12h_format", true))
    val is12HourFormat: StateFlow<Boolean> = _is12HourFormat.asStateFlow()

    private val _isOverlayEnabled = MutableStateFlow(prefs.getBoolean("is_overlay_enabled", false))
    val isOverlayEnabled: StateFlow<Boolean> = _isOverlayEnabled.asStateFlow()

    private val _alarmDisplayDurationSec = MutableStateFlow(prefs.getInt("alarm_duration_sec", 60))
    val alarmDisplayDurationSec: StateFlow<Int> = _alarmDisplayDurationSec.asStateFlow()

    private val _islandPositionMode = MutableStateFlow(prefs.getString("island_position_mode", "center") ?: "center")
    val islandPositionMode: StateFlow<String> = _islandPositionMode.asStateFlow()

    fun setThemeMode(mode: String) {
        prefs.edit().putString("theme_mode", mode).apply()
        _themeMode.value = mode
    }

    fun setAccentName(name: String) {
        prefs.edit().putString("accent_name", name).apply()
        _accentName.value = name
    }

    fun set12HourFormat(is12h: Boolean) {
        prefs.edit().putBoolean("is_12h_format", is12h).apply()
        _is12HourFormat.value = is12h
    }

    fun setOverlayEnabled(enabled: Boolean) {
        prefs.edit().putBoolean("is_overlay_enabled", enabled).apply()
        _isOverlayEnabled.value = enabled
    }

    fun setAlarmDisplayDurationSec(seconds: Int) {
        prefs.edit().putInt("alarm_duration_sec", seconds).apply()
        _alarmDisplayDurationSec.value = seconds
    }

    fun setIslandPositionMode(mode: String) {
        prefs.edit().putString("island_position_mode", mode).apply()
        _islandPositionMode.value = mode
    }

    fun getSavedIslandX(defaultVal: Int): Int = prefs.getInt("island_saved_x", defaultVal)
    fun getSavedIslandY(defaultVal: Int): Int = prefs.getInt("island_saved_y", defaultVal)
    fun saveIslandPosition(x: Int, y: Int) {
        prefs.edit().putInt("island_saved_x", x).putInt("island_saved_y", y).apply()
    }
}
