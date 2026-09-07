package com.sanlives.app.alarm

import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.media.AudioAttributes
import android.media.RingtoneManager
import android.net.Uri
import android.os.Build
import android.os.PowerManager
import androidx.core.app.NotificationCompat
import com.sanlives.app.R
import com.sanlives.app.SanLivesApp

class AlarmReceiver : BroadcastReceiver() {

    override fun onReceive(context: Context, intent: Intent) {
        val action = intent.action ?: return
        val alarmId = intent.getLongExtra(EXTRA_ALARM_ID, -1L)
        val label = intent.getStringExtra(EXTRA_ALARM_LABEL) ?: "Alarm"
        val hour = intent.getIntExtra(EXTRA_ALARM_HOUR, 0)
        val minute = intent.getIntExtra(EXTRA_ALARM_MINUTE, 0)
        val soundUri = intent.getStringExtra(EXTRA_ALARM_SOUND_URI)
        val snoozeMin = intent.getIntExtra(EXTRA_ALARM_SNOOZE_MIN, 10)
        val repeatDays = intent.getStringArrayListExtra(EXTRA_ALARM_REPEAT_DAYS) ?: arrayListOf()
        val mission = intent.getStringExtra(EXTRA_ALARM_MISSION) ?: "none"

        when (action) {
            ACTION_ALARM_FIRE -> {
                // Acquire temporary partial wake lock to guarantee execution
                val pm = context.getSystemService(Context.POWER_SERVICE) as PowerManager
                val wakeLock = pm.newWakeLock(
                    PowerManager.PARTIAL_WAKE_LOCK or PowerManager.ACQUIRE_CAUSES_WAKEUP,
                    "SanLives:AlarmWakeLock"
                )
                wakeLock.acquire(30000)

                // Launch Full-Screen Wake-up Activity
                val fullScreenIntent = Intent(context, AlarmAlertActivity::class.java).apply {
                    flags = Intent.FLAG_ACTIVITY_NEW_TASK or
                            Intent.FLAG_ACTIVITY_CLEAR_TOP or
                            Intent.FLAG_ACTIVITY_EXCLUDE_FROM_RECENTS
                    putExtra(EXTRA_ALARM_ID, alarmId)
                    putExtra(EXTRA_ALARM_LABEL, label)
                    putExtra(EXTRA_ALARM_HOUR, hour)
                    putExtra(EXTRA_ALARM_MINUTE, minute)
                    putExtra(EXTRA_ALARM_SOUND_URI, soundUri)
                    putExtra(EXTRA_ALARM_SNOOZE_MIN, snoozeMin)
                    putExtra(EXTRA_ALARM_REPEAT_DAYS, repeatDays)
                    putExtra(EXTRA_ALARM_MISSION, mission)
                }

                val fullScreenPendingIntent = PendingIntent.getActivity(
                    context,
                    alarmId.toInt(),
                    fullScreenIntent,
                    PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
                )

                // Post high-priority Heads-up Notification
                showAlarmNotification(context, alarmId, label, fullScreenPendingIntent, soundUri)

                // Direct launch activity if screen is interactive/on or as background full screen
                context.startActivity(fullScreenIntent)

                // Notify Floating Island overlay if running
                val islandIntent = Intent(ACTION_ISLAND_ALARM_NOTIFY).apply {
                    putExtra(EXTRA_ALARM_ID, alarmId)
                    putExtra(EXTRA_ALARM_LABEL, label)
                }
                context.sendBroadcast(islandIntent)
            }
            ACTION_ALARM_SNOOZE -> {
                dismissAlarmNotification(context, alarmId)
                val scheduler = AlarmScheduler(context)
                scheduler.scheduleSnooze(alarmId, label, snoozeMin, soundUri)
            }
            ACTION_ALARM_DISMISS -> {
                dismissAlarmNotification(context, alarmId)
            }
        }
    }

