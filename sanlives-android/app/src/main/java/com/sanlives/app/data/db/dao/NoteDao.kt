package com.sanlives.app.data.db.dao

import androidx.room.*
import com.sanlives.app.data.db.entity.NoteEntity
import kotlinx.coroutines.flow.Flow

@Dao
interface NoteDao {
    @Query("SELECT * FROM notes ORDER BY isPinnedQuickNote DESC, lastModified DESC")
    fun getAllNotes(): Flow<List<NoteEntity>>

    @Query("SELECT * FROM notes WHERE isPinnedQuickNote = 1 ORDER BY lastModified DESC LIMIT 2")
    fun getPinnedQuickNotes(): Flow<List<NoteEntity>>

    @Query("SELECT * FROM notes WHERE id = :id LIMIT 1")
    suspend fun getNoteById(id: Long): NoteEntity?

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertNote(note: NoteEntity): Long

    @Update
    suspend fun updateNote(note: NoteEntity)

    @Delete
    suspend fun deleteNote(note: NoteEntity)

    @Query("SELECT COUNT(*) FROM notes WHERE isPinnedQuickNote = 1")
    suspend fun getPinnedCount(): Int
}
