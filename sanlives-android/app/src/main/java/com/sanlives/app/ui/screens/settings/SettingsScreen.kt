package com.sanlives.app.ui.screens.settings

import android.widget.Toast
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.animation.*
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.hapticfeedback.HapticFeedbackType
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalHapticFeedback
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.sanlives.app.data.backup.BackupManager
import com.sanlives.app.service.FloatingIslandService
import com.sanlives.app.ui.components.CardWithAccentBar
import com.sanlives.app.ui.components.IconChip
import com.sanlives.app.ui.components.SanLivesPillButton
import com.sanlives.app.ui.components.SanLivesSlider
import com.sanlives.app.ui.theme.ACCENT_PRESETS
import com.sanlives.app.ui.theme.LocalSanLivesColors
import com.sanlives.app.ui.viewmodel.SettingsViewModel
import com.sanlives.app.util.PermissionsHelper
import kotlinx.coroutines.launch
import java.text.SimpleDateFormat
import java.util.*

@Composable
fun SettingsScreen(
    viewModel: SettingsViewModel,
    onLaunchBedsideMode: (() -> Unit)? = null
) {
    val colors = LocalSanLivesColors.current
    val context = LocalContext.current
    val haptic = LocalHapticFeedback.current
    val coroutineScope = rememberCoroutineScope()

    val themeMode by viewModel.themeMode.collectAsState()
    val accentName by viewModel.accentName.collectAsState()
    val is12h by viewModel.is12HourFormat.collectAsState()
    val isOverlayEnabled by viewModel.isOverlayEnabled.collectAsState()
    val alarmDuration by viewModel.alarmDurationSec.collectAsState()
    val islandPositionMode by viewModel.islandPositionMode.collectAsState()

    var hasExactAlarm by remember { mutableStateOf(PermissionsHelper.hasExactAlarmPermission(context)) }
    var hasOverlay by remember { mutableStateOf(PermissionsHelper.hasOverlayPermission(context)) }
    var hasNotifs by remember { mutableStateOf(PermissionsHelper.hasNotificationPermission(context)) }
    var hasBatteryOpt by remember { mutableStateOf(PermissionsHelper.isIgnoringBatteryOptimizations(context)) }

    // Export JSON Backup Launcher
    val exportLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.CreateDocument("application/json")
    ) { uri ->
        if (uri != null) {
            coroutineScope.launch {
                val success = BackupManager.exportToJson(context, uri)
                if (success) {
                    Toast.makeText(context, "✓ Backup Exported Successfully!", Toast.LENGTH_LONG).show()
                } else {
                    Toast.makeText(context, "❌ Export Failed. Check storage permissions.", Toast.LENGTH_SHORT).show()
                }
            }
        }
    }

    // Import JSON Backup Launcher
    val importLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.OpenDocument()
    ) { uri ->
        if (uri != null) {
            coroutineScope.launch {
                val success = BackupManager.importFromJson(context, uri)
                if (success) {
                    Toast.makeText(context, "✓ Backup Imported Successfully!", Toast.LENGTH_LONG).show()
                } else {
                    Toast.makeText(context, "❌ Import Failed. Invalid JSON structure.", Toast.LENGTH_SHORT).show()
                }
            }
        }
    }

    Scaffold(containerColor = colors.background) { padding ->
        LazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .padding(horizontal = 16.dp, vertical = 12.dp),
            verticalArrangement = Arrangement.spacedBy(14.dp)
        ) {
            // Header
            item {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    IconChip(emoji = "⚙️", accentColor = colors.accentColor, size = 32.dp)
                    Spacer(modifier = Modifier.width(10.dp))
                    Column {
                        Text(
                            text = "Settings & Preferences",
                            fontSize = 18.sp,
                            fontWeight = FontWeight.ExtraBold,
                            color = colors.textPrimary
                        )
                        Text(
                            text = "Customize visuals, floating island, and system behavior",
                            fontSize = 11.sp,
                            color = colors.textSecondary
                        )
                    }
                }
            }

            // SECTION 1: APPEARANCE & THEME
            item {
                SectionHeader("🎨 Appearance & Styling")
            }

            // Theme Mode Toggle
            item {
                CardWithAccentBar(categoryColor = colors.accentColor) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Column {
                            Text(
                                text = "Theme Mode",
                                fontSize = 14.sp,
                                fontWeight = FontWeight.Bold,
                                color = colors.textPrimary
                            )
                            Text(
                                text = if (themeMode == "dark") "OLED Deep Black (#0C0C0F)" else "Clean High-Contrast Light",
                                fontSize = 11.sp,
                                color = colors.textSecondary
                            )
                        }
                        Row(
                            modifier = Modifier
                                .clip(RoundedCornerShape(12.dp))
                                .background(colors.inputBackground)
                                .padding(2.dp)
                        ) {
                            ThemeToggleChip(
                                label = "🌙 Dark",
                                isSelected = themeMode == "dark",
                                onClick = {
                                    haptic.performHapticFeedback(HapticFeedbackType.TextHandleMove)
                                    viewModel.setThemeMode("dark")
                                }
                            )
                            ThemeToggleChip(
                                label = "☀️ Light",
                                isSelected = themeMode == "light",
                                onClick = {
                                    haptic.performHapticFeedback(HapticFeedbackType.TextHandleMove)
                                    viewModel.setThemeMode("light")
                                }
                            )
                        }
                    }
                }
            }

            // 12 Dynamic Accent Presets
            item {
                CardWithAccentBar(categoryColor = colors.accentColor) {
                    Text(
                        text = "Accent Color Preset",
                        fontSize = 14.sp,
                        fontWeight = FontWeight.Bold,
                        color = colors.textPrimary
                    )
                    Text(
                        text = "Matches desktop dual-mode gradient identity",
                        fontSize = 11.sp,
                        color = colors.textSecondary
                    )
                    Spacer(modifier = Modifier.height(12.dp))

                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween
                    ) {
                        ACCENT_PRESETS.take(6).forEach { preset ->
                            AccentColorChip(
                                preset = preset,
                                isSelected = accentName == preset.id,
                                isDark = themeMode == "dark",
                                onClick = {
                                    haptic.performHapticFeedback(HapticFeedbackType.TextHandleMove)
                                    viewModel.setAccentName(preset.id)
                                }
                            )
                        }
                    }
                    Spacer(modifier = Modifier.height(8.dp))
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween
                    ) {
                        ACCENT_PRESETS.drop(6).take(6).forEach { preset ->
                            AccentColorChip(
                                preset = preset,
                                isSelected = accentName == preset.id,
                                isDark = themeMode == "dark",
                                onClick = {
                                    haptic.performHapticFeedback(HapticFeedbackType.TextHandleMove)
                                    viewModel.setAccentName(preset.id)
                                }
                            )
                        }
                    }
                }
            }

            // 12h vs 24h Digital Time Format
            item {
                CardWithAccentBar(categoryColor = colors.accentColor) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Column {
                            Text(
                                text = "Digital Time Format",
                                fontSize = 14.sp,
                                fontWeight = FontWeight.Bold,
                                color = colors.textPrimary
                            )
                            Text(
                                text = if (is12h) "12-Hour format (e.g. 09:30 AM)" else "24-Hour Military format (e.g. 21:30)",
                                fontSize = 11.sp,
                                color = colors.textSecondary
                            )
                        }
                        Switch(
                            checked = is12h,
                            onCheckedChange = {
                                haptic.performHapticFeedback(HapticFeedbackType.TextHandleMove)
                                viewModel.set12HourFormat(it)
                            },
                            colors = SwitchDefaults.colors(
                                checkedThumbColor = Color.White,
                                checkedTrackColor = colors.accentColor
                            )
                        )
                    }
                }
            }

            // SECTION 2: FLOATING ISLAND ASSISTANT
            item {
                SectionHeader("🫧 Floating Island Assistant")
            }

            // Floating Island Bubble (SYSTEM_ALERT_WINDOW)
            item {
                CardWithAccentBar(categoryColor = Color(0xFF38BDF8)) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Column(modifier = Modifier.weight(1f)) {
                            Text(
                                text = "Floating Island Bubble",
                                fontSize = 14.sp,
                                fontWeight = FontWeight.Bold,
                                color = colors.textPrimary
                            )
                            Text(
                                text = "Draggable dynamic island assistant overlay with magnetic edge-docking",
                                fontSize = 11.sp,
                                color = colors.textSecondary
                            )
                        }
                        Switch(
                            checked = isOverlayEnabled,
                            onCheckedChange = { enabled ->
                                haptic.performHapticFeedback(HapticFeedbackType.TextHandleMove)
                                if (enabled) {
                                    if (!PermissionsHelper.hasOverlayPermission(context)) {
                                        Toast.makeText(context, "Please grant 'Display over other apps' permission", Toast.LENGTH_LONG).show()
                                        PermissionsHelper.openOverlaySettings(context)
                                    } else {
                                        viewModel.setOverlayEnabled(true)
                                        FloatingIslandService.start(context)
                                    }
                                } else {
                                    viewModel.setOverlayEnabled(false)
                                    FloatingIslandService.stop(context)
                                }
                            },
                            colors = SwitchDefaults.colors(
                                checkedThumbColor = Color.White,
                                checkedTrackColor = colors.accentColor
                            )
                        )
                    }
                }
            }

            // Camera Cutout & Island Docking Position Mode
            item {
                CardWithAccentBar(categoryColor = Color(0xFF38BDF8)) {
                    Column(modifier = Modifier.fillMaxWidth()) {
                        Text(
                            text = "Camera Cutout & Island Docking",
                            fontSize = 14.sp,
                            fontWeight = FontWeight.Bold,
                            color = colors.textPrimary
                        )
                        Text(
                            text = "Adapt Floating Island to your phone's front camera location",
                            fontSize = 11.sp,
                            color = colors.textSecondary
                        )
                        Spacer(modifier = Modifier.height(10.dp))
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.spacedBy(6.dp)
                        ) {
                            val positions = listOf(
                                "center" to "📍 Center",
                                "left" to "↖️ Left",
                                "right" to "↗️ Right",
                                "free" to "🖐️ Free"
                            )
                            positions.forEach { (modeKey, label) ->
                                val isSelected = islandPositionMode == modeKey
                                Box(
                                    modifier = Modifier
                                        .weight(1f)
                                        .clip(RoundedCornerShape(10.dp))
                                        .background(if (isSelected) colors.accentColor else colors.inputBackground)
                                        .clickable {
                                            haptic.performHapticFeedback(HapticFeedbackType.TextHandleMove)
                                            viewModel.setIslandPositionMode(modeKey)
                                            if (isOverlayEnabled) {
                                                FloatingIslandService.start(context)
                                            }
                                        }
                                        .padding(vertical = 8.dp),
                                    contentAlignment = Alignment.Center
                                ) {
                                    Text(
                                        text = label,
                                        fontSize = 11.sp,
                                        fontWeight = if (isSelected) FontWeight.Bold else FontWeight.Normal,
                                        color = if (isSelected) Color.White else colors.textSecondary
                                    )
                                }
                            }
                        }
                    }
                }
            }

            // Nightstand OLED Bedside Clock Mode
            item {
                CardWithAccentBar(categoryColor = Color(0xFF8B5CF6)) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Column(modifier = Modifier.weight(1f)) {
                            Text(
                                text = "🌙 Nightstand Bedside Clock",
                                fontSize = 14.sp,
                                fontWeight = FontWeight.Bold,
                                color = colors.textPrimary
                            )
                            Text(
                                text = "Minimalist OLED black clock with breathing digits and dimmer",
                                fontSize = 11.sp,
                                color = colors.textSecondary
                            )
                        }
                        SanLivesPillButton(
                            text = "Launch",
                            onClick = {
                                haptic.performHapticFeedback(HapticFeedbackType.LongPress)
                                onLaunchBedsideMode?.invoke()
                            },
                            backgroundColor = Color(0xFF8B5CF6)
                        )
                    }
                }
            }

            // SECTION 3: ALARMS & AUDIO BEHAVIOR
            item {
                SectionHeader("⏰ Alarms & Audio")
            }

            // Alarm Auto-Dismiss Duration Slider
            item {
                CardWithAccentBar(categoryColor = Color(0xFFEF4444)) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween
                    ) {
                        Text(
                            text = "Alarm Auto-Dismiss Duration",
                            fontSize = 14.sp,
                            fontWeight = FontWeight.Bold,
                            color = colors.textPrimary
                        )
                        Text(
                            text = "s",
                            fontSize = 13.sp,
                            fontWeight = FontWeight.Bold,
                            color = Color(0xFFEF4444)
                        )
                    }
                    Spacer(modifier = Modifier.height(4.dp))
                    SanLivesSlider(
                        value = alarmDuration.toFloat(),
                        onValueChange = { viewModel.setAlarmDurationSec(it.toInt()) },
                        valueRange = 10f..180f
                    )
                }
            }

            // SECTION 4: DATA BACKUP & RESTORE
            item {
                SectionHeader("💾 Data Backup & Restore")
            }

            item {
                CardWithAccentBar(categoryColor = Color(0xFF10B981)) {
                    Text(
                        text = "Full Device Backup & Restore",
                        fontSize = 14.sp,
                        fontWeight = FontWeight.Bold,
                        color = colors.textPrimary
                    )
                    Text(
                        text = "Export and restore all alarms, timetable, notes, calendar, and tasks into a clean .json file",
                        fontSize = 11.sp,
                        color = colors.textSecondary
                    )
                    Spacer(modifier = Modifier.height(12.dp))

                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(10.dp)
                    ) {
                        SanLivesPillButton(
                            text = "📤 Export Backup",
                            onClick = {
                                haptic.performHapticFeedback(HapticFeedbackType.LongPress)
                                val dateStr = SimpleDateFormat("yyyyMMdd_HHmm", Locale.getDefault()).format(Date())
                                exportLauncher.launch("sanlives_backup_.json")
                            },
                            backgroundColor = Color(0xFF10B981),
                            modifier = Modifier.weight(1f)
                        )

                        SanLivesPillButton(
                            text = "📥 Import Backup",
                            onClick = {
                                haptic.performHapticFeedback(HapticFeedbackType.LongPress)
                                importLauncher.launch(arrayOf("application/json", "text/*"))
                            },
                            backgroundColor = colors.inputBackground,
                            contentColor = colors.textPrimary,
                            modifier = Modifier.weight(1f)
                        )
                    }
                }
            }

            // SECTION 5: SYSTEM PERMISSIONS & RELIABILITY
            item {
                SectionHeader("⚡ System Permissions & Battery")
            }

            item {
                CardWithAccentBar(categoryColor = Color(0xFF64748B)) {
                    Text(
                        text = "Background Reliability & Permissions",
                        fontSize = 14.sp,
                        fontWeight = FontWeight.Bold,
                        color = colors.textPrimary
                    )
                    Spacer(modifier = Modifier.height(10.dp))

                    PermissionRow("Exact Alarms (SCHEDULE_EXACT_ALARM)", hasExactAlarm) {
                        PermissionsHelper.openExactAlarmSettings(context)
                    }
                    Spacer(modifier = Modifier.height(6.dp))
                    PermissionRow("Overlay Bubble (SYSTEM_ALERT_WINDOW)", hasOverlay) {
                        PermissionsHelper.openOverlaySettings(context)
                    }
                    Spacer(modifier = Modifier.height(6.dp))
                    PermissionRow("Notifications (POST_NOTIFICATIONS)", hasNotifs) {
                        PermissionsHelper.openNotificationSettings(context)
                    }
                    Spacer(modifier = Modifier.height(6.dp))
                    PermissionRow("Ignore Battery Optimizations (Guaranteed Alarms)", hasBatteryOpt) {
                        PermissionsHelper.requestIgnoreBatteryOptimizations(context)
                    }
                }
            }

            // SECTION 6: DESKTOP SYNC (FUTURE STAGE)
            item {
                SectionHeader("🔗 Desktop Synchronization")
            }

            item {
                CardWithAccentBar(categoryColor = Color(0xFF64748B)) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Column(modifier = Modifier.weight(1f)) {
                            Text(
                                text = "Dlives Desktop Sync",
                                fontSize = 14.sp,
                                fontWeight = FontWeight.Bold,
                                color = colors.textPrimary
                            )
                            Text(
                                text = "Local Wi-Fi peer-to-peer sync engine (Coming in Next Stage)",
                                fontSize = 11.sp,
                                color = colors.textSecondary
                            )
                        }
                        Switch(
                            checked = false,
                            onCheckedChange = {
                                Toast.makeText(context, "Desktop Sync will be available in the next release!", Toast.LENGTH_SHORT).show()
                            },
                            enabled = false
                        )
                    }
                }
            }

            item {
                Spacer(modifier = Modifier.height(16.dp))
            }
        }
    }
}

