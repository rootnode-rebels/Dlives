package com.sanlives.app.ui.viewmodel

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.sanlives.app.SanLivesApp
import com.sanlives.app.alarm.AlarmScheduler
import com.sanlives.app.data.db.entity.AlarmEntity
import com.sanlives.app.data.db.entity.TimetableEntity
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch

class AlarmsViewModel(application: Application) : AndroidViewModel(application) {
    private val app = application as SanLivesApp
    private val repository = app.repository
    private val scheduler = AlarmScheduler(application)

    val alarms: StateFlow<List<AlarmEntity>> = repository.allAlarms
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    val timetableEntries: StateFlow<List<TimetableEntity>> = repository.allTimetableEntries
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    fun saveAlarm(alarm: AlarmEntity) {
        viewModelScope.launch {
            val savedId = repository.insertAlarm(alarm)
            val updated = if (alarm.id == 0L) alarm.copy(id = savedId) else alarm
            if (updated.isEnabled) {
                scheduler.schedule(updated)
            } else {
                scheduler.cancel(updated.id)
            }
        }
    }

    fun toggleAlarm(alarm: AlarmEntity) {
        viewModelScope.launch {
            val updated = alarm.copy(isEnabled = !alarm.isEnabled, lastModified = System.currentTimeMillis())
            repository.updateAlarm(updated)
            if (updated.isEnabled) {
                scheduler.schedule(updated)
            } else {
                scheduler.cancel(updated.id)
            }
        }
    }

    fun deleteAlarm(alarm: AlarmEntity) {
        viewModelScope.launch {
            scheduler.cancel(alarm.id)
            repository.deleteAlarm(alarm)
        }
    }

    fun saveTimetableEntry(entry: TimetableEntity) {
        viewModelScope.launch {
            repository.insertTimetableEntry(entry)
        }
    }

    fun toggleTimetableEntry(entry: TimetableEntity) {
        viewModelScope.launch {
            val updated = entry.copy(isCompleted = !entry.isCompleted, lastModified = System.currentTimeMillis())
            repository.updateTimetableEntry(updated)
        }
    }

    fun deleteTimetableEntry(entry: TimetableEntity) {
        viewModelScope.launch {
            repository.deleteTimetableEntry(entry)
        }
    }
}
