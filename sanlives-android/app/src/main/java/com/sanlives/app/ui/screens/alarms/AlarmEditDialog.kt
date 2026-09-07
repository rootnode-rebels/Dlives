package com.sanlives.app.ui.screens.alarms

import android.provider.OpenableColumns
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.MusicNote
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.window.Dialog
import com.sanlives.app.data.db.entity.AlarmEntity
import com.sanlives.app.ui.components.SanLivesPillButton
import com.sanlives.app.ui.components.WheelTimePicker
import com.sanlives.app.ui.theme.LocalSanLivesColors
import java.util.*

@Composable
fun AlarmEditDialog(
    alarm: AlarmEntity?,
    is12Hour: Boolean,
    onDismiss: () -> Unit,
    onSave: (AlarmEntity) -> Unit
) {
    val colors = LocalSanLivesColors.current
    val context = LocalContext.current

    val initialHour = alarm?.hour ?: Calendar.getInstance().get(Calendar.HOUR_OF_DAY)
    val initialMinute = alarm?.minute ?: Calendar.getInstance().get(Calendar.MINUTE)

    var selectedHour by remember { mutableIntStateOf(initialHour) }
    var selectedMinute by remember { mutableIntStateOf(initialMinute) }
    var label by remember { mutableStateOf(alarm?.label ?: "Alarm") }
    val selectedDays = remember { mutableStateListOf<String>().apply { if (alarm != null) addAll(alarm.repeatDays) } }
    var snoozeMin by remember { mutableIntStateOf(alarm?.snoozeDurationMinutes ?: 10) }
    var soundUri by remember { mutableStateOf(alarm?.soundUri) }
    var soundTitle by remember { mutableStateOf(alarm?.soundTitle ?: "Default Alarm Tone") }
    var mission by remember { mutableStateOf(alarm?.dismissMission ?: "none") }

    val daysOfWeek = listOf("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")

    // Audio file picker launcher
    val audioPickerLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.GetContent()
    ) { uri ->
        if (uri != null) {
            soundUri = uri.toString()
            var displayName = "Custom Audio Tone"
            try {
                context.contentResolver.query(uri, null, null, null, null)?.use { cursor ->
                    val nameIndex = cursor.getColumnIndex(OpenableColumns.DISPLAY_NAME)
                    if (cursor.moveToFirst() && nameIndex != -1) {
                        displayName = cursor.getString(nameIndex)
                    }
                }
            } catch (e: Exception) {
                e.printStackTrace()
            }
            soundTitle = displayName
        }
    }

    Dialog(onDismissRequest = onDismiss) {
        Card(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp),
            shape = RoundedCornerShape(20.dp),
            colors = CardDefaults.cardColors(containerColor = colors.cardBackground)
        ) {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(20.dp),
                horizontalAlignment = Alignment.CenterHorizontally
            ) {
                Text(
                    text = if (alarm == null) "➕ Set New Alarm" else "✏️ Edit Alarm",
                    fontSize = 16.sp,
                    fontWeight = FontWeight.Bold,
                    color = colors.textPrimary
                )

                Spacer(modifier = Modifier.height(14.dp))

                // Vertical Direct-Snap Wheel Time Picker
                WheelTimePicker(
                    initialHour = selectedHour,
                    initialMinute = selectedMinute,
                    is12Hour = is12Hour,
                    onTimeSelected = { h, m ->
                        selectedHour = h
                        selectedMinute = m
                    }
                )

                Spacer(modifier = Modifier.height(14.dp))

                // Alarm Label Input
                OutlinedTextField(
                    value = label,
                    onValueChange = { label = it },
                    label = { Text("Alarm Label", fontSize = 11.sp) },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(10.dp),
                    colors = OutlinedTextFieldDefaults.colors(
                        focusedContainerColor = colors.inputBackground,
                        unfocusedContainerColor = colors.inputBackground,
                        focusedBorderColor = colors.accentColor,
                        unfocusedBorderColor = colors.inputBorder,
                        focusedTextColor = colors.textPrimary,
                        unfocusedTextColor = colors.textPrimary
                    )
                )

                Spacer(modifier = Modifier.height(12.dp))

                // Custom Audio Ringtone / Tone Picker
                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .clip(RoundedCornerShape(10.dp))
                        .background(colors.inputBackground)
                        .clickable { audioPickerLauncher.launch("audio/*") }
                        .padding(horizontal = 12.dp, vertical = 8.dp)
                ) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Row(verticalAlignment = Alignment.CenterVertically, modifier = Modifier.weight(1f)) {
                            Icon(Icons.Default.MusicNote, contentDescription = "Tone", tint = colors.accentColor, modifier = Modifier.size(18.dp))
                            Spacer(modifier = Modifier.width(8.dp))
                            Column {
                                Text(
                                    text = "Sound Tone",
                                    fontSize = 10.sp,
                                    color = colors.textSecondary
                                )
                                Text(
                                    text = soundTitle,
                                    fontSize = 12.sp,
                                    fontWeight = FontWeight.SemiBold,
                                    color = colors.textPrimary,
                                    maxLines = 1,
                                    overflow = TextOverflow.Ellipsis
                                )
                            }
                        }
                        Text(
                            text = "Change ↗",
                            fontSize = 11.sp,
                            fontWeight = FontWeight.Bold,
                            color = colors.accentColor
                        )
                    }
                }

                Spacer(modifier = Modifier.height(12.dp))

                // Repeat Days Chips
                Text(
                    text = "Repeat on:",
                    fontSize = 11.sp,
                    fontWeight = FontWeight.SemiBold,
                    color = colors.textSecondary,
                    modifier = Modifier.align(Alignment.Start)
                )
                Spacer(modifier = Modifier.height(6.dp))
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween
                ) {
                    daysOfWeek.forEach { day ->
                        val isSelected = selectedDays.contains(day)
                        Box(
                            modifier = Modifier
                                .size(34.dp)
                                .clip(CircleShape)
                                .background(if (isSelected) colors.accentColor else colors.inputBackground)
                                .clickable {
                                    if (isSelected) selectedDays.remove(day) else selectedDays.add(day)
                                },
                            contentAlignment = Alignment.Center
                        ) {
                            Text(
                                text = day.take(1),
                                fontSize = 11.sp,
                                fontWeight = FontWeight.Bold,
                                color = if (isSelected) Color.White else colors.textSecondary
                            )
                        }
                    }
                }

                Spacer(modifier = Modifier.height(12.dp))

                // Snooze Duration Selector
                Text(
                    text = "Snooze Duration:",
                    fontSize = 11.sp,
                    fontWeight = FontWeight.SemiBold,
                    color = colors.textSecondary,
                    modifier = Modifier.align(Alignment.Start)
                )
                Spacer(modifier = Modifier.height(6.dp))
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween
                ) {
                    listOf(5, 10, 15, 30).forEach { mins ->
                        val isSelected = snoozeMin == mins
                        Box(
                            modifier = Modifier
                                .clip(RoundedCornerShape(8.dp))
                                .background(if (isSelected) colors.accentColor else colors.inputBackground)
                                .clickable { snoozeMin = mins }
                                .padding(horizontal = 12.dp, vertical = 6.dp),
                            contentAlignment = Alignment.Center
                        ) {
                            Text(
                                text = "${mins}m",
                                fontSize = 11.sp,
                                fontWeight = FontWeight.Bold,
                                color = if (isSelected) Color.White else colors.textSecondary
                            )
                        }
                    }
                }

                Spacer(modifier = Modifier.height(12.dp))

                // Wake-Up Dismiss Mission Challenge Selector
                Text(
                    text = "Wake-Up Mission Challenge:",
                    fontSize = 11.sp,
                    fontWeight = FontWeight.SemiBold,
                    color = colors.textSecondary,
                    modifier = Modifier.align(Alignment.Start)
                )
                Spacer(modifier = Modifier.height(6.dp))
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween
                ) {
                    val missionOptions = listOf(
                        "none" to "Standard",
                        "math" to "🔢 Math",
                        "shake" to "📳 Shake"
                    )
                    missionOptions.forEach { (key, label) ->
                        val isSelected = mission == key
                        Box(
                            modifier = Modifier
                                .clip(RoundedCornerShape(8.dp))
                                .background(if (isSelected) Color(0xFFEF4444) else colors.inputBackground)
                                .clickable { mission = key }
                                .padding(horizontal = 10.dp, vertical = 6.dp),
                            contentAlignment = Alignment.Center
                        ) {
                            Text(
                                text = label,
                                fontSize = 11.sp,
                                fontWeight = FontWeight.Bold,
                                color = if (isSelected) Color.White else colors.textSecondary
                            )
                        }
                    }
                }

                Spacer(modifier = Modifier.height(18.dp))

                // Dialog Buttons
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.End
                ) {
                    TextButton(onClick = onDismiss) {
                        Text("Cancel", color = colors.textSecondary)
                    }
                    Spacer(modifier = Modifier.width(8.dp))
                    SanLivesPillButton(
                        text = "Save Alarm",
                        onClick = {
                            val newAlarm = (alarm ?: AlarmEntity(hour = selectedHour, minute = selectedMinute)).copy(
                                hour = selectedHour,
                                minute = selectedMinute,
                                label = label.ifBlank { "Alarm" },
                                repeatDays = selectedDays.toList(),
                                soundUri = soundUri,
                                soundTitle = soundTitle,
                                snoozeDurationMinutes = snoozeMin,
                                dismissMission = mission,
                                isEnabled = true,
                                lastModified = System.currentTimeMillis()
                            )
                            onSave(newAlarm)
                        }
                    )
                }
            }
        }
    }
}