    private fun showAlarmNotification(
        context: Context,
        alarmId: Long,
        label: String,
        fullScreenPendingIntent: PendingIntent,
        soundUriStr: String?
    ) {
        val nm = context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        val channelId = SanLivesApp.CHANNEL_ALARMS_ID

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val soundUri = if (soundUriStr != null) Uri.parse(soundUriStr) else RingtoneManager.getDefaultUri(RingtoneManager.TYPE_ALARM)
            val channel = NotificationChannel(channelId, "Dlives Alarms", NotificationManager.IMPORTANCE_HIGH).apply {
                description = "Critical Alarm alerts with sound and full screen"
                enableLights(true)
                enableVibration(true)
                setBypassDnd(true)
                setSound(
                    soundUri,
                    AudioAttributes.Builder()
                        .setUsage(AudioAttributes.USAGE_ALARM)
                        .setContentType(AudioAttributes.CONTENT_TYPE_SONIFICATION)
                        .build()
                )
            }
            nm.createNotificationChannel(channel)
        }

        // Snooze intent action
        val snoozeIntent = Intent(context, AlarmReceiver::class.java).apply {
            action = ACTION_ALARM_SNOOZE
            putExtra(EXTRA_ALARM_ID, alarmId)
            putExtra(EXTRA_ALARM_LABEL, label)
        }
        val snoozePendingIntent = PendingIntent.getBroadcast(
            context,
            (alarmId + 200000).toInt(),
            snoozeIntent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )

        // Dismiss intent action
        val dismissIntent = Intent(context, AlarmReceiver::class.java).apply {
            action = ACTION_ALARM_DISMISS
            putExtra(EXTRA_ALARM_ID, alarmId)
        }
        val dismissPendingIntent = PendingIntent.getBroadcast(
            context,
            (alarmId + 300000).toInt(),
            dismissIntent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )

        val notification = NotificationCompat.Builder(context, channelId)
            .setSmallIcon(R.drawable.ic_sanlives_logo)
            .setContentTitle("⏰ $label")
            .setContentText("Dlives Alarm is firing!")
            .setPriority(NotificationCompat.PRIORITY_MAX)
            .setCategory(NotificationCompat.CATEGORY_ALARM)
            .setVisibility(NotificationCompat.VISIBILITY_PUBLIC)
            .setFullScreenIntent(fullScreenPendingIntent, true)
            .setContentIntent(fullScreenPendingIntent)
            .addAction(R.drawable.ic_sanlives_logo, "Snooze", snoozePendingIntent)
            .addAction(R.drawable.ic_sanlives_logo, "Dismiss", dismissPendingIntent)
            .setAutoCancel(true)
            .setOngoing(true)
            .build()

        nm.notify(alarmId.toInt(), notification)
    }

    private fun dismissAlarmNotification(context: Context, alarmId: Long) {
        val nm = context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        nm.cancel(alarmId.toInt())
    }

    companion object {
        const val ACTION_ALARM_FIRE = "com.sanlives.app.ACTION_ALARM_FIRE"
        const val ACTION_ALARM_SNOOZE = "com.sanlives.app.ACTION_ALARM_SNOOZE"
        const val ACTION_ALARM_DISMISS = "com.sanlives.app.ACTION_ALARM_DISMISS"
        const val ACTION_ISLAND_ALARM_NOTIFY = "com.sanlives.app.ACTION_ISLAND_ALARM_NOTIFY"

        const val EXTRA_ALARM_ID = "extra_alarm_id"
        const val EXTRA_ALARM_LABEL = "extra_alarm_label"
        const val EXTRA_ALARM_HOUR = "extra_alarm_hour"
        const val EXTRA_ALARM_MINUTE = "extra_alarm_minute"
        const val EXTRA_ALARM_SOUND_URI = "extra_alarm_sound_uri"
        const val EXTRA_ALARM_SNOOZE_MIN = "extra_alarm_snooze_min"
        const val EXTRA_ALARM_REPEAT_DAYS = "extra_alarm_repeat_days"
        const val EXTRA_ALARM_MISSION = "extra_alarm_mission"
    }
}
