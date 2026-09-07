package com.sanlives.app.data.db.entity

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "alarms")
data class AlarmEntity(
    @PrimaryKey(autoGenerate = true)
    val id: Long = 0,
    val hour: Int,
    val minute: Int,
    val label: String = "Alarm",
    val repeatDays: List<String> = emptyList(), // e.g. ["Mon", "Tue", "Wed"]
    val soundUri: String? = null,
    val soundTitle: String = "Default Alarm Tone",
    val snoozeDurationMinutes: Int = 10,
    val dismissMission: String = "none", // "none", "math", "shake"
    val isEnabled: Boolean = true,
    val lastModified: Long = System.currentTimeMillis()
)
