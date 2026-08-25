import os
import math
import uuid
import shutil
import tempfile
import psutil
import subprocess
import webbrowser
import winsound
import threading
import ctypes
from datetime import datetime, date, timedelta
import calendar as pycalendar
from PyQt6.QtCore import Qt, QTime, QDate, QTimer, QUrl, pyqtSignal, QRectF, QPointF, QSize, QObject, QEvent, QPropertyAnimation, QEasingCurve, QAbstractAnimation, pyqtProperty, QThread, QMimeData, QPoint
from PyQt6.QtGui import QColor, QPixmap, QIcon, QDragEnterEvent, QDragMoveEvent, QDropEvent, QTextCharFormat, QFont, QPainter, QPainterPath, QPen, QBrush, QLinearGradient, QRadialGradient, QDrag, QFontMetrics
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QLineEdit,
    QPushButton, QListWidget, QListWidgetItem, QCheckBox,
    QTextEdit, QSlider, QProgressBar, QComboBox, QSpinBox,
    QGraphicsDropShadowEffect, QFrame, QTimeEdit, QFileDialog,
    QApplication, QScrollArea, QGridLayout, QMessageBox, QInputDialog, QDialog,
    QFormLayout, QDoubleSpinBox, QStackedWidget, QAbstractItemView, QSizePolicy, QMenu
)
from storage_manager import StorageManager
from settings_manager import SettingsManager
from system_monitor import SystemMonitor

# DUAL ACCENT PALETTES (Dark Mode Vivid vs Light Mode Deep/High-Contrast)
ACCENT_PALETTES = {
    "sky_blue": {"name": "Sky Blue", "dark": "#38bdf8", "light": "#0284c7"},
    "teal": {"name": "Teal", "dark": "#2dd4bf", "light": "#0d9488"},
    "gold": {"name": "Gold", "dark": "#fbbf24", "light": "#d97706"},
    "coral": {"name": "Coral", "dark": "#fb923c", "light": "#ea580c"},
    "purple": {"name": "Purple", "dark": "#a78bfa", "light": "#7c3aed"},
    "emerald": {"name": "Emerald Green", "dark": "#34d399", "light": "#059669"},
    "hot_pink": {"name": "Hot Pink", "dark": "#f472b6", "light": "#db2777"},
    "dark_onyx": {"name": "Dark Onyx", "dark": "#94a3b8", "light": "#1e293b"},
    "slate": {"name": "Slate Gray", "dark": "#a1a1aa", "light": "#3f3f46"},
    "silver": {"name": "Silver Gray", "dark": "#e2e8f0", "light": "#334155"},
    "orchid": {"name": "Orchid Purple", "dark": "#c084fc", "light": "#9333ea"},
    "mint": {"name": "Mint Green", "dark": "#4ade80", "light": "#16a34a"}
}

def get_accent_text_color(accent_hex: str) -> str:
    """Returns dynamic high-contrast dark (#090d16) or white (#ffffff) based on accent perceptual luminance."""
    try:
        c = QColor(accent_hex)
        # Standard ITU-R BT.601 perceptual luminance formula
        lum = (0.299 * c.red() + 0.587 * c.green() + 0.114 * c.blue())
        return "#090d16" if lum > 175 else "#ffffff"
    except Exception:
        return "#ffffff"

def resolve_accent_color(settings: SettingsManager) -> str:
    """Resolves live accent hex based on settings accent identity and theme mode."""
    identity = settings.get("accent_identity", "sky_blue") if settings else "sky_blue"
    mode = settings.get("theme_mode", "dark") if settings else "dark"
    if identity in ACCENT_PALETTES:
        return ACCENT_PALETTES[identity].get(mode, ACCENT_PALETTES[identity]["dark"])
    return settings.get("accent_color", "#38bdf8") if settings else "#38bdf8"

def get_accent_tinted_logo(accent_color: str, mode: str = "dark", size: int = 26, custom_path: str = "") -> QPixmap:
    """Returns a transparent-background logo of the user's custom stylized 'D' emblem tinted in the active accent color."""
    if custom_path and os.path.exists(custom_path):
        return QPixmap(custom_path).scaled(size, size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)

    logo_fname = "san_lives_logo_light.png" if mode == "light" else "san_lives_logo_dark.png"
    logo_path = os.path.join(os.path.dirname(__file__), "assets", logo_fname)
    if not os.path.exists(logo_path):
        logo_path = os.path.join(os.path.dirname(__file__), "assets", "san_lives_logo.png")
    
    if os.path.exists(logo_path):
        src_pixmap = QPixmap(logo_path).scaled(size, size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        if not src_pixmap.isNull():
            tinted = QPixmap(src_pixmap.size())
            tinted.fill(Qt.GlobalColor.transparent)

            painter = QPainter(tinted)
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.drawPixmap(0, 0, src_pixmap)

            # Tint ONLY the custom stylized 'D' emblem shape with accent color preserving alpha mask
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
            accent_qcol = QColor(accent_color)
            painter.fillRect(tinted.rect(), accent_qcol)
            painter.end()
            return tinted

    # Fallback vector-drawn 'D' alphabet
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

    accent_qcol = QColor(accent_color)
    font = QFont("Segoe UI", -1, QFont.Weight.Black)
    font.setPixelSize(int(size * 0.86))
    painter.setFont(font)

    rect = QRectF(0, 0, size, size)
    shadow_col = QColor(0, 0, 0, 160) if mode == "dark" else QColor(0, 0, 0, 50)
    painter.setPen(shadow_col)
    painter.drawText(rect.translated(1, 1.5), Qt.AlignmentFlag.AlignCenter, "D")

    painter.setPen(accent_qcol)
    painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, "D")
    painter.end()

    return pix

# CATEGORY ACCENT COLOR PALETTES FOR HOME CARDS
CATEGORY_ACCENTS = {
    "alarms": {"dark": "#f97316", "light": "#c2410c"},     # Coral / Red-Orange
    "timetable": {"dark": "#38bdf8", "light": "#0284c7"},  # Sky Blue
    "calendar": {"dark": "#a855f7", "light": "#7e22ce"},   # Purple
    "notes": {"dark": "#eab308", "light": "#ca8a04"},      # Amber / Gold
    "dropzone": {"dark": "#10b981", "light": "#15803d"}    # Emerald Green
}

# CENTRALIZED DUAL THEME PALETTE ARCHITECTURE
THEME_PALETTES = {
    "dark": {
        "bg_rgb": (8, 10, 16),
        "container_border": QColor(255, 255, 255, 35),
        "card_bg": "rgba(255, 255, 255, 0.04)",
        "card_border": "rgba(255, 255, 255, 0.10)",
        "text_primary": "#ffffff",
        "text_secondary": "#cbd5e1",
        "text_muted": "#64748b",
        "input_bg": "rgba(255, 255, 255, 0.06)",
        "input_border": "rgba(255, 255, 255, 0.14)",
        "list_item_bg": "rgba(255, 255, 255, 0.04)",
        "list_item_hover": "rgba(255, 255, 255, 0.08)",
        "list_item_border": "rgba(255, 255, 255, 0.10)",
        "combo_popup_bg": "#0c0e15",
        "sub_btn_bg": "rgba(255, 255, 255, 0.06)",
        "sub_btn_text": "#ffffff",
        "sub_btn_border": "rgba(255, 255, 255, 0.12)"
    },
    "light": {
        "bg_rgb": (248, 250, 252),
        "container_border": QColor(0, 0, 0, 45),
        "card_bg": "rgba(0, 0, 0, 0.05)",
        "card_border": "rgba(0, 0, 0, 0.15)",
        "text_primary": "#0f172a",
        "text_secondary": "#1e293b",
        "text_muted": "#475569",
        "input_bg": "rgba(0, 0, 0, 0.06)",
        "input_border": "rgba(0, 0, 0, 0.18)",
        "list_item_bg": "rgba(0, 0, 0, 0.04)",
        "list_item_hover": "rgba(0, 0, 0, 0.08)",
        "list_item_border": "rgba(0, 0, 0, 0.12)",
        "combo_popup_bg": "#ffffff",
        "sub_btn_bg": "rgba(0, 0, 0, 0.06)",
        "sub_btn_text": "#0f172a",
        "sub_btn_border": "rgba(0, 0, 0, 0.12)"
    }
}

def format_display_time(now_dt: datetime, is_12h: bool = True) -> str:
    """Formats current datetime cleanly for 12h (5:58:25 PM) or 24h (17:58:25) mode."""
    if is_12h:
        hour_12 = now_dt.strftime("%I").lstrip("0")
        if not hour_12:
            hour_12 = "12"
        return f"{hour_12}:" + now_dt.strftime("%M:%S %p")
    else:
        return now_dt.strftime("%H:%M:%S")

def format_alarm_time(time_24h_str: str, is_12h: bool = True) -> str:
    """Converts canonical 24h 'HH:MM' string into clean 12h 'h:mm AM/PM' or 24h 'HH:MM'."""
    try:
        parts = time_24h_str.split(":")
        h = int(parts[0])
        m = int(parts[1].split()[0])
        if is_12h:
            ampm = "AM" if h < 12 else "PM"
            h_12 = h % 12
            if h_12 == 0:
                h_12 = 12
            return f"{h_12}:{m:02d} {ampm}"
        else:
            return f"{h:02d}:{m:02d}"
    except Exception:
        return time_24h_str

def format_mmss(seconds: int) -> str:
    """Formats integer seconds into clean 'm:ss' timestamp string (e.g. 145 -> '2:25')."""
    if seconds <= 0:
        return "0:00"
    m = seconds // 60
    s = seconds % 60
    return f"{m}:{s:02d}"

class ElidedLabel(QLabel):
    """Custom QLabel that elides overflowing text with an ellipsis (...) according to available width
    and provides a tooltip with the complete unclipped text."""
    def __init__(self, text: str = "", parent=None):
        super().__init__(parent)
        self._full_text = str(text) if text is not None else ""
        self.setToolTip(self._full_text)
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.setMinimumWidth(0)
        self._update_elided()

    def setText(self, text: str):
        self._full_text = str(text) if text is not None else ""
        self.setToolTip(self._full_text)
        self._update_elided()

    def text(self) -> str:
        return self._full_text

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_elided()

    def _update_elided(self):
        if not self._full_text:
            super().setText("")
            return
        fm = self.fontMetrics()
        w = max(10, self.width() - 2)
        elided = fm.elidedText(self._full_text, Qt.TextElideMode.ElideRight, w)
        super().setText(elided)

class NoWheelSlider(QSlider):
    """QSlider that ignores mouse wheel events so parent scroll views scroll smoothly without accidental value changes."""
    def wheelEvent(self, event):
        event.ignore()

class NoWheelSpinBox(QSpinBox):
    """QSpinBox that ignores mouse wheel events when hovered to prevent scroll hijacking."""
    def wheelEvent(self, event):
        event.ignore()

class CustomSpinBox(NoWheelSpinBox):
    """Custom SpinBox that ignores wheel scroll events to prevent page scroll hijacking."""
    pass

class WheelColumnWidget(QWidget):
    """Single vertical wheel column (HH, MM, AM/PM) supporting wheel scroll, touch/drag scroll, wraparound, and smooth snapping animation."""
    valueChanged = pyqtSignal()

    def __init__(self, items: list, is_loop: bool = True, parent=None):
        super().__init__(parent)
        self.items = [str(x) for x in items]
        self.is_loop = is_loop
        self.selected_index = 0
        self._scroll_offset = 0.0
        self._accumulated_delta = 0
        self.item_height = 24
        self.setFixedSize(44, 72)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self.theme_mode = "dark"
        self.accent_color = "#38bdf8"

        self.anim = QPropertyAnimation(self, b"scroll_offset_prop")
        self.anim.setDuration(180)
        self.anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        self.dragging = False
        self.drag_start_y = 0
        self.drag_start_offset = 0.0

    @pyqtProperty(float)
    def scroll_offset_prop(self) -> float:
        return self._scroll_offset

    @scroll_offset_prop.setter
    def scroll_offset_prop(self, val: float):
        self._scroll_offset = val
        self.update()

    def apply_theme(self, accent_color: str, mode: str = "dark"):
        self.accent_color = accent_color
        self.theme_mode = mode
        self.update()

    def get_selected_item(self) -> str:
        if not self.items:
            return ""
        idx = self.selected_index % len(self.items)
        return self.items[idx]

    def set_selected_item(self, val: str):
        val_str = str(val)
        if val_str in self.items:
            self.selected_index = self.items.index(val_str)
            self._scroll_offset = 0.0
            self._accumulated_delta = 0
            self.update()

    def set_items(self, items: list, default_val: str = None):
        self.items = [str(x) for x in items]
        if default_val and str(default_val) in self.items:
            self.selected_index = self.items.index(str(default_val))
        else:
            self.selected_index = min(self.selected_index, len(self.items) - 1) if self.items else 0
        self._scroll_offset = 0.0
        self._accumulated_delta = 0
        self.update()

    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        if delta == 0:
            return

        self._accumulated_delta += delta

        # Mouse wheel standard notch is 120 units. Touchpads emit rapid micro-deltas (e.g. 8, 15).
        # Accumulate until threshold (120) is reached to prevent hyper-speed touchpad jumping.
        if abs(self._accumulated_delta) < 120:
            event.accept()
            return

        steps = int(self._accumulated_delta / 120)
        self._accumulated_delta -= (steps * 120)

        self.anim.stop()
        n = len(self.items)
        if not n:
            event.accept()
            return

        if steps > 0:
            # Scrolling UP moves back in sequence
            if self.is_loop:
                self.selected_index = (self.selected_index - steps) % n
            else:
                self.selected_index = max(0, self.selected_index - steps)
        else:
            # Scrolling DOWN moves forward in sequence
            if self.is_loop:
                self.selected_index = (self.selected_index - steps) % n
            else:
                self.selected_index = min(n - 1, self.selected_index - steps)

        # Correct direction: scrolling UP moves previous item DOWN into center (+0.5)
        # scrolling DOWN moves next item UP into center (-0.5)
        self._scroll_offset = 0.5 if steps > 0 else -0.5
        self.anim.setStartValue(self._scroll_offset)
        self.anim.setEndValue(0.0)
        self.anim.start()
        self.valueChanged.emit()
        event.accept()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = True
            self._accumulated_delta = 0
            self.press_pos_y = event.y()
            self.drag_start_y = event.y()
            self.drag_start_offset = self._scroll_offset
            if self.anim.state() == QAbstractAnimation.State.Running:
                self.anim.stop()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.dragging:
            dy = event.y() - self.drag_start_y
            self._scroll_offset = self.drag_start_offset - (dy / self.item_height)
            self.update()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.dragging and event.button() == Qt.MouseButton.LeftButton:
            self.dragging = False
            n = len(self.items)
            if n > 0:
                total_dy = abs(event.y() - getattr(self, 'press_pos_y', event.y()))
                if total_dy < 4:
                    # Direct click on an offset number item
                    cy = self.height() / 2.0
                    click_offset = int(round((event.y() - cy) / float(self.item_height)))
                    if click_offset != 0:
                        if self.is_loop:
                            self.selected_index = (self.selected_index + click_offset) % n
                        else:
                            self.selected_index = max(0, min(n - 1, self.selected_index + click_offset))
                        self._scroll_offset = -float(click_offset)

                    self.anim.setStartValue(self._scroll_offset)
                    self.anim.setEndValue(0.0)
                    self.anim.start()
                    self.valueChanged.emit()
                else:
                    # Drag gesture snap
                    steps = int(round(self._scroll_offset))
                    if steps != 0:
                        if self.is_loop:
                            self.selected_index = (self.selected_index + steps) % n
                        else:
                            self.selected_index = max(0, min(n - 1, self.selected_index + steps))
                        self._scroll_offset -= steps

                    self.anim.setStartValue(self._scroll_offset)
                    self.anim.setEndValue(0.0)
                    self.anim.start()
                    self.valueChanged.emit()
        super().mouseReleaseEvent(event)

    def paintEvent(self, event):
        painter = QPainter()
        if not painter.begin(self):
            return
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = float(self.width())
        h = float(self.height())
        pal = THEME_PALETTES.get(self.theme_mode, THEME_PALETTES["dark"])
        n = len(self.items)
        if not n:
            painter.end()
            return

        cy = h / 2.0
        ih = float(self.item_height)

        # 1. Clear, high-contrast selection band behind centered value
        sel_rect = QRectF(2, cy - ih / 2.0, w - 4, ih)
        band_bg = QColor(pal["input_bg"])
        band_border = QColor(self.accent_color)
        band_border.setAlpha(180)

        painter.setBrush(QBrush(band_bg))
        painter.setPen(QPen(band_border, 1.5))
        painter.drawRoundedRect(sel_rect, 5.0, 5.0)

        # 2. Draw vertical wheel numbers centered around selected_index + scroll_offset
        for offset_i in range(-2, 3):
            item_idx_raw = self.selected_index + offset_i
            if self.is_loop:
                item_idx = item_idx_raw % n
            else:
                if item_idx_raw < 0 or item_idx_raw >= n:
                    continue
                item_idx = item_idx_raw

            val_str = self.items[item_idx]
            item_y = cy + (offset_i - self._scroll_offset) * ih
            dist = abs(item_y - cy)

            if dist < ih / 2.0:
                font_sz = 12.0
                font_wt = QFont.Weight.ExtraBold
                txt_color = QColor(self.accent_color)
            elif dist < ih * 1.5:
                font_sz = 9.5
                font_wt = QFont.Weight.Medium
                txt_color = QColor(pal["text_secondary"])
                txt_color.setAlpha(160)
            else:
                font_sz = 8.5
                font_wt = QFont.Weight.Normal
                txt_color = QColor(pal["text_muted"])
                txt_color.setAlpha(70)

            item_rect = QRectF(0, item_y - ih / 2.0, w, ih)
            painter.setFont(QFont("Segoe UI", int(font_sz), font_wt))
            painter.setPen(txt_color)
            painter.drawText(item_rect, Qt.AlignmentFlag.AlignCenter, val_str)


class WheelTimePickerWidget(QWidget):
    """Modern Vertical Scroll-Wheel Time Picker supporting 12h (HH:MM AM/PM) and 24h (HH:MM) modes."""
    timeChanged = pyqtSignal(str)

    def __init__(self, is_12h: bool = True, parent=None):
        super().__init__(parent)
        self.is_12h = is_12h
        self.theme_mode = "dark"
        self.accent_color = "#38bdf8"
        self.init_ui()

    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(4)

        hours_12 = [f"{i:02d}" for i in range(1, 13)]
        hours_24 = [f"{i:02d}" for i in range(0, 24)]
        minutes = [f"{i:02d}" for i in range(0, 60)]

        init_hours = hours_12 if self.is_12h else hours_24
        self.col_hour = WheelColumnWidget(init_hours, is_loop=True)
        self.lbl_colon = QLabel(":")
        self.lbl_colon.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.col_min = WheelColumnWidget(minutes, is_loop=True)
        self.col_ampm = WheelColumnWidget(["AM", "PM"], is_loop=True)

        self.col_hour.valueChanged.connect(self.on_val_changed)
        self.col_min.valueChanged.connect(self.on_val_changed)
        self.col_ampm.valueChanged.connect(self.on_val_changed)

        layout.addWidget(self.col_hour)
        layout.addWidget(self.lbl_colon)
        layout.addWidget(self.col_min)
        layout.addWidget(self.col_ampm)

        if not self.is_12h:
            self.col_ampm.hide()

    def set_12h_format(self, is_12h: bool):
        if self.is_12h == is_12h:
            return
        cur_24h = self.get_time_24h()
        self.is_12h = is_12h
        hours = [f"{i:02d}" for i in range(1, 13)] if is_12h else [f"{i:02d}" for i in range(0, 24)]
        self.col_hour.set_items(hours)
        if is_12h:
            self.col_ampm.show()
        else:
            self.col_ampm.hide()
        self.set_time_24h(cur_24h)

    def apply_theme(self, accent_color: str, mode: str = "dark"):
        self.accent_color = accent_color
        self.theme_mode = mode
        self.lbl_colon.setStyleSheet(f"color: {accent_color}; font-size: 14px; font-weight: 800; background: transparent;")
        for col in (self.col_hour, self.col_min, self.col_ampm):
            col.apply_theme(accent_color, mode)

    def get_time_24h(self) -> str:
        try:
            h_str = self.col_hour.get_selected_item()
            m_str = self.col_min.get_selected_item()
            h = int(h_str) if h_str else 0
            m = int(m_str) if m_str else 0

            if self.is_12h:
                ampm = self.col_ampm.get_selected_item()
                if ampm == "PM" and h < 12:
                    h += 12
                elif ampm == "AM" and h == 12:
                    h = 0

            return f"{h:02d}:{m:02d}"
        except Exception:
            return "00:00"

    def set_time_24h(self, time_str: str):
        try:
            parts = time_str.split(":")
            h = int(parts[0])
            m = int(parts[1].split()[0])

            if self.is_12h:
                ampm = "AM" if h < 12 else "PM"
                h_12 = h % 12
                if h_12 == 0:
                    h_12 = 12
                self.col_hour.set_selected_item(f"{h_12:02d}")
                self.col_min.set_selected_item(f"{m:02d}")
                self.col_ampm.set_selected_item(ampm)
            else:
                self.col_hour.set_selected_item(f"{h:02d}")
                self.col_min.set_selected_item(f"{m:02d}")
        except Exception as e:
            print(f"[WheelTimePicker set_time_24h error]: {e}")

    def on_val_changed(self):
        self.timeChanged.emit(self.get_time_24h())

class NoWheelDoubleSpinBox(QDoubleSpinBox):
    """QDoubleSpinBox that ignores mouse wheel events when hovered to prevent scroll hijacking."""
    def wheelEvent(self, event):
        event.ignore()

class NoWheelComboBox(QComboBox):
    """QComboBox that ignores mouse wheel events when closed/hovered so page scrolling remains smooth."""
    def wheelEvent(self, event):
        if not self.view() or not self.view().isVisible():
            event.ignore()
        else:
            super().wheelEvent(event)

