package com.sanlives.app.service

import android.animation.ValueAnimator
import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
import android.graphics.PixelFormat
import android.os.Build
import android.os.IBinder
import android.util.DisplayMetrics
import android.view.Gravity
import android.view.MotionEvent
import android.view.WindowManager
import android.view.animation.DecelerateInterpolator
import androidx.compose.runtime.*
import androidx.compose.ui.platform.ComposeView
import androidx.core.app.NotificationCompat
import androidx.lifecycle.*
import androidx.savedstate.*
import com.sanlives.app.MainActivity
import com.sanlives.app.SanLivesApp
import com.sanlives.app.data.db.AppDatabase
import com.sanlives.app.data.db.entity.AlarmEntity
import com.sanlives.app.data.db.entity.NoteEntity
import com.sanlives.app.data.db.entity.TimetableEntity
import com.sanlives.app.ui.screens.overlay.FloatingIslandOverlayView
import kotlinx.coroutines.*
import kotlinx.coroutines.flow.collectLatest

class FloatingIslandService : Service(), LifecycleOwner, ViewModelStoreOwner, SavedStateRegistryOwner {

    private val lifecycleRegistry = LifecycleRegistry(this)
    private val store = ViewModelStore()
    private val savedStateRegistryController = SavedStateRegistryController.create(this)

    override val lifecycle: Lifecycle get() = lifecycleRegistry
    override val viewModelStore: ViewModelStore get() = store
    override val savedStateRegistry: SavedStateRegistry get() = savedStateRegistryController.savedStateRegistry

    private var windowManager: WindowManager? = null
    private var overlayComposeView: ComposeView? = null
    private var windowLayoutParams: WindowManager.LayoutParams? = null

    private val serviceScope = CoroutineScope(Dispatchers.Main + SupervisorJob())
    private val isExpanded = mutableStateOf(false)

