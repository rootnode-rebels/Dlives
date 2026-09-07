package com.sanlives.app.data.db.dao

import androidx.room.*
import com.sanlives.app.data.db.entity.CalendarEventEntity
import kotlinx.coroutines.flow.Flow

@Dao
interface CalendarEventDao {
    @Query("SELECT * FROM calendar_events ORDER BY dateEpochDay ASC, startTime ASC")
    fun getAllEvents(): Flow<List<CalendarEventEntity>>

    @Query("SELECT * FROM calendar_events WHERE dateEpochDay = :epochDay ORDER BY startTime ASC")
    fun getEventsForDate(epochDay: Long): Flow<List<CalendarEventEntity>>

    @Query("SELECT DISTINCT dateEpochDay FROM calendar_events")
    fun getDatesWithEvents(): Flow<List<Long>>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertEvent(event: CalendarEventEntity): Long

    @Update
    suspend fun updateEvent(event: CalendarEventEntity)

    @Delete
    suspend fun deleteEvent(event: CalendarEventEntity)
}
