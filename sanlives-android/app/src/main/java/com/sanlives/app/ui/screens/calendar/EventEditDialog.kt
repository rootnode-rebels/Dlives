package com.sanlives.app.ui.screens.calendar

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.window.Dialog
import com.sanlives.app.data.db.entity.CalendarEventEntity
import com.sanlives.app.ui.components.SanLivesPillButton
import com.sanlives.app.ui.theme.LocalSanLivesColors
import java.time.LocalDate

@Composable
fun EventEditDialog(
    selectedDate: LocalDate,
    event: CalendarEventEntity?,
    onDismiss: () -> Unit,
    onSave: (CalendarEventEntity) -> Unit
) {
    val colors = LocalSanLivesColors.current

    var title by remember { mutableStateOf(event?.title ?: "") }
    var description by remember { mutableStateOf(event?.description ?: "") }
    var startTime by remember { mutableStateOf(event?.startTime ?: "09:00") }
    var colorTag by remember { mutableStateOf(event?.colorTag ?: "#38BDF8") }

    val colorOptions = listOf("#38BDF8", "#8B5CF6", "#10B981", "#F59E0B", "#EF4444", "#FF4081")

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
                    text = if (event == null) "➕ Add Calendar Event" else "✏️ Edit Event",
                    fontSize = 16.sp,
                    fontWeight = FontWeight.Bold,
                    color = colors.textPrimary
                )

                Text(
                    text = selectedDate.toString(),
                    fontSize = 12.sp,
                    color = colors.accentColor
                )

                Spacer(modifier = Modifier.height(16.dp))

                OutlinedTextField(
                    value = title,
                    onValueChange = { title = it },
                    label = { Text("Event Title", fontSize = 11.sp) },
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
                    value = startTime,
                    onValueChange = { startTime = it },
                    label = { Text("Time (e.g. 10:30 AM)", fontSize = 11.sp) },
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
                    label = { Text("Description / Location", fontSize = 11.sp) },
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

                Spacer(modifier = Modifier.height(14.dp))

                // Color Tag Selection
                Text(
                    text = "Event Color Tag:",
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
                    colorOptions.forEach { hex ->
                        val parsed = try { Color(android.graphics.Color.parseColor(hex)) } catch (e: Exception) { Color(0xFF38BDF8) }
                        val isSelected = colorTag.equals(hex, ignoreCase = true)
                        Box(
                            modifier = Modifier
                                .size(32.dp)
                                .clip(CircleShape)
                                .background(parsed)
                                .clickable { colorTag = hex }
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
                }

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
                        text = "Save Event",
                        onClick = {
                            if (title.isNotBlank()) {
                                val newEvent = (event ?: CalendarEventEntity(
                                    title = title,
                                    dateEpochDay = selectedDate.toEpochDay()
                                )).copy(
                                    title = title.trim(),
                                    description = description.trim(),
                                    startTime = startTime.trim(),
                                    colorTag = colorTag,
                                    dateEpochDay = selectedDate.toEpochDay(),
                                    lastModified = System.currentTimeMillis()
                                )
                                onSave(newEvent)
                            }
                        }
                    )
                }
            }
        }
    }
}
