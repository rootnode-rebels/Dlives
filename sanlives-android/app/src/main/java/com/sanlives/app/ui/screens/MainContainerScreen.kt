package com.sanlives.app.ui.screens

import androidx.compose.animation.*
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.viewmodel.compose.viewModel
import com.sanlives.app.ui.screens.alarms.AlarmsTimetableScreen
import com.sanlives.app.ui.screens.calendar.CalendarScreen
import com.sanlives.app.ui.screens.notes.NoteDetailScreen
import com.sanlives.app.ui.screens.notes.NotesListScreen
import com.sanlives.app.ui.screens.pomodoro.PomodoroScreen
import com.sanlives.app.ui.screens.settings.SettingsScreen
import com.sanlives.app.ui.screens.tasks.TasksScreen
import com.sanlives.app.ui.theme.LocalSanLivesColors
import com.sanlives.app.ui.viewmodel.*

sealed class Screen(val route: String, val title: String, val icon: String) {
    object Alarms : Screen("alarms", "Alarms", "⏰")
    object Pomodoro : Screen("pomodoro", "Focus", "🍅")
    object Calendar : Screen("calendar", "Calendar", "📅")
    object Notes : Screen("notes", "Notes", "📝")
    object Tasks : Screen("tasks", "Tasks", "⚡")
    object Settings : Screen("settings", "Settings", "⚙️")
}

@Composable
fun MainContainerScreen(targetScreen: String = "alarms") {
    val colors = LocalSanLivesColors.current

    var currentScreen by remember { mutableStateOf<Screen>(Screen.Alarms) }
    var viewingNoteId by remember { mutableStateOf<Long?>(null) }

    LaunchedEffect(targetScreen) {
        currentScreen = when (targetScreen.lowercase()) {
            "pomodoro", "focus" -> Screen.Pomodoro
            "calendar" -> Screen.Calendar
            "notes" -> Screen.Notes
            "tasks" -> Screen.Tasks
            "settings" -> Screen.Settings
            else -> Screen.Alarms
        }
        viewingNoteId = null
    }

    val alarmsVm: AlarmsViewModel = viewModel()
    val calendarVm: CalendarViewModel = viewModel()
    val notesVm: NotesViewModel = viewModel()
    val tasksVm: TasksViewModel = viewModel()
    val settingsVm: SettingsViewModel = viewModel()

    val is12Hour by settingsVm.is12HourFormat.collectAsState()

    val navItems = listOf(
        Screen.Alarms,
        Screen.Pomodoro,
        Screen.Calendar,
        Screen.Notes,
        Screen.Tasks,
        Screen.Settings
    )

    var isBedsideMode by remember { mutableStateOf(false) }

    if (isBedsideMode) {
        val alarms by alarmsVm.alarms.collectAsState()
        val nextActiveAlarm = remember(alarms) {
            alarms.filter { it.isEnabled }.minByOrNull { it.hour * 60 + it.minute }
        }
        com.sanlives.app.ui.screens.bedside.BedsideClockScreen(
            is12Hour = is12Hour,
            nextAlarm = nextActiveAlarm,
            onExit = { isBedsideMode = false }
        )
    } else {
        Scaffold(
            containerColor = colors.background,
            bottomBar = {
                if (viewingNoteId == null) {
                    Surface(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(horizontal = 10.dp, vertical = 6.dp),
                        shape = RoundedCornerShape(22.dp),
                        color = colors.cardBackground,
                        border = BorderStroke(1.dp, colors.cardBorder),
                        shadowElevation = 8.dp
                    ) {
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(vertical = 2.dp),
                            horizontalArrangement = Arrangement.SpaceAround,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            navItems.forEach { item ->
                                val isSelected = currentScreen == item
                                Column(
                                    modifier = Modifier
                                        .defaultMinSize(minWidth = 48.dp, minHeight = 48.dp)
                                        .clip(RoundedCornerShape(14.dp))
                                        .clickable { currentScreen = item }
                                        .padding(horizontal = 6.dp, vertical = 4.dp),
                                    horizontalAlignment = Alignment.CenterHorizontally,
                                    verticalArrangement = Arrangement.Center
                                ) {
                                    Text(
                                        text = item.icon,
                                        fontSize = if (isSelected) 17.sp else 15.sp
                                    )
                                    Text(
                                        text = item.title,
                                        fontSize = 9.5.sp,
                                        fontWeight = if (isSelected) FontWeight.Bold else FontWeight.Normal,
                                        color = if (isSelected) colors.accentColor else colors.textSecondary
                                    )
                                }
                            }
                        }
                    }
                }
            }
        ) { padding ->
            Box(
                modifier = Modifier
                    .fillMaxSize()
                    .background(colors.background)
                    .padding(padding)
            ) {
                if (viewingNoteId != null) {
                    Box(modifier = Modifier.fillMaxSize().background(colors.background)) {
                        NoteDetailScreen(
                            noteId = viewingNoteId!!,
                            viewModel = notesVm,
                            onBack = { viewingNoteId = null }
                        )
                    }
                } else {
                    AnimatedContent(
                        targetState = currentScreen,
                        transitionSpec = {
                            fadeIn(animationSpec = androidx.compose.animation.core.tween(150)) togetherWith
                                    fadeOut(animationSpec = androidx.compose.animation.core.tween(100))
                        },
                        label = "ScreenTransition",
                        modifier = Modifier.fillMaxSize().background(colors.background)
                    ) { screen ->
                        Box(modifier = Modifier.fillMaxSize().background(colors.background)) {
                            when (screen) {
                                is Screen.Alarms -> AlarmsTimetableScreen(viewModel = alarmsVm, is12Hour = is12Hour)
                                is Screen.Pomodoro -> PomodoroScreen()
                                is Screen.Calendar -> CalendarScreen(viewModel = calendarVm)
                                is Screen.Notes -> NotesListScreen(viewModel = notesVm, onNoteClick = { viewingNoteId = it })
                                is Screen.Tasks -> TasksScreen(viewModel = tasksVm)
                                is Screen.Settings -> SettingsScreen(viewModel = settingsVm, onLaunchBedsideMode = { isBedsideMode = true })
                            }
                        }
                    }
                }
            }
        }
    }
}
