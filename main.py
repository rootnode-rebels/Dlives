import hashlib
import time
import sys
import os
import time
import ctypes
import threading
import winsound
import traceback
from datetime import datetime, timedelta

def uncaught_exception_handler(exctype, value, tb):
    if issubclass(exctype, RecursionError):
        print(f"=== RECURSION ERROR CRASH ===: {value}", file=sys.stderr, flush=True)
        sys.exit(1)
    print("=== UNCAUGHT EXCEPTION CRASH ===", file=sys.stderr)
    traceback.print_exception(exctype, value, tb)
    sys.stderr.flush()
    sys.exit(1)

sys.excepthook = uncaught_exception_handler

from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QPropertyAnimation, QEasingCurve, QSize, QThread, pyqtProperty, QObject, QUrl, QFileSystemWatcher
from PyQt6.QtGui import QColor, QFont, QIcon, QPixmap, QPainter, QPainterPath, QPen, QBrush, QCursor, QAction, QImage
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QStackedWidget, QFrame, QSizePolicy, QGraphicsDropShadowEffect, QGraphicsOpacityEffect,
    QComboBox, QSystemTrayIcon, QMenu, QStyle, QLineEdit, QTextEdit, QPlainTextEdit, QAbstractSpinBox, QFileDialog
)

try:
    from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
    HAS_QT_MULTIMEDIA = True
except ImportError:
    HAS_QT_MULTIMEDIA = False

try:
    from pynput import keyboard as pynput_keyboard
    HAS_PYNPUT = True
except ImportError:
    HAS_PYNPUT = False

from storage_manager import StorageManager
from settings_manager import SettingsManager
from system_monitor import SystemMonitor, NowPlayingWorkerThread, PriorityNotificationWorkerThread, AlarmSchedulerWorkerThread
from ui_components import (
    CollapsedPillWidget, ContainerFrame, AlarmBannerModalCard, NotificationBannerModalCard,
    HomeLandingTabWidget, ControlCenterTabWidget, HardwareDiagnosticsTabWidget,
    ClipboardShelfTabWidget, CalendarTabWidget, AlarmsTabWidget,
    AppLauncherTabWidget, QuickNotesTabWidget, SettingsTabWidget,
    NotificationsTabWidget, THEME_PALETTES, resolve_accent_color,
    get_accent_text_color, get_accent_tinted_logo
)


class HotkeySignalEmitter(QObject):
    toggle_requested = pyqtSignal()


class TelemetryWorkerThread(QThread):
    """Background Worker Thread for System Diagnostics & Telemetry (1000ms polling)."""
    telemetry_updated = pyqtSignal(dict)
    system_event_triggered = pyqtSignal(dict)

    def __init__(self, interval_ms: int = 1000, parent=None):
        super().__init__(parent)
        self.interval_ms = interval_ms
        self.is_running = True
        self.prev_battery_pct = None
        self.prev_charging = None
        self.prev_net_connected = None
        self.prev_hotspot_active = None
        self.is_first_tick = True

    def run(self):
        try:
            from comtypes import CoInitialize
            CoInitialize()
        except Exception:
            pass
        print("[STARTUP] Telemetry Worker Thread Started & Polling (1000ms)")

        while self.is_running:
            try:
                try:
                    bat_info = SystemMonitor.get_battery_info()
                except Exception as e:
                    print(f"[Telemetry Fetch Error - Battery]: {e}")
                    bat_info = {"percent": None, "charging": False}

                try:
                    cpu_val = SystemMonitor.get_cpu_usage()
                except Exception as e:
                    print(f"[Telemetry Fetch Error - CPU]: {e}")
                    cpu_val = 0.0

                try:
                    ram_val = SystemMonitor.get_ram_details()
                except Exception as e:
                    print(f"[Telemetry Fetch Error - RAM]: {e}")
                    ram_val = {"percent": 0.0, "used_gb": 0.0, "total_gb": 0.0}

                try:
                    wifi_val = SystemMonitor.get_wifi_network_info()
                except Exception as e:
                    print(f"[Telemetry Fetch Error - WiFi]: {e}")
                    wifi_val = {"connected": False, "name": "Unknown", "ssid": ""}

                try:
                    vol_val = SystemMonitor.get_master_volume()
                except Exception as e:
                    print(f"[Telemetry Fetch Error - Volume]: {e}")
                    vol_val = 50

                try:
                    bri_val = SystemMonitor.get_brightness()
                except Exception as e:
                    print(f"[Telemetry Fetch Error - Brightness]: {e}")
                    bri_val = 100

                try:
                    boot_val = SystemMonitor.get_boot_timestamp()
                except Exception:
                    boot_val = "--:--"

                try:
                    uptime_val = SystemMonitor.get_uptime_string()
                except Exception:
                    uptime_val = "0h 0m"

                try:
                    disk_val = SystemMonitor.get_disk_info()
                except Exception:
                    disk_val = {"used_gb": 0.0, "total_gb": 0.0}

                hotspot_val = SystemMonitor.is_hotspot_active()
                cur_pct = bat_info.get("percent")
                cur_charging = bat_info.get("charging", False)
                cur_connected = wifi_val.get("connected", False)
                cur_ssid = wifi_val.get("ssid") or wifi_val.get("name") or ""

                # Edge-triggered transition detection for In-Pill highlighted status toasts
                if not self.is_first_tick:
                    # 1. Charging transitions (Plugged in, Unplugged, or reached 100% Fully Charged)
                    if cur_charging is True and self.prev_charging is False:
                        if cur_pct is not None and cur_pct >= 100:
                            self.system_event_triggered.emit({
                                "type": "fully_charged",
                                "text": "Fully Charged (100%)",
                                "icon": "⚡",
                                "color": "#00e676"
                            })
                        else:
                            pct_str = f" ({cur_pct}%)" if cur_pct is not None else ""
                            self.system_event_triggered.emit({
                                "type": "charging_connected",
                                "text": f"Charging{pct_str}",
                                "icon": "⚡",
                                "color": "#00e676"
                            })
                    elif cur_charging is False and self.prev_charging is True:
                        pct_str = f" ({cur_pct}%)" if cur_pct is not None else ""
                        self.system_event_triggered.emit({
                            "type": "charging_disconnected",
                            "text": f"On Battery{pct_str}",
                            "icon": "🔋",
                            "color": "#38bdf8"
                        })
                    elif cur_charging is True and cur_pct is not None and cur_pct >= 100 and (self.prev_battery_pct is not None and self.prev_battery_pct < 100):
                        self.system_event_triggered.emit({
                            "type": "fully_charged",
                            "text": "Fully Charged (100%)",
                            "icon": "⚡",
                            "color": "#00e676"
                        })

                    # 2. Network Connected / Disconnected / SSID switch
                    if cur_connected and (self.prev_net_connected is False or (cur_ssid and self.prev_ssid and cur_ssid != self.prev_ssid)):
                        ssid_name = cur_ssid if cur_ssid else "Network"
                        self.system_event_triggered.emit({
                            "type": "net_connected",
                            "text": f"Connected: {ssid_name}",
                            "icon": "📶",
                            "color": "#38bdf8"
                        })
                    elif not cur_connected and self.prev_net_connected is True:
                        self.system_event_triggered.emit({
                            "type": "net_disconnected",
                            "text": "Network Disconnected",
                            "icon": "⚠️",
                            "color": "#f97316"
                        })

                    # 3. Hotspot Active / Disabled
                    if hotspot_val is True and self.prev_hotspot_active is False:
                        self.system_event_triggered.emit({
                            "type": "hotspot_active",
                            "text": "Hotspot Active",
                            "icon": "📡",
                            "color": "#a855f7"
                        })
                    elif hotspot_val is False and self.prev_hotspot_active is True:
                        self.system_event_triggered.emit({
                            "type": "hotspot_inactive",
                            "text": "Hotspot Off",
                            "icon": "📡",
                            "color": "#94a3b8"
                        })
                else:
                    self.is_first_tick = False

                self.prev_battery_pct = cur_pct
                self.prev_charging = cur_charging
                self.prev_net_connected = cur_connected
                self.prev_ssid = cur_ssid
                self.prev_hotspot_active = hotspot_val

                data = {
                    "cpu": cpu_val,
                    "ram_info": ram_val,
                    "wifi_network": wifi_val,
                    "battery": bat_info,
                    "charging": bat_info.get('charging', False) if isinstance(bat_info, dict) else False,
                    "volume": vol_val,
                    "brightness": bri_val,
                    "boot_timestamp": boot_val,
                    "uptime": uptime_val,
                    "disk": disk_val,
                    "hotspot_active": hotspot_val,
                    "windows_theme": SystemMonitor.get_windows_theme_mode()
                }
                self.telemetry_updated.emit(data)
            except Exception as e:
                print(f"[Telemetry Worker Exception]: {e}")

            self.msleep(self.interval_ms)

    def stop(self):
        self.is_running = False
        self.wait(1000)


