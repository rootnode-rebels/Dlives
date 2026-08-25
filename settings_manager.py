import json
import os
import sys
import tempfile
import winreg
from PyQt6.QtCore import QObject, pyqtSignal, QTimer

from storage_manager import get_app_data_dir, safe_atomic_write_json

def get_base_dir() -> str:
    """Backwards compatible alias returning centralized get_app_data_dir()."""
    return get_app_data_dir()

DEFAULT_SETTINGS = {
    "position": "top_center",
    "offset_y": 12,
    "offset_x": 0,
    "monitor_index": 0,
    "bg_color": "#0f0f14",
    "bg_opacity": 0.90,
    "accent_color": "#38bdf8",
    "border_color": "#27272a",
    "enable_acrylic_blur": False,
    "auto_hide_delay_ms": 2500,
    "hover_delay_ms": 400,
    "font_scale": "normal",
    "enable_caps_num_trigger": True,
    "enable_charging_trigger": True,
    "start_with_windows": False,
    "show_home_alarms": True,
    "show_home_calendar": True,
    "show_home_notes": True,
    "show_home_dropzone": True,
    "show_home_timetable": True,
    "time_format_12h": True,
    "corner_radius": 20,
    "alarm_autodismiss_seconds": 30,
    "theme_mode": "dark",
    "accent_identity": "sky_blue",
    "sync_windows_theme": False,
    "suppress_popups_in_fullscreen": True,
    "notification_popup_enabled": True,
    "popup_notification_apps": ["WhatsApp", "Slack", "Microsoft Teams", "Discord", "Telegram", "Mail", "Outlook", "Chrome", "Edge"],
    "notification_popup_autodismiss_seconds": 3,
    "enable_system_pill_toasts": True,
    "show_home_pomodoro": True,
    "pomodoro_focus_min": 25,
    "pomodoro_short_break_min": 5,
    "pomodoro_long_break_min": 15,
    "watermark_opacity": 0.04,
    "visible_tabs": ["home", "control", "hardware", "shelf_clip", "calendar", "alarms", "apps", "notes", "settings", "notifs"],
    "tab_order": ["home", "control", "hardware", "shelf_clip", "calendar", "alarms", "apps", "notes", "settings", "notifs"]
}

REG_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_NAME = "Dlives"

class SettingsManager(QObject):
    """Manages application preferences, JSON persistence, and Windows registry startup sync."""
    settings_changed = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        base_dir = get_base_dir()
        self.settings_file = os.path.join(base_dir, "settings.json")
        self.settings = self.load_settings()

        self.last_startup_reg_state = self.settings.get("start_with_windows", False)
        if self.last_startup_reg_state:
            self.sync_registry_startup()

        self.save_timer = QTimer(self)
        self.save_timer.setSingleShot(True)
        self.save_timer.setInterval(400)
        self.save_timer.timeout.connect(self.flush_save)

    def load_settings(self) -> dict:
        settings = DEFAULT_SETTINGS.copy()
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        settings.update(data)
            except Exception as e:
                print(f"Error loading settings.json (recovered defaults): {e}")
        else:
            try:
                safe_atomic_write_json(self.settings_file, settings)
            except Exception as e:
                print(f"Error auto-creating settings.json on first launch: {e}")

        # Position safety check
        if settings.get("position") not in ("top_center", "top_left", "top_right", "bottom_center"):
            settings["position"] = "top_center"

        # Defensive type & range validation
        try:
            settings["bg_opacity"] = max(0.85, min(1.0, float(settings.get("bg_opacity", 0.90))))
        except (ValueError, TypeError):
            settings["bg_opacity"] = 0.90

        try:
            settings["offset_y"] = int(settings.get("offset_y", 12))
        except (ValueError, TypeError):
            settings["offset_y"] = 12

        try:
            settings["offset_x"] = int(settings.get("offset_x", 0))
        except (ValueError, TypeError):
            settings["offset_x"] = 0

        try:
            settings["monitor_index"] = max(0, int(settings.get("monitor_index", 0)))
        except (ValueError, TypeError):
            settings["monitor_index"] = 0

        try:
            settings["corner_radius"] = max(8, min(30, int(settings.get("corner_radius", 20))))
        except (ValueError, TypeError):
            settings["corner_radius"] = 20

        try:
            settings["alarm_autodismiss_seconds"] = max(5, int(settings.get("alarm_autodismiss_seconds", 30)))
        except (ValueError, TypeError):
            settings["alarm_autodismiss_seconds"] = 30

        try:
            val = int(settings.get("hover_delay_ms", 400))
            settings["hover_delay_ms"] = val if val >= 300 else 400
        except (ValueError, TypeError):
            settings["hover_delay_ms"] = 400

        return settings

    def save_settings(self):
        """Immediately notifies UI subscribers and debounces disk file write."""
        import time
        t0 = time.perf_counter()
        print(f"[SIGNAL] settings_changed EMITTED from SettingsManager: theme_mode={self.settings.get('theme_mode')}, accent_identity={self.settings.get('accent_identity')}, corner_radius={self.settings.get('corner_radius')}, bg_opacity={self.settings.get('bg_opacity')}", flush=True)
        self.settings_changed.emit(self.settings)
        t_emit_ms = (time.perf_counter() - t0) * 1000.0
        print(f"[TIMING] settings_changed signal emission took: {t_emit_ms:.2f}ms", flush=True)
        self.save_timer.start(400)

    def flush_save(self):
        """Writes current settings to disk immediately."""
        import time
        t0 = time.perf_counter()
        try:
            safe_atomic_write_json(self.settings_file, self.settings)

            cur_startup = self.settings.get("start_with_windows", False)
            if getattr(self, "last_startup_reg_state", None) != cur_startup:
                self.last_startup_reg_state = cur_startup
                self.sync_registry_startup()
            t_disk_ms = (time.perf_counter() - t0) * 1000.0
            print(f"[TIMING] disk_write (flush_save): {t_disk_ms:.2f}ms", flush=True)
        except Exception as e:
            print(f"Error flushing settings to disk: {e}")

    def get(self, key, default=None):
        val = self.settings.get(key)
        if val is not None:
            return val
        if default is not None:
            return default
        return DEFAULT_SETTINGS.get(key)

    def set(self, key, value):
        if self.settings.get(key) == value:
            return
        self.settings[key] = value
        self.save_settings()

    def update_settings(self, new_settings: dict):
        changed = False
        for k, v in new_settings.items():
            if self.settings.get(k) != v:
                self.settings[k] = v
                changed = True
        if changed:
            self.save_settings()

    def sync_registry_startup(self):
        """Syncs application startup preference with Windows Registry using context managers."""
        enable = bool(self.settings.get("start_with_windows", False))
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH, 0, winreg.KEY_ALL_ACCESS) as key:
                # Clean up legacy autostart value 'DynamicIsland' if present
                try:
                    winreg.DeleteValue(key, "DynamicIsland")
                    print("[REGISTRY MIGRATION]: Cleaned up legacy 'DynamicIsland' autostart key.", flush=True)
                except FileNotFoundError:
                    pass

                if enable:
                    if getattr(sys, 'frozen', False):
                        exe_path = sys.executable
                    else:
                        exe_path = os.path.abspath(sys.argv[0])
                    winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, f'"{exe_path}"')
                else:
                    try:
                        winreg.DeleteValue(key, APP_NAME)
                    except FileNotFoundError:
                        pass
        except Exception as e:
            print(f"Registry startup sync exception: {e}")
