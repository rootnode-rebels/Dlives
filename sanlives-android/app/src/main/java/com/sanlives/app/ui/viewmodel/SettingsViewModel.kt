package com.sanlives.app.ui.viewmodel

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import com.sanlives.app.SanLivesApp
import kotlinx.coroutines.flow.StateFlow

class SettingsViewModel(application: Application) : AndroidViewModel(application) {
    private val prefs = (application as SanLivesApp).preferencesManager

    val themeMode: StateFlow<String> = prefs.themeMode
    val accentName: StateFlow<String> = prefs.accentName
    val is12HourFormat: StateFlow<Boolean> = prefs.is12HourFormat
    val isOverlayEnabled: StateFlow<Boolean> = prefs.isOverlayEnabled
    val alarmDurationSec: StateFlow<Int> = prefs.alarmDisplayDurationSec
    val islandPositionMode: StateFlow<String> = prefs.islandPositionMode

    fun setThemeMode(mode: String) = prefs.setThemeMode(mode)
    fun setAccentName(accent: String) = prefs.setAccentName(accent)
    fun set12HourFormat(is12h: Boolean) = prefs.set12HourFormat(is12h)
    fun setOverlayEnabled(enabled: Boolean) = prefs.setOverlayEnabled(enabled)
    fun setAlarmDurationSec(sec: Int) = prefs.setAlarmDisplayDurationSec(sec)
    fun setIslandPositionMode(mode: String) = prefs.setIslandPositionMode(mode)
}
