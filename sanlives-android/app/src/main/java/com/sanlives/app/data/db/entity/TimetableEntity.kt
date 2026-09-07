package com.sanlives.app.data.db.entity

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "timetable_entries")
data class TimetableEntity(
    @PrimaryKey(autoGenerate = true)
    val id: Long = 0,
    val hour: Int,
    val minute: Int,
    val title: String,
    val description: String = "",
    val isCompleted: Boolean = false,
    val repeatDaily: Boolean = true,
    val lastModified: Long = System.currentTimeMillis()
)