class ContainerFrame(QFrame):
    """Smooth Sub-Pixel Antialiased OLED Glass Container Frame supporting Light & Dark Mode, Dynamic Ambient Aura, and Subtle Brand Watermark."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.bg_opacity = 0.90
        self.corner_radius = 20
        self.accent_color = "#38bdf8"
        self.theme_mode = "dark"
        self.aura_state = "idle"
        self.watermark_pixmap = None
        
        wm_path = os.path.join(os.path.dirname(__file__), "assets", "san_lives_watermark.png")
        if os.path.exists(wm_path):
            self.watermark_pixmap = QPixmap(wm_path)

    def set_style_properties(self, bg_opacity: float, corner_radius: int, accent_color: str, theme_mode: str = "dark"):
        self.bg_opacity = bg_opacity
        self.corner_radius = corner_radius
        self.accent_color = accent_color
        self.theme_mode = theme_mode
        self.update()

    def set_aura_state(self, state: str):
        if self.aura_state != state:
            self.aura_state = state
            self.update()

    def paintEvent(self, event):
        painter = QPainter()
        if not painter.begin(self):
            return
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = float(self.width())
        h = float(self.height())
        if w <= 4.0 or h <= 4.0:
            painter.end()
            return

        pal = THEME_PALETTES.get(self.theme_mode, THEME_PALETTES["dark"])
        r, g, b = pal["bg_rgb"]
        is_dark = (self.theme_mode == "dark")

        rect = QRectF(0.5, 0.5, w - 1.0, h - 1.0)
        cr = float(self.corner_radius)
        path = QPainterPath()
        path.addRoundedRect(rect, cr, cr)

        # ----------------------------------------------------
        # 1. Multi-Stop Frosted Translucent Base Fill (Sub-Surface Volume)
        # ----------------------------------------------------
        base_grad = QLinearGradient(0.0, 0.0, 0.0, h)
        alpha_int = int(self.bg_opacity * (248 if is_dark else 248))
        if is_dark:
            base_grad.setColorAt(0.0, QColor(r + 6, g + 8, b + 12, alpha_int))
            base_grad.setColorAt(0.35, QColor(r + 2, g + 3, b + 6, int(alpha_int * 0.98)))
            base_grad.setColorAt(1.0, QColor(r, g, b, alpha_int))
        else:
            base_grad.setColorAt(0.0, QColor(255, 255, 255, alpha_int))
            base_grad.setColorAt(0.35, QColor(246, 249, 254, int(alpha_int * 0.98)))
            base_grad.setColorAt(1.0, QColor(238, 242, 250, alpha_int))
        painter.fillPath(path, QBrush(base_grad))

        # ----------------------------------------------------
        # 2. Subtle Accent Chroma Tint Wash (4-7% ambient chromatic infusion)
        # ----------------------------------------------------
        accent_color_obj = QColor(self.accent_color)
        accent_wash = QLinearGradient(0.0, 0.0, w, h)
        tint_alpha = 10 if is_dark else 16
        accent_wash.setColorAt(0.0, QColor(accent_color_obj.red(), accent_color_obj.green(), accent_color_obj.blue(), tint_alpha))
        accent_wash.setColorAt(0.5, QColor(accent_color_obj.red(), accent_color_obj.green(), accent_color_obj.blue(), int(tint_alpha * 0.35)))
        accent_wash.setColorAt(1.0, QColor(accent_color_obj.red(), accent_color_obj.green(), accent_color_obj.blue(), int(tint_alpha * 0.10)))
        painter.fillPath(path, QBrush(accent_wash))

        # ----------------------------------------------------
        # 3. Ambient Diagonal Specular Sheen (35° ambient light sweep)
        # ----------------------------------------------------
        specular_diagonal = QLinearGradient(0.0, 0.0, w * 0.70, h * 0.45)
        if is_dark:
            specular_diagonal.setColorAt(0.0, QColor(255, 255, 255, 26))
            specular_diagonal.setColorAt(0.30, QColor(255, 255, 255, 8))
            specular_diagonal.setColorAt(0.70, QColor(255, 255, 255, 2))
            specular_diagonal.setColorAt(1.0, QColor(255, 255, 255, 0))
        else:
            specular_diagonal.setColorAt(0.0, QColor(255, 255, 255, 200))
            specular_diagonal.setColorAt(0.30, QColor(255, 255, 255, 80))
            specular_diagonal.setColorAt(0.70, QColor(255, 255, 255, 20))
            specular_diagonal.setColorAt(1.0, QColor(255, 255, 255, 0))
        painter.fillPath(path, QBrush(specular_diagonal))

        # ----------------------------------------------------
        # 4. Subtle Brand Watermark in Expanded Frame
        # ----------------------------------------------------
        wm_pix = None
        wm_opacity = 0.04
        if hasattr(self, 'settings') and self.settings:
            custom_wm = self.settings.get("custom_watermark_path", "")
            if custom_wm and os.path.exists(custom_wm):
                wm_pix = QPixmap(custom_wm)
            try:
                wm_opacity = float(self.settings.get("watermark_opacity", 0.04))
            except (ValueError, TypeError):
                wm_opacity = 0.04
        if not wm_pix and self.watermark_pixmap:
            wm_pix = self.watermark_pixmap

        if wm_pix and not wm_pix.isNull() and h > 140:
            wm_w = 100.0
            wm_h = wm_w * float(wm_pix.height()) / float(wm_pix.width()) if wm_pix.width() > 0 else 100.0
            wm_x = w - wm_w - 16.0
            wm_y = h - wm_h - 12.0
            wm_rect = QRectF(wm_x, wm_y, wm_w, wm_h)
            painter.setOpacity(max(0.005, min(0.40, wm_opacity)))
            painter.drawPixmap(wm_rect.toRect(), wm_pix)
            painter.setOpacity(1.0)

        # ----------------------------------------------------
        # 5. Physical Fresnel Bezel (Directional Light Crest Highlight)
        # ----------------------------------------------------
        if self.aura_state == "charging":
            border_brush = QBrush(QColor("#00e676"))
        elif self.aura_state == "media":
            border_brush = QBrush(QColor(self.accent_color))
        elif self.aura_state == "low_battery":
            border_brush = QBrush(QColor("#f59e0b"))
        else:
            outer_bezel = QLinearGradient(0.0, 0.0, 0.0, h)
            if is_dark:
                outer_bezel.setColorAt(0.0, QColor(255, 255, 255, 85))  # Refined grazing light crest
                outer_bezel.setColorAt(0.15, QColor(255, 255, 255, 40))
                outer_bezel.setColorAt(0.60, QColor(255, 255, 255, 18))
                outer_bezel.setColorAt(1.0, QColor(0, 0, 0, 75))        # Grounded rim at bottom
            else:
                outer_bezel.setColorAt(0.0, QColor(255, 255, 255, 240))
                outer_bezel.setColorAt(0.20, QColor(255, 255, 255, 160))
                outer_bezel.setColorAt(0.70, QColor(0, 0, 0, 25))
                outer_bezel.setColorAt(1.0, QColor(0, 0, 0, 55))
            border_brush = QBrush(outer_bezel)

        pen = QPen(border_brush, 1.0)
        pen.setCosmetic(True)
        painter.setPen(pen)
        painter.drawPath(path)


class GlassPanel(QFrame):
    """
    Apple 'Liquid Glass' Inspired Reusable Translucent Component in PyQt6.
    Renders multi-layered refractive glass aesthetics via deterministic custom QPainter passes:
      - Pass 1: Multi-Stop Frosted Translucent Base (Dark smoked glass vs Crisp milk glass)
      - Pass 2: Prismatic Chromatic Dispersion Fringe (Cyan/violet sub-pixel edge refraction)
      - Pass 3: Ambient Category & Accent Refraction Wash (3-8% chromatic blend)
      - Pass 4: Apple-Style Dual Specular Sheen (35° diagonal sweep + top-left radial bloom)
      - Pass 5: Physical Fresnel Double-Layer Bezel (Outer light highlight crest + Inner dark inset depth rim)
    """
    def __init__(self, category_key: str = "default", corner_radius: int = 12, parent=None):
        super().__init__(parent)
        self.category_key = category_key
        self.corner_radius = corner_radius
        self.theme_mode = "dark"
        self.accent_color = "#38bdf8"
        self.is_hovered = False
        self.setObjectName("card_frame")
        self.setMouseTracking(True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setStyleSheet("QFrame#card_frame { background: transparent; border: none; }")

    def set_category(self, category_key: str):
        self.category_key = category_key
        self.update()

    def set_corner_radius(self, radius: int):
        self.corner_radius = radius
        self.update()

    def apply_theme(self, accent_color: str, mode: str = "dark"):
        self.accent_color = accent_color
        self.theme_mode = mode
        self.update()

    def enterEvent(self, event):
        self.is_hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.is_hovered = False
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event):
        painter = QPainter()
        if not painter.begin(self):
            return
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = float(self.width())
        h = float(self.height())
        if w <= 4.0 or h <= 4.0:
            painter.end()
            return

        cr = float(self.corner_radius)

        # Pass 0: Soft Ambient Drop Shadow Pass
        shadow_path = QPainterPath()
        shadow_path.addRoundedRect(QRectF(1.0, 2.0, w - 2.0, h - 2.0), cr, cr)
        shadow_col = QColor(0, 0, 0, 70) if (self.theme_mode == "dark") else QColor(15, 23, 42, 30)
        painter.fillPath(shadow_path, shadow_col)

        rect = QRectF(0.5, 0.5, w - 1.0, h - 1.0)
        path = QPainterPath()
        path.addRoundedRect(rect, cr, cr)

        is_dark = (self.theme_mode == "dark")

        # Resolve category chromatic accent
        cat_palette = CATEGORY_ACCENTS.get(self.category_key)
        if cat_palette:
            cat_color_str = cat_palette.get(self.theme_mode, self.accent_color)
        else:
            cat_color_str = self.accent_color
        cat_color = QColor(cat_color_str)

        # ----------------------------------------------------
        # PASS 1: Multi-Stop Frosted Translucent Base (Sub-Surface Volume)
        # ----------------------------------------------------
        base_grad = QLinearGradient(0.0, 0.0, 0.0, h)
        if is_dark:
            base_grad.setColorAt(0.0, QColor(16, 20, 30, 240 if self.is_hovered else 232))
            base_grad.setColorAt(0.4, QColor(10, 13, 20, 232 if self.is_hovered else 222))
            base_grad.setColorAt(1.0, QColor(6, 8, 14, 246 if self.is_hovered else 238))
        else:
            # Crystalline Milk Glass
            base_grad.setColorAt(0.0, QColor(255, 255, 255, 245 if self.is_hovered else 235))
            base_grad.setColorAt(0.4, QColor(246, 249, 254, 225 if self.is_hovered else 215))
            base_grad.setColorAt(1.0, QColor(238, 242, 250, 240 if self.is_hovered else 230))
        painter.fillPath(path, QBrush(base_grad))

        # ----------------------------------------------------
        # PASS 2: Prismatic Chromatic Dispersion Fringe (Edge Refraction)
        # ----------------------------------------------------
        dispersion_grad = QLinearGradient(0.0, 0.0, min(w * 0.5, 120.0), min(h * 0.4, 60.0))
        c_disp_1 = QColor(56, 189, 248)  # Cyan/Sky Blue
        c_disp_2 = QColor(168, 85, 247)  # Violet/Purple
        disp_alpha = 24 if self.is_hovered else 14
        c_disp_1.setAlpha(disp_alpha if is_dark else disp_alpha + 8)
        c_disp_2.setAlpha(int(disp_alpha * 0.6) if is_dark else int(disp_alpha * 0.7))
        dispersion_grad.setColorAt(0.0, c_disp_1)
        dispersion_grad.setColorAt(0.6, c_disp_2)
        dispersion_grad.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.fillPath(path, QBrush(dispersion_grad))

        # ----------------------------------------------------
        # PASS 3: Ambient Category Refraction Wash
        # ----------------------------------------------------
        accent_wash = QLinearGradient(0.0, 0.0, w, h)
        wash_alpha_start = 18 if self.is_hovered else 10
        wash_alpha_end = 4 if self.is_hovered else 2
        c_wash_1 = QColor(cat_color)
        c_wash_1.setAlpha(wash_alpha_start if is_dark else wash_alpha_start + 6)
        c_wash_2 = QColor(cat_color)
        c_wash_2.setAlpha(wash_alpha_end)
        accent_wash.setColorAt(0.0, c_wash_1)
        accent_wash.setColorAt(0.5, QColor(cat_color.red(), cat_color.green(), cat_color.blue(), int(wash_alpha_start * 0.4)))
        accent_wash.setColorAt(1.0, c_wash_2)
        painter.fillPath(path, QBrush(accent_wash))

        # ----------------------------------------------------
        # PASS 4: Apple-Style Dual Specular Sheen (Diagonal Sweep + Corner Bloom)
        # ----------------------------------------------------
        # 4A: Diagonal Specular Light-Sweep (35-degree ambient overhead light angle)
        specular_diagonal = QLinearGradient(0.0, 0.0, w * 0.65, h * 0.50)
        if is_dark:
            specular_diagonal.setColorAt(0.0, QColor(255, 255, 255, 32 if self.is_hovered else 22))
            specular_diagonal.setColorAt(0.20, QColor(255, 255, 255, 10 if self.is_hovered else 6))
            specular_diagonal.setColorAt(0.60, QColor(255, 255, 255, 2 if self.is_hovered else 1))
            specular_diagonal.setColorAt(1.0, QColor(255, 255, 255, 0))
        else:
            specular_diagonal.setColorAt(0.0, QColor(255, 255, 255, 210 if self.is_hovered else 180))
            specular_diagonal.setColorAt(0.25, QColor(255, 255, 255, 90 if self.is_hovered else 65))
            specular_diagonal.setColorAt(0.70, QColor(255, 255, 255, 25 if self.is_hovered else 15))
            specular_diagonal.setColorAt(1.0, QColor(255, 255, 255, 0))
        painter.fillPath(path, QBrush(specular_diagonal))

        # 4B: Convex Corner Light Bloom (simulates curved corner catching ambient light)
        bloom_rad = max(45.0, min(w, h) * 0.65)
        specular_radial = QRadialGradient(QPointF(0.0, 0.0), bloom_rad)
        if is_dark:
            specular_radial.setColorAt(0.0, QColor(255, 255, 255, 20 if self.is_hovered else 12))
            specular_radial.setColorAt(0.45, QColor(255, 255, 255, 6))
            specular_radial.setColorAt(1.0, QColor(255, 255, 255, 0))
        else:
            specular_radial.setColorAt(0.0, QColor(255, 255, 255, 160 if self.is_hovered else 120))
            specular_radial.setColorAt(0.45, QColor(255, 255, 255, 45))
            specular_radial.setColorAt(1.0, QColor(255, 255, 255, 0))
        painter.fillPath(path, QBrush(specular_radial))

        # ----------------------------------------------------
        # PASS 5: Physical Fresnel Double-Layer Glass Bezel
        # ----------------------------------------------------
        # 5A: Outer Light Bezel (Razor-sharp top crest highlight + soft base shadow)
        outer_bezel = QLinearGradient(0.0, 0.0, 0.0, h)
        if is_dark:
            top_border_alpha = 80 if self.is_hovered else 60
            bot_border_alpha = 25 if self.is_hovered else 15
            outer_bezel.setColorAt(0.0, QColor(255, 255, 255, top_border_alpha))
            outer_bezel.setColorAt(0.15, QColor(255, 255, 255, int(top_border_alpha * 0.65)))
            outer_bezel.setColorAt(0.6, QColor(255, 255, 255, 18))
            outer_bezel.setColorAt(1.0, QColor(0, 0, 0, bot_border_alpha))
        else:
            top_border_alpha = 255 if self.is_hovered else 245
            bot_border_alpha = 70 if self.is_hovered else 50
            outer_bezel.setColorAt(0.0, QColor(255, 255, 255, top_border_alpha))
            outer_bezel.setColorAt(0.2, QColor(255, 255, 255, 185))
            outer_bezel.setColorAt(0.7, QColor(0, 0, 0, 25))
            outer_bezel.setColorAt(1.0, QColor(0, 0, 0, bot_border_alpha))

        pen_outer = QPen(QBrush(outer_bezel), 1.0)
        pen_outer.setCosmetic(True)
        painter.setPen(pen_outer)
        painter.drawPath(path)

        # 5B: Inner Inset Depth Rim (1px inset path with soft dark bevel)
        if w > 4.0 and h > 4.0:
            inset_rect = QRectF(1.5, 1.5, w - 3.0, h - 3.0)
            inset_path = QPainterPath()
            inset_cr = max(2.0, cr - 1.0)
            inset_path.addRoundedRect(inset_rect, inset_cr, inset_cr)

            inset_gradient = QLinearGradient(0.0, 0.0, 0.0, h)
            if is_dark:
                inset_gradient.setColorAt(0.0, QColor(255, 255, 255, 18 if self.is_hovered else 10))
                inset_gradient.setColorAt(0.4, QColor(0, 0, 0, 0))
                inset_gradient.setColorAt(1.0, QColor(0, 0, 0, 50))
            else:
                inset_gradient.setColorAt(0.0, QColor(255, 255, 255, 120))
                inset_gradient.setColorAt(0.4, QColor(255, 255, 255, 25))
                inset_gradient.setColorAt(1.0, QColor(0, 0, 0, 30))

            pen_inner = QPen(QBrush(inset_gradient), 1.0)
            pen_inner.setCosmetic(True)
            painter.setPen(pen_inner)
            painter.drawPath(inset_path)


LiquidGlassCard = GlassPanel


class SmoothScrollFilter(QObject):
    """Intercepts wheel events on QScrollArea and QListWidget to provide smooth 60fps stutter-free animated scrolling."""
    def __init__(self, target_widget, step_size: int = 36, duration: int = 90, parent=None):
        super().__init__(parent or target_widget)
        self.target_widget = target_widget
        self.step_size = step_size
        self.duration = duration
        self._animation = None

        # CRITICAL FIX: Force pixel-based continuous scroll mode instead of item-based snap jumps
        if hasattr(target_widget, 'setVerticalScrollMode'):
            target_widget.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        if hasattr(target_widget, 'setHorizontalScrollMode'):
            target_widget.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)

        # Enable smooth scroll filter on target widget viewport
        viewport = target_widget.viewport() if hasattr(target_widget, 'viewport') and target_widget.viewport() else target_widget
        viewport.installEventFilter(self)

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.Wheel:
            scroll_bar = self.target_widget.verticalScrollBar()
            if not scroll_bar or not scroll_bar.isVisible() or scroll_bar.maximum() == 0:
                return False

            angle_delta = event.angleDelta().y()
            if angle_delta == 0:
                return False

            num_steps = angle_delta / 120.0
            scroll_delta = -int(num_steps * self.step_size)

            # Lazy-initialize single persistent QPropertyAnimation instance
            if self._animation is None:
                self._animation = QPropertyAnimation(scroll_bar, b"value", self)
                self._animation.setEasingCurve(QEasingCurve.Type.OutQuad)

            # Stop active animation instantaneously to prevent distance backlog accumulation
            if self._animation.state() == QAbstractAnimation.State.Running:
                self._animation.stop()

            current_val = scroll_bar.value()
            new_target = max(scroll_bar.minimum(), min(scroll_bar.maximum(), current_val + scroll_delta))

            if new_target == current_val:
                return True

            self._animation.setDuration(self.duration)
            self._animation.setStartValue(current_val)
            self._animation.setEndValue(new_target)
            self._animation.start()
            return True

        return super().eventFilter(obj, event)

# DYNAMIC THEME QSS GENERATORS
def get_card_qss(mode: str = "dark") -> str:
    pal = THEME_PALETTES.get(mode, THEME_PALETTES["dark"])
    top_border = "rgba(255, 255, 255, 0.16)" if mode == "dark" else "rgba(255, 255, 255, 0.85)"
    return f"""
        QFrame#card_frame {{
            background-color: {pal["card_bg"]};
            border: 1px solid {pal["card_border"]};
            border-top: 1px solid {top_border};
            border-radius: 10px;
        }}
    """

def get_category_card_qss(category_key: str, mode: str = "dark") -> str:
    """Generates styled category cards with frosted lighting depth, top-edge reflection, and left-edge accent stripe."""
    pal = THEME_PALETTES.get(mode, THEME_PALETTES["dark"])
    cat_accent = CATEGORY_ACCENTS.get(category_key, {"dark": "#38bdf8", "light": "#0284c7"})[mode]

    if mode == "dark":
        grad_start = "rgba(255, 255, 255, 0.08)"
        grad_end = "rgba(255, 255, 255, 0.03)"
        top_border = "rgba(255, 255, 255, 0.18)"
    else:
        grad_start = "rgba(255, 255, 255, 0.95)"
        grad_end = "rgba(240, 243, 246, 0.85)"
        top_border = "rgba(255, 255, 255, 0.85)"

    return f"""
        QFrame#card_frame {{
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {grad_start}, stop:1 {grad_end});
            border: 1px solid {pal["card_border"]};
            border-top: 1px solid {top_border};
            border-left: 3.5px solid {cat_accent};
            border-radius: 10px;
        }}
        QFrame#card_frame:hover {{
            border: 1px solid {cat_accent}66;
            border-top: 1px solid {top_border};
            border-left: 3.5px solid {cat_accent};
        }}
    """

def make_card_header(title: str, icon_emoji: str, category_key: str, mode: str = "dark") -> QWidget:
    """Creates a compact header with a 18x18 circular icon chip matching category accent color."""
    w = QWidget()
    w.setStyleSheet("background: transparent;")
    h_box = QHBoxLayout(w)
    h_box.setContentsMargins(0, 0, 0, 0)
    h_box.setSpacing(6)

    cat_accent = CATEGORY_ACCENTS.get(category_key, {"dark": "#38bdf8", "light": "#0284c7"})[mode]
    chip_bg = f"{cat_accent}26" if mode == "dark" else f"{cat_accent}1e"

    chip = QLabel(icon_emoji)
    chip.setFixedSize(18, 18)
    chip.setAlignment(Qt.AlignmentFlag.AlignCenter)
    chip.setStyleSheet(f"QLabel {{ background-color: {chip_bg}; border-radius: 9px; font-size: 9.5px; font-family: 'Segoe UI Emoji', 'Segoe UI Symbol', 'Segoe UI', sans-serif; }}")

    display_title = title.upper()
    if len(display_title) > 22:
        display_title = display_title[:21] + "…"

    lbl_title = QLabel(display_title)
    lbl_title.setMinimumWidth(0)
    lbl_title.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
    lbl_title.setToolTip(title)
    lbl_title.setStyleSheet(f"color: {cat_accent}; font-size: 9.5px; font-weight: 800; letter-spacing: 0.5px; background: transparent;")

    h_box.addWidget(chip)
    h_box.addWidget(lbl_title, 1)
    return w

def make_empty_state(icon_emoji: str, headline: str, subtext: str, mode: str = "dark") -> QWidget:
    """Renders a warm, illustrative empty state container with compact icon and text."""
    w = QWidget()
    w.setStyleSheet("background: transparent;")
    layout = QVBoxLayout(w)
    layout.setContentsMargins(2, 2, 2, 2)
    layout.setSpacing(1)
    layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

    pal = THEME_PALETTES.get(mode, THEME_PALETTES["dark"])

    lbl_ico = QLabel(icon_emoji)
    lbl_ico.setStyleSheet("font-size: 18px; font-family: 'Segoe UI Emoji', 'Segoe UI Symbol', 'Segoe UI', sans-serif; background: transparent;")
    lbl_ico.setAlignment(Qt.AlignmentFlag.AlignCenter)

    lbl_head = QLabel(headline)
    lbl_head.setStyleSheet(f"color: {pal['text_secondary']}; font-size: 9px; font-weight: 700; background: transparent;")
    lbl_head.setAlignment(Qt.AlignmentFlag.AlignCenter)

    lbl_sub = QLabel(subtext)
    lbl_sub.setStyleSheet(f"color: {pal['text_muted']}; font-size: 8px; font-style: italic; background: transparent;")
    lbl_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)

    layout.addWidget(lbl_ico)
    layout.addWidget(lbl_head)
    layout.addWidget(lbl_sub)
    return w

def get_scrollbar_qss(accent: str, mode: str = "dark") -> str:
    handle_bg = "rgba(255, 255, 255, 0.22)" if mode == "dark" else "rgba(0, 0, 0, 0.20)"
    return f"""
        QScrollBar:vertical {{
            background: transparent;
            width: 5px;
            margin: 0px;
            border: none;
            border-radius: 2.5px;
        }}
        QScrollBar::handle:vertical {{
            background: {handle_bg};
            min-height: 24px;
            border-radius: 2.5px;
        }}
        QScrollBar::handle:vertical:hover {{
            background: {accent};
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0px;
            width: 0px;
            background: none;
            border: none;
        }}
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
            background: none;
        }}
        QScrollBar:horizontal {{
            height: 0px;
            width: 0px;
            background: transparent;
            border: none;
        }}
        QScrollBar::handle:horizontal, QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal, QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
            height: 0px;
            width: 0px;
            background: transparent;
            border: none;
        }}
    """

def get_checkbox_qss(accent: str, mode: str = "dark") -> str:
    pal = THEME_PALETTES.get(mode, THEME_PALETTES["dark"])
    ind_border = "rgba(255, 255, 255, 0.26)" if mode == "dark" else "rgba(0, 0, 0, 0.26)"
    ind_bg = "rgba(255, 255, 255, 0.08)" if mode == "dark" else "rgba(0, 0, 0, 0.05)"
    ind_hover = "rgba(255, 255, 255, 0.16)" if mode == "dark" else "rgba(0, 0, 0, 0.10)"
    text_color = pal["text_primary"]
    return f"""
        QCheckBox {{
            color: {text_color};
            font-size: 10.5px;
            font-weight: 600;
            spacing: 6px;
            background: transparent;
        }}
        QCheckBox::indicator {{
            width: 15px;
            height: 15px;
            border-radius: 4px;
            border: 1px solid {ind_border};
            background-color: {ind_bg};
        }}
        QCheckBox::indicator:hover {{
            border: 1px solid {accent};
            background-color: {ind_hover};
        }}
        QCheckBox::indicator:checked {{
            background-color: {accent};
            border: 1px solid {accent};
        }}
    """

def get_slider_qss(accent: str, mode: str = "dark") -> str:
    pal = THEME_PALETTES.get(mode, THEME_PALETTES["dark"])
    return f"""
        QSlider::groove:horizontal {{
            background: {pal['input_bg']};
            height: 4px;
            border-radius: 2px;
            border: none;
            margin: 0 2px;
        }}
        QSlider::sub-page:horizontal {{
            background: {accent};
            border-radius: 2px;
        }}
        QSlider::add-page:horizontal {{
            background: {pal['input_bg']};
            border-radius: 2px;
        }}
        QSlider::handle:horizontal {{
            background: #ffffff;
            border: 2px solid {accent};
            width: 12px;
            height: 12px;
            margin: -4px 0;
            border-radius: 6px;
        }}
        QSlider::handle:horizontal:hover {{
            background: #ffffff;
            border: 2px solid {accent};
            width: 14px;
            height: 14px;
            margin: -5px 0;
            border-radius: 7px;
        }}
        QSlider::handle:horizontal:pressed {{
            background: {accent};
            border: 2px solid #ffffff;
            width: 14px;
            height: 14px;
            margin: -5px 0;
            border-radius: 7px;
        }}
    """

def get_spinbox_qss(accent: str, mode: str = "dark") -> str:
    pal = THEME_PALETTES.get(mode, THEME_PALETTES["dark"])
    return f"""
        QSpinBox, QDoubleSpinBox, QTimeEdit {{
            background: {pal["input_bg"]};
            color: {pal["text_primary"]};
            border: 1px solid {pal["input_border"]};
            border-radius: 5px;
            padding: 2px 6px;
            font-size: 11px;
            font-weight: 600;
        }}
        QSpinBox:hover, QDoubleSpinBox:hover, QTimeEdit:hover {{
            border: 1px solid {accent};
        }}
        QSpinBox::up-button, QSpinBox::down-button,
        QTimeEdit::up-button, QTimeEdit::down-button,
        QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{
            width: 0px;
            height: 0px;
            border: none;
            background: none;
        }}
        QSpinBox::up-arrow, QSpinBox::down-arrow,
        QTimeEdit::up-arrow, QTimeEdit::down-arrow,
        QDoubleSpinBox::up-arrow, QDoubleSpinBox::down-arrow {{
            width: 0px;
            height: 0px;
            image: none;
        }}
    """

def get_combobox_qss(accent: str, mode: str = "dark") -> str:
    pal = THEME_PALETTES.get(mode, THEME_PALETTES["dark"])
    return f"""
        QComboBox {{
            background: {pal["input_bg"]};
            color: {pal["text_primary"]};
            border: 1px solid {pal["input_border"]};
            border-radius: 5px;
            padding: 2px 6px;
            font-size: 10px;
            font-weight: bold;
        }}
        QComboBox:hover {{
            border: 1px solid {accent};
            background: {pal["input_bg"]};
        }}
        QComboBox::drop-down {{
            border: none;
            width: 16px;
        }}
        QComboBox::down-arrow {{
            image: none;
            border: none;
        }}
        QComboBox QAbstractItemView {{
            background-color: {pal["combo_popup_bg"]};
            color: {pal["text_primary"]};
            border: 1px solid {pal["input_border"]};
            border-radius: 6px;
            padding: 4px;
            selection-background-color: {accent};
            selection-color: {get_accent_text_color(accent)};
            outline: none;
        }}
    """

def get_lineedit_qss(accent: str, mode: str = "dark") -> str:
    pal = THEME_PALETTES.get(mode, THEME_PALETTES["dark"])
    return f"""
        QLineEdit {{
            background: {pal["input_bg"]};
            color: {pal["text_primary"]};
            border: 1px solid {pal["input_border"]};
            border-radius: 5px;
            padding: 2px 6px;
            font-size: 9.5px;
        }}
        QLineEdit:focus {{
            border: 1px solid {accent};
        }}
    """

def flash_copy_feedback(btn: QPushButton, text: str):
    """Copies text to clipboard and flashes button with a crisp green '✓ Copied!' badge for 1200ms."""
    try:
        QApplication.clipboard().setText(text)
        orig_text = btn.text()
        orig_style = btn.styleSheet()
        btn.setText("✓ Copied!")
        btn.setStyleSheet("QPushButton { background-color: #00e676 !important; color: #ffffff !important; font-weight: 800 !important; border-radius: 5px !important; font-size: 9.5px !important; border: none !important; padding: 0 4px !important; }")

        def restore():
            try:
                btn.setText(orig_text)
                btn.setStyleSheet(orig_style)
            except Exception:
                pass

        QTimer.singleShot(1200, restore)
    except Exception as e:
        print(f"[Flash Copy Error]: {e}")

def get_list_widget_qss(accent: str, mode: str = "dark") -> str:
    pal = THEME_PALETTES.get(mode, THEME_PALETTES["dark"])
    c = QColor(accent)
    sel_bg = f"rgba({c.red()}, {c.green()}, {c.blue()}, 0.25)" if mode == "dark" else f"rgba({c.red()}, {c.green()}, {c.blue()}, 0.18)"
    border_hover = "rgba(255, 255, 255, 0.25)" if mode == "dark" else "rgba(0, 0, 0, 0.18)"
    return f"""
        QListWidget, QListWidget > QWidget > QWidget {{
            background: transparent;
            color: {pal["text_primary"]};
            border: none;
            outline: none;
        }}
        QListWidget::item {{
            background: {pal["list_item_bg"]};
            color: {pal["text_primary"]};
            border: 1px solid {pal["list_item_border"]};
            border-radius: 8px;
            margin: 2px 4px;
            padding: 5px 8px;
            font-size: 10.5px;
            font-weight: 600;
            outline: none;
        }}
        QListWidget::item:hover {{
            background: {pal["list_item_hover"]};
            color: {pal["text_primary"]};
            border: 1px solid {border_hover};
        }}
        QListWidget::item:selected {{
            background: {sel_bg};
            color: {pal["text_primary"]};
            border: 1.5px solid {accent};
            font-weight: 700;
        }}
        {get_scrollbar_qss(accent, mode)}
    """
class MiniSoundwaveVisualizer(QWidget):
    """4-bar compact soundwave animated visualizer for the collapsed pill."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.accent_color = "#38bdf8"
        self.setFixedSize(22, 16)
        self.bar_heights = [3.0, 4.0, 3.0, 4.0]
        self._step = 0
        self.is_active = False

        self.anim_timer = QTimer(self)
        self.anim_timer.setInterval(28)  # ~36 FPS high-refresh fluid animation
        self.anim_timer.timeout.connect(self._on_tick)

    def start_pulsing(self):
        if not self.is_active:
            self.is_active = True
            if self.isVisible():
                self.anim_timer.start()

    def stop_pulsing(self):
        self.is_active = False
        self.anim_timer.stop()
        self.bar_heights = [3.0, 4.0, 3.0, 4.0]
        self.update()

    def hideEvent(self, event):
        self.anim_timer.stop()
        super().hideEvent(event)

    def showEvent(self, event):
        if self.is_active:
            self.anim_timer.start()
        super().showEvent(event)

    def _on_tick(self):
        if not self.isVisible() or not self.is_active:
            return
        self._step = (self._step + 1) % 360
        s = float(self._step)
        # Butter-smooth continuous trigonometric float oscillation
        h1 = 3.0 + 8.5 * abs(math.sin(s * 0.08))
        h2 = 4.0 + 10.0 * abs(math.sin(s * 0.11 + 1.2))
        h3 = 4.0 + 9.5 * abs(math.sin(s * 0.09 + 2.4))
        h4 = 3.0 + 7.5 * abs(math.sin(s * 0.13 + 0.8))
        self.bar_heights = [h1, h2, h3, h4]
        self.update()

    def paintEvent(self, event):
        painter = QPainter()
        if not painter.begin(self):
            return
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        color = QColor(self.accent_color)
        painter.setBrush(QBrush(color))
        painter.setPen(Qt.PenStyle.NoPen)

        w = 2.5
        spacing = 2.5
        x_start = 2.0
        h_total = float(self.height())

        for idx, h in enumerate(self.bar_heights):
            x = x_start + idx * (w + spacing)
            y = (h_total - h) / 2.0
            painter.drawRoundedRect(QRectF(x, y, w, float(h)), 1.2, 1.2)

    def apply_theme(self, accent: str):
        self.accent_color = accent
        self.update()


class AnimatedLockBadge(QWidget):
    """Dynamic popping animated lock badge (CAPS / NUM) with smooth spring bounce and glow."""
    def __init__(self, text: str, width: int = 38, parent=None):
        super().__init__(parent)
        self.text = text
        self.badge_width = width
        self.badge_height = 18
        self.setFixedSize(width + 4, 20)

        self.is_active = False
        self.accent_color = "#38bdf8"
        self.theme_mode = "dark"

        self._scale = 1.0

        self.anim = QPropertyAnimation(self, b"scale_prop")
        self.anim.setDuration(200)
        self.anim.setEasingCurve(QEasingCurve.Type.OutBack)

    @pyqtProperty(float)
    def scale_prop(self) -> float:
        return self._scale

    @scale_prop.setter
    def scale_prop(self, val: float):
        self._scale = val
        self.update()

    def set_state(self, active: bool, animate: bool = True):
        if self.is_active == active:
            return
        self.is_active = active
        if animate and self.isVisible():
            self.anim.stop()
            self.anim.setStartValue(1.24 if active else 0.85)
            self.anim.setEndValue(1.0)
            self.anim.start()
        else:
            self._scale = 1.0
            self.update()

    def apply_theme(self, accent_color: str, mode: str = "dark"):
        self.accent_color = accent_color
        self.theme_mode = mode
        self.update()

    def paintEvent(self, event):
        painter = QPainter()
        if not painter.begin(self):
            return
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        pal = THEME_PALETTES.get(self.theme_mode, THEME_PALETTES["dark"])
        center_x = float(self.width()) / 2.0
        center_y = float(self.height()) / 2.0

        w = float(self.badge_width) * self._scale
        h = float(self.badge_height) * self._scale
        x = center_x - (w / 2.0)
        y = center_y - (h / 2.0)
        rect = QRectF(x, y, w, h)

        if self.is_active:
            bg_color = QColor(self.accent_color)
            text_color = QColor("#ffffff")
            font_weight = QFont.Weight.Bold
        else:
            if self.theme_mode == "dark":
                bg_color = QColor(255, 255, 255, 20)
                text_color = QColor(148, 163, 184)
            else:
                bg_color = QColor(0, 0, 0, 16)
                text_color = QColor(100, 116, 139)
            font_weight = QFont.Weight.DemiBold

        path = QPainterPath()
        path.addRoundedRect(rect, 4.0, 4.0)
        painter.fillPath(path, QBrush(bg_color))

        font = QFont("Segoe UI", 7)
        font.setWeight(font_weight)
        font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 0.5)
        painter.setFont(font)
        painter.setPen(text_color)
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, self.text)


class CollapsedPillWidget(QWidget):
    """Collapsed Header supporting Light & Dark Mode, animated lock badges, soundwave visualizer, and in-pill status toasts."""
    double_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.caps_state = False
        self.num_state = False
        self.is_muted = False
        self.theme_mode = "dark"
        self.latest_battery = {}
        self.latest_charging = False
        self.is_toast_active = False
        self.init_ui()

    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 4, 12, 4)
        layout.setSpacing(6)

        # 0. Mini San Lives Brand Logo
        self.logo_label = QLabel(self)
        self.logo_label.setFixedSize(20, 20)
        self.logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.logo_label.setCursor(Qt.CursorShape.PointingHandCursor)
        self.logo_label.setToolTip("Click to Open Full Workspace Studio")
        pix = self.get_logo_pixmap("dark", 18)
        if not pix.isNull():
            self.logo_label.setPixmap(pix)
        self.logo_label.setStyleSheet("background: transparent;")
        self.logo_label.mousePressEvent = lambda event: (self.double_clicked.emit(), event.accept()) if event.button() == Qt.MouseButton.LeftButton else None
        layout.addWidget(self.logo_label)

        # 1. Digital Clock & Date
        clock_layout = QVBoxLayout()
        clock_layout.setSpacing(0)

        self.clock_label = QLabel("00:00:00")
        self.clock_label.setStyleSheet("color: #ffffff; font-size: 11.5px; font-weight: 700; font-family: 'Segoe UI', sans-serif;")

        self.date_label = QLabel("Mon, Jan 01")
        self.date_label.setStyleSheet("color: #cbd5e1; font-size: 9.5px; font-weight: 600;")

        clock_layout.addWidget(self.clock_label)
        clock_layout.addWidget(self.date_label)
        layout.addLayout(clock_layout)

        # 2. Animated Pop Spring Lock Badges
        self.caps_badge = AnimatedLockBadge("CAPS", width=38, parent=self)
        self.num_badge = AnimatedLockBadge("NUM", width=34, parent=self)

        # Backwards compatible alias properties
        self.caps_label = self.caps_badge
        self.num_label = self.num_badge

        layout.addWidget(self.caps_badge)
        layout.addWidget(self.num_badge)

        # 3. Mini Soundwave Visualizer & Next Track Button (Active during media playback)
        self.soundwave = MiniSoundwaveVisualizer(self)
        self.soundwave.hide()
        layout.addWidget(self.soundwave)

        layout.addStretch()

        # Pomodoro Running Countdown Badge in empty space of collapsed pill
        self.pomo_badge = QLabel("🍅 25:00", self)
        self.pomo_badge.setFixedHeight(20)
        self.pomo_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.pomo_badge.setStyleSheet("QLabel { background: rgba(239, 68, 68, 0.22); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.5); border-radius: 5px; font-size: 10px; font-weight: 800; font-family: 'Segoe UI', monospace; padding: 0 6px; }")
        self.pomo_badge.hide()
        layout.addWidget(self.pomo_badge)

        # In-Pill Highlighted Status Toast Label (Minimized bar highlight for fully charged, network, hotspot)
        self.pill_toast_label = QLabel("")
        self.pill_toast_label.setFixedHeight(20)
        self.pill_toast_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.pill_toast_label.hide()
        layout.addWidget(self.pill_toast_label)

        # Live Battery Percentage + Icon Label
        self.battery_label = QLabel("🔋 --%")
        self.battery_label.setFixedHeight(20)
        self.battery_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.battery_label.setStyleSheet("QLabel { background: rgba(255, 255, 255, 0.12); color: #ffffff; border: 1px solid rgba(255, 255, 255, 0.2); border-radius: 5px; font-size: 10.5px; font-weight: 700; padding: 0 6px; }")
        layout.addWidget(self.battery_label)

        # Quick Mute Button
        self.mute_btn = QPushButton("🔊")
        self.mute_btn.setFixedSize(22, 20)
        self.mute_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.mute_btn.setStyleSheet("QPushButton { background-color: rgba(255, 255, 255, 0.10); border-radius: 5px; border: 1px solid rgba(255, 255, 255, 0.2); font-size: 10px; } QPushButton:hover { background-color: rgba(56, 189, 248, 0.25); border: 1px solid #38bdf8; }")
        self.mute_btn.clicked.connect(self.toggle_mute)
        layout.addWidget(self.mute_btn)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.double_clicked.emit()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def get_logo_pixmap(self, mode: str = "dark", size: int = 18, accent_color: str = "#38bdf8") -> QPixmap:
        custom_logo = ""
        if hasattr(self, 'settings') and self.settings:
            custom_logo = self.settings.get("custom_logo_path", "")
        return get_accent_tinted_logo(accent_color, mode, size, custom_logo)

    def apply_theme(self, accent_color: str, mode: str = "dark"):
        self.theme_mode = mode
        pal = THEME_PALETTES.get(mode, THEME_PALETTES["dark"])
        self.clock_label.setStyleSheet(f"color: {pal['text_primary']}; font-size: 11.5px; font-weight: 700; font-family: 'Segoe UI', sans-serif;")
        self.date_label.setStyleSheet(f"color: {pal['text_secondary']}; font-size: 9.5px; font-weight: 600;")
        self.battery_label.setStyleSheet(f"QLabel {{ background: {pal['input_bg']}; color: {pal['text_primary']}; border: 1px solid {pal['input_border']}; border-radius: 5px; font-size: 10.5px; font-weight: 700; padding: 0 6px; }}")
        self.mute_btn.setStyleSheet(f"QPushButton {{ background-color: {pal['input_bg']}; color: {pal['text_primary']}; border-radius: 5px; border: 1px solid {pal['input_border']}; font-size: 10px; }} QPushButton:hover {{ border: 1px solid {accent_color}; }}")
        
        pix = self.get_logo_pixmap(mode, 18, accent_color)
        if not pix.isNull():
            self.logo_label.setPixmap(pix)

        self.soundwave.apply_theme(accent_color)
        self.caps_badge.apply_theme(accent_color, mode)
        self.num_badge.apply_theme(accent_color, mode)

    def update_now_playing_state(self, is_playing: bool):
        """Activates or silences the pill soundwave indicator based on live media state."""
        if is_playing:
            self.soundwave.start_pulsing()
            self.soundwave.show()
        else:
            self.soundwave.stop_pulsing()
            self.soundwave.hide()

    def update_pomodoro_badge(self, text: str, is_running: bool):
        """Updates or toggles the minimized pill Pomodoro countdown badge."""
        if is_running:
            self.pomo_badge.setText(f"🍅 {text}")
            self.pomo_badge.show()
        else:
            self.pomo_badge.hide()

    def update_clock_and_date(self, is_12h: bool = True):
        now = datetime.now()
        self.clock_label.setText(format_display_time(now, is_12h))
        self.date_label.setText(now.strftime("%a, %b %d"))

    def update_fast_clock_and_lock_badges(self, is_12h: bool = True, accent_color: str = "#38bdf8"):
        self.update_clock_and_date(is_12h=is_12h)
        caps_now = SystemMonitor.is_caps_lock_on()
        num_now = SystemMonitor.is_num_lock_on()

        if caps_now != self.caps_state:
            self.caps_state = caps_now
            self.caps_badge.set_state(caps_now, animate=True)

        if num_now != self.num_state:
            self.num_state = num_now
            self.num_badge.set_state(num_now, animate=True)

    def update_badge_styles(self, caps_on: bool, num_on: bool, accent_color: str = "#38bdf8"):
        self.caps_state = caps_on
        self.num_state = num_on
        self.caps_badge.set_state(caps_on, animate=False)
        self.num_badge.set_state(num_on, animate=False)

    def update_battery_display(self, battery: dict, charging: bool):
        try:
            self.latest_battery = battery
            self.latest_charging = charging
            if not self.is_toast_active:
                percent = battery.get('percent', None) if battery else None
                if percent is not None and percent >= 0:
                    icon = "⚡" if charging else "🔋"
                    self.battery_label.setText(f"{icon} {int(percent)}%")
                else:
                    self.battery_label.setText("🔋 N/A")
        except Exception:
            self.battery_label.setText("🔋 N/A")

    def show_pill_toast(self, text: str, icon: str = "", bg_color: str = "#00e676", duration_ms: int = 3200):
        """Highlights a system event pill inside the minimized bar with dynamic capsule styling."""
        try:
            self.is_toast_active = True
            msg = f"{icon} {text}".strip() if icon else text
            self.pill_toast_label.setText(msg)
            self.pill_toast_label.setStyleSheet(f"""
                QLabel {{
                    background-color: {bg_color};
                    color: #ffffff;
                    font-size: 9.5px;
                    font-weight: 800;
                    border-radius: 6px;
                    padding: 1px 9px;
                    border: 1px solid rgba(255, 255, 255, 0.40);
                }}
            """)
            self.battery_label.hide()
            self.pill_toast_label.show()
            self.update()
            if self.window():
                self.window().update()

            def restore_toast():
                try:
                    self.is_toast_active = False
                    self.pill_toast_label.hide()
                    self.battery_label.show()
                    self.update_battery_display(self.latest_battery, self.latest_charging)
                    self.update()
                    if self.window():
                        self.window().update()
                except Exception:
                    pass

            QTimer.singleShot(duration_ms, restore_toast)
        except Exception as e:
            print(f"[Pill Toast Exception]: {e}")

    def show_temp_status(self, text: str, duration_ms: int = 3000):
        """Backwards compatible alias calling show_pill_toast."""
        self.show_pill_toast(text=text, duration_ms=duration_ms)

    def toggle_mute(self):
        self.is_muted = not self.is_muted
        SystemMonitor.set_master_mute(self.is_muted)
        self.mute_btn.setText("🔇" if self.is_muted else "🔊")

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.double_clicked.emit()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)


