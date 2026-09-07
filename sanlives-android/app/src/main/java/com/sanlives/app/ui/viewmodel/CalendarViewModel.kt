package com.sanlives.app.ui.viewmodel

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.sanlives.app.SanLivesApp
import com.sanlives.app.data.db.entity.CalendarEventEntity
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.flow.*
import kotlinx.coroutines.launch
import java.time.LocalDate

@OptIn(ExperimentalCoroutinesApi::class)
class CalendarViewModel(application: Application) : AndroidViewModel(application) {
    private val repository = (application as SanLivesApp).repository

    private val _selectedDate = MutableStateFlow(LocalDate.now())
    val selectedDate: StateFlow<LocalDate> = _selectedDate.asStateFlow()

    val datesWithEvents: StateFlow<List<Long>> = repository.datesWithEvents
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    val eventsForSelectedDate: StateFlow<List<CalendarEventEntity>> = _selectedDate
        .flatMapLatest { date ->
            repository.getEventsForDate(date.toEpochDay())
        }
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    fun setSelectedDate(date: LocalDate) {
        _selectedDate.value = date
    }

    fun saveEvent(event: CalendarEventEntity) {
        viewModelScope.launch {
            repository.insertEvent(event)
        }
    }

    fun deleteEvent(event: CalendarEventEntity) {
        viewModelScope.launch {
            repository.deleteEvent(event)
        }
    }
}
