# Dlives — Project Info Package
> **This file is the authoritative reference for building the Dlives marketing website.**
> The website session has no memory of app development history — everything needed is here.

---

## App Identity

| Field | Value |
|---|---|
| **App Name** | Dlives |
| **Version** | 1.0 |
| **Platform** | Windows 10 / 11 (standalone .exe) |
| **Installer filename** | `Dlives_Setup.exe` |
| **Installer size** | ~100 MB |
| **Publisher** | Fugentech |
| **Contact / Support email** | suhashoskere@gmail.com |
| **Android companion** | `Dlives.apk` — in development, not publicly released yet |
| **Install location** | `%LocalAppData%\Programs\Dlives\` (no admin/UAC required) |
| **User data location** | `%AppData%\Dlives\` (notes, alarms, calendar, clipboard history, settings) |

---

## Tagline Options

1. **"Your Windows desktop, alive."** *(recommended — clean, evocative)*
2. **"The dynamic island your Windows deserves."**
3. **"Everything you need. Always at the top."**
4. **"One floating bar. Infinite control."**
5. **"Live smarter. Right at the edge of your screen."**

---

## One-Paragraph Description (Hero / Meta Description)

Dlives is a dynamic floating island for Windows 10 and 11 — a sleek, always-on-top glass bar that lives at the edge of your screen and expands on hover to reveal a full productivity dashboard. Control your media, track alarms and timetables, manage notes and calendar events, monitor system health, browse clipboard history, and launch apps — all without ever leaving what you're doing. Built with a Liquid Glass aesthetic, it blends into any desktop setup and reacts to your system in real time.

---

## Long Description (2-3 paragraphs, for About/Docs pages)

Dlives brings a dynamic island interaction model to Windows desktops. The app lives as a compact, always-on-top pill at the edge of your screen — invisible when you don't need it, alive when you do. Hover over it and it smoothly expands into a full-featured productivity hub with tabs for every part of your workflow: alarms and timetable, calendar events, quick notes, media controls, clipboard history, system diagnostics, and a customizable app launcher. Everything snaps back when you move away, leaving your desktop clean and distraction-free.

The visual design is inspired by Apple's Dynamic Island and modern glassmorphism aesthetics: a dark OLED background, translucent glass panels, soft depth shadows, rounded corners, and accent color highlights that you fully control. You can set the accent to sky blue, emerald, rose, amber, violet, or any custom hex — and the entire interface re-skins instantly without a restart. The island's position, opacity, corner radius, blur level, and which tabs appear are all configurable from the built-in Settings and App Interface Configurator.

Dlives is fully standalone — no Python, no .NET, no Visual C++ runtime. The installer requires no admin rights and leaves no system footprint outside your user directories. User data lives in %AppData%\Dlives\ as human-readable JSON and plain text files, so you always own your data. An Android companion app that syncs alarms and notifications is currently in development.

---

## Full Feature List

### 1. Home Dashboard
The default expanded view. Shows a live summary of your day at a glance: upcoming alarms, today's timetable schedule, pinned quick notes, a Focus and Pomodoro timer, Now Playing media info, recent notifications, and a Quick Drop Zone for files. Cards are individually toggleable via Settings.

### 2. Control Center (Media + Volume + Brightness)
System media transport (Prev / Play-Pause / Next) that hooks into Windows SMTC, so it controls any app playing audio: Spotify, Chrome, VLC, YouTube Music, etc. Live track title and artist display. Master volume slider. Display brightness slider. All controls update in real time.

### 3. System Diagnostics (Sys)
Live hardware telemetry: CPU load %, RAM usage (used / total GB), active Wi-Fi network name and signal strength, system uptime, battery percentage and charging status, and storage usage. Includes a one-click Clear Temp Files button. Auto-refreshes every second.

### 4. Clipboard and File Shelf
Two-panel tab: Clipboard History captures everything you copy to the clipboard and lets you one-click re-copy any past entry. File Shelf Zone is a drag-and-drop holding area for files you want to quickly move between locations.

### 5. Calendar and Events
A full monthly calendar grid (glassmorphism-styled). Click any date to see its events. Add new events with a title directly from the island. Events persist in %AppData%\Dlives\calendar.json.

### 6. Alarms and Timetable
Alarms: Set alarms with a time picker, custom title, repeat days (M/T/W/Th/F/Sa/Su), and a chime sound. When an alarm fires, a modal Alarm Banner card slides in with dismiss/snooze options. Alarms persist in %AppData%\Dlives\alarms.json.
Timetable: A separate sub-tab for a recurring daily schedule checklist.

### 7. App Launcher
A customizable quick-launch grid of your favorite apps and executables. Ships with presets. Add any custom app via "+ Add Custom App" and it pins to the grid.

### 8. Notes
A multi-note scratchpad. Create named notes, write in a plain text editor, and content auto-saves on every keystroke. Pin up to 2 notes to the Home Dashboard card for quick glance. Notes are stored as plain .txt files in %AppData%\Dlives\notes\ — fully accessible from File Explorer.

### 9. Settings and Liquid Glass Customization
Full live customization engine: Theme Mode (Dark/Light), Accent Color (10 presets + custom hex), Position (6 screen positions), Glass Opacity slider, Corner Radius slider, Win32 Acrylic Blur toggle, Start with Windows toggle, auto-hide delay. All changes apply instantly without restarting.

### 10. Notifications (Notifs)
Captures recent Windows system notifications and displays them in a scrollable feed inside the island. Shows notifications from any app (WhatsApp, Mail, System alerts, etc.).

### 11. App Interface / Customization Studio (Full Window)
A separate full-screen resizable window (Customization Studio and Island Configurator) accessible via Settings. Contains: Island Modules and Tabs (reorder/toggle tabs), Theme and Glassmorphism, Island Position and Physics, Home Dashboard Cards config, Alarms and Notifications settings, App Launcher Shortcuts, System and Data Backups.

---

## System Requirements

| Requirement | Detail |
|---|---|
| **OS** | Windows 10 (build 1903+) or Windows 11 |
| **Architecture** | x64 only |
| **RAM** | 100 MB minimum |
| **Disk** | ~70 MB for the installer; ~75 MB installed |
| **Dependencies** | None — fully standalone installer, no Python/runtimes required |
| **Admin rights** | Not required — per-user installation |
| **Internet** | Not required — fully offline app |

---

## User Data Storage

All user data lives in %AppData%\Dlives\ (which resolves to C:\Users\<YourName>\AppData\Roaming\Dlives\).

| File / Folder | Contents |
|---|---|
| `settings.json` | All app preferences (position, theme, accent, opacity, etc.) |
| `alarms.json` | All configured alarms |
| `calendar.json` | All calendar events |
| `clipboard.json` | Clipboard history buffer |
| `fileshelf.json` | File shelf items |
| `timetable.json` | Timetable schedule blocks |
| `notes\` | One .txt file per note, named by note title |
| `notes_index.json` | Index of note metadata (order, pinned state) |

Notes / File Explorer integration: Each note you create in the Notes tab is saved as a real .txt file in %AppData%\Dlives\notes\<NoteTitle>.txt. You can open, edit, copy, or share these files directly from File Explorer — any external edits are picked up by the app. This makes notes fully portable and not locked into any proprietary format.

---

## First-Run Considerations for Documentation

### Windows SmartScreen Warning
Because the installer (Dlives_Setup_v1.0.exe) is not yet code-signed with a paid certificate, Windows may show a SmartScreen blue warning screen: "Windows protected your PC — Microsoft Defender SmartScreen prevented an unrecognized app from starting."

How to bypass:
1. Click "More info" on the SmartScreen screen.
2. Click "Run anyway" — the installer will launch normally.
3. This is a one-time step; once installed, the app runs without further warnings.

This is expected behavior for any unsigned installer and does not indicate the app is malicious.

### Notification Access
Dlives captures Windows notifications using the Windows notification API. On first launch, Windows may prompt for notification access permission. Grant this permission for the Notifications tab to populate. If you accidentally deny it:
1. Go to Windows Settings > System > Notifications.
2. Ensure notifications are enabled globally, then restart Dlives.

### Autorun on Startup
The "Start with Windows" toggle in Settings adds a registry key at HKCU\Software\Microsoft\Windows\CurrentVersion\Run\Dlives. No admin rights needed. Uninstalling the app automatically removes this key.

---

## Design Reference (for website visual language)

The website must visually match the app's aesthetic:

| Token | Value |
|---|---|
| **Background** | #0f0f14 (near-black OLED dark) |
| **Secondary BG** | #13131a or #1a1a2e |
| **Glass card surface** | rgba(255,255,255,0.04) with backdrop-filter: blur(20px) |
| **Card border** | rgba(255,255,255,0.08) |
| **Primary accent** | #38bdf8 (Sky Blue) |
| **Accent glow** | rgba(56,189,248,0.25) |
| **Text primary** | #f0f0f5 |
| **Text secondary** | #8888aa |
| **Danger/alert red** | #ef4444 |
| **Radius** | 20px for large cards, 12px for smaller elements |
| **Font** | Inter (Google Fonts) |
| **App logo** | assets/app-icon.png |

---

## Available Screenshots (in assets/screenshots/)

| Filename | What it shows |
|---|---|
| `home-tab.png` | Home Dashboard — alarms overview, timetable, notes pinned, Pomodoro timer, drop zone |
| `control-media.png` | Control Center — media transport (Now Playing IDLE), volume and brightness sliders |
| `system-diagnostics.png` | Sys tab — CPU 17%, RAM 81%, Network connected, diagnostics summary |
| `clipboard-shelf.png` | Shelf tab — Clipboard history with multiple entries, re-copy buttons |
| `calendar.png` | Calendar tab — August 2026 month grid, event panel |
| `alarms.png` | Alarms tab — Set New Alarm form with time picker, repeat days, sound picker |
| `app-launcher.png` | Apps tab — App launcher grid with File Explorer, PowerShell, Arcu, custom apps |
| `notes.png` | Notes tab — Multi-note sidebar, note editor with pin/copy/home actions |
| `settings.png` | Settings tab — Accent color swatches, dark/light mode, position, opacity/radius sliders |
| `notifications.png` | Notifs tab — Recent Windows notifications feed |
| `app-interface-configurator.png` | Full App Interface/Customization Studio window — Tab manager with all modules listed |

---

## Website Structure (to be built)

```
website/
├── index.html              # Landing page
├── docs/
│   ├── getting-started.html
│   ├── features.html
│   ├── faq.html
│   └── support.html
├── assets/
│   ├── app-icon.png
│   ├── screenshots/        # All .png files listed above
│   └── css/ js/ fonts/     # Site assets
├── PROJECT_INFO.md         # This file
└── README.md               # Deployment instructions
```

---

## Deployment Notes

- Download link: Connected directly to GitHub binary asset: `https://github.com/rootnode-rebels/Dlives/releases/download/v1.0.0/Dlives_Setup.exe`
- Zero binary footprint hosted on static web host.