class GlobalDropOverlay(QFrame):
    """Translucent visual drop feedback overlay frame across the dashboard surface."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setStyleSheet("""
            QFrame#global_drop_overlay {
                background-color: rgba(15, 23, 42, 0.90);
                border: 2px dashed #06b6d4;
                border-radius: 16px;
            }
        """)
        self.setObjectName("global_drop_overlay")
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label = QLabel("📥 Drop anywhere to save file to File Shelf", self)
        label.setStyleSheet("color: #38bdf8; font-size: 15px; font-weight: bold; background: transparent;")
        layout.addWidget(label)
        self.hide()


class MainAppEventFilter(QObject):
    """Application-level event filter for scoped Left/Right arrow main tab navigation."""
    def __init__(self, main_window):
        super().__init__(main_window)
        self.main_window = main_window

    def eventFilter(self, obj, event):
        from PyQt6.QtCore import QEvent
        if event.type() == QEvent.Type.KeyPress:
            if event.key() in (Qt.Key.Key_Left, Qt.Key.Key_Right, Qt.Key.Key_Up, Qt.Key.Key_Down):
                focused = QApplication.focusWidget()

                # Exclusion 1: Text editors, search inputs, sliders, wheel pickers
                if self.is_widget_excluded(focused):
                    return super().eventFilter(obj, event)

                # Exclusion 2: Active modal dialogs (e.g. AddAppDialog)
                if QApplication.activeModalWidget() is not None:
                    return super().eventFilter(obj, event)

                # Active Tab 4-Directional Grid Arrow Switching
                if self.main_window.is_expanded:
                    self.main_window.switch_tab_directional(event.key())
                    return True

        return super().eventFilter(obj, event)

    def is_widget_excluded(self, widget) -> bool:
        if widget is None:
            return False

        from PyQt6.QtWidgets import QLineEdit, QTextEdit, QPlainTextEdit, QSlider, QComboBox, QSpinBox, QDoubleSpinBox
        if isinstance(widget, (QLineEdit, QTextEdit, QPlainTextEdit, QSlider, QComboBox, QSpinBox, QDoubleSpinBox)):
            return True

        name = widget.metaObject().className()
        if any(ex in name for ex in ["QLineEdit", "QTextEdit", "QPlainTextEdit", "QSlider", "QComboBox", "WheelColumnWidget"]):
            return True

        parent = widget.parent()
        while parent:
            pname = parent.metaObject().className()
            if any(ex in pname for ex in ["AddAppDialog", "WheelTimePickerWidget"]):
                return True
            parent = parent.parent()

        return False


class DynamicIsland(QWidget):
    """Dynamic Island Pro v2.2.0 Main Overlay Window."""
    def __init__(self, storage: StorageManager = None, settings: SettingsManager = None):
        super().__init__()
        self.storage = storage or StorageManager()
        self.settings = settings or SettingsManager()
        self.settings.settings_changed.connect(self.on_settings_changed)

        # Alarm Scheduler Trigger Tracker (Prevents Duplicate Alerts in Same Minute)
        self.triggered_keys_today = set()
        self.last_checked_date = datetime.now().strftime("%Y-%m-%d")

        # Geometry Constraints
        self.setWindowTitle("Dlives")
        self.collapsed_width = 380
        self.collapsed_height = 36
        self.expanded_width = 588
        self.expanded_height = 350
        self.margin = 22

        self.current_frame_width = self.collapsed_width
        self.current_frame_height = self.collapsed_height
        self.is_expanded = False
        self.is_alarm_alert_active = False
        self.last_home_flags = (
            self.settings.get("show_home_alarms", True),
            self.settings.get("show_home_timetable", True),
            self.settings.get("show_home_calendar", True),
            self.settings.get("show_home_notes", True),
            self.settings.get("show_home_now_playing", True),
            self.settings.get("show_home_notifications", True),
            self.settings.get("show_home_pomodoro", True),
            self.settings.get("show_home_dropzone", True),
        )

        # QMediaPlayer & QAudioOutput Engine for Custom Alarm Sounds
        if HAS_QT_MULTIMEDIA:
            try:
                self.media_player = QMediaPlayer(self)
                self.audio_output = QAudioOutput(self)
                self.media_player.setAudioOutput(self.audio_output)
                self.audio_output.setVolume(1.0)
            except Exception as e:
                print(f"[QMediaPlayer Init Exception]: {e}")
                self.media_player = None
                self.audio_output = None
        else:
            self.media_player = None
            self.audio_output = None

        # Continuous Alarm Sound & Auto-Dismiss Timers
        self.alarm_sound_timer = QTimer(self)
        self.alarm_sound_timer.timeout.connect(self.play_continuous_sound_step)

        self.auto_dismiss_timer = QTimer(self)
        self.auto_dismiss_timer.setSingleShot(True)
        self.auto_dismiss_timer.timeout.connect(self.dismiss_alarm_alert)

        self.init_window_flags()
        self.init_ui()

        # Decoupled Timers
        self.hover_timer = QTimer(self)
        self.hover_timer.setSingleShot(True)
        self.hover_timer.timeout.connect(self.expand_island)

        self.leave_timer = QTimer(self)
        self.leave_timer.setSingleShot(True)
        self.leave_timer.timeout.connect(self.perform_soft_collapse)

        self.clock_timer = QTimer(self)
        self.clock_timer.setInterval(200)  # High-speed clock tick
        self.clock_timer.timeout.connect(self.on_fast_clock_tick)
        self.clock_timer.start()

        # Dedicated Isolated Alarm & Timetable Scheduler Worker Thread (Zero GUI blocking)
        self.alarm_scheduler_thread = AlarmSchedulerWorkerThread(self.storage, parent=self)
        self.alarm_scheduler_thread.alarm_due.connect(self.on_alarm_scheduler_due)
        self.alarm_scheduler_thread.start()

        # Fallback GUI Scheduler Timer (1000ms Interval)
        self.scheduler_timer = QTimer(self)
        self.scheduler_timer.setInterval(1000)
        self.scheduler_timer.timeout.connect(self.check_scheduled_alarms_and_timetable)
        self.scheduler_timer.start()

        self.mouse_outside_since = None
        self.safety_net_timer = QTimer(self)
        self.safety_net_timer.setInterval(100)
        self.safety_net_timer.timeout.connect(self.check_force_collapse_safety)
        self.safety_net_timer.start()

        # Application-Level Event Filter for Arrow Tab Navigation
        self.app_event_filter = MainAppEventFilter(self)
        QApplication.instance().installEventFilter(self.app_event_filter)

        # Initial Positioning
        self.update_window_position(self.collapsed_width, self.collapsed_height)
        self.init_telemetry_thread()
        self.init_system_tray()
        self.show()
        print("[STARTUP] GUI Window Created", flush=True)

    def closeEvent(self, event):
        try:
            if hasattr(self, 'alarm_scheduler_thread') and self.alarm_scheduler_thread and self.alarm_scheduler_thread.isRunning():
                self.alarm_scheduler_thread.stop()
            if hasattr(self, 'telemetry_thread') and self.telemetry_thread and self.telemetry_thread.isRunning():
                self.telemetry_thread.stop()
            if hasattr(self, 'priority_notif_thread') and self.priority_notif_thread and self.priority_notif_thread.isRunning():
                self.priority_notif_thread.stop()
            if hasattr(self, 'scheduler_timer') and self.scheduler_timer:
                self.scheduler_timer.stop()
        except Exception:
            pass
        super().closeEvent(event)

    def init_window_flags(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setAcceptDrops(True)

        icon_path = os.path.join(os.path.dirname(__file__), "app_icon.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
            QApplication.setWindowIcon(QIcon(icon_path))

    def init_ui(self):
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(self.margin, self.margin, self.margin, self.margin)

        self.full_app_window = None

        # Right-click drag repositioning state
        self._right_drag_active = False
        self._right_drag_start_pos = None
        self._right_drag_start_win_pos = None
        self._right_drag_distance = 0

        # Container Frame
        self.container_frame = ContainerFrame()
        self.container_frame.settings = self.settings
        self.container_frame.setObjectName("container_frame")
        self.container_frame.setFixedSize(self.collapsed_width, self.collapsed_height)
        self.container_frame.setAcceptDrops(True)

        self.frame_layout = QVBoxLayout(self.container_frame)
        self.frame_layout.setContentsMargins(0, 0, 0, 0)
        self.frame_layout.setSpacing(0)

        # 1. Collapsed Pill Header
        self.pill_widget = CollapsedPillWidget(self.container_frame)
        self.pill_widget.settings = self.settings
        self.pill_widget.double_clicked.connect(self.open_full_app_window)
        self.frame_layout.addWidget(self.pill_widget)

        # Install event filters for seamless right-click dragging anywhere on bar
        self.installEventFilter(self)
        self.container_frame.installEventFilter(self)
        self.pill_widget.installEventFilter(self)

        # 2. Full-Window Alarm/Timetable Modal Takeover Card
        self.alarm_banner_card = AlarmBannerModalCard(self.container_frame)
        self.alarm_banner_card.dismiss_requested.connect(self.dismiss_alarm_alert)
        self.alarm_banner_card.snooze_requested.connect(self.snooze_alarm_alert)
        self.alarm_banner_card.mark_done_requested.connect(self.mark_done_alarm_alert)
        self.alarm_banner_card.hide()
        self.frame_layout.addWidget(self.alarm_banner_card)

        # 2b. Full-Window Priority Notification Takeover Card
        self.notification_banner_card = NotificationBannerModalCard(self.container_frame)
        self.notification_banner_card.dismiss_requested.connect(self.dismiss_notification_popup)
        self.notification_banner_card.open_requested.connect(self.on_notification_popup_open)
        self.notification_banner_card.hide()
        self.frame_layout.addWidget(self.notification_banner_card)

        # 3. Expanded Dashboard Container
        self.dashboard_widget = QWidget(self.container_frame)
        self.dashboard_widget.setFixedSize(self.expanded_width, self.expanded_height)
        dashboard_layout = QVBoxLayout(self.dashboard_widget)
        dashboard_layout.setContentsMargins(6, 4, 6, 4)
        dashboard_layout.setSpacing(4)

        # Quick Header Bar
        dash_header_box = QHBoxLayout()
        dash_header_box.setContentsMargins(14, 4, 14, 0)
        dash_header_box.setSpacing(6)

        self.dash_logo_lbl = QLabel()
        self.dash_logo_lbl.setFixedSize(20, 20)
        logo_p = os.path.join(os.path.dirname(__file__), "assets", "san_lives_logo.png")
        if os.path.exists(logo_p):
            self.dash_logo_lbl.setPixmap(QPixmap(logo_p).scaled(20, 20, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))

        self.dash_brand_lbl = QLabel("DLIVES")
        self.dash_brand_lbl.setStyleSheet("color: #38bdf8; font-size: 10px; font-weight: 900; letter-spacing: 0.5px; background: transparent;")

        self.btn_open_full_app = QPushButton("🖥️ Expand Workspace \u2197")
        self.btn_open_full_app.setToolTip("Open Full Workspace Studio Window")
        self.btn_open_full_app.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_open_full_app.setFixedHeight(22)
        self.btn_open_full_app.setObjectName("btn_open_full_app")
        self.btn_open_full_app.clicked.connect(lambda: self.open_full_app_window())

        dash_header_box.addWidget(self.dash_logo_lbl)
        dash_header_box.addWidget(self.dash_brand_lbl)
        dash_header_box.addStretch()
        dash_header_box.addWidget(self.btn_open_full_app)
        dashboard_layout.addLayout(dash_header_box)

        # 2-Row Dynamic Inset Navigation Tab Bar
        tab_bar_box = QVBoxLayout()
        tab_bar_box.setContentsMargins(14, 2, 14, 2)
        tab_bar_box.setSpacing(3)

        self.row1_layout = QHBoxLayout()
        self.row1_layout.setSpacing(3)
        self.row2_layout = QHBoxLayout()
        self.row2_layout.setSpacing(3)

        tab_bar_box.addLayout(self.row1_layout)
        tab_bar_box.addLayout(self.row2_layout)
        dashboard_layout.addLayout(tab_bar_box)

        # Main Stacked Tab Content Views
        self.stacked_widget = QStackedWidget()
        self.stacked_widget.setFixedSize(576, 274)
        self.stacked_widget.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        self.tab_home = HomeLandingTabWidget(self.storage, self.settings)
        self.tab_control = ControlCenterTabWidget(self.settings)
        self.tab_hardware = HardwareDiagnosticsTabWidget(self.settings)
        self.tab_shelf_clip = ClipboardShelfTabWidget(self.storage, self.settings)
        self.tab_calendar = CalendarTabWidget(self.storage, self.settings)
        self.tab_alarms = AlarmsTabWidget(self.storage, self.settings)
        self.tab_apps = AppLauncherTabWidget(self.storage, self.settings)
        self.tab_notes = QuickNotesTabWidget(self.storage, self.settings)
        self.tab_settings = SettingsTabWidget(self.settings)
        self.tab_settings.open_full_window_requested.connect(lambda: self.open_full_app_window(0))
        self.tab_notifications = NotificationsTabWidget(self.settings)
        self.tab_notifications.open_notification_requested.connect(lambda _: self.expand_dashboard())
        self.tab_home.pomo_tick_relayed.connect(self.pill_widget.update_pomodoro_badge)

        self.all_tabs_map = {
            "home": {"title": "🏠 Home", "widget": self.tab_home},
            "control": {"title": "🎛️ Control", "widget": self.tab_control},
            "hardware": {"title": "📊 Sys", "widget": self.tab_hardware},
            "shelf_clip": {"title": "📋 Shelf", "widget": self.tab_shelf_clip},
            "calendar": {"title": "📅 Calendar", "widget": self.tab_calendar},
            "alarms": {"title": "🔔 Alarms", "widget": self.tab_alarms},
            "apps": {"title": "🚀 Apps", "widget": self.tab_apps},
            "notes": {"title": "📝 Notes", "widget": self.tab_notes},
            "notifs": {"title": "🔔 Notifs", "widget": self.tab_notifications},
            "settings": {"title": "⚙️ Settings", "widget": self.tab_settings},
        }

        self.tab_buttons = []
        self.active_tab_keys = []
        self.last_tab_config = (None, None)
        self.rebuild_island_tabs()

        dashboard_layout.addWidget(self.stacked_widget)
        self.dashboard_widget.hide()

        self.frame_layout.addWidget(self.dashboard_widget)
        outer_layout.addWidget(self.container_frame)

        # Global Translucent Drop Overlay
        self.global_drop_overlay = GlobalDropOverlay(self.container_frame)

        # Smooth Geometry Animation
        self.anim = QPropertyAnimation(self, b"frameGeometrySize")
        self.anim.setDuration(220)
        self.anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.anim.valueChanged.connect(self.on_anim_frame_size_changed)

        self.apply_container_style()
        self.switch_tab(0)

        # Non-Blocking Background Priority Notification Poller Thread
        self.priority_notif_thread = PriorityNotificationWorkerThread(self.settings, interval_ms=2500, parent=self)
        self.priority_notif_thread.priority_notification_found.connect(self.trigger_notification_popup)
        self.priority_notif_thread.start()

    def switch_tab_relative(self, delta: int):
        curr = self.stacked_widget.currentIndex()
        count = self.stacked_widget.count()
        if count <= 0:
            return
        new_idx = (curr + delta) % count
        self.switch_tab(new_idx)

    def switch_tab_directional(self, key_code):
        curr = self.stacked_widget.currentIndex()
        count = self.stacked_widget.count()
        if count <= 0:
            return

        row_size = 5  # 2 rows of 5 buttons each

        if key_code == Qt.Key.Key_Left:
            new_idx = (curr - 1) % count
        elif key_code == Qt.Key.Key_Right:
            new_idx = (curr + 1) % count
        elif key_code == Qt.Key.Key_Down:
            if curr < row_size:
                new_idx = curr + row_size  # Row 1 -> Row 2
            else:
                new_idx = curr - row_size  # Row 2 -> Row 1 (wraparound)
        elif key_code == Qt.Key.Key_Up:
            if curr >= row_size:
                new_idx = curr - row_size  # Row 2 -> Row 1
            else:
                new_idx = curr + row_size  # Row 1 -> Row 2 (wraparound)
        else:
            return

        new_idx = max(0, min(new_idx, count - 1))
        self.switch_tab(new_idx)

    def get_frame_geometry_size(self) -> QSize:
        return QSize(self.current_frame_width, self.current_frame_height)

    def set_frame_geometry_size(self, size: QSize):
        self.current_frame_width = size.width()
        self.current_frame_height = size.height()

    frameGeometrySize = pyqtProperty(QSize, get_frame_geometry_size, set_frame_geometry_size)

    def on_anim_frame_size_changed(self, size: QSize):
        w = size.width()
        h = size.height()
        self.container_frame.setFixedSize(w, h)
        self.update_window_position(w, h)

    def apply_container_style(self):
        bg_opacity = float(self.settings.get("bg_opacity", 0.90))
        corner_radius = int(self.settings.get("corner_radius", 20))
        mode = self.settings.get("theme_mode", "dark")
        accent_color = resolve_accent_color(self.settings)
        self.container_frame.set_style_properties(bg_opacity, corner_radius, accent_color, mode)
        if hasattr(self, 'dash_brand_lbl'):
            self.dash_brand_lbl.setStyleSheet(f"color: {accent_color}; font-size: 10px; font-weight: 900; letter-spacing: 0.5px; background: transparent;")
        if hasattr(self, 'dash_logo_lbl'):
            self.dash_logo_lbl.setFixedSize(20, 20)
            custom_logo = self.settings.get("custom_logo_path", "")
            pix = get_accent_tinted_logo(accent_color, mode, 18, custom_logo)
            if not pix.isNull():
                self.dash_logo_lbl.setPixmap(pix)
        if hasattr(self, 'btn_open_full_app'):
            btn_bg = "rgba(56, 189, 248, 0.14)" if mode == "dark" else "rgba(2, 132, 199, 0.12)"
            btn_border = "rgba(56, 189, 248, 0.35)" if mode == "dark" else "rgba(2, 132, 199, 0.30)"
            self.btn_open_full_app.setStyleSheet(f"""
                QPushButton {{
                    background-color: {btn_bg};
                    color: {accent_color};
                    border: 1px solid {btn_border};
                    border-radius: 5px;
                    font-size: 9.5px;
                    font-weight: 800;
                    padding: 0 8px;
                }}
                QPushButton:hover {{
                    background-color: {accent_color};
                    color: #ffffff;
                    border: 1px solid {accent_color};
                }}
            """)

    def update_ambient_aura(self, data: dict = None):
        if not hasattr(self, 'container_frame'):
            return
        if data is None:
            data = getattr(self, 'latest_telemetry', {}) or {}
        charging = data.get('charging', False)
        bat = data.get('battery', {})
        pct = bat.get('percent') if isinstance(bat, dict) else None

        if charging:
            self.container_frame.set_aura_state("charging")
        elif getattr(self, 'is_media_playing', False):
            self.container_frame.set_aura_state("media")
        elif pct is not None and pct <= 20 and not charging:
            self.container_frame.set_aura_state("low_battery")
        else:
            self.container_frame.set_aura_state("idle")

    def update_notif_badge(self, count: int):
        self.unread_notif_count = count
        for idx, key in enumerate(getattr(self, 'active_tab_keys', [])):
            if key == "notifs" and idx < len(self.tab_buttons):
                btn = self.tab_buttons[idx]
                if count > 0:
                    btn.setText(f"🔔 Notifs ({count})")
                else:
                    btn.setText("🔔 Notifs")
                break

    def rebuild_island_tabs(self):
        """Dynamically arranges visible tabs and tab buttons in the compact island according to settings."""
        if not hasattr(self, 'all_tabs_map') or not self.all_tabs_map:
            return
        while self.row1_layout.count():
            item = self.row1_layout.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)
                w.deleteLater()

        while self.row2_layout.count():
            item = self.row2_layout.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)
                w.deleteLater()

        default_order = ["home", "control", "hardware", "shelf_clip", "calendar", "alarms", "apps", "notes", "notifs", "settings"]
        tab_order = self.settings.get("tab_order", default_order)
        visible_tabs = set(self.settings.get("visible_tabs", default_order))
        if "home" not in visible_tabs:
            visible_tabs.add("home")

        active_tab_keys = [k for k in tab_order if k in visible_tabs and k in self.all_tabs_map]
        for k in visible_tabs:
            if k not in active_tab_keys and k in self.all_tabs_map:
                active_tab_keys.append(k)

        if not active_tab_keys:
            active_tab_keys = ["home"]

        while self.stacked_widget.count():
            self.stacked_widget.removeWidget(self.stacked_widget.widget(0))

        self.tab_buttons = []
        self.active_tab_keys = active_tab_keys

        half = (len(active_tab_keys) + 1) // 2
        for idx, key in enumerate(active_tab_keys):
            info = self.all_tabs_map[key]
            widget = info["widget"]
            widget.setFixedSize(576, 274)
            widget.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            self.stacked_widget.addWidget(widget)

            btn = QPushButton(info["title"])
            btn.setFixedHeight(20)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _, i=idx: self.switch_tab(i))
            btn.installEventFilter(self)
            self.tab_buttons.append(btn)

            if idx < half:
                self.row1_layout.addWidget(btn)
            else:
                self.row2_layout.addWidget(btn)

        self.last_tab_config = (tuple(tab_order), tuple(sorted(visible_tabs)))
        cur_idx = min(max(0, self.stacked_widget.currentIndex()), len(active_tab_keys) - 1)
        self.switch_tab(cur_idx)

    def switch_tab(self, index: int):
        prev_idx = self.stacked_widget.currentIndex()
        target_widget = self.stacked_widget.widget(index)

        # Stop any active fade animation
        if hasattr(self, '_tab_fade_anim') and self._tab_fade_anim and self._tab_fade_anim.state() == QPropertyAnimation.State.Running:
            self._tab_fade_anim.stop()

        self.stacked_widget.setCurrentIndex(index)

        if target_widget:
            try:
                target_widget.setFixedSize(576, 274)
                target_widget.setGeometry(0, 0, 576, 274)
                if target_widget.layout():
                    target_widget.layout().activate()
                target_widget.show()
                target_widget.raise_()
            except Exception:
                pass

        if prev_idx != index and target_widget:
            try:
                effect = getattr(target_widget, '_tab_fade_effect', None)
                if not effect:
                    effect = QGraphicsOpacityEffect(target_widget)
                    target_widget._tab_fade_effect = effect

                target_widget.setGraphicsEffect(effect)
                effect.setOpacity(0.0)

                anim = QPropertyAnimation(effect, b"opacity", self)
                anim.setDuration(350)
                anim.setStartValue(0.0)
                anim.setEndValue(1.0)
                anim.setEasingCurve(QEasingCurve.Type.OutCubic)
                anim.start()
                self._tab_fade_anim = anim
            except Exception:
                pass

        accent = resolve_accent_color(self.settings)
        accent_txt = get_accent_text_color(accent)
        mode = self.settings.get("theme_mode", "dark")
        pal = THEME_PALETTES.get(mode, THEME_PALETTES["dark"])

        for idx, btn in enumerate(self.tab_buttons):
            if idx == index:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {accent};
                        color: {accent_txt};
                        font-weight: 800;
                        border-radius: 5px;
                        font-size: 8.5px;
                        border: 1px solid rgba(255, 255, 255, 0.35);
                        padding: 1px 4px;
                    }}
                """)
            else:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {pal['sub_btn_bg']};
                        color: {pal['sub_btn_text']};
                        border-radius: 5px;
                        font-size: 8.5px;
                        font-weight: 600;
                        border: 1px solid {pal['sub_btn_border']};
                        padding: 1px 4px;
                    }}
                    QPushButton:hover {{
                        background-color: {pal['list_item_hover']};
                        color: {pal['text_primary']};
                        border: 1px solid {accent};
                    }}
                """)

        tab_widget = self.stacked_widget.widget(index)
        if hasattr(tab_widget, "apply_theme"):
            tab_widget.apply_theme(accent, mode)

        if hasattr(tab_widget, "load_notifications_feed"):
            try:
                tab_widget.load_notifications_feed()
            except Exception as e:
                print(f"Error loading notifications feed on tab switch: {e}")
        elif hasattr(tab_widget, "load_alarms") and hasattr(tab_widget, "load_timetable"):
            try:
                tab_widget.load_alarms()
                tab_widget.load_timetable()
            except Exception as e:
                print(f"Error reloading alarms/timetable on tab switch: {e}")

    def update_window_position(self, frame_w: int, frame_h: int):
        if not hasattr(self, '_cached_screen_geo') or self._cached_screen_geo is None:
            screens = QApplication.screens()
            mon_idx = int(self.settings.get("monitor_index", 0))
            if 0 <= mon_idx < len(screens):
                screen = screens[mon_idx]
            else:
                screen = QApplication.primaryScreen()
            if not screen:
                return
            self._cached_screen_geo = screen.availableGeometry()
        
        geo = self._cached_screen_geo
        pos_setting = self.settings.get("position", "top_center")
        offset_x = int(self.settings.get("offset_x", 0))
        offset_y = int(self.settings.get("offset_y", 12))

        win_w = int(round(frame_w + (self.margin * 2)))
        win_h = int(round(frame_h + (self.margin * 2)))

        if pos_setting == "top_left":
            x = int(round(geo.x() + offset_x))
            y = int(round(geo.y() + offset_y))
        elif pos_setting == "top_right":
            x = int(round(geo.x() + geo.width() - win_w - offset_x))
            y = int(round(geo.y() + offset_y))
        elif pos_setting == "bottom_center":
            x = int(round(geo.x() + ((geo.width() - win_w) / 2.0) + offset_x))
            y = int(round(geo.y() + geo.height() - win_h - offset_y))
        else:  # top_center
            x = int(round(geo.x() + ((geo.width() - win_w) / 2.0) + offset_x))
            y = int(round(geo.y() + offset_y))

        self.setGeometry(x, y, win_w, win_h)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls() or event.mimeData().hasText():
            print("[Main Window DragEnter]: File/text dragged over DynamicIsland main window!")
            event.acceptProposedAction()
            if not self.is_expanded:
                self.expand_island()
            if hasattr(self, 'global_drop_overlay') and self.global_drop_overlay:
                self.global_drop_overlay.setGeometry(self.dashboard_widget.geometry())
                self.global_drop_overlay.raise_()
                self.global_drop_overlay.show()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls() or event.mimeData().hasText():
            event.acceptProposedAction()

    def dragLeaveEvent(self, event):
        if hasattr(self, 'global_drop_overlay') and self.global_drop_overlay:
            self.global_drop_overlay.hide()
        super().dragLeaveEvent(event)

    def dropEvent(self, event):
        if hasattr(self, 'global_drop_overlay') and self.global_drop_overlay:
            self.global_drop_overlay.hide()

        if event.mimeData().hasUrls():
            saved_count = 0
            for url in event.mimeData().urls():
                fp = url.toLocalFile()
                if fp and os.path.exists(fp):
                    self.storage.add_shelf_file(fp)
                    saved_count += 1
            if saved_count > 0:
                print(f"[Global Window DropEvent]: Saved {saved_count} file(s) to File Shelf!")
                if hasattr(self, 'pill_widget'):
                    self.pill_widget.show_temp_status(f"📥 Saved {saved_count} file(s) to Shelf!")
            event.acceptProposedAction()

    def enterEvent(self, event):
        self.mouse_outside_since = None
        self.leave_timer.stop()
        self.check_force_collapse_safety()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.check_force_collapse_safety()
        super().leaveEvent(event)

    def get_stable_target_expanded_rect(self):
        """Returns the STABLE, non-shifting target expanded window bounding box with a tight 8px hover buffer."""
        from PyQt6.QtCore import QRect
        screen = QApplication.primaryScreen()
        if not screen:
            return self.frameGeometry()

        geo = screen.availableGeometry()
        pos_setting = self.settings.get("position", "top_center")
        offset_x = int(self.settings.get("offset_x", 0))
        offset_y = int(self.settings.get("offset_y", 12))

        # Tight responsive bounding box: visible card dimensions + 8px hover buffer
        buffer = 8
        card_w = self.expanded_width + (buffer * 2)
        card_h = self.expanded_height + (buffer * 2)

        win_w = self.expanded_width + (self.margin * 2)
        win_h = self.expanded_height + (self.margin * 2)

        if pos_setting == "top_left":
            x = geo.x() + offset_x + self.margin - buffer
            y = geo.y() + offset_y + self.margin - buffer
        elif pos_setting == "top_right":
            x = geo.x() + geo.width() - win_w - offset_x + self.margin - buffer
            y = geo.y() + offset_y + self.margin - buffer
        elif pos_setting == "bottom_center":
            x = geo.x() + ((geo.width() - win_w) // 2) + offset_x + self.margin - buffer
            y = geo.y() + geo.height() - win_h - offset_y + self.margin - buffer
        else:  # top_center
            x = geo.x() + ((geo.width() - win_w) // 2) + offset_x + self.margin - buffer
            y = geo.y() + offset_y + self.margin - buffer

        return QRect(x, y, card_w, card_h)

    def leaveEvent(self, event):
        if self.is_alarm_alert_active:
            print("[Collapse Check]: Leave event ignored because alarm takeover is active.", flush=True)
            return

        cursor_pos = QCursor.pos()
        from PyQt6.QtCore import QAbstractAnimation
        is_animating = hasattr(self, 'anim') and self.anim.state() == QAbstractAnimation.State.Running
        if self.is_expanded or is_animating:
            target_rect = self.get_stable_target_expanded_rect()
            if target_rect.contains(cursor_pos):
                print(f"[Collapse Check]: Leave event skipped; cursor {cursor_pos} still within STABLE bounds {target_rect}.", flush=True)
                return

        # Prevent collapse if user is actively typing in a text field
        focus_w = QApplication.focusWidget()
        if focus_w and self.isAncestorOf(focus_w) and isinstance(focus_w, (QLineEdit, QTextEdit, QPlainTextEdit, QAbstractSpinBox)):
            return

        if self.mouse_outside_since is None:
            self.mouse_outside_since = time.time()

        self.leave_timer.start(80)
        super().leaveEvent(event)

    def eventFilter(self, watched, event):
        from PyQt6.QtCore import QEvent
        et = event.type()
        if et == QEvent.Type.MouseButtonPress:
            if event.button() == Qt.MouseButton.RightButton:
                self._right_drag_active = True
                self._right_drag_start_pos = event.globalPosition().toPoint()
                self._right_drag_start_win_pos = self.pos()
                self._right_drag_distance = 0
                self.setCursor(Qt.CursorShape.ClosedHandCursor)
                return True
        elif et == QEvent.Type.MouseMove:
            if getattr(self, '_right_drag_active', False) and (event.buttons() & Qt.MouseButton.RightButton):
                delta = event.globalPosition().toPoint() - self._right_drag_start_pos
                self._right_drag_distance = delta.manhattanLength()
                self.move(self._right_drag_start_win_pos + delta)
                return True
        elif et == QEvent.Type.MouseButtonRelease:
            if getattr(self, '_right_drag_active', False) and event.button() == Qt.MouseButton.RightButton:
                self._right_drag_active = False
                self.setCursor(Qt.CursorShape.ArrowCursor)
                if getattr(self, '_right_drag_distance', 0) > 4:
                    self._save_dragged_position()
                    return True
                else:
                    # Minor right click without dragging: show context menu
                    self.show_island_context_menu(event.globalPosition().toPoint())
                    return True
        elif et == QEvent.Type.ContextMenu:
            if getattr(self, '_right_drag_distance', 0) > 4:
                return True
        elif et == QEvent.Type.KeyPress:
            if self.is_expanded:
                key = event.key()
                focus_w = QApplication.focusWidget()
                if not (focus_w and self.isAncestorOf(focus_w) and isinstance(focus_w, (QLineEdit, QTextEdit, QPlainTextEdit, QAbstractSpinBox))):
                    if key in (Qt.Key.Key_Right, Qt.Key.Key_Down):
                        cur_idx = self.stacked_widget.currentIndex()
                        next_idx = (cur_idx + 1) % max(1, len(self.active_tab_keys))
                        self.switch_tab(next_idx)
                        if 0 <= next_idx < len(self.tab_buttons):
                            self.tab_buttons[next_idx].setFocus()
                        return True
                    elif key in (Qt.Key.Key_Left, Qt.Key.Key_Up):
                        cur_idx = self.stacked_widget.currentIndex()
                        next_idx = (cur_idx - 1 + max(1, len(self.active_tab_keys))) % max(1, len(self.active_tab_keys))
                        self.switch_tab(next_idx)
                        if 0 <= next_idx < len(self.tab_buttons):
                            self.tab_buttons[next_idx].setFocus()
                        return True
        return super().eventFilter(watched, event)

    def _save_dragged_position(self):
        """Converts dragged screen coordinates to relative monitor offsets and persists them live."""
        try:
            screens = QApplication.screens()
            mon_idx = int(self.settings.get("monitor_index", 0))
            screen = screens[mon_idx] if (0 <= mon_idx < len(screens)) else QApplication.primaryScreen()
            if not screen:
                return
            geo = screen.availableGeometry()
            pos_setting = self.settings.get("position", "top_center")
            win_w = self.width()
            win_h = self.height()
            current_x = self.x()
            current_y = self.y()

            if pos_setting == "top_left":
                offset_x = current_x - geo.x()
                offset_y = current_y - geo.y()
            elif pos_setting == "top_right":
                offset_x = geo.x() + geo.width() - win_w - current_x
                offset_y = current_y - geo.y()
            elif pos_setting == "bottom_center":
                default_center_x = geo.x() + ((geo.width() - win_w) // 2)
                offset_x = current_x - default_center_x
                offset_y = geo.y() + geo.height() - win_h - current_y
            else:  # top_center
                default_center_x = geo.x() + ((geo.width() - win_w) // 2)
                offset_x = current_x - default_center_x
                offset_y = current_y - geo.y()

            self.settings.update_settings({"offset_x": int(offset_x), "offset_y": int(offset_y)})
            print(f"[Island Repositioned]: offset_x={int(offset_x)}, offset_y={int(offset_y)} saved live to preferences.", flush=True)
        except Exception as e:
            print(f"[Save Dragged Position Error]: {e}", flush=True)

    def show_island_context_menu(self, global_pt: QPoint):
        try:
            if hasattr(self, 'tray_icon') and self.tray_icon.contextMenu():
                self.tray_icon.contextMenu().popup(global_pt)
        except Exception as e:
            print(f"[Island Context Menu Error]: {e}", flush=True)

    def is_any_combo_popup_visible(self) -> bool:
        try:
            popup = QApplication.activePopupWidget()
            if popup and popup.isVisible() and popup.width() > 10 and popup.height() > 10:
                pname = popup.metaObject().className()
                if not any(ign in pname for ign in ["ToolTip", "GlobalDropOverlay", "DynamicIsland", "CollapsedPillWidget"]):
                    if popup.windowFlags() & Qt.WindowType.Popup:
                        return True

            for combo in self.findChildren(QComboBox):
                if combo and combo.view() and combo.view().isVisible():
                    return True
        except Exception:
            pass
        return False

    def expand_island(self):
        if self.is_alarm_alert_active:
            self.pill_widget.hide()
            self.dashboard_widget.hide()
            self.alarm_banner_card.show()
            if not self.is_expanded:
                self.is_expanded = True
                self.anim.stop()
                self.anim.setDuration(160)
                self.anim.setEasingCurve(QEasingCurve.Type.OutQuad)
                self.anim.setStartValue(QSize(self.current_frame_width, self.current_frame_height))
                self.anim.setEndValue(QSize(self.expanded_width, self.expanded_height))
                self.anim.start()
            return

        if not self.is_expanded:
            self.is_expanded = True
            self.pill_widget.hide()
            self.alarm_banner_card.hide()
            if hasattr(self, 'notification_banner_card'):
                self.notification_banner_card.hide()
            self.dashboard_widget.show()

            # Set keyboard focus to current tab button so arrow keys work immediately on expand without manual click
            curr_idx = self.stacked_widget.currentIndex()
            if hasattr(self, 'tab_buttons') and 0 <= curr_idx < len(self.tab_buttons):
                self.tab_buttons[curr_idx].setFocus()

            self.anim.stop()
            self.anim.setDuration(480)
            self.anim.setEasingCurve(QEasingCurve.Type.OutCubic)
            self.anim.setStartValue(QSize(self.current_frame_width, self.current_frame_height))
            self.anim.setEndValue(QSize(self.expanded_width, self.expanded_height))
            self.anim.start()

    def perform_soft_collapse(self):
        if self.is_alarm_alert_active:
            return

        if self.is_expanded:
            if self.is_any_combo_popup_visible():
                self.leave_timer.start(100)
                return

            focus_w = QApplication.focusWidget()
            if focus_w and self.isAncestorOf(focus_w) and isinstance(focus_w, (QLineEdit, QTextEdit, QPlainTextEdit, QAbstractSpinBox)):
                return

            cursor_pos = QCursor.pos()
            target_rect = self.get_stable_target_expanded_rect()
            if target_rect.contains(cursor_pos):
                if not self.dashboard_widget.isVisible():
                    self.dashboard_widget.show()
                    self.pill_widget.hide()
                return

            self.force_collapse()

    def check_force_collapse_safety(self):
        """High-frequency mouse position tracker for both smooth hover-dwell expansion and stable collapse safety."""
        cursor_pos = QCursor.pos()

        if not self.is_expanded:
            self.mouse_outside_since = None
            if self.is_alarm_alert_active or QApplication.activeModalWidget() is not None:
                self.mouse_inside_collapsed_since = None
                return

            if self.frameGeometry().contains(cursor_pos):
                if getattr(self, 'mouse_inside_collapsed_since', None) is None:
                    self.mouse_inside_collapsed_since = time.time()
                else:
                    elapsed = (time.time() - self.mouse_inside_collapsed_since) * 1000.0
                    delay = float(self.settings.get("hover_delay_ms", 400))
                    if elapsed >= delay:
                        self.mouse_inside_collapsed_since = None
                        self.expand_island()
            else:
                self.mouse_inside_collapsed_since = None
            return

        self.mouse_inside_collapsed_since = None
        if self.is_alarm_alert_active or QApplication.activeModalWidget() is not None:
            self.mouse_outside_since = None
            return

        focus_w = QApplication.focusWidget()
        if focus_w and self.isAncestorOf(focus_w) and isinstance(focus_w, (QLineEdit, QTextEdit, QPlainTextEdit, QAbstractSpinBox)):
            self.mouse_outside_since = None
            return

        target_rect = self.get_stable_target_expanded_rect()
        if not target_rect.contains(cursor_pos):
            if self.mouse_outside_since is None:
                self.mouse_outside_since = time.time()
            else:
                elapsed = time.time() - self.mouse_outside_since
                if elapsed >= 0.15:
                    if not self.is_any_combo_popup_visible():
                        self.perform_soft_collapse()
                if elapsed >= 0.8:
                    self.force_collapse()
        else:
            self.mouse_outside_since = None

    def force_collapse(self):
        """Forces dashboard collapse immediately and cleanly closes lingering popups."""
        self.mouse_outside_since = None
        self.leave_timer.stop()
        if hasattr(self, 'global_drop_overlay') and self.global_drop_overlay:
            self.global_drop_overlay.hide()

        for combo in self.findChildren(QComboBox):
            try:
                combo.hidePopup()
            except Exception:
                pass

        self.is_expanded = False
        self.dashboard_widget.hide()
        self.alarm_banner_card.hide()
        if hasattr(self, 'notification_banner_card'):
            self.notification_banner_card.hide()
        self.pill_widget.show()

        self.anim.stop()
        self.anim.setDuration(280)
        self.anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.anim.setStartValue(QSize(self.current_frame_width, self.current_frame_height))
        self.anim.setEndValue(QSize(self.collapsed_width, self.collapsed_height))
        self.anim.start()

    def init_global_hotkey(self):
        self.hotkey_emitter = HotkeySignalEmitter()
        self.hotkey_emitter.toggle_requested.connect(self.toggle_expanded_state)

        if HAS_PYNPUT:
            def on_press(key):
                try:
                    if key == pynput_keyboard.Key.f10:
                        self.hotkey_emitter.toggle_requested.emit()
                except Exception as e:
                    print(f"Hotkey listener exception: {e}")

            self.hotkey_listener = pynput_keyboard.Listener(on_press=on_press)
            self.hotkey_listener.daemon = True
            self.hotkey_listener.start()
            print("[STARTUP] Global Hotkey Listener (F10) Active")

    def toggle_expanded_state(self):
        if self.is_expanded:
            self.perform_soft_collapse()
        else:
            self.expand_island()

    def init_system_tray(self):
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return

        icon_path = os.path.join(os.path.dirname(__file__), "app_icon.png")
        icon = QIcon(icon_path) if os.path.exists(icon_path) else QApplication.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon)

        self.tray_icon = QSystemTrayIcon(icon, self)
        self.tray_icon.setToolTip("Dlives • Dynamic Island")

        tray_menu = QMenu()
        tray_menu.setStyleSheet("""
            QMenu {
                background-color: #18181b;
                color: #f4f4f5;
                border: 1px solid #27272a;
                border-radius: 8px;
                padding: 4px;
                font-family: 'Segoe UI', sans-serif;
                font-size: 11px;
            }
            QMenu::item {
                padding: 6px 16px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #38bdf8;
                color: #ffffff;
            }
        """)

        act_toggle = QAction("🏝️ Toggle Dynamic Island", self)
        act_toggle.triggered.connect(self.toggle_expanded_state)

        act_full = QAction("⚙️ Open Customization Studio", self)
        act_full.triggered.connect(self.open_full_app_window)

        act_home = QAction("🏠 Open Home Dashboard", self)
        act_home.triggered.connect(lambda: (self.expand_island(), self.switch_tab(0)))

        act_restart = QAction("🔄 Restart Dlives", self)
        act_restart.triggered.connect(self.restart_application)

        act_quit = QAction("❌ Quit Dlives", self)
        act_quit.triggered.connect(QApplication.instance().quit)

        tray_menu.addAction(act_toggle)
        tray_menu.addAction(act_full)
        tray_menu.addAction(act_home)
        tray_menu.addSeparator()
        tray_menu.addAction(act_restart)
        tray_menu.addSeparator()
        tray_menu.addAction(act_quit)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.on_tray_activated)
        self.tray_icon.show()

    def open_full_app_window(self, view_index: int = None):
        """Opens or focuses the standalone Full App Window."""
        if not self.full_app_window:
            from full_app_window import SanLivesFullAppWindow
            self.full_app_window = SanLivesFullAppWindow(self.storage, self.settings)
        if self.full_app_window.isMinimized():
            self.full_app_window.showNormal()
        if isinstance(view_index, int) and hasattr(self.full_app_window, "switch_view"):
            self.full_app_window.switch_view(view_index)
        self.full_app_window.show()
        self.full_app_window.raise_()
        self.full_app_window.activateWindow()

    def on_tray_activated(self, reason):
        if reason in (QSystemTrayIcon.ActivationReason.Trigger, QSystemTrayIcon.ActivationReason.DoubleClick):
            self.toggle_expanded_state()

    def restart_application(self):
        try:
            import subprocess
            self.close()
            subprocess.Popen([sys.executable] + sys.argv)
            QApplication.instance().quit()
        except Exception as e:
            print(f"[Restart Error]: {e}")

    def on_settings_changed(self, new_settings: dict):
        import time
        t0 = time.perf_counter()

        accent = resolve_accent_color(self.settings)
        mode = new_settings.get("theme_mode", "dark")
        print(f"[SIGNAL] DynamicIsland.on_settings_changed RECEIVED settings_changed: mode={mode}, accent={accent}", flush=True)

        t_container_0 = time.perf_counter()
        self.apply_container_style()
        t_container_ms = (time.perf_counter() - t_container_0) * 1000.0

        t_header_0 = time.perf_counter()
        self.pill_widget.apply_theme(accent, mode)
        self.alarm_banner_card.apply_theme(accent, mode)
        self.notification_banner_card.apply_theme(accent, mode)
        t_header_ms = (time.perf_counter() - t_header_0) * 1000.0

        t_tabs_0 = time.perf_counter()
        cur_tab = self.stacked_widget.currentWidget()
        tab_times = []
        if cur_tab and hasattr(cur_tab, "apply_theme"):
            tt0 = time.perf_counter()
            cur_tab.apply_theme(accent, mode)
            tt_ms = (time.perf_counter() - tt0) * 1000.0
            tab_name = cur_tab.__class__.__name__
            tab_times.append(f"{tab_name} (active): {tt_ms:.2f}ms")
        t_tabs_ms = (time.perf_counter() - t_tabs_0) * 1000.0

        # Check if tab order or visibility changed
        default_order = ["home", "control", "hardware", "shelf_clip", "calendar", "alarms", "apps", "notes", "notifs", "settings"]
        current_tab_order = tuple(new_settings.get("tab_order", default_order))
        current_visible_tabs = tuple(sorted(new_settings.get("visible_tabs", default_order)))
        if getattr(self, 'last_tab_config', None) != (current_tab_order, current_visible_tabs):
            self.rebuild_island_tabs()
        else:
            self.switch_tab(self.stacked_widget.currentIndex())

        # Only rebuild Home grid widgets when Home Module visibility toggles change
        home_flags = (
            new_settings.get("show_home_alarms", True),
            new_settings.get("show_home_timetable", True),
            new_settings.get("show_home_calendar", True),
            new_settings.get("show_home_notes", True),
            new_settings.get("show_home_now_playing", True),
            new_settings.get("show_home_notifications", True),
            new_settings.get("show_home_pomodoro", True),
            new_settings.get("show_home_dropzone", True),
        )
        t_grid_ms = 0.0
        if getattr(self, "last_home_flags", None) != home_flags:
            self.last_home_flags = home_flags
            if hasattr(self, 'tab_home'):
                t_grid_0 = time.perf_counter()
                self.tab_home.refresh_home_widgets()
                t_grid_ms = (time.perf_counter() - t_grid_0) * 1000.0

        self.update_window_position(self.current_frame_width, self.current_frame_height)
        if hasattr(self, 'tab_settings') and hasattr(self.tab_settings, 'sync_controls_from_settings'):
            self.tab_settings.sync_controls_from_settings(new_settings)
        t_total_ms = (time.perf_counter() - t0) * 1000.0

        print(f"[TIMING] --- on_settings_changed Total: {t_total_ms:.2f}ms ---", flush=True)
        print(f"[TIMING] container_style: {t_container_ms:.2f}ms | header_apply: {t_header_ms:.2f}ms | active_tab_apply: {t_tabs_ms:.2f}ms | home_grid_rebuild: {t_grid_ms:.2f}ms", flush=True)
        print(f"[TIMING] Breakdown: {', '.join(tab_times)}", flush=True)

    def init_telemetry_thread(self):
        self.telemetry_thread = TelemetryWorkerThread(interval_ms=1000, parent=self)
        self.telemetry_thread.telemetry_updated.connect(self.on_telemetry_updated)
        self.telemetry_thread.system_event_triggered.connect(self.on_system_event_triggered)
        self.telemetry_thread.start()

        self.now_playing_thread = NowPlayingWorkerThread(interval_ms=1000, parent=self)
        self.now_playing_thread.media_info_updated.connect(self.on_now_playing_updated)
        self.now_playing_thread.start()
        print("[STARTUP] Async Telemetry & Now Playing Threads Started", flush=True)

    def on_now_playing_updated(self, info: dict):
        from PyQt6.sip import isdeleted
        if isdeleted(self):
            return
        is_playing = info.get("is_playing", False)
        self.is_media_playing = is_playing
        if hasattr(self, 'pill_widget'):
            self.pill_widget.update_now_playing_state(is_playing)
        self.update_ambient_aura()

    def trigger_pill_toast_expansion(self, text: str, icon: str = "", bg_color: str = "#00e676", duration_ms: int = 3200):
        if not self.settings.get("enable_system_pill_toasts", True):
            return

        if self.is_expanded:
            if hasattr(self, 'pill_widget'):
                self.pill_widget.show_pill_toast(text=text, icon=icon, bg_color=bg_color, duration_ms=duration_ms)
            return

        msg = f"{icon} {text}".strip() if icon else text
        calc_w = max(390, min(520, 310 + len(msg) * 7))

        if hasattr(self, 'pill_widget'):
            self.pill_widget.show_pill_toast(text=text, icon=icon, bg_color=bg_color, duration_ms=duration_ms)

        # Smooth dynamic pill expansion animation
        self.anim.stop()
        self.anim.setDuration(220)
        self.anim.setEasingCurve(QEasingCurve.Type.OutBack)
        self.anim.setStartValue(QSize(self.current_frame_width, self.collapsed_height))
        self.anim.setEndValue(QSize(calc_w, self.collapsed_height))
        self.anim.start()

        def restore_pill_width():
            if not self.is_expanded:
                self.anim.stop()
                self.anim.setDuration(190)
                self.anim.setEasingCurve(QEasingCurve.Type.OutCubic)
                self.anim.setStartValue(QSize(self.current_frame_width, self.collapsed_height))
                self.anim.setEndValue(QSize(self.collapsed_width, self.collapsed_height))
                self.anim.start()

        QTimer.singleShot(duration_ms, restore_pill_width)

    def on_system_event_triggered(self, event: dict):
        text = event.get("text", "")
        icon = event.get("icon", "")
        color = event.get("color", "#00e676")
        self.trigger_pill_toast_expansion(text=text, icon=icon, bg_color=color, duration_ms=3200)

    def on_fast_clock_tick(self):
        is_12h = self.settings.get("time_format_12h", True)
        accent = resolve_accent_color(self.settings)
        self.pill_widget.update_fast_clock_and_lock_badges(is_12h=is_12h, accent_color=accent)

    def on_telemetry_updated(self, data: dict):
        from PyQt6.sip import isdeleted
        if isdeleted(self):
            return
        self.latest_telemetry = data

        # Windows Theme Sync
        if self.settings.get("sync_windows_theme", False):
            win_theme = data.get("windows_theme")
            cur_theme = self.settings.get("theme_mode", "dark")
            if win_theme and win_theme != cur_theme:
                self.settings.update_settings({"theme_mode": win_theme})

        volume = data.get('volume', 50)
        brightness = data.get('brightness', 100)
        cpu = data.get('cpu', 0.0)
        ram_dict = data.get('ram_info', {})
        ram_pct = ram_dict.get('percent', 0.0) if isinstance(ram_dict, dict) else 0.0
        battery = data.get('battery', {})
        charging = data.get('charging', False)

        # Isolated Update 1: Collapsed Pill Battery Display
        try:
            if hasattr(self, 'pill_widget'):
                self.pill_widget.update_battery_display(battery, charging)
        except Exception as e:
            print(f"[Telemetry UI Error - Pill Battery]: {e}")

        # Isolated Update 2: Control Center Tab Live Sliders & Metrics
        try:
            if hasattr(self, 'tab_control'):
                self.tab_control.update_live_metrics(volume, brightness, cpu, ram_pct)
        except Exception as e:
            print(f"[Telemetry UI Error - Control Tab]: {e}")

        # Isolated Update 3: Hardware Diagnostics Tab Live Telemetry
        try:
            if hasattr(self, 'tab_hardware'):
                self.tab_hardware.update_diagnostics_data(data)
        except Exception as e:
            print(f"[Telemetry UI Error - Hardware Tab]: {e}")

        # Update Dynamic Ambient Aura
        self.update_ambient_aura(data)

    def prepopulate_past_keys_today(self, now_dt):
        """Pre-populates triggered_keys_today on initial app startup for all entries scheduled earlier today."""
        today_str = now_dt.strftime("%Y-%m-%d")
        now_total_min = now_dt.hour * 60 + now_dt.minute
        day_abbrs = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        today_day = day_abbrs[now_dt.weekday()]

        try:
            alarms = self.storage.load_alarms()
            for alarm in alarms:
                if not alarm.get("enabled", True):
                    continue
                alarm_time = alarm.get("time", "")
                if not alarm_time:
                    continue
                a_min = -1
                try:
                    ts = str(alarm_time).strip().upper()
                    if "AM" in ts or "PM" in ts:
                        dt_parsed = datetime.strptime(ts, "%I:%M %p")
                        a_min = dt_parsed.hour * 60 + dt_parsed.minute
                    else:
                        parts = ts.split(":")
                        if len(parts) >= 2:
                            a_min = int(parts[0]) * 60 + int(parts[1])
                except Exception:
                    continue
                if a_min >= 0 and a_min < now_total_min:
                    days = alarm.get("days", [])
                    day_match = (not days) or any(str(d).lower().startswith(today_day.lower()[:3]) for d in days)
                    if day_match:
                        trigger_key = f"alarm_{alarm.get('id')}_{today_str}_{alarm_time}"
                        self.triggered_keys_today.add(trigger_key)
        except Exception as e:
            print(f"[GUI SCHEDULER PREPOPULATE ALARMS ERROR]: {e}", flush=True)

        try:
            timetable = self.storage.load_timetable()
            for entry in timetable:
                tt_time = entry.get("time", "")
                if not tt_time:
                    continue
                tt_min = -1
                try:
                    ts = str(tt_time).strip().upper()
                    if "AM" in ts or "PM" in ts:
                        dt_parsed = datetime.strptime(ts, "%I:%M %p")
                        tt_min = dt_parsed.hour * 60 + dt_parsed.minute
                    else:
                        parts = ts.split(":")
                        if len(parts) >= 2:
                            tt_min = int(parts[0]) * 60 + int(parts[1])
                except Exception:
                    continue
                if tt_min >= 0 and tt_min < now_total_min:
                    days = entry.get("days", [])
                    day_match = (not days) or any(str(d).lower().startswith(today_day.lower()[:3]) for d in days)
                    if day_match:
                        entry_id = str(entry.get("id", ""))
                        trigger_key = f"timetable_{entry_id}_{today_str}_{tt_time}"
                        self.triggered_keys_today.add(trigger_key)
        except Exception as e:
            print(f"[GUI SCHEDULER PREPOPULATE TIMETABLE ERROR]: {e}", flush=True)

    def check_scheduled_alarms_and_timetable(self):
        """Dedicated Rock-Solid Alarm & Timetable Scheduler Tick (1000ms loop with range catchup & logging)."""
        now_dt = datetime.now()
        now_str = now_dt.strftime("%H:%M")
        now_total_min = now_dt.hour * 60 + now_dt.minute
        today_str = now_dt.strftime("%Y-%m-%d")

        day_abbrs = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        today_day = day_abbrs[now_dt.weekday()]

        # Midnight Rollover / Startup Init Check
        if today_str != self.last_checked_date:
            is_initial_startup = (self.last_checked_date == "")
            self.last_checked_date = today_str
            self.triggered_keys_today.clear()
            if is_initial_startup:
                self.prepopulate_past_keys_today(now_dt)
            timetable = self.storage.load_timetable()
            dirty = False
            for entry in timetable:
                if entry.get("days") and entry.get("is_completed", False):
                    entry["is_completed"] = False
                    dirty = True
            if dirty:
                self.storage.save_timetable(timetable)
                if hasattr(self, 'tab_alarms'):
                    self.tab_alarms.load_timetable()
                if hasattr(self, 'tab_home'):
                    self.tab_home.refresh_home_widgets()

        if self.is_alarm_alert_active:
            # Active alert is holding the modal takeover card; defer checking new triggers
            return

        alarms = self.storage.load_alarms()
        timetable = self.storage.load_timetable()

        # Check Alarms
        for alarm in alarms:
            if not alarm.get('enabled', True):
                continue

            alarm_time = alarm.get('time', '')
            if not alarm_time:
                continue

            # Robust time parsing (supports 24h '14:30' and 12h '02:30 PM')
            a_min = -1
            try:
                ts = str(alarm_time).strip().upper()
                if "AM" in ts or "PM" in ts:
                    dt_parsed = datetime.strptime(ts, "%I:%M %p")
                    a_min = dt_parsed.hour * 60 + dt_parsed.minute
                else:
                    parts = ts.split(':')
                    if len(parts) >= 2:
                        a_min = int(parts[0]) * 60 + int(parts[1])
            except Exception as e:
                print(f"[ALARM TIME PARSE ERROR]: Could not parse alarm time '{alarm_time}': {e}", flush=True)
                continue

            if a_min < 0:
                continue

            diff_min = now_total_min - a_min
            # Range check: scheduled for current minute or up to 1 minute grace catchup
            if 0 <= diff_min <= 1:
                days = alarm.get('days', [])
                day_match = (not days) or any(str(d).lower().startswith(today_day.lower()[:3]) for d in days)
                if day_match:
                    trigger_key = f"alarm_{alarm.get('id')}_{today_str}_{alarm_time}"
                    if trigger_key not in self.triggered_keys_today:
                        self.triggered_keys_today.add(trigger_key)
                        label = alarm.get('label', 'Alarm')
                        sound_val = alarm.get('sound', 'system_exclamation')
                        print(f"[ALARM TRIGGER]: Scheduled={alarm_time}, SystemTime={now_dt.strftime('%H:%M:%S')} (Delta: {diff_min}m), Label='{label}' (ID: {alarm.get('id')})", flush=True)
                        self.trigger_alarm_alert(label, is_timetable=False, time_str=now_str, days=days, sound_path=sound_val)
                        return

        # Check Timetable Tasks
        for entry in timetable:
            if entry.get("is_completed", False):
                continue

            tt_time = entry.get('time', '')
            if not tt_time:
                continue

            # Robust time parsing (supports 24h '14:30' and 12h '02:30 PM')
            tt_min = -1
            try:
                ts = str(tt_time).strip().upper()
                if "AM" in ts or "PM" in ts:
                    dt_parsed = datetime.strptime(ts, "%I:%M %p")
                    tt_min = dt_parsed.hour * 60 + dt_parsed.minute
                else:
                    parts = ts.split(':')
                    if len(parts) >= 2:
                        tt_min = int(parts[0]) * 60 + int(parts[1])
            except Exception as e:
                print(f"[TIMETABLE TIME PARSE ERROR]: Could not parse timetable time '{tt_time}': {e}", flush=True)
                continue

            if tt_min < 0:
                continue

            diff_min = now_total_min - tt_min
            # Range check: scheduled for current minute or up to 1 minute grace catchup
            if 0 <= diff_min <= 1:
                days = entry.get('days', [])
                day_match = (not days) or any(str(d).lower().startswith(today_day.lower()[:3]) for d in days)
                if day_match:
                    entry_id = str(entry.get('id', ''))
                    trigger_key = f"timetable_{entry_id}_{today_str}_{tt_time}"
                    if trigger_key not in self.triggered_keys_today:
                        self.triggered_keys_today.add(trigger_key)
                        title_str = entry.get("title", "Timetable Task")
                        sound_val = entry.get('sound', 'system_exclamation')
                        print(f"[TIMETABLE TRIGGER]: Scheduled={tt_time}, SystemTime={now_dt.strftime('%H:%M:%S')} (Delta: {diff_min}m), Task='{title_str}' (ID: {entry_id})", flush=True)
                        self.trigger_alarm_alert(title_str, is_timetable=True, time_str=now_str, days=days, task_id=entry_id, sound_path=sound_val)
                        return

    def play_continuous_sound_step(self, sound_path: str = None):
        def async_sound():
            SystemMonitor.play_alarm_sound_effect(sound_path)
        threading.Thread(target=async_sound, daemon=True).start()

    def start_continuous_alarm_sound(self, sound_path: str = None):
        if sound_path and os.path.exists(sound_path) and self.media_player:
            try:
                self.media_player.stop()
                self.media_player.setSource(QUrl.fromLocalFile(sound_path))
                self.media_player.setLoops(QMediaPlayer.Loops.Infinite)
                self.media_player.play()
                print(f"[Custom Sound Alarm]: Playing continuous custom sound via QMediaPlayer: {sound_path}")
                return
            except Exception as e:
                print(f"[Custom Sound Alarm Error]: Failed QMediaPlayer playback: {e}")

        if not self.alarm_sound_timer.isActive():
            self.play_continuous_sound_step(sound_path)
            self.alarm_sound_timer.start(1200)

    def stop_alarm_sound(self):
        if hasattr(self, 'alarm_sound_timer') and self.alarm_sound_timer.isActive():
            self.alarm_sound_timer.stop()
        if hasattr(self, 'media_player') and self.media_player:
            try:
                self.media_player.stop()
            except Exception:
                pass
        try:
            import winsound
            winsound.PlaySound(None, winsound.SND_PURGE)
        except Exception:
            pass
        print("[SOUND CONTROL]: Alarm sound stopped and purged cleanly.", flush=True)

    def trigger_alarm_alert(self, title: str, is_timetable: bool = False, time_str: str = "", days: list = None, task_id: str = "", sound_path: str = None):
        self.is_alarm_alert_active = True
        self.start_continuous_alarm_sound(sound_path)

        self.pill_widget.hide()
        self.dashboard_widget.hide()
        self.alarm_banner_card.set_trigger_data(title, is_timetable, time_str, days, task_id)
        self.alarm_banner_card.show()

        if self.isHidden():
            self.show()
            self.raise_()

        # Expand island to full height for modal takeover card
        self.is_expanded = True
        self.anim.stop()
        self.anim.setStartValue(QSize(self.current_frame_width, self.current_frame_height))
        self.anim.setEndValue(QSize(self.expanded_width, self.expanded_height))
        self.anim.start()

        # Configurable Auto-Dismiss Timeout
        autodismiss_seconds = int(self.settings.get("alarm_autodismiss_seconds", 30))
        self.alarm_banner_card.start_countdown(autodismiss_seconds)
        if autodismiss_seconds > 0:
            self.auto_dismiss_timer.start(autodismiss_seconds * 1000)
        else:
            self.auto_dismiss_timer.stop()

    def on_alarm_scheduler_due(self, data: dict):
        """Invoked directly by the dedicated AlarmSchedulerWorkerThread when an alarm/timetable is due."""
        print(f"[ALARM SCHEDULER DUE]: Triggering alert for '{data.get('title')}' (is_timetable={data.get('is_timetable')})", flush=True)
        self.trigger_alarm_alert(
            title=data.get("title", "Alarm"),
            is_timetable=data.get("is_timetable", False),
            time_str=data.get("time_str", ""),
            days=data.get("days", []),
            task_id=data.get("task_id", ""),
            sound_path=data.get("sound_path", None)
        )

    def _collapse_after_modal_dismiss(self):
        """Cleanly collapses island after an alert/notification modal closes."""
        self.force_collapse()

    def dismiss_alarm_alert(self):
        self.stop_alarm_sound()
        self.is_alarm_alert_active = False
        self.auto_dismiss_timer.stop()
        self.alarm_banner_card.countdown_timer.stop()
        self.alarm_banner_card.hide()
        self._collapse_after_modal_dismiss()

    def snooze_alarm_alert(self, alarm_data: dict, minutes: int):
        self.stop_alarm_sound()
        self.is_alarm_alert_active = False
        self.auto_dismiss_timer.stop()
        self.alarm_banner_card.countdown_timer.stop()
        self.alarm_banner_card.hide()

        # Calculate Snoozed Time
        now = datetime.now()
        snooze_dt = now + timedelta(minutes=minutes)
        snooze_time_str = snooze_dt.strftime("%H:%M")

        is_tt = alarm_data.get("is_timetable", False)
        title = f"{alarm_data.get('title', 'Alarm')} (Snoozed {minutes}m)"

        if is_tt:
            timetable = self.storage.load_timetable()
            timetable.append({
                "id": f"snooze_{int(now.timestamp())}",
                "time": snooze_time_str,
                "title": title,
                "is_completed": False,
                "days": []
            })
            self.storage.save_timetable(timetable)
            self.tab_alarms.load_timetable()
        else:
            alarms = self.storage.load_alarms()
            alarms.append({
                "id": f"snooze_{int(now.timestamp())}",
                "time": snooze_time_str,
                "label": title,
                "days": [],
                "enabled": True
            })
            self.storage.save_alarms(alarms)
            self.tab_alarms.load_alarms()

        self.tab_home.refresh_home_widgets()
        self._collapse_after_modal_dismiss()

    def mark_done_alarm_alert(self, alarm_data: dict):
        print(f"[MARK DONE ALERT]: Button invoked with alarm_data: {alarm_data}", flush=True)
        self.stop_alarm_sound()
        self.is_alarm_alert_active = False
        self.auto_dismiss_timer.stop()
        self.alarm_banner_card.countdown_timer.stop()
        self.alarm_banner_card.hide()

        task_id = str(alarm_data.get("task_id", "")).strip()
        time_str = alarm_data.get("time_str", "")
        title = alarm_data.get("title", "")

        timetable = self.storage.load_timetable()
        marked = False
        for t in timetable:
            t_id = str(t.get("id", "")).strip()
            # Match by ID or fallback by time + title
            if (task_id and t_id == task_id) or (t.get("time") == time_str and t.get("title") == title):
                t["is_completed"] = True
                marked = True
                print(f"[MARK DONE ALERT]: Successfully marked task '{t.get('title')}' (id={t_id}) as is_completed=True in timetable.json", flush=True)
                break

        if marked:
            self.storage.save_timetable(timetable)
            if hasattr(self, 'tab_alarms'):
                self.tab_alarms.load_timetable()
            if hasattr(self, 'tab_home'):
                self.tab_home.refresh_home_widgets()
            print(f"[MARK DONE ALERT]: UI lists and Home widgets refreshed immediately.", flush=True)
        else:
            print(f"[MARK DONE ALERT WARNING]: Could not find matching task for id='{task_id}', title='{title}', time='{time_str}'", flush=True)

        self._collapse_after_modal_dismiss()

    def trigger_notification_popup(self, notif_data: dict):
        if not self.settings.get("notification_popup_enabled", True):
            return

        # Suppress large takeover banner during Fullscreen Gaming or Focus Assist Quiet Hours
        if self.settings.get("suppress_popups_in_fullscreen", True) and SystemMonitor.is_focus_assist_or_fullscreen_active():
            app_n = notif_data.get("app") or notif_data.get("app_name") or "Alert"
            if hasattr(self, 'pill_widget'):
                self.pill_widget.show_pill_toast(text=f"{app_n}: {notif_data.get('title', '')}", icon="🔔", bg_color="#38bdf8", duration_ms=3500)
            return

        self.is_alarm_alert_active = True

        try:
            import winsound
            winsound.MessageBeep(winsound.MB_ICONASTERISK)
        except Exception:
            pass

        self.pill_widget.hide()
        self.dashboard_widget.hide()
        if hasattr(self, 'alarm_banner_card'):
            self.alarm_banner_card.hide()

        accent = resolve_accent_color(self.settings)
        mode = self.settings.get("theme_mode", "dark")
        autodismiss = int(self.settings.get("notification_popup_autodismiss_seconds", 3))
        self.notification_banner_card.set_notification_data(notif_data, autodismiss_sec=autodismiss, accent_color=accent, mode=mode)
        self.notification_banner_card.show()

        if self.isHidden():
            self.show()
            self.raise_()

        # Expand island for notification banner takeover card
        self.is_expanded = True
        self.anim.stop()
        self.anim.setStartValue(QSize(self.current_frame_width, self.current_frame_height))
        self.anim.setEndValue(QSize(self.expanded_width, self.expanded_height))
        self.anim.start()

    def dismiss_notification_popup(self):
        self.is_alarm_alert_active = False
        if hasattr(self, 'notification_banner_card'):
            self.notification_banner_card.countdown_timer.stop()
            self.notification_banner_card.hide()
        self._collapse_after_modal_dismiss()

    def on_notification_popup_open(self, notif_data: dict):
        self.dismiss_notification_popup()
        self.expand_island()
        self.switch_tab(9)  # Switch to Notifications Tab

    def check_incoming_priority_notifications(self):
        if not self.settings.get("notification_popup_enabled", True):
            return
        if self.is_alarm_alert_active or self.is_expanded:
            return

        priority_apps = [a.lower().strip() for a in self.settings.get("popup_notification_apps", []) if a.strip()]
        if not priority_apps:
            return

        try:
            res = SystemMonitor.get_windows_notifications()
            items = res.get("notifications", [])
            for notif in items:
                n_id = notif.get("id")
                if not n_id:
                    continue
                if n_id not in self.seen_notification_ids:
                    self.seen_notification_ids.add(n_id)
                    app_name = (notif.get("app") or notif.get("app_name") or "").lower()
                    if any(p in app_name for p in priority_apps):
                        self.trigger_notification_popup(notif)
                        break
        except Exception:
            pass

    def closeEvent(self, event):
        try:
            if hasattr(self, 'telemetry_thread') and self.telemetry_thread:
                self.telemetry_thread.stop()
            if hasattr(self, 'now_playing_thread') and self.now_playing_thread:
                self.now_playing_thread.stop()
            if hasattr(self, 'priority_notif_thread') and self.priority_notif_thread:
                self.priority_notif_thread.stop()
            if hasattr(self, 'safety_net_timer') and self.safety_net_timer:
                self.safety_net_timer.stop()
            if hasattr(self, 'scheduler_timer') and self.scheduler_timer:
                self.scheduler_timer.stop()
            if hasattr(self, 'leave_timer') and self.leave_timer:
                self.leave_timer.stop()
        except Exception as e:
            print(f"[DynamicIsland Close Exception]: {e}")
        super().closeEvent(event)


class ScreenshotAndClipboardMonitor(QObject):
    """Monitors system clipboard for copied text AND newly captured screenshots (Win+Shift+S / Snipping Tool),
    as well as watching the Windows Screenshots directory to auto-save all snips/screenshots to the File Shelf."""

    def __init__(self, storage: StorageManager, pill_widget=None, parent=None):
        super().__init__(parent)
        self.storage = storage
        self.pill_widget = pill_widget
        self.clipboard = QApplication.clipboard()
        self.clipboard.dataChanged.connect(self.on_clipboard_changed)
        self._last_text = ""
        self._recent_hashes = {}

        # Ensure dedicated local screenshots directory
        self.local_screenshots_dir = os.path.join(self.storage.base_dir, "screenshots")
        os.makedirs(self.local_screenshots_dir, exist_ok=True)

        # QFileSystemWatcher for Windows default & OneDrive Screenshots folders
        self.win_screenshots_dirs = [
            os.path.join(os.path.expanduser("~"), "Pictures", "Screenshots"),
            os.path.join(os.path.expanduser("~"), "OneDrive", "Pictures", "Screenshots")
        ]
        self.file_watcher = QFileSystemWatcher(self)
        for sdir in self.win_screenshots_dirs:
            try:
                os.makedirs(sdir, exist_ok=True)
                self.file_watcher.addPath(sdir)
                print(f"[Screenshot Monitor]: Watching Windows Screenshots folder: {sdir}", flush=True)
            except Exception as e:
                print(f"[Screenshot Monitor Folder Add Error]: {e}", flush=True)
        self.file_watcher.directoryChanged.connect(self.on_folder_changed)

    def on_clipboard_changed(self):
        try:
            mime = self.clipboard.mimeData()
            if not mime:
                return

            # 1. Check for Screenshot Image in Clipboard (Win+Shift+S / Snipping Tool)
            if mime.hasImage():
                img = self.clipboard.image()
                if not img.isNull() and img.width() > 10 and img.height() > 10:
                    self.save_snipped_image(img)
                    return

            # 2. Check for Text Snippets
            if mime.hasText():
                text = mime.text()
                if text and text != self._last_text and len(text.strip()) > 0:
                    self._last_text = text
                    self.storage.add_clipboard_entry(text)
        except Exception as e:
            print(f"[Clipboard/Screenshot Monitor Exception]: {e}", flush=True)

    def save_snipped_image(self, qimage: QImage):
        try:
            now = time.time()
            ptr = qimage.bits()
            if ptr is None:
                return
            try:
                sample_bytes = bytes(ptr[:min(qimage.sizeInBytes(), 65536)])
            except Exception:
                sample_bytes = f"{qimage.width()}_{qimage.height()}_{qimage.depth()}_{qimage.sizeInBytes()}".encode()
            img_hash = hashlib.md5(sample_bytes).hexdigest()

            # Debounce duplicate clipboard triggers within 6 seconds
            if img_hash in self._recent_hashes:
                if now - self._recent_hashes[img_hash] < 6.0:
                    return
            self._recent_hashes[img_hash] = now
            self._recent_hashes = {h: ts for h, ts in self._recent_hashes.items() if now - ts < 30.0}

            timestamp_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            filename = f"Screenshot_{timestamp_str}.png"
            file_path = os.path.join(self.local_screenshots_dir, filename)

            if qimage.save(file_path, "PNG"):
                print(f"[SCREENSHOT AUTO-SAVED TO SHELF]: {file_path}", flush=True)
                self.storage.add_shelf_file(file_path)
                if self.pill_widget:
                    self.pill_widget.show_temp_status("📸 Screenshot saved to Shelf!")
        except Exception as e:
            print(f"[Save Snipped Image Error]: {e}", flush=True)

    def on_folder_changed(self, path: str):
        try:
            if not os.path.exists(path):
                return
            files = [os.path.join(path, f) for f in os.listdir(path) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
            if not files:
                return
            newest_file = max(files, key=os.path.getmtime)
            mtime = os.path.getmtime(newest_file)
            now = time.time()

            if now - mtime < 5.0:
                file_size = os.path.getsize(newest_file)
                file_sig = f"{os.path.basename(newest_file)}_{file_size}"
                if file_sig in self._recent_hashes:
                    if now - self._recent_hashes[file_sig] < 6.0:
                        return
                self._recent_hashes[file_sig] = now

                print(f"[SCREENSHOT FOLDER AUTO-SAVED TO SHELF]: {newest_file}", flush=True)
                self.storage.add_shelf_file(newest_file)
                if self.pill_widget:
                    self.pill_widget.show_temp_status("📸 Screenshot saved to Shelf!")
        except Exception as e:
            print(f"[Screenshot Folder Watcher Error]: {e}", flush=True)


_SINGLE_INSTANCE_MUTEX = None

def ensure_single_instance() -> bool:
    """Uses a Win32 Named Mutex to prevent duplicates and restores the existing window if already open."""
    global _SINGLE_INSTANCE_MUTEX
    try:
        ERROR_ALREADY_EXISTS = 183
        _SINGLE_INSTANCE_MUTEX = ctypes.windll.kernel32.CreateMutexW(None, False, "Local\\Dlives_DynamicIsland_SingleInstance_Mutex")
        last_err = ctypes.windll.kernel32.GetLastError()
        if last_err == ERROR_ALREADY_EXISTS:
            try:
                hwnd = ctypes.windll.user32.FindWindowW(None, "Dlives")
                if hwnd:
                    ctypes.windll.user32.ShowWindow(hwnd, 9)  # SW_RESTORE
                    ctypes.windll.user32.SetForegroundWindow(hwnd)
            except Exception:
                pass
            return False
        return True
    except Exception:
        return True


def main():
    if not ensure_single_instance():
        print("[SingleInstance] Another instance of Dlives is already running. Existing window focused.", flush=True)
        sys.exit(0)

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.setApplicationName("Dlives")
    app.setApplicationDisplayName("Dlives")

    # Clean Segoe UI Font for crisp, uncompressed text rendering
    app_font = QFont("Segoe UI", 9)
    app.setFont(app_font)

    island = DynamicIsland()
    island.setWindowTitle("Dlives")
    app.aboutToQuit.connect(island.storage.flush_dirty_notes)
    app.aboutToQuit.connect(island.settings.flush_save)
    clip_monitor = ScreenshotAndClipboardMonitor(island.storage, island.pill_widget, island)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
