package com.sanlives.app.ui.screens.alarms

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.window.Dialog
import com.sanlives.app.data.db.entity.TimetableEntity
import com.sanlives.app.ui.components.SanLivesPillButton
import com.sanlives.app.ui.components.WheelTimePicker
import com.sanlives.app.ui.theme.LocalSanLivesColors
import java.util.*

@Composable
fun TimetableEditDialog(
    entry: TimetableEntity?,
    is12Hour: Boolean,
    onDismiss: () -> Unit,
    onSave: (TimetableEntity) -> Unit
) {
    val colors = LocalSanLivesColors.current

    val initialHour = entry?.hour ?: Calendar.getInstance().get(Calendar.HOUR_OF_DAY)
    val initialMinute = entry?.minute ?: Calendar.getInstance().get(Calendar.MINUTE)

    var selectedHour by remember { mutableIntStateOf(initialHour) }
    var selectedMinute by remember { mutableIntStateOf(initialMinute) }
    var title by remember { mutableStateOf(entry?.title ?: "") }
    var description by remember { mutableStateOf(entry?.description ?: "") }

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
                    text = if (entry == null) "➕ Add Timetable Task" else "✏️ Edit Timetable Task",
                    fontSize = 16.sp,
                    fontWeight = FontWeight.Bold,
                    color = colors.textPrimary
                )

                Spacer(modifier = Modifier.height(16.dp))

                WheelTimePicker(
                    initialHour = selectedHour,
                    initialMinute = selectedMinute,
                    is12Hour = is12Hour,
                    onTimeSelected = { h, m ->
                        selectedHour = h
                        selectedMinute = m
                    }
                )

                Spacer(modifier = Modifier.height(16.dp))

                OutlinedTextField(
                    value = title,
                    onValueChange = { title = it },
                    label = { Text("Task Title", fontSize = 11.sp) },
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

                Spacer(modifier = Modifier.height(10.dp))

                OutlinedTextField(
                    value = description,
                    onValueChange = { description = it },
                    label = { Text("Notes / Details (Optional)", fontSize = 11.sp) },
                    singleLine = false,
                    maxLines = 3,
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

                Spacer(modifier = Modifier.height(20.dp))

                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.End
                ) {
                    TextButton(onClick = onDismiss) {
                        Text("Cancel", color = colors.textSecondary)
                    }
                    Spacer(modifier = Modifier.width(8.dp))
                    SanLivesPillButton(
                        text = "Save Task",
                        onClick = {
                            if (title.isNotBlank()) {
                                val newEntry = (entry ?: TimetableEntity(
                                    hour = selectedHour,
                                    minute = selectedMinute,
                                    title = title
                                )).copy(
                                    hour = selectedHour,
                                    minute = selectedMinute,
                                    title = title.trim(),
                                    description = description.trim(),
                                    lastModified = System.currentTimeMillis()
                                )
                                onSave(newEntry)
                            }
                        }
                    )
                }
            }
        }
    }
}
