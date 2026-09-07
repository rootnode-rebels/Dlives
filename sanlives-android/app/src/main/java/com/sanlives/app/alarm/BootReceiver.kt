package com.sanlives.app.alarm

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import com.sanlives.app.data.db.AppDatabase
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch

class BootReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        val action = intent.action
        if (action == Intent.ACTION_BOOT_COMPLETED ||
            action == Intent.ACTION_MY_PACKAGE_REPLACED ||
            action == Intent.ACTION_TIME_CHANGED ||
            action == Intent.ACTION_TIMEZONE_CHANGED) {

            val scheduler = AlarmScheduler(context)
            val db = AppDatabase.getDatabase(context)

            CoroutineScope(Dispatchers.IO).launch {
                try {
                    val alarms = db.alarmDao().getEnabledAlarms()
                    alarms.forEach { alarm ->
                        scheduler.schedule(alarm)
                    }
                } catch (e: Exception) {
                    e.printStackTrace()
                }
            }
        }
    }
}