@Composable
fun SectionHeader(title: String) {
    val colors = LocalSanLivesColors.current
    Text(
        text = title,
        fontSize = 12.5.sp,
        fontWeight = FontWeight.Bold,
        color = colors.accentColor,
        letterSpacing = 0.5.sp,
        modifier = Modifier.padding(top = 4.dp, bottom = 2.dp)
    )
}

@Composable
fun ThemeToggleChip(
    label: String,
    isSelected: Boolean,
    onClick: () -> Unit
) {
    val colors = LocalSanLivesColors.current
    Box(
        modifier = Modifier
            .clip(RoundedCornerShape(10.dp))
            .background(if (isSelected) colors.accentColor else Color.Transparent)
            .clickable { onClick() }
            .padding(horizontal = 12.dp, vertical = 6.dp)
    ) {
        Text(
            text = label,
            fontSize = 11.sp,
            fontWeight = FontWeight.Bold,
            color = if (isSelected) Color.White else colors.textSecondary
        )
    }
}

@Composable
fun AccentColorChip(
    preset: com.sanlives.app.ui.theme.AccentPreset,
    isSelected: Boolean,
    isDark: Boolean,
    onClick: () -> Unit
) {
    val color = if (isDark) preset.darkColor else preset.lightColor
    Box(
        modifier = Modifier
            .size(36.dp)
            .clip(CircleShape)
            .background(color)
            .clickable { onClick() }
            .padding(4.dp),
        contentAlignment = Alignment.Center
    ) {
        if (isSelected) {
            Box(
                modifier = Modifier
                    .size(12.dp)
                    .clip(CircleShape)
                    .background(Color.White)
            )
        }
    }
}

@Composable
fun PermissionRow(
    title: String,
    isGranted: Boolean,
    onManage: () -> Unit
) {
    val colors = LocalSanLivesColors.current
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically
    ) {
        Column(modifier = Modifier.weight(1f)) {
            Text(
                text = title,
                fontSize = 11.5.sp,
                color = colors.textPrimary
            )
            Text(
                text = if (isGranted) "✅ Granted" else "⚠️ Action Required",
                fontSize = 10.sp,
                fontWeight = FontWeight.Bold,
                color = if (isGranted) Color(0xFF10B981) else Color(0xFFEF4444)
            )
        }
        if (!isGranted) {
            TextButton(onClick = onManage) {
                Text("Grant", fontSize = 11.sp, color = colors.accentColor)
            }
        }
    }
}
