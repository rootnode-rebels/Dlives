package com.sanlives.app.ui.screens.bedside

import android.app.Activity
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.os.BatteryManager
import android.view.WindowManager
import androidx.compose.animation.core.*
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.BrightnessLow
import androidx.compose.material.icons.filled.Close
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.sanlives.app.data.db.entity.AlarmEntity
import com.sanlives.app.ui.theme.LocalSanLivesColors
import kotlinx.coroutines.delay
import java.text.SimpleDateFormat
import java.util.*

@Composable
fun BedsideClockScreen(
    is12Hour: Boolean,
    nextAlarm: AlarmEntity?,
    onExit: () -> Unit
) {
    val context = LocalContext.current
    val activity = context as? Activity

    var currentTimeStr by remember { mutableStateOf("") }
    var currentSecondsStr by remember { mutableStateOf("") }
    var currentDateStr by remember { mutableStateOf("") }
    var shiftOffset by remember { mutableIntStateOf(0) }
    var brightnessLevel by remember { mutableFloatStateOf(0.15f) }
    var showBrightnessControl by remember { mutableStateOf(false) }

    // Keep screen on during nightstand mode
    DisposableEffect(Unit) {
        activity?.window?.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        val originalBrightness = activity?.window?.attributes?.screenBrightness
        activity?.window?.attributes = activity?.window?.attributes?.apply {
            screenBrightness = brightnessLevel
        }
        onDispose {
            activity?.window?.clearFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
            activity?.window?.attributes = activity?.window?.attributes?.apply {
                screenBrightness = originalBrightness ?: WindowManager.LayoutParams.BRIGHTNESS_OVERRIDE_NONE
            }
        }
    }

    // Update screen brightness dynamically
    LaunchedEffect(brightnessLevel) {
        activity?.window?.attributes = activity?.window?.attributes?.apply {
            screenBrightness = brightnessLevel
        }
    }

    // Live Clock & Anti-Burn-In Pixel Shifter
    LaunchedEffect(Unit) {
        while (true) {
            val now = Date()
            val timeFormat = if (is12Hour) SimpleDateFormat("hh:mm", Locale.getDefault()) else SimpleDateFormat("HH:mm", Locale.getDefault())
            val ampmFormat = if (is12Hour) SimpleDateFormat("a", Locale.getDefault()).format(now) else ""
            currentTimeStr = " ".trim()
            currentSecondsStr = SimpleDateFormat("ss", Locale.getDefault()).format(now)
            currentDateStr = SimpleDateFormat("EEEE, MMMM d", Locale.getDefault()).format(now)

            // Anti-Burn-In: slight 2px shift every 60s
            shiftOffset = (0..6).random()
            delay(1000)
        }
    }

    // Battery percentage lookup
    val batteryStatus = remember {
        val ifilter = IntentFilter(Intent.ACTION_BATTERY_CHANGED)
        val batteryIntent = context.registerReceiver(null, ifilter)
        val level = batteryIntent?.getIntExtra(BatteryManager.EXTRA_LEVEL, -1) ?: -1
        val scale = batteryIntent?.getIntExtra(BatteryManager.EXTRA_SCALE, -1) ?: -1
        if (level >= 0 && scale > 0) (level * 100 / scale) else 100
    }

    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(Color.Black)
            .padding(24.dp),
        contentAlignment = Alignment.Center
    ) {
        // Top Exit & Brightness Toolbar
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .align(Alignment.TopCenter),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            IconButton(onClick = onExit) {
                Icon(Icons.Default.Close, contentDescription = "Exit", tint = Color(0xFF64748B))
            }

            Row(verticalAlignment = Alignment.CenterVertically) {
                IconButton(onClick = { showBrightnessControl = !showBrightnessControl }) {
                    Icon(Icons.Default.BrightnessLow, contentDescription = "Brightness", tint = Color(0xFF64748B))
                }
                Spacer(modifier = Modifier.width(6.dp))
                Text(
                    text = "🔋 %",
                    fontSize = 11.sp,
                    color = Color(0xFF475569)
                )
            }
        }

        // Main Breathing OLED Clock
        Column(
            modifier = Modifier.offset(x = shiftOffset.dp, y = shiftOffset.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            // Digital Time
            Row(verticalAlignment = Alignment.Bottom) {
                Text(
                    text = currentTimeStr.ifBlank { "00:00" },
                    fontSize = 72.sp,
                    fontWeight = FontWeight.Thin,
                    color = Color(0xFFE2E8F0).copy(alpha = 0.85f),
                    letterSpacing = 2.sp
                )
                Spacer(modifier = Modifier.width(8.dp))
                Text(
                    text = currentSecondsStr,
                    fontSize = 24.sp,
                    fontWeight = FontWeight.Light,
                    color = Color(0xFF38BDF8).copy(alpha = 0.6f),
                    modifier = Modifier.padding(bottom = 14.dp)
                )
            }

            Spacer(modifier = Modifier.height(6.dp))

            // Date
            Text(
                text = currentDateStr,
                fontSize = 14.sp,
                color = Color(0xFF64748B).copy(alpha = 0.8f)
            )

            Spacer(modifier = Modifier.height(20.dp))

            // Next Alarm Pill
            if (nextAlarm != null) {
                Box(
                    modifier = Modifier
                        .clip(RoundedCornerShape(20.dp))
                        .background(Color(0xFF1E222D).copy(alpha = 0.6f))
                        .padding(horizontal = 14.dp, vertical = 6.dp)
                ) {
                    Text(
                        text = "⏰ %02d:%02d • %s".format(nextAlarm.hour, nextAlarm.minute, nextAlarm.label),
                        fontSize = 12.sp,
                        fontWeight = FontWeight.SemiBold,
                        color = Color(0xFF38BDF8).copy(alpha = 0.8f)
                    )
                }
            }
        }

        // Bottom Dimming Slider Overlay
        if (showBrightnessControl) {
            Card(
                modifier = Modifier
                    .fillMaxWidth(0.75f)
                    .align(Alignment.BottomCenter)
                    .padding(bottom = 16.dp),
                shape = RoundedCornerShape(16.dp),
                colors = CardDefaults.cardColors(containerColor = Color(0xFF15171E).copy(alpha = 0.9f))
            ) {
                Column(modifier = Modifier.padding(14.dp), horizontalAlignment = Alignment.CenterHorizontally) {
                    Text(
                        text = "Dimmer: %",
                        fontSize = 11.sp,
                        color = Color.White
                    )
                    Spacer(modifier = Modifier.height(4.dp))
                    Slider(
                        value = brightnessLevel,
                        onValueChange = { brightnessLevel = it },
                        valueRange = 0.02f..1.0f,
                        colors = SliderDefaults.colors(
                            thumbColor = Color(0xFF38BDF8),
                            activeTrackColor = Color(0xFF38BDF8),
                            inactiveTrackColor = Color(0xFF232733)
                        )
                    )
                }
            }
        }
    }
}
