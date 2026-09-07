package com.sanlives.app.ui.screens.calendar

import androidx.compose.animation.*
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
import androidx.compose.material.icons.filled.ChevronLeft
import androidx.compose.material.icons.filled.ChevronRight
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.sanlives.app.data.db.entity.CalendarEventEntity
import com.sanlives.app.ui.components.CardWithAccentBar
import com.sanlives.app.ui.components.EmptyStateView
import com.sanlives.app.ui.components.IconChip
import com.sanlives.app.ui.theme.CategoryCalendarColor
import com.sanlives.app.ui.theme.LocalSanLivesColors
import com.sanlives.app.ui.viewmodel.CalendarViewModel
import java.time.DayOfWeek
import java.time.LocalDate
import java.time.YearMonth
import java.time.format.TextStyle
import java.util.*

@Composable
fun CalendarScreen(viewModel: CalendarViewModel) {
    val colors = LocalSanLivesColors.current
    val selectedDate by viewModel.selectedDate.collectAsState()
    val datesWithEvents by viewModel.datesWithEvents.collectAsState()
    val eventsForDate by viewModel.eventsForSelectedDate.collectAsState()

    var currentYearMonth by remember { mutableStateOf(YearMonth.from(selectedDate)) }
    var showAddDialog by remember { mutableStateOf(false) }
    var editingEvent by remember { mutableStateOf<CalendarEventEntity?>(null) }

    Scaffold(
        containerColor = colors.background,
        floatingActionButton = {
            FloatingActionButton(
                onClick = {
                    editingEvent = null
                    showAddDialog = true
                },
                containerColor = CategoryCalendarColor,
                contentColor = Color.White,
                shape = CircleShape
            ) {
                Icon(Icons.Default.Add, contentDescription = "Add Event")
            }
        }
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .padding(horizontal = 16.dp, vertical = 12.dp)
        ) {
            // Month Header & Navigation
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = "${currentYearMonth.month.getDisplayName(TextStyle.FULL, Locale.getDefault())} ${currentYearMonth.year}",
                    fontSize = 18.sp,
                    fontWeight = FontWeight.ExtraBold,
                    color = colors.textPrimary
                )

                Row {
                    IconButton(
                        onClick = { currentYearMonth = currentYearMonth.minusMonths(1) }
                    ) {
                        Icon(Icons.Default.ChevronLeft, contentDescription = "Prev Month", tint = colors.textPrimary)
                    }
                    IconButton(
                        onClick = { currentYearMonth = currentYearMonth.plusMonths(1) }
                    ) {
                        Icon(Icons.Default.ChevronRight, contentDescription = "Next Month", tint = colors.textPrimary)
                    }
                }
            }

            Spacer(modifier = Modifier.height(10.dp))

            // Days of Week Header (Mon..Sun)
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceAround
            ) {
                listOf("M", "T", "W", "T", "F", "S", "S").forEach { day ->
                    Text(
                        text = day,
                        fontSize = 11.sp,
                        fontWeight = FontWeight.Bold,
                        color = colors.textSecondary,
                        textAlign = TextAlign.Center,
                        modifier = Modifier.width(36.dp)
                    )
                }
            }

            Spacer(modifier = Modifier.height(8.dp))

            // Month Days Grid
            MonthDaysGrid(
                yearMonth = currentYearMonth,
                selectedDate = selectedDate,
                datesWithEvents = datesWithEvents.toSet(),
                onDateSelected = { viewModel.setSelectedDate(it) }
            )

            Spacer(modifier = Modifier.height(16.dp))

            // Selected Date Schedule Header
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically
            ) {
                IconChip(emoji = "📅", accentColor = CategoryCalendarColor, size = 28.dp)
                Spacer(modifier = Modifier.width(8.dp))
                Text(
                    text = "Events for ${selectedDate.dayOfWeek.getDisplayName(TextStyle.SHORT, Locale.getDefault())}, ${selectedDate.month.getDisplayName(TextStyle.SHORT, Locale.getDefault())} ${selectedDate.dayOfMonth}",
                    fontSize = 13.sp,
                    fontWeight = FontWeight.Bold,
                    color = colors.textPrimary
                )
            }

            Spacer(modifier = Modifier.height(10.dp))

            // Events List
            if (eventsForDate.isEmpty()) {
                EmptyStateView(
                    icon = "🌴",
                    title = "Nothing Scheduled",
                    subtitle = "Tap the + button to add an event for this date."
                )
            } else {
                LazyColumn(
                    verticalArrangement = Arrangement.spacedBy(8.dp),
                    modifier = Modifier.fillMaxSize()
                ) {
                    items(eventsForDate, key = { it.id }) { event ->
                        EventCard(
                            event = event,
                            onClick = {
                                editingEvent = event
                                showAddDialog = true
                            },
                            onDelete = { viewModel.deleteEvent(event) }
                        )
                    }
                }
            }
        }
    }

    if (showAddDialog) {
        EventEditDialog(
            selectedDate = selectedDate,
            event = editingEvent,
            onDismiss = { showAddDialog = false },
            onSave = {
                viewModel.saveEvent(it)
                showAddDialog = false
            }
        )
    }
}

