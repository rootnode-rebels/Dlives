package com.sanlives.app.ui.screens.overlay

import androidx.compose.animation.*
import androidx.compose.animation.core.*
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.gestures.detectDragGestures
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Clear
import androidx.compose.material.icons.filled.Close
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.hapticfeedback.HapticFeedbackType
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalHapticFeedback
import androidx.compose.ui.platform.LocalSoftwareKeyboardController
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.sanlives.app.data.db.entity.AlarmEntity
import com.sanlives.app.data.db.entity.NoteEntity
import com.sanlives.app.data.db.entity.TimetableEntity
import com.sanlives.app.pomodoro.FocusSoundscapesManager
import com.sanlives.app.pomodoro.PomodoroManager
import com.sanlives.app.pomodoro.PomodoroMode
import com.sanlives.app.pomodoro.PomodoroState
import com.sanlives.app.pomodoro.Soundscape
import com.sanlives.app.ui.theme.SanLivesTheme
import kotlinx.coroutines.delay
import java.text.SimpleDateFormat
import java.util.*

@Composable
fun LiveClockText(
    is12Hour: Boolean,
    modifier: Modifier = Modifier,
    color: Color = Color.White,
    fontSize: androidx.compose.ui.unit.TextUnit = 12.5.sp
) {
    var timeStr by remember { mutableStateOf("") }
    LaunchedEffect(is12Hour) {
        val pattern = if (is12Hour) "hh:mm" else "HH:mm"
        val sdf = SimpleDateFormat(pattern, Locale.getDefault())
        while (true) {
            val now = Calendar.getInstance()
            timeStr = sdf.format(now.time)
            val sec = now.get(Calendar.SECOND)
            val delayMs = ((60 - sec) * 1000L).coerceIn(1000L, 60000L)
            delay(delayMs)
        }
    }
    Text(
        text = timeStr.ifBlank { "--:--" },
        fontSize = fontSize,
        fontWeight = FontWeight.Bold,
        color = color,
        modifier = modifier
    )
}

@Composable
fun IslandPillPomoCountdownText() {
    val pomoSec by PomodoroManager.remainingSeconds.collectAsState()
    Text(
        text = "%02d:%02d".format(pomoSec / 60, pomoSec % 60),
        fontSize = 13.sp,
        fontWeight = FontWeight.Bold,
        color = Color(0xFFFF9500),
        letterSpacing = 0.5.sp
    )
}

@Composable
fun IslandExpandedPomoCountdownText(isRunning: Boolean) {
    val pomoSec by PomodoroManager.remainingSeconds.collectAsState()
    Text(
        text = "%02d:%02d".format(pomoSec / 60, pomoSec % 60),
        fontSize = 38.sp,
        fontWeight = FontWeight.ExtraBold,
        color = if (isRunning) Color(0xFFFF9500) else Color.White,
        letterSpacing = 1.sp
    )
}

