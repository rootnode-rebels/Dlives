package com.sanlives.app.data.repository

import com.sanlives.app.data.db.AppDatabase
import com.sanlives.app.data.db.entity.*
import kotlinx.coroutines.flow.Flow

class AppRepository(private val db: AppDatabase) {

    // Alarms
    val allAlarms: Flow<List<AlarmEntity>> = db.alarmDao().getAllAlarms()
    suspend fun getEnabledAlarms(): List<AlarmEntity> = db.alarmDao().getEnabledAlarms()
    suspend fun getAlarmById(id: Long): AlarmEntity? = db.alarmDao().getAlarmById(id)
    suspend fun insertAlarm(alarm: AlarmEntity): Long =
        db.alarmDao().insertAlarm(alarm.copy(lastModified = System.currentTimeMillis()))
    suspend fun updateAlarm(alarm: AlarmEntity) =
        db.alarmDao().updateAlarm(alarm.copy(lastModified = System.currentTimeMillis()))
    suspend fun deleteAlarm(alarm: AlarmEntity) = db.alarmDao().deleteAlarm(alarm)
    suspend fun deleteAlarmById(id: Long) = db.alarmDao().deleteAlarmById(id)

    // Timetable
    val allTimetableEntries: Flow<List<TimetableEntity>> = db.timetableDao().getAllEntries()
    suspend fun insertTimetableEntry(entry: TimetableEntity): Long =
        db.timetableDao().insertEntry(entry.copy(lastModified = System.currentTimeMillis()))
    suspend fun updateTimetableEntry(entry: TimetableEntity) =
        db.timetableDao().updateEntry(entry.copy(lastModified = System.currentTimeMillis()))
    suspend fun deleteTimetableEntry(entry: TimetableEntity) = db.timetableDao().deleteEntry(entry)
    suspend fun resetDailyCompletion() = db.timetableDao().resetDailyCompletion()

    // Notes
    val allNotes: Flow<List<NoteEntity>> = db.noteDao().getAllNotes()
    val pinnedQuickNotes: Flow<List<NoteEntity>> = db.noteDao().getPinnedQuickNotes()
    suspend fun getNoteById(id: Long): NoteEntity? = db.noteDao().getNoteById(id)
    suspend fun insertNote(note: NoteEntity): Long =
        db.noteDao().insertNote(note.copy(lastModified = System.currentTimeMillis()))
    suspend fun updateNote(note: NoteEntity) =
        db.noteDao().updateNote(note.copy(lastModified = System.currentTimeMillis()))
    suspend fun deleteNote(note: NoteEntity) = db.noteDao().deleteNote(note)
    suspend fun getPinnedCount(): Int = db.noteDao().getPinnedCount()

    // Calendar Events
    val allEvents: Flow<List<CalendarEventEntity>> = db.calendarEventDao().getAllEvents()
    fun getEventsForDate(epochDay: Long): Flow<List<CalendarEventEntity>> = db.calendarEventDao().getEventsForDate(epochDay)
    val datesWithEvents: Flow<List<Long>> = db.calendarEventDao().getDatesWithEvents()
    suspend fun insertEvent(event: CalendarEventEntity): Long =
        db.calendarEventDao().insertEvent(event.copy(lastModified = System.currentTimeMillis()))
    suspend fun updateEvent(event: CalendarEventEntity) =
        db.calendarEventDao().updateEvent(event.copy(lastModified = System.currentTimeMillis()))
    suspend fun deleteEvent(event: CalendarEventEntity) = db.calendarEventDao().deleteEvent(event)

    // Tasks
    val allTasks: Flow<List<TaskEntity>> = db.taskDao().getAllTasks()
    suspend fun insertTask(task: TaskEntity): Long =
        db.taskDao().insertTask(task.copy(lastModified = System.currentTimeMillis()))
    suspend fun updateTask(task: TaskEntity) =
        db.taskDao().updateTask(task.copy(lastModified = System.currentTimeMillis()))
    suspend fun deleteTask(task: TaskEntity) = db.taskDao().deleteTask(task)
}
