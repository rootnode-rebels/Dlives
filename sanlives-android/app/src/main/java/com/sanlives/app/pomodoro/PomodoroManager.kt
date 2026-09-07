package com.sanlives.app.pomodoro

import android.content.Context
import android.content.Intent
import android.media.RingtoneManager
import kotlinx.coroutines.*
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow

enum class PomodoroState { IDLE, RUNNING, PAUSED }
enum class PomodoroMode(val displayName: String, val defaultMinutes: Int) {
    FOCUS("Focus", 25),
    SHORT_BREAK("Short Break", 5),
    LONG_BREAK("Long Break", 15)
}

object PomodoroManager {
    private var scope = CoroutineScope(Dispatchers.Main + SupervisorJob())
    private var timerJob: Job? = null

    private val _state = MutableStateFlow(PomodoroState.IDLE)
    val state: StateFlow<PomodoroState> = _state.asStateFlow()

    private val _mode = MutableStateFlow(PomodoroMode.FOCUS)
    val mode: StateFlow<PomodoroMode> = _mode.asStateFlow()

    private val _remainingSeconds = MutableStateFlow(25 * 60)
    val remainingSeconds: StateFlow<Int> = _remainingSeconds.asStateFlow()

    private val _totalSeconds = MutableStateFlow(25 * 60)
    val totalSeconds: StateFlow<Int> = _totalSeconds.asStateFlow()

    private val _completedSessions = MutableStateFlow(0)
    val completedSessions: StateFlow<Int> = _completedSessions.asStateFlow()

    private var targetEndTimeMs: Long = 0L

    fun start(context: Context) {
        if (_state.value == PomodoroState.RUNNING) return
        _state.value = PomodoroState.RUNNING
        targetEndTimeMs = System.currentTimeMillis() + (_remainingSeconds.value * 1000L)

        timerJob?.cancel()
        timerJob = scope.launch {
            while (_state.value == PomodoroState.RUNNING) {
                val now = System.currentTimeMillis()
                val diffSec = ((targetEndTimeMs - now) / 1000L).toInt()

                if (diffSec <= 0) {
                    _remainingSeconds.value = 0
                    notifyIsland(context)
                    onTimerFinished(context)
                    break
                } else {
                    _remainingSeconds.value = diffSec
                    notifyIsland(context)
                }
                delay(1000)
            }
        }
        notifyIsland(context)
    }

    fun pause(context: Context) {
        _state.value = PomodoroState.PAUSED
        timerJob?.cancel()
        val now = System.currentTimeMillis()
        val diffSec = ((targetEndTimeMs - now) / 1000L).toInt().coerceAtLeast(0)
        _remainingSeconds.value = diffSec
        notifyIsland(context)
    }

    fun reset(context: Context) {
        timerJob?.cancel()
        _state.value = PomodoroState.IDLE
        _remainingSeconds.value = _mode.value.defaultMinutes * 60
        _totalSeconds.value = _mode.value.defaultMinutes * 60
        targetEndTimeMs = 0L
        notifyIsland(context)
    }

    fun setMode(newMode: PomodoroMode, context: Context) {
        timerJob?.cancel()
        _mode.value = newMode
        _state.value = PomodoroState.IDLE
        _remainingSeconds.value = newMode.defaultMinutes * 60
        _totalSeconds.value = newMode.defaultMinutes * 60
        notifyIsland(context)
    }

    private fun onTimerFinished(context: Context) {
        _state.value = PomodoroState.IDLE
        if (_mode.value == PomodoroMode.FOCUS) {
            _completedSessions.value += 1
            if (_completedSessions.value % 4 == 0) {
                setMode(PomodoroMode.LONG_BREAK, context)
            } else {
                setMode(PomodoroMode.SHORT_BREAK, context)
            }
        } else {
            setMode(PomodoroMode.FOCUS, context)
        }

        // Play completion chime
        try {
            val notificationUri = RingtoneManager.getDefaultUri(RingtoneManager.TYPE_NOTIFICATION)
            val r = RingtoneManager.getRingtone(context, notificationUri)
            r.play()
        } catch (e: Exception) {
            e.printStackTrace()
        }

        notifyIsland(context)
    }

    private fun notifyIsland(context: Context) {
        val intent = Intent(ACTION_POMODORO_TICK).apply {
            putExtra(EXTRA_POMO_STATE, _state.value.name)
            putExtra(EXTRA_POMO_REMAINING, _remainingSeconds.value)
            putExtra(EXTRA_POMO_MODE, _mode.value.displayName)
        }
        context.sendBroadcast(intent)
    }

    const val ACTION_POMODORO_TICK = "com.sanlives.app.ACTION_POMODORO_TICK"
    const val EXTRA_POMO_STATE = "extra_pomo_state"
    const val EXTRA_POMO_REMAINING = "extra_pomo_remaining"
    const val EXTRA_POMO_MODE = "extra_pomo_mode"
}
