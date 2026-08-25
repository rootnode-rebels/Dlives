# Dynamic Island Pro — Technical Architecture & Complete Application Manual

**Dynamic Island Pro** is a production-grade, native Windows 10/11 desktop widget built with Python 3.14, PyQt6, and Win32 C-API interop. It brings an interactive, hardware-accelerated dark OLED glass dynamic island to Windows with live system telemetry, control sliders, media transport, scheduled alarms with audio chimes, calendar storage, task management, quick notes, live UI customization, and system tray integration.

---

## 1. Project Directory Sitemap

```
d:\projects\dreminds\
├── main.py                   # Root application entrypoint, window manager & event loops
├── system_monitor.py          # Win32 C-API interop, system telemetry & media triggers
├── settings_manager.py        # settings.json manager & Windows registry autorun sync
├── storage_manager.py         # tasks.json, notes.txt, calendar.json & alarms.json persistence
├── ui_components.py           # Mini-taskbar pill header & 8 interactive dashboard tabs
├── requirements.txt           # Python dependency manifest
├── dist/
│   └── DynamicIsland.exe      # Compiled 40.0 MB zero-dependency standalone executable
├── settings.json              # Saved user preferences & theme settings
├── tasks.json                 # Persistent task checklist
├── notes.txt                  # Auto-saved scratchpad text
├── calendar.json              # Date-bound calendar events
└── alarms.json                # Scheduled alarms configuration
```

---

## 2. Technical Stack & Libraries

- **GUI Framework**: `PyQt6` (`PyQt6.QtWidgets`, `PyQt6.QtCore`, `PyQt6.QtGui`)
- **Language**: Python 3.14+ (Win64)
- **Win32 C-API Interop**:
  - `ctypes.windll.user32.GetKeyState` for Caps Lock (`VK_CAPITAL = 0x14`) & Num Lock (`VK_NUMLOCK = 0x90`).
  - `ctypes.windll.user32.SetWindowCompositionAttribute` for native Windows 10/11 Acrylic Blur (`ACCENT_ENABLE_ACRYLICBLURBEHIND`).
  - `ctypes.windll.user32.keybd_event` for system media key triggers (`VK_MEDIA_NEXT_TRACK`, `VK_MEDIA_PREV_TRACK`, `VK_MEDIA_PLAY_PAUSE`).
  - `winsound.MessageBeep` / `winsound.Beep` for native Windows alarm chime audio.
  - `winreg` for Windows startup autorun (`HKCU\Software\Microsoft\Windows\CurrentVersion\Run\DynamicIsland`).
- **Telemetry Libraries**:
  - `psutil`: Battery percentage & AC charging status, CPU %, RAM %, Disk space (GB), System Uptime.
  - `pycaw`: Windows Core Audio Master Volume query & scalar setter.
  - `screen_brightness_control`: Active display brightness query & setter.
- **Packaging**: `PyInstaller` standalone single-file binary compilation.

---

## 3. Core Architecture & Modules Breakdown

### A. `main.py`
- **Root Window Translucency**:
  Configures top-level window flags and attributes:
  ```python
  self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
  self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
  self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
  self.setStyleSheet("background: transparent;")
  ```
  This ensures zero black box rectangle artifacts appear behind the rounded glass corners or shadow padding.
- **Smart Conditional Visibility & Auto-Hide Logic**:
  Stays hidden (`hide()`) by default. Auto-reveals (`show()`) if Caps/Num Lock is ON, AC Power is charging, or mouse hovers top-center edge.
- **Anti-Collapse Interaction Lock**:
  Uses `QApplication.focusWidget()` and input state checks so the island **never auto-collapses or hides** while the user is actively typing in text fields or adjusting controls.
- **Smooth Expansion Animation**:
  Uses `QPropertyAnimation` with an `OutCubic` curve targeting window `frameSize` property (expanding 380px×36px pill to 540px×340px card).
- **1-Second Monitoring & Alarm Loop**:
  Checks system telemetry, updates live clock, checks active alarms against current time `HH:mm`, and triggers `winsound` chime audio + visual alarm banner when an alarm fires.
- **System Tray Integration (`QSystemTrayIcon`)**:
  System tray icon with context menu (Toggle Island, Settings, Exit).

