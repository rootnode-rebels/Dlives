package com.sanlives.app

import android.Manifest
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.Surface
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.core.content.ContextCompat
import com.sanlives.app.service.FloatingIslandService
import com.sanlives.app.ui.screens.MainContainerScreen
import com.sanlives.app.ui.theme.SanLivesTheme
import com.sanlives.app.util.PermissionsHelper
import kotlinx.coroutines.launch

class MainActivity : ComponentActivity() {

    private val requestNotificationPermissionLauncher =
        registerForActivityResult(ActivityResultContracts.RequestPermission()) { isGranted ->
            // Notification permission handled
        }

    private val targetScreenState = androidx.compose.runtime.mutableStateOf("alarms")

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        val target = intent?.getStringExtra("target_screen") ?: "alarms"
        targetScreenState.value = target

        // Request POST_NOTIFICATIONS on Android 13+
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            if (ContextCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) {
                requestNotificationPermissionLauncher.launch(Manifest.permission.POST_NOTIFICATIONS)
            }
        }

        val app = application as SanLivesApp
        val prefs = app.preferencesManager

        // Handle shared incoming text (e.g. from browser or other apps)
        if (intent?.action == android.content.Intent.ACTION_SEND && intent.type == "text/plain") {
            val sharedText = intent.getStringExtra(android.content.Intent.EXTRA_TEXT)
            if (!sharedText.isNullOrBlank()) {
                kotlinx.coroutines.CoroutineScope(kotlinx.coroutines.Dispatchers.IO).launch {
                    app.repository.insertNote(
                        com.sanlives.app.data.db.entity.NoteEntity(
                            title = "Shared Note",
                            content = sharedText,
                            isPinnedQuickNote = false
                        )
                    )
                }
            }
        }

        // Restore Floating Island Service if enabled
        if (prefs.isOverlayEnabled.value && PermissionsHelper.hasOverlayPermission(this)) {
            FloatingIslandService.start(this)
        }

        setContent {
            val themeMode by prefs.themeMode.collectAsState()
            val accentName by prefs.accentName.collectAsState()

            SanLivesTheme(themeMode = themeMode, accentName = accentName) {
                Surface(
                    modifier = Modifier.fillMaxSize()
                ) {
                    MainContainerScreen(targetScreen = targetScreenState.value)
                }
            }
        }
    }

    override fun onNewIntent(intent: android.content.Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        val target = intent.getStringExtra("target_screen") ?: "alarms"
        targetScreenState.value = target
    }
}
