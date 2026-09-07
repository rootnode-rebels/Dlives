package com.sanlives.app.ui.screens.tasks

import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.hapticfeedback.HapticFeedbackType
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalHapticFeedback
import androidx.compose.ui.platform.LocalSoftwareKeyboardController
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.style.TextDecoration
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.sanlives.app.data.db.entity.TaskEntity
import com.sanlives.app.data.streak.StreakManager
import com.sanlives.app.ui.components.CardWithAccentBar
import com.sanlives.app.ui.components.ConfettiCelebrationView
import com.sanlives.app.ui.components.EmptyStateView
import com.sanlives.app.ui.components.IconChip
import com.sanlives.app.ui.components.SanLivesPillButton
import com.sanlives.app.ui.theme.CategoryTasksColor
import com.sanlives.app.ui.theme.LocalSanLivesColors
import com.sanlives.app.ui.viewmodel.TasksViewModel

@Composable
fun TasksScreen(viewModel: TasksViewModel) {
    val colors = LocalSanLivesColors.current
    val context = LocalContext.current
    val haptic = LocalHapticFeedback.current
    val tasks by viewModel.tasks.collectAsState()

    val streakManager = remember { StreakManager(context) }
    val currentStreak by streakManager.currentStreak.collectAsState()
    val bestStreak by streakManager.bestStreak.collectAsState()

    var showConfetti by remember { mutableStateOf(false) }

    val totalTasks = tasks.size
    val completedTasks = remember(tasks) { tasks.count { it.isCompleted } }
    val progress = if (totalTasks > 0) completedTasks.toFloat() / totalTasks else 0f
    val animatedProgress by animateFloatAsState(targetValue = progress, label = "TaskProgress")

    // Check if 100% completed to trigger streak update and confetti burst
    LaunchedEffect(completedTasks, totalTasks) {
        if (totalTasks > 0 && completedTasks == totalTasks) {
            val wasNewDay = streakManager.recordDayCompleted()
            if (wasNewDay) {
                showConfetti = true
            }
        }
    }

    Box(modifier = Modifier.fillMaxSize()) {
        Scaffold(containerColor = colors.background) { padding ->
            Column(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(padding)
                    .padding(horizontal = 16.dp, vertical = 12.dp)
            ) {
                // Header
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.SpaceBetween
                ) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        IconChip(emoji = "⚡", accentColor = CategoryTasksColor, size = 32.dp)
                        Spacer(modifier = Modifier.width(10.dp))
                        Column {
                            Text(
                                text = "To-Do Checklist",
                                fontSize = 18.sp,
                                fontWeight = FontWeight.ExtraBold,
                                color = colors.textPrimary
                            )
                            Text(
                                text = "Manage your actionable items and track daily momentum",
                                fontSize = 11.sp,
                                color = colors.textSecondary
                            )
                        }
                    }

                    // Habit Streak Flame Badge
                    Box(
                        modifier = Modifier
                            .clip(RoundedCornerShape(12.dp))
                            .background(Color(0xFFFF9500).copy(alpha = 0.15f))
                            .padding(horizontal = 10.dp, vertical = 6.dp)
                    ) {
                        Text(
                            text = "🔥 ${currentStreak}d (best: ${bestStreak}d)",
                            fontSize = 11.5.sp,
                            fontWeight = FontWeight.Bold,
                            color = Color(0xFFFF9500)
                        )
                    }
                }

                Spacer(modifier = Modifier.height(14.dp))

                // Daily Progress Momentum Card
                if (totalTasks > 0) {
                    Card(
                        modifier = Modifier.fillMaxWidth(),
                        shape = RoundedCornerShape(16.dp),
                        colors = CardDefaults.cardColors(containerColor = colors.cardBackground),
                        border = androidx.compose.foundation.BorderStroke(1.dp, colors.cardBorder)
                    ) {
                        Column(modifier = Modifier.padding(14.dp)) {
                            Row(
                                modifier = Modifier.fillMaxWidth(),
                                horizontalArrangement = Arrangement.SpaceBetween,
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                Text(
                                    text = "Daily Momentum",
                                    fontSize = 13.sp,
                                    fontWeight = FontWeight.Bold,
                                    color = colors.textPrimary
                                )
                                Text(
                                    text = "${completedTasks} / ${totalTasks} completed (${(progress * 100).toInt()}%)",
                                    fontSize = 11.sp,
                                    fontWeight = FontWeight.SemiBold,
                                    color = if (progress == 1f) Color(0xFF10B981) else colors.accentColor
                                )
                            }

                            Spacer(modifier = Modifier.height(8.dp))

                            LinearProgressIndicator(
                                progress = { animatedProgress },
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .height(8.dp)
                                    .clip(RoundedCornerShape(4.dp)),
                                color = if (progress == 1f) Color(0xFF10B981) else colors.accentColor,
                                trackColor = colors.inputBackground
                            )

                            if (progress == 1f) {
                                Spacer(modifier = Modifier.height(6.dp))
                                Text(
                                    text = "🎉 All tasks done! Daily streak extended.",
                                    fontSize = 10.5.sp,
                                    fontWeight = FontWeight.Bold,
                                    color = Color(0xFF10B981)
                                )
                            }
                        }
                    }

                    Spacer(modifier = Modifier.height(14.dp))
                }

                // Add Task Bar (Isolated to avoid full screen recomposition on typing)
                AddTaskInputBar(
                    onAddTask = { title ->
                        haptic.performHapticFeedback(HapticFeedbackType.LongPress)
                        viewModel.addTask(title)
                    }
                )

                Spacer(modifier = Modifier.height(16.dp))

                // Tasks List
                if (tasks.isEmpty()) {
                    EmptyStateView(
                        icon = "⚡",
                        title = "No Tasks Added",
                        subtitle = "Type a task above and tap the + button to stay organized."
                    )
                } else {
                    LazyColumn(
                        verticalArrangement = Arrangement.spacedBy(8.dp),
                        modifier = Modifier.fillMaxSize()
                    ) {
                        items(tasks, key = { it.id }) { task ->
                            TaskCard(
                                task = task,
                                onToggle = {
                                    haptic.performHapticFeedback(HapticFeedbackType.TextHandleMove)
                                    viewModel.toggleTask(task)
                                },
                                onDelete = {
                                    haptic.performHapticFeedback(HapticFeedbackType.LongPress)
                                    viewModel.deleteTask(task)
                                }
                            )
                        }
                    }
                }
            }
        }

        // Confetti Celebration Overlay
        ConfettiCelebrationView(trigger = showConfetti) {
            showConfetti = false
        }
    }
}

