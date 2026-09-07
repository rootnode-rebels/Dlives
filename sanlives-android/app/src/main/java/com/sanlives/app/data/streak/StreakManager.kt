package com.sanlives.app.data.streak

import android.content.Context
import android.content.SharedPreferences
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import java.text.SimpleDateFormat
import java.util.*

class StreakManager(context: Context) {
    private val prefs: SharedPreferences =
        context.getSharedPreferences("sanlives_streaks", Context.MODE_PRIVATE)

    private val _currentStreak = MutableStateFlow(prefs.getInt("current_streak", 1))
    val currentStreak: StateFlow<Int> = _currentStreak.asStateFlow()

    private val _bestStreak = MutableStateFlow(prefs.getInt("best_streak", 1))
    val bestStreak: StateFlow<Int> = _bestStreak.asStateFlow()

    private val dateFormat = SimpleDateFormat("yyyy-MM-dd", Locale.getDefault())

    fun recordDayCompleted(): Boolean {
        val todayStr = dateFormat.format(Date())
        val lastCompleted = prefs.getString("last_completed_date", "")

        if (lastCompleted == todayStr) {
            return false // Already recorded today
        }

        val cal = Calendar.getInstance()
        cal.add(Calendar.DAY_OF_YEAR, -1)
        val yesterdayStr = dateFormat.format(cal.time)

        val newStreak = if (lastCompleted == yesterdayStr) {
            _currentStreak.value + 1
        } else {
            1
        }

        val newBest = maxOf(newStreak, _bestStreak.value)

        prefs.edit()
            .putInt("current_streak", newStreak)
            .putInt("best_streak", newBest)
            .putString("last_completed_date", todayStr)
            .apply()

        _currentStreak.value = newStreak
        _bestStreak.value = newBest
        return true
    }
}
