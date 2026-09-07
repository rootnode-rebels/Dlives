package com.sanlives.app.data.db.dao

import androidx.room.*
import com.sanlives.app.data.db.entity.TimetableEntity
import kotlinx.coroutines.flow.Flow

@Dao
interface TimetableDao {
    @Query("SELECT * FROM timetable_entries ORDER BY hour ASC, minute ASC")
    fun getAllEntries(): Flow<List<TimetableEntity>>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertEntry(entry: TimetableEntity): Long

    @Update
    suspend fun updateEntry(entry: TimetableEntity)

    @Delete
    suspend fun deleteEntry(entry: TimetableEntity)

    @Query("UPDATE timetable_entries SET isCompleted = 0 WHERE repeatDaily = 1")
    suspend fun resetDailyCompletion()
}