@Composable
fun MonthDaysGrid(
    yearMonth: YearMonth,
    selectedDate: LocalDate,
    datesWithEvents: Set<Long>,
    onDateSelected: (LocalDate) -> Unit
) {
    val colors = LocalSanLivesColors.current
    val today = LocalDate.now()

    val firstDayOfMonth = yearMonth.atDay(1)
    val daysInMonth = yearMonth.lengthOfMonth()
    val dayOfWeekOffset = (firstDayOfMonth.dayOfWeek.value - 1) % 7 // Monday = 0

    val totalCells = ((dayOfWeekOffset + daysInMonth + 6) / 7) * 7

    Column(modifier = Modifier.fillMaxWidth()) {
        for (week in 0 until (totalCells / 7)) {
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(vertical = 2.dp),
                horizontalArrangement = Arrangement.SpaceAround
            ) {
                for (day in 0 until 7) {
                    val cellIndex = week * 7 + day
                    val dayOfMonth = cellIndex - dayOfWeekOffset + 1

                    if (dayOfMonth in 1..daysInMonth) {
                        val date = yearMonth.atDay(dayOfMonth)
                        val isSelected = date == selectedDate
                        val isToday = date == today
                        val hasEvents = datesWithEvents.contains(date.toEpochDay())
                        val isWeekend = date.dayOfWeek == DayOfWeek.SATURDAY || date.dayOfWeek == DayOfWeek.SUNDAY

                        Box(
                            modifier = Modifier
                                .size(38.dp)
                                .clip(CircleShape)
                                .background(
                                    when {
                                        isSelected -> colors.accentColor
                                        isToday -> colors.accentColor.copy(alpha = 0.2f)
                                        else -> Color.Transparent
                                    }
                                )
                                .clickable { onDateSelected(date) },
                            contentAlignment = Alignment.Center
                        ) {
                            Column(horizontalAlignment = Alignment.CenterHorizontally) {
                                Text(
                                    text = "$dayOfMonth",
                                    fontSize = 12.sp,
                                    fontWeight = if (isSelected || isToday) FontWeight.Bold else FontWeight.Normal,
                                    color = when {
                                        isSelected -> Color.White
                                        isToday -> colors.accentColor
                                        isWeekend -> colors.textSecondary.copy(alpha = 0.6f)
                                        else -> colors.textPrimary
                                    }
                                )
                                if (hasEvents) {
                                    Box(
                                        modifier = Modifier
                                            .size(4.dp)
                                            .clip(CircleShape)
                                            .background(if (isSelected) Color.White else CategoryCalendarColor)
                                    )
                                }
                            }
                        }
                    } else {
                        Spacer(modifier = Modifier.size(38.dp))
                    }
                }
            }
        }
    }
}

@Composable
fun EventCard(
    event: CalendarEventEntity,
    onClick: () -> Unit,
    onDelete: () -> Unit
) {
    val colors = LocalSanLivesColors.current
    val tagColor = remember(event.colorTag) {
        try { Color(android.graphics.Color.parseColor(event.colorTag)) } catch (e: Exception) { CategoryCalendarColor }
    }

    CardWithAccentBar(
        categoryColor = tagColor,
        onClick = onClick
    ) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = event.title,
                    fontSize = 14.sp,
                    fontWeight = FontWeight.Bold,
                    color = colors.textPrimary
                )
                if (!event.startTime.isNullOrBlank()) {
                    Text(
                        text = "⏰ " + if (event.description.isNotBlank()) " • " else "",
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
