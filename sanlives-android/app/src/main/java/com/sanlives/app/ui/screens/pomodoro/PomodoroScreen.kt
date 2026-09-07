package com.sanlives.app.ui.screens.pomodoro

import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.foundation.Canvas
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
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.sanlives.app.pomodoro.FocusSoundscapesManager
import com.sanlives.app.pomodoro.PomodoroManager
import com.sanlives.app.pomodoro.PomodoroMode
import com.sanlives.app.pomodoro.PomodoroState
import com.sanlives.app.pomodoro.Soundscape
import com.sanlives.app.ui.components.CardWithAccentBar
import com.sanlives.app.ui.components.IconChip
import com.sanlives.app.ui.components.SanLivesPillButton
import com.sanlives.app.ui.theme.LocalSanLivesColors

@Composable
fun PomodoroScreen() {
    val colors = LocalSanLivesColors.current
    val context = LocalContext.current

    val state by PomodoroManager.state.collectAsState()
    val mode by PomodoroManager.mode.collectAsState()
    val sessions by PomodoroManager.completedSessions.collectAsState()

    val currentSoundscape by FocusSoundscapesManager.currentSoundscape.collectAsState()
    val soundVolume by FocusSoundscapesManager.volume.collectAsState()

    Scaffold(containerColor = colors.background) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .padding(horizontal = 16.dp, vertical = 12.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            // Header
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically
            ) {
                IconChip(emoji = "🍅", accentColor = Color(0xFFEF4444), size = 32.dp)
                Spacer(modifier = Modifier.width(10.dp))
                Column(modifier = Modifier.weight(1f)) {
                    Text(
                        text = "Pomodoro & Focus Timer",
                        fontSize = 17.5.sp,
                        fontWeight = FontWeight.ExtraBold,
                        color = colors.textPrimary,
                        maxLines = 1
                    )
                    Text(
                        text = "Live countdown syncs with the Floating Island",
                        fontSize = 11.sp,
                        color = colors.textSecondary,
                        maxLines = 1
                    )
                }
            }

            Spacer(modifier = Modifier.height(14.dp))

            // Mode Selector Chips
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .clip(RoundedCornerShape(16.dp))
                    .background(colors.inputBackground)
                    .padding(4.dp),
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                PomodoroMode.values().forEach { m ->
                    val isSelected = mode == m
                    Box(
                        modifier = Modifier
                            .weight(1f)
                            .clip(RoundedCornerShape(12.dp))
                            .background(if (isSelected) colors.accentColor else Color.Transparent)
                            .clickable { PomodoroManager.setMode(m, context) }
                            .padding(vertical = 7.dp),
                        contentAlignment = Alignment.Center
                    ) {
                        Text(
                            text = m.displayName,
                            fontSize = 11.sp,
                            fontWeight = FontWeight.Bold,
                            color = if (isSelected) Color.White else colors.textSecondary
                        )
                    }
                }
            }

            Spacer(modifier = Modifier.height(20.dp))

            // Isolated Circular Countdown Progress Ring (Recomposes locally every second without triggering full screen)
            PomodoroCountdownRing(
                mode = mode,
                accentColor = colors.accentColor,
                trackColor = colors.inputBackground,
                textColor = colors.textPrimary
            )

            Spacer(modifier = Modifier.height(16.dp))

            // Sessions Completed Chips
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.Center
            ) {
                Text(
                    text = "Sessions: ",
                    fontSize = 11.sp,
                    color = colors.textSecondary
                )
                for (i in 1..4) {
                    val isDone = (sessions % 4) >= i
                    Text(
                        text = if (isDone) "🍅 " else "⚪ ",
                        fontSize = 13.sp
                    )
                }
                Text(
                    text = "($sessions total)",
                    fontSize = 10.5.sp,
                    fontWeight = FontWeight.Bold,
                    color = colors.accentColor
                )
            }

            Spacer(modifier = Modifier.height(16.dp))

            // Ambient Soundscapes Card
            Card(
                shape = RoundedCornerShape(16.dp),
                colors = CardDefaults.cardColors(containerColor = colors.cardBackground),
                border = androidx.compose.foundation.BorderStroke(0.5.dp, colors.cardBorder),
                modifier = Modifier.fillMaxWidth()
            ) {
                Column(modifier = Modifier.padding(12.dp)) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text(
                            text = "🎧 Ambient Focus Audio",
                            fontSize = 12.sp,
                            fontWeight = FontWeight.Bold,
                            color = colors.textPrimary
                        )
                        Text(
                            text = currentSoundscape.displayName,
                            fontSize = 10.sp,
                            fontWeight = FontWeight.SemiBold,
                            color = colors.accentColor
                        )
                    }

                    Spacer(modifier = Modifier.height(8.dp))

                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(6.dp)
                    ) {
                        Soundscape.values().forEach { sc ->
                            val isSel = currentSoundscape == sc
                            Box(
                                modifier = Modifier
                                    .weight(1f)
                                    .clip(RoundedCornerShape(10.dp))
                                    .background(if (isSel) colors.accentColor else colors.inputBackground)
                                    .clickable { FocusSoundscapesManager.setSoundscape(sc) }
                                    .padding(vertical = 6.dp),
                                contentAlignment = Alignment.Center
                            ) {
                                Text(
                                    text = "${sc.icon}",
                                    fontSize = 13.sp
                                )
                            }
                        }
                    }

                    if (currentSoundscape != Soundscape.NONE) {
                        Spacer(modifier = Modifier.height(6.dp))
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Text(text = "🔈", fontSize = 11.sp)
                            Spacer(modifier = Modifier.width(6.dp))
                            Slider(
                                value = soundVolume,
                                onValueChange = { FocusSoundscapesManager.setVolume(it) },
                                modifier = Modifier.weight(1f),
                                colors = SliderDefaults.colors(
                                    thumbColor = colors.accentColor,
                                    activeTrackColor = colors.accentColor
                                )
                            )
                            Spacer(modifier = Modifier.width(6.dp))
                            Text(text = "🔊", fontSize = 11.sp)
                        }
                    }
                }
            }

            Spacer(modifier = Modifier.height(16.dp))

            // Action Buttons (Start / Pause / Reset)
            Row(
                modifier = Modifier.fillMaxWidth(0.85f),
                horizontalArrangement = Arrangement.SpaceEvenly
            ) {
                if (state == PomodoroState.RUNNING) {
                    SanLivesPillButton(
                        text = "⏸ Pause",
                        onClick = { PomodoroManager.pause(context) },
                        isPrimary = true,
                        backgroundColor = Color(0xFFF59E0B),
                        modifier = Modifier.weight(1f)
                    )
                } else {
                    SanLivesPillButton(
                        text = if (state == PomodoroState.PAUSED) "▶ Resume" else "▶ Start Focus",
                        onClick = { PomodoroManager.start(context) },
                        isPrimary = true,
                        backgroundColor = colors.accentColor,
                        modifier = Modifier.weight(1f)
                    )
                }

                Spacer(modifier = Modifier.width(12.dp))

                SanLivesPillButton(
                    text = "↺ Reset",
                    onClick = { PomodoroManager.reset(context) },
                    isPrimary = false,
                    backgroundColor = colors.inputBackground,
                    contentColor = colors.textPrimary,
                    modifier = Modifier.weight(0.7f)
                )
            }
        }
    }
}

