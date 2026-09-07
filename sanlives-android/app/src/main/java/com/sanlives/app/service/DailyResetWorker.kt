package com.sanlives.app.service

import android.content.Context
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import com.sanlives.app.data.db.AppDatabase

class DailyResetWorker(
    appContext: Context,
    workerParams: WorkerParameters
) : CoroutineWorker(appContext, workerParams) {

    override suspend fun doWork(): Result {
        return try {
            val db = AppDatabase.getDatabase(applicationContext)
            db.timetableDao().resetDailyCompletion()
            Result.success()
        } catch (e: Exception) {
            Result.retry()
        }
    }
}
