package com.sanlives.app.ui.components

import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.material3.Slider
import androidx.compose.material3.SliderDefaults
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import com.sanlives.app.ui.theme.LocalSanLivesColors

@Composable
fun SanLivesSlider(
    value: Float,
    onValueChange: (Float) -> Unit,
    valueRange: ClosedFloatingPointRange<Float>,
    modifier: Modifier = Modifier,
    steps: Int = 0
) {
    val colors = LocalSanLivesColors.current

    Slider(
        value = value,
        onValueChange = onValueChange,
        valueRange = valueRange,
        steps = steps,
        modifier = modifier.fillMaxWidth(),
        colors = SliderDefaults.colors(
            thumbColor = colors.accentColor,
            activeTrackColor = colors.accentColor,
            inactiveTrackColor = colors.inputBackground
        )
    )
}
