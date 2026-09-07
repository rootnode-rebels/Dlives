package com.sanlives.app.ui.theme

import androidx.compose.material3.ColorScheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.compositionLocalOf
import androidx.compose.runtime.remember
import androidx.compose.ui.graphics.Color

data class SanLivesCustomColors(
    val isDark: Boolean,
    val background: Color,
    val cardBackground: Color,
    val cardBorder: Color,
    val textPrimary: Color,
    val textSecondary: Color,
    val inputBackground: Color,
    val inputBorder: Color,
    val accentColor: Color
)

val LocalSanLivesColors = compositionLocalOf {
    SanLivesCustomColors(
        isDark = true,
        background = DarkBg,
        cardBackground = DarkCard,
        cardBorder = DarkCardBorder,
        textPrimary = DarkTextPrimary,
        textSecondary = DarkTextSecondary,
        inputBackground = DarkInputBg,
        inputBorder = DarkInputBorder,
        accentColor = Color(0xFF38BDF8)
    )
}

@Composable
fun SanLivesTheme(
    themeMode: String = "dark",
    accentName: String = "sky_blue",
    content: @Composable () -> Unit
) {
    val isDark = themeMode != "light"
    val accent = remember(accentName, isDark) { getAccentColor(accentName, isDark) }

    val customColors = remember(isDark, accent) {
        if (isDark) {
            SanLivesCustomColors(
                isDark = true,
                background = DarkBg,
                cardBackground = DarkCard,
                cardBorder = DarkCardBorder,
                textPrimary = DarkTextPrimary,
                textSecondary = DarkTextSecondary,
                inputBackground = DarkInputBg,
                inputBorder = DarkInputBorder,
                accentColor = accent
            )
        } else {
            SanLivesCustomColors(
                isDark = false,
                background = LightBg,
                cardBackground = LightCard,
                cardBorder = LightCardBorder,
                textPrimary = LightTextPrimary,
                textSecondary = LightTextSecondary,
                inputBackground = LightInputBg,
                inputBorder = LightInputBorder,
                accentColor = accent
            )
        }
    }

    val materialColors: ColorScheme = remember(isDark, accent) {
        if (isDark) {
            darkColorScheme(
                primary = accent,
                background = DarkBg,
                surface = DarkCard,
                onPrimary = Color.White,
                onBackground = DarkTextPrimary,
                onSurface = DarkTextPrimary
            )
        } else {
            lightColorScheme(
                primary = accent,
                background = LightBg,
                surface = LightCard,
                onPrimary = Color.White,
                onBackground = LightTextPrimary,
                onSurface = LightTextPrimary
            )
        }
    }

    CompositionLocalProvider(LocalSanLivesColors provides customColors) {
        MaterialTheme(
            colorScheme = materialColors,
            typography = Typography,
            content = content
        )
    }
}
