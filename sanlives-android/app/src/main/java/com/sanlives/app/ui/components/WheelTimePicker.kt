package com.sanlives.app.ui.components

import androidx.compose.animation.core.Animatable
import androidx.compose.foundation.ExperimentalFoundationApi
import androidx.compose.foundation.background
import androidx.compose.foundation.gestures.snapping.rememberSnapFlingBehavior
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Text
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.sanlives.app.ui.theme.LocalSanLivesColors
import kotlinx.coroutines.flow.distinctUntilChanged

@OptIn(ExperimentalFoundationApi::class)
@Composable
fun WheelTimePicker(
    initialHour: Int,
    initialMinute: Int,
    is12Hour: Boolean,
    onTimeSelected: (hour: Int, minute: Int) -> Unit,
    modifier: Modifier = Modifier
) {
    val colors = LocalSanLivesColors.current

    val initialAmPm = if (initialHour >= 12) "PM" else "AM"
    val initialDisplayHour = if (is12Hour) {
        val h = initialHour % 12
        if (h == 0) 12 else h
    } else initialHour

    var selectedHour by remember { mutableStateOf(initialDisplayHour) }
    var selectedMinute by remember { mutableStateOf(initialMinute) }
    var selectedAmPm by remember { mutableStateOf(initialAmPm) }

    fun notifyChange() {
        val final24Hour = if (is12Hour) {
            when {
                selectedAmPm == "AM" && selectedHour == 12 -> 0
                selectedAmPm == "PM" && selectedHour < 12 -> selectedHour + 12
                else -> selectedHour
            }
        } else selectedHour
        onTimeSelected(final24Hour, selectedMinute)
    }

    val hours = if (is12Hour) (1..12).toList() else (0..23).toList()
    val minutes = (0..59).toList()
    val amPmList = listOf("AM", "PM")

    Box(
        modifier = modifier
            .fillMaxWidth()
            .height(160.dp)
            .clip(RoundedCornerShape(12.dp))
            .background(colors.inputBackground),
        contentAlignment = Alignment.Center
    ) {
        // Selection highlight bar in center
        Box(
            modifier = Modifier
                .fillMaxWidth(0.9f)
                .height(44.dp)
                .clip(RoundedCornerShape(8.dp))
                .background(colors.accentColor.copy(alpha = 0.15f))
        )

        Row(
            modifier = Modifier.fillMaxSize(),
            horizontalArrangement = Arrangement.Center,
            verticalAlignment = Alignment.CenterVertically
        ) {
            // Hours Column
            WheelColumn(
                items = hours.map { if (is12Hour) "$it" else "%02d".format(it) },
                initialItem = if (is12Hour) "$initialDisplayHour" else "%02d".format(initialDisplayHour),
                onItemSelected = {
                    selectedHour = it.toInt()
                    notifyChange()
                },
                modifier = Modifier.weight(1f)
            )

            Text(
                text = ":",
                fontSize = 22.sp,
                fontWeight = FontWeight.Bold,
                color = colors.textPrimary,
                modifier = Modifier.padding(horizontal = 4.dp)
            )

            // Minutes Column
            WheelColumn(
                items = minutes.map { "%02d".format(it) },
                initialItem = "%02d".format(initialMinute),
                onItemSelected = {
                    selectedMinute = it.toInt()
                    notifyChange()
                },
                modifier = Modifier.weight(1f)
            )

            // AM / PM Column if 12h
            if (is12Hour) {
                Spacer(modifier = Modifier.width(8.dp))
                WheelColumn(
                    items = amPmList,
                    initialItem = initialAmPm,
                    onItemSelected = {
                        selectedAmPm = it
                        notifyChange()
                    },
                    modifier = Modifier.weight(1f)
                )
            }
        }
    }
}

@OptIn(ExperimentalFoundationApi::class)
@Composable
private fun WheelColumn(
    items: List<String>,
    initialItem: String,
    onItemSelected: (String) -> Unit,
    modifier: Modifier = Modifier
) {
    val colors = LocalSanLivesColors.current
    val itemHeight = 44.dp
    val initialIndex = items.indexOf(initialItem).coerceAtLeast(0)
    val listState = rememberLazyListState(initialFirstVisibleItemIndex = initialIndex)
    val flingBehavior = rememberSnapFlingBehavior(lazyListState = listState)

    LaunchedEffect(listState) {
        snapshotFlow { listState.firstVisibleItemIndex }
            .distinctUntilChanged()
            .collect { idx ->
                if (idx in items.indices) {
                    onItemSelected(items[idx])
                }
            }
    }

    LazyColumn(
        state = listState,
        flingBehavior = flingBehavior,
        contentPadding = PaddingValues(vertical = itemHeight),
        modifier = modifier.height(160.dp),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        items(items.size) { index ->
            val isSelected = listState.firstVisibleItemIndex == index
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .height(itemHeight),
                contentAlignment = Alignment.Center
            ) {
                Text(
                    text = items[index],
                    fontSize = if (isSelected) 19.sp else 14.sp,
                    fontWeight = if (isSelected) FontWeight.Bold else FontWeight.Normal,
                    color = if (isSelected) colors.accentColor else colors.textSecondary.copy(alpha = 0.6f)
                )
            }
        }
    }
}