# FULL-WINDOW TAKEOVER ALARM MODAL CARD
# FULL-WINDOW TAKEOVER ALARM MODAL CARD
class AlarmBannerModalCard(QFrame):
    """Full-Window Takeover Alarm/Timetable Card supporting Dual Theme & Cohesive Controls."""
    dismiss_requested = pyqtSignal()
    snooze_requested = pyqtSignal(dict, int)
    mark_done_requested = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("alarm_full_takeover_card")
        self.alarm_data = {}
        self.theme_mode = "dark"
        self.total_autodismiss_ms = 30000
        self.remaining_autodismiss_ms = 30000
        self.snooze_pill_buttons = {}
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # 1. Hero Icon Container with Soft Anchored Radial Glow (Static Icon)
        self.icon_glow_frame = QWidget()
        self.icon_glow_frame.setFixedSize(70, 50)
        icon_box = QVBoxLayout(self.icon_glow_frame)
        icon_box.setContentsMargins(0, 0, 0, 0)
        icon_box.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.icon_lbl = QLabel("\U0001F514")
        self.icon_lbl.setStyleSheet("font-size: 32px; font-family: 'Segoe UI Emoji', 'Segoe UI Symbol', 'Segoe UI', sans-serif; background: transparent;")
        self.icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_box.addWidget(self.icon_lbl, 0, Qt.AlignmentFlag.AlignCenter)

        self.glow_effect = QGraphicsDropShadowEffect(self.icon_glow_frame)
        self.glow_effect.setBlurRadius(36)
        self.glow_effect.setColor(QColor(239, 68, 68, 120))
        self.glow_effect.setOffset(0, 0)
        self.icon_glow_frame.setGraphicsEffect(self.glow_effect)

        # 2. Tag Label
        self.tag_lbl = QLabel("\U0001F514 ALARM ALERT")
        self.tag_lbl.setStyleSheet("color: #ef4444; font-size: 12px; font-weight: 800; letter-spacing: 1px; background: transparent;")
        self.tag_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # 3. Time & Title Headline
        self.headline_lbl = QLabel("")
        self.headline_lbl.setWordWrap(True)
        self.headline_lbl.setStyleSheet("color: #f8fafc; font-size: 15px; font-weight: 800; background: transparent;")
        self.headline_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # 4. Details / Days Subtitle
        self.details_lbl = QLabel("")
        self.details_lbl.setStyleSheet("color: #94a3b8; font-size: 10.5px; font-weight: 600; background: transparent;")
        self.details_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(self.icon_glow_frame, 0, Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.tag_lbl)
        layout.addWidget(self.headline_lbl)
        layout.addWidget(self.details_lbl)
        layout.addSpacing(6)

        # 5. Direct 1-Click Action Bar (Snooze Pills + Mark Done if Timetable + Dismiss)
        action_bar = QHBoxLayout()
        action_bar.setSpacing(6)
        action_bar.setAlignment(Qt.AlignmentFlag.AlignCenter)

        durations = [("5m", 5), ("10m", 10), ("15m", 15), ("30m", 30), ("1h", 60)]
        for label_text, mins in durations:
            btn = QPushButton(label_text)
            btn.setFixedHeight(28)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _, m=mins: self.trigger_snooze_for_duration(m))
            self.snooze_pill_buttons[mins] = btn
            action_bar.addWidget(btn)

        # Primary Positive Mark Done Button (for Timetable tasks)
        self.mark_done_btn = QPushButton("\u2705 Mark Done")
        self.mark_done_btn.setFixedHeight(28)
        self.mark_done_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.mark_done_btn.setStyleSheet("QPushButton { background: #00e676; color: #0f0f14; border: none; border-radius: 6px; font-size: 10.5px; font-weight: 800; padding: 0 10px; } QPushButton:hover { background: #10b981; }")
        self.mark_done_btn.clicked.connect(self.on_mark_done_clicked)
        self.mark_done_btn.hide()

        # Primary Bold Dismiss Button
        self.dismiss_btn = QPushButton("\u274c Dismiss")
        self.dismiss_btn.setFixedHeight(28)
        self.dismiss_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.dismiss_btn.setStyleSheet("QPushButton { background: #ef4444; color: #ffffff; border: none; border-radius: 6px; font-size: 10.5px; font-weight: 800; padding: 0 12px; } QPushButton:hover { background: #dc2626; }")
        self.dismiss_btn.clicked.connect(self.dismiss_requested.emit)

        action_bar.addWidget(self.mark_done_btn)
        action_bar.addWidget(self.dismiss_btn)

        layout.addLayout(action_bar)

        # 6. Thin Accent-Colored Depleting Countdown Progress Bar
        self.dismiss_progress_bar = QProgressBar()
        self.dismiss_progress_bar.setFixedHeight(3)
        self.dismiss_progress_bar.setRange(0, 1000)
        self.dismiss_progress_bar.setValue(1000)
        self.dismiss_progress_bar.setTextVisible(False)
        layout.addWidget(self.dismiss_progress_bar)

        self.countdown_timer = QTimer(self)
        self.countdown_timer.setInterval(30)
        self.countdown_timer.timeout.connect(self.on_countdown_tick)

    def trigger_snooze_for_duration(self, minutes: int):
        self.countdown_timer.stop()
        self.snooze_requested.emit(self.alarm_data, minutes)

    def update_pill_styles(self, accent_color: str, mode: str):
        pal = THEME_PALETTES.get(mode, THEME_PALETTES["dark"])
        qss = f"""
            QPushButton {{
                background-color: {pal['input_bg']};
                color: {pal['text_primary']};
                border: 1px solid {pal['input_border']};
                border-radius: 12px;
                font-size: 10px;
                font-weight: 700;
                padding: 0 8px;
            }}
            QPushButton:hover {{
                border: 1px solid {accent_color};
                background-color: {pal['list_item_hover']};
                color: {pal['text_primary']};
            }}
            QPushButton:pressed {{
                background-color: {accent_color};
                color: #ffffff;
                border: none;
            }}
        """
        for btn in self.snooze_pill_buttons.values():
            btn.setStyleSheet(qss)

    def on_countdown_tick(self):
        self.remaining_autodismiss_ms -= 30
        if self.total_autodismiss_ms > 0:
            ratio = max(0.0, self.remaining_autodismiss_ms / float(self.total_autodismiss_ms))
            self.dismiss_progress_bar.setValue(int(ratio * 1000))
        if self.remaining_autodismiss_ms <= 0:
            self.countdown_timer.stop()

    def start_countdown(self, seconds: int):
        if seconds > 0:
            self.total_autodismiss_ms = seconds * 1000
            self.remaining_autodismiss_ms = self.total_autodismiss_ms
            self.dismiss_progress_bar.setValue(1000)
            self.dismiss_progress_bar.show()
            self.countdown_timer.start()
        else:
            self.total_autodismiss_ms = 0
            self.dismiss_progress_bar.hide()
            self.countdown_timer.stop()

    def apply_theme(self, accent_color: str, mode: str = "dark"):
        self.theme_mode = mode
        pal = THEME_PALETTES.get(mode, THEME_PALETTES["dark"])
        self.headline_lbl.setStyleSheet(f"color: {pal['text_primary']}; font-size: 15px; font-weight: 800; background: transparent;")
        self.details_lbl.setStyleSheet(f"color: {pal['text_secondary']}; font-size: 10.5px; font-weight: 600; background: transparent;")

        self.update_pill_styles(accent_color, mode)

        # Theme-Reactive Countdown Bar: accent_color for remaining time chunk, pal['input_bg'] for elapsed track
        self.dismiss_progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background: {pal['input_bg']};
                border: none;
                border-radius: 1.5px;
            }}
            QProgressBar::chunk {{
                background: {accent_color};
                border-radius: 1.5px;
            }}
        """)

    def set_trigger_data(self, title: str, is_timetable: bool = False, time_str: str = "", days: list = None, task_id: str = ""):
        self.alarm_data = {
            "title": title,
            "is_timetable": is_timetable,
            "time_str": time_str,
            "days": days or [],
            "task_id": task_id
        }

        accent = "#38bdf8"
        if hasattr(self, 'settings') and self.settings:
            accent = resolve_accent_color(self.settings)

        if is_timetable:
            self.icon_lbl.setText("\U0001F4C5")
            self.tag_lbl.setText("\U0001F4C5 TIMETABLE TASK ALERT")
            self.tag_lbl.setStyleSheet(f"color: {accent}; font-size: 12px; font-weight: 800; letter-spacing: 1px; background: transparent;")
            self.glow_effect.setColor(QColor(56, 189, 248, 120))
            self.mark_done_btn.show()
        else:
            self.icon_lbl.setText("\U0001F514")
            self.tag_lbl.setText("\U0001F514 ALARM ALERT")
            self.tag_lbl.setStyleSheet("color: #ef4444; font-size: 12px; font-weight: 800; letter-spacing: 1px; background: transparent;")
            self.glow_effect.setColor(QColor(239, 68, 68, 120))
            self.mark_done_btn.hide()

        self.headline_lbl.setText(f"{time_str} • {title}")

        if days:
            if len(days) == 7 or set(days) == {"Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"}:
                days_str = "Repeats: Daily"
            elif len(days) == 5 and set(days) == {"Mon", "Tue", "Wed", "Thu", "Fri"}:
                days_str = "Repeats: Weekdays (Mon–Fri)"
            else:
                days_str = f"Repeats: {', '.join(days)}"
        else:
            days_str = "One-Time Alert"

        self.details_lbl.setText(days_str)
        self.update_pill_styles(accent, self.theme_mode)

    def on_mark_done_clicked(self):
        print(f"[AlarmBannerModalCard]: Mark Done button clicked! alarm_data={self.alarm_data}", flush=True)
        self.countdown_timer.stop()
        self.mark_done_requested.emit(self.alarm_data)


class NotificationBannerModalCard(QFrame):
    """Full-Window Takeover Notification Banner Card for Priority Apps."""
    open_requested = pyqtSignal(dict)
    dismiss_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("notif_full_takeover_card")
        self.notif_data = {}
        self.theme_mode = "dark"
        self.total_autodismiss_ms = 3000
        self.remaining_autodismiss_ms = 3000
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(6)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # 1. Hero App Badge & Icon
        self.icon_frame = QWidget()
        self.icon_frame.setFixedSize(60, 44)
        icon_box = QVBoxLayout(self.icon_frame)
        icon_box.setContentsMargins(0, 0, 0, 0)
        icon_box.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.app_icon_lbl = QLabel("🔔")
        self.app_icon_lbl.setStyleSheet("font-size: 28px; background: transparent;")
        self.app_icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_box.addWidget(self.app_icon_lbl, 0, Qt.AlignmentFlag.AlignCenter)

        self.tag_lbl = QLabel("🔔 NOTIFICATION")
        self.tag_lbl.setStyleSheet("color: #38bdf8; font-size: 11px; font-weight: 800; letter-spacing: 1px; background: transparent;")
        self.tag_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # 2. Title & Message Headline
        self.headline_lbl = QLabel("Notification Title")
        self.headline_lbl.setWordWrap(True)
        self.headline_lbl.setStyleSheet("color: #f8fafc; font-size: 14px; font-weight: 800; background: transparent;")
        self.headline_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.body_lbl = QLabel("Message body text snippet goes here...")
        self.body_lbl.setWordWrap(True)
        self.body_lbl.setStyleSheet("color: #cbd5e1; font-size: 10.5px; font-weight: 500; background: transparent;")
        self.body_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(self.icon_frame, 0, Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.tag_lbl)
        layout.addWidget(self.headline_lbl)
        layout.addWidget(self.body_lbl)
        layout.addSpacing(4)

        # 3. Action Bar (Open + Dismiss)
        action_bar = QHBoxLayout()
        action_bar.setSpacing(8)
        action_bar.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.open_btn = QPushButton("↗️ Open")
        self.open_btn.setFixedHeight(28)
        self.open_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.open_btn.setStyleSheet("QPushButton { background: #38bdf8; color: #ffffff; border: none; border-radius: 6px; font-size: 10.5px; font-weight: 800; padding: 0 16px; } QPushButton:hover { background: #0284c7; }")
        self.open_btn.clicked.connect(self.on_open_clicked)

        self.dismiss_btn = QPushButton("✕ Dismiss")
        self.dismiss_btn.setFixedHeight(28)
        self.dismiss_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.dismiss_btn.setStyleSheet("QPushButton { background: rgba(255, 255, 255, 0.08); color: #cbd5e1; border: 1px solid rgba(255, 255, 255, 0.15); border-radius: 6px; font-size: 10.5px; font-weight: 700; padding: 0 14px; } QPushButton:hover { background: #ef4444; color: #ffffff; border-color: #ef4444; }")
        self.dismiss_btn.clicked.connect(self.dismiss_requested.emit)

        action_bar.addWidget(self.open_btn)
        action_bar.addWidget(self.dismiss_btn)
        layout.addLayout(action_bar)

        # 4. Thin Depleting Countdown Progress Bar
        self.dismiss_progress_bar = QProgressBar()
        self.dismiss_progress_bar.setFixedHeight(3)
        self.dismiss_progress_bar.setRange(0, 1000)
        self.dismiss_progress_bar.setValue(1000)
        self.dismiss_progress_bar.setTextVisible(False)
        layout.addWidget(self.dismiss_progress_bar)

        self.countdown_timer = QTimer(self)
        self.countdown_timer.setInterval(40)
        self.countdown_timer.timeout.connect(self.on_countdown_tick)

    def set_notification_data(self, notif: dict, autodismiss_sec: int = 3, accent_color: str = "#38bdf8", mode: str = "dark"):
        self.notif_data = notif
        self.theme_mode = mode
        self.total_autodismiss_ms = max(2000, autodismiss_sec * 1000)
        self.remaining_autodismiss_ms = self.total_autodismiss_ms

        app_name = notif.get("app", "Notification")
        title = notif.get("title", "")
        body = notif.get("body", "")

        self.tag_lbl.setText(f"🔔 {app_name.upper()} NOTIFICATION")
        self.headline_lbl.setText(title if title else app_name)
        self.body_lbl.setText(body if body else "New notification received.")

        pal = THEME_PALETTES.get(mode, THEME_PALETTES["dark"])
        self.tag_lbl.setStyleSheet(f"color: {accent_color}; font-size: 11px; font-weight: 800; letter-spacing: 1px; background: transparent;")
        self.headline_lbl.setStyleSheet(f"color: {pal['text_primary']}; font-size: 14px; font-weight: 800; background: transparent;")
        self.body_lbl.setStyleSheet(f"color: {pal['text_secondary']}; font-size: 10.5px; font-weight: 500; background: transparent;")
        self.open_btn.setStyleSheet(f"QPushButton {{ background: {accent_color}; color: #ffffff; border: none; border-radius: 6px; font-size: 10.5px; font-weight: 800; padding: 0 16px; }}")

        self.dismiss_progress_bar.setStyleSheet(f"QProgressBar {{ background: {pal['input_bg']}; border-radius: 1.5px; border: none; }} QProgressBar::chunk {{ background: {accent_color}; border-radius: 1.5px; }}")
        self.dismiss_progress_bar.setValue(1000)
        self.countdown_timer.start()

    def on_countdown_tick(self):
        self.remaining_autodismiss_ms -= self.countdown_timer.interval()
        if self.remaining_autodismiss_ms <= 0:
            self.countdown_timer.stop()
            self.dismiss_requested.emit()
        else:
            fraction = self.remaining_autodismiss_ms / float(self.total_autodismiss_ms)
            self.dismiss_progress_bar.setValue(int(fraction * 1000))

    def on_open_clicked(self):
        self.countdown_timer.stop()
        self.open_requested.emit(self.notif_data)

    def apply_theme(self, accent_color: str, mode: str = "dark"):
        self.theme_mode = mode
        pal = THEME_PALETTES.get(mode, THEME_PALETTES["dark"])
        self.tag_lbl.setStyleSheet(f"color: {accent_color}; font-size: 11px; font-weight: 800; letter-spacing: 1px; background: transparent;")
        self.headline_lbl.setStyleSheet(f"color: {pal['text_primary']}; font-size: 14px; font-weight: 800; background: transparent;")
        self.body_lbl.setStyleSheet(f"color: {pal['text_secondary']}; font-size: 10.5px; font-weight: 500; background: transparent;")
        self.open_btn.setStyleSheet(f"QPushButton {{ background: {accent_color}; color: #ffffff; border: none; border-radius: 6px; font-size: 10.5px; font-weight: 800; padding: 0 16px; }}")
        self.dismiss_progress_bar.setStyleSheet(f"QProgressBar {{ background: {pal['input_bg']}; border-radius: 1.5px; border: none; }} QProgressBar::chunk {{ background: {accent_color}; border-radius: 1.5px; }}")


class DropZoneCard(GlassPanel):
    """Dedicated Drop Zone Card with OLE Drag & Drop, Liquid Glass aesthetics, and Shelf storage integration."""
    def __init__(self, storage: StorageManager, settings: SettingsManager, parent=None):
        super().__init__(category_key="dropzone", corner_radius=12, parent=parent)
        self.storage = storage
        self.settings = settings
        self.setAcceptDrops(True)
        self.init_ui()

    def init_ui(self):
        mode = self.settings.get("theme_mode", "dark") if self.settings else "dark"
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        b_drop = QVBoxLayout(self)
        b_drop.setContentsMargins(8, 6, 8, 6)
        b_drop.setSpacing(4)

        hdr = make_card_header("Quick Drop Zone", "\U0001F4CE", "dropzone", mode)
        b_drop.addWidget(hdr)

        pal = THEME_PALETTES.get(mode, THEME_PALETTES["dark"])
        accent = resolve_accent_color(self.settings) if self.settings else "#38bdf8"
        self.lbl_hint = QLabel("Drag & drop files or screenshots here to save directly into your Shelf library.")
        self.lbl_hint.setWordWrap(True)
        self.lbl_hint.setStyleSheet(f"color: {pal['text_secondary']}; background: transparent; font-size: 9px; font-style: italic; font-family: 'Segoe UI', sans-serif; letter-spacing: normal;")
        b_drop.addWidget(self.lbl_hint)

        # Quick Screen Snipping Button
        self.btn_snip = QPushButton("✂️ Quick Screen Snip")
        self.btn_snip.setFixedHeight(22)
        self.btn_snip.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_snip.setStyleSheet(f"QPushButton {{ background-color: {pal['input_bg']}; color: {pal['text_primary']}; border: 1px solid {pal['input_border']}; border-radius: 4px; font-size: 9px; font-weight: bold; padding: 0 8px; }} QPushButton:hover {{ border: 1px solid {accent}; color: {accent}; }}")
        self.btn_snip.clicked.connect(self.trigger_screen_snip)
        b_drop.addWidget(self.btn_snip)

        if hasattr(self.storage, 'fileshelf_changed'):
            self.storage.fileshelf_changed.connect(self.refresh_shelf_status)
        self.refresh_shelf_status()

    def trigger_screen_snip(self):
        try:
            import subprocess
            subprocess.Popen(["cmd", "/c", "start", "ms-screenclip:"])
        except Exception as e:
            print(f"[Screenclip Trigger Error]: {e}")

    def refresh_shelf_status(self):
        try:
            from PyQt6.sip import isdeleted
            if isdeleted(self):
                return
            shelf = self.storage.load_shelf()
            pal = THEME_PALETTES.get(self.settings.get("theme_mode", "dark") if self.settings else "dark", THEME_PALETTES["dark"])
            if shelf:
                last_item = shelf[0]
                name = last_item.get("name", "File") if isinstance(last_item, dict) else str(last_item)
                count = len(shelf)
                self.lbl_hint.setText(f"📥 Saved '{name}' ({count} item{'s' if count != 1 else ''} in Shelf)")
                self.lbl_hint.setStyleSheet(f"color: {resolve_accent_color(self.settings) if self.settings else '#38bdf8'}; background: transparent; font-size: 9px; font-weight: 700; font-family: 'Segoe UI', sans-serif;")
            else:
                self.lbl_hint.setText("Drag & drop files or screenshots here to save directly into your Shelf library.")
                self.lbl_hint.setStyleSheet(f"color: {pal['text_secondary']}; background: transparent; font-size: 9px; font-style: italic; font-family: 'Segoe UI', sans-serif;")
        except Exception as e:
            print(f"[Drop Zone Status Exception]: {e}")

    def apply_theme(self, accent_color: str, mode: str = "dark"):
        super().apply_theme(accent_color, mode)
        pal = THEME_PALETTES.get(mode, THEME_PALETTES["dark"])
        if hasattr(self, 'btn_snip'):
            self.btn_snip.setStyleSheet(f"QPushButton {{ background-color: {pal['input_bg']}; color: {pal['text_primary']}; border: 1px solid {pal['input_border']}; border-radius: 4px; font-size: 9px; font-weight: bold; padding: 0 8px; }} QPushButton:hover {{ border: 1px solid {accent_color}; color: {accent_color}; }}")
        self.refresh_shelf_status()

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls() or event.mimeData().hasText():
            print("[Drop Zone DragEnter]: File dragged over Drop Zone widget!")
            self.is_hovered = True
            self.update()
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls() or event.mimeData().hasText():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        self.is_hovered = False
        self.update()
        super().dragLeaveEvent(event)

    def dropEvent(self, event):
        self.is_hovered = False
        self.update()
        if event.mimeData().hasUrls():
            saved_count = 0
            for url in event.mimeData().urls():
                fp = url.toLocalFile()
                if fp and os.path.exists(fp):
                    print(f"[Drop Zone DropEvent]: Saved file to shelf: {fp}")
                    self.storage.add_shelf_file(fp)
                    saved_count += 1
            if saved_count > 0:
                self.refresh_shelf_status()
                event.acceptProposedAction()
            else:
                event.ignore()
        else:
            event.ignore()


class PomodoroFocusWidget(GlassPanel):
    """Pomodoro & Focus Countdown Timer Widget with visual countdown, mode tabs, progress tracking, and Liquid Glass styling."""
    pomo_tick = pyqtSignal(str, bool)

    def __init__(self, settings: SettingsManager = None, parent=None):
        super().__init__(category_key="alarms", corner_radius=12, parent=parent)
        self.settings = settings
        self.current_mode = "focus"
        self.total_seconds = 25 * 60
        self.remaining_seconds = 25 * 60
        self.is_running = False
        self.sessions_completed = 0
        self.theme_mode = "dark"

        self.timer = QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.on_timer_tick)

        self.init_ui()

    def init_ui(self):
        mode = self.settings.get("theme_mode", "dark") if self.settings else "dark"
        self.theme_mode = mode
        accent = resolve_accent_color(self.settings) if self.settings else "#38bdf8"
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(4)

        hdr = make_card_header("Focus & Pomodoro", "🍅", "alarms", mode)
        layout.addWidget(hdr)

        pal = THEME_PALETTES.get(mode, THEME_PALETTES["dark"])

        # Mode Selection Tabs
        mode_box = QHBoxLayout()
        mode_box.setSpacing(4)
        self.btn_mode_focus = QPushButton("🍅 Focus")
        self.btn_mode_short = QPushButton("☕ Short")
        self.btn_mode_long = QPushButton("🌴 Long")

        self.mode_buttons = {
            "focus": self.btn_mode_focus,
            "short_break": self.btn_mode_short,
            "long_break": self.btn_mode_long
        }

        for k, btn in self.mode_buttons.items():
            btn.setFixedHeight(18)
            btn.setMinimumWidth(0)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _, m=k: self.set_mode(m))
            mode_box.addWidget(btn, 1)

        layout.addLayout(mode_box)

        # Big Countdown Display + Session Tracker
        display_box = QHBoxLayout()
        self.time_lbl = QLabel("25:00")
        self.time_lbl.setStyleSheet(f"color: {pal['text_primary']}; font-size: 20px; font-weight: 800; font-family: 'Segoe UI', monospace; background: transparent;")

        self.session_lbl = QLabel("🍅 Session 1/4")
        self.session_lbl.setStyleSheet(f"color: {pal['text_secondary']}; font-size: 9px; font-weight: 600; background: transparent;")

        display_box.addWidget(self.time_lbl)
        display_box.addStretch()
        display_box.addWidget(self.session_lbl)
        layout.addLayout(display_box)

        # Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(3)
        self.progress_bar.setRange(0, 1000)
        self.progress_bar.setValue(1000)
        self.progress_bar.setTextVisible(False)
        layout.addWidget(self.progress_bar)

        # Controls Row
        ctrl_box = QHBoxLayout()
        ctrl_box.setSpacing(4)

        self.btn_toggle = QPushButton("▶ Start")
        self.btn_toggle.setFixedHeight(20)
        self.btn_toggle.setMinimumWidth(0)
        self.btn_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_toggle.clicked.connect(self.toggle_timer)

        self.btn_reset = QPushButton("↺ Reset")
        self.btn_reset.setFixedHeight(20)
        self.btn_reset.setMinimumWidth(0)
        self.btn_reset.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_reset.clicked.connect(self.reset_timer)

        self.btn_skip = QPushButton("⏭ Skip")
        self.btn_skip.setFixedHeight(20)
        self.btn_skip.setMinimumWidth(0)
        self.btn_skip.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_skip.clicked.connect(self.skip_cycle)

        ctrl_box.addWidget(self.btn_toggle, 1)
        ctrl_box.addWidget(self.btn_reset, 1)
        ctrl_box.addWidget(self.btn_skip, 1)
        layout.addLayout(ctrl_box)

        self.setMinimumWidth(0)
        self.apply_theme(accent, mode)
        self.set_mode("focus")

    def set_mode(self, mode: str):
        self.timer.stop()
        self.is_running = False
        self.current_mode = mode
        if mode == "focus":
            mins = self.settings.get("pomodoro_focus_min", 25) if self.settings else 25
        elif mode == "short_break":
            mins = self.settings.get("pomodoro_short_break_min", 5) if self.settings else 5
        else:
            mins = self.settings.get("pomodoro_long_break_min", 15) if self.settings else 15

        self.total_seconds = mins * 60
        self.remaining_seconds = self.total_seconds
        self.update_display()
        self.btn_toggle.setText("▶ Start")
        accent = resolve_accent_color(self.settings) if self.settings else "#38bdf8"
        self.apply_theme(accent, self.theme_mode)

    def toggle_timer(self):
        if self.is_running:
            self.timer.stop()
            self.is_running = False
            self.btn_toggle.setText("▶ Resume")
        else:
            self.timer.start()
            self.is_running = True
            self.btn_toggle.setText("⏸ Pause")
        self.update_display()

    def reset_timer(self):
        self.set_mode(self.current_mode)

    def skip_cycle(self):
        if self.current_mode == "focus":
            self.sessions_completed += 1
            if self.sessions_completed % 4 == 0:
                self.set_mode("long_break")
            else:
                self.set_mode("short_break")
        else:
            self.set_mode("focus")
        self.update_session_tracker()

    def on_timer_tick(self):
        if self.remaining_seconds > 0:
            self.remaining_seconds -= 1
            self.update_display()
        else:
            self.timer.stop()
            self.is_running = False
            self.btn_toggle.setText("▶ Start")
            try:
                import winsound
                winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
            except Exception:
                pass
            self.skip_cycle()

    def update_display(self):
        mins = self.remaining_seconds // 60
        secs = self.remaining_seconds % 60
        time_str = f"{mins:02d}:{secs:02d}"
        self.time_lbl.setText(time_str)
        if self.total_seconds > 0:
            ratio = self.remaining_seconds / float(self.total_seconds)
            self.progress_bar.setValue(int(ratio * 1000))
        self.pomo_tick.emit(time_str, self.is_running)

    def update_session_tracker(self):
        s_num = (self.sessions_completed % 4) + 1
        self.session_lbl.setText(f"🍅 Session {s_num}/4")

    def apply_theme(self, accent_color: str, mode: str = "dark"):
        super().apply_theme(accent_color, mode)
        pal = THEME_PALETTES.get(mode, THEME_PALETTES["dark"])
        is_dark = (mode == "dark")
        sub_btn_bg = "rgba(255, 255, 255, 0.08)" if is_dark else "rgba(0, 0, 0, 0.05)"
        sub_btn_border = "rgba(255, 255, 255, 0.12)" if is_dark else "rgba(0, 0, 0, 0.08)"
        sub_btn_hover = "rgba(255, 255, 255, 0.16)" if is_dark else "rgba(0, 0, 0, 0.10)"

        if hasattr(self, 'time_lbl'):
            self.time_lbl.setStyleSheet(f"color: {pal['text_primary']}; font-size: 20px; font-weight: 800; font-family: 'Segoe UI', monospace; background: transparent;")
        if hasattr(self, 'session_lbl'):
            self.session_lbl.setStyleSheet(f"color: {pal['text_secondary']}; font-size: 9px; font-weight: 600; background: transparent;")

        if hasattr(self, 'btn_toggle'):
            self.btn_toggle.setStyleSheet(f"QPushButton {{ background-color: {accent_color}; color: #ffffff; font-weight: 800; border-radius: 6px; border: 1px solid rgba(255, 255, 255, 0.35); font-size: 9.5px; padding: 0 8px; }}")
        if hasattr(self, 'btn_reset'):
            self.btn_reset.setStyleSheet(f"QPushButton {{ background-color: {sub_btn_bg}; color: {pal['text_primary']}; border-radius: 6px; border: 1px solid {sub_btn_border}; font-size: 9.5px; font-weight: 600; padding: 0 6px; }} QPushButton:hover {{ background-color: {sub_btn_hover}; border: 1px solid rgba(255, 255, 255, 0.25); }}")
        if hasattr(self, 'btn_skip'):
            self.btn_skip.setStyleSheet(f"QPushButton {{ background-color: {sub_btn_bg}; color: {pal['text_primary']}; border-radius: 6px; border: 1px solid {sub_btn_border}; font-size: 9.5px; font-weight: 600; padding: 0 6px; }} QPushButton:hover {{ background-color: {sub_btn_hover}; border: 1px solid rgba(255, 255, 255, 0.25); }}")

        if hasattr(self, 'mode_buttons'):
            for k, btn in self.mode_buttons.items():
                if k == self.current_mode:
                    btn.setStyleSheet(f"QPushButton {{ background-color: {accent_color}; color: #ffffff; font-weight: 800; border-radius: 9px; border: 1px solid rgba(255, 255, 255, 0.40); font-size: 9px; padding: 0 6px; }}")
                else:
                    btn.setStyleSheet(f"QPushButton {{ background-color: {sub_btn_bg}; color: {pal['text_secondary']}; border-radius: 9px; border: 1px solid {sub_btn_border}; font-size: 9px; font-weight: 600; padding: 0 6px; }} QPushButton:hover {{ background-color: {sub_btn_hover}; color: {pal['text_primary']}; border: 1px solid rgba(255, 255, 255, 0.25); }}")

        if hasattr(self, 'progress_bar'):
            self.progress_bar.setStyleSheet(f"QProgressBar {{ background: {sub_btn_bg}; border: none; border-radius: 1.5px; }} QProgressBar::chunk {{ background: {accent_color}; border-radius: 1.5px; }}")


# 1. HOME LANDING VIEW (USER-SELECTABLE QUICK NOTES PINNING & REAL-TIME SYNC)
class HomeLandingTabWidget(QWidget):
    pomo_tick_relayed = pyqtSignal(str, bool)

    def __init__(self, storage: StorageManager, settings: SettingsManager, parent=None):
        super().__init__(parent)
        self.storage = storage
        self.settings = settings
        self.home_notes_edits = {}  # filename -> QTextEdit
        self.init_ui()

        # Real-time note sync & pin change signals
        self.storage.note_content_changed.connect(self.on_storage_note_changed)
        self.storage.home_pins_changed.connect(self.refresh_home_widgets)
        self.storage.timetable_changed.connect(self.refresh_home_widgets)
        self.storage.alarms_changed.connect(self.refresh_home_widgets)
        self.storage.calendar_changed.connect(self.refresh_home_widgets)

    def closeEvent(self, event):
        try:
            self.refresh_home_widgets()
            try:
                self.storage.note_content_changed.disconnect(self.on_storage_note_changed)
            except Exception:
                pass
            try:
                self.storage.home_pins_changed.disconnect(self.refresh_home_widgets)
            except Exception:
                pass
            try:
                self.storage.timetable_changed.disconnect(self.refresh_home_widgets)
            except Exception:
                pass
            try:
                self.storage.alarms_changed.disconnect(self.refresh_home_widgets)
            except Exception:
                pass
            try:
                self.storage.calendar_changed.disconnect(self.refresh_home_widgets)
            except Exception:
                pass
        except Exception:
            pass
        super().closeEvent(event)

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        accent = resolve_accent_color(self.settings)
        mode = self.settings.get("theme_mode", "dark")

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setStyleSheet(f"QScrollArea, QScrollArea > QWidget > QWidget {{ border: none; background: transparent; }} {get_scrollbar_qss(accent, mode)}")
        if self.scroll.viewport():
            self.scroll.viewport().setStyleSheet("background: transparent;")

        self.content_widget = QWidget()
        self.content_widget.setStyleSheet("background: transparent;")
        self.content_layout = QGridLayout(self.content_widget)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(8)

        self.refresh_home_widgets()

        self.scroll.setWidget(self.content_widget)
        layout.addWidget(self.scroll)

    def apply_theme(self, accent_color: str, mode: str = "dark"):
        print(f"[SIGNAL] HomeLandingTabWidget RECEIVED apply_theme: mode={mode}, accent={accent_color}", flush=True)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setStyleSheet(f"QScrollArea, QScrollArea > QWidget > QWidget {{ border: none; background: transparent; }} {get_scrollbar_qss(accent_color, mode)}")
        if self.scroll.viewport():
            self.scroll.viewport().setStyleSheet("background: transparent;")
        self.content_widget.setStyleSheet("background: transparent;")

        # Lightweight in-place styling of existing child widgets without full grid teardown
        for i in range(self.content_layout.count()):
            item = self.content_layout.itemAt(i)
            if item and item.widget():
                w = item.widget()
                if hasattr(w, "apply_theme"):
                    try:
                        w.apply_theme(accent_color, mode)
                    except Exception:
                        pass
                for child_glass in w.findChildren(GlassPanel):
                    try:
                        child_glass.apply_theme(accent_color, mode)
                    except Exception:
                        pass

    def on_storage_note_changed(self, note_id: str, content: str):
        home_pinned = self.storage.get_home_pinned_notes()
        target_note = next((n for n in home_pinned if n.get("id") == note_id), None)
        if target_note:
            fname = target_note.get("filename")
            if fname in self.home_notes_edits:
                editor = self.home_notes_edits[fname]
                if not editor.hasFocus():
                    if editor.toPlainText() != content:
                        cursor = editor.textCursor()
                        pos = cursor.position()
                        editor.blockSignals(True)
                        editor.setPlainText(content)
                        cursor.setPosition(min(pos, len(content)))
                        editor.setTextCursor(cursor)
                        editor.blockSignals(False)

    def refresh_home_widgets(self):
        from PyQt6.sip import isdeleted
        if isdeleted(self):
            return

        self.home_notes_edits.clear()
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            w = item.widget()
            if w and not isdeleted(w):
                try:
                    for child_timer in w.findChildren(QTimer):
                        try:
                            child_timer.stop()
                        except Exception:
                            pass
                    for child_worker in w.findChildren(QThread):
                        try:
                            if hasattr(child_worker, 'stop'):
                                child_worker.stop()
                            child_worker.quit()
                            child_worker.wait(200)
                        except Exception:
                            pass
                    if hasattr(w, 'worker_thread') and w.worker_thread:
                        try:
                            w.worker_thread.stop()
                            w.worker_thread.quit()
                            w.worker_thread.wait(200)
                        except Exception:
                            pass
                    if hasattr(self.storage, 'fileshelf_changed') and hasattr(w, 'refresh_shelf_status'):
                        try:
                            self.storage.fileshelf_changed.disconnect(w.refresh_shelf_status)
                        except Exception:
                            pass
                except Exception:
                    pass
                w.deleteLater()

        accent = resolve_accent_color(self.settings)
        mode = self.settings.get("theme_mode", "dark")
        pal = THEME_PALETTES.get(mode, THEME_PALETTES["dark"])

        alarms = self.storage.load_alarms()
        enabled_alarms = [a for a in alarms if a.get('enabled', True)]
        timetable = self.storage.load_timetable()
        cal_data = self.storage.load_calendar()
        today_str = datetime.now().strftime("%Y-%m-%d")
        today_events = cal_data.get(today_str, [])

        enabled_cards = []
        card_tt_ref = None

        # 1. Alarms Preview Card
        if self.settings.get("show_home_alarms", True):
            card_alarm = GlassPanel(category_key="alarms", corner_radius=12)
            card_alarm.apply_theme(accent, mode)
            card_alarm.setMinimumWidth(0)
            card_alarm.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            b_alarm = QVBoxLayout(card_alarm)
            b_alarm.setContentsMargins(8, 6, 8, 6)
            b_alarm.setSpacing(4)

            hdr = make_card_header("Upcoming Alarms", "🔔", "alarms", mode)
            b_alarm.addWidget(hdr)

            is_12h = self.settings.get("time_format_12h", True)
            if enabled_alarms:
                for al in enabled_alarms[:4]:
                    disp_time = format_alarm_time(al.get('time', '00:00'), is_12h)
                    lbl_item = ElidedLabel(f"• {disp_time}  -  {al.get('label', 'Alarm')}")
                    lbl_item.setStyleSheet(f"color: {pal['text_primary']}; background: transparent; font-size: 9.5px; font-weight: 600; font-family: 'Segoe UI', sans-serif; letter-spacing: normal;")
                    b_alarm.addWidget(lbl_item)
            else:
                b_alarm.addWidget(make_empty_state("\U0001F514", "You're all clear!", "No active alarms scheduled for today.", mode))

            enabled_cards.append((card_alarm, False))

        # 2. Timetable Tasks Preview Card
        if self.settings.get("show_home_timetable", True):
            card_tt = GlassPanel(category_key="timetable", corner_radius=12)
            card_tt.apply_theme(accent, mode)
            card_tt.setMinimumWidth(0)
            card_tt.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            b_tt = QVBoxLayout(card_tt)
            b_tt.setContentsMargins(8, 6, 8, 6)
            b_tt.setSpacing(4)

            hdr = make_card_header("Today's Timetable", "\U0001F4C5", "timetable", mode)
            b_tt.addWidget(hdr)

            if timetable:
                columns_container = QWidget()
                columns_container.setMinimumWidth(0)
                columns_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
                columns_container.setStyleSheet("background: transparent;")
                cols_box = QHBoxLayout(columns_container)
                cols_box.setContentsMargins(0, 0, 0, 0)
                cols_box.setSpacing(6)

                half = (len(timetable) + 1) // 2
                col1_tasks = timetable[:half]
                col2_tasks = timetable[half:]

                is_12h = self.settings.get("time_format_12h", True)
                font_sz = 9 if len(timetable) > 10 else 9.5
                row_pad = 1 if len(timetable) > 10 else 2

                col1_widget = QWidget()
                col1_widget.setMinimumWidth(0)
                col1_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
                col1_widget.setStyleSheet("background: transparent;")
                c1_box = QVBoxLayout(col1_widget)
                c1_box.setContentsMargins(0, 0, 0, 0)
                c1_box.setSpacing(2)

                for task in col1_tasks:
                    task_id = str(task.get("id") or task.get("title", ""))
                    title_txt = task.get("title", "Task")
                    time_txt = format_alarm_time(task.get("time", "00:00"), is_12h)
                    done = bool(task.get("is_completed", task.get("completed", False)))

                    row = QWidget()
                    row.setMinimumWidth(0)
                    row.setStyleSheet("background: transparent;")
                    r_box = QHBoxLayout(row)
                    r_box.setContentsMargins(0, row_pad, 0, row_pad)
                    r_box.setSpacing(3)

                    btn_mark = QPushButton("✓" if done else "○")
                    btn_mark.setFixedSize(16, 16)
                    btn_mark.setCursor(Qt.CursorShape.PointingHandCursor)
                    btn_mark.setToolTip("Mark Incomplete" if done else "Mark Completed")
                    btn_mark.setStyleSheet(f"QPushButton {{ background: transparent; color: {'#10b981' if done else pal['text_muted']}; border: none; font-size: {font_sz + 1}px; font-weight: bold; padding: 0; }} QPushButton:hover {{ color: #10b981; }}")
                    btn_mark.clicked.connect(lambda _, tid=task_id, curr_done=done: self.storage.toggle_timetable_task(tid, not curr_done))

                    lbl_time = QLabel(time_txt)
                    lbl_time.setStyleSheet(f"color: {accent}; font-size: {font_sz}px; font-weight: 700; background: transparent;")

                    lbl_title = ElidedLabel(title_txt)
                    if done:
                        lbl_title.setStyleSheet(f"color: {pal['text_muted']}; font-size: {font_sz}px; font-weight: 500; background: transparent; text-decoration: line-through;")
                    else:
                        lbl_title.setStyleSheet(f"color: {pal['text_primary']}; font-size: {font_sz}px; font-weight: 600; background: transparent;")

                    btn_del_tt = QPushButton("×")
                    btn_del_tt.setFixedSize(14, 14)
                    btn_del_tt.setCursor(Qt.CursorShape.PointingHandCursor)
                    btn_del_tt.setToolTip("Delete Task")
                    btn_del_tt.setStyleSheet("QPushButton { background: transparent; color: rgba(239, 68, 68, 0.6); border: none; font-size: 11px; font-weight: bold; padding: 0; } QPushButton:hover { color: #ef4444; background: rgba(239, 68, 68, 0.18); border-radius: 2px; }")
                    btn_del_tt.clicked.connect(lambda _, tid=task_id: self.storage.delete_timetable_task(tid))

                    r_box.addWidget(btn_mark)
                    r_box.addWidget(lbl_time)
                    r_box.addWidget(lbl_title, 1)
                    r_box.addWidget(btn_del_tt)
                    c1_box.addWidget(row)

                col2_widget = QWidget()
                col2_widget.setMinimumWidth(0)
                col2_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
                col2_widget.setStyleSheet("background: transparent;")
                c2_box = QVBoxLayout(col2_widget)
                c2_box.setContentsMargins(0, 0, 0, 0)
                c2_box.setSpacing(2)

                for task in col2_tasks:
                    task_id = str(task.get("id") or task.get("title", ""))
                    title_txt = task.get("title", "Task")
                    time_txt = format_alarm_time(task.get("time", "00:00"), is_12h)
                    done = bool(task.get("is_completed", task.get("completed", False)))

                    row = QWidget()
                    row.setMinimumWidth(0)
                    row.setStyleSheet("background: transparent;")
                    r_box = QHBoxLayout(row)
                    r_box.setContentsMargins(0, row_pad, 0, row_pad)
                    r_box.setSpacing(3)

                    btn_mark = QPushButton("✓" if done else "○")
                    btn_mark.setFixedSize(16, 16)
                    btn_mark.setCursor(Qt.CursorShape.PointingHandCursor)
                    btn_mark.setToolTip("Mark Incomplete" if done else "Mark Completed")
                    btn_mark.setStyleSheet(f"QPushButton {{ background: transparent; color: {'#10b981' if done else pal['text_muted']}; border: none; font-size: {font_sz + 1}px; font-weight: bold; padding: 0; }} QPushButton:hover {{ color: #10b981; }}")
                    btn_mark.clicked.connect(lambda _, tid=task_id, curr_done=done: self.storage.toggle_timetable_task(tid, not curr_done))

                    lbl_time = QLabel(time_txt)
                    lbl_time.setStyleSheet(f"color: {accent}; font-size: {font_sz}px; font-weight: 700; background: transparent;")

                    lbl_title = ElidedLabel(title_txt)
                    if done:
                        lbl_title.setStyleSheet(f"color: {pal['text_muted']}; font-size: {font_sz}px; font-weight: 500; background: transparent; text-decoration: line-through;")
                    else:
                        lbl_title.setStyleSheet(f"color: {pal['text_primary']}; font-size: {font_sz}px; font-weight: 600; background: transparent;")

                    btn_del_tt = QPushButton("×")
                    btn_del_tt.setFixedSize(14, 14)
                    btn_del_tt.setCursor(Qt.CursorShape.PointingHandCursor)
                    btn_del_tt.setToolTip("Delete Task")
                    btn_del_tt.setStyleSheet("QPushButton { background: transparent; color: rgba(239, 68, 68, 0.6); border: none; font-size: 11px; font-weight: bold; padding: 0; } QPushButton:hover { color: #ef4444; background: rgba(239, 68, 68, 0.18); border-radius: 2px; }")
                    btn_del_tt.clicked.connect(lambda _, tid=task_id: self.storage.delete_timetable_task(tid))

                    r_box.addWidget(btn_mark)
                    r_box.addWidget(lbl_time)
                    r_box.addWidget(lbl_title, 1)
                    r_box.addWidget(btn_del_tt)
                    c2_box.addWidget(row)

                c1_box.addStretch()
                c2_box.addStretch()
                cols_box.addWidget(col1_widget, 1)
                cols_box.addWidget(col2_widget, 1)
                b_tt.addWidget(columns_container)
            else:
                b_tt.addWidget(make_empty_state("\u2615", "Open Schedule", "No tasks scheduled for today — enjoy your time!", mode))

            card_tt_ref = card_tt
            enabled_cards.append((card_tt, False))

        # 3. Calendar Events Card
        if self.settings.get("show_home_calendar", True) and today_events:
            card_cal = GlassPanel(category_key="calendar", corner_radius=12)
            card_cal.apply_theme(accent, mode)
            card_cal.setMinimumWidth(0)
            card_cal.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
            b_cal = QVBoxLayout(card_cal)
            b_cal.setContentsMargins(8, 6, 8, 6)
            b_cal.setSpacing(2)

            hdr = make_card_header("Calendar Events", "\U0001F4C5", "calendar", mode)
            b_cal.addWidget(hdr)

            is_12h = self.settings.get("time_format_12h", True)
            for ev in today_events[:4]:
                ev_id = ev.get('id') if isinstance(ev, dict) else str(ev)
                ev_title = ev.get('title', 'Event') if isinstance(ev, dict) else str(ev)
                ev_time = ev.get('time', '') if isinstance(ev, dict) else ''

                row = QWidget()
                row.setMinimumWidth(0)
                row.setStyleSheet("background: transparent;")
                r_box = QHBoxLayout(row)
                r_box.setContentsMargins(0, 1, 0, 1)
                r_box.setSpacing(4)

                lbl_bullet = QLabel("•")
                lbl_bullet.setStyleSheet(f"color: {accent}; font-size: 10px; font-weight: bold; background: transparent;")
                r_box.addWidget(lbl_bullet)

                if ev_time:
                    lbl_t = QLabel(format_alarm_time(ev_time, is_12h))
                    lbl_t.setStyleSheet(f"color: {accent}; font-size: 9.5px; font-weight: 700; background: transparent;")
                    r_box.addWidget(lbl_t)

                lbl_ev = ElidedLabel(ev_title)
                lbl_ev.setStyleSheet(f"color: {pal['text_primary']}; background: transparent; font-size: 9.5px; font-weight: 600; font-family: 'Segoe UI', sans-serif; letter-spacing: normal;")
                r_box.addWidget(lbl_ev, 1)

                btn_del_ev = QPushButton("×")
                btn_del_ev.setFixedSize(14, 14)
                btn_del_ev.setCursor(Qt.CursorShape.PointingHandCursor)
                btn_del_ev.setToolTip("Delete Event")
                btn_del_ev.setStyleSheet("QPushButton { background: transparent; color: rgba(239, 68, 68, 0.6); border: none; font-size: 11px; font-weight: bold; padding: 0; } QPushButton:hover { color: #ef4444; background: rgba(239, 68, 68, 0.18); border-radius: 2px; }")
                btn_del_ev.clicked.connect(lambda _, eid=ev_id, dstr=today_str: self.storage.delete_calendar_event(dstr, eid))
                r_box.addWidget(btn_del_ev)

                b_cal.addWidget(row)

            b_cal.addStretch()
            enabled_cards.append((card_cal, False))

        # 4. User-Selectable Quick Notes Cards (Up to 2 Pinned Notes)
        if self.settings.get("show_home_notes", True):
            home_pinned = self.storage.get_home_pinned_notes()

            if not home_pinned:
                card_notes_empty = GlassPanel(category_key="notes", corner_radius=12)
                card_notes_empty.apply_theme(accent, mode)
                card_notes_empty.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
                b_ne = QVBoxLayout(card_notes_empty)
                b_ne.setContentsMargins(8, 6, 8, 6)
                b_ne.setSpacing(4)

                hdr = make_card_header("Quick Notes", "\U0001F4DD", "notes", mode)
                b_ne.addWidget(hdr)
                b_ne.addWidget(make_empty_state("\U0001F4CD", "No Notes Pinned to Home", "Pin up to 2 notes from the Notes tab using the \U0001F4CD button.", mode))

                enabled_cards.append((card_notes_empty, False))
            else:
                notes_container = QWidget()
                notes_container.setMinimumWidth(0)
                notes_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
                notes_container.setStyleSheet("background: transparent;")
                nc_layout = QHBoxLayout(notes_container)
                nc_layout.setContentsMargins(0, 0, 0, 0)
                nc_layout.setSpacing(6)

                for note_data in home_pinned[:2]:
                    fname = note_data.get("filename", "")
                    title = note_data.get("title", "Quick Note")

                    card_note = GlassPanel(category_key="notes", corner_radius=12)
                    card_note.apply_theme(accent, mode)
                    card_note.setMinimumWidth(0)
                    card_note.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
                    b_note = QVBoxLayout(card_note)
                    b_note.setContentsMargins(8, 6, 8, 6)
                    b_note.setSpacing(4)

                    hdr = make_card_header(title, "\U0001F4DD", "notes", mode)
                    b_note.addWidget(hdr)

                    editor = QTextEdit()
                    editor.setMinimumHeight(24)
                    editor.setMinimumWidth(0)
                    editor.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
                    editor.setPlaceholderText("Type your note content here...")
                    editor.setStyleSheet(f"QTextEdit {{ background: {pal['input_bg']}; border: 1px solid {pal['input_border']}; border-radius: 5px; color: {pal['text_primary']}; font-size: 9px; font-weight: 500; font-family: 'Segoe UI', sans-serif; letter-spacing: normal; padding: 4px; }} {get_scrollbar_qss(accent, mode)}")
                    editor.blockSignals(True)
                    editor.setPlainText(self.storage.load_note_content(fname))
                    editor.blockSignals(False)
                    editor.textChanged.connect(lambda f=fname, ed=editor: self.on_pinned_note_changed(f, ed.toPlainText()))

                    self.home_notes_edits[fname] = editor
                    b_note.addWidget(editor)
                    nc_layout.addWidget(card_note, 1)

                enabled_cards.append((notes_container, False))

            # 5. Full Rich Now Playing Media Transport Card (Home Module)
        if self.settings.get("show_home_now_playing", True):
            card_np = NowPlayingWidget(self.settings, compact=True)
            enabled_cards.append((card_np, True))

        # 6. Compact Recent Notifications Card (Home Module)
        if self.settings.get("show_home_notifications", True):
            card_notif = GlassPanel(category_key="alarms", corner_radius=12)
            card_notif.apply_theme(accent, mode)
            card_notif.setMinimumWidth(0)
            card_notif.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            b_notif = QVBoxLayout(card_notif)
            b_notif.setContentsMargins(8, 6, 8, 6)
            b_notif.setSpacing(4)

            try:
                res = SystemMonitor.get_windows_notifications()
                notifs = res.get("notifications", []) if isinstance(res, dict) else []
            except Exception:
                notifs = []

            if notifs:
                for n in notifs[:2]:
                    lbl_n = ElidedLabel(f"• [{n.get('app_name')}] {n.get('title')}")
                    lbl_n.setStyleSheet(f"color: {pal['text_primary']}; font-size: 9.5px; font-weight: 600; background: transparent;")
                    b_notif.addWidget(lbl_n)
            else:
                b_notif.addWidget(make_empty_state("\U0001F514", "Clear Inbox", "No recent notifications", mode))

            enabled_cards.append((card_notif, False))

        # 7. Pomodoro & Focus Timer Card
        if self.settings.get("show_home_pomodoro", True):
            card_pomo = PomodoroFocusWidget(self.settings, parent=self)
            card_pomo.setMinimumWidth(0)
            card_pomo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            card_pomo.pomo_tick.connect(self.pomo_tick_relayed.emit)
            enabled_cards.append((card_pomo, False))

        # 8. Drop Zone Card
        if self.settings.get("show_home_dropzone", True):
            card_drop = DropZoneCard(self.storage, self.settings)
            enabled_cards.append((card_drop, True))

        # Dynamically lay out enabled cards into grid positions (row, col)
        curr_row = 0
        curr_col = 0
        timetable_row = -1

        for card_w, span_two in enabled_cards:
            if span_two:
                if curr_col != 0:
                    curr_row += 1
                    curr_col = 0
                self.content_layout.addWidget(card_w, curr_row, 0, 1, 2)
                curr_row += 1
                curr_col = 0
            else:
                if card_w == card_tt_ref:
                    timetable_row = curr_row
                self.content_layout.addWidget(card_w, curr_row, curr_col, 1, 1)
                if curr_col == 0:
                    curr_col = 1
                else:
                    curr_row += 1
                    curr_col = 0

        # Dynamic Row Stretch Reflow based on Timetable demand:
        tt_task_count = len(timetable) if self.settings.get("show_home_timetable", True) else 0
        total_rows = curr_row + (1 if curr_col > 0 else 0)

        for r in range(total_rows):
            if r == timetable_row and tt_task_count > 10:
                self.content_layout.setRowStretch(r, 3)
            elif r == timetable_row and tt_task_count > 5:
                self.content_layout.setRowStretch(r, 2)
            else:
                self.content_layout.setRowStretch(r, 1)

        self.content_layout.setColumnStretch(0, 1)
        self.content_layout.setColumnStretch(1, 1)

    def on_pinned_note_changed(self, filename: str, content: str):
        if filename:
            self.storage.save_note_content(filename, content)
            index = self.storage.load_notes_index()
            note = next((n for n in index if n.get("filename") == filename), None)
            if note:
                self.storage.note_content_changed.emit(note.get("id", ""), content)


# NOW PLAYING REUSABLE COMPONENT
class NowPlayingWidget(GlassPanel):
    """Unified, live-updating Now Playing & Media Transport Widget with Liquid Glass aesthetics."""
    def __init__(self, settings: SettingsManager, compact: bool = False, parent=None):
        super().__init__(category_key="timetable", corner_radius=12, parent=parent)
        self.settings = settings
        self.compact = compact
        self.init_ui()

        # Dedicated background QThread for WinRT media session updates (Zero main thread blocking!)
        from system_monitor import NowPlayingWorkerThread
        self.worker_thread = NowPlayingWorkerThread(interval_ms=1000, parent=self)
        self.worker_thread.media_info_updated.connect(self.update_now_playing_data)
        self.worker_thread.start()

    def stop_worker(self):
        if hasattr(self, 'worker_thread') and self.worker_thread:
            try:
                self.worker_thread.stop()
                self.worker_thread.quit()
                self.worker_thread.wait(200)
            except Exception:
                pass

    def closeEvent(self, event):
        self.stop_worker()
        super().closeEvent(event)

    def init_ui(self):
        mode = self.settings.get("theme_mode", "dark")
        accent = resolve_accent_color(self.settings)
        pal = THEME_PALETTES.get(mode, THEME_PALETTES["dark"])
        chip_bg = f"{accent}26" if mode == "dark" else f"{accent}1e"

        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumWidth(0)

        b_layout = QVBoxLayout(self)
        b_layout.setContentsMargins(8, 6, 8, 6)
        b_layout.setSpacing(4)

        # Header Row
        m_head = QHBoxLayout()
        m_head.setSpacing(4 if self.compact else 6)

        self.chip_media = QLabel("\U0001F3B5")
        self.chip_media.setFixedSize(16 if self.compact else 20, 16 if self.compact else 20)
        self.chip_media.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.chip_media.setStyleSheet(f"QLabel {{ background-color: {chip_bg}; border-radius: 6px; font-size: {'9px' if self.compact else '10px'}; font-family: 'Segoe UI Emoji', 'Segoe UI Symbol', 'Segoe UI', sans-serif; }}")

        self.lbl_m_title = QLabel("NOW PLAYING" if self.compact else "SYSTEM MEDIA TRANSPORT")
        self.lbl_m_title.setStyleSheet(f"color: {accent}; font-size: 9.5px; font-weight: 800; letter-spacing: 0.5px; background: transparent;")

        self.chip_app_name = QLabel("IDLE")
        self.chip_app_name.setStyleSheet(f"color: {accent}; background: {pal['input_bg']}; border: 1px solid {pal['input_border']}; border-radius: 4px; padding: 1px 6px; font-size: 8.5px; font-weight: bold;")

        m_head.addWidget(self.chip_media)
        m_head.addWidget(self.lbl_m_title)
        m_head.addStretch()
        m_head.addWidget(self.chip_app_name)
        b_layout.addLayout(m_head)

        # Track Info Container
        np_box = QHBoxLayout()
        np_box.setSpacing(6 if self.compact else 8)

        self.lbl_artwork = QLabel("\U0001F3B5")
        art_sz = 28 if self.compact else 36
        self.lbl_artwork.setFixedSize(art_sz, art_sz)
        self.lbl_artwork.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_artwork.setStyleSheet(f"QLabel {{ background: {pal['input_bg']}; border: 1px solid {pal['input_border']}; border-radius: 6px; font-size: {'13px' if self.compact else '16px'}; font-family: 'Segoe UI Emoji', 'Segoe UI Symbol', sans-serif; }}")

        np_text_box = QVBoxLayout()
        np_text_box.setSpacing(1)

        self.lbl_track_title = QLabel("Nothing Playing")
        self.lbl_track_title.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.lbl_track_title.setStyleSheet(f"color: {pal['text_primary']}; font-size: {'9.5px' if self.compact else '10.5px'}; font-weight: 800; background: transparent;")

        self.lbl_track_artist = QLabel("Play audio or video in Spotify, Chrome, etc.")
        self.lbl_track_artist.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.lbl_track_artist.setStyleSheet(f"color: {pal['text_secondary']}; font-size: {'8.5px' if self.compact else '9px'}; font-weight: 500; background: transparent;")

        np_text_box.addWidget(self.lbl_track_title)
        np_text_box.addWidget(self.lbl_track_artist)

        np_box.addWidget(self.lbl_artwork)
        np_box.addLayout(np_text_box, 1)
        b_layout.addLayout(np_box)

        # Seek Bar Row
        seek_box = QHBoxLayout()
        seek_box.setContentsMargins(0, 0, 0, 0)
        seek_box.setSpacing(6 if self.compact else 8)

        pos_w = 34 if self.compact else 40
        self.lbl_media_pos = QLabel("0:00")
        self.lbl_media_pos.setFixedWidth(pos_w)
        self.lbl_media_pos.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.lbl_media_pos.setStyleSheet(f"color: {pal['text_secondary']}; font-size: {'8.5px' if self.compact else '9.5px'}; font-weight: 600; padding-right: 3px; background: transparent;")

        self.slider_media_seek = NoWheelSlider(Qt.Orientation.Horizontal)
        self.slider_media_seek.setRange(0, 100)
        self.slider_media_seek.setValue(0)
        self.slider_media_seek.setMinimumWidth(0)
        self.slider_media_seek.setStyleSheet(get_slider_qss(accent, mode))
        self.slider_media_seek.sliderReleased.connect(self.on_media_seek_released)

        self.lbl_media_dur = QLabel("0:00")
        self.lbl_media_dur.setFixedWidth(pos_w)
        self.lbl_media_dur.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.lbl_media_dur.setStyleSheet(f"color: {pal['text_secondary']}; font-size: {'8.5px' if self.compact else '9.5px'}; font-weight: 600; padding-left: 3px; background: transparent;")

        seek_box.addWidget(self.lbl_media_pos, 0, Qt.AlignmentFlag.AlignVCenter)
        seek_box.addWidget(self.slider_media_seek, 1, Qt.AlignmentFlag.AlignVCenter)
        seek_box.addWidget(self.lbl_media_dur, 0, Qt.AlignmentFlag.AlignVCenter)
        b_layout.addLayout(seek_box)

        # Transport Controls Row
        m_btn_layout = QHBoxLayout()
        m_btn_layout.setSpacing(6 if self.compact else 8)

        self.btn_prev = QPushButton("⏮ Prev")
        self.btn_play = QPushButton("▶ Play")
        self.btn_next = QPushButton("⏭ Next")

        btn_h = 20 if self.compact else 24
        btn_font = "8.5px" if self.compact else "10px"

        for btn in (self.btn_prev, self.btn_play, self.btn_next):
            btn.setFixedHeight(btn_h)
            btn.setMinimumWidth(0)
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)

        btn_qss_sub = f"QPushButton {{ background-color: {pal['input_bg']}; color: {pal['text_primary']}; font-family: 'Segoe UI', sans-serif; font-size: {btn_font}; font-weight: bold; border-radius: 4px; border: 1px solid {pal['input_border']}; padding: 1px 2px; outline: none; }} QPushButton:hover {{ border: 1px solid {accent}; background: {pal['list_item_hover']}; }}"
        btn_qss_play = f"QPushButton {{ background-color: {accent}; color: #ffffff; font-family: 'Segoe UI', sans-serif; font-size: {btn_font}; font-weight: 800; border-radius: 4px; border: none; padding: 1px 2px; outline: none; }}"

        self.btn_prev.setStyleSheet(btn_qss_sub)
        self.btn_next.setStyleSheet(btn_qss_sub)
        self.btn_play.setStyleSheet(btn_qss_play)

        self.btn_prev.clicked.connect(self.on_media_prev_clicked)
        self.btn_play.clicked.connect(self.on_media_play_pause_clicked)
        self.btn_next.clicked.connect(self.on_media_next_clicked)

        m_btn_layout.addWidget(self.btn_prev, 1)
        m_btn_layout.addWidget(self.btn_play, 1)
        m_btn_layout.addWidget(self.btn_next, 1)
        b_layout.addLayout(m_btn_layout)

        self.update_now_playing_data({})

    def apply_theme(self, accent_color: str, mode: str = "dark"):
        super().apply_theme(accent_color, mode)
        pal = THEME_PALETTES.get(mode, THEME_PALETTES["dark"])
        chip_bg = f"{accent_color}26" if mode == "dark" else f"{accent_color}1e"
        btn_font = "8.5px" if self.compact else "10px"

        self.chip_media.setStyleSheet(f"QLabel {{ background-color: {chip_bg}; border-radius: 6px; font-size: {'9px' if self.compact else '10px'}; font-family: 'Segoe UI Emoji', 'Segoe UI Symbol', 'Segoe UI', sans-serif; }}")
        self.lbl_m_title.setStyleSheet(f"color: {accent_color}; font-size: 9.5px; font-weight: 800; letter-spacing: 0.5px; background: transparent;")
        self.chip_app_name.setStyleSheet(f"color: {accent_color}; background: {pal['input_bg']}; border: 1px solid {pal['input_border']}; border-radius: 4px; padding: 1px 6px; font-size: 8.5px; font-weight: bold;")

        self.lbl_artwork.setStyleSheet(f"QLabel {{ background: {pal['input_bg']}; border: 1px solid {pal['input_border']}; border-radius: 6px; font-size: {'13px' if self.compact else '16px'}; font-family: 'Segoe UI Emoji', 'Segoe UI Symbol', sans-serif; }}")
        self.lbl_track_title.setStyleSheet(f"color: {pal['text_primary']}; font-size: {'9.5px' if self.compact else '10.5px'}; font-weight: 800; background: transparent;")
        self.lbl_track_artist.setStyleSheet(f"color: {pal['text_secondary']}; font-size: {'8.5px' if self.compact else '9px'}; font-weight: 500; background: transparent;")

        self.lbl_media_pos.setStyleSheet(f"color: {pal['text_secondary']}; font-size: {'8.5px' if self.compact else '9.5px'}; font-weight: 600; padding-right: 3px; background: transparent;")
        self.lbl_media_dur.setStyleSheet(f"color: {pal['text_secondary']}; font-size: {'8.5px' if self.compact else '9.5px'}; font-weight: 600; padding-left: 3px; background: transparent;")
        self.slider_media_seek.setStyleSheet(get_slider_qss(accent_color, mode))

        btn_qss_sub = f"QPushButton {{ background-color: {pal['input_bg']}; color: {pal['text_primary']}; font-family: 'Segoe UI', sans-serif; font-size: {btn_font}; font-weight: bold; border-radius: 4px; border: 1px solid {pal['input_border']}; padding: 1px 2px; outline: none; }} QPushButton:hover {{ border: 1px solid {accent_color}; background: {pal['list_item_hover']}; }}"
        btn_qss_play = f"QPushButton {{ background-color: {accent_color}; color: #ffffff; font-family: 'Segoe UI', sans-serif; font-size: {btn_font}; font-weight: 800; border-radius: 4px; border: none; padding: 1px 2px; outline: none; }}"

        self.btn_prev.setStyleSheet(btn_qss_sub)
        self.btn_next.setStyleSheet(btn_qss_sub)
        self.btn_play.setStyleSheet(btn_qss_play)

    def update_now_playing_data(self, info: dict):
        try:
            from PyQt6.sip import isdeleted
            if isdeleted(self) or not isinstance(info, dict):
                return
            if info.get("status") != "none" and info.get("title"):
                title = info.get("title", "Unknown Track")
                artist = info.get("artist", "Unknown Artist")
                self.chip_app_name.setText(info.get("app_name", "MEDIA").upper())

                if self.compact:
                    fmt_title = title if len(title) <= 24 else title[:23] + "…"
                    fmt_artist = artist if len(artist) <= 24 else artist[:23] + "…"
                else:
                    fmt_title = title if len(title) <= 42 else title[:41] + "…"
                    fmt_artist = artist if len(artist) <= 48 else artist[:47] + "…"

                self.lbl_track_title.setText(fmt_title)
                self.lbl_track_title.setToolTip(title)
                self.lbl_track_artist.setText(fmt_artist)
                self.lbl_track_artist.setToolTip(artist)

                # Artwork
                thumb_bytes = info.get("thumbnail_bytes")
                if thumb_bytes:
                    pix = QPixmap()
                    if pix.loadFromData(thumb_bytes):
                        art_sz = 28 if self.compact else 36
                        scaled = pix.scaled(art_sz, art_sz, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
                        self.lbl_artwork.setPixmap(scaled)
                    else:
                        self.lbl_artwork.setText("\U0001F3B5")
                else:
                    self.lbl_artwork.setText("\U0001F3B5")

                # Seek Bar & Timestamps
                dur = info.get("duration_sec", 0)
                pos = info.get("position_sec", 0)
                self.lbl_media_pos.setText(format_mmss(pos))
                self.lbl_media_dur.setText(format_mmss(dur))

                if dur > 0:
                    if not self.slider_media_seek.isSliderDown():
                        self.slider_media_seek.setRange(0, dur)
                        self.slider_media_seek.setValue(pos)
                    self.slider_media_seek.show()
                else:
                    self.slider_media_seek.hide()

                if info.get("is_playing"):
                    self.btn_play.setText("⏸ Pause")
                else:
                    self.btn_play.setText("▶ Play")
            else:
                self.lbl_track_title.setText("Nothing Playing")
                self.lbl_track_artist.setText("Play audio or video in Spotify, Chrome, etc.")
                self.chip_app_name.setText("IDLE")
                self.lbl_artwork.setText("\U0001F3B5")
                self.lbl_media_pos.setText("0:00")
                self.lbl_media_dur.setText("0:00")
                self.slider_media_seek.hide()
                self.btn_play.setText("▶ Play")
        except Exception as e:
            print(f"[NowPlayingWidget Update Exception]: {e}")

    def on_media_seek_released(self):
        val = self.slider_media_seek.value()
        SystemMonitor.set_media_position(val)
        QTimer.singleShot(200, lambda: self.update_now_playing_data(SystemMonitor.get_now_playing_info()))

    def on_media_prev_clicked(self):
        SystemMonitor.trigger_media_prev()
        QTimer.singleShot(200, lambda: self.update_now_playing_data(SystemMonitor.get_now_playing_info()))

    def on_media_play_pause_clicked(self):
        SystemMonitor.trigger_media_play_pause()
        QTimer.singleShot(200, lambda: self.update_now_playing_data(SystemMonitor.get_now_playing_info()))

    def on_media_next_clicked(self):
        SystemMonitor.trigger_media_next()
        QTimer.singleShot(200, lambda: self.update_now_playing_data(SystemMonitor.get_now_playing_info()))


# 2. CONTROL CENTER TAB WIDGET
class ControlCenterTabWidget(QWidget):
    def __init__(self, settings: SettingsManager, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(8)

        accent = resolve_accent_color(self.settings)
        mode = self.settings.get("theme_mode", "dark")
        pal = THEME_PALETTES.get(mode, THEME_PALETTES["dark"])
        card_qss = get_card_qss(mode)
        slider_qss = get_slider_qss(accent, mode)

        chip_bg = f"{accent}26" if mode == "dark" else f"{accent}1e"

        import time
        self.last_user_vol_change_time = 0

        # 1. Rich WinRT Now Playing Media Transport Card (Appears FIRST)
        self.card_media = NowPlayingWidget(self.settings, compact=False)
        layout.addWidget(self.card_media)

        # 2. System Master Volume Card (Appears SECOND)
        card_vol = GlassPanel(category_key="alarms", corner_radius=10)
        b_vol = QVBoxLayout(card_vol)
        b_vol.setContentsMargins(8, 6, 8, 6)
        b_vol.setSpacing(6)

        v_head = QHBoxLayout()
        v_head.setSpacing(6)

        self.chip_vol = QLabel("🔊")
        self.chip_vol.setFixedSize(20, 20)
        self.chip_vol.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.chip_vol.setStyleSheet(f"QLabel {{ background-color: {chip_bg}; border-radius: 6px; font-size: 10px; font-family: 'Segoe UI Emoji', 'Segoe UI Symbol', 'Segoe UI', sans-serif; }}")

        self.lbl_v_title = QLabel("SYSTEM MASTER VOLUME")
        self.lbl_v_title.setStyleSheet(f"color: {accent}; font-size: 9.5px; font-weight: 800; letter-spacing: 0.5px; background: transparent;")

        self.lbl_vol_val = QLabel("50%")
        self.lbl_vol_val.setStyleSheet(f"color: {accent}; background: {pal['input_bg']}; border: 1px solid {pal['input_border']}; border-radius: 5px; padding: 2px 8px; font-size: 10px; font-weight: bold;")

        v_head.addWidget(self.chip_vol)
        v_head.addWidget(self.lbl_v_title)
        v_head.addStretch()
        v_head.addWidget(self.lbl_vol_val)
        b_vol.addLayout(v_head)

        self.slider_vol = QSlider(Qt.Orientation.Horizontal)
        self.slider_vol.setRange(0, 100)
        self.slider_vol.setValue(SystemMonitor.get_master_volume())
        self.slider_vol.setStyleSheet(slider_qss)
        self.slider_vol.valueChanged.connect(self.on_volume_changed)

        b_vol.addWidget(self.slider_vol)
        layout.addWidget(card_vol)

        # 3. Display Brightness Card (Appears THIRD)
        card_bri = GlassPanel(category_key="settings", corner_radius=10)
        b_bri = QVBoxLayout(card_bri)
        b_bri.setContentsMargins(8, 6, 8, 6)
        b_bri.setSpacing(6)

        b_head = QHBoxLayout()
        b_head.setSpacing(6)

        self.chip_bri = QLabel("☀️")
        self.chip_bri.setFixedSize(20, 20)
        self.chip_bri.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.chip_bri.setStyleSheet(f"QLabel {{ background-color: {chip_bg}; border-radius: 6px; font-size: 10px; font-family: 'Segoe UI Emoji', 'Segoe UI Symbol', 'Segoe UI', sans-serif; }}")

        self.lbl_b_title = QLabel("DISPLAY BRIGHTNESS")
        self.lbl_b_title.setStyleSheet(f"color: {accent}; font-size: 9.5px; font-weight: 800; letter-spacing: 0.5px; background: transparent;")

        self.lbl_bri_val = QLabel("100%")
        self.lbl_bri_val.setStyleSheet(f"color: {accent}; background: {pal['input_bg']}; border: 1px solid {pal['input_border']}; border-radius: 5px; padding: 2px 8px; font-size: 10px; font-weight: bold;")

        b_head.addWidget(self.chip_bri)
        b_head.addWidget(self.lbl_b_title)
        b_head.addStretch()
        b_head.addWidget(self.lbl_bri_val)
        b_bri.addLayout(b_head)

        self.slider_bri = QSlider(Qt.Orientation.Horizontal)
        self.slider_bri.setRange(0, 100)
        self.slider_bri.setValue(SystemMonitor.get_brightness())
        self.slider_bri.setStyleSheet(slider_qss)
        self.slider_bri.valueChanged.connect(self.on_brightness_changed)

        b_bri.addWidget(self.slider_bri)
        layout.addWidget(card_bri)

        layout.addStretch()

    def on_volume_changed(self, val: int):
        import time
        self.lbl_vol_val.setText(f"{val}%")
        self.last_user_vol_change_time = time.time()
        print(f"[Volume Slider Changed]: User dragged slider to {val}%")
        SystemMonitor.set_master_volume(val)

    def on_brightness_changed(self, val: int):
        self.lbl_bri_val.setText(f"{val}%")
        SystemMonitor.set_brightness(val)

    def apply_theme(self, accent_color: str, mode: str = "dark"):
        pal = THEME_PALETTES.get(mode, THEME_PALETTES["dark"])
        chip_bg = f"{accent_color}26" if mode == "dark" else f"{accent_color}1e"

        if hasattr(self, 'card_media'):
            self.card_media.apply_theme(accent_color, mode)

        for gp in self.findChildren(GlassPanel):
            gp.apply_theme(accent_color, mode)

        for chip in (self.chip_vol, self.chip_bri):
            chip.setStyleSheet(f"QLabel {{ background-color: {chip_bg}; border-radius: 6px; font-size: 10px; font-family: 'Segoe UI Emoji', 'Segoe UI Symbol', 'Segoe UI', sans-serif; }}")

        self.lbl_v_title.setStyleSheet(f"color: {accent_color}; font-size: 9.5px; font-weight: 800; letter-spacing: 0.5px; background: transparent;")
        self.lbl_b_title.setStyleSheet(f"color: {accent_color}; font-size: 9.5px; font-weight: 800; letter-spacing: 0.5px; background: transparent;")

        pill_qss = f"color: {accent_color}; background: {pal['input_bg']}; border: 1px solid {pal['input_border']}; border-radius: 5px; padding: 2px 8px; font-size: 10px; font-weight: bold;"
        self.lbl_vol_val.setStyleSheet(pill_qss)
        self.lbl_bri_val.setStyleSheet(pill_qss)

        slider_qss = get_slider_qss(accent_color, mode)
        self.slider_vol.setStyleSheet(slider_qss)
        self.slider_bri.setStyleSheet(slider_qss)

    def update_live_metrics(self, vol: int, bri: int, cpu: float, ram: float):
        from PyQt6.sip import isdeleted
        if isdeleted(self):
            return
        import time
        now = time.time()
        if not self.slider_vol.isSliderDown() and (now - getattr(self, 'last_user_vol_change_time', 0) > 2.0):
            self.slider_vol.setValue(vol)
            self.lbl_vol_val.setText(f"{vol}%")
        if not self.slider_bri.isSliderDown():
            self.slider_bri.setValue(bri)
            self.lbl_bri_val.setText(f"{bri}%")


# 3. HARDWARE DIAGNOSTICS TAB WIDGET (WITH RAM PROGRESS BAR & TEMP CLEANUP BUTTON)
class HardwareDiagnosticsTabWidget(QWidget):
    def __init__(self, settings: SettingsManager, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        accent = resolve_accent_color(self.settings)
        mode = self.settings.get("theme_mode", "dark")
        pal = THEME_PALETTES.get(mode, THEME_PALETTES["dark"])
        card_qss = get_card_qss(mode)

        top_grid = QHBoxLayout()
        top_grid.setSpacing(6)

        # Card A: CPU Load %
        card_cpu = GlassPanel(category_key="default", corner_radius=10)
        b_cpu = QVBoxLayout(card_cpu)
        b_cpu.setContentsMargins(6, 6, 6, 6)
        b_cpu.setSpacing(2)

        self.lbl_c_head = QLabel("💻 CPU LOAD")
        self.lbl_c_head.setStyleSheet(f"color: {pal['text_muted']}; font-size: 8.5px; font-weight: bold; background: transparent;")
        self.val_cpu = QLabel("0.0%")
        self.val_cpu.setStyleSheet(f"color: {accent}; font-size: 16px; font-weight: bold; background: transparent;")
        self.bar_cpu = QProgressBar()
        self.bar_cpu.setFixedHeight(4)
        self.bar_cpu.setTextVisible(False)
        self.bar_cpu.setStyleSheet(f"QProgressBar {{ background: {pal['input_bg']}; border-radius: 2px; }} QProgressBar::chunk {{ background: {accent}; border-radius: 2px; }}")

        b_cpu.addWidget(self.lbl_c_head)
        b_cpu.addWidget(self.val_cpu)
        b_cpu.addWidget(self.bar_cpu)
        top_grid.addWidget(card_cpu, 1)

        # Card B: RAM Usage % (ADDED RAM PROGRESS BAR - Req 1)
        card_ram = GlassPanel(category_key="default", corner_radius=10)
        b_ram = QVBoxLayout(card_ram)
        b_ram.setContentsMargins(6, 6, 6, 6)
        b_ram.setSpacing(2)

        self.lbl_r_head = QLabel("🧠 RAM USAGE")
        self.lbl_r_head.setStyleSheet(f"color: {pal['text_muted']}; font-size: 8.5px; font-weight: bold; background: transparent;")
        self.val_ram = QLabel("0.0%")
        self.val_ram.setStyleSheet(f"color: {accent}; font-size: 16px; font-weight: bold; background: transparent;")
        self.bar_ram = QProgressBar()
        self.bar_ram.setFixedHeight(4)
        self.bar_ram.setTextVisible(False)
        self.bar_ram.setStyleSheet(f"QProgressBar {{ background: {pal['input_bg']}; border-radius: 2px; }} QProgressBar::chunk {{ background: {accent}; border-radius: 2px; }}")

        self.lbl_ram_sub = QLabel("0.0 / 0.0 GB")
        self.lbl_ram_sub.setStyleSheet(f"color: {pal['text_secondary']}; font-size: 8.5px; background: transparent;")

        b_ram.addWidget(self.lbl_r_head)
        b_ram.addWidget(self.val_ram)
        b_ram.addWidget(self.bar_ram)
        b_ram.addWidget(self.lbl_ram_sub)
        top_grid.addWidget(card_ram, 1)

        # Card C: Wi-Fi / Network Info
        card_net = GlassPanel(category_key="default", corner_radius=10)
        b_net = QVBoxLayout(card_net)
        b_net.setContentsMargins(6, 6, 6, 6)
        b_net.setSpacing(2)

        self.lbl_n_head = QLabel("📶 NETWORK")
        self.lbl_n_head.setStyleSheet(f"color: {pal['text_muted']}; font-size: 8.5px; font-weight: bold; background: transparent;")
        self.val_net_status = QLabel("Checking...")
        self.val_net_status.setStyleSheet("color: #00e676; font-size: 11px; font-weight: bold; background: transparent;")
        self.val_net_name = QLabel("Wi-Fi Network")
        self.val_net_name.setStyleSheet(f"color: {pal['text_secondary']}; font-size: 8.5px; background: transparent;")

        b_net.addWidget(self.lbl_n_head)
        b_net.addWidget(self.val_net_status)
        b_net.addWidget(self.val_net_name)
        top_grid.addWidget(card_net, 1)

        layout.addLayout(top_grid)

        # 2. Secondary Footer Statistics Card (ADDED TEMP FILE CLEANUP BUTTON - Req 2)
        card_sec = GlassPanel(category_key="default", corner_radius=10)
        b_sec = QVBoxLayout(card_sec)
        b_sec.setContentsMargins(8, 6, 8, 6)
        b_sec.setSpacing(4)

        sec_head_box = QHBoxLayout()
        self.lbl_sec_head = QLabel("⚙️ SYSTEM DIAGNOSTICS SUMMARY")
        self.lbl_sec_head.setStyleSheet(f"color: {accent}; font-size: 9.5px; font-weight: 800; letter-spacing: 0.5px; background: transparent;")

        self.btn_clear_temp = QPushButton("🧹 Clear Temp Files")
        self.btn_clear_temp.setFixedHeight(22)
        self.btn_clear_temp.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_clear_temp.setStyleSheet(f"QPushButton {{ background-color: {pal['input_bg']}; color: {pal['text_primary']}; font-size: 9px; font-weight: bold; border-radius: 4px; border: 1px solid {pal['input_border']}; padding: 0 8px; }} QPushButton:hover {{ border: 1px solid {accent}; }}")
        self.btn_clear_temp.clicked.connect(self.on_clear_temp_files)

        sec_head_box.addWidget(self.lbl_sec_head)
        sec_head_box.addStretch()
        sec_head_box.addWidget(self.btn_clear_temp)
        b_sec.addLayout(sec_head_box)

        sec_grid = QGridLayout()
        sec_grid.setSpacing(6)

        self.lbl_boot = QLabel("Boot Time: --:--")
        self.lbl_uptime = QLabel("Uptime: 0h 0m")
        self.lbl_battery = QLabel("Battery: 100% (AC)")
        self.lbl_storage = QLabel("Storage (C:): -- / -- GB")

        for lbl in (self.lbl_boot, self.lbl_uptime, self.lbl_battery, self.lbl_storage):
            lbl.setStyleSheet(f"color: {pal['text_secondary']}; font-size: 9.5px; background: transparent;")

        sec_grid.addWidget(self.lbl_boot, 0, 0)
        sec_grid.addWidget(self.lbl_uptime, 0, 1)
        sec_grid.addWidget(self.lbl_battery, 1, 0)
        sec_grid.addWidget(self.lbl_storage, 1, 1)

        b_sec.addLayout(sec_grid)

        self.lbl_temp_status = QLabel("")
        self.lbl_temp_status.setStyleSheet("color: #00e676; font-size: 9.5px; font-weight: bold; background: transparent;")
        self.lbl_temp_status.hide()
        b_sec.addWidget(self.lbl_temp_status)

        layout.addWidget(card_sec)
        layout.addStretch()

    def apply_theme(self, accent_color: str, mode: str = "dark"):
        pal = THEME_PALETTES.get(mode, THEME_PALETTES["dark"])
        for gp in self.findChildren(GlassPanel):
            gp.apply_theme(accent_color, mode)

        for lbl in (self.lbl_c_head, self.lbl_r_head, self.lbl_n_head):
            lbl.setStyleSheet(f"color: {pal['text_muted']}; font-size: 8.5px; font-weight: bold; background: transparent;")

        self.val_cpu.setStyleSheet(f"color: {accent_color}; font-size: 16px; font-weight: bold; background: transparent;")
        self.val_ram.setStyleSheet(f"color: {accent_color}; font-size: 16px; font-weight: bold; background: transparent;")

        bar_qss = f"QProgressBar {{ background: {pal['input_bg']}; border-radius: 2px; }} QProgressBar::chunk {{ background: {accent_color}; border-radius: 2px; }}"
        self.bar_cpu.setStyleSheet(bar_qss)
        self.bar_ram.setStyleSheet(bar_qss)

        self.lbl_sec_head.setStyleSheet(f"color: {accent_color}; font-size: 9.5px; font-weight: 800; letter-spacing: 0.5px; background: transparent;")
        self.btn_clear_temp.setStyleSheet(f"QPushButton {{ background-color: {pal['input_bg']}; color: {pal['text_primary']}; font-size: 9px; font-weight: bold; border-radius: 4px; border: 1px solid {pal['input_border']}; padding: 0 8px; }} QPushButton:hover {{ border: 1px solid {accent_color}; }}")
        self.lbl_ram_sub.setStyleSheet(f"color: {pal['text_secondary']}; font-size: 8.5px; background: transparent;")
        self.val_net_name.setStyleSheet(f"color: {pal['text_secondary']}; font-size: 8.5px; background: transparent;")

        for lbl in (self.lbl_boot, self.lbl_uptime, self.lbl_battery, self.lbl_storage):
            lbl.setStyleSheet(f"color: {pal['text_secondary']}; font-size: 9.5px; background: transparent;")

    def update_diagnostics_data(self, data: dict):
        from PyQt6.sip import isdeleted
        if isdeleted(self) or not isinstance(data, dict):
            return

        def safe_num(val, default=0.0):
            try:
                return float(val) if val is not None else default
            except (TypeError, ValueError):
                return default

        cpu = safe_num(data.get("cpu"), 0.0)
        self.val_cpu.setText(f"{cpu:.1f}%")
        self.bar_cpu.setValue(int(cpu))

        ram_dict = data.get("ram_info") if isinstance(data.get("ram_info"), dict) else {}
        ram_pct = safe_num(ram_dict.get("percent"), 0.0)
        ram_used = safe_num(ram_dict.get("used_gb"), 0.0)
        ram_total = safe_num(ram_dict.get("total_gb"), 0.0)
        self.val_ram.setText(f"{ram_pct:.1f}%")
        self.bar_ram.setValue(int(ram_pct))
        self.lbl_ram_sub.setText(f"{ram_used:.1f} / {ram_total:.1f} GB")

        net_dict = data.get("wifi_network") if isinstance(data.get("wifi_network"), dict) else {}
        if net_dict.get("connected", False):
            self.val_net_status.setText("● Connected")
            self.val_net_status.setStyleSheet("color: #00e676; font-size: 11px; font-weight: bold; background: transparent;")
            ssid = str(net_dict.get("ssid", "")).strip()
            signal = str(net_dict.get("signal", "")).strip()
            if ssid:
                display_text = f"{ssid} ({signal})" if signal else ssid
                self.val_net_name.setText(display_text)
                self.val_net_name.setToolTip(f"Connected to Wi-Fi SSID: {ssid}\nSignal: {signal if signal else 'Active'}\nInterface: {net_dict.get('name', 'Wi-Fi')}")
            else:
                ifname = str(net_dict.get("name", "Active Connection"))
                self.val_net_name.setText(ifname)
                self.val_net_name.setToolTip(f"Connected Interface: {ifname}")
        else:
            self.val_net_status.setText("○ Offline")
            self.val_net_status.setStyleSheet("color: #ef4444; font-size: 11px; font-weight: bold; background: transparent;")
            self.val_net_name.setText("Disconnected")
            self.val_net_name.setToolTip("No active network connection")

        self.lbl_boot.setText(f"Boot: {data.get('boot_timestamp', '--:--')}")
        self.lbl_uptime.setText(f"Uptime: {data.get('uptime', '0h 0m')}")

        battery = data.get("battery") if isinstance(data.get("battery"), dict) else {}
        charging = bool(data.get("charging", False))
        if battery and battery.get("percent") is not None:
            pct = int(safe_num(battery.get("percent"), 0.0))
            status_str = "Plugged In" if charging else "Discharging"
            self.lbl_battery.setText(f"Battery: {pct}% ({status_str})")
        else:
            self.lbl_battery.setText("Battery: Desktop (AC)")

        disk = data.get("disk") if isinstance(data.get("disk"), dict) else {}
        if disk:
            used = safe_num(disk.get("used_gb"), 0.0)
            total = safe_num(disk.get("total_gb"), 0.0)
            self.lbl_storage.setText(f"Storage (C:): {used:.1f} / {total:.1f} GB")

    def on_clear_temp_files(self):
        """Safely deletes user %TEMP% files, reporting total space freed without elevational or system-level risk."""
        temp_dir = os.environ.get("TEMP") or tempfile.gettempdir()
        if not os.path.exists(temp_dir):
            return

        freed_bytes = 0
        deleted_count = 0

        for root, dirs, files in os.walk(temp_dir, topdown=False):
            for name in files:
                fp = os.path.join(root, name)
                try:
                    size = os.path.getsize(fp)
                    os.remove(fp)
                    freed_bytes += size
                    deleted_count += 1
                except Exception:
                    pass  # Skip locked/in-use files silently

            for name in dirs:
                dp = os.path.join(root, name)
                try:
                    os.rmdir(dp)
                except Exception:
                    pass

        if freed_bytes >= 1024 * 1024 * 1024:
            freed_str = f"{freed_bytes / (1024**3):.2f} GB"
        else:
            freed_str = f"{freed_bytes / (1024**2):.1f} MB"

        self.lbl_temp_status.setText(f"🧹 Cleaned {freed_str} of temporary files ({deleted_count} files removed)")
        self.lbl_temp_status.show()


def safe_clear_list_widget(list_widget: QListWidget):
    """Safely clears a QListWidget containing custom item widgets to prevent C++ Access Violation crashes."""
    if not list_widget:
        return
    for i in range(list_widget.count()):
        item = list_widget.item(i)
        if item:
            w = list_widget.itemWidget(item)
            if w:
                w.deleteLater()
    list_widget.clear()


# 4. CLIPBOARD & FILE SHELF MERGED TAB WIDGET (WITH PROPER EMPTY STATE SIZING FIX - Req 2)
class ClipboardShelfTabWidget(QWidget):
    def __init__(self, storage: StorageManager, settings: SettingsManager = None, parent=None):
        super().__init__(parent)
        self.storage = storage
        self.settings = settings
        self.setAcceptDrops(True)
        self.init_ui()

        if hasattr(self.storage, 'clipboard_changed'):
            self.storage.clipboard_changed.connect(self.load_clipboard_history)
        if hasattr(self.storage, 'fileshelf_changed'):
            self.storage.fileshelf_changed.connect(self.load_shelf_files)

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        accent = resolve_accent_color(self.settings) if self.settings else "#38bdf8"
        mode = self.settings.get("theme_mode", "dark") if self.settings else "dark"
        pal = THEME_PALETTES.get(mode, THEME_PALETTES["dark"])

        nav_box = QHBoxLayout()
        nav_box.setSpacing(4)

        self.btn_sub_clip = QPushButton("📋 Clipboard History")
        self.btn_sub_shelf = QPushButton("📁 File Shelf Zone")

        for btn in (self.btn_sub_clip, self.btn_sub_shelf):
            btn.setFixedHeight(22)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)

        self.btn_sub_clip.clicked.connect(lambda: self.switch_sub_tab(0))
        self.btn_sub_shelf.clicked.connect(lambda: self.switch_sub_tab(1))

        nav_box.addWidget(self.btn_sub_clip)
        nav_box.addWidget(self.btn_sub_shelf)
        layout.addLayout(nav_box)

        self.sub_stacked = QStackedWidget()

        # Sub-View 0: Clipboard History
        self.sub_clip_widget = QWidget()
        clip_layout = QVBoxLayout(self.sub_clip_widget)
        clip_layout.setContentsMargins(0, 0, 0, 0)
        clip_layout.setSpacing(4)

        clip_head = QHBoxLayout()
        self.lbl_clip_head = QLabel("📋 Clipboard History")
        self.lbl_clip_head.setStyleSheet(f"color: {accent}; font-size: 10px; font-weight: 800; background: transparent;")

        self.btn_clear_clips = QPushButton("🗑️ Clear All")
        self.btn_clear_clips.setFixedHeight(20)
        self.btn_clear_clips.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_clear_clips.setStyleSheet("QPushButton { background: rgba(239, 68, 68, 0.15); color: #ef4444; border: 1px solid rgba(239, 68, 68, 0.3); border-radius: 4px; font-size: 9px; font-weight: bold; padding: 0 6px; } QPushButton:hover { background: #ef4444; color: #ffffff; }")
        self.btn_clear_clips.clicked.connect(self.on_clear_clips_clicked)

        clip_head.addWidget(self.lbl_clip_head)
        clip_head.addStretch()
        clip_head.addWidget(self.btn_clear_clips)
        clip_layout.addLayout(clip_head)

        clip_card = GlassPanel(category_key="notes", corner_radius=10)
        c_box = QVBoxLayout(clip_card)
        c_box.setContentsMargins(2, 2, 2, 2)
        c_box.setSpacing(0)

        self.clip_list = QListWidget()
        self.clip_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.clip_list.setStyleSheet(get_list_widget_qss(accent, mode))
        c_box.addWidget(self.clip_list)
        clip_layout.addWidget(clip_card)
        self.sub_stacked.addWidget(self.sub_clip_widget)

        # Sub-View 1: File Shelf Zone
        self.sub_shelf_widget = QWidget()
        shelf_layout = QVBoxLayout(self.sub_shelf_widget)
        shelf_layout.setContentsMargins(0, 0, 0, 0)
        shelf_layout.setSpacing(4)

        drop_card = GlassPanel(category_key="notes", corner_radius=10)
        b_drop = QVBoxLayout(drop_card)
        b_drop.setContentsMargins(8, 6, 8, 6)
        b_drop.setAlignment(Qt.AlignmentFlag.AlignCenter)

        lbl_icon = QLabel("📥")
        lbl_icon.setStyleSheet("font-size: 20px; font-family: 'Segoe UI Emoji', 'Segoe UI Symbol', 'Segoe UI', sans-serif; background: transparent;")
        self.lbl_drop_msg = QLabel("Drag and Drop Files Here")
        self.lbl_drop_msg.setStyleSheet(f"color: {pal['text_primary']}; font-size: 10.5px; font-weight: bold; background: transparent;")
        self.lbl_drop_sub = QLabel("Files dropped will be saved into your Shelf library.")
        self.lbl_drop_sub.setStyleSheet(f"color: {pal['text_secondary']}; font-size: 8.5px; background: transparent;")

        b_drop.addWidget(lbl_icon, 0, Qt.AlignmentFlag.AlignCenter)
        b_drop.addWidget(self.lbl_drop_msg, 0, Qt.AlignmentFlag.AlignCenter)
        b_drop.addWidget(self.lbl_drop_sub, 0, Qt.AlignmentFlag.AlignCenter)

        shelf_layout.addWidget(drop_card)

        shelf_head = QHBoxLayout()
        self.lbl_shelf_head = QLabel("📁 Saved Shelf Files")
        self.lbl_shelf_head.setStyleSheet(f"color: {accent}; font-size: 10px; font-weight: 800; background: transparent;")

        self.btn_clear_shelf = QPushButton("🗑️ Clear All")
        self.btn_clear_shelf.setFixedHeight(20)
        self.btn_clear_shelf.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_clear_shelf.setStyleSheet("QPushButton { background: rgba(239, 68, 68, 0.15); color: #ef4444; border: 1px solid rgba(239, 68, 68, 0.3); border-radius: 4px; font-size: 9px; font-weight: bold; padding: 0 6px; } QPushButton:hover { background: #ef4444; color: #ffffff; }")
        self.btn_clear_shelf.clicked.connect(self.on_clear_shelf_clicked)

        shelf_head.addWidget(self.lbl_shelf_head)
        shelf_head.addStretch()
        shelf_head.addWidget(self.btn_clear_shelf)
        shelf_layout.addLayout(shelf_head)

        shelf_card = GlassPanel(category_key="notes", corner_radius=10)
        s_box = QVBoxLayout(shelf_card)
        s_box.setContentsMargins(2, 2, 2, 2)
        s_box.setSpacing(0)

        self.shelf_list = QListWidget()
        self.shelf_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.shelf_list.setStyleSheet(get_list_widget_qss(accent, mode))
        s_box.addWidget(self.shelf_list)
        shelf_layout.addWidget(shelf_card)

        # Smooth animated scrolling (36px per notch, 120ms OutQuad easing)
        self.clip_scroll_filter = SmoothScrollFilter(self.clip_list, step_size=36, duration=120)
        self.shelf_scroll_filter = SmoothScrollFilter(self.shelf_list, step_size=36, duration=120)

        self.sub_stacked.addWidget(self.sub_shelf_widget)
        layout.addWidget(self.sub_stacked)

        active_sub = int(self.settings.get("shelf_active_subtab", 0)) if self.settings else 0
        self.switch_sub_tab(active_sub)
        self.load_clipboard_history()
        self.load_shelf_files()

    def on_delete_clip_clicked(self, text: str):
        self.storage.delete_clipboard_entry(text)
        self.load_clipboard_history()

    def on_clear_clips_clicked(self):
        self.storage.clear_clipboard()
        self.load_clipboard_history()

    def on_delete_shelf_clicked(self, file_path: str):
        self.storage.delete_shelf_file(file_path)
        self.load_shelf_files()

    def on_clear_shelf_clicked(self):
        self.storage.clear_shelf()
        self.load_shelf_files()

    def apply_theme(self, accent_color: str, mode: str = "dark"):
        pal = THEME_PALETTES.get(mode, THEME_PALETTES["dark"])
        for gp in self.findChildren(GlassPanel):
            gp.apply_theme(accent_color, mode)

        if hasattr(self, 'lbl_clip_head'):
            self.lbl_clip_head.setStyleSheet(f"color: {accent_color}; font-size: 10px; font-weight: 800; background: transparent;")
        if hasattr(self, 'lbl_shelf_head'):
            self.lbl_shelf_head.setStyleSheet(f"color: {accent_color}; font-size: 10px; font-weight: 800; background: transparent;")
        self.lbl_drop_msg.setStyleSheet(f"color: {pal['text_primary']}; font-size: 10.5px; font-weight: bold; background: transparent;")
        self.lbl_drop_sub.setStyleSheet(f"color: {pal['text_secondary']}; font-size: 8.5px; background: transparent;")
        self.clip_list.setStyleSheet(get_list_widget_qss(accent_color, mode))
        self.shelf_list.setStyleSheet(get_list_widget_qss(accent_color, mode))
        self.switch_sub_tab(self.sub_stacked.currentIndex())

    def switch_sub_tab(self, idx: int):
        self.sub_stacked.setCurrentIndex(idx)
        if self.settings:
            self.settings.set("shelf_active_subtab", idx)
        accent = resolve_accent_color(self.settings) if self.settings else "#38bdf8"
        mode = self.settings.get("theme_mode", "dark") if self.settings else "dark"
        pal = THEME_PALETTES.get(mode, THEME_PALETTES["dark"])

        if idx == 0:
            self.btn_sub_clip.setStyleSheet(f"QPushButton {{ background-color: {accent}; color: #ffffff; font-weight: bold; border-radius: 4px; border: none; font-size: 9.5px; }}")
            self.btn_sub_shelf.setStyleSheet(f"QPushButton {{ background-color: {pal['sub_btn_bg']}; color: {pal['sub_btn_text']}; border-radius: 4px; border: 1px solid {pal['sub_btn_border']}; font-size: 9.5px; }}")
        else:
            self.btn_sub_shelf.setStyleSheet(f"QPushButton {{ background-color: {accent}; color: #ffffff; font-weight: bold; border-radius: 4px; border: none; font-size: 9.5px; }}")
            self.btn_sub_clip.setStyleSheet(f"QPushButton {{ background-color: {pal['sub_btn_bg']}; color: {pal['sub_btn_text']}; border-radius: 4px; border: 1px solid {pal['sub_btn_border']}; font-size: 9.5px; }}")

    def load_clipboard_history(self):
        try:
            safe_clear_list_widget(self.clip_list)
            clips = self.storage.load_clipboard()
            mode = self.settings.get("theme_mode", "dark") if self.settings else "dark"

            if clips:
                for item in clips:
                    self.add_clip_item_to_widget(item)
            else:
                w_empty = QListWidgetItem(self.clip_list)
                w_empty.setSizeHint(QSize(0, 84))
                empty_widget = make_empty_state("📋", "Clipboard Empty", "Copied text snippets will appear here.", mode)
                self.clip_list.setItemWidget(w_empty, empty_widget)
        except Exception as e:
            print(f"[Clipboard Load Exception]: {e}")

    def add_clip_item_to_widget(self, item):
        try:
            accent = resolve_accent_color(self.settings) if self.settings else "#38bdf8"
            mode = self.settings.get("theme_mode", "dark") if self.settings else "dark"
            pal = THEME_PALETTES.get(mode, THEME_PALETTES["dark"])

            clip_text = item.get("text", "") if isinstance(item, dict) else str(item)
            w_item = QListWidgetItem(self.clip_list)
            w_item.setSizeHint(QSize(0, 56))

            row = QWidget()
            r_box = QHBoxLayout(row)
            r_box.setContentsMargins(10, 4, 10, 4)
            r_box.setSpacing(6)

            txt_lbl = QLabel(clip_text)
            txt_lbl.setWordWrap(True)
            txt_lbl.setStyleSheet(f"color: {pal['text_primary']}; background: transparent; font-size: 10.5px; font-weight: 600; font-family: 'Segoe UI', sans-serif; letter-spacing: normal; padding: 2px 0;")

            copy_btn = QPushButton("Copy")
            copy_btn.setFixedSize(48, 24)
            copy_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            copy_btn.setStyleSheet(f"QPushButton {{ background-color: {pal['input_bg']}; color: {accent}; border: 1px solid {accent}; border-radius: 5px; font-size: 9.5px; font-weight: bold; padding: 0 4px; }} QPushButton:hover {{ background-color: {accent}; color: #ffffff; }}")
            copy_btn.clicked.connect(lambda _, b=copy_btn, t=clip_text: flash_copy_feedback(b, t))

            del_btn = QPushButton("🗑️")
            del_btn.setFixedSize(24, 24)
            del_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            del_btn.setStyleSheet("QPushButton { background-color: rgba(239, 68, 68, 0.15); color: #ef4444; border-radius: 4px; border: 1px solid rgba(239, 68, 68, 0.3); font-size: 9.5px; } QPushButton:hover { background-color: #ef4444; color: #ffffff; }")
            del_btn.clicked.connect(lambda _, t=clip_text: self.on_delete_clip_clicked(t))

            r_box.addWidget(txt_lbl, 1, Qt.AlignmentFlag.AlignVCenter)
            r_box.addWidget(copy_btn, 0, Qt.AlignmentFlag.AlignVCenter)
            r_box.addWidget(del_btn, 0, Qt.AlignmentFlag.AlignVCenter)

            self.clip_list.setItemWidget(w_item, row)
        except Exception as e:
            print(f"[Add Clip Item Exception]: {e}")

    def load_shelf_files(self):
        try:
            safe_clear_list_widget(self.shelf_list)
            files = self.storage.load_shelf()
            mode = self.settings.get("theme_mode", "dark") if self.settings else "dark"

            if files:
                for f_item in files:
                    self.add_shelf_item_to_widget(f_item)
            else:
                w_empty = QListWidgetItem(self.shelf_list)
                w_empty.setSizeHint(QSize(0, 84))
                empty_widget = make_empty_state("📁", "Shelf Empty", "Drop files above to add them to your shelf.", mode)
                self.shelf_list.setItemWidget(w_empty, empty_widget)
        except Exception as e:
            print(f"[Shelf Load Exception]: {e}")

    def add_shelf_item_to_widget(self, f_item):
        accent = resolve_accent_color(self.settings) if self.settings else "#38bdf8"
        mode = self.settings.get("theme_mode", "dark") if self.settings else "dark"
        pal = THEME_PALETTES.get(mode, THEME_PALETTES["dark"])

        if isinstance(f_item, str):
            f_name = os.path.basename(f_item)
            f_path = f_item
        else:
            f_name = f_item.get("name", "File")
            f_path = f_item.get("path", "")

        w_item = QListWidgetItem(self.shelf_list)
        w_item.setSizeHint(QSize(0, 52))

        row = QWidget()
        r_box = QHBoxLayout(row)
        r_box.setContentsMargins(10, 4, 10, 4)
        r_box.setSpacing(6)

        is_img = f_name.lower().endswith(('.png', '.jpg', '.jpeg', '.webp', '.bmp', '.gif'))
        icon_str = "📸" if ("screenshot" in f_name.lower() or is_img) else "📄"
        lbl = QLabel(f"{icon_str} {f_name}")
        lbl.setStyleSheet(f"color: {pal['text_primary']}; background: transparent; font-size: 10.5px; font-weight: 600; font-family: 'Segoe UI', sans-serif; letter-spacing: normal;")

        open_btn = QPushButton("Open")
        open_btn.setFixedSize(44, 24)
        open_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        open_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        open_btn.setStyleSheet(f"QPushButton {{ background: {pal['input_bg']}; color: {pal['text_primary']}; border-radius: 4px; font-size: 9.5px; padding: 0 6px; }} QPushButton:hover {{ background: {accent}; color: #ffffff; }}")
        open_btn.clicked.connect(lambda _, p=f_path: os.startfile(p) if os.path.exists(p) else None)

        copy_btn = QPushButton("Copy")
        copy_btn.setFixedSize(44, 24)
        copy_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        copy_btn.setStyleSheet(f"QPushButton {{ background: {pal['input_bg']}; color: {pal['text_primary']}; border-radius: 4px; font-size: 9.5px; padding: 0 6px; }} QPushButton:hover {{ background: {accent}; color: #ffffff; }}")

        def copy_shelf_file(btn_obj, fp):
            clipboard = QApplication.clipboard()
            mime = QMimeData()
            if os.path.exists(fp):
                mime.setUrls([QUrl.fromLocalFile(fp)])
            mime.setText(fp)
            clipboard.setMimeData(mime)
            flash_copy_feedback(btn_obj, "Copied!")

        copy_btn.clicked.connect(lambda _, b=copy_btn, p=f_path: copy_shelf_file(b, p))

        del_btn = QPushButton("🗑️")
        del_btn.setFixedSize(24, 24)
        del_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        del_btn.setStyleSheet("QPushButton { background-color: rgba(239, 68, 68, 0.15); color: #ef4444; border-radius: 4px; border: 1px solid rgba(239, 68, 68, 0.3); font-size: 9.5px; } QPushButton:hover { background-color: #ef4444; color: #ffffff; }")
        del_btn.clicked.connect(lambda _, p=f_path: self.on_delete_shelf_clicked(p))

        r_box.addWidget(lbl, 1, Qt.AlignmentFlag.AlignVCenter)
        r_box.addWidget(open_btn, 0, Qt.AlignmentFlag.AlignVCenter)
        r_box.addWidget(copy_btn, 0, Qt.AlignmentFlag.AlignVCenter)
        r_box.addWidget(del_btn, 0, Qt.AlignmentFlag.AlignVCenter)

        self.shelf_list.setItemWidget(w_item, row)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls() or event.mimeData().hasText():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                fp = url.toLocalFile()
                if fp:
                    self.storage.add_shelf_file(fp)
            self.load_shelf_files()
            self.switch_sub_tab(1)
            event.acceptProposedAction()


# 5. CALENDAR TAB WIDGET
class DayCellWidget(QWidget):
    cell_clicked = pyqtSignal(QDate)

    def __init__(self, date_obj: QDate, is_current_month: bool, is_today: bool, is_selected: bool, has_events: bool, accent_color: str, mode: str = "dark", parent=None):
        super().__init__(parent)
        self.date_obj = date_obj
        self.is_current_month = is_current_month
        self.is_today = is_today
        self.is_selected = is_selected
        self.has_events = has_events
        self.accent_color = accent_color
        self.theme_mode = mode
        self.is_hovered = False

        self.setFixedSize(36, 32)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self.hover_timer = QTimer(self)
        self.hover_timer.setSingleShot(True)
        self.hover_timer.timeout.connect(self.on_hover_timeout)

    def enterEvent(self, event):
        self.hover_timer.start(80)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.hover_timer.stop()
        if self.is_hovered:
            self.is_hovered = False
            self.update()
        super().leaveEvent(event)

    def on_hover_timeout(self):
        self.is_hovered = True
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.cell_clicked.emit(self.date_obj)
        super().mousePressEvent(event)

    def paintEvent(self, event):
        painter = QPainter()
        if not painter.begin(self):
            return
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = QRectF(0, 0, self.width(), self.height())
        accent = QColor(self.accent_color)
        pal = THEME_PALETTES.get(self.theme_mode, THEME_PALETTES["dark"])

        if self.is_selected:
            painter.setBrush(QBrush(accent))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(rect.adjusted(2, 2, -2, -2), 6, 6)
            text_color = QColor("#ffffff")
        elif self.is_today:
            border_pen = QPen(accent, 1.5)
            painter.setPen(border_pen)
            painter.setBrush(QBrush(QColor(128, 128, 128, 25)))
            painter.drawRoundedRect(rect.adjusted(2, 2, -2, -2), 6, 6)
            text_color = accent
        elif self.is_hovered:
            painter.setBrush(QBrush(QColor(128, 128, 128, 30)))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(rect.adjusted(2, 2, -2, -2), 6, 6)
            text_color = QColor(pal["text_primary"])
        else:
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(Qt.PenStyle.NoPen)
            text_color = QColor(pal["text_primary"]) if self.is_current_month else QColor(pal["text_muted"])

        painter.setPen(text_color)
        font = QFont("Segoe UI", 9, QFont.Weight.Bold if (self.is_today or self.is_selected) else QFont.Weight.Normal)
        painter.setFont(font)
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, str(self.date_obj.day()))

        if self.has_events:
            dot_color = QColor("#ffffff") if self.is_selected else accent
            painter.setBrush(QBrush(dot_color))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QPointF(self.width() / 2.0, self.height() - 4.5), 1.8, 1.8)


class CalendarTabWidget(QWidget):
    def __init__(self, storage: StorageManager, settings: SettingsManager, parent=None):
        super().__init__(parent)
        self.storage = storage
        self.settings = settings
        self.selected_date = QDate.currentDate()
        self.current_view_date = QDate.currentDate()
        self.init_ui()

        self.storage.calendar_changed.connect(lambda: (self.render_custom_calendar(), self.load_events()))

    def init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(6, 6, 6, 6)
        main_layout.setSpacing(8)

        accent = resolve_accent_color(self.settings)
        mode = self.settings.get("theme_mode", "dark")
        pal = THEME_PALETTES.get(mode, THEME_PALETTES["dark"])

        card_cal = GlassPanel(category_key="calendar", corner_radius=10)
        left_box = QVBoxLayout(card_cal)
        left_box.setContentsMargins(8, 6, 8, 6)
        left_box.setSpacing(4)

        header_bar = QHBoxLayout()
        header_bar.setSpacing(4)

        self.btn_prev_m = QPushButton("◀")
        self.btn_next_m = QPushButton("▶")
        self.month_year_lbl = QLabel()
        self.month_year_lbl.setStyleSheet(f"color: {pal['text_primary']}; font-size: 11px; font-weight: bold; background: transparent;")
        self.btn_today = QPushButton("Today")

        for btn in (self.btn_prev_m, self.btn_next_m, self.btn_today):
            btn.setFixedHeight(20)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(f"QPushButton {{ background: {pal['input_bg']}; color: {pal['text_primary']}; border-radius: 4px; font-size: 9px; padding: 0 6px; }} QPushButton:hover {{ background: {accent}; color: #ffffff; }}")

        self.btn_prev_m.clicked.connect(self.prev_month)
        self.btn_next_m.clicked.connect(self.next_month)
        self.btn_today.clicked.connect(self.jump_today)

        header_bar.addWidget(self.btn_prev_m)
        header_bar.addWidget(self.month_year_lbl, 1)
        header_bar.addWidget(self.btn_next_m)
        header_bar.addWidget(self.btn_today)
        left_box.addLayout(header_bar)

        self.weekday_labels = []
        weekdays_layout = QHBoxLayout()
        weekdays_layout.setSpacing(2)
        for w in ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]:
            lbl = QLabel(w)
            lbl.setFixedSize(36, 16)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet(f"color: {pal['text_muted']}; font-size: 8px; font-weight: bold; letter-spacing: 0.5px; background: transparent;")
            self.weekday_labels.append(lbl)
            weekdays_layout.addWidget(lbl)
        left_box.addLayout(weekdays_layout)

        self.grid_widget = QWidget()
        self.grid_widget.setStyleSheet("background: transparent;")
        self.grid_layout = QGridLayout(self.grid_widget)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        self.grid_layout.setSpacing(2)
        left_box.addWidget(self.grid_widget)

        main_layout.addWidget(card_cal, 3)

        card_events = GlassPanel(category_key="calendar", corner_radius=10)
        right_panel = QVBoxLayout(card_events)
        right_panel.setContentsMargins(8, 6, 8, 6)
        right_panel.setSpacing(6)

        self.date_header = QLabel(f"Events: {self.selected_date.toString('yyyy-MM-dd')}")
        self.date_header.setStyleSheet(f"color: {accent}; font-size: 10px; font-weight: bold; background: transparent;")
        right_panel.addWidget(self.date_header)

        input_box = QHBoxLayout()
        input_box.setSpacing(4)
        self.event_input = QLineEdit()
        self.event_input.setPlaceholderText("Add event for selected date...")
        self.event_input.setFixedHeight(26)
        self.event_input.setStyleSheet(f"QLineEdit {{ background: {pal['input_bg']}; border: 1px solid {pal['input_border']}; border-radius: 6px; color: {pal['text_primary']}; padding: 2px 8px; font-size: 10px; }} QLineEdit:hover {{ border: 1px solid {accent}; }}")
        self.event_input.returnPressed.connect(self.add_event)

        self.add_btn = QPushButton("+ Add")
        self.add_btn.setFixedHeight(26)
        self.add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.add_btn.setStyleSheet(f"QPushButton {{ background-color: {accent}; color: #ffffff; font-weight: bold; border-radius: 6px; border: none; padding: 0 8px; font-size: 9px; }}")
        self.add_btn.clicked.connect(self.add_event)

        input_box.addWidget(self.event_input)
        input_box.addWidget(self.add_btn)
        right_panel.addLayout(input_box)

        self.event_list = QListWidget()
        self.event_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.event_list.setStyleSheet(get_list_widget_qss(accent, mode))
        self.cal_scroll_filter = SmoothScrollFilter(self.event_list, step_size=40, duration=200)
        right_panel.addWidget(self.event_list)

        main_layout.addWidget(card_events, 2)
        self.render_custom_calendar()
        self.load_events()

    def apply_theme(self, accent_color: str, mode: str = "dark"):
        pal = THEME_PALETTES.get(mode, THEME_PALETTES["dark"])
        for gp in self.findChildren(GlassPanel):
            gp.apply_theme(accent_color, mode)

        for lbl in self.weekday_labels:
            lbl.setStyleSheet(f"color: {pal['text_muted']}; font-size: 8px; font-weight: bold; letter-spacing: 0.5px; background: transparent;")

        self.month_year_lbl.setStyleSheet(f"color: {pal['text_primary']}; font-size: 11px; font-weight: bold; background: transparent;")
        self.date_header.setStyleSheet(f"color: {accent_color}; font-size: 10px; font-weight: bold; background: transparent;")
        self.add_btn.setStyleSheet(f"QPushButton {{ background-color: {accent_color}; color: #ffffff; font-weight: bold; border-radius: 6px; border: none; padding: 0 8px; font-size: 9px; }}")
        self.event_input.setStyleSheet(f"QLineEdit {{ background: {pal['input_bg']}; border: 1px solid {pal['input_border']}; border-radius: 6px; color: {pal['text_primary']}; padding: 2px 8px; font-size: 10px; }} QLineEdit:hover {{ border: 1px solid {accent_color}; }}")
        self.event_list.setStyleSheet(get_list_widget_qss(accent_color, mode))

        for btn in (self.btn_prev_m, self.btn_next_m, self.btn_today):
            btn.setStyleSheet(f"QPushButton {{ background: {pal['input_bg']}; color: {pal['text_primary']}; border-radius: 4px; font-size: 9px; padding: 0 6px; }} QPushButton:hover {{ background: {accent_color}; color: #ffffff; }}")

        self.render_custom_calendar()

    def prev_month(self):
        self.current_view_date = self.current_view_date.addMonths(-1)
        self.render_custom_calendar()

    def next_month(self):
        self.current_view_date = self.current_view_date.addMonths(1)
        self.render_custom_calendar()

    def jump_today(self):
        self.current_view_date = QDate.currentDate()
        self.on_cell_clicked(QDate.currentDate())

    def on_cell_clicked(self, clicked_date: QDate):
        self.selected_date = clicked_date
        self.date_header.setText(f"Events: {self.selected_date.toString('yyyy-MM-dd')}")
        self.render_custom_calendar()
        self.load_events()

    def render_custom_calendar(self):
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        accent = resolve_accent_color(self.settings)
        mode = self.settings.get("theme_mode", "dark")

        year = self.current_view_date.year()
        month = self.current_view_date.month()
        self.month_year_lbl.setText(f"{pycalendar.month_name[month]} {year}")

        first_day_of_month = QDate(year, month, 1)
        start_day_of_week = first_day_of_month.dayOfWeek()

        start_date = first_day_of_month.addDays(-(start_day_of_week - 1))
        today_date = QDate.currentDate()
        cal_data = self.storage.load_calendar()

        curr_date = start_date
        for r in range(6):
            for c in range(7):
                is_curr_m = (curr_date.month() == month)
                is_tod = (curr_date == today_date)
                is_sel = (curr_date == self.selected_date)
                has_evts = bool(cal_data.get(curr_date.toString("yyyy-MM-dd"), []))

                cell = DayCellWidget(curr_date, is_curr_m, is_tod, is_sel, has_evts, accent, mode)
                cell.cell_clicked.connect(self.on_cell_clicked)
                self.grid_layout.addWidget(cell, r, c)
                curr_date = curr_date.addDays(1)

    def load_events(self):
        self.event_list.clear()
        cal_data = self.storage.load_calendar()
        date_str = self.selected_date.toString("yyyy-MM-dd")
        events = cal_data.get(date_str, [])
        accent = resolve_accent_color(self.settings)
        mode = self.settings.get("theme_mode", "dark")
        pal = THEME_PALETTES.get(mode, THEME_PALETTES["dark"])

        if events:
            for ev in events:
                ev_id = ev.get('id') if isinstance(ev, dict) else str(ev)
                ev_title = ev.get('title', '') if isinstance(ev, dict) else str(ev)

                w_item = QListWidgetItem(self.event_list)
                w_item.setSizeHint(QSize(0, 32))

                row = QWidget()
                row.setStyleSheet("background: transparent;")
                r_box = QHBoxLayout(row)
                r_box.setContentsMargins(6, 2, 6, 2)
                r_box.setSpacing(6)

                lbl_b = QLabel("•")
                lbl_b.setStyleSheet(f"color: {accent}; font-size: 11px; font-weight: bold; background: transparent;")
                r_box.addWidget(lbl_b)

                lbl_t = ElidedLabel(ev_title)
                lbl_t.setStyleSheet(f"color: {pal['text_primary']}; font-size: 10px; font-weight: 600; background: transparent;")
                r_box.addWidget(lbl_t, 1)

                del_btn = QPushButton("🗑️")
                del_btn.setFixedSize(22, 22)
                del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                del_btn.setToolTip("Delete Event")
                del_btn.setStyleSheet("QPushButton { background-color: rgba(239, 68, 68, 0.12); color: #ef4444; border-radius: 4px; border: 1px solid rgba(239, 68, 68, 0.25); font-size: 9.5px; } QPushButton:hover { background-color: #ef4444; color: #ffffff; }")
                del_btn.clicked.connect(lambda _, eid=ev_id, dstr=date_str: self.delete_event(dstr, eid))
                r_box.addWidget(del_btn)

                self.event_list.setItemWidget(w_item, row)
        else:
            w_empty = QListWidgetItem(self.event_list)
            w_empty.setSizeHint(QSize(0, 84))
            empty_widget = make_empty_state("📅", "No Events Today", "Click + Add above to schedule an event.", self.settings.get("theme_mode", "dark"))
            self.event_list.setItemWidget(w_empty, empty_widget)

    def delete_event(self, date_str: str, event_id: str):
        self.storage.delete_calendar_event(date_str, event_id)
        self.render_custom_calendar()
        self.load_events()

    def add_event(self):
        txt = self.event_input.text().strip()
        if txt:
            date_str = self.selected_date.toString("yyyy-MM-dd")
            self.storage.add_calendar_event(date_str, txt)
            self.event_input.clear()
            self.render_custom_calendar()
            self.load_events()


class SoundSelectorWidget(QWidget):
    """Reusable Sound Selector Widget supporting built-in chimes, custom audio files, audition preview, and persistent library storage."""
    def __init__(self, storage: StorageManager, settings: SettingsManager = None, parent=None):
        super().__init__(parent)
        self.storage = storage
        self.settings = settings
        self.preview_player = None
        self.audio_output = None
        self.init_ui()

    def init_ui(self):
        accent = resolve_accent_color(self.settings) if self.settings else "#38bdf8"
        mode = self.settings.get("theme_mode", "dark") if self.settings else "dark"

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(3)

        self.sound_combo = NoWheelComboBox()
        self.sound_combo.setFixedHeight(22)
        self.sound_combo.setStyleSheet(get_combobox_qss(accent, mode))
        self.sound_combo.currentIndexChanged.connect(self.on_combo_index_changed)

        self.btn_preview = QPushButton("▶️")
        self.btn_preview.setFixedSize(22, 22)
        self.btn_preview.setToolTip("Preview / Audition Sound")
        self.btn_preview.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_preview.setStyleSheet(f"QPushButton {{ background: rgba(255,255,255,0.08); color: white; border-radius: 4px; font-size: 10px; border: 1px solid rgba(255,255,255,0.1); }} QPushButton:hover {{ background: {accent}; }}")
        self.btn_preview.clicked.connect(self.preview_selected_sound)

        self.btn_delete = QPushButton("🗑️")
        self.btn_delete.setFixedSize(22, 22)
        self.btn_delete.setToolTip("Remove Custom Sound from Library")
        self.btn_delete.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_delete.setStyleSheet("QPushButton { background: rgba(239,68,68,0.15); color: #ef4444; border-radius: 4px; font-size: 9.5px; border: 1px solid rgba(239,68,68,0.3); } QPushButton:hover { background: #ef4444; color: white; }")
        self.btn_delete.clicked.connect(self.delete_selected_custom_sound)
        self.btn_delete.hide()

        layout.addWidget(self.sound_combo, 1)
        layout.addWidget(self.btn_preview)
        layout.addWidget(self.btn_delete)

        self.populate_sounds()

        if self.storage:
            self.storage.custom_sounds_changed.connect(self.populate_sounds)

    def populate_sounds(self):
        current_data = self.get_selected_sound_value()
        self.sound_combo.blockSignals(True)
        self.sound_combo.clear()

        # Built-in Chimes
        self.sound_combo.addItem("🔔 System Exclamation", "system_exclamation")
        self.sound_combo.addItem("🔔 System Asterisk", "system_asterisk")
        self.sound_combo.addItem("🔔 System Notification", "system_notification")

        # Custom Sounds
        if self.storage:
            custom_sounds = self.storage.load_custom_sounds()
            if custom_sounds:
                for sound in custom_sounds:
                    title = sound.get("title", "Custom Sound")
                    path = sound.get("path", "")
                    self.sound_combo.addItem(f"🎵 {title}", path)

        # Add Custom Action
        self.sound_combo.addItem("➕ Add Custom Sound...", "add_custom")

        if current_data:
            idx = self.sound_combo.findData(current_data)
            if idx >= 0:
                self.sound_combo.setCurrentIndex(idx)

        self.sound_combo.blockSignals(False)
        self.update_btn_states()

    def update_btn_states(self):
        val = self.get_selected_sound_value()
        if val and os.path.exists(str(val)) and val not in ["system_exclamation", "system_asterisk", "system_notification", "add_custom"]:
            self.btn_delete.show()
        else:
            self.btn_delete.hide()

    def get_selected_sound_value(self) -> str:
        return self.sound_combo.currentData()

    def set_selected_sound_value(self, val: str):
        if not val:
            return
        idx = self.sound_combo.findData(val)
        if idx >= 0:
            self.sound_combo.setCurrentIndex(idx)

    def on_combo_index_changed(self, idx: int):
        val = self.sound_combo.currentData()
        if val == "add_custom":
            self.browse_custom_sound()
        self.update_btn_states()

    def browse_custom_sound(self):
        fp, _ = QFileDialog.getOpenFileName(
            self,
            "Select Custom Alarm Sound File",
            "",
            "Audio Files (*.mp3 *.wav *.ogg *.m4a *.flac *.wma);;All Files (*.*)"
        )
        if fp:
            title = os.path.splitext(os.path.basename(fp))[0].replace("_", " ").title()
            new_item = self.storage.add_custom_sound(title, fp)
            self.populate_sounds()
            self.set_selected_sound_value(fp)
        else:
            self.sound_combo.setCurrentIndex(0)

    def preview_selected_sound(self):
        sound_val = self.get_selected_sound_value()
        if not sound_val or sound_val == "add_custom":
            return

        if sound_val and os.path.exists(str(sound_val)):
            try:
                from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
                if not self.preview_player:
                    self.preview_player = QMediaPlayer(self)
                    self.audio_output = QAudioOutput(self)
                    self.preview_player.setAudioOutput(self.audio_output)
                    self.audio_output.setVolume(1.0)

                self.preview_player.stop()
                self.preview_player.setSource(QUrl.fromLocalFile(sound_val))
                self.preview_player.play()
                print(f"[Sound Preview]: Auditioning custom file: {sound_val}")
                return
            except Exception as e:
                print(f"[Sound Preview Error]: {e}")

        SystemMonitor.play_alarm_sound_effect(sound_val)

    def delete_selected_custom_sound(self):
        sound_val = self.get_selected_sound_value()
        if not sound_val or sound_val in ["system_exclamation", "system_asterisk", "system_notification", "add_custom"]:
            return

        alarms = self.storage.load_alarms()
        timetable = self.storage.load_timetable()
        in_use_alarms = [a for a in alarms if a.get("sound") == sound_val]
        in_use_tt = [t for t in timetable if t.get("sound") == sound_val]

        if in_use_alarms or in_use_tt:
            res = QMessageBox.warning(
                self,
                "Custom Sound In Use",
                f"This custom sound is currently assigned to {len(in_use_alarms) + len(in_use_tt)} alarm(s)/task(s).\n\nDo you want to reassign those alarms to the default chime and remove this sound?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if res != QMessageBox.StandardButton.Yes:
                return

            for a in in_use_alarms:
                a["sound"] = "system_exclamation"
            self.storage.save_alarms(alarms)

            for t in in_use_tt:
                t["sound"] = "system_exclamation"
            self.storage.save_timetable(timetable)

        self.storage.delete_custom_sound(sound_val)
        self.populate_sounds()

    def apply_theme(self, accent_color: str, mode: str = "dark"):
        combo_qss = get_combobox_qss(accent_color, mode)
        if hasattr(self, 'sound_combo'):
            self.sound_combo.setStyleSheet(combo_qss)


# 6. ALARMS & TIMETABLE MERGED TAB WIDGET
class AlarmsTabWidget(QWidget):
    def __init__(self, storage: StorageManager, settings: SettingsManager, parent=None):
        super().__init__(parent)
        self.storage = storage
        self.settings = settings
        self.editing_alarm_id = None
        self.init_ui()

        self.storage.alarms_changed.connect(self.load_alarms)
        self.storage.timetable_changed.connect(self.load_timetable)

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(6, 6, 6, 6)
        main_layout.setSpacing(6)

        accent = resolve_accent_color(self.settings)
        mode = self.settings.get("theme_mode", "dark")
        pal = THEME_PALETTES.get(mode, THEME_PALETTES["dark"])
        card_qss = get_card_qss(mode)

        self.form_labels = []

        nav_box = QHBoxLayout()
        nav_box.setSpacing(4)

        self.btn_sub_alarms = QPushButton("🔔 Alarms")
        self.btn_sub_timetable = QPushButton("📅 Timetable Schedule")

        for btn in (self.btn_sub_alarms, self.btn_sub_timetable):
            btn.setFixedHeight(22)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)

        self.btn_sub_alarms.clicked.connect(lambda: self.switch_sub_tab(0))
        self.btn_sub_timetable.clicked.connect(lambda: self.switch_sub_tab(1))

        nav_box.addWidget(self.btn_sub_alarms)
        nav_box.addWidget(self.btn_sub_timetable)
        main_layout.addLayout(nav_box)

        self.sub_stacked = QStackedWidget()

        # SUB-VIEW 0: ALARMS BUILDER & LIST
        self.alarms_sub_widget = QWidget()
        alarms_sub_layout = QVBoxLayout(self.alarms_sub_widget)
        alarms_sub_layout.setContentsMargins(0, 2, 0, 0)
        alarms_sub_layout.setSpacing(4)

        setter_card = GlassPanel(category_key="alarms", corner_radius=10)
        setter_box = QVBoxLayout(setter_card)
        setter_box.setContentsMargins(8, 6, 8, 6)
        setter_box.setSpacing(5)

        self.card_title_lbl = QLabel("➕ Set New Alarm")
        self.card_title_lbl.setStyleSheet(f"color: {accent}; font-size: 10px; font-weight: 800; letter-spacing: 0.5px; background: transparent;")
        setter_box.addWidget(self.card_title_lbl)

        r1 = QHBoxLayout()
        r1.setSpacing(4)

        lbl_t = QLabel("Time:")
        lbl_t.setStyleSheet(f"color: {pal['text_primary']}; font-size: 10px; font-weight: 700; background: transparent;")
        self.form_labels.append(lbl_t)

        is_12h = self.settings.get("time_format_12h", True)
        self.alarm_time_picker = WheelTimePickerWidget(is_12h=is_12h)

        self.alarm_title_input = QLineEdit()
        self.alarm_title_input.setPlaceholderText("Alarm title (e.g. Standup Meeting)...")
        self.alarm_title_input.setFixedHeight(24)
        self.alarm_title_input.setStyleSheet(f"QLineEdit {{ background: {pal['input_bg']}; border: 1px solid {pal['input_border']}; border-radius: 5px; color: {pal['text_primary']}; padding: 2px 6px; font-size: 10px; }} QLineEdit:hover {{ border: 1px solid {accent}; }}")

        r1.addWidget(lbl_t)
        r1.addWidget(self.alarm_time_picker)
        r1.addWidget(self.alarm_title_input, 1)
        setter_box.addLayout(r1)

        r2 = QHBoxLayout()
        self.day_chips = {}
        for d_code, d_lbl in [("M", "Mon"), ("T", "Tue"), ("W", "Wed"), ("Th", "Thu"), ("F", "Fri"), ("Sa", "Sat"), ("Su", "Sun")]:
            btn = QPushButton(d_code)
            btn.setFixedSize(22, 20)
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(f"QPushButton {{ background: {pal['sub_btn_bg']}; color: {pal['sub_btn_text']}; border: 1px solid {pal['sub_btn_border']}; border-radius: 4px; font-size: 9px; font-weight: bold; }} QPushButton:checked {{ background: {accent}; color: #ffffff; }}")
            self.day_chips[d_lbl] = btn
            r2.addWidget(btn)

        self.sound_selector = SoundSelectorWidget(self.storage, self.settings)

        self.add_btn = QPushButton("+ Add Alarm")
        self.add_btn.setFixedHeight(22)
        self.add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.add_btn.setStyleSheet(f"QPushButton {{ background-color: {accent}; color: #ffffff; font-weight: bold; border-radius: 4px; border: none; padding: 0 8px; font-size: 9px; }}")
        self.add_btn.clicked.connect(self.on_add_or_update_alarm)

        self.cancel_edit_btn = QPushButton("Cancel")
        self.cancel_edit_btn.setFixedHeight(22)
        self.cancel_edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cancel_edit_btn.setStyleSheet(f"QPushButton {{ background-color: {pal['sub_btn_bg']}; color: {pal['sub_btn_text']}; border-radius: 4px; border: 1px solid {pal['sub_btn_border']}; font-size: 9px; padding: 0 6px; }}")
        self.cancel_edit_btn.clicked.connect(self.reset_form_to_add_mode)
        self.cancel_edit_btn.hide()

        r2.addStretch()
        r2.addWidget(self.sound_selector)
        r2.addWidget(self.cancel_edit_btn)
        r2.addWidget(self.add_btn)
        setter_box.addLayout(r2)

        alarms_sub_layout.addWidget(setter_card)

        list_head = QHBoxLayout()
        self.lbl_list = QLabel("SCHEDULED ALARMS")
        self.lbl_list.setStyleSheet(f"color: {pal['text_primary']}; font-size: 10px; font-weight: 800; letter-spacing: 0.5px; background: transparent;")
        self.form_labels.append(self.lbl_list)
        list_head.addWidget(self.lbl_list)
        list_head.addStretch()
        alarms_sub_layout.addLayout(list_head)

        self.alarm_list_widget = QListWidget()
        self.alarm_list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.alarm_list_widget.setStyleSheet(get_list_widget_qss(accent, mode))
        self.alarm_scroll_filter = SmoothScrollFilter(self.alarm_list_widget, step_size=40, duration=200)
        alarms_sub_layout.addWidget(self.alarm_list_widget)

        self.sub_stacked.addWidget(self.alarms_sub_widget)

        # SUB-VIEW 1: TIMETABLE TASKS BUILDER & LIST
        self.timetable_sub_widget = QWidget()
        tt_sub_layout = QVBoxLayout(self.timetable_sub_widget)
        tt_sub_layout.setContentsMargins(0, 2, 0, 0)
        tt_sub_layout.setSpacing(4)

        tt_card = GlassPanel(category_key="timetable", corner_radius=10)
        tt_box = QVBoxLayout(tt_card)
        tt_box.setContentsMargins(8, 6, 8, 6)
        tt_box.setSpacing(5)

        self.tt_title = QLabel("➕ Add Timetable Task")
        self.tt_title.setStyleSheet(f"color: {accent}; font-size: 10px; font-weight: 800; letter-spacing: 0.5px; background: transparent;")
        tt_box.addWidget(self.tt_title)

        t_r1 = QHBoxLayout()
        t_r1.setSpacing(4)

        t_lbl_time = QLabel("Time:")
        t_lbl_time.setStyleSheet(f"color: {pal['text_primary']}; font-size: 10px; font-weight: 700; background: transparent;")
        self.form_labels.append(t_lbl_time)

        self.tt_time_picker = WheelTimePickerWidget(is_12h=is_12h)

        self.tt_title_input = QLineEdit()
        self.tt_title_input.setPlaceholderText("Task title (e.g. Lunch Break, Gym)...")
        self.tt_title_input.setFixedHeight(24)
        self.tt_title_input.setStyleSheet(f"QLineEdit {{ background: {pal['input_bg']}; border: 1px solid {pal['input_border']}; border-radius: 5px; color: {pal['text_primary']}; padding: 2px 6px; font-size: 10px; }} QLineEdit:hover {{ border: 1px solid {accent}; }}")

        t_r1.addWidget(t_lbl_time)
        t_r1.addWidget(self.tt_time_picker)
        t_r1.addWidget(self.tt_title_input, 1)
        tt_box.addLayout(t_r1)

        t_r2 = QHBoxLayout()
        t_r2.setSpacing(4)

        self.tt_add_btn = QPushButton("+ Add Task")
        self.tt_add_btn.setFixedHeight(22)
        self.tt_add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.tt_add_btn.setStyleSheet(f"QPushButton {{ background-color: {accent}; color: #ffffff; font-weight: bold; border-radius: 4px; border: none; padding: 0 8px; font-size: 9px; }}")
        self.tt_add_btn.clicked.connect(self.on_add_timetable_task)

        t_r2.addStretch()
        t_r2.addWidget(self.tt_add_btn)
        tt_box.addLayout(t_r2)

        tt_sub_layout.addWidget(tt_card)

        tt_list_head = QHBoxLayout()
        self.lbl_tt_list = QLabel("TODAY'S TIMETABLE SCHEDULE")
        self.lbl_tt_list.setStyleSheet(f"color: {pal['text_primary']}; font-size: 10px; font-weight: 800; letter-spacing: 0.5px; background: transparent;")
        self.form_labels.append(self.lbl_tt_list)
        tt_list_head.addWidget(self.lbl_tt_list)
        tt_list_head.addStretch()
        tt_sub_layout.addLayout(tt_list_head)

        self.timetable_list_widget = QListWidget()
        self.timetable_list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.timetable_list_widget.setStyleSheet(get_list_widget_qss(accent, mode))
        self.timetable_scroll_filter = SmoothScrollFilter(self.timetable_list_widget, step_size=40, duration=200)
        tt_sub_layout.addWidget(self.timetable_list_widget)

        self.sub_stacked.addWidget(self.timetable_sub_widget)

        main_layout.addWidget(self.sub_stacked)

        self.switch_sub_tab(0)
        self.load_alarms()
        self.load_timetable()

    def apply_theme(self, accent_color: str, mode: str = "dark"):
        pal = THEME_PALETTES.get(mode, THEME_PALETTES["dark"])
        for gp in self.findChildren(GlassPanel):
            gp.apply_theme(accent_color, mode)

        for lbl in self.form_labels:
            lbl.setStyleSheet(f"color: {pal['text_primary']}; font-size: 10px; font-weight: 700; background: transparent;")

        self.card_title_lbl.setStyleSheet(f"color: {accent_color}; font-size: 10px; font-weight: 800; letter-spacing: 0.5px; background: transparent;")
        self.tt_title.setStyleSheet(f"color: {accent_color}; font-size: 10px; font-weight: 800; letter-spacing: 0.5px; background: transparent;")
        self.add_btn.setStyleSheet(f"QPushButton {{ background-color: {accent_color}; color: #ffffff; font-weight: bold; border-radius: 4px; border: none; padding: 0 8px; font-size: 9px; }}")
        self.tt_add_btn.setStyleSheet(f"QPushButton {{ background-color: {accent_color}; color: #ffffff; font-weight: bold; border-radius: 4px; border: none; padding: 0 8px; font-size: 9px; }}")

        combo_qss = get_combobox_qss(accent_color, mode)
        list_qss = get_list_widget_qss(accent_color, mode)
        input_qss = f"QLineEdit {{ background: {pal['input_bg']}; border: 1px solid {pal['input_border']}; border-radius: 5px; color: {pal['text_primary']}; padding: 2px 6px; font-size: 10px; }} QLineEdit:hover {{ border: 1px solid {accent_color}; }}"

        is_12h = self.settings.get("time_format_12h", True)
        if hasattr(self, 'alarm_time_picker'):
            self.alarm_time_picker.apply_theme(accent_color, mode)
            self.alarm_time_picker.set_12h_format(is_12h)
        if hasattr(self, 'tt_time_picker'):
            self.tt_time_picker.apply_theme(accent_color, mode)
            self.tt_time_picker.set_12h_format(is_12h)

        if hasattr(self, 'sound_selector'):
            self.sound_selector.apply_theme(accent_color, mode)

        self.alarm_title_input.setStyleSheet(input_qss)
        self.tt_title_input.setStyleSheet(input_qss)

        self.alarm_list_widget.setStyleSheet(list_qss)
        self.timetable_list_widget.setStyleSheet(list_qss)

        for btn in self.day_chips.values():
            btn.setStyleSheet(f"QPushButton {{ background: {pal['sub_btn_bg']}; color: {pal['sub_btn_text']}; border: 1px solid {pal['sub_btn_border']}; border-radius: 4px; font-size: 9px; font-weight: bold; }} QPushButton:checked {{ background: {accent_color}; color: #ffffff; }}")

        self.switch_sub_tab(self.sub_stacked.currentIndex())
        self.load_alarms()
        self.load_timetable()

    def switch_sub_tab(self, idx: int):
        self.sub_stacked.setCurrentIndex(idx)
        accent = resolve_accent_color(self.settings)
        mode = self.settings.get("theme_mode", "dark")
        pal = THEME_PALETTES.get(mode, THEME_PALETTES["dark"])

        if idx == 0:
            self.btn_sub_alarms.setStyleSheet(f"QPushButton {{ background-color: {accent}; color: #ffffff; font-weight: bold; border-radius: 4px; border: none; font-size: 9.5px; }}")
            self.btn_sub_timetable.setStyleSheet(f"QPushButton {{ background-color: {pal['sub_btn_bg']}; color: {pal['sub_btn_text']}; border-radius: 4px; border: 1px solid {pal['sub_btn_border']}; font-size: 9.5px; }}")
        else:
            self.btn_sub_timetable.setStyleSheet(f"QPushButton {{ background-color: {accent}; color: #ffffff; font-weight: bold; border-radius: 4px; border: none; font-size: 9.5px; }}")
            self.btn_sub_alarms.setStyleSheet(f"QPushButton {{ background-color: {pal['sub_btn_bg']}; color: {pal['sub_btn_text']}; border-radius: 4px; border: 1px solid {pal['sub_btn_border']}; font-size: 9.5px; }}")

    def load_alarms(self):
        self.alarm_list_widget.clear()
        alarms = self.storage.load_alarms()
        is_12h = self.settings.get("time_format_12h", True)
        mode = self.settings.get("theme_mode", "dark")

        if alarms:
            for al in alarms:
                self.add_alarm_item_widget(al, is_12h)
        else:
            w_item = QListWidgetItem(self.alarm_list_widget)
            w_item.setSizeHint(QSize(0, 84))
            empty_widget = make_empty_state("🔔", "No Alarms Scheduled", "Set a new alarm using the controls above.", mode)
            self.alarm_list_widget.setItemWidget(w_item, empty_widget)

    def add_alarm_item_widget(self, al: dict, is_12h: bool = True):
        accent = resolve_accent_color(self.settings)
        mode = self.settings.get("theme_mode", "dark")
        pal = THEME_PALETTES.get(mode, THEME_PALETTES["dark"])

        w_item = QListWidgetItem(self.alarm_list_widget)
        w_item.setSizeHint(QSize(0, 52))

        row = QWidget()
        r_box = QHBoxLayout(row)
        r_box.setContentsMargins(10, 4, 10, 4)
        r_box.setSpacing(8)

        disp_time = format_alarm_time(al.get("time", "00:00"), is_12h)
        t_lbl = QLabel(disp_time)
        t_lbl.setStyleSheet(f"color: {accent}; font-size: 11px; font-weight: bold; background: transparent; font-family: 'Segoe UI', sans-serif; letter-spacing: normal;")

        lbl_title = QLabel(al.get("label", "Alarm"))
        lbl_title.setWordWrap(True)
        lbl_title.setStyleSheet(f"color: {pal['text_primary']}; background: transparent; font-size: 10.5px; font-weight: 600; font-family: 'Segoe UI', sans-serif; letter-spacing: normal;")

        chk = QCheckBox()
        chk.setChecked(al.get("enabled", True))
        chk.setStyleSheet(get_checkbox_qss(accent, mode))
        chk.toggled.connect(lambda checked, aid=al.get("id"): self.toggle_alarm_state(aid, checked))

        edit_btn = QPushButton("\u270f\ufe0f")
        edit_btn.setFixedSize(24, 24)
        edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        edit_btn.setStyleSheet(f"QPushButton {{ background: {pal['sub_btn_bg']}; border-radius: 4px; font-size: 9.5px; }}")
        edit_btn.clicked.connect(lambda _, a=al: self.setup_alarm_edit(a))

        del_btn = QPushButton("\U0001F5D1")
        del_btn.setFixedSize(24, 24)
        del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        del_btn.setStyleSheet("QPushButton { background: rgba(239,68,68,0.2); color: #ef4444; border-radius: 4px; font-size: 9.5px; }")
        del_btn.clicked.connect(lambda _, aid=al.get("id"): self.delete_alarm(aid))

        r_box.addWidget(chk, 0, Qt.AlignmentFlag.AlignVCenter)
        r_box.addWidget(t_lbl, 0, Qt.AlignmentFlag.AlignVCenter)
        r_box.addWidget(lbl_title, 1, Qt.AlignmentFlag.AlignVCenter)
        r_box.addWidget(edit_btn, 0, Qt.AlignmentFlag.AlignVCenter)
        r_box.addWidget(del_btn, 0, Qt.AlignmentFlag.AlignVCenter)

        self.alarm_list_widget.setItemWidget(w_item, row)

    def toggle_alarm_state(self, alarm_id: str, enabled: bool):
        alarms = self.storage.load_alarms()
        for a in alarms:
            if a.get("id") == alarm_id:
                a["enabled"] = enabled
                break
        self.storage.save_alarms(alarms)

    def delete_alarm(self, alarm_id: str):
        alarms = self.storage.load_alarms()
        alarms = [a for a in alarms if a.get("id") != alarm_id]
        self.storage.save_alarms(alarms)
        self.load_alarms()

    def setup_alarm_edit(self, al: dict):
        self.editing_alarm_id = al.get("id")
        self.card_title_lbl.setText("✏️ Edit Scheduled Alarm")
        self.add_btn.setText("💾 Save Changes")
        self.cancel_edit_btn.show()

        if hasattr(self, 'alarm_time_picker'):
            self.alarm_time_picker.set_time_24h(al.get("time", "00:00"))
        self.alarm_title_input.setText(al.get("label", ""))
        if hasattr(self, 'sound_selector'):
            self.sound_selector.set_selected_sound_value(al.get("sound", "system_exclamation"))

        days = al.get("days", [])
        for d_lbl, btn in self.day_chips.items():
            btn.setChecked(d_lbl in days)

    def showEvent(self, event):
        super().showEvent(event)
        if not getattr(self, 'editing_alarm_id', None):
            self.prefill_current_time()

    def prefill_current_time(self):
        now_str = datetime.now().strftime("%H:%M")
        if hasattr(self, 'alarm_time_picker'):
            self.alarm_time_picker.set_time_24h(now_str)
        if hasattr(self, 'tt_time_picker'):
            self.tt_time_picker.set_time_24h(now_str)

    def reset_form_to_add_mode(self):
        self.editing_alarm_id = None
        accent = resolve_accent_color(self.settings)
        self.card_title_lbl.setText("➕ Set New Alarm")
        self.card_title_lbl.setStyleSheet(f"color: {accent}; font-size: 10px; font-weight: 800; letter-spacing: 0.5px; background: transparent;")
        self.add_btn.setText("+ Add Alarm")
        self.cancel_edit_btn.hide()
        self.alarm_title_input.clear()
        for btn in self.day_chips.values():
            btn.setChecked(False)
        self.prefill_current_time()

    def on_add_or_update_alarm(self):
        time_str = self.alarm_time_picker.get_time_24h()
        label = self.alarm_title_input.text().strip() or "Alarm"
        selected_days = [d_lbl for d_lbl, btn in self.day_chips.items() if btn.isChecked()]
        sound_val = self.sound_selector.get_selected_sound_value() if hasattr(self, 'sound_selector') else "system_exclamation"

        alarms = self.storage.load_alarms()
        if self.editing_alarm_id:
            for a in alarms:
                if a.get("id") == self.editing_alarm_id:
                    a["time"] = time_str
                    a["label"] = label
                    a["days"] = selected_days
                    a["sound"] = sound_val
                    break
        else:
            new_al = {
                "id": str(uuid.uuid4())[:8],
                "time": time_str,
                "label": label,
                "days": selected_days,
                "sound": sound_val,
                "enabled": True
            }
            alarms.append(new_al)

        self.storage.save_alarms(alarms)
        self.reset_form_to_add_mode()
        self.load_alarms()

    # Timetable Schedule Methods
    def load_timetable(self):
        self.timetable_list_widget.clear()
        timetable = self.storage.load_timetable()
        is_12h = self.settings.get("time_format_12h", True)
        mode = self.settings.get("theme_mode", "dark")

        if timetable:
            for entry in timetable:
                self.add_timetable_item_widget(entry, is_12h)
        else:
            w_item = QListWidgetItem(self.timetable_list_widget)
            w_item.setSizeHint(QSize(0, 84))
            empty_widget = make_empty_state("📅", "No Timetable Tasks", "Add a timetable schedule task above.", mode)
            self.timetable_list_widget.setItemWidget(w_item, empty_widget)

    def add_timetable_item_widget(self, entry: dict, is_12h: bool = True):
        accent = resolve_accent_color(self.settings)
        mode = self.settings.get("theme_mode", "dark")
        pal = THEME_PALETTES.get(mode, THEME_PALETTES["dark"])

        w_item = QListWidgetItem(self.timetable_list_widget)
        w_item.setSizeHint(QSize(0, 52))

        row = QWidget()
        r_box = QHBoxLayout(row)
        r_box.setContentsMargins(10, 4, 10, 4)
        r_box.setSpacing(8)

        chk = QCheckBox()
        chk.setChecked(bool(entry.get("is_completed", entry.get("completed", False))))
        chk.setStyleSheet(get_checkbox_qss(accent, mode))
        task_id = str(entry.get("id") or entry.get("title", ""))
        chk.toggled.connect(lambda checked, tid=task_id: self.toggle_timetable_task(tid, checked))

        disp_time = format_alarm_time(entry.get("time", "00:00"), is_12h)
        t_lbl = QLabel(disp_time)
        t_lbl.setStyleSheet(f"color: {accent}; font-size: 11px; font-weight: bold; background: transparent; font-family: 'Segoe UI', sans-serif; letter-spacing: normal;")

        lbl_title = QLabel(entry.get("title", "Task"))
        lbl_title.setWordWrap(True)

        if entry.get("is_completed", entry.get("completed", False)):
            lbl_title.setStyleSheet(f"color: {pal['text_muted']}; background: transparent; font-size: 10.5px; font-family: 'Segoe UI', sans-serif; letter-spacing: normal; text-decoration: line-through;")
        else:
            lbl_title.setStyleSheet(f"color: {pal['text_primary']}; background: transparent; font-size: 10.5px; font-weight: 600; font-family: 'Segoe UI', sans-serif; letter-spacing: normal;")

        del_btn = QPushButton("\U0001F5D1")
        del_btn.setFixedSize(24, 24)
        del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        del_btn.setStyleSheet("QPushButton { background: rgba(239,68,68,0.2); color: #ef4444; border-radius: 4px; font-size: 9.5px; }")
        del_btn.clicked.connect(lambda _, tid=task_id: self.delete_timetable_task(tid))

        r_box.addWidget(chk, 0, Qt.AlignmentFlag.AlignVCenter)
        r_box.addWidget(t_lbl, 0, Qt.AlignmentFlag.AlignVCenter)
        r_box.addWidget(lbl_title, 1, Qt.AlignmentFlag.AlignVCenter)
        r_box.addWidget(del_btn, 0, Qt.AlignmentFlag.AlignVCenter)

        self.timetable_list_widget.setItemWidget(w_item, row)

    def toggle_timetable_task(self, task_id: str, is_completed: bool):
        self.storage.toggle_timetable_task(task_id, is_completed)

    def delete_timetable_task(self, task_id: str):
        self.storage.delete_timetable_task(task_id)

    def on_add_timetable_task(self):
        time_str = self.tt_time_picker.get_time_24h()
        title = self.tt_title_input.text().strip() or "Timetable Task"

        new_entry = {
            "id": str(uuid.uuid4())[:8],
            "time": time_str,
            "title": title,
            "is_completed": False,
            "days": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
            "sound_enabled": True
        }

        timetable = self.storage.load_timetable()
        timetable.append(new_entry)
        self.storage.save_timetable(timetable)

        self.tt_title_input.clear()
        self.load_timetable()


# 7. APP LAUNCHER TAB WIDGET
INSTALLED_APPS_CACHE = None


class StartMenuScanThread(QThread):
    scanned_apps_ready = pyqtSignal(list)

    def run(self):
        apps = []
        known_exes = set()
        dirs = [
            os.path.join(os.environ.get("ProgramData", "C:\\ProgramData"), r"Microsoft\Windows\Start Menu\Programs"),
            os.path.join(os.environ.get("AppData", "C:\\Users\\Default\\AppData\\Roaming"), r"Microsoft\Windows\Start Menu\Programs")
        ]

        try:
            try:
                import pythoncom
                pythoncom.CoInitialize()
            except Exception:
                pass

            import win32com.client
            shell = win32com.client.Dispatch("WScript.Shell")

            for base_dir in dirs:
                if not os.path.exists(base_dir):
                    continue
                for root, _, files in os.walk(base_dir):
                    for fname in files:
                        if fname.lower().endswith(".lnk"):
                            lnk_path = os.path.join(root, fname)
                            try:
                                shortcut = shell.CreateShortCut(lnk_path)
                                target = shortcut.TargetPath
                                if target and target.lower().endswith(".exe") and os.path.exists(target):
                                    target_lower = target.lower()
                                    if "uninstall" in target_lower or "unins000" in target_lower or "setup" in target_lower:
                                        continue
                                    if target_lower not in known_exes:
                                        known_exes.add(target_lower)
                                        name = os.path.splitext(fname)[0]
                                        apps.append({
                                            "name": name,
                                            "path": target,
                                            "icon": "📱"
                                        })
                            except Exception:
                                pass
        except Exception as e:
            print(f"Start Menu Scan Thread Exception: {e}")

        apps.sort(key=lambda x: x["name"].lower())
        self.scanned_apps_ready.emit(apps)


class AddAppDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🚀 Add Application Shortcut")
        self.setFixedSize(480, 360)
        self.selected_app_name = ""
        self.selected_app_path = ""
        self.selected_app_icon = "🚀"

        self.setStyleSheet("""
            QDialog { background-color: #0f0f14; border: 1px solid rgba(255, 255, 255, 0.15); border-radius: 8px; }
            QLabel { color: #f8fafc; font-size: 10px; font-weight: bold; }
            QLineEdit { background: rgba(255, 255, 255, 0.08); border: 1px solid rgba(255, 255, 255, 0.15); border-radius: 5px; color: white; padding: 2px 6px; font-size: 10px; }
        """)

        self.init_ui()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Left:
            self.cycle_tab(-1)
            event.accept()
            return
        elif event.key() == Qt.Key.Key_Right:
            self.cycle_tab(1)
            event.accept()
            return
        super().keyPressEvent(event)

    def cycle_tab(self, direction: int):
        cur = self.stacked_tabs.currentIndex()
        count = self.stacked_tabs.count()
        new_idx = (cur + direction) % count
        self.switch_tab(new_idx)

    def switch_tab(self, idx: int):
        self.stacked_tabs.setCurrentIndex(idx)
        for i, btn in enumerate(self.tab_buttons):
            if i == idx:
                btn.setStyleSheet("QPushButton { background-color: #38bdf8; color: #ffffff; font-weight: bold; border-radius: 4px; border: none; font-size: 9px; }")
            else:
                btn.setStyleSheet("QPushButton { background-color: rgba(255, 255, 255, 0.08); color: #94a3b8; border-radius: 4px; border: 1px solid rgba(255, 255, 255, 0.1); font-size: 9px; }")

        if idx == 1 and not getattr(self, "running_apps_loaded", False):
            self.load_running_apps()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(6)

        # Header Flanking Chevrons & Tab Navigation Bar
        header_bar = QHBoxLayout()
        header_bar.setSpacing(4)

        self.btn_prev_tab = QPushButton("◀")
        self.btn_prev_tab.setFixedSize(22, 22)
        self.btn_prev_tab.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_prev_tab.setStyleSheet("QPushButton { background: rgba(255, 255, 255, 0.08); color: #f8fafc; border-radius: 4px; border: 1px solid rgba(255, 255, 255, 0.1); font-size: 9px; } QPushButton:hover { background: #38bdf8; color: #ffffff; }")
        self.btn_prev_tab.clicked.connect(lambda: self.cycle_tab(-1))

        self.btn_next_tab = QPushButton("▶")
        self.btn_next_tab.setFixedSize(22, 22)
        self.btn_next_tab.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_next_tab.setStyleSheet("QPushButton { background: rgba(255, 255, 255, 0.08); color: #f8fafc; border-radius: 4px; border: 1px solid rgba(255, 255, 255, 0.1); font-size: 9px; } QPushButton:hover { background: #38bdf8; color: #ffffff; }")
        self.btn_next_tab.clicked.connect(lambda: self.cycle_tab(1))

        self.btn_t0 = QPushButton("📱 Installed Apps")
        self.btn_t1 = QPushButton("🏃 Running Now")
        self.btn_t2 = QPushButton("📁 Browse Manually")
        self.tab_buttons = [self.btn_t0, self.btn_t1, self.btn_t2]

        for i, btn in enumerate(self.tab_buttons):
            btn.setFixedHeight(22)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _, idx=i: self.switch_tab(idx))

        header_bar.addWidget(self.btn_prev_tab)
        header_bar.addWidget(self.btn_t0)
        header_bar.addWidget(self.btn_t1)
        header_bar.addWidget(self.btn_t2)
        header_bar.addWidget(self.btn_next_tab)
        layout.addLayout(header_bar)

        self.stacked_tabs = QStackedWidget()

        # TAB 0: INSTALLED APPS (Start Menu Scanner)
        self.tab_installed = QWidget()
        t0_layout = QVBoxLayout(self.tab_installed)
        t0_layout.setContentsMargins(0, 4, 0, 0)
        t0_layout.setSpacing(4)

        t0_search_bar = QHBoxLayout()
        t0_search_bar.setSpacing(4)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Search installed applications...")
        self.search_input.textChanged.connect(self.filter_installed_apps)

        self.refresh_btn = QPushButton("🔄 Refresh")
        self.refresh_btn.setFixedSize(65, 22)
        self.refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.refresh_btn.setStyleSheet("QPushButton { background: rgba(255, 255, 255, 0.08); color: white; border-radius: 4px; font-size: 9px; }")
        self.refresh_btn.clicked.connect(self.force_rescan_installed)

        t0_search_bar.addWidget(self.search_input, 1)
        t0_search_bar.addWidget(self.refresh_btn)
        t0_layout.addLayout(t0_search_bar)

        self.lbl_installed_status = QLabel("⏳ Scanning Start Menu shortcuts...")
        self.lbl_installed_status.setStyleSheet("color: #38bdf8; font-size: 9.5px; font-style: italic;")
        t0_layout.addWidget(self.lbl_installed_status)

        self.installed_list = QListWidget()
        self.installed_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.installed_list.setStyleSheet(get_list_widget_qss("#38bdf8", "dark"))
        t0_layout.addWidget(self.installed_list)
        self.stacked_tabs.addWidget(self.tab_installed)

        # TAB 1: RUNNING NOW (Active GUI Processes)
        self.tab_running = QWidget()
        t1_layout = QVBoxLayout(self.tab_running)
        t1_layout.setContentsMargins(0, 4, 0, 0)
        t1_layout.setSpacing(4)

        self.lbl_running_status = QLabel("Active GUI applications currently running:")
        self.lbl_running_status.setStyleSheet("color: #94a3b8; font-size: 9px;")
        t1_layout.addWidget(self.lbl_running_status)

        self.running_list = QListWidget()
        self.running_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.running_list.setStyleSheet(get_list_widget_qss("#38bdf8", "dark"))
        t1_layout.addWidget(self.running_list)
        self.stacked_tabs.addWidget(self.tab_running)

        # TAB 2: BROWSE MANUALLY
        self.tab_browse = QWidget()
        t2_layout = QVBoxLayout(self.tab_browse)
        t2_layout.setContentsMargins(0, 4, 0, 0)
        t2_layout.setSpacing(6)

        form = QFormLayout()
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("App Name (e.g. Spotify)")

        path_box = QHBoxLayout()
        self.path_input = QLineEdit()
        self.path_input.setPlaceholderText("Target .exe Path...")

        browse_btn = QPushButton("Browse")
        browse_btn.setFixedHeight(22)
        browse_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        browse_btn.setStyleSheet("QPushButton { background: rgba(255, 255, 255, 0.1); color: white; border-radius: 4px; font-size: 9px; padding: 0 6px; }")
        browse_btn.clicked.connect(self.browse_path)

        path_box.addWidget(self.path_input, 1)
        path_box.addWidget(browse_btn)

        form.addRow("App Name:", self.name_input)
        form.addRow("Target Executable:", path_box)
        t2_layout.addLayout(form)
        t2_layout.addStretch()

        self.stacked_tabs.addWidget(self.tab_browse)
        layout.addWidget(self.stacked_tabs)

        # Bottom Dialog Actions
        btn_box = QHBoxLayout()
        self.add_confirm_btn = QPushButton("Add Shortcut")
        self.add_confirm_btn.setFixedHeight(24)
        self.add_confirm_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.add_confirm_btn.setStyleSheet("QPushButton { background-color: #38bdf8; color: #ffffff; font-weight: bold; border-radius: 4px; font-size: 10px; }")
        self.add_confirm_btn.clicked.connect(self.confirm_and_accept)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setFixedHeight(24)
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.setStyleSheet("QPushButton { background-color: rgba(255,255,255,0.08); color: #cbd5e1; border-radius: 4px; font-size: 10px; }")
        cancel_btn.clicked.connect(self.reject)

        btn_box.addStretch()
        btn_box.addWidget(cancel_btn)
        btn_box.addWidget(self.add_confirm_btn)
        layout.addLayout(btn_box)

        self.switch_tab(0)
        self.load_installed_apps()

    def load_installed_apps(self):
        global INSTALLED_APPS_CACHE
        if INSTALLED_APPS_CACHE is not None:
            self.populate_installed_apps(INSTALLED_APPS_CACHE)
            return

        self.lbl_installed_status.setText("⏳ Scanning Start Menu shortcuts...")
        self.lbl_installed_status.show()

        self.scan_thread = StartMenuScanThread(self)
        self.scan_thread.scanned_apps_ready.connect(self.on_installed_apps_scanned)
        self.scan_thread.start()

    def force_rescan_installed(self):
        global INSTALLED_APPS_CACHE
        INSTALLED_APPS_CACHE = None
        self.installed_list.clear()
        self.load_installed_apps()

    def on_installed_apps_scanned(self, apps: list):
        global INSTALLED_APPS_CACHE
        INSTALLED_APPS_CACHE = apps
        self.populate_installed_apps(apps)

    def populate_installed_apps(self, apps: list):
        self.installed_list.clear()
        self.lbl_installed_status.setText(f"Found {len(apps)} installed applications:")
        self.lbl_installed_status.show()

        for app in apps:
            w_item = QListWidgetItem(self.installed_list)
            w_item.setSizeHint(QSize(0, 38))

            row = QWidget()
            box = QHBoxLayout(row)
            box.setContentsMargins(6, 2, 6, 2)
            box.setSpacing(6)

            lbl_name = QLabel(f"📱  {app['name']}")
            lbl_name.setStyleSheet("color: #f8fafc; font-size: 10px; font-weight: 600; background: transparent;")

            btn_add = QPushButton("+ Add")
            btn_add.setFixedSize(45, 20)
            btn_add.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_add.setStyleSheet("QPushButton { background-color: #38bdf8; color: #ffffff; font-weight: bold; border-radius: 4px; font-size: 8.5px; }")
            btn_add.clicked.connect(lambda _, a=app: self.add_app_directly(a["name"], a["path"]))

            box.addWidget(lbl_name, 1)
            box.addWidget(btn_add)
            self.installed_list.setItemWidget(w_item, row)

    def filter_installed_apps(self, text: str):
        query = text.strip().lower()
        for i in range(self.installed_list.count()):
            item = self.installed_list.item(i)
            w = self.installed_list.itemWidget(item)
            if w:
                lbl = w.findChild(QLabel)
                if lbl:
                    show = (query in lbl.text().lower())
                    item.setHidden(not show)

    def load_running_apps(self):
        self.running_apps_loaded = True
        self.running_list.clear()

        visible_pids = set()
        try:
            import win32gui, win32process
            def enum_cb(hwnd, extra):
                if win32gui.IsWindowVisible(hwnd):
                    length = win32gui.GetWindowTextLength(hwnd)
                    if length > 0:
                        _, pid = win32process.GetWindowThreadProcessId(hwnd)
                        if pid:
                            visible_pids.add(pid)
                return True
            win32gui.EnumWindows(enum_cb, None)
        except Exception as e:
            print(f"EnumWindows error: {e}")

        running_apps = []
        known_paths = set()

        for pid in visible_pids:
            try:
                proc = psutil.Process(pid)
                exe = proc.exe()
                if exe and exe.lower().endswith(".exe") and os.path.exists(exe):
                    exe_lower = exe.lower()
                    if "explorer.exe" in exe_lower or "python" in exe_lower:
                        continue
                    if exe_lower not in known_paths:
                        known_paths.add(exe_lower)
                        proc_name = proc.name()
                        clean_name = os.path.splitext(proc_name)[0].replace("_", " ").replace("-", " ").capitalize()
                        running_apps.append({"name": clean_name, "path": exe})
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        running_apps.sort(key=lambda x: x["name"].lower())

        if not running_apps:
            item = QListWidgetItem(self.running_list)
            empty_w = make_empty_state("🏃", "No Visible Apps", "No active GUI application windows detected.", "dark")
            item.setSizeHint(empty_w.sizeHint())
            self.running_list.addItem(item)
            self.running_list.setItemWidget(item, empty_w)
            return

        for app in running_apps:
            w_item = QListWidgetItem(self.running_list)
            w_item.setSizeHint(QSize(0, 38))

            row = QWidget()
            box = QHBoxLayout(row)
            box.setContentsMargins(6, 2, 6, 2)
            box.setSpacing(6)

            lbl_name = QLabel(f"⚡  {app['name']}")
            lbl_name.setStyleSheet("color: #f8fafc; font-size: 10px; font-weight: 600; background: transparent;")

            btn_add = QPushButton("+ Add")
            btn_add.setFixedSize(45, 20)
            btn_add.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_add.setStyleSheet("QPushButton { background-color: #38bdf8; color: #ffffff; font-weight: bold; border-radius: 4px; font-size: 8.5px; }")
            btn_add.clicked.connect(lambda _, a=app: self.add_app_directly(a["name"], a["path"]))

            box.addWidget(lbl_name, 1)
            box.addWidget(btn_add)
            self.running_list.setItemWidget(w_item, row)

    def add_app_directly(self, name: str, path: str):
        self.selected_app_name = name
        self.selected_app_path = path
        self.accept()

    def confirm_and_accept(self):
        cur_idx = self.stacked_tabs.currentIndex()
        if cur_idx == 2:
            self.selected_app_name = self.name_input.text().strip()
            self.selected_app_path = self.path_input.text().strip()
        if self.selected_app_name and self.selected_app_path:
            self.accept()

    def browse_path(self):
        fp, _ = QFileDialog.getOpenFileName(self, "Select Application Executable", "", "Executables (*.exe *.lnk);;All Files (*.*)")
        if fp:
            self.path_input.setText(fp)
            if not self.name_input.text():
                base_name = os.path.splitext(os.path.basename(fp))[0]
                self.name_input.setText(base_name.capitalize())


class AppShortcutCard(GlassPanel):
    """App shortcut card with real Windows app logo, drag-and-drop reordering, hover shift controls, and right-click context menu."""
    def __init__(self, app_info: dict, index: int, total_count: int, accent: str, pal: dict, on_launch, on_remove, on_reorder, storage: StorageManager = None, parent=None):
        super().__init__(category_key="default", corner_radius=8, parent=parent)
        self.app_info = app_info
        self.index = index
        self.total_count = total_count
        self.on_launch = on_launch
        self.on_remove = on_remove
        self.on_reorder = on_reorder
        self.storage = storage
        self.setFixedSize(70, 52)
        self.setAcceptDrops(True)
        self.drag_start_pos = None

        self.btn = QPushButton(self)
        self.btn.setGeometry(0, 0, 70, 52)
        self.btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn.setStyleSheet(f"QPushButton {{ background: transparent; color: {pal['text_primary']}; font-size: 8.5px; font-weight: bold; border: none; text-align: center; padding: 2px; }}")

        # Resolve real app icon image
        icon_path = app_info.get("icon_path", "")
        cmd = app_info.get("command", "")
        app_id = app_info.get("id", "")

        if (not icon_path or not os.path.exists(icon_path)) and storage:
            icon_path = storage.extract_and_cache_app_icon(cmd, app_id)
            if icon_path:
                app_info["icon_path"] = icon_path

        app_name = app_info.get('name', 'App')
        self.btn.setToolTip(app_name)

        if icon_path and os.path.exists(icon_path):
            pix = QPixmap(icon_path)
            if not pix.isNull() and pix.width() > 0:
                self.btn.setIcon(QIcon(pix))
                self.btn.setIconSize(QSize(28, 28))
                self.btn.setText("")
            else:
                self.btn.setText(app_name)
        else:
            self.btn.setText(app_name)

        self.btn.clicked.connect(lambda: self.on_launch(cmd))

        # Context menu for right-click removal
        self.btn.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.btn.customContextMenuRequested.connect(self.show_context_menu)

        # Hover ✕ remove button
        self.btn_del = QPushButton("×", self)
        self.btn_del.setGeometry(52, 2, 16, 16)
        self.btn_del.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_del.setToolTip("Remove Shortcut")
        self.btn_del.setStyleSheet("QPushButton { background-color: rgba(239, 68, 68, 0.9); color: #ffffff; font-size: 11px; font-weight: bold; border-radius: 8px; border: none; padding-bottom: 2px; } QPushButton:hover { background-color: #dc2626; }")
        self.btn_del.clicked.connect(lambda: self.on_remove(app_info.get("id", "")))
        self.btn_del.hide()

        # Hover ◀ shift left button
        self.btn_left = QPushButton("◀", self)
        self.btn_left.setGeometry(2, 2, 14, 14)
        self.btn_left.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_left.setToolTip("Move Left")
        self.btn_left.setStyleSheet("QPushButton { background-color: rgba(15, 23, 42, 0.85); color: #cbd5e1; font-size: 8px; font-weight: bold; border-radius: 3px; border: 1px solid rgba(255, 255, 255, 0.15); padding: 0; } QPushButton:hover { background-color: #38bdf8; color: #ffffff; }")
        self.btn_left.clicked.connect(lambda: self.on_reorder(self.index, self.index - 1))
        self.btn_left.hide()

        # Hover ▶ shift right button
        self.btn_right = QPushButton("▶", self)
        self.btn_right.setGeometry(18, 2, 14, 14)
        self.btn_right.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_right.setToolTip("Move Right")
        self.btn_right.setStyleSheet("QPushButton { background-color: rgba(15, 23, 42, 0.85); color: #cbd5e1; font-size: 8px; font-weight: bold; border-radius: 3px; border: 1px solid rgba(255, 255, 255, 0.15); padding: 0; } QPushButton:hover { background-color: #38bdf8; color: #ffffff; }")
        self.btn_right.clicked.connect(lambda: self.on_reorder(self.index, self.index + 1))
        self.btn_right.hide()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_start_pos = event.pos()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.MouseButton.LeftButton) or not self.drag_start_pos:
            return
        if (event.pos() - self.drag_start_pos).manhattanLength() < QApplication.startDragDistance():
            return

        drag = QDrag(self)
        mime_data = QMimeData()
        mime_data.setText(f"app_idx:{self.index}")
        drag.setMimeData(mime_data)

        pix = self.grab()
        drag.setPixmap(pix)
        drag.setHotSpot(event.pos())
        drag.exec(Qt.DropAction.MoveAction)

    def dragEnterEvent(self, event):
        if event.mimeData().hasText() and event.mimeData().text().startswith("app_idx:"):
            event.acceptProposedAction()
            self.is_hovered = True
            self.update()
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        self.is_hovered = False
        self.update()
        super().dragLeaveEvent(event)

    def dropEvent(self, event):
        self.is_hovered = False
        self.update()
        if event.mimeData().hasText() and event.mimeData().text().startswith("app_idx:"):
            try:
                src_idx = int(event.mimeData().text().split(":")[1])
                if src_idx != self.index:
                    self.on_reorder(src_idx, self.index)
                    event.acceptProposedAction()
                    return
            except Exception:
                pass
        event.ignore()

    def enterEvent(self, event):
        self.btn_del.show()
        if self.index > 0:
            self.btn_left.show()
        if self.index < self.total_count - 1:
            self.btn_right.show()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.btn_del.hide()
        self.btn_left.hide()
        self.btn_right.hide()
        super().leaveEvent(event)

    def show_context_menu(self, pos):
        menu = QMenu(self)
        menu.setStyleSheet("QMenu { background-color: #1e293b; color: #f8fafc; border: 1px solid #334155; border-radius: 6px; padding: 4px; } QMenu::item { padding: 4px 14px; border-radius: 4px; font-size: 9.5px; } QMenu::item:selected { background-color: #ef4444; color: #ffffff; }")
        del_action = menu.addAction("🗑️ Remove Shortcut")
        action = menu.exec(self.btn.mapToGlobal(pos))
        if action == del_action:
            self.on_remove(self.app_info.get("id", ""))


class AppLauncherTabWidget(QWidget):
    def __init__(self, storage: StorageManager, settings: SettingsManager = None, parent=None):
        super().__init__(parent)
        self.storage = storage
        self.settings = settings
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        accent = resolve_accent_color(self.settings) if self.settings else "#38bdf8"
        mode = self.settings.get("theme_mode", "dark") if self.settings else "dark"

        head_box = QHBoxLayout()
        self.lbl_head = QLabel("🚀 APP LAUNCHER GRID")
        self.lbl_head.setStyleSheet(f"color: {accent}; font-size: 10px; font-weight: 800; letter-spacing: 0.5px; background: transparent;")

        self.add_app_btn = QPushButton("+ Add Custom App")
        self.add_app_btn.setFixedHeight(20)
        self.add_app_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.add_app_btn.setStyleSheet(f"QPushButton {{ background-color: {accent}; color: #ffffff; border: none; border-radius: 4px; font-size: 9px; font-weight: bold; padding: 0 6px; }}")
        self.add_app_btn.clicked.connect(self.show_add_app_dialog)

        head_box.addWidget(self.lbl_head)
        head_box.addStretch()
        head_box.addWidget(self.add_app_btn)
        layout.addLayout(head_box)

        scroll = QScrollArea()
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"QScrollArea, QScrollArea > QWidget > QWidget {{ border: none; background: transparent; }} {get_scrollbar_qss(accent, mode)}")
        if scroll.viewport():
            scroll.viewport().setStyleSheet("background: transparent;")
        self.app_scroll_filter = SmoothScrollFilter(scroll, step_size=40, duration=200)

        self.grid_widget = QWidget()
        self.grid_widget.setStyleSheet("background: transparent;")
        self.grid_layout = QGridLayout(self.grid_widget)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        self.grid_layout.setSpacing(6)

        scroll.setWidget(self.grid_widget)
        layout.addWidget(scroll)

        self.render_app_grid()

    def apply_theme(self, accent_color: str, mode: str = "dark"):
        self.current_accent = accent_color
        self.current_mode = mode
        self.lbl_head.setStyleSheet(f"color: {accent_color}; font-size: 10px; font-weight: 800; letter-spacing: 0.5px; background: transparent;")
        self.add_app_btn.setStyleSheet(f"QPushButton {{ background-color: {accent_color}; color: #ffffff; border: none; border-radius: 4px; font-size: 9px; font-weight: bold; padding: 0 6px; }}")
        pal = THEME_PALETTES.get(mode, THEME_PALETTES["dark"])
        for card in self.findChildren(AppShortcutCard):
            card.apply_theme(accent_color, mode)
            card.btn.setStyleSheet(f"QPushButton {{ background: transparent; color: {pal['text_primary']}; font-size: 8.5px; font-weight: bold; border: none; text-align: center; padding: 2px; }}")

    def reorder_apps(self, from_idx: int, to_idx: int):
        apps = self.storage.load_app_launcher()
        if 0 <= from_idx < len(apps) and 0 <= to_idx < len(apps) and from_idx != to_idx:
            item = apps.pop(from_idx)
            apps.insert(to_idx, item)
            self.storage.save_app_launcher(apps)
            self.render_app_grid(getattr(self, 'current_accent', None), getattr(self, 'current_mode', None))

    def render_app_grid(self, accent_color: str = None, mode: str = None):
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)
                w.deleteLater()

        accent = accent_color or (resolve_accent_color(self.settings) if self.settings else "#38bdf8")
        cur_mode = mode or (self.settings.get("theme_mode", "dark") if self.settings else "dark")
        pal = THEME_PALETTES.get(cur_mode, THEME_PALETTES["dark"])

        apps = self.storage.load_app_launcher()
        cols = 4
        for idx, app_info in enumerate(apps):
            r = idx // cols
            c = idx % cols

            card = AppShortcutCard(
                app_info=app_info,
                index=idx,
                total_count=len(apps),
                accent=accent,
                pal=pal,
                on_launch=self.launch_app,
                on_remove=self.remove_app,
                on_reorder=self.reorder_apps,
                storage=self.storage
            )
            card.apply_theme(accent, cur_mode)
            self.grid_layout.addWidget(card, r, c)

    def remove_app(self, app_id: str):
        if app_id:
            self.storage.remove_app_launcher_shortcut(app_id)
            self.render_app_grid()

    def launch_app(self, command: str):
        if command:
            try:
                subprocess.Popen(command, shell=True)
            except Exception as e:
                print(f"Failed to launch app ({command}): {e}")

    def show_add_app_dialog(self):
        dlg = AddAppDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            name = dlg.selected_app_name
            path = dlg.selected_app_path
            icon = getattr(dlg, 'selected_app_icon', '🚀')
            if name and path:
                self.storage.add_app_launcher_shortcut(name, path, icon)
                self.render_app_grid()


# 8. MULTI-NOTE MANAGER TAB WIDGET (WITH USER-SELECTABLE HOME PINNING TOGGLE - Req 1)
class QuickNotesTabWidget(QWidget):
    def __init__(self, storage: StorageManager, settings: SettingsManager = None, parent=None):
        super().__init__(parent)
        self.storage = storage
        self.settings = settings
        self.current_note_id = None
        self.auto_save_timer = QTimer(self)
        self.auto_save_timer.setSingleShot(True)
        self.auto_save_timer.setInterval(400)
        self.auto_save_timer.timeout.connect(self.save_current_note_content)

        self.init_ui()

        # Real-time note sync connection
        self.storage.note_content_changed.connect(self.on_storage_note_changed)
        self.storage.note_deleted_externally.connect(self.on_note_deleted_externally)
        self.storage.notes_index_changed.connect(self.load_notes_list)

    def on_note_deleted_externally(self, note_id: str, filename: str):
        if self.current_note_id == note_id:
            self.note_editor.blockSignals(True)
            self.note_title_input.blockSignals(True)
            self.note_editor.setPlainText("[This note was deleted externally in File Explorer]")
            self.note_title_input.setText("Note Deleted Externally")
            self.note_editor.blockSignals(False)
            self.note_title_input.blockSignals(False)
            self.current_note_id = None

        self.load_notes_list()

    def on_storage_note_changed(self, note_id: str, content: str):
        if self.current_note_id == note_id:
            if hasattr(self, 'note_editor') and not self.note_editor.hasFocus():
                if self.note_editor.toPlainText() != content:
                    cursor = self.note_editor.textCursor()
                    pos = cursor.position()
                    self.note_editor.blockSignals(True)
                    self.note_editor.setPlainText(content)
                    cursor.setPosition(min(pos, len(content)))
                    self.note_editor.setTextCursor(cursor)
                    self.note_editor.blockSignals(False)

    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        accent = resolve_accent_color(self.settings) if self.settings else "#38bdf8"
        mode = self.settings.get("theme_mode", "dark") if self.settings else "dark"
        pal = THEME_PALETTES.get(mode, THEME_PALETTES["dark"])

        left_card = GlassPanel(category_key="notes", corner_radius=10)
        left_panel = QVBoxLayout(left_card)
        left_panel.setContentsMargins(8, 6, 8, 6)
        left_panel.setSpacing(4)

        head_box = QHBoxLayout()
        self.lbl_head = QLabel("📝 NOTES")
        self.lbl_head.setStyleSheet(f"color: {accent}; font-size: 10px; font-weight: 800; background: transparent;")

        self.new_btn = QPushButton("+ New")
        self.new_btn.setFixedHeight(20)
        self.new_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.new_btn.setStyleSheet(f"QPushButton {{ background-color: {accent}; color: #ffffff; border: none; border-radius: 4px; font-size: 9px; font-weight: bold; padding: 0 6px; }}")
        self.new_btn.clicked.connect(self.on_create_new_note)

        head_box.addWidget(self.lbl_head)
        head_box.addStretch()
        head_box.addWidget(self.new_btn)
        left_panel.addLayout(head_box)

        self.note_list = QListWidget()
        self.note_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.note_list.setStyleSheet(get_list_widget_qss(accent, mode))
        self.notes_scroll_filter = SmoothScrollFilter(self.note_list, step_size=36, duration=200)
        self.note_list.itemClicked.connect(self.on_note_selected)
        left_panel.addWidget(self.note_list)

        layout.addWidget(left_card, 2)

        right_card = GlassPanel(category_key="notes", corner_radius=10)
        right_panel = QVBoxLayout(right_card)
        right_panel.setContentsMargins(8, 6, 8, 6)
        right_panel.setSpacing(4)

        editor_head = QHBoxLayout()
        self.note_title_input = QLineEdit()
        self.note_title_input.setFixedHeight(24)
        self.note_title_input.setStyleSheet(f"QLineEdit {{ background: {pal['input_bg']}; border: 1px solid {pal['input_border']}; border-radius: 5px; color: {pal['text_primary']}; font-weight: bold; padding: 2px 6px; font-size: 10px; }} QLineEdit:hover {{ border: 1px solid {accent}; }}")
        self.note_title_input.editingFinished.connect(self.on_title_edited)

        # Added Pin to Home Button (Req 1)
        self.home_pin_btn = QPushButton("📍 Home")
        self.home_pin_btn.setFixedHeight(24)
        self.home_pin_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.home_pin_btn.setStyleSheet(f"QPushButton {{ background-color: {pal['sub_btn_bg']}; color: {pal['text_primary']}; border-radius: 5px; font-size: 9.5px; padding: 0 6px; }}")
        self.home_pin_btn.clicked.connect(self.on_toggle_home_pin)

        self.pin_btn = QPushButton("📌 Pin")
        self.pin_btn.setFixedHeight(24)
        self.pin_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.pin_btn.setStyleSheet(f"QPushButton {{ background-color: {pal['sub_btn_bg']}; color: {pal['text_primary']}; border-radius: 5px; font-size: 9.5px; padding: 0 6px; }}")
        self.pin_btn.clicked.connect(self.on_toggle_pin)

        self.copy_note_btn = QPushButton("📋 Copy")
        self.copy_note_btn.setFixedHeight(24)
        self.copy_note_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.copy_note_btn.setStyleSheet(f"QPushButton {{ background-color: {pal['sub_btn_bg']}; color: {pal['text_primary']}; border-radius: 5px; font-size: 9.5px; padding: 0 6px; }}")
        self.copy_note_btn.clicked.connect(lambda: flash_copy_feedback(self.copy_note_btn, self.note_editor.toPlainText()))

        self.del_note_btn = QPushButton("🗑️")
        self.del_note_btn.setFixedSize(24, 24)
        self.del_note_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.del_note_btn.setStyleSheet("QPushButton { background-color: rgba(239, 68, 68, 0.2); color: #ef4444; border-radius: 5px; font-size: 9.5px; }")
        self.del_note_btn.clicked.connect(self.on_delete_note)

        editor_head.addWidget(self.note_title_input, 1)
        editor_head.addWidget(self.copy_note_btn)
        editor_head.addWidget(self.home_pin_btn)
        editor_head.addWidget(self.pin_btn)
        editor_head.addWidget(self.del_note_btn)
        right_panel.addLayout(editor_head)

        self.note_editor = QTextEdit()
        self.note_editor.setPlaceholderText("Start typing your note content here...")
        self.note_editor.setStyleSheet(f"QTextEdit {{ background: {pal['input_bg']}; border: 1px solid {pal['input_border']}; border-radius: 6px; color: {pal['text_primary']}; font-size: 10.5px; padding: 6px; }} {get_scrollbar_qss(accent, mode)}")
        self.note_editor.textChanged.connect(self.on_editor_text_changed)

        right_panel.addWidget(self.note_editor)
        layout.addWidget(right_card, 3)

        self.load_notes_list()

    def apply_theme(self, accent_color: str, mode: str = "dark"):
        pal = THEME_PALETTES.get(mode, THEME_PALETTES["dark"])
        for gp in self.findChildren(GlassPanel):
            gp.apply_theme(accent_color, mode)

        self.lbl_head.setStyleSheet(f"color: {accent_color}; font-size: 10px; font-weight: 800; background: transparent;")
        self.new_btn.setStyleSheet(f"QPushButton {{ background-color: {accent_color}; color: #ffffff; border: none; border-radius: 4px; font-size: 9px; font-weight: bold; padding: 0 6px; }}")
        self.note_title_input.setStyleSheet(f"QLineEdit {{ background: {pal['input_bg']}; border: 1px solid {pal['input_border']}; border-radius: 5px; color: {pal['text_primary']}; font-weight: bold; padding: 2px 6px; font-size: 10px; }} QLineEdit:hover {{ border: 1px solid {accent_color}; }}")
        self.note_list.setStyleSheet(get_list_widget_qss(accent_color, mode))
        self.note_editor.setStyleSheet(f"QTextEdit {{ background: {pal['input_bg']}; border: 1px solid {pal['input_border']}; border-radius: 6px; color: {pal['text_primary']}; font-size: 10.5px; padding: 6px; }} {get_scrollbar_qss(accent_color, mode)}")
        if not self.note_editor.hasFocus() and not self.note_title_input.hasFocus():
            self.load_notes_list()

    def load_notes_list(self):
        self.note_list.clear()
        index = self.storage.load_notes_index()

        if index:
            for item in index:
                title = item.get("title", "Untitled")
                pin_mark = "📌 " if item.get("is_pinned", False) else ""
                home_mark = "📍 " if item.get("is_pinned_home", False) else ""
                w_item = QListWidgetItem(f"{pin_mark}{home_mark}{title}")
                w_item.setSizeHint(QSize(0, 42))
                w_item.setData(Qt.ItemDataRole.UserRole, item.get("id"))
                self.note_list.addItem(w_item)

            if not self.current_note_id:
                pinned = self.storage.get_pinned_note()
                self.current_note_id = pinned.get("id") if pinned else index[0].get("id")

            for i in range(self.note_list.count()):
                it = self.note_list.item(i)
                if it.data(Qt.ItemDataRole.UserRole) == self.current_note_id:
                    self.note_list.setCurrentItem(it)
                    break

            if not self.note_editor.hasFocus() and not self.note_title_input.hasFocus():
                self.load_note_to_editor(self.current_note_id)

    def load_note_to_editor(self, note_id: str):
        index = self.storage.load_notes_index()
        note = next((n for n in index if n.get("id") == note_id), None)
        if note:
            self.current_note_id = note_id
            self.note_title_input.blockSignals(True)
            self.note_editor.blockSignals(True)

            self.note_title_input.setText(note.get("title", ""))
            content = self.storage.load_note_content(note.get("filename", ""))
            self.note_editor.setPlainText(content)

            self.update_pin_btn_style(note.get("is_pinned", False), note.get("is_pinned_home", False))

            self.note_title_input.blockSignals(False)
            self.note_editor.blockSignals(False)

    def update_pin_btn_style(self, is_pinned: bool, is_pinned_home: bool):
        accent = resolve_accent_color(self.settings) if self.settings else "#38bdf8"
        mode = self.settings.get("theme_mode", "dark") if self.settings else "dark"
        pal = THEME_PALETTES.get(mode, THEME_PALETTES["dark"])

        if is_pinned:
            self.pin_btn.setStyleSheet(f"QPushButton {{ background-color: {accent}; color: #ffffff; font-weight: bold; border-radius: 5px; font-size: 9.5px; padding: 0 6px; }}")
        else:
            self.pin_btn.setStyleSheet(f"QPushButton {{ background-color: {pal['sub_btn_bg']}; color: {pal['text_primary']}; border-radius: 5px; font-size: 9.5px; padding: 0 6px; }}")

        if is_pinned_home:
            self.home_pin_btn.setStyleSheet(f"QPushButton {{ background-color: {accent}; color: #ffffff; font-weight: bold; border-radius: 5px; font-size: 9.5px; padding: 0 6px; }}")
        else:
            self.home_pin_btn.setStyleSheet(f"QPushButton {{ background-color: {pal['sub_btn_bg']}; color: {pal['text_primary']}; border-radius: 5px; font-size: 9.5px; padding: 0 6px; }}")

    def on_note_selected(self, item: QListWidgetItem):
        note_id = item.data(Qt.ItemDataRole.UserRole)
        if note_id and note_id != self.current_note_id:
            self.save_current_note_content()
            self.load_note_to_editor(note_id)

    def on_editor_text_changed(self):
        self.auto_save_timer.start(400)

    def save_current_note_content(self):
        if self.current_note_id:
            index = self.storage.load_notes_index()
            note = next((n for n in index if n.get("id") == self.current_note_id), None)
            if note:
                text = self.note_editor.toPlainText()
                self.storage.save_note_content(note.get("filename", ""), text)
                self.storage.note_content_changed.emit(self.current_note_id, text)

    def on_title_edited(self):
        if self.current_note_id:
            new_title = self.note_title_input.text().strip() or "Untitled Note"
            self.storage.rename_note(self.current_note_id, new_title)
            for i in range(self.note_list.count()):
                it = self.note_list.item(i)
                if it.data(Qt.ItemDataRole.UserRole) == self.current_note_id:
                    index = self.storage.load_notes_index()
                    note = next((n for n in index if n.get("id") == self.current_note_id), None)
                    if note:
                        pin_mark = "📌 " if note.get("is_pinned", False) else ""
                        home_mark = "📍 " if note.get("is_pinned_home", False) else ""
                        it.setText(f"{pin_mark}{home_mark}{new_title}")
                    break

    def on_create_new_note(self):
        self.save_current_note_content()
        new_note = self.storage.create_note("New Note")
        self.current_note_id = new_note.get("id")
        self.load_notes_list()

    def on_delete_note(self):
        if self.current_note_id:
            self.storage.delete_note(self.current_note_id)
            self.current_note_id = None
            self.load_notes_list()

    def on_toggle_pin(self):
        if self.current_note_id:
            index = self.storage.load_notes_index()
            for n in index:
                n["is_pinned"] = (n.get("id") == self.current_note_id)
            self.storage.save_notes_index(index)
            self.load_notes_list()

    def on_toggle_home_pin(self):
        if self.current_note_id:
            self.storage.toggle_home_pin(self.current_note_id)
            self.load_notes_list()


# 9. SETTINGS TAB WIDGET
class SettingsTabWidget(QWidget):
    open_full_window_requested = pyqtSignal()

    def __init__(self, settings: SettingsManager, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.current_accent_identity = self.settings.get("accent_identity", "sky_blue")
        self.form_labels = []

        # Fluid 60fps slider drag preview timer (throttles heavy window repaints to ~25fps)
        self.preview_timer = QTimer(self)
        self.preview_timer.setSingleShot(True)
        self.preview_timer.timeout.connect(self.commit_live_preview_settings)
        self.pending_opacity = None
        self.pending_radius = None

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(8)

        accent = resolve_accent_color(self.settings)
        mode = self.settings.get("theme_mode", "dark")
        pal = THEME_PALETTES.get(mode, THEME_PALETTES["dark"])

        self.lbl_head = QLabel("⚙️ DLIVES PREFERENCES")
        self.lbl_head.setStyleSheet(f"color: {accent}; font-size: 10px; font-weight: 800; letter-spacing: 0.5px; background: transparent;")
        layout.addWidget(self.lbl_head)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setStyleSheet(f"QScrollArea, QScrollArea > QWidget > QWidget {{ border: none; background: transparent; }} {get_scrollbar_qss(accent, mode)}")
        if self.scroll.viewport():
            self.scroll.viewport().setStyleSheet("background: transparent;")

        # Comfortably fast, smooth 60px scroll step size for Settings panel
        self.settings_scroll_filter = SmoothScrollFilter(self.scroll, step_size=60, duration=90)

        scroll_widget = GlassPanel(category_key="settings", corner_radius=10)
        form_layout = QVBoxLayout(scroll_widget)
        form_layout.setContentsMargins(8, 8, 22, 8)
        form_layout.setSpacing(8)

        # Standalone Full App Workspace Launch Card
        self.full_card = GlassPanel(category_key="settings", corner_radius=8)
        fc_layout = QHBoxLayout(self.full_card)
        fc_layout.setContentsMargins(10, 8, 10, 8)
        fc_layout.setSpacing(8)

        fc_info = QVBoxLayout()
        fc_info.setSpacing(2)
        self.lbl_fc_title = QLabel("🖥️ FULL APP WORKSPACE STUDIO")
        self.lbl_fc_title.setStyleSheet(f"color: {accent}; font-size: 11px; font-weight: 800; background: transparent;")
        self.lbl_fc_desc = QLabel("Open the resizable desktop window with multi-pane modules and Tab Manager.")
        self.lbl_fc_desc.setStyleSheet(f"color: {pal['text_secondary']}; font-size: 9.5px; font-weight: 500; background: transparent;")
        fc_info.addWidget(self.lbl_fc_title)
        fc_info.addWidget(self.lbl_fc_desc)

        self.btn_launch_full = QPushButton("Launch Full Window \u2197")
        self.btn_launch_full.setFixedHeight(26)
        self.btn_launch_full.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_launch_full.setStyleSheet(f"QPushButton {{ background-color: {accent}; color: #ffffff; border: none; border-radius: 5px; font-size: 10.5px; font-weight: bold; padding: 0 12px; }} QPushButton:hover {{ opacity: 0.85; }}")
        self.btn_launch_full.clicked.connect(self.trigger_open_full_window)

        fc_layout.addLayout(fc_info, 1)
        fc_layout.addWidget(self.btn_launch_full)
        form_layout.addWidget(self.full_card)

        form = QFormLayout()
        form.setVerticalSpacing(12)
        form.setHorizontalSpacing(14)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        def make_form_lbl(txt: str) -> QLabel:
            l = QLabel(txt)
            l.setMinimumWidth(130)
            l.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            l.setStyleSheet(f"color: {pal['text_primary']}; font-size: 10px; font-weight: 700; background: transparent;")
            self.form_labels.append(l)
            return l

        # Row 0: Theme Mode Switch (🌙 Dark / ☀️ Light)
        theme_row = QHBoxLayout()
        theme_row.setSpacing(6)

        self.btn_theme_dark = QPushButton("\U0001F319 Dark Mode")
        self.btn_theme_light = QPushButton("\u2600\ufe0f Light Mode")

        for btn in (self.btn_theme_dark, self.btn_theme_light):
            btn.setFixedHeight(22)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)

        self.btn_theme_dark.clicked.connect(lambda: self.switch_theme_mode("dark"))
        self.btn_theme_light.clicked.connect(lambda: self.switch_theme_mode("light"))

        theme_row.addWidget(self.btn_theme_dark)
        theme_row.addWidget(self.btn_theme_light)
        theme_row.addStretch()

        form.addRow(make_form_lbl("Theme Mode:"), theme_row)

        # Row 1: Accent Color Presets
        color_grid = QHBoxLayout()
        color_grid.setSpacing(4)
        for identity, data in ACCENT_PALETTES.items():
            btn = QPushButton()
            btn.setFixedSize(16, 16)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            hex_show = data.get(mode, data["dark"])
            btn.setStyleSheet(f"background-color: {hex_show}; border-radius: 8px; border: 1px solid {pal['card_border']};")
            btn.clicked.connect(lambda _, ident=identity: self.select_accent_identity(ident))
            color_grid.addWidget(btn)

        cur_data = ACCENT_PALETTES.get(self.current_accent_identity, ACCENT_PALETTES["sky_blue"])
        self.color_name_lbl = QLabel(cur_data["name"])
        self.color_name_lbl.setStyleSheet(f"color: {pal['text_secondary']}; font-size: 9.5px; font-weight: 600; background: transparent;")
        color_grid.addWidget(self.color_name_lbl)
        color_grid.addStretch()

        form.addRow(make_form_lbl("Accent Color:"), color_grid)

        # Row 2: Island Position
        self.pos_combo = NoWheelComboBox()
        self.pos_combo.addItems(["Top Center", "Top Left", "Top Right", "Bottom Center"])
        pos_curr = self.settings.get("position", "top_center")
        pos_idx_map = {"top_center": 0, "top_left": 1, "top_right": 2, "bottom_center": 3}
        self.pos_combo.setCurrentIndex(pos_idx_map.get(pos_curr, 0))
        self.pos_combo.setFixedSize(110, 24)
        self.pos_combo.setStyleSheet(get_combobox_qss(accent, mode))
        self.pos_combo.activated.connect(self.on_position_combo_activated)

        form.addRow(make_form_lbl("Position:"), self.pos_combo)

        # Row 3: Background Opacity Slider
        opacity_row = QHBoxLayout()
        opacity_row.setSpacing(6)

        self.opacity_slider = NoWheelSlider(Qt.Orientation.Horizontal)
        self.opacity_slider.setRange(10, 100)
        curr_op = int(self.settings.get("bg_opacity", 0.90) * 100)
        self.opacity_slider.setValue(curr_op)
        self.opacity_slider.setStyleSheet(get_slider_qss(accent, mode))
        self.opacity_slider.valueChanged.connect(self.on_opacity_slider_changed)
        self.opacity_slider.sliderReleased.connect(self.on_slider_released)

        self.opacity_lbl = QLabel(f"{curr_op}%")
        self.opacity_lbl.setMinimumWidth(38)
        self.opacity_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.opacity_lbl.setStyleSheet(f"color: {accent}; background: {pal['input_bg']}; border: 1px solid {pal['input_border']}; border-radius: 5px; padding: 2px 4px; font-size: 10px; font-weight: bold;")
        opacity_row.addWidget(self.opacity_slider)
        opacity_row.addWidget(self.opacity_lbl)

        form.addRow(make_form_lbl("Glass Opacity:"), opacity_row)

        # Row 4: Corner Radius Slider (High resolution 40-300 range for smooth gliding)
        radius_row = QHBoxLayout()
        radius_row.setSpacing(6)

        self.radius_slider = NoWheelSlider(Qt.Orientation.Horizontal)
        self.radius_slider.setRange(40, 300)
        curr_rad = self.settings.get("corner_radius", 20)
        self.radius_slider.setValue(curr_rad * 10)
        self.radius_slider.setStyleSheet(get_slider_qss(accent, mode))
        self.radius_slider.valueChanged.connect(self.on_radius_slider_changed)
        self.radius_slider.sliderReleased.connect(self.on_slider_released)

        self.radius_lbl = QLabel(f"{curr_rad}px")
        self.radius_lbl.setMinimumWidth(38)
        self.radius_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.radius_lbl.setStyleSheet(f"color: {accent}; background: {pal['input_bg']}; border: 1px solid {pal['input_border']}; border-radius: 5px; padding: 2px 4px; font-size: 10px; font-weight: bold;")
        radius_row.addWidget(self.radius_slider)
        radius_row.addWidget(self.radius_lbl)

        form.addRow(make_form_lbl("Corner Radius:"), radius_row)

        # Row 5: Watermark Opacity Slider
        wm_op_row = QHBoxLayout()
        wm_op_row.setSpacing(6)

        self.wm_opacity_slider = NoWheelSlider(Qt.Orientation.Horizontal)
        self.wm_opacity_slider.setRange(1, 25)
        curr_wm_op = int(self.settings.get("watermark_opacity", 0.04) * 100)
        self.wm_opacity_slider.setValue(max(1, min(25, curr_wm_op)))
        self.wm_opacity_slider.setStyleSheet(get_slider_qss(accent, mode))
        self.wm_opacity_slider.valueChanged.connect(self.on_wm_opacity_slider_changed)

        self.wm_opacity_lbl = QLabel(f"{curr_wm_op}%")
        self.wm_opacity_lbl.setMinimumWidth(38)
        self.wm_opacity_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.wm_opacity_lbl.setStyleSheet(f"color: {accent}; background: {pal['input_bg']}; border: 1px solid {pal['input_border']}; border-radius: 5px; padding: 2px 4px; font-size: 10px; font-weight: bold;")
        wm_op_row.addWidget(self.wm_opacity_slider)
        wm_op_row.addWidget(self.wm_opacity_lbl)

        form.addRow(make_form_lbl("Watermark Opacity:"), wm_op_row)

        form_layout.addLayout(form)
        self.scroll.setWidget(scroll_widget)
        layout.addWidget(self.scroll)

        self.save_btn = QPushButton("💾 Apply & Save Settings")
        self.save_btn.setFixedHeight(24)
        self.save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.save_btn.setStyleSheet(f"QPushButton {{ background-color: {accent}; color: #ffffff; font-weight: bold; border-radius: 4px; font-size: 10px; border: none; }}")
        self.save_btn.clicked.connect(self.apply_settings)
        layout.addWidget(self.save_btn)

        self.update_theme_switch_buttons(mode)

    def browse_custom_logo(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select App Logo Image", "", "Images (*.png *.jpg *.jpeg *.ico *.svg)"
        )
        if file_path:
            self.settings.set("custom_logo_path", file_path)
            self.logo_path_edit.setText(file_path)

    def reset_custom_logo(self):
        self.settings.set("custom_logo_path", "")
        self.logo_path_edit.setText("Default Built-in 3D Glass Logo")

    def browse_custom_watermark(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Background Watermark Image", "", "Images (*.png *.jpg *.jpeg *.ico *.svg)"
        )
        if file_path:
            self.settings.set("custom_watermark_path", file_path)
            self.watermark_path_edit.setText(file_path)

    def reset_custom_watermark(self):
        self.settings.set("custom_watermark_path", "")
        self.watermark_path_edit.setText("Default Transparent Watermark")

    def switch_theme_mode(self, mode: str):
        accent = resolve_accent_color(self.settings)
        self.settings.update_settings({"theme_mode": mode, "accent_color": accent})

    def update_theme_switch_buttons(self, mode: str):
        accent = resolve_accent_color(self.settings)
        pal = THEME_PALETTES.get(mode, THEME_PALETTES["dark"])
        if mode == "dark":
            self.btn_theme_dark.setStyleSheet(f"QPushButton {{ background-color: {accent}; color: #ffffff; font-weight: bold; border-radius: 4px; border: none; font-size: 9.5px; }}")
            self.btn_theme_light.setStyleSheet(f"QPushButton {{ background-color: {pal['sub_btn_bg']}; color: {pal['sub_btn_text']}; border-radius: 4px; border: 1px solid {pal['sub_btn_border']}; font-size: 9.5px; }}")
        else:
            self.btn_theme_light.setStyleSheet(f"QPushButton {{ background-color: {accent}; color: #ffffff; font-weight: bold; border-radius: 4px; border: none; font-size: 9.5px; }}")
            self.btn_theme_dark.setStyleSheet(f"QPushButton {{ background-color: {pal['sub_btn_bg']}; color: {pal['sub_btn_text']}; border-radius: 4px; border: 1px solid {pal['sub_btn_border']}; font-size: 9.5px; }}")

    def apply_theme(self, accent_color: str, mode: str = "dark"):
        pal = THEME_PALETTES.get(mode, THEME_PALETTES["dark"])
        for gp in self.findChildren(GlassPanel):
            gp.apply_theme(accent_color, mode)

        if hasattr(self, 'lbl_fc_title'):
            self.lbl_fc_title.setStyleSheet(f"color: {accent_color}; font-size: 11px; font-weight: 800; background: transparent;")
        if hasattr(self, 'lbl_fc_desc'):
            self.lbl_fc_desc.setStyleSheet(f"color: {pal['text_secondary']}; font-size: 9.5px; font-weight: 500; background: transparent;")
        if hasattr(self, 'btn_launch_full'):
            self.btn_launch_full.setStyleSheet(f"QPushButton {{ background-color: {accent_color}; color: #ffffff; border: none; border-radius: 5px; font-size: 10.5px; font-weight: bold; padding: 0 12px; }} QPushButton:hover {{ opacity: 0.85; }}")

        for lbl in self.form_labels:
            lbl.setStyleSheet(f"color: {pal['text_primary']}; font-size: 10px; font-weight: 700; background: transparent;")

        self.lbl_head.setStyleSheet(f"color: {accent_color}; font-size: 10px; font-weight: 800; letter-spacing: 0.5px; background: transparent;")
        self.color_name_lbl.setStyleSheet(f"color: {pal['text_secondary']}; font-size: 9.5px; font-weight: 600; background: transparent;")
        self.opacity_lbl.setStyleSheet(f"color: {pal['text_primary']}; font-size: 10px; font-weight: 700; background: transparent;")
        self.radius_lbl.setStyleSheet(f"color: {pal['text_primary']}; font-size: 10px; font-weight: 700; background: transparent;")
        if hasattr(self, 'wm_opacity_lbl'):
            self.wm_opacity_lbl.setStyleSheet(f"color: {accent_color}; background: {pal['input_bg']}; border: 1px solid {pal['input_border']}; border-radius: 5px; padding: 2px 6px; font-size: 10px; font-weight: bold;")
        self.save_btn.setStyleSheet(f"QPushButton {{ background-color: {accent_color}; color: #ffffff; font-weight: bold; border-radius: 4px; font-size: 10px; border: none; }}")
        self.pos_combo.setStyleSheet(get_combobox_qss(accent_color, mode))

        slider_qss = f"QSlider::groove:horizontal {{ background: {pal['input_bg']}; height: 6px; border-radius: 3px; }} QSlider::sub-page:horizontal {{ background: {accent_color}; border-radius: 3px; }} QSlider::handle:horizontal {{ background: {pal['text_primary']}; width: 14px; margin-top: -4px; margin-bottom: -4px; border-radius: 7px; }}"
        self.opacity_slider.setStyleSheet(slider_qss)
        self.radius_slider.setStyleSheet(slider_qss)
        if hasattr(self, 'wm_opacity_slider'):
            self.wm_opacity_slider.setStyleSheet(slider_qss)

        self.update_theme_switch_buttons(mode)

    def on_opacity_slider_changed(self, value: int):
        self.opacity_lbl.setText(f"{value}%")
        self.pending_opacity = value / 100.0
        self.preview_timer.start(40)

    def on_radius_slider_changed(self, value: int):
        rad_px = int(round(value / 10.0))
        self.radius_lbl.setText(f"{rad_px}px")
        self.pending_radius = rad_px
        self.preview_timer.start(40)

    def on_wm_opacity_slider_changed(self, value: int):
        self.wm_opacity_lbl.setText(f"{value}%")
        self.settings.set("watermark_opacity", value / 100.0)

    def on_slider_released(self):
        self.commit_live_preview_settings()

    def commit_live_preview_settings(self):
        updates = {}
        if self.pending_opacity is not None:
            updates["bg_opacity"] = self.pending_opacity
            self.pending_opacity = None
        if self.pending_radius is not None:
            updates["corner_radius"] = self.pending_radius
            self.pending_radius = None
        if updates:
            self.settings.update_settings(updates)

    def select_accent_identity(self, identity: str):
        self.current_accent_identity = identity
        cur_data = ACCENT_PALETTES.get(identity, ACCENT_PALETTES["sky_blue"])
        mode = self.settings.get("theme_mode", "dark")
        self.color_name_lbl.setText(cur_data["name"])

        resolved_hex = cur_data.get(mode, cur_data["dark"])
        self.settings.update_settings({"accent_identity": identity, "accent_color": resolved_hex})

    def apply_settings(self):
        pos_map = {0: "top_center", 1: "top_left", 2: "top_right", 3: "bottom_center"}
        mode = self.settings.get("theme_mode", "dark")
        cur_data = ACCENT_PALETTES.get(self.current_accent_identity, ACCENT_PALETTES["sky_blue"])
        resolved_hex = cur_data.get(mode, cur_data["dark"])

    def on_position_combo_activated(self, index: int):
        pos_map = {0: "top_center", 1: "top_left", 2: "top_right", 3: "bottom_center"}
        chosen_pos = pos_map.get(index, "top_center")
        self.settings.update_settings({
            "position": chosen_pos,
            "offset_x": 0,
            "offset_y": 12
        })

    def apply_settings(self):
        pos_map = {0: "top_center", 1: "top_left", 2: "top_right", 3: "bottom_center"}
        mode = self.settings.get("theme_mode", "dark")
        cur_data = ACCENT_PALETTES.get(self.current_accent_identity, ACCENT_PALETTES["sky_blue"])
        resolved_hex = cur_data.get(mode, cur_data["dark"])

        new_pos = pos_map.get(self.pos_combo.currentIndex(), "top_center")

        new_settings = {
            "accent_identity": self.current_accent_identity,
            "accent_color": resolved_hex,
            "position": new_pos,
            "offset_x": 0,
            "offset_y": 12,
            "bg_opacity": self.opacity_slider.value() / 100.0,
            "corner_radius": int(round(self.radius_slider.value() / 10.0)),
            "watermark_opacity": self.wm_opacity_slider.value() / 100.0
        }
        self.settings.update_settings(new_settings)

    def sync_controls_from_settings(self, settings_dict: dict = None):
        """Live updates all UI sliders, combos, swatches, and checkboxes from incoming settings without re-triggering save loops."""
        if settings_dict is None:
            settings_dict = self.settings.settings if self.settings else {}

        ident = settings_dict.get("accent_identity", "sky_blue")
        self.current_accent_identity = ident
        cur_data = ACCENT_PALETTES.get(ident, ACCENT_PALETTES["sky_blue"])
        if hasattr(self, 'color_name_lbl'):
            self.color_name_lbl.setText(cur_data["name"])

        mode = settings_dict.get("theme_mode", "dark")
        self.update_theme_switch_buttons(mode)

        if hasattr(self, 'opacity_slider'):
            op_val = int(round(settings_dict.get("bg_opacity", 0.90) * 100.0))
            self.opacity_slider.blockSignals(True)
            self.opacity_slider.setValue(op_val)
            self.opacity_lbl.setText(f"{op_val}%")
            self.opacity_slider.blockSignals(False)

        if hasattr(self, 'radius_slider'):
            rad_val = int(settings_dict.get("corner_radius", 20))
            self.radius_slider.blockSignals(True)
            self.radius_slider.setValue(rad_val * 10)
            self.radius_lbl.setText(f"{rad_val}px")
            self.radius_slider.blockSignals(False)

        if hasattr(self, 'wm_opacity_slider'):
            wm_op_val = int(round(settings_dict.get("watermark_opacity", 0.04) * 100.0))
            self.wm_opacity_slider.blockSignals(True)
            self.wm_opacity_slider.setValue(wm_op_val)
            self.wm_opacity_lbl.setText(f"{wm_op_val}%")
            self.wm_opacity_slider.blockSignals(False)

    def trigger_open_full_window(self):
        self.open_full_window_requested.emit()
        w = self.window()
        if hasattr(w, 'open_full_app_window'):
            w.open_full_app_window(9)
        else:
            from full_app_window import SanLivesFullAppWindow
            if not hasattr(self, '_standalone_full_win') or self._standalone_full_win is None:
                self._standalone_full_win = SanLivesFullAppWindow(settings=self.settings)
            self._standalone_full_win.show()
            self._standalone_full_win.raise_()
            self._standalone_full_win.activateWindow()


import webbrowser

# 10. NOTIFICATIONS FEED TAB WIDGET
class NotificationsTabWidget(QWidget):
    open_notification_requested = pyqtSignal(dict)

    def __init__(self, settings: SettingsManager = None, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.item_checkboxes = {}
        self.cleared_notification_ids = set()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        accent = resolve_accent_color(self.settings) if self.settings else "#38bdf8"
        mode = self.settings.get("theme_mode", "dark") if self.settings else "dark"
        pal = THEME_PALETTES.get(mode, THEME_PALETTES["dark"])

        head_box = QHBoxLayout()
        self.lbl_head = QLabel("\U0001F514 RECENT WINDOWS NOTIFICATIONS")
        self.lbl_head.setStyleSheet(f"color: {accent}; font-size: 10px; font-weight: 800; letter-spacing: 0.5px; background: transparent;")

        self.clear_all_btn = QPushButton("🗑️ Clear All")
        self.clear_all_btn.setFixedHeight(20)
        self.clear_all_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clear_all_btn.setStyleSheet(f"QPushButton {{ background-color: {pal['input_bg']}; color: {pal['text_primary']}; border: 1px solid {pal['input_border']}; border-radius: 4px; font-size: 9px; font-weight: bold; padding: 0 6px; }} QPushButton:hover {{ border: 1px solid {accent}; }}")
        self.clear_all_btn.clicked.connect(self.clear_all_notifications)

        self.delete_sel_btn = QPushButton("❌ Delete Selected")
        self.delete_sel_btn.setFixedHeight(20)
        self.delete_sel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.delete_sel_btn.setStyleSheet(f"QPushButton {{ background-color: {pal['input_bg']}; color: #ef4444; border: 1px solid {pal['input_border']}; border-radius: 4px; font-size: 9px; font-weight: bold; padding: 0 6px; }} QPushButton:hover {{ border: 1px solid #ef4444; }}")
        self.delete_sel_btn.setVisible(False)
        self.delete_sel_btn.clicked.connect(self.delete_selected_notifications)

        self.refresh_btn = QPushButton("\U0001F504 Refresh")
        self.refresh_btn.setFixedHeight(20)
        self.refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.refresh_btn.setStyleSheet(f"QPushButton {{ background-color: {pal['input_bg']}; color: {pal['text_primary']}; border: 1px solid {pal['input_border']}; border-radius: 4px; font-size: 9px; font-weight: bold; padding: 0 6px; }} QPushButton:hover {{ border: 1px solid {accent}; }}")
        self.refresh_btn.clicked.connect(self.load_notifications_feed)

        head_box.addWidget(self.lbl_head)
        head_box.addStretch()
        head_box.addWidget(self.delete_sel_btn)
        head_box.addWidget(self.clear_all_btn)
        head_box.addWidget(self.refresh_btn)
        layout.addLayout(head_box)

        feed_card = GlassPanel(category_key="alarms", corner_radius=10)
        feed_box = QVBoxLayout(feed_card)
        feed_box.setContentsMargins(6, 6, 6, 6)
        feed_box.setSpacing(4)

        # Status Banner
        self.status_lbl = QLabel()
        self.status_lbl.setStyleSheet(f"background: {pal['input_bg']}; color: {pal['text_secondary']}; border: 1px solid {pal['input_border']}; border-radius: 5px; padding: 4px; font-size: 9px; font-style: italic;")
        feed_box.addWidget(self.status_lbl)

        self.notif_list = QListWidget()
        self.notif_list.setStyleSheet(get_list_widget_qss(accent, mode))
        self.notif_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.notif_scroll_filter = SmoothScrollFilter(self.notif_list, step_size=36, duration=200)
        feed_box.addWidget(self.notif_list)

        layout.addWidget(feed_card)

        self.load_notifications_feed()

    def clear_all_notifications(self):
        res = SystemMonitor.get_windows_notifications()
        items = res.get("notifications", [])
        for item in items:
            self.cleared_notification_ids.add(item.get("id"))
        self.load_notifications_feed()

    def delete_selected_notifications(self):
        for notif_id, chk in list(self.item_checkboxes.items()):
            if chk.isChecked():
                self.cleared_notification_ids.add(notif_id)
        self.load_notifications_feed()

    def update_selection_state(self):
        any_checked = any(chk.isChecked() for chk in self.item_checkboxes.values())
        self.delete_sel_btn.setVisible(any_checked)

    def open_notification(self, data: dict):
        url = data.get("launch_url", "")
        if url:
            try:
                webbrowser.open(url)
            except Exception as e:
                print(f"Error opening notification URL '{url}': {e}")
                SystemMonitor.focus_app_window(data.get("app_name", ""), data.get("app_id", ""))
        else:
            SystemMonitor.focus_app_window(data.get("app_name", ""), data.get("app_id", ""))

        self.open_notification_requested.emit(data)

    def load_notifications_feed(self):
        self.notif_list.clear()
        self.item_checkboxes.clear()
        self.delete_sel_btn.setVisible(False)
        self.status_lbl.setText("⏳ Fetching Windows notifications in background...")

        from system_monitor import NotificationsWorkerThread
        self.worker = NotificationsWorkerThread(self)
        self.worker.notifications_ready.connect(self.populate_notifications)
        self.worker.start()

    def populate_notifications(self, res: dict):
        from PyQt6.sip import isdeleted
        if isdeleted(self) or not isinstance(res, dict):
            return

        self.notif_list.clear()
        self.item_checkboxes.clear()
        status = res.get("status", "unknown")
        raw_items = res.get("notifications", [])
        items = [i for i in raw_items if i.get("id") not in self.cleared_notification_ids]

        accent = resolve_accent_color(self.settings) if self.settings else "#38bdf8"
        mode = self.settings.get("theme_mode", "dark") if self.settings else "dark"
        pal = THEME_PALETTES.get(mode, THEME_PALETTES["dark"])
        is_dark = (mode == "dark")

        if status == "denied":
            self.status_lbl.setText("\u26a0\ufe0f Windows Notification Access Required: Enable access in Windows Settings > Privacy & security > Notifications.")
            self.status_lbl.show()
        elif status == "unsupported":
            self.status_lbl.setText("\u2139\ufe0f WinRT Notification Listener is unsupported on this system environment.")
            self.status_lbl.show()
        else:
            self.status_lbl.setText(f"\u2705 Active Notification Stream ({len(items)} items captured)")
            self.status_lbl.show()

        print(f"[Notif] UI refreshed with {len(items)} notification(s) (status='{status}')", flush=True)

        if not items:
            item = QListWidgetItem(self.notif_list)
            empty_w = make_empty_state("\U0001F514", "No Recent Notifications", "Notifications from apps (WhatsApp, Mail, System) will appear here.", mode)
            item.setSizeHint(empty_w.sizeHint())
            self.notif_list.addItem(item)
            self.notif_list.setItemWidget(item, empty_w)
            return

        for data in items[:25]:
            notif_id = data.get("id")
            item_frame = QFrame()
            item_frame.setObjectName("notif_item_frame")
            frame_bg = "rgba(255, 255, 255, 0.05)" if is_dark else "rgba(255, 255, 255, 0.85)"
            frame_border = "rgba(255, 255, 255, 0.10)" if is_dark else "rgba(0, 0, 0, 0.08)"
            item_frame.setStyleSheet(f"""
                QFrame#notif_item_frame {{
                    background-color: {frame_bg};
                    border: 1px solid {frame_border};
                    border-radius: 8px;
                }}
                QFrame#notif_item_frame:hover {{
                    border: 1px solid {accent}66;
                    background-color: rgba(255, 255, 255, 0.09);
                }}
            """)
            box = QVBoxLayout(item_frame)
            box.setContentsMargins(8, 6, 8, 6)
            box.setSpacing(3)

            top_row = QHBoxLayout()
            top_row.setSpacing(6)

            chk = QCheckBox()
            chk.setStyleSheet(get_checkbox_qss(accent, mode))
            chk.toggled.connect(self.update_selection_state)
            self.item_checkboxes[notif_id] = chk

            chip_bg = "rgba(56, 189, 248, 0.18)" if mode == "dark" else "rgba(2, 132, 199, 0.12)"
            chip_border = "rgba(56, 189, 248, 0.35)" if mode == "dark" else "rgba(2, 132, 199, 0.25)"
            chip_color = accent if mode == "dark" else "#0369a1"
            chip_app = QLabel(data.get("app_name", "App").upper())
            chip_app.setStyleSheet(f"color: {chip_color}; background-color: {chip_bg}; border: 1px solid {chip_border}; font-size: 9.5px; font-weight: 800; border-radius: 4px; padding: 2px 6px; letter-spacing: 0.5px;")

            lbl_time = QLabel(data.get("timestamp", ""))
            lbl_time.setStyleSheet(f"color: {pal['text_muted']}; font-size: 9.5px; font-weight: 600; background: transparent;")

            btn_open = QPushButton("\u2197\ufe0f Open")
            btn_open.setFixedHeight(20)
            btn_open.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_open.setStyleSheet(f"QPushButton {{ background-color: rgba(56, 189, 248, 0.18); color: {accent}; border: 1px solid rgba(56, 189, 248, 0.35); border-radius: 4px; font-size: 9.5px; font-weight: bold; padding: 0 8px; }} QPushButton:hover {{ background-color: {accent}; color: #ffffff; }}")
            btn_open.clicked.connect(lambda _, d=data: self.open_notification(d))

            top_row.addWidget(chk)
            top_row.addWidget(chip_app)
            top_row.addStretch()
            top_row.addWidget(lbl_time)
            top_row.addWidget(btn_open)
            box.addLayout(top_row)

            lbl_title = QLabel(data.get("title", ""))
            lbl_title.setStyleSheet(f"color: {pal['text_primary']}; font-size: 11px; font-weight: 800; background: transparent; padding-top: 2px;")
            box.addWidget(lbl_title)

            body = data.get("body", "")
            if body:
                lbl_body = QLabel(body)
                lbl_body.setWordWrap(True)
                lbl_body.setStyleSheet(f"color: {pal['text_secondary']}; font-size: 10px; font-weight: 500; background: transparent; padding-top: 1px;")
                box.addWidget(lbl_body)

            item = QListWidgetItem(self.notif_list)
            item.setSizeHint(item_frame.sizeHint())
            self.notif_list.addItem(item)
            self.notif_list.setItemWidget(item, item_frame)

    def apply_theme(self, accent_color: str, mode: str = "dark"):
        pal = THEME_PALETTES.get(mode, THEME_PALETTES["dark"])
        for gp in self.findChildren(GlassPanel):
            gp.apply_theme(accent_color, mode)

        self.lbl_head.setStyleSheet(f"color: {accent_color}; font-size: 10px; font-weight: 800; letter-spacing: 0.5px; background: transparent;")
        self.clear_all_btn.setStyleSheet(f"QPushButton {{ background-color: {pal['input_bg']}; color: {pal['text_primary']}; border: 1px solid {pal['input_border']}; border-radius: 4px; font-size: 9px; font-weight: bold; padding: 0 6px; }} QPushButton:hover {{ border: 1px solid {accent_color}; }}")
        self.refresh_btn.setStyleSheet(f"QPushButton {{ background-color: {pal['input_bg']}; color: {pal['text_primary']}; border: 1px solid {pal['input_border']}; border-radius: 4px; font-size: 9px; font-weight: bold; padding: 0 6px; }} QPushButton:hover {{ border: 1px solid {accent_color}; }}")
        self.notif_list.setStyleSheet(get_list_widget_qss(accent_color, mode))
