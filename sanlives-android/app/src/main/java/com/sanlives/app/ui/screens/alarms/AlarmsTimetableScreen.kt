package com.sanlives.app.ui.screens.alarms

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.sanlives.app.data.db.entity.AlarmEntity
import com.sanlives.app.data.db.entity.TimetableEntity
import com.sanlives.app.ui.components.CardWithAccentBar
import com.sanlives.app.ui.components.EmptyStateView
import com.sanlives.app.ui.components.IconChip
import com.sanlives.app.ui.theme.CategoryAlarmColor
import com.sanlives.app.ui.theme.CategoryTimetableColor
import com.sanlives.app.ui.theme.LocalSanLivesColors
import com.sanlives.app.ui.viewmodel.AlarmsViewModel
import com.sanlives.app.util.PermissionsHelper

@Composable
fun AlarmsTimetableScreen(
    viewModel: AlarmsViewModel,
    is12Hour: Boolean
) {
    val colors = LocalSanLivesColors.current
    val context = androidx.compose.ui.platform.LocalContext.current
    var selectedSubTab by remember { mutableIntStateOf(0) } // 0 = Alarms, 1 = Timetable

    val alarms by viewModel.alarms.collectAsState()
    val timetableEntries by viewModel.timetableEntries.collectAsState()

    var showAlarmDialog by remember { mutableStateOf(false) }
    var editingAlarm by remember { mutableStateOf<AlarmEntity?>(null) }

    var showTimetableDialog by remember { mutableStateOf(false) }
    var editingTimetable by remember { mutableStateOf<TimetableEntity?>(null) }

    Scaffold(
        containerColor = colors.background,
        floatingActionButton = {
            FloatingActionButton(
                onClick = {
                    if (selectedSubTab == 0) {
                        editingAlarm = null
                        showAlarmDialog = true
                    } else {
                        editingTimetable = null
                        showTimetableDialog = true
                    }
                },
                containerColor = colors.accentColor,
                contentColor = Color.White,
                shape = CircleShape
            ) {
                Icon(Icons.Default.Add, contentDescription = "Add")
            }
        }
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .padding(horizontal = 16.dp, vertical = 12.dp)
        ) {
            // Segmented Floating Pill Tabs (Alarms vs Timetable)
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .height(42.dp)
                    .clip(RoundedCornerShape(21.dp))
                    .background(colors.inputBackground)
                    .padding(3.dp)
            ) {
                Row(modifier = Modifier.fillMaxSize()) {
                    Box(
                        modifier = Modifier
                            .weight(1f)
                            .fillMaxHeight()
                            .clip(RoundedCornerShape(18.dp))
                            .background(if (selectedSubTab == 0) colors.accentColor else Color.Transparent)
                            .clickable { selectedSubTab = 0 },
                        contentAlignment = Alignment.Center
                    ) {
                        Text(
                            text = "⏰ Alarms",
                            fontSize = 12.5.sp,
                            fontWeight = FontWeight.Bold,
                            color = if (selectedSubTab == 0) Color.White else colors.textSecondary
                        )
                    }
                    Box(
                        modifier = Modifier
                            .weight(1f)
                            .fillMaxHeight()
                            .clip(RoundedCornerShape(18.dp))
                            .background(if (selectedSubTab == 1) colors.accentColor else Color.Transparent)
                            .clickable { selectedSubTab = 1 },
                        contentAlignment = Alignment.Center
                    ) {
                        Text(
                            text = "📅 Timetable",
                            fontSize = 12.5.sp,
                            fontWeight = FontWeight.Bold,
                            color = if (selectedSubTab == 1) Color.White else colors.textSecondary
                        )
                    }
                }
            }

            Spacer(modifier = Modifier.height(14.dp))

            // Background Reliability & Battery Optimization Guidance Banner
            val hasExactAlarm = remember { PermissionsHelper.hasExactAlarmPermission(context) }
            val isIgnoringBattery = remember { PermissionsHelper.isIgnoringBatteryOptimizations(context) }

            if (!hasExactAlarm) {
                Card(
                    shape = RoundedCornerShape(14.dp),
                    colors = CardDefaults.cardColors(containerColor = Color(0xFFEF4444).copy(alpha = 0.15f)),
                    border = BorderStroke(1.dp, Color(0xFFEF4444).copy(alpha = 0.3f)),
                    modifier = Modifier
                        .fillMaxWidth()
                        .clickable { PermissionsHelper.openExactAlarmSettings(context) }
                ) {
                    Row(
                        modifier = Modifier.padding(12.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text(text = "⚠️", fontSize = 20.sp)
                        Spacer(modifier = Modifier.width(10.dp))
                        Column(modifier = Modifier.weight(1f)) {
                            Text(
                                text = "Exact Alarms Disabled",
                                fontSize = 12.5.sp,
                                fontWeight = FontWeight.Bold,
                                color = Color(0xFFEF4444)
                            )
                            Text(
                                text = "Tap here to allow Dlives to schedule alarms that fire at the exact second.",
                                fontSize = 10.5.sp,
                                color = colors.textSecondary
                            )
                        }
                    }
                }
                Spacer(modifier = Modifier.height(10.dp))
            } else if (!isIgnoringBattery) {
                Card(
                    shape = RoundedCornerShape(14.dp),
                    colors = CardDefaults.cardColors(containerColor = Color(0xFFF59E0B).copy(alpha = 0.15f)),
                    border = BorderStroke(1.dp, Color(0xFFF59E0B).copy(alpha = 0.3f)),
                    modifier = Modifier
                        .fillMaxWidth()
                        .clickable { PermissionsHelper.requestIgnoreBatteryOptimizations(context) }
                ) {
                    Row(
                        modifier = Modifier.padding(12.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text(text = "🔋", fontSize = 20.sp)
                        Spacer(modifier = Modifier.width(10.dp))
                        Column(modifier = Modifier.weight(1f)) {
                            Text(
                                text = "Battery Optimization Active",
                                fontSize = 12.5.sp,
                                fontWeight = FontWeight.Bold,
                                color = Color(0xFFF59E0B)
                            )
                            Text(
                                text = "Tap to exempt app from Doze mode so alarms reliably ring when your phone is asleep.",
                                fontSize = 10.5.sp,
                                color = colors.textSecondary
                            )
                        }
                    }
                }
                Spacer(modifier = Modifier.height(10.dp))
            }

            if (selectedSubTab == 0) {
                // Alarms List
                if (alarms.isEmpty()) {
                    EmptyStateView(
                        icon = "⏰",
                        title = "No Alarms Set",
                        subtitle = "Tap the + button below to create your first exact alarm."
                    )
                } else {
                    LazyColumn(
                        verticalArrangement = Arrangement.spacedBy(10.dp),
                        modifier = Modifier.fillMaxSize()
                    ) {
                        items(alarms, key = { it.id }) { alarm ->
                            AlarmCard(
                                alarm = alarm,
                                is12Hour = is12Hour,
                                onToggle = { viewModel.toggleAlarm(alarm) },
                                onClick = {
                                    editingAlarm = alarm
                                    showAlarmDialog = true
                                },
                                onDelete = { viewModel.deleteAlarm(alarm) }
                            )
                        }
                    }
                }
            } else {
                // Timetable List
                if (timetableEntries.isEmpty()) {
                    EmptyStateView(
                        icon = "📅",
                        title = "Timetable Empty",
                        subtitle = "Schedule daily recurring tasks and routines."
                    )
                } else {
                    LazyColumn(
                        verticalArrangement = Arrangement.spacedBy(10.dp),
                        modifier = Modifier.fillMaxSize()
                    ) {
                        items(timetableEntries, key = { it.id }) { entry ->
                            TimetableCard(
                                entry = entry,
                                is12Hour = is12Hour,
                                onToggle = { viewModel.toggleTimetableEntry(entry) },
                                onClick = {
                                    editingTimetable = entry
                                    showTimetableDialog = true
                                },
                                onDelete = { viewModel.deleteTimetableEntry(entry) }
                            )
                        }
                    }
                }
            }
        }
    }

    if (showAlarmDialog) {
        AlarmEditDialog(
            alarm = editingAlarm,
            is12Hour = is12Hour,
            onDismiss = { showAlarmDialog = false },
            onSave = {
                viewModel.saveAlarm(it)
                showAlarmDialog = false
            }
        )
    }

    if (showTimetableDialog) {
        TimetableEditDialog(
            entry = editingTimetable,
            is12Hour = is12Hour,
            onDismiss = { showTimetableDialog = false },
            onSave = {
                viewModel.saveTimetableEntry(it)
                showTimetableDialog = false
            }
        )
    }
}

