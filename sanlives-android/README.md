# Dlives for Android (Kotlin + Jetpack Compose)

A native Android companion application matching the visual design, custom components, and floating island assistant of the **Dlives** Windows desktop app.

---

## 🌟 Key Architecture & Features

### 1. 🗄️ Local Room Database & Storage (Offline First)
- **Entities (with lastModified sync timestamp)**:
  - AlarmEntity: Time, repeat days, snooze duration, custom sound URI, enabled state.
  - TimetableEntity: Time, task title, description, daily repeating, completion state.
  - NoteEntity: Title, content, pinned quick note flag (up to 2 pinned).
  - CalendarEventEntity: Date, time, title, description, color tag.
  - TaskEntity: Checklist to-do item, priority, completion state.

### 2. ⏰ System Exact Alarms & Full-Screen Alert UI
- Powered by AlarmManager.setExactAndAllowWhileIdle (RTC_WAKEUP) to fire reliably when the phone is sleeping or app is killed.
- SCHEDULE_EXACT_ALARM & USE_EXACT_ALARM permission handling with Android 12+ compatibility.
- BootReceiver re-schedules all enabled alarms on device boot or timezone updates.
- AlarmAlertActivity: Full-screen wake-lock alert UI matching desktop with audio ringtone playback, vibration, 1-tap snooze pills (5/10/15/30/60m), dismiss button, and auto-dismiss countdown progress bar.

### 3. 🫧 Floating "Island" Overlay Bubble (SYSTEM_ALERT_WINDOW)
- Foreground Service FloatingIslandService + WindowManager + ComposeView.
- **Collapsed State**: Draggable pill bubble showing live digital time, battery/status chip, and subtle ambient aura glow. Single-touch drag anywhere on screen.
- **Expanded State**: Tap to expand into a quick dashboard card showing next upcoming alarm, today's timetable tasks, and pinned quick notes.
- **Auto-Collapse**: Collapses after 6 seconds of inactivity or tapping outside.
- **Alarm Override**: Automatically expands overlay when an alarm fires.

### 4. 🎨 Desktop-Matched Visual Design System
- **Dark Theme Default**: OLED near-black (#0C0C0F).
- **Light Theme Toggle**: Clean light palette (#F8FAFC).
- **12 Dynamic Accent Presets**: Sky Blue, Teal, Gold, Coral, Purple, Emerald, Pink, Onyx, Slate, Silver, Orchid, Mint.
- **Custom Components**:
  - CardWithAccentBar: Rounded card with category left-edge colored bar.
  - IconChip: Rounded background chip behind icons.
  - WheelTimePicker: Vertical direct-snap wheel time picker (Hour, Minute, AM/PM).
  - SanLivesSlider: Thin track slider with accent color fill and circular thumb.
  - SanLivesPillButton: Tactile rounded pill buttons.
  - EmptyStateView: Centered friendly empty state with icon, title, and subtitle.

### 5. 📝 Notes Auto-Save & Debounce
- 3-second debounce auto-save interval during typing inactivity (no disk thrashing).
- Pin up to 2 quick notes for instant display on the Floating Island Assistant.

---

## 🚀 How to Open and Build in Android Studio
1. Open **Android Studio**.
2. Select **Open** and choose the sanlives-android/ folder.
3. Allow Gradle to sync dependencies.
4. Run on an Android Device or Emulator (API 26+ / Android 8.0+).
