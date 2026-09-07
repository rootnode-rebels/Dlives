package com.sanlives.app.data.backup

import android.content.Context
import android.net.Uri
import com.sanlives.app.data.db.AppDatabase
import com.sanlives.app.data.db.entity.*
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject
import java.io.BufferedReader
import java.io.InputStreamReader
import java.io.OutputStreamWriter
import java.text.SimpleDateFormat
import java.util.*

object BackupManager {

    suspend fun exportToJson(context: Context, uri: Uri): Boolean = withContext(Dispatchers.IO) {
        try {
            val db = AppDatabase.getDatabase(context)
            val root = JSONObject()

            root.put("version", "3.2.1")
            root.put("timestamp", System.currentTimeMillis())
            root.put("exportedAt", SimpleDateFormat("yyyy-MM-dd HH:mm:ss", Locale.getDefault()).format(Date()))

            // Alarms
            val alarms = db.alarmDao().getAllAlarms().first()
            val alarmsArray = JSONArray()
            alarms.forEach { a ->
                val obj = JSONObject().apply {
                    put("hour", a.hour)
                    put("minute", a.minute)
                    put("label", a.label)
                    put("repeatDays", JSONArray(a.repeatDays))
                    put("soundUri", a.soundUri ?: "")
                    put("soundTitle", a.soundTitle)
                    put("snoozeDurationMinutes", a.snoozeDurationMinutes)
                    put("isEnabled", a.isEnabled)
                    put("lastModified", a.lastModified)
                }
                alarmsArray.put(obj)
            }
            root.put("alarms", alarmsArray)

            // Timetable
            val timetable = db.timetableDao().getAllEntries().first()
            val ttArray = JSONArray()
            timetable.forEach { t ->
                val obj = JSONObject().apply {
                    put("hour", t.hour)
                    put("minute", t.minute)
                    put("title", t.title)
                    put("description", t.description)
                    put("isCompleted", t.isCompleted)
                    put("repeatDaily", t.repeatDaily)
                    put("lastModified", t.lastModified)
                }
                ttArray.put(obj)
            }
            root.put("timetable", ttArray)

            // Notes
            val notes = db.noteDao().getAllNotes().first()
            val notesArray = JSONArray()
            notes.forEach { n ->
                val obj = JSONObject().apply {
                    put("title", n.title)
                    put("content", n.content)
                    put("isPinnedQuickNote", n.isPinnedQuickNote)
                    put("createdAt", n.createdAt)
                    put("lastModified", n.lastModified)
                }
                notesArray.put(obj)
            }
            root.put("notes", notesArray)

            // Calendar Events
            val events = db.calendarEventDao().getAllEvents().first()
            val eventsArray = JSONArray()
            events.forEach { e ->
                val obj = JSONObject().apply {
                    put("title", e.title)
                    put("description", e.description)
                    put("dateEpochDay", e.dateEpochDay)
                    put("startTime", e.startTime ?: "")
                    put("endTime", e.endTime ?: "")
                    put("colorTag", e.colorTag)
                    put("lastModified", e.lastModified)
                }
                eventsArray.put(obj)
            }
            root.put("calendarEvents", eventsArray)

            // Tasks
            val tasks = db.taskDao().getAllTasks().first()
            val tasksArray = JSONArray()
            tasks.forEach { tk ->
                val obj = JSONObject().apply {
                    put("title", tk.title)
                    put("isCompleted", tk.isCompleted)
                    put("priority", tk.priority)
                    put("createdAt", tk.createdAt)
                    put("lastModified", tk.lastModified)
                }
                tasksArray.put(obj)
            }
            root.put("tasks", tasksArray)

            context.contentResolver.openOutputStream(uri)?.use { os ->
                OutputStreamWriter(os, "UTF-8").use { writer ->
                    writer.write(root.toString(2))
                }
            }
            true
        } catch (e: Exception) {
            e.printStackTrace()
            false
        }
    }