@Composable
fun AddTaskInputBar(onAddTask: (String) -> Unit) {
    val colors = LocalSanLivesColors.current
    var text by remember { mutableStateOf("") }
    val kb = LocalSoftwareKeyboardController.current

    Row(
        modifier = Modifier.fillMaxWidth(),
        verticalAlignment = Alignment.CenterVertically
    ) {
        OutlinedTextField(
            value = text,
            onValueChange = { text = it },
            placeholder = { Text("Add a new task...", fontSize = 12.sp, color = colors.textSecondary) },
            singleLine = true,
            modifier = Modifier
                .weight(1f)
                .height(48.dp),
            shape = RoundedCornerShape(12.dp),
            keyboardOptions = KeyboardOptions(imeAction = ImeAction.Done),
            keyboardActions = KeyboardActions(onDone = {
                if (text.isNotBlank()) {
                    onAddTask(text.trim())
                    text = ""
                    kb?.hide()
                }
            }),
            colors = OutlinedTextFieldDefaults.colors(
                focusedContainerColor = colors.inputBackground,
                unfocusedContainerColor = colors.inputBackground,
                focusedBorderColor = colors.accentColor,
                unfocusedBorderColor = colors.inputBorder,
                focusedTextColor = colors.textPrimary,
                unfocusedTextColor = colors.textPrimary
            )
        )

        Spacer(modifier = Modifier.width(8.dp))

        IconButton(
            onClick = {
                if (text.isNotBlank()) {
                    onAddTask(text.trim())
                    text = ""
                    kb?.hide()
                }
            },
            modifier = Modifier
                .size(48.dp)
                .clip(CircleShape)
                .background(CategoryTasksColor)
        ) {
            Icon(Icons.Default.Add, contentDescription = "Add Task", tint = Color.White)
        }
    }
}

@Composable
fun TaskCard(
    task: TaskEntity,
    onToggle: () -> Unit,
    onDelete: () -> Unit
) {
    val colors = LocalSanLivesColors.current

    CardWithAccentBar(
        categoryColor = if (task.isCompleted) Color(0xFF10B981) else CategoryTasksColor,
        onClick = onToggle
    ) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Row(
                modifier = Modifier.weight(1f),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Checkbox(
                    checked = task.isCompleted,
                    onCheckedChange = { onToggle() },
                    colors = CheckboxDefaults.colors(
                        checkedColor = Color(0xFF10B981),
                        uncheckedColor = colors.textSecondary
                    )
                )
                Spacer(modifier = Modifier.width(8.dp))
                Column {
                    Text(
                        text = task.title,
                        fontSize = 13.5.sp,
                        fontWeight = if (task.isCompleted) FontWeight.Normal else FontWeight.SemiBold,
                        color = if (task.isCompleted) colors.textSecondary else colors.textPrimary,
                        textDecoration = if (task.isCompleted) TextDecoration.LineThrough else TextDecoration.None
                    )
                    if (task.categoryTag.isNotBlank() && task.categoryTag != "General") {
                        Text(
                            text = task.categoryTag,
                            fontSize = 10.sp,
                            color = colors.textSecondary.copy(alpha = 0.7f)
                        )
                    }
                }
            }

            IconButton(onClick = onDelete) {
                Icon(
                    Icons.Default.Delete,
                    contentDescription = "Delete",
                    tint = colors.textSecondary.copy(alpha = 0.5f),
                    modifier = Modifier.size(18.dp)
                )
            }
        }
    }
}