@Composable
fun FloatingIslandOverlayView(
    isExpanded: Boolean,
    onToggleExpand: () -> Unit,
    nextAlarm: AlarmEntity?,
    timetableTasks: List<TimetableEntity>,
    pinnedNotes: List<NoteEntity>,
    themeMode: String,
    accentName: String,
    is12Hour: Boolean,
    onDrag: (Int, Int) -> Unit,
    onDragEnd: () -> Unit,
    onToggleTimetableTask: (TimetableEntity) -> Unit,
    onQuickSaveNote: (String) -> Unit,
    onOpenMainApp: (String) -> Unit
) {
    val context = LocalContext.current
    val haptic = LocalHapticFeedback.current

    SanLivesTheme(themeMode = themeMode, accentName = accentName) {
        var quickNoteText by remember { mutableStateOf("") }
        var selectedTab by remember { mutableIntStateOf(0) } // 0 = Focus, 1 = Routines, 2 = Notes
        var isParkedAsDot by remember { mutableStateOf(false) }

        val pomoState by PomodoroManager.state.collectAsState()
        val pomoMode by PomodoroManager.mode.collectAsState()
        val currentSoundscape by FocusSoundscapesManager.currentSoundscape.collectAsState()

        // Auto-collapse after 10s of inactivity when expanded (if user is not typing)
        LaunchedEffect(isExpanded) {
            if (isExpanded) {
                delay(10000)
                if (quickNoteText.isBlank() && pomoState != PomodoroState.RUNNING) {
                    onToggleExpand()
                }
            }
        }

        // Dynamic Apple Island Bouncy Fluid Spring Transition
        AnimatedContent(
            targetState = if (isParkedAsDot) "dot" else if (isExpanded) "expanded" else "pill",
            transitionSpec = {
                (fadeIn(animationSpec = tween(180, easing = LinearOutSlowInEasing)) +
                        scaleIn(
                            initialScale = 0.85f,
                            animationSpec = spring(
                                dampingRatio = Spring.DampingRatioLowBouncy,
                                stiffness = Spring.StiffnessMediumLow
                            )
                        ))
                    .togetherWith(
                        fadeOut(animationSpec = tween(120)) +
                                scaleOut(
                                    targetScale = 0.85f,
                                    animationSpec = spring(
                                        dampingRatio = Spring.DampingRatioNoBouncy,
                                        stiffness = Spring.StiffnessMedium
                                    )
                                )
                    )
            },
            label = "AppleIslandSpringMorph"
        ) { state ->
            when (state) {
                "dot" -> {
                    // 0. MINI-DOT BEZEL PARKING (14dp glowing dot)
                    Box(
                        modifier = Modifier
                            .size(26.dp)
                            .shadow(16.dp, CircleShape, spotColor = Color(0xFF38BDF8))
                            .clip(CircleShape)
                            .background(Color.Black)
                            .border(BorderStroke(1.dp, Color(0xFF2C2C2E)), CircleShape)
                            .clickable {
                                haptic.performHapticFeedback(HapticFeedbackType.LongPress)
                                isParkedAsDot = false
                            },
                        contentAlignment = Alignment.Center
                    ) {
                        Box(
                            modifier = Modifier
                                .size(10.dp)
                                .clip(CircleShape)
                                .background(if (pomoState == PomodoroState.RUNNING) Color(0xFFFF9500) else Color(0xFF38BDF8))
                        )
                    }
                }
                "pill" -> {
                    // 1. iPHONE DYNAMIC ISLAND COLLAPSED CAPSULE (With crisp shadow + contrast border)
                    Box(
                        modifier = Modifier
                            .wrapContentSize()
                            .shadow(16.dp, RoundedCornerShape(22.dp), spotColor = Color.Black.copy(alpha = 0.9f), ambientColor = Color.Black)
                            .clip(RoundedCornerShape(22.dp))
                            .background(Color(0xFF0D0E11))
                            .border(BorderStroke(1.dp, Color(0xFF3A3D4D).copy(alpha = 0.8f)), RoundedCornerShape(22.dp))
                            .pointerInput(Unit) {
                                detectTapGestures(
                                    onTap = {
                                        haptic.performHapticFeedback(HapticFeedbackType.LongPress)
                                        onToggleExpand()
                                    },
                                    onDoubleTap = {
                                        haptic.performHapticFeedback(HapticFeedbackType.TextHandleMove)
                                        isParkedAsDot = true
                                    }
                                )
                            }
                            .pointerInput(Unit) {
                                detectDragGestures(
                                    onDrag = { change, dragAmount ->
                                        change.consume()
                                        onDrag(dragAmount.x.toInt(), dragAmount.y.toInt())
                                    },
                                    onDragEnd = {
                                        onDragEnd()
                                    }
                                )
                            }
                            .padding(horizontal = 14.dp, vertical = 8.dp),
                        contentAlignment = Alignment.Center
                    ) {
                        Row(
                            verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.spacedBy(8.dp)
                        ) {
                            // LEADING WING (Left Side of Island)
                            if (pomoState == PomodoroState.RUNNING) {
                                Box(
                                    modifier = Modifier
                                        .size(20.dp)
                                        .clip(CircleShape)
                                        .background(Color(0xFFFF3B30).copy(alpha = 0.25f)),
                                    contentAlignment = Alignment.Center
                                ) {
                                    Text(text = "🍅", fontSize = 11.sp)
                                }
                            } else if (nextAlarm != null) {
                                Text(text = "⏰", fontSize = 12.5.sp)
                            } else {
                                Text(text = "⚡", fontSize = 12.5.sp)
                            }

                            // CENTER EQUALIZER (Soundwave canvas animation when active)
                            if (pomoState == PomodoroState.RUNNING) {
                                AppleSoundWaveVisualizer()
                            }

                            // TRAILING WING (Right Side of Island)
                            if (pomoState == PomodoroState.RUNNING) {
                                IslandPillPomoCountdownText()
                            } else if (nextAlarm != null) {
                                Text(
                                    text = "%02d:%02d".format(nextAlarm.hour, nextAlarm.minute),
                                    fontSize = 12.5.sp,
                                    fontWeight = FontWeight.Bold,
                                    color = Color(0xFF38BDF8)
                                )
                            } else {
                                LiveClockText(is12Hour = is12Hour)
                            }
                        }
                    }
                }
                "expanded" -> {
                    // 2. iPHONE DYNAMIC ISLAND EXPANDED CARD
                    Box(
                        modifier = Modifier
                            .width(360.dp)
                            .shadow(32.dp, RoundedCornerShape(32.dp), spotColor = Color.Black)
                            .clip(RoundedCornerShape(32.dp))
                            .background(Color(0xFF000000))
                            .border(BorderStroke(1.dp, Color(0xFF2C2C2E)), RoundedCornerShape(32.dp))
                            .pointerInput(Unit) {
                                detectDragGestures(
                                    onDrag = { change, dragAmount ->
                                        change.consume()
                                        onDrag(dragAmount.x.toInt(), dragAmount.y.toInt())
                                    },
                                    onDragEnd = {
                                        onDragEnd()
                                    }
                                )
                            }
                            .padding(18.dp)
                    ) {
                        Column {
                            // TOP HEADER ROW
                            Row(
                                modifier = Modifier.fillMaxWidth(),
                                horizontalArrangement = Arrangement.SpaceBetween,
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                Row(verticalAlignment = Alignment.CenterVertically) {
                                    Box(
                                        modifier = Modifier
                                            .size(24.dp)
                                            .clip(CircleShape)
                                            .background(Color(0xFF1C1C1E)),
                                        contentAlignment = Alignment.Center
                                    ) {
                                        Text(text = "", fontSize = 13.sp, color = Color.White)
                                    }
                                    Spacer(modifier = Modifier.width(8.dp))
                                    Text(
                                        text = "Dlives",
                                        fontSize = 13.sp,
                                        fontWeight = FontWeight.ExtraBold,
                                        color = Color.White
                                    )
                                }

                                Row(verticalAlignment = Alignment.CenterVertically) {
                                    // Mini Bezel Parking toggle
                                    Box(
                                        modifier = Modifier
                                            .size(24.dp)
                                            .clip(CircleShape)
                                            .background(Color(0xFF1C1C1E))
                                            .clickable {
                                                haptic.performHapticFeedback(HapticFeedbackType.TextHandleMove)
                                                isParkedAsDot = true
                                            },
                                        contentAlignment = Alignment.Center
                                    ) {
                                        Text(text = "•", fontSize = 16.sp, color = Color(0xFF38BDF8), fontWeight = FontWeight.Bold)
                                    }
                                    Spacer(modifier = Modifier.width(8.dp))
                                    LiveClockText(is12Hour = is12Hour, color = Color(0xFF8E8E93), fontSize = 12.sp)
                                    Spacer(modifier = Modifier.width(8.dp))
                                    Box(
                                        modifier = Modifier
                                            .size(24.dp)
                                            .clip(CircleShape)
                                            .background(Color(0xFF1C1C1E))
                                            .clickable {
                                                haptic.performHapticFeedback(HapticFeedbackType.LongPress)
                                                onToggleExpand()
                                            },
                                        contentAlignment = Alignment.Center
                                    ) {
                                        Icon(
                                            imageVector = Icons.Default.Close,
                                            contentDescription = "Collapse",
                                            tint = Color(0xFF8E8E93),
                                            modifier = Modifier.size(13.dp)
                                        )
                                    }
                                }
                            }

                            Spacer(modifier = Modifier.height(14.dp))

                            // APPLE FLUID SEGMENTED TABS
                            Row(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .height(34.dp)
                                    .clip(RoundedCornerShape(17.dp))
                                    .background(Color(0xFF1C1C1E))
                                    .padding(2.5.dp),
                                horizontalArrangement = Arrangement.SpaceBetween
                            ) {
                                listOf("🍅 Focus", "📅 Routines", "📝 Notes").forEachIndexed { index, tabName ->
                                    val isTabSelected = selectedTab == index
                                    Box(
                                        modifier = Modifier
                                            .weight(1f)
                                            .fillMaxHeight()
                                            .clip(RoundedCornerShape(15.dp))
                                            .background(if (isTabSelected) Color(0xFF2C2C2E) else Color.Transparent)
                                            .clickable {
                                                haptic.performHapticFeedback(HapticFeedbackType.TextHandleMove)
                                                selectedTab = index
                                            },
                                        contentAlignment = Alignment.Center
                                    ) {
                                        Text(
                                            text = tabName,
                                            fontSize = 11.sp,
                                            fontWeight = if (isTabSelected) FontWeight.Bold else FontWeight.Medium,
                                            color = if (isTabSelected) Color.White else Color(0xFF8E8E93)
                                        )
                                    }
                                }
                            }

                            Spacer(modifier = Modifier.height(14.dp))

                            // TAB CONTENT
                            when (selectedTab) {
                                0 -> {
                                    // FOCUS / POMODORO
                                    Column(
                                        modifier = Modifier.fillMaxWidth(),
                                        horizontalAlignment = Alignment.CenterHorizontally
                                    ) {
                                        IslandExpandedPomoCountdownText(isRunning = pomoState == PomodoroState.RUNNING)
                                        Text(
                                            text = pomoMode.displayName.uppercase(),
                                            fontSize = 10.sp,
                                            fontWeight = FontWeight.Bold,
                                            color = Color(0xFF8E8E93),
                                            letterSpacing = 1.5.sp
                                        )

                                        Spacer(modifier = Modifier.height(12.dp))

                                        Row(
                                            horizontalArrangement = Arrangement.spacedBy(10.dp),
                                            verticalAlignment = Alignment.CenterVertically
                                        ) {
                                            AppleIconButton(
                                                icon = if (pomoState == PomodoroState.RUNNING) "⏸" else "▶",
                                                bg = if (pomoState == PomodoroState.RUNNING) Color(0xFFFF9500) else Color(0xFF30D158),
                                                onClick = {
                                                    haptic.performHapticFeedback(HapticFeedbackType.LongPress)
                                                    if (pomoState == PomodoroState.RUNNING) {
                                                        PomodoroManager.pause(context)
                                                    } else {
                                                        PomodoroManager.start(context)
                                                    }
                                                }
                                            )
                                            AppleIconButton(
                                                icon = "↺",
                                                bg = Color(0xFF2C2C2E),
                                                onClick = {
                                                    haptic.performHapticFeedback(HapticFeedbackType.LongPress)
                                                    PomodoroManager.reset(context)
                                                }
                                            )
                                        }

                                        Spacer(modifier = Modifier.height(12.dp))

                                        // Ambient soundscape row
                                        Row(
                                            modifier = Modifier
                                                .fillMaxWidth()
                                                .horizontalScroll(rememberScrollState()),
                                            horizontalArrangement = Arrangement.spacedBy(6.dp)
                                        ) {
                                            Soundscape.values().filter { it != Soundscape.NONE }.forEach { sound ->
                                                val isPlaying = currentSoundscape == sound
                                                Box(
                                                    modifier = Modifier
                                                        .clip(RoundedCornerShape(10.dp))
                                                        .background(if (isPlaying) Color(0xFFFF9500).copy(alpha = 0.2f) else Color(0xFF1C1C1E))
                                                        .border(BorderStroke(0.8.dp, if (isPlaying) Color(0xFFFF9500) else Color(0xFF2C2C2E)), RoundedCornerShape(10.dp))
                                                        .clickable {
                                                            haptic.performHapticFeedback(HapticFeedbackType.TextHandleMove)
                                                            FocusSoundscapesManager.setSoundscape(if (isPlaying) Soundscape.NONE else sound)
                                                        }
                                                        .padding(horizontal = 8.dp, vertical = 5.dp)
                                                ) {
                                                    Text(
                                                        text = "${sound.icon} ${sound.displayName}",
                                                        fontSize = 10.sp,
                                                        fontWeight = if (isPlaying) FontWeight.Bold else FontWeight.Normal,
                                                        color = if (isPlaying) Color(0xFFFF9500) else Color.White
                                                    )
                                                }
                                            }
                                        }
                                    }
                                }
                                1 -> {
                                    // ROUTINES / TIMETABLE
                                    Column(
                                        modifier = Modifier
                                            .fillMaxWidth()
                                            .heightIn(max = 140.dp)
                                    ) {
                                        if (timetableTasks.isEmpty()) {
                                            Text(
                                                text = "No routines for today 🌴",
                                                fontSize = 12.sp,
                                                color = Color(0xFF8E8E93),
                                                modifier = Modifier.padding(vertical = 14.dp)
                                            )
                                        } else {
                                            timetableTasks.take(3).forEach { task ->
                                                Row(
                                                    modifier = Modifier
                                                        .fillMaxWidth()
                                                        .padding(vertical = 4.dp),
                                                    verticalAlignment = Alignment.CenterVertically
                                                ) {
                                                    Checkbox(
                                                        checked = task.isCompleted,
                                                        onCheckedChange = {
                                                            haptic.performHapticFeedback(HapticFeedbackType.TextHandleMove)
                                                            onToggleTimetableTask(task)
                                                        },
                                                        colors = CheckboxDefaults.colors(
                                                            checkedColor = Color(0xFF30D158),
                                                            uncheckedColor = Color(0xFF8E8E93)
                                                        )
                                                    )
                                                    Spacer(modifier = Modifier.width(6.dp))
                                                    Text(
                                                        text = task.title,
                                                        fontSize = 12.sp,
                                                        color = if (task.isCompleted) Color(0xFF8E8E93) else Color.White,
                                                        maxLines = 1,
                                                        overflow = TextOverflow.Ellipsis
                                                    )
                                                }
                                            }
                                        }
                                    }
                                }
                                2 -> {
                                    // QUICK NOTES & MEMOS
                                    Column(modifier = Modifier.fillMaxWidth()) {
                                        pinnedNotes.take(2).forEach { pNote ->
                                            Box(
                                                modifier = Modifier
                                                    .fillMaxWidth()
                                                    .clip(RoundedCornerShape(8.dp))
                                                    .background(Color(0xFF1C1C1E))
                                                    .padding(8.dp)
                                            ) {
                                                Text(
                                                    text = "📌 ${pNote.title}: ${pNote.content}",
                                                    fontSize = 11.5.sp,
                                                    color = Color.White,
                                                    maxLines = 1,
                                                    overflow = TextOverflow.Ellipsis
                                                )
                                            }
                                            Spacer(modifier = Modifier.height(6.dp))
                                        }

                                        val kb = LocalSoftwareKeyboardController.current
                                        Row(
                                            modifier = Modifier.fillMaxWidth(),
                                            verticalAlignment = Alignment.CenterVertically
                                        ) {
                                            TextField(
                                                value = quickNoteText,
                                                onValueChange = { quickNoteText = it },
                                                placeholder = { Text("Quick memo...", fontSize = 12.sp, color = Color(0xFF8E8E93)) },
                                                modifier = Modifier
                                                    .weight(1f)
                                                    .heightIn(min = 46.dp),
                                                textStyle = TextStyle(fontSize = 12.5.sp, color = Color.White),
                                                shape = RoundedCornerShape(12.dp),
                                                colors = TextFieldDefaults.colors(
                                                    focusedContainerColor = Color(0xFF1C1C1E),
                                                    unfocusedContainerColor = Color(0xFF1C1C1E),
                                                    focusedIndicatorColor = Color.Transparent,
                                                    unfocusedIndicatorColor = Color.Transparent
                                                ),
                                                keyboardOptions = KeyboardOptions(imeAction = ImeAction.Done),
                                                keyboardActions = KeyboardActions(onDone = {
                                                    if (quickNoteText.isNotBlank()) {
                                                        onQuickSaveNote(quickNoteText)
                                                        quickNoteText = ""
                                                        kb?.hide()
                                                    }
                                                })
                                            )
                                            Spacer(modifier = Modifier.width(6.dp))
                                            Button(
                                                onClick = {
                                                    if (quickNoteText.isNotBlank()) {
                                                        onQuickSaveNote(quickNoteText)
                                                        quickNoteText = ""
                                                        kb?.hide()
                                                    }
                                                },
                                                shape = RoundedCornerShape(12.dp),
                                                colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF38BDF8)),
                                                modifier = Modifier.height(44.dp),
                                                contentPadding = PaddingValues(horizontal = 12.dp)
                                            ) {
                                                Text("Add", fontSize = 11.5.sp, fontWeight = FontWeight.Bold, color = Color.White)
                                            }
                                        }
                                    }
                                }
                            }

                            Spacer(modifier = Modifier.height(14.dp))

                            // BOTTOM ACTION: OPEN FULL APP (with active screen route)
                            Box(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .clip(RoundedCornerShape(12.dp))
                                    .background(Color(0xFF1C1C1E))
                                    .border(BorderStroke(0.8.dp, Color(0xFF2C2C2E)), RoundedCornerShape(12.dp))
                                    .clickable {
                                        haptic.performHapticFeedback(HapticFeedbackType.LongPress)
                                        val route = when (selectedTab) {
                                            0 -> "pomodoro"
                                            1 -> "alarms"
                                            2 -> "notes"
                                            else -> "alarms"
                                        }
                                        onOpenMainApp(route)
                                    }
                                    .padding(vertical = 9.dp),
                                contentAlignment = Alignment.Center
                            ) {
                                Text(
                                    text = "Open in Dlives ↗",
                                    fontSize = 11.5.sp,
                                    fontWeight = FontWeight.Bold,
                                    color = Color(0xFF38BDF8)
                                )
                            }
                        }
                    }
                }
            }
        }
    }
}