    suspend fun importFromJson(context: Context, uri: Uri): Boolean = withContext(Dispatchers.IO) {
        try {
            val content = StringBuilder()
            context.contentResolver.openInputStream(uri)?.use { inputStream ->
                BufferedReader(InputStreamReader(inputStream, "UTF-8")).use { reader ->
                    var line: String?
                    while (reader.readLine().also { line = it } != null) {
                        content.append(line)
                    }
                }
            }

            val root = JSONObject(content.toString())
            val db = AppDatabase.getDatabase(context)

            // Import Alarms
            if (root.has("alarms")) {
                val alarmsArray = root.getJSONArray("alarms")
                for (i in 0 until alarmsArray.length()) {
                    val obj = alarmsArray.getJSONObject(i)
                    val days = mutableListOf<String>()
                    val daysArr = obj.optJSONArray("repeatDays")
                    if (daysArr != null) {
                        for (d in 0 until daysArr.length()) {
                            days.add(daysArr.getString(d))
                        }
                    }
                    val alarm = AlarmEntity(
                        hour = obj.optInt("hour", 8),
                        minute = obj.optInt("minute", 0),
                        label = obj.optString("label", "Alarm"),
                        repeatDays = days,
                        soundUri = if (obj.optString("soundUri").isBlank()) null else obj.optString("soundUri"),
                        soundTitle = obj.optString("soundTitle", "Default Alarm Tone"),
                        snoozeDurationMinutes = obj.optInt("snoozeDurationMinutes", 10),
                        isEnabled = obj.optBoolean("isEnabled", true),
                        lastModified = obj.optLong("lastModified", System.currentTimeMillis())
                    )
                    db.alarmDao().insertAlarm(alarm)
                }
            }

            // Import Timetable
            if (root.has("timetable")) {
                val ttArray = root.getJSONArray("timetable")
                for (i in 0 until ttArray.length()) {
                    val obj = ttArray.getJSONObject(i)
                    val entry = TimetableEntity(
                        hour = obj.optInt("hour", 9),
                        minute = obj.optInt("minute", 0),
                        title = obj.optString("title", "Routine Task"),
                        description = obj.optString("description", ""),
                        isCompleted = obj.optBoolean("isCompleted", false),
                        repeatDaily = obj.optBoolean("repeatDaily", true),
                        lastModified = obj.optLong("lastModified", System.currentTimeMillis())
                    )
                    db.timetableDao().insertEntry(entry)
                }
            }

            // Import Notes
            if (root.has("notes")) {
                val notesArray = root.getJSONArray("notes")
                for (i in 0 until notesArray.length()) {
                    val obj = notesArray.getJSONObject(i)
                    val note = NoteEntity(
                        title = obj.optString("title", "Untitled Note"),
                        content = obj.optString("content", ""),
                        isPinnedQuickNote = obj.optBoolean("isPinnedQuickNote", false),
                        createdAt = obj.optLong("createdAt", System.currentTimeMillis()),
                        lastModified = obj.optLong("lastModified", System.currentTimeMillis())
                    )
                    db.noteDao().insertNote(note)
                }
            }

            // Import Calendar Events
            if (root.has("calendarEvents")) {
                val eventsArray = root.getJSONArray("calendarEvents")
                for (i in 0 until eventsArray.length()) {
                    val obj = eventsArray.getJSONObject(i)
                    val event = CalendarEventEntity(
                        title = obj.optString("title", "Event"),
                        description = obj.optString("description", ""),
                        dateEpochDay = obj.optLong("dateEpochDay", 0L),
                        startTime = if (obj.optString("startTime").isBlank()) null else obj.optString("startTime"),
                        endTime = if (obj.optString("endTime").isBlank()) null else obj.optString("endTime"),
                        colorTag = obj.optString("colorTag", "#38BDF8"),
                        lastModified = obj.optLong("lastModified", System.currentTimeMillis())
                    )
                    db.calendarEventDao().insertEvent(event)
                }
            }

            // Import Tasks
            if (root.has("tasks")) {
                val tasksArray = root.getJSONArray("tasks")
                for (i in 0 until tasksArray.length()) {
                    val obj = tasksArray.getJSONObject(i)
                    val task = TaskEntity(
                        title = obj.optString("title", "Task"),
                        isCompleted = obj.optBoolean("isCompleted", false),
                        priority = obj.optInt("priority", 1),
                        createdAt = obj.optLong("createdAt", System.currentTimeMillis()),
                        lastModified = obj.optLong("lastModified", System.currentTimeMillis())
                    )
                    db.taskDao().insertTask(task)
                }
            }

            true
        } catch (e: Exception) {
            e.printStackTrace()
            false
        }
    }
}
