package com.sanlives.app.alarm

import android.app.AlarmManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.os.Build
import com.sanlives.app.data.db.entity.AlarmEntity
import java.util.*

class AlarmScheduler(private val context: Context) {
    private val alarmManager = context.getSystemService(Context.ALARM_SERVICE) as AlarmManager

    fun schedule(alarm: AlarmEntity) {
        if (!alarm.isEnabled) return

        val intent = Intent(context, AlarmReceiver::class.java).apply {
            action = AlarmReceiver.ACTION_ALARM_FIRE
            putExtra(AlarmReceiver.EXTRA_ALARM_ID, alarm.id)
            putExtra(AlarmReceiver.EXTRA_ALARM_LABEL, alarm.label)
            putExtra(AlarmReceiver.EXTRA_ALARM_HOUR, alarm.hour)
            putExtra(AlarmReceiver.EXTRA_ALARM_MINUTE, alarm.minute)
            putExtra(AlarmReceiver.EXTRA_ALARM_SOUND_URI, alarm.soundUri)
            putExtra(AlarmReceiver.EXTRA_ALARM_SNOOZE_MIN, alarm.snoozeDurationMinutes)
            putExtra(AlarmReceiver.EXTRA_ALARM_REPEAT_DAYS, ArrayList(alarm.repeatDays))
            putExtra(AlarmReceiver.EXTRA_ALARM_MISSION, alarm.dismissMission)
        }

        val pendingIntent = PendingIntent.getBroadcast(
            context,
            alarm.id.toInt(),
            intent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )

        val triggerTime = calculateNextTriggerTime(alarm.hour, alarm.minute, alarm.repeatDays)

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            if (alarmManager.canScheduleExactAlarms()) {
                alarmManager.setExactAndAllowWhileIdle(AlarmManager.RTC_WAKEUP, triggerTime, pendingIntent)
            } else {
                alarmManager.setAndAllowWhileIdle(AlarmManager.RTC_WAKEUP, triggerTime, pendingIntent)
            }
        } else {
            alarmManager.setExactAndAllowWhileIdle(AlarmManager.RTC_WAKEUP, triggerTime, pendingIntent)
        }
    }

    fun scheduleSnooze(alarmId: Long, label: String, snoozeMinutes: Int, soundUri: String?) {
        val intent = Intent(context, AlarmReceiver::class.java).apply {
            action = AlarmReceiver.ACTION_ALARM_FIRE
            putExtra(AlarmReceiver.EXTRA_ALARM_ID, alarmId)
            putExtra(AlarmReceiver.EXTRA_ALARM_LABEL, "$label (Snoozed)")
            putExtra(AlarmReceiver.EXTRA_ALARM_SOUND_URI, soundUri)
            putExtra(AlarmReceiver.EXTRA_ALARM_SNOOZE_MIN, snoozeMinutes)
        }

        val pendingIntent = PendingIntent.getBroadcast(
            context,
            (alarmId + 100000).toInt(),
            intent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )

        val triggerTime = System.currentTimeMillis() + (snoozeMinutes * 60 * 1000L)
        alarmManager.setExactAndAllowWhileIdle(AlarmManager.RTC_WAKEUP, triggerTime, pendingIntent)
    }

    fun cancel(alarmId: Long) {
        val intent = Intent(context, AlarmReceiver::class.java).apply {
            action = AlarmReceiver.ACTION_ALARM_FIRE
        }
        val pendingIntent = PendingIntent.getBroadcast(
            context,
            alarmId.toInt(),
            intent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )
        alarmManager.cancel(pendingIntent)

        // Cancel potential snooze
        val snoozeIntent = PendingIntent.getBroadcast(
            context,
            (alarmId + 100000).toInt(),
            intent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )
        alarmManager.cancel(snoozeIntent)
    }

    companion object {
        fun calculateNextTriggerTime(hour: Int, minute: Int, repeatDays: List<String>): Long {
            val now = Calendar.getInstance()
            val target = Calendar.getInstance().apply {
                set(Calendar.HOUR_OF_DAY, hour)
                set(Calendar.MINUTE, minute)
                set(Calendar.SECOND, 0)
                set(Calendar.MILLISECOND, 0)
            }

            if (repeatDays.isEmpty()) {
                // One-time alarm
                if (target.timeInMillis <= now.timeInMillis) {
                    target.add(Calendar.DAY_OF_YEAR, 1)
                }
                return target.timeInMillis
            }

            // Repeating day alarm (Mon..Sun)
            val dayMap = mapOf(
                "Sun" to Calendar.SUNDAY,
                "Mon" to Calendar.MONDAY,
                "Tue" to Calendar.TUESDAY,
                "Wed" to Calendar.WEDNESDAY,
                "Thu" to Calendar.THURSDAY,
                "Fri" to Calendar.FRIDAY,
                "Sat" to Calendar.SATURDAY
            )
            val targetDays = repeatDays.mapNotNull { dayMap[it] }.toSet()

            while (target.timeInMillis <= now.timeInMillis || !targetDays.contains(target.get(Calendar.DAY_OF_WEEK))) {
                target.add(Calendar.DAY_OF_YEAR, 1)
            }

            return target.timeInMillis
        }
    }
}