@Composable
fun AlarmCard(
    alarm: AlarmEntity,
    is12Hour: Boolean,
    onToggle: () -> Unit,
    onClick: () -> Unit,
    onDelete: () -> Unit
) {
    val colors = LocalSanLivesColors.current

    val timeFormatted = if (is12Hour) {
        val ampm = if (alarm.hour >= 12) "PM" else "AM"
        val h = alarm.hour % 12
        val displayHour = if (h == 0) 12 else h
        "%02d:%02d %s".format(displayHour, alarm.minute, ampm)
    } else {
        "%02d:%02d".format(alarm.hour, alarm.minute)
    }

    val repeatText = if (alarm.repeatDays.isEmpty()) "Once" else alarm.repeatDays.joinToString(" • ")

    CardWithAccentBar(
        categoryColor = CategoryAlarmColor,
        onClick = onClick
    ) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                IconChip(emoji = "⏰", accentColor = CategoryAlarmColor)
                Spacer(modifier = Modifier.width(12.dp))
                Column {
                    Text(
                        text = timeFormatted,
                        fontSize = 20.sp,
                        fontWeight = FontWeight.ExtraBold,
                        color = if (alarm.isEnabled) colors.textPrimary else colors.textSecondary.copy(alpha = 0.5f)
                    )
                    Text(
                        text = "${alarm.label}  |  $repeatText",
                        fontSize = 11.sp,
                        color = colors.textSecondary
                    )
                }
            }

            Row(verticalAlignment = Alignment.CenterVertically) {
                IconButton(onClick = onDelete) {
                    Icon(
                        Icons.Default.Delete,
                        contentDescription = "Delete",
                        tint = Color(0xFFEF4444).copy(alpha = 0.7f),
                        modifier = Modifier.size(20.dp)
                    )
                }
                Switch(
                    checked = alarm.isEnabled,
                    onCheckedChange = { onToggle() },
                    colors = SwitchDefaults.colors(
                        checkedThumbColor = Color.White,
                        checkedTrackColor = colors.accentColor,
                        uncheckedThumbColor = colors.textSecondary,
                        uncheckedTrackColor = colors.inputBackground
                    )
                )
            }
        }
    }
}

