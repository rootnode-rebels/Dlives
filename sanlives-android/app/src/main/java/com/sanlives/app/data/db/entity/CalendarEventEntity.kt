package com.sanlives.app.data.db.entity

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "calendar_events")
data class CalendarEventEntity(
    @PrimaryKey(autoGenerate = true)
    val id: Long = 0,
    val title: String,
    val description: String = "",
    val dateEpochDay: Long, // LocalDate.toEpochDay()
    val startTime: String? = null, // "09:00"
    val endTime: String? = null,   // "10:30"
    val colorTag: String = "#38BDF8",
    val lastModified: Long = System.currentTimeMillis()
)