    override fun onCreate() {
        super.onCreate()
        savedStateRegistryController.performRestore(null)
        lifecycleRegistry.handleLifecycleEvent(Lifecycle.Event.ON_CREATE)
        lifecycleRegistry.handleLifecycleEvent(Lifecycle.Event.ON_START)
        lifecycleRegistry.handleLifecycleEvent(Lifecycle.Event.ON_RESUME)

        createNotificationChannel()
        startForeground(NOTIFICATION_ID, createNotification())

        setupFloatingIslandWindow()
    }

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                CHANNEL_ID,
                "Floating Island Assistant",
                NotificationManager.IMPORTANCE_LOW
            ).apply {
                description = "Keeps the Dlives dynamic island assistant floating"
                setShowBadge(false)
            }
            val nm = getSystemService(NotificationManager::class.java)
            nm?.createNotificationChannel(channel)
        }
    }

    private fun createNotification(): Notification {
        val intent = Intent(this, MainActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP
        }
        val pendingIntent = PendingIntent.getActivity(
            this,
            0,
            intent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )

        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle("Dlives Floating Island")
            .setContentText("Dynamic Assistant is active")
            .setSmallIcon(android.R.drawable.ic_dialog_info)
            .setContentIntent(pendingIntent)
            .setOngoing(true)
            .setPriority(NotificationCompat.PRIORITY_LOW)
            .build()
    }

    private fun setupFloatingIslandWindow() {
        windowManager = getSystemService(WINDOW_SERVICE) as WindowManager

        val layoutType = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY
        } else {
            @Suppress("DEPRECATION")
            WindowManager.LayoutParams.TYPE_PHONE
        }

        val app = application as SanLivesApp
        val db = AppDatabase.getDatabase(this)
        val prefs = app.preferencesManager

        val displayMetrics = DisplayMetrics()
        windowManager?.defaultDisplay?.getMetrics(displayMetrics)
        val screenWidth = displayMetrics.widthPixels

        val statusBarResId = resources.getIdentifier("status_bar_height", "dimen", "android")
        val statusBarHeight = if (statusBarResId > 0) resources.getDimensionPixelSize(statusBarResId) else 75

        // DEFAULT: Top-Right safe corner (so it never overlaps status bar or left-aligned screen headers)
        val defaultTopRightX = (screenWidth - 340).coerceAtLeast(30)
        val defaultTopRightY = statusBarHeight + 24
        val initialX = prefs.getSavedIslandX(defaultTopRightX)
        val initialY = prefs.getSavedIslandY(defaultTopRightY)

        windowLayoutParams = WindowManager.LayoutParams(
            WindowManager.LayoutParams.WRAP_CONTENT,
            WindowManager.LayoutParams.WRAP_CONTENT,
            layoutType,
            WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE or
                    WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN or
                    WindowManager.LayoutParams.FLAG_LAYOUT_NO_LIMITS,
            PixelFormat.TRANSLUCENT
        ).apply {
            gravity = Gravity.TOP or Gravity.START
            x = initialX
            y = initialY
        }

        overlayComposeView = ComposeView(this).apply {
            setViewTreeLifecycleOwner(this@FloatingIslandService)
            setViewTreeSavedStateRegistryOwner(this@FloatingIslandService)

            setContent {
                val themeMode by prefs.themeMode.collectAsState()
                val accentName by prefs.accentName.collectAsState()
                val is12h by prefs.is12HourFormat.collectAsState()
                val positionMode by prefs.islandPositionMode.collectAsState()

                var nextAlarm by remember { mutableStateOf<AlarmEntity?>(null) }
                val timetableTasks = remember { mutableStateListOf<TimetableEntity>() }
                val pinnedNotes = remember { mutableStateListOf<NoteEntity>() }

                LaunchedEffect(Unit) {
                    db.alarmDao().getAllAlarms().collectLatest { list ->
                        nextAlarm = list.firstOrNull { it.isEnabled }
                    }
                }

                LaunchedEffect(Unit) {
                    db.timetableDao().getAllEntries().collectLatest { list ->
                        timetableTasks.clear()
                        timetableTasks.addAll(list)
                    }
                }

                LaunchedEffect(Unit) {
                    db.noteDao().getPinnedQuickNotes().collectLatest { list ->
                        pinnedNotes.clear()
                        pinnedNotes.addAll(list)
                    }
                }

                // Dynamically update window flags when expanded to allow soft keyboard input
                LaunchedEffect(isExpanded.value) {
                    val params = windowLayoutParams ?: return@LaunchedEffect
                    if (isExpanded.value) {
                        params.flags = WindowManager.LayoutParams.FLAG_NOT_TOUCH_MODAL or
                                WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN or
                                WindowManager.LayoutParams.FLAG_WATCH_OUTSIDE_TOUCH
                    } else {
                        params.flags = WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE or
                                WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN
                    }
                    try {
                        windowManager?.updateViewLayout(overlayComposeView, params)
                    } catch (e: Exception) {
                        e.printStackTrace()
                    }
                }

                FloatingIslandOverlayView(
                    isExpanded = isExpanded.value,
                    onToggleExpand = { isExpanded.value = !isExpanded.value },
                    nextAlarm = nextAlarm,
                    timetableTasks = timetableTasks,
                    pinnedNotes = pinnedNotes,
                    themeMode = themeMode,
                    accentName = accentName,
                    is12Hour = is12h,
                    onDrag = { dx, dy ->
                        val params = windowLayoutParams ?: return@FloatingIslandOverlayView
                        params.x += dx
                        params.y = (params.y + dy).coerceAtLeast(statusBarHeight)
                        try {
                            windowManager?.updateViewLayout(overlayComposeView, params)
                        } catch (e: Exception) {
                            e.printStackTrace()
                        }
                    },
                    onDragEnd = {
                        val params = windowLayoutParams ?: return@FloatingIslandOverlayView
                        val targetX = when (positionMode) {
                            "left" -> if (params.x < screenWidth / 2) 24 else (screenWidth - 340).coerceAtLeast(30)
                            "center" -> {
                                val centerX = (screenWidth - 340) / 2
                                when {
                                    Math.abs(params.x - centerX) < 180 && params.y < 250 -> centerX
                                    params.x + 100 > screenWidth / 2 -> (screenWidth - 340).coerceAtLeast(30)
                                    else -> 24
                                }
                            }
                            else -> { // "right" or "free"
                                params.x.coerceIn(24, (screenWidth - 340).coerceAtLeast(24))
                            }
                        }
                        val anim = ValueAnimator.ofInt(params.x, targetX).apply {
                            duration = 240
                            interpolator = DecelerateInterpolator()
                            addUpdateListener { va ->
                                params.x = va.animatedValue as Int
                                try {
                                    windowManager?.updateViewLayout(overlayComposeView, params)
                                } catch (e: Exception) {
                                    e.printStackTrace()
                                }
                            }
                        }
                        anim.start()
                        prefs.saveIslandPosition(targetX, params.y)
                    },
                    onToggleTimetableTask = { task ->
                        serviceScope.launch(Dispatchers.IO) {
                            db.timetableDao().updateEntry(
                                task.copy(isCompleted = !task.isCompleted, lastModified = System.currentTimeMillis())
                            )
                        }
                    },
                    onQuickSaveNote = { content ->
                        serviceScope.launch(Dispatchers.IO) {
                            db.noteDao().insertNote(
                                NoteEntity(
                                    title = "Quick Memo",
                                    content = content,
                                    isPinnedQuickNote = true
                                )
                            )
                        }
                    },
                    onOpenMainApp = { screenRoute ->
                        val intent = Intent(this@FloatingIslandService, MainActivity::class.java).apply {
                            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_SINGLE_TOP
                            putExtra("target_screen", screenRoute)
                        }
                        startActivity(intent)
                        isExpanded.value = false
                    }
                )
            }

            // Outside touch listener to collapse island when expanded
            setOnTouchListener { _, event ->
                if (event.action == MotionEvent.ACTION_OUTSIDE && isExpanded.value) {
                    isExpanded.value = false
                    true
                } else {
                    false
                }
            }
        }

        windowManager?.addView(overlayComposeView, windowLayoutParams)
    }

    override fun onDestroy() {
        super.onDestroy()
        lifecycleRegistry.handleLifecycleEvent(Lifecycle.Event.ON_DESTROY)
        serviceScope.cancel()

        try {
            if (overlayComposeView != null) {
                windowManager?.removeView(overlayComposeView)
                overlayComposeView = null
            }
        } catch (e: Exception) {
            e.printStackTrace()
        }
    }

    override fun onConfigurationChanged(newConfig: android.content.res.Configuration) {
        super.onConfigurationChanged(newConfig)
        val displayMetrics = DisplayMetrics()
        windowManager?.defaultDisplay?.getMetrics(displayMetrics)
        val screenWidth = displayMetrics.widthPixels
        val app = application as SanLivesApp
        val defaultTopRightX = (screenWidth - 340).coerceAtLeast(30)
        val newX = app.preferencesManager.getSavedIslandX(defaultTopRightX)

        windowLayoutParams?.let { params ->
            params.x = newX
            try {
                if (overlayComposeView != null) {
                    windowManager?.updateViewLayout(overlayComposeView, params)
                }
            } catch (e: Exception) {
                e.printStackTrace()
            }
        }
    }

    override fun onBind(intent: Intent?): IBinder? = null

    companion object {
        private const val NOTIFICATION_ID = 9981
        private const val CHANNEL_ID = "sanlives_floating_island_channel"

        fun start(context: Context) {
            val intent = Intent(context, FloatingIslandService::class.java)
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                context.startForegroundService(intent)
            } else {
                context.startService(intent)
            }
        }

        fun stop(context: Context) {
            val intent = Intent(context, FloatingIslandService::class.java)
            context.stopService(intent)
        }
    }
}