@Composable
fun AppleIconButton(
    icon: String,
    bg: Color,
    onClick: () -> Unit
) {
    Box(
        modifier = Modifier
            .size(38.dp)
            .clip(CircleShape)
            .background(bg)
            .clickable { onClick() },
        contentAlignment = Alignment.Center
    ) {
        Text(text = icon, fontSize = 14.sp, color = Color.White, fontWeight = FontWeight.Bold)
    }
}

@Composable
fun AppleSoundWaveVisualizer() {
    val infiniteTransition = rememberInfiniteTransition(label = "AppleWave")
    val b1 by infiniteTransition.animateFloat(
        initialValue = 4f,
        targetValue = 13f,
        animationSpec = infiniteRepeatable(tween(350, easing = LinearEasing), RepeatMode.Reverse),
        label = "b1"
    )
    val b2 by infiniteTransition.animateFloat(
        initialValue = 13f,
        targetValue = 4f,
        animationSpec = infiniteRepeatable(tween(480, easing = LinearEasing), RepeatMode.Reverse),
        label = "b2"
    )
    val b3 by infiniteTransition.animateFloat(
        initialValue = 6f,
        targetValue = 15f,
        animationSpec = infiniteRepeatable(tween(320, easing = LinearEasing), RepeatMode.Reverse),
        label = "b3"
    )

    Canvas(modifier = Modifier.size(16.dp, 14.dp)) {
        val barW = 2.5.dp.toPx()
        val corner = CornerRadius(1.5.dp.toPx(), 1.5.dp.toPx())
        val midY = size.height / 2f
        val color = Color(0xFFFF9500)

        // Bar 1
        val h1 = b1.dp.toPx()
        drawRoundRect(color, Offset(0f, midY - h1 / 2f), Size(barW, h1), corner)
        // Bar 2
        val h2 = b2.dp.toPx()
        drawRoundRect(color, Offset(5.5.dp.toPx(), midY - h2 / 2f), Size(barW, h2), corner)
        // Bar 3
        val h3 = b3.dp.toPx()
        drawRoundRect(color, Offset(11.dp.toPx(), midY - h3 / 2f), Size(barW, h3), corner)
    }
}
