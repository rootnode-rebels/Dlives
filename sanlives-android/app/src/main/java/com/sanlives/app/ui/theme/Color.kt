package com.sanlives.app.ui.theme

import androidx.compose.ui.graphics.Color

// Base Palettes
val DarkBg = Color(0xFF0C0C0F)
val DarkCard = Color(0xFF15171E)
val DarkCardBorder = Color(0xFF232733)
val DarkTextPrimary = Color(0xFFF8FAFC)
val DarkTextSecondary = Color(0xFF94A3B8)
val DarkInputBg = Color(0xFF1E222D)
val DarkInputBorder = Color(0xFF2E3446)

val LightBg = Color(0xFFF8FAFC)
val LightCard = Color(0xFFFFFFFF)
val LightCardBorder = Color(0xFFE2E8F0)
val LightTextPrimary = Color(0xFF0F172A)
val LightTextSecondary = Color(0xFF64748B)
val LightInputBg = Color(0xFFF1F5F9)
val LightInputBorder = Color(0xFFCBD5E1)

// Category Accent Colors (Left-edge bar & chips)
val CategoryAlarmColor = Color(0xFFEF4444)
val CategoryCalendarColor = Color(0xFF8B5CF6)
val CategoryNotesColor = Color(0xFFF59E0B)
val CategoryTasksColor = Color(0xFF38BDF8)
val CategoryTimetableColor = Color(0xFF10B981)

data class AccentPreset(
    val id: String,
    val name: String,
    val darkColor: Color,
    val lightColor: Color
)

val ACCENT_PRESETS = listOf(
    AccentPreset("sky_blue", "Sky Blue", Color(0xFF38BDF8), Color(0xFF0284C7)),
    AccentPreset("teal", "Teal", Color(0xFF14B8A6), Color(0xFF0D9488)),
    AccentPreset("gold", "Gold", Color(0xFFEAB308), Color(0xFFCA8A04)),
    AccentPreset("coral", "Coral", Color(0xFFF97316), Color(0xFFC2410C)),
    AccentPreset("purple", "Purple", Color(0xFF7C4DFF), Color(0xFF6D28D9)),
    AccentPreset("emerald", "Emerald", Color(0xFF00E676), Color(0xFF15803D)),
    AccentPreset("hot_pink", "Hot Pink", Color(0xFFFF4081), Color(0xFFDB2777)),
    AccentPreset("dark_onyx", "Onyx", Color(0xFF38383E), Color(0xFF18181B)),
    AccentPreset("slate", "Slate", Color(0xFF64748B), Color(0xFF475569)),
    AccentPreset("silver", "Silver", Color(0xFFE5E7EB), Color(0xFF6B7280)),
    AccentPreset("orchid", "Orchid", Color(0xFFA855F7), Color(0xFF7E22CE)),
    AccentPreset("mint", "Mint", Color(0xFF22C55E), Color(0xFF16A34A))
)

fun getAccentColor(id: String, isDark: Boolean): Color {
    val preset = ACCENT_PRESETS.find { it.id == id } ?: ACCENT_PRESETS[0]
    return if (isDark) preset.darkColor else preset.lightColor
}
