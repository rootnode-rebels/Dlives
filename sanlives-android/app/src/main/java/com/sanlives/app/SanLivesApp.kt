package com.sanlives.app

import android.app.Application
import android.app.NotificationChannel
import android.app.NotificationManager
import android.media.AudioAttributes
import android.media.RingtoneManager
import android.os.Build
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import com.sanlives.app.data.db.AppDatabase
import com.sanlives.app.data.preferences.PreferencesManager
import com.sanlives.app.data.repository.AppRepository
import com.sanlives.app.service.DailyResetWorker
import java.util.concurrent.TimeUnit

class SanLivesApp : Application() {

    lateinit var database: AppDatabase
        private set

    lateinit var repository: AppRepository
        private set

    lateinit var preferencesManager: PreferencesManager
        private set

    override fun onCreate() {
        super.onCreate()

        database = AppDatabase.getDatabase(this)
        repository = AppRepository(database)
        preferencesManager = PreferencesManager(this)

        createNotificationChannels()
        scheduleDailyResetWork()
    }

    private fun createNotificationChannels() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val nm = getSystemService(NotificationManager::class.java)

            // Alarms Channel
            val alarmSound = RingtoneManager.getDefaultUri(RingtoneManager.TYPE_ALARM)
            val alarmChannel = NotificationChannel(
                CHANNEL_ALARMS_ID,
                "Dlives Alarms",
                NotificationManager.IMPORTANCE_HIGH
            ).apply {
                description = "Critical Alarm alerts with full screen priority"
                enableLights(true)
                enableVibration(true)
                setBypassDnd(true)
                setSound(
                    alarmSound,
                    AudioAttributes.Builder()
                        .setUsage(AudioAttributes.USAGE_ALARM)
                        .setContentType(AudioAttributes.CONTENT_TYPE_SONIFICATION)
                        .build()
                )
            }

            // Foreground Island Service Channel
            val serviceChannel = NotificationChannel(
                CHANNEL_SERVICE_ID,
                "Dlives Assistant Service",
                NotificationManager.IMPORTANCE_LOW
            ).apply {
                description = "Keeps the floating island bubble assistant active"
            }

            nm.createNotificationChannels(listOf(alarmChannel, serviceChannel))
        }
    }

    private fun scheduleDailyResetWork() {
        val resetWork = PeriodicWorkRequestBuilder<DailyResetWorker>(24, TimeUnit.HOURS)
            .build()

        WorkManager.getInstance(this).enqueueUniquePeriodicWork(
            "SanLivesDailyTimetableReset",
            ExistingPeriodicWorkPolicy.KEEP,
            resetWork
        )
    }

    companion object {
        const val CHANNEL_ALARMS_ID = "sanlives_alarms_channel"
        const val CHANNEL_SERVICE_ID = "sanlives_service_channel"
    }
}