### B. `system_monitor.py`
- `apply_win32_acrylic(hwnd, hex_color, opacity)`: Passes `ACCENT_POLICY` struct to `SetWindowCompositionAttribute` in `user32.dll`.
- `is_caps_lock_on()` & `is_num_lock_on()`: Bitwise query on `GetKeyState`.
- `get_battery_info()`, `get_cpu_usage()`, `get_ram_usage()`, `get_disk_info()`, `get_uptime_string()`.
- `get_master_volume()` & `set_master_volume(level)` via `pycaw`.
- `get_brightness()` & `set_brightness(level)` via `screen_brightness_control`.
- `trigger_media_prev()`, `trigger_media_play_pause()`, `trigger_media_next()`.

### C. `settings_manager.py`
- Manages persistent preferences in `settings.json`:
  ```json
  {
    "position": "top_center",
    "offset_y": 12,
    "offset_x": 0,
    "bg_color": "#0c0c0f",
    "bg_opacity": 0.92,
    "accent_color": "#38bdf8",
    "border_color": "#27272a",
    "enable_acrylic_blur": true,
    "enable_caps_num_trigger": true,
    "enable_charging_trigger": true,
    "start_with_windows": false
  }
  ```
- Emits `settings_changed` signal for **Live Customization Engine** (theme and position updates occur instantly in real time without restarting).
- Automatically creates or deletes registry keys in `HKCU\Software\Microsoft\Windows\CurrentVersion\Run\DynamicIsland` when `start_with_windows` is toggled.

### D. `storage_manager.py`
- Centralized read/write storage manager for `tasks.json`, `notes.txt`, `calendar.json`, and `alarms.json`.

### E. `ui_components.py`
Contains the mini-taskbar pill header and 8 interactive dashboard tabs:

1. **`CollapsedPillWidget` (Mini-Taskbar Header)**:
   - Live Digital Clock (`HH:MM:SS AM/PM`) & Date (`Tue, Aug 11`) updated every second.
   - Lock Badges (`CAPS`, `NUM`) with pulsing glow animations (`QGraphicsDropShadowEffect`) when toggled.
   - Telemetry Badges: Battery % (with `⚡`/`🔋` charging icon), CPU %, RAM %.
   - Quick Action Mute Toggle Button (`🔊`/`🔇`).
2. **`ControlCenterTabWidget` (`🎛️ Control`)**:
   - Master Volume Slider (`pycaw`) & Brightness Slider (`screen_brightness_control`).
   - Media Transport Bar (`⏮️`, `⏯️`, `⏭️`).
   - CPU & RAM progress meters.
3. **`HardwareDiagnosticsTabWidget` (`📊 Hardware`)**:
   - Detailed hardware diagnostics: Disk Space (Used/Total GB & progress bar), System Uptime, Battery Health.
4. **`CalendarTabWidget` (`📅 Calendar`)**:
   - Dark glassmorphism `QCalendarWidget` with date picker, event list, and event creation (`calendar.json`).
5. **`AlarmsTabWidget` (`⏰ Alarms`)**:
   - `QTimeEdit` picker, alarm title input, active alarm checklist with enable/disable toggles & delete buttons (`alarms.json`).
6. **`TasksTabWidget` (`📋 Tasks`)**:
   - Task input bar, interactive checkable list with strike-through styling, delete buttons (`tasks.json`).
7. **`AppLauncherTabWidget` (`🚀 Apps`)**:
   - Grid app launcher for Web Browser, File Explorer, Terminal/CMD, and Notepad.
8. **`QuickNotesTabWidget` (`📝 Notes`)**:
   - Scratchpad text editor connected to `textChanged` signal for instant keystroke auto-saving (`notes.txt`).
9. **`SettingsTabWidget` (`⚙️ Settings`)**:
   - Live color pickers (Accent color, presets, background color, opacity slider), positioning dropdown (Top Center, Top Left, Top Right), Y/X offset spinboxes, Win32 Acrylic blur toggle, and Windows startup autorun toggle.

---

## 4. User Configuration & Controls Quick Reference

- **Show / Expand**: Move mouse cursor to top-center edge of monitor or press `Caps Lock` / `Num Lock`.
- **Toggle Visibility**: Right-click system tray icon -> Select **Toggle Dynamic Island** or click tray icon.
- **Open Settings Directly**: Right-click tray icon -> Select **Open Settings**.
- **Quick Mute**: Click `🔊` button on the mini-taskbar header.
- **Start on Boot**: Go to `⚙️ Settings` tab -> Check **Start with Windows** -> Click **Apply & Save Settings**.

---

## 5. How to Run & Build

### Running Source Code Locally:
```bash
python main.py
```

### Compiling Standalone `.exe` Executable:
```bash
python -m PyInstaller --noconsole --onefile --name "DynamicIsland" main.py
```
Output binary will be located at:
`d:\projects\dreminds\dist\DynamicIsland.exe`