@Composable
fun PomodoroCountdownRing(
    mode: PomodoroMode,
    accentColor: Color,
    trackColor: Color,
    textColor: Color,
    modifier: Modifier = Modifier
) {
    val remainingSec by PomodoroManager.remainingSeconds.collectAsState()
    val totalSec by PomodoroManager.totalSeconds.collectAsState()

    val minutes = remainingSec / 60
    val seconds = remainingSec % 60
    val timeFormatted = "%02d:%02d".format(minutes, seconds)

    val progress = if (totalSec > 0) remainingSec / totalSec.toFloat() else 0f
    val animatedProgress by animateFloatAsState(targetValue = progress, label = "PomoProgress")

    Box(
        modifier = modifier.size(210.dp),
        contentAlignment = Alignment.Center
    ) {
        Canvas(modifier = Modifier.fillMaxSize()) {
            drawCircle(
                color = trackColor,
                style = Stroke(width = 12.dp.toPx())
            )
            drawArc(
                color = accentColor,
                startAngle = -90f,
                sweepAngle = 360f * animatedProgress,
                useCenter = false,
                style = Stroke(width = 12.dp.toPx(), cap = StrokeCap.Round)
            )
        }

        Column(horizontalAlignment = Alignment.CenterHorizontally) {
            Text(
                text = timeFormatted,
                fontSize = 38.sp,
                fontWeight = FontWeight.ExtraBold,
                color = textColor
            )
            Spacer(modifier = Modifier.height(2.dp))
            Text(
                text = mode.displayName.uppercase(),
                fontSize = 10.5.sp,
                fontWeight = FontWeight.Bold,
                color = accentColor,
                letterSpacing = 1.sp
            )
        }
    }
}
