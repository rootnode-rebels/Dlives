package com.sanlives.app.sync

import android.content.Context
import android.net.nsd.NsdManager
import android.net.nsd.NsdServiceInfo
import android.os.Build
import android.util.Log
import com.sanlives.app.data.db.AppDatabase
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject

object LocalSyncManager {

    private const val TAG = "SanLivesSync"
    private const val SERVICE_TYPE = "_sanlives._tcp."
    private const val SERVICE_NAME = "SanLives-Android"
    private const val SYNC_PORT = 8990

    private var nsdManager: NsdManager? = null
    private var registrationListener: NsdManager.RegistrationListener? = null
    private var isRegistered = false

    fun startBroadcasting(context: Context) {
        if (isRegistered) return

        try {
            nsdManager = context.getSystemService(Context.NSD_SERVICE) as NsdManager
            val serviceInfo = NsdServiceInfo().apply {
                serviceName = SERVICE_NAME
                serviceType = SERVICE_TYPE
                port = SYNC_PORT
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP) {
                    setAttribute("device", Build.MODEL)
                    setAttribute("version", "3.2.1")
                }
            }

            registrationListener = object : NsdManager.RegistrationListener {
                override fun onServiceRegistered(serviceInfo: NsdServiceInfo) {
                    Log.d(TAG, "NSD Service Registered: ${serviceInfo.serviceName}")
                    isRegistered = true
                }

                override fun onRegistrationFailed(serviceInfo: NsdServiceInfo, errorCode: Int) {
                    Log.e(TAG, "NSD Registration Failed: $errorCode")
                    isRegistered = false
                }

                override fun onServiceUnregistered(serviceInfo: NsdServiceInfo) {
                    Log.d(TAG, "NSD Service Unregistered")
                    isRegistered = false
                }

                override fun onUnregistrationFailed(serviceInfo: NsdServiceInfo, errorCode: Int) {
                    Log.e(TAG, "NSD Unregistration Failed: $errorCode")
                }
            }

            nsdManager?.registerService(serviceInfo, NsdManager.PROTOCOL_DNS_SD, registrationListener)
        } catch (e: Exception) {
            Log.e(TAG, "Failed to start NSD broadcasting", e)
        }
    }

    fun stopBroadcasting() {
        if (!isRegistered) return
        try {
            registrationListener?.let { nsdManager?.unregisterService(it) }
            isRegistered = false
        } catch (e: Exception) {
            Log.e(TAG, "Failed to stop NSD broadcasting", e)
        }
    }

    suspend fun buildSyncPayload(context: Context): JSONObject = withContext(Dispatchers.IO) {
        val db = AppDatabase.getDatabase(context)
        val payload = JSONObject()

        payload.put("deviceModel", Build.MODEL)
        payload.put("protocolVersion", 2)
        payload.put("timestamp", System.currentTimeMillis())

        // Notes
        val notes = db.noteDao().getAllNotes().first()
        val notesArr = JSONArray()
        notes.forEach { n ->
            notesArr.put(JSONObject().apply {
                put("title", n.title)
                put("content", n.content)
                put("categoryTag", n.categoryTag)
                put("isPinnedQuickNote", n.isPinnedQuickNote)
                put("lastModified", n.lastModified)
            })
        }
        payload.put("notes", notesArr)

        // Tasks
        val tasks = db.taskDao().getAllTasks().first()
        val tasksArr = JSONArray()
        tasks.forEach { t ->
            tasksArr.put(JSONObject().apply {
                put("title", t.title)
                put("isCompleted", t.isCompleted)
                put("categoryTag", t.categoryTag)
                put("lastModified", t.lastModified)
            })
        }
        payload.put("tasks", tasksArr)

        payload
    }
}