@Composable
fun TimetableCard(
    entry: TimetableEntity,
    is12Hour: Boolean,
    onToggle: () -> Unit,
    onClick: () -> Unit,
    onDelete: () -> Unit
) {
    val colors = LocalSanLivesColors.current

    val timeFormatted = if (is12Hour) {
        val ampm = if (entry.hour >= 12) "PM" else "AM"
        val h = entry.hour % 12
        val displayHour = if (h == 0) 12 else h
        "%02d:%02d %s".format(displayHour, entry.minute, ampm)
    } else {
        "%02d:%02d".format(entry.hour, entry.minute)
    }

    CardWithAccentBar(
        categoryColor = CategoryTimetableColor,
        onClick = onClick
    ) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Row(
                verticalAlignment = Alignment.CenterVertically,
                modifier = Modifier.weight(1f)
            ) {
                Checkbox(
                    checked = entry.isCompleted,
                    onCheckedChange = { onToggle() },
                    colors = CheckboxDefaults.colors(
                        checkedColor = CategoryTimetableColor,
                        checkmarkColor = Color.White,
                        uncheckedColor = colors.textSecondary
                    )
                )
                Spacer(modifier = Modifier.width(6.dp))
                Column {
                    Text(
                        text = entry.title,
                        fontSize = 14.sp,
                        fontWeight = FontWeight.Bold,
                        color = if (entry.isCompleted) colors.textSecondary.copy(alpha = 0.5f) else colors.textPrimary
                    )
                    Text(
                        text = timeFormatted + if (entry.description.isNotBlank()) " • ${entry.description}" else "",
                        fontSize = 11.sp,
                        color = colors.textSecondary
                    )
                }
            }

            IconButton(onClick = onDelete) {
                Icon(
                    Icons.Default.Delete,
                    contentDescription = "Delete",
                    tint = Color(0xFFEF4444).copy(alpha = 0.7f),
                    modifier = Modifier.size(20.dp)
                )
            }
        }
    }
}
