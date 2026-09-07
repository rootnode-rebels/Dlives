"""
Dlives • Customization Studio & Island Configurator
=====================================================
Dedicated configuration and customization hub for the compact Dynamic Island.
Contains ZERO duplicate functional day-to-day widgets (notes, alarms, media,
and clipboard are used exclusively in the compact island).

Features:
- Island Modules & Tab Manager (CENTERPIECE): Choose which tabs appear on the
  floating island and their exact order with instant live synchronization.
- Theme, Optics & Glassmorphism: Dark smoked glass / light milk glass, 12 accents,
  opacity, radius, and sheen sweeps.
- Island Position & Geometry: Screen anchors, monitor selection, offsets, hover delays.
- Home Dashboard Modules: Toggles for cards rendered inside the island's Home tab.
- Alarms, Sounds & Notifications: Chimes, custom audio testing, popup takeovers, 12h/24h.
- App Launcher Shortcuts Config: Register and manage .exe apps on the island.
- System Integration & Backups: Start with Windows, config export/import, factory reset.
"""

import os
import sys
import json
import webbrowser
from PyQt6.QtWidgets import (
    QWidget, QMainWindow, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QStackedWidget, QListWidget, QListWidgetItem, QScrollArea, QFrame,
    QCheckBox, QSizePolicy, QApplication, QGraphicsDropShadowEffect, QGraphicsOpacityEffect,
    QComboBox, QSlider, QSpinBox, QLineEdit, QFileDialog, QMessageBox,
    QFormLayout, QGridLayout, QButtonGroup, QInputDialog
)
from PyQt6.QtCore import Qt, QSize, pyqtSignal, QPoint, QTimer, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QIcon, QPixmap, QColor, QPainter, QPainterPath, QLinearGradient, QFont, QPalette

from storage_manager import StorageManager
from settings_manager import SettingsManager
from ui_components import (
    GlassPanel,
    THEME_PALETTES,
    ACCENT_PALETTES,
    resolve_accent_color,
    get_accent_text_color,
    get_accent_tinted_logo,
    get_list_widget_qss,
    get_scrollbar_qss,
    get_checkbox_qss,
    get_combobox_qss,
    get_spinbox_qss,
    get_lineedit_qss,
    SmoothScrollFilter
)

ISLAND_TAB_DEFINITIONS = [
    {"id": "home", "title": "Home Dashboard", "icon": "🏠", "desc": "Overview of active alarms, timetable, notes & media"},
    {"id": "control", "title": "Control Center", "icon": "🎛️", "desc": "Media playback controls, volume & brightness sliders"},
    {"id": "hardware", "title": "Hardware Diagnostics (Sys)", "icon": "📊", "desc": "Real-time CPU, RAM, Wi-Fi speed & temp cleaner"},
    {"id": "shelf_clip", "title": "Clipboard & File Shelf", "icon": "📋", "desc": "Clipboard history buffer & drag-and-drop file shelf"},
    {"id": "calendar", "title": "Calendar & Events", "icon": "📅", "desc": "Monthly calendar grid & daily event schedule"},
    {"id": "alarms", "title": "Alarms & Timetable", "icon": "🔔", "desc": "Chime alarms, recurring schedules & timetable checklist"},
    {"id": "apps", "title": "App Launcher", "icon": "🚀", "desc": "Quick access grid for favorite apps & executables"},
    {"id": "notes", "title": "Quick Notes", "icon": "📝", "desc": "Multi-note scratchpad synced live with File Explorer"},
    {"id": "notifs", "title": "Notifications Feed", "icon": "🔔", "desc": "Windows toast notification history & actionable items"},
    {"id": "settings", "title": "Quick Settings", "icon": "⚙️", "desc": "Compact island in-place settings and studio launcher"},
]


def create_form_label(text: str, pal: dict) -> QLabel:
    """Creates a high-contrast readable label for form rows against dark/light glass."""
    lbl = QLabel(text)
    lbl.setStyleSheet(f"color: {pal['text_primary']}; font-size: 11px; font-weight: 600; background: transparent; border: none; border-radius: 0px;")
    return lbl


# =============================================================================
# 1. CENTERPIECE: ISLAND MODULES & TAB MANAGER
# =============================================================================
class TabManagerConfigWidget(QWidget):
    """Primary centerpiece: Choose which tabs appear on the compact island and their order."""
    tab_configuration_changed = pyqtSignal()

    def __init__(self, settings: SettingsManager, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        accent = resolve_accent_color(self.settings) if self.settings else "#38bdf8"
        mode = self.settings.get("theme_mode", "dark") if self.settings else "dark"
        pal = THEME_PALETTES.get(mode, THEME_PALETTES["dark"])

        # Header Info Card
        header_card = GlassPanel(category_key="settings", corner_radius=12)
        h_box = QVBoxLayout(header_card)
        h_box.setContentsMargins(16, 12, 16, 12)
        h_box.setSpacing(4)

        lbl_title = QLabel("🧩 Floating Island Modules & Tab Manager")
        lbl_title.setStyleSheet(f"color: {accent}; font-size: 14px; font-weight: 800; background: transparent;")
        lbl_desc = QLabel("Configure exactly which tabs and modules appear in the compact floating island and reorder them.\nChanges apply live to the floating bar without restarting.")
        lbl_desc.setStyleSheet(f"color: {pal['text_secondary']}; font-size: 10.5px; line-height: 1.3; background: transparent;")

        h_box.addWidget(lbl_title)
        h_box.addWidget(lbl_desc)
        layout.addWidget(header_card)

        # Tab List Card
        list_card = GlassPanel(category_key="default", corner_radius=12)
        list_box = QVBoxLayout(list_card)
        list_box.setContentsMargins(14, 12, 14, 12)
        list_box.setSpacing(10)

        # Toolbar
        tool_row = QHBoxLayout()
        tool_row.setSpacing(8)

        self.btn_move_up = QPushButton("▲ Move Up")
        self.btn_move_down = QPushButton("▼ Move Down")
        self.btn_preset_all = QPushButton("🌟 All Modules")
        self.btn_preset_minimal = QPushButton("⚡ Minimalist (Home+Alarms+Notes)")
        self.btn_reset_defaults = QPushButton("🔄 Reset Defaults")

        for b in (self.btn_move_up, self.btn_move_down, self.btn_preset_all, self.btn_preset_minimal, self.btn_reset_defaults):
            b.setFixedHeight(26)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setStyleSheet(f"QPushButton {{ background: {pal['input_bg']}; color: {pal['text_primary']}; border: 1px solid {pal['input_border']}; border-radius: 5px; font-size: 10px; font-weight: bold; padding: 0 10px; }} QPushButton:hover {{ border: 1px solid {accent}; }}")

        self.btn_move_up.clicked.connect(self.move_selected_up)
        self.btn_move_down.clicked.connect(self.move_selected_down)
        self.btn_preset_all.clicked.connect(self.apply_preset_all)
        self.btn_preset_minimal.clicked.connect(self.apply_preset_minimal)
        self.btn_reset_defaults.clicked.connect(self.reset_defaults)

        tool_row.addWidget(self.btn_move_up)
        tool_row.addWidget(self.btn_move_down)
        tool_row.addStretch()
        tool_row.addWidget(self.btn_preset_all)
        tool_row.addWidget(self.btn_preset_minimal)
        tool_row.addWidget(self.btn_reset_defaults)
        list_box.addLayout(tool_row)

        self.tab_list = QListWidget()
        self.tab_list.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.tab_list.viewport().setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.tab_list.viewport().setAutoFillBackground(False)
        self.tab_list.setSpacing(4)
        self.tab_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.tab_list.setStyleSheet(get_list_widget_qss(accent, mode))
        list_box.addWidget(self.tab_list)

        layout.addWidget(list_card, 1)

        # Bottom Action Bar
        action_bar = GlassPanel(category_key="settings", corner_radius=12)
        action_box = QHBoxLayout(action_bar)
        action_box.setContentsMargins(16, 10, 16, 10)
        action_box.setSpacing(12)

        accent_txt = get_accent_text_color(accent)
        self.btn_save_tabs = QPushButton("💾 Apply && Save Tab Configuration")
        self.btn_save_tabs.setFixedHeight(32)
        self.btn_save_tabs.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_save_tabs.setStyleSheet(f"QPushButton {{ background-color: {accent}; color: {accent_txt}; border: 1px solid rgba(255, 255, 255, 0.40); border-radius: 6px; font-size: 11.5px; font-weight: 800; padding: 0 20px; }} QPushButton:hover {{ opacity: 0.9; }}")
        self.btn_save_tabs.clicked.connect(self.save_tab_configuration)

        self.lbl_status = QLabel("💡 Tip: Changes apply live to the floating island immediately.")
        self.lbl_status.setStyleSheet(f"color: {pal['text_muted']}; font-size: 10px; background: transparent;")

        action_box.addWidget(self.btn_save_tabs)
        action_box.addWidget(self.lbl_status)
        action_box.addStretch()

        layout.addWidget(action_bar)
        self.populate_tabs()

    def populate_tabs(self):
        # Cleanly tear down all previous item widgets to eliminate orphaned child leaks and black rectangular repaint artifacts
        while self.tab_list.count():
            item = self.tab_list.takeItem(0)
            if item:
                w = self.tab_list.itemWidget(item)
                if w:
                    self.tab_list.removeItemWidget(item)
                    w.setParent(None)
                    w.deleteLater()
        self.tab_list.clear()

        # Clean sweep any detached viewport children
        for child in self.tab_list.viewport().findChildren(QWidget):
            child.setParent(None)
            child.deleteLater()

        mode = self.settings.get("theme_mode", "dark") if self.settings else "dark"
        accent = resolve_accent_color(self.settings) if self.settings else "#38bdf8"
        pal = THEME_PALETTES.get(mode, THEME_PALETTES["dark"])

        default_order = [t["id"] for t in ISLAND_TAB_DEFINITIONS]
        tab_order = list(self.settings.get("tab_order", default_order)) if self.settings else default_order
        visible_tabs = set(self.settings.get("visible_tabs", default_order)) if self.settings else set(default_order)

        def_map = {t["id"]: t for t in ISLAND_TAB_DEFINITIONS}

        for t in ISLAND_TAB_DEFINITIONS:
            if t["id"] not in tab_order:
                tab_order.append(t["id"])

        for tab_id in tab_order:
            if tab_id not in def_map:
                continue
            info = def_map[tab_id]
            is_vis = tab_id in visible_tabs

            item = QListWidgetItem(self.tab_list)
            item.setSizeHint(QSize(0, 48))
            item.setData(Qt.ItemDataRole.UserRole, tab_id)

            row = QWidget()
            row.setStyleSheet("background: transparent; border: none; outline: none;")
            r_box = QHBoxLayout(row)
            r_box.setContentsMargins(10, 4, 10, 4)
            r_box.setSpacing(12)

            chk = QCheckBox()
            chk.setChecked(is_vis)
            chk.setStyleSheet(get_checkbox_qss(accent, mode))
            if tab_id == "home":
                chk.setEnabled(False)
                chk.setChecked(True)
                chk.setToolTip("Home Dashboard is required as the island landing.")
            else:
                chk.toggled.connect(lambda checked, tid=tab_id: self.on_tab_visibility_toggled(tid, checked))

            lbl_icon = QLabel(info["icon"])
            lbl_icon.setStyleSheet("font-size: 17px; background: transparent; border: none; outline: none;")

            txt_box = QVBoxLayout()
            txt_box.setSpacing(1)
            lbl_title = QLabel(info["title"])
            lbl_title.setStyleSheet(f"color: {pal['text_primary']}; font-size: 11px; font-weight: bold; background: transparent; border: none; outline: none;")
            lbl_desc = QLabel(info["desc"])
            lbl_desc.setStyleSheet(f"color: {pal['text_muted']}; font-size: 9px; background: transparent; border: none; outline: none;")
            txt_box.addWidget(lbl_title)
            txt_box.addWidget(lbl_desc)

            badge = QLabel("ACTIVE ON ISLAND" if is_vis else "HIDDEN")
            badge_bg = f"rgba({QColor(accent).red()}, {QColor(accent).green()}, {QColor(accent).blue()}, 0.20)" if is_vis else "rgba(100, 116, 139, 0.15)"
            badge_color = accent if is_vis else pal['text_muted']
            badge.setStyleSheet(f"background: {badge_bg}; color: {badge_color}; border: 1px solid {badge_color}55; border-radius: 5px; font-size: 8px; font-weight: 800; padding: 2px 8px; outline: none;")

            r_box.addWidget(chk)
            r_box.addWidget(lbl_icon)
            r_box.addLayout(txt_box, 1)
            r_box.addWidget(badge)

            self.tab_list.addItem(item)
            self.tab_list.setItemWidget(item, row)

        self.tab_list.viewport().update()
        self.tab_list.update()
        self.update()

    def on_tab_visibility_toggled(self, tab_id: str, is_visible: bool):
        visible = set(self.settings.get("visible_tabs", [t["id"] for t in ISLAND_TAB_DEFINITIONS]))
        if is_visible:
            visible.add(tab_id)
        else:
            if tab_id != "home":
                visible.discard(tab_id)
        self.settings.update_settings({"visible_tabs": list(visible)})
        self.tab_configuration_changed.emit()

    def move_selected_up(self):
        row = self.tab_list.currentRow()
        if row > 0:
            default_order = [t["id"] for t in ISLAND_TAB_DEFINITIONS]
            tab_order = list(self.settings.get("tab_order", default_order))
            tab_order[row], tab_order[row - 1] = tab_order[row - 1], tab_order[row]
            self.settings.update_settings({"tab_order": tab_order})
            self.populate_tabs()
            self.tab_list.setCurrentRow(row - 1)
            self.tab_configuration_changed.emit()

    def move_selected_down(self):
        row = self.tab_list.currentRow()
        default_order = [t["id"] for t in ISLAND_TAB_DEFINITIONS]
        tab_order = list(self.settings.get("tab_order", default_order))
        if 0 <= row < len(tab_order) - 1:
            tab_order[row], tab_order[row + 1] = tab_order[row + 1], tab_order[row]
            self.settings.update_settings({"tab_order": tab_order})
            self.populate_tabs()
            self.tab_list.setCurrentRow(row + 1)
            self.tab_configuration_changed.emit()

    def apply_preset_all(self):
        all_tabs = [t["id"] for t in ISLAND_TAB_DEFINITIONS]
        self.settings.update_settings({"visible_tabs": all_tabs})
        self.populate_tabs()
        self.save_tab_configuration()

    def apply_preset_minimal(self):
        minimal = ["home", "alarms", "notes"]
        self.settings.update_settings({"visible_tabs": minimal})
        self.populate_tabs()
        self.save_tab_configuration()

    def reset_defaults(self):
        default_order = [t["id"] for t in ISLAND_TAB_DEFINITIONS]
        self.settings.update_settings({
            "tab_order": default_order,
            "visible_tabs": default_order
        })
        self.populate_tabs()
        self.save_tab_configuration()

    def save_tab_configuration(self):
        order = []
        visible = []
        for i in range(self.tab_list.count()):
            item = self.tab_list.item(i)
            tid = item.data(Qt.ItemDataRole.UserRole)
            order.append(tid)
            w = self.tab_list.itemWidget(item)
            if w:
                chk = w.findChild(QCheckBox)
                if chk and chk.isChecked():
                    visible.append(tid)
        if "home" not in visible:
            visible.insert(0, "home")

        self.settings.update_settings({"tab_order": order, "visible_tabs": visible})
        self.tab_configuration_changed.emit()

        if hasattr(self, 'btn_save_tabs'):
            orig_text = "💾 Apply && Save Tab Configuration"
            accent = resolve_accent_color(self.settings) if self.settings else "#38bdf8"
            accent_txt = get_accent_text_color(accent)
            self.btn_save_tabs.setText("✓ Tab Configuration Saved Live!")
            self.btn_save_tabs.setStyleSheet("QPushButton { background-color: #10b981 !important; color: #ffffff !important; border: 1px solid #10b981 !important; border-radius: 6px !important; font-size: 11.5px !important; font-weight: 800 !important; padding: 0 20px !important; }")
            def restore():
                try:
                    self.btn_save_tabs.setText(orig_text)
                    self.btn_save_tabs.setStyleSheet(f"QPushButton {{ background-color: {accent}; color: {accent_txt}; border: 1px solid rgba(255, 255, 255, 0.40); border-radius: 6px; font-size: 11.5px; font-weight: 800; padding: 0 20px; }} QPushButton:hover {{ opacity: 0.9; }}")
                except Exception:
                    pass
            QTimer.singleShot(1500, restore)

    def apply_theme(self, accent_color: str, mode: str = "dark"):
        pal = THEME_PALETTES.get(mode, THEME_PALETTES["dark"])
        for gp in self.findChildren(GlassPanel):
            gp.apply_theme(accent_color, mode)
        accent_txt = get_accent_text_color(accent_color)
        if hasattr(self, 'btn_save_tabs'):
            self.btn_save_tabs.setStyleSheet(f"QPushButton {{ background-color: {accent_color}; color: {accent_txt}; border: 1px solid rgba(255, 255, 255, 0.40); border-radius: 6px; font-size: 11.5px; font-weight: 800; padding: 0 20px; }} QPushButton:hover {{ opacity: 0.9; }}")
        if hasattr(self, 'tab_list'):
            self.tab_list.setStyleSheet(get_list_widget_qss(accent_color, mode))
        self.populate_tabs()


# =============================================================================
# 2. THEME & GLASSMORPHISM CONFIGURATION
# =============================================================================
class ThemeOpticsConfigWidget(QWidget):
    """Configures Dark/Light mode, 12 accents, opacity, corner radius, and glass optics."""
    def __init__(self, settings: SettingsManager, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.accent_buttons = {}
        self.init_ui()

    def init_ui(self):
        accent = resolve_accent_color(self.settings) if self.settings else "#38bdf8"
        mode = self.settings.get("theme_mode", "dark") if self.settings else "dark"
        pal = THEME_PALETTES.get(mode, THEME_PALETTES["dark"])

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        scroll.viewport().setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        scroll.viewport().setAutoFillBackground(False)
        scroll.setStyleSheet(f"QScrollArea, QScrollArea > QWidget > QWidget {{ background: transparent; border: none; }} {get_scrollbar_qss(accent, mode)}")

        container = QWidget()
        container.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        container.setStyleSheet("background: transparent; border: none;")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        # Panel: Theme Mode & Accents
        theme_card = GlassPanel(category_key="settings", corner_radius=12)
        t_box = QVBoxLayout(theme_card)
        t_box.setContentsMargins(16, 14, 16, 14)
        t_box.setSpacing(10)

        lbl_t_title = QLabel("🎨 Theme Mode & Visual Accent Palette")
        lbl_t_title.setStyleSheet(f"color: {accent}; font-size: 13px; font-weight: 800; background: transparent;")
        t_box.addWidget(lbl_t_title)

        mode_row = QHBoxLayout()
        self.btn_dark_mode = QPushButton("🌙 Dark Smoked Glass")
        self.btn_light_mode = QPushButton("☀️ Light Crystalline Milk Glass")
        for b in (self.btn_dark_mode, self.btn_light_mode):
            b.setFixedHeight(30)
            b.setCursor(Qt.CursorShape.PointingHandCursor)

        self.btn_dark_mode.clicked.connect(lambda: self.set_theme_mode("dark"))
        self.btn_light_mode.clicked.connect(lambda: self.set_theme_mode("light"))
        mode_row.addWidget(self.btn_dark_mode)
        mode_row.addWidget(self.btn_light_mode)
        t_box.addLayout(mode_row)

        lbl_accents = QLabel("Accent Color Identity (12 High-Contrast Palettes):")
        lbl_accents.setStyleSheet(f"color: {pal['text_primary']}; font-size: 10.5px; font-weight: bold; margin-top: 6px; background: transparent;")
        t_box.addWidget(lbl_accents)

        accent_grid = QGridLayout()
        accent_grid.setSpacing(8)
        self.accent_group = QButtonGroup(self)

        row, col = 0, 0
        current_identity = self.settings.get("accent_identity", "sky_blue")

        for key, data in ACCENT_PALETTES.items():
            btn = QPushButton(f" {data['name']}")
            btn.setFixedHeight(28)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _, k=key: self.select_accent_identity(k))
            self.accent_buttons[key] = btn
            accent_grid.addWidget(btn, row, col)
            col += 1
            if col >= 4:
                col = 0
                row += 1

        t_box.addLayout(accent_grid)
        layout.addWidget(theme_card)

        # Panel: Glassmorphism Optics
        optics_card = GlassPanel(category_key="default", corner_radius=12)
        o_box = QVBoxLayout(optics_card)
        o_box.setContentsMargins(16, 14, 16, 14)
        o_box.setSpacing(12)

        lbl_o_title = QLabel("✨ Glass Optics, Blur & Geometry")
        lbl_o_title.setStyleSheet(f"color: {accent}; font-size: 13px; font-weight: 800; background: transparent;")
        o_box.addWidget(lbl_o_title)

        # Opacity Slider
        op_row = QHBoxLayout()
        self.lbl_op = QLabel("Glass Background Opacity:")
        self.lbl_op.setStyleSheet(f"color: {pal['text_primary']}; font-size: 11px; font-weight: bold; background: transparent; border: none; border-radius: 0px;")
        self.lbl_op_val = QLabel(f"{int(float(self.settings.get('bg_opacity', 0.90)) * 100)}%")
        self.lbl_op_val.setStyleSheet(f"color: {accent}; font-size: 11px; font-weight: 800; background: transparent; border: none; border-radius: 0px;")
        op_row.addWidget(self.lbl_op)
        op_row.addStretch()
        op_row.addWidget(self.lbl_op_val)
        o_box.addLayout(op_row)

        self.slider_opacity = QSlider(Qt.Orientation.Horizontal)
        self.slider_opacity.setRange(20, 100)
        self.slider_opacity.setValue(int(float(self.settings.get("bg_opacity", 0.90)) * 100))
        self.slider_opacity.valueChanged.connect(self.on_opacity_slider_changed)
        o_box.addWidget(self.slider_opacity)

        # Corner Radius Slider
        rad_row = QHBoxLayout()
        self.lbl_rad = QLabel("Glass Corner Radius:")
        self.lbl_rad.setStyleSheet(f"color: {pal['text_primary']}; font-size: 11px; font-weight: bold; background: transparent; border: none; border-radius: 0px;")
        self.lbl_rad_val = QLabel(f"{int(self.settings.get('corner_radius', 20))}px")
        self.lbl_rad_val.setStyleSheet(f"color: {accent}; font-size: 11px; font-weight: 800; background: transparent; border: none; border-radius: 0px;")
        rad_row.addWidget(self.lbl_rad)
        rad_row.addStretch()
        rad_row.addWidget(self.lbl_rad_val)
        o_box.addLayout(rad_row)

        self.slider_radius = QSlider(Qt.Orientation.Horizontal)
        self.slider_radius.setRange(0, 36)
        self.slider_radius.setValue(int(self.settings.get("corner_radius", 20)))
        self.slider_radius.valueChanged.connect(self.on_radius_slider_changed)
        o_box.addWidget(self.slider_radius)

        layout.addWidget(optics_card)
        layout.addStretch()

        scroll.setWidget(container)
        container.setAutoFillBackground(False)
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll)

        self.update_active_swatches()

    def set_theme_mode(self, mode: str):
        self.settings.update_settings({"theme_mode": mode})
        cur_id = self.settings.get("accent_identity", "sky_blue")
        cur_data = ACCENT_PALETTES.get(cur_id, ACCENT_PALETTES["sky_blue"])
        resolved_hex = cur_data.get(mode, cur_data["dark"])
        self.settings.update_settings({"accent_color": resolved_hex})
        self.update_active_swatches()

    def select_accent_identity(self, identity: str):
        if identity not in ACCENT_PALETTES:
            return
        mode = self.settings.get("theme_mode", "dark")
        cur_data = ACCENT_PALETTES[identity]
        resolved_hex = cur_data.get(mode, cur_data["dark"])
        self.settings.update_settings({
            "accent_identity": identity,
            "accent_color": resolved_hex
        })
        self.update_active_swatches()

    def on_opacity_slider_changed(self, val: int):
        self.lbl_op_val.setText(f"{val}%")
        self.settings.update_settings({"bg_opacity": val / 100.0})

    def on_radius_slider_changed(self, val: int):
        self.lbl_rad_val.setText(f"{val}px")
        self.settings.update_settings({"corner_radius": val})

    def update_active_swatches(self):
        mode = self.settings.get("theme_mode", "dark")
        accent = resolve_accent_color(self.settings)
        active_id = self.settings.get("accent_identity", "sky_blue")
        pal = THEME_PALETTES.get(mode, THEME_PALETTES["dark"])

        if mode == "dark":
            self.btn_dark_mode.setStyleSheet(f"QPushButton {{ background-color: {accent}; color: {get_accent_text_color(accent)}; font-weight: bold; border-radius: 6px; border: 1px solid rgba(255,255,255,0.3); }}")
            self.btn_light_mode.setStyleSheet(f"QPushButton {{ background: {pal['input_bg']}; color: {pal['text_primary']}; border-radius: 6px; border: 1px solid {pal['input_border']}; }}")
        else:
            self.btn_light_mode.setStyleSheet(f"QPushButton {{ background-color: {accent}; color: {get_accent_text_color(accent)}; font-weight: bold; border-radius: 6px; border: 1px solid rgba(0,0,0,0.2); }}")
            self.btn_dark_mode.setStyleSheet(f"QPushButton {{ background: {pal['input_bg']}; color: {pal['text_primary']}; border-radius: 6px; border: 1px solid {pal['input_border']}; }}")

        for k, btn in self.accent_buttons.items():
            hex_val = ACCENT_PALETTES[k].get(mode, ACCENT_PALETTES[k]["dark"])
            btn_txt = get_accent_text_color(hex_val)
            if k == active_id:
                btn.setStyleSheet(f"QPushButton {{ background-color: {hex_val}; color: {btn_txt}; font-weight: 800; font-size: 10px; border-radius: 6px; border: 2px solid #ffffff; }}")
            else:
                btn.setStyleSheet(f"QPushButton {{ background-color: {hex_val}; color: {btn_txt}; font-weight: 600; font-size: 9.5px; border-radius: 6px; border: 1px solid rgba(255,255,255,0.2); }} QPushButton:hover {{ border: 2px solid #ffffff; }}")

    def apply_theme(self, accent_color: str, mode: str = "dark"):
        pal = THEME_PALETTES.get(mode, THEME_PALETTES["dark"])
        for gp in self.findChildren(GlassPanel):
            gp.apply_theme(accent_color, mode)
        for sc in self.findChildren(QScrollArea):
            sc.setStyleSheet(f"QScrollArea, QScrollArea > QWidget > QWidget {{ background: transparent; border: none; }} {get_scrollbar_qss(accent_color, mode)}")
        self.update_active_swatches()
        if hasattr(self, 'lbl_op'):
            self.lbl_op.setStyleSheet(f"color: {pal['text_primary']}; font-size: 11px; font-weight: bold; background: transparent; border: none; border-radius: 0px;")
        if hasattr(self, 'lbl_op_val'):
            self.lbl_op_val.setStyleSheet(f"color: {accent_color}; font-size: 11px; font-weight: 800; background: transparent; border: none; border-radius: 0px;")
        if hasattr(self, 'lbl_rad'):
            self.lbl_rad.setStyleSheet(f"color: {pal['text_primary']}; font-size: 11px; font-weight: bold; background: transparent; border: none; border-radius: 0px;")
        if hasattr(self, 'lbl_rad_val'):
            self.lbl_rad_val.setStyleSheet(f"color: {accent_color}; font-size: 11px; font-weight: 800; background: transparent; border: none; border-radius: 0px;")


# =============================================================================
# 3. ISLAND POSITION & GEOMETRY CONFIGURATION
# =============================================================================
class IslandPositionConfigWidget(QWidget):
    """Configures screen anchors, monitor selection, offsets, and hover expansion delays."""
    def __init__(self, settings: SettingsManager, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        accent = resolve_accent_color(self.settings) if self.settings else "#38bdf8"
        mode = self.settings.get("theme_mode", "dark") if self.settings else "dark"
        pal = THEME_PALETTES.get(mode, THEME_PALETTES["dark"])

        card = GlassPanel(category_key="settings", corner_radius=12)
        c_box = QVBoxLayout(card)
        c_box.setContentsMargins(16, 14, 16, 14)
        c_box.setSpacing(12)

        lbl_title = QLabel("📍 Island Screen Position & Physical Geometry")
        lbl_title.setStyleSheet(f"color: {accent}; font-size: 13px; font-weight: 800; background: transparent;")
        c_box.addWidget(lbl_title)

        form = QFormLayout()
        form.setSpacing(12)

        # Position Anchor
        self.lbl_f_pos = create_form_label("Monitor Screen Anchor:", pal)
        self.combo_pos = QComboBox()
        self.combo_pos.addItem("Top Center (Default)", "top_center")
        self.combo_pos.addItem("Top Left", "top_left")
        self.combo_pos.addItem("Top Right", "top_right")
        self.combo_pos.addItem("Bottom Center", "bottom_center")
        idx = self.combo_pos.findData(self.settings.get("position", "top_center"))
        if idx >= 0:
            self.combo_pos.setCurrentIndex(idx)
        self.combo_pos.setStyleSheet(get_combobox_qss(accent, mode))
        self.combo_pos.currentIndexChanged.connect(lambda: self.settings.update_settings({"position": self.combo_pos.currentData()}))
        form.addRow(self.lbl_f_pos, self.combo_pos)

        # Monitor Index
        self.lbl_f_mon = create_form_label("Active Monitor Screen:", pal)
        self.combo_mon = QComboBox()
        screens = QApplication.screens()
        for i, s in enumerate(screens):
            geo = s.geometry()
            self.combo_mon.addItem(f"Monitor {i + 1} ({geo.width()}x{geo.height()})", i)
        cur_mon = int(self.settings.get("monitor_index", 0))
        if 0 <= cur_mon < len(screens):
            self.combo_mon.setCurrentIndex(cur_mon)
        self.combo_mon.setStyleSheet(get_combobox_qss(accent, mode))
        self.combo_mon.currentIndexChanged.connect(lambda: self.settings.update_settings({"monitor_index": self.combo_mon.currentData()}))
        form.addRow(self.lbl_f_mon, self.combo_mon)

        # Offset X
        self.lbl_f_x = create_form_label("Horizontal Offset X (px):", pal)
        self.spin_x = QSpinBox()
        self.spin_x.setRange(-1000, 1000)
        self.spin_x.setValue(int(self.settings.get("offset_x", 0)))
        self.spin_x.setStyleSheet(get_spinbox_qss(accent, mode))
        self.spin_x.valueChanged.connect(lambda v: self.settings.update_settings({"offset_x": v}))
        form.addRow(self.lbl_f_x, self.spin_x)

        # Offset Y
        self.lbl_f_y = create_form_label("Vertical Offset Y (px):", pal)
        self.spin_y = QSpinBox()
        self.spin_y.setRange(0, 800)
        self.spin_y.setValue(int(self.settings.get("offset_y", 12)))
        self.spin_y.setStyleSheet(get_spinbox_qss(accent, mode))
        self.spin_y.valueChanged.connect(lambda v: self.settings.update_settings({"offset_y": v}))
        form.addRow(self.lbl_f_y, self.spin_y)

        # Hover Delay
        self.lbl_f_hover = create_form_label("Hover Expansion Delay:", pal)
        self.spin_hover = QSpinBox()
        self.spin_hover.setRange(50, 1000)
        self.spin_hover.setSuffix(" ms")
        self.spin_hover.setValue(int(self.settings.get("hover_delay_ms", 300)))
        self.spin_hover.setStyleSheet(get_spinbox_qss(accent, mode))
        self.spin_hover.valueChanged.connect(lambda v: self.settings.update_settings({"hover_delay_ms": v}))
        form.addRow(self.lbl_f_hover, self.spin_hover)

        c_box.addLayout(form)
        layout.addWidget(card)

        # Tip Card
        tip_card = GlassPanel(category_key="default", corner_radius=12)
        t_box = QVBoxLayout(tip_card)
        t_box.setContentsMargins(14, 10, 14, 10)
        self.lbl_tip = QLabel("💡 Quick Drag: You can also hold the RIGHT mouse button anywhere on the compact floating island and drag it directly to reposition it on screen!")
        self.lbl_tip.setStyleSheet(f"color: {pal['text_secondary']}; font-size: 10px; line-height: 1.3; background: transparent; border: none; border-radius: 0px;")
        self.lbl_tip.setWordWrap(True)
        t_box.addWidget(self.lbl_tip)
        layout.addWidget(tip_card)

        layout.addStretch()

    def apply_theme(self, accent_color: str, mode: str = "dark"):
        pal = THEME_PALETTES.get(mode, THEME_PALETTES["dark"])
        for gp in self.findChildren(GlassPanel):
            gp.apply_theme(accent_color, mode)
        for lbl in (self.lbl_f_pos, self.lbl_f_mon, self.lbl_f_x, self.lbl_f_y, self.lbl_f_hover):
            lbl.setStyleSheet(f"color: {pal['text_primary']}; font-size: 11px; font-weight: 600; background: transparent; border: none; border-radius: 0px;")
        if hasattr(self, 'lbl_tip'):
            self.lbl_tip.setStyleSheet(f"color: {pal['text_secondary']}; font-size: 10px; line-height: 1.3; background: transparent; border: none; border-radius: 0px;")
        self.combo_pos.setStyleSheet(get_combobox_qss(accent_color, mode))
        self.combo_mon.setStyleSheet(get_combobox_qss(accent_color, mode))
        self.spin_x.setStyleSheet(get_spinbox_qss(accent_color, mode))
        self.spin_y.setStyleSheet(get_spinbox_qss(accent_color, mode))
        self.spin_hover.setStyleSheet(get_spinbox_qss(accent_color, mode))


# =============================================================================
# 4. HOME DASHBOARD MODULES CONFIGURATION
# =============================================================================
class HomeModulesConfigWidget(QWidget):
    """Configures which card modules render inside the island's Home tab."""
    def __init__(self, settings: SettingsManager, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        accent = resolve_accent_color(self.settings) if self.settings else "#38bdf8"
        mode = self.settings.get("theme_mode", "dark") if self.settings else "dark"
        pal = THEME_PALETTES.get(mode, THEME_PALETTES["dark"])

        card = GlassPanel(category_key="settings", corner_radius=12)
        c_box = QVBoxLayout(card)
        c_box.setContentsMargins(16, 14, 16, 14)
        c_box.setSpacing(10)

        lbl_title = QLabel("🏠 Home Dashboard Card Modules")
        lbl_title.setStyleSheet(f"color: {accent}; font-size: 13px; font-weight: 800; background: transparent;")
        lbl_desc = QLabel("Toggle which card sections are rendered on the compact island's Home dashboard.")
        lbl_desc.setStyleSheet(f"color: {pal['text_secondary']}; font-size: 10.5px; background: transparent;")
        c_box.addWidget(lbl_title)
        c_box.addWidget(lbl_desc)

        self.home_toggles = [
            ("show_home_alarms", "🔔 Active Alarms Card", "Shows upcoming alarms and quick snooze actions on Home"),
            ("show_home_timetable", "📅 Daily Timetable Schedule", "Shows today's daily routine checklist and progress"),
            ("show_home_calendar", "🗓️ Calendar Mini-Planner", "Shows upcoming calendar events and day overview"),
            ("show_home_notes", "📝 Quick Notes Preview", "Shows the most recently pinned note snippet"),
            ("show_home_dropzone", "📥 File Drop Zone && Shelf", "Quick drag-and-drop target to stash files"),
            ("show_home_pomodoro", "🍅 Pomodoro Focus Timer", "Shows 25-minute focus session timer in Home header"),
            ("show_home_now_playing", "🎵 Media Transport && Now Playing", "Shows active music/video playback and media controls"),
            ("show_home_notifications", "🔔 Recent Notifications Feed", "Shows latest unread Windows notifications summary"),
        ]

        grid = QGridLayout()
        grid.setSpacing(10)
        self.desc_labels = []

        for idx, (setting_key, label_txt, desc_txt) in enumerate(self.home_toggles):
            escaped_label = label_txt.replace("&", "&&") if "&&" not in label_txt else label_txt
            chk = QCheckBox(escaped_label)
            chk.setChecked(bool(self.settings.get(setting_key, True)))
            chk.setStyleSheet(get_checkbox_qss(accent, mode))
            chk.toggled.connect(lambda val, k=setting_key: self.settings.update_settings({k: val}))

            desc = QLabel(desc_txt)
            desc.setStyleSheet(f"color: {pal['text_muted']}; font-size: 9.5px; margin-left: 22px; background: transparent; border: none; border-radius: 0px;")
            self.desc_labels.append(desc)

            box = QVBoxLayout()
            box.setSpacing(1)
            box.addWidget(chk)
            box.addWidget(desc)

            r = idx // 2
            c = idx % 2
            grid.addLayout(box, r, c)

        c_box.addLayout(grid)
        layout.addWidget(card)
        layout.addStretch()

    def apply_theme(self, accent_color: str, mode: str = "dark"):
        pal = THEME_PALETTES.get(mode, THEME_PALETTES["dark"])
        for gp in self.findChildren(GlassPanel):
            gp.apply_theme(accent_color, mode)
        for chk in self.findChildren(QCheckBox):
            chk.setStyleSheet(get_checkbox_qss(accent_color, mode))
        if hasattr(self, 'desc_labels'):
            for d in self.desc_labels:
                d.setStyleSheet(f"color: {pal['text_muted']}; font-size: 9.5px; margin-left: 22px; background: transparent; border: none; border-radius: 0px;")


# =============================================================================
# 5. ALARMS, SOUNDS & NOTIFICATIONS CONFIGURATION
# =============================================================================
class AlarmsNotifsConfigWidget(QWidget):
    """Configures alarm audio themes, auto-dismiss timers, 12h/24h, and priority notification popups."""
    def __init__(self, settings: SettingsManager, storage: StorageManager = None, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.storage = storage or StorageManager()
        self.init_ui()

    def init_ui(self):
        accent = resolve_accent_color(self.settings) if self.settings else "#38bdf8"
        mode = self.settings.get("theme_mode", "dark") if self.settings else "dark"
        pal = THEME_PALETTES.get(mode, THEME_PALETTES["dark"])

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        scroll.viewport().setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        scroll.viewport().setAutoFillBackground(False)
        scroll.setStyleSheet(f"QScrollArea, QScrollArea > QWidget > QWidget {{ background: transparent; border: none; }} {get_scrollbar_qss(accent, mode)}")

        container = QWidget()
        container.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        container.setStyleSheet("background: transparent; border: none;")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        # Panel: Alarm & Sound Audio
        alarm_card = GlassPanel(category_key="alarms", corner_radius=12)
        a_box = QVBoxLayout(alarm_card)
        a_box.setContentsMargins(16, 14, 16, 14)
        a_box.setSpacing(10)

        lbl_a_title = QLabel("🔔 Alarm Audio & Clock Preferences")
        lbl_a_title.setStyleSheet(f"color: {accent}; font-size: 13px; font-weight: 800; background: transparent;")
        a_box.addWidget(lbl_a_title)

        form = QFormLayout()
        form.setSpacing(12)

        # Time Format
        self.lbl_f_clock = create_form_label("Clock Display Format:", pal)
        self.chk_12h = QCheckBox("Use 12-Hour AM/PM Format (Uncheck for 24-Hour Military Time)")
        self.chk_12h.setChecked(bool(self.settings.get("time_format_12h", True)))
        self.chk_12h.setStyleSheet(get_checkbox_qss(accent, mode))
        self.chk_12h.toggled.connect(lambda v: self.settings.update_settings({"time_format_12h": v}))
        form.addRow(self.lbl_f_clock, self.chk_12h)

        # Auto Dismiss
        self.lbl_f_dismiss = create_form_label("Alarm Auto-Dismiss:", pal)
        self.combo_dismiss = QComboBox()
        self.combo_dismiss.addItem("15 Seconds", 15)
        self.combo_dismiss.addItem("30 Seconds (Default)", 30)
        self.combo_dismiss.addItem("60 Seconds", 60)
        self.combo_dismiss.addItem("2 Minutes", 120)
        self.combo_dismiss.addItem("Never (Requires Manual Dismiss)", 0)
        cur_d = int(self.settings.get("alarm_autodismiss_seconds", 30))
        idx = self.combo_dismiss.findData(cur_d)
        if idx >= 0:
            self.combo_dismiss.setCurrentIndex(idx)
        self.combo_dismiss.setStyleSheet(get_combobox_qss(accent, mode))
        self.combo_dismiss.currentIndexChanged.connect(lambda: self.settings.update_settings({"alarm_autodismiss_seconds": self.combo_dismiss.currentData()}))
        form.addRow(self.lbl_f_dismiss, self.combo_dismiss)

        a_box.addLayout(form)
        layout.addWidget(alarm_card)

        # Panel: Priority Notification Popups & Real Monitored App Manager
        notif_card = GlassPanel(category_key="settings", corner_radius=12)
        n_box = QVBoxLayout(notif_card)
        n_box.setContentsMargins(16, 14, 16, 14)
        n_box.setSpacing(10)

        lbl_n_title = QLabel("📢 Priority Notification Takeover Popups")
        lbl_n_title.setStyleSheet(f"color: {accent}; font-size: 13px; font-weight: 800; background: transparent;")
        n_box.addWidget(lbl_n_title)

        self.chk_notif_popup = QCheckBox("Enable Full-Island Notification Takeover Popups")
        self.chk_notif_popup.setChecked(bool(self.settings.get("notification_popup_enabled", True)))
        self.chk_notif_popup.setStyleSheet(get_checkbox_qss(accent, mode))
        self.chk_notif_popup.toggled.connect(lambda v: self.settings.update_settings({"notification_popup_enabled": v}))
        n_box.addWidget(self.chk_notif_popup)

        self.chk_suppress_fs = QCheckBox("Suppress Notification Popups when Full-Screen Apps/Games are active")
        self.chk_suppress_fs.setChecked(bool(self.settings.get("suppress_popups_in_fullscreen", True)))
        self.chk_suppress_fs.setStyleSheet(get_checkbox_qss(accent, mode))
        self.chk_suppress_fs.toggled.connect(lambda v: self.settings.update_settings({"suppress_popups_in_fullscreen": v}))
        n_box.addWidget(self.chk_suppress_fs)

        self.chk_pill_toasts = QCheckBox("Show in-pill status toasts (charging, battery, clipboard events)")
        self.chk_pill_toasts.setChecked(bool(self.settings.get("enable_system_pill_toasts", True)))
        self.chk_pill_toasts.setStyleSheet(get_checkbox_qss(accent, mode))
        self.chk_pill_toasts.toggled.connect(lambda v: self.settings.update_settings({"enable_system_pill_toasts": v}))
        n_box.addWidget(self.chk_pill_toasts)

        # Monitored Apps Header & Controls
        lbl_apps_head = QLabel("📱 Monitored Priority Applications (.exe Control)")
        lbl_apps_head.setStyleSheet(f"color: {accent}; font-size: 11.5px; font-weight: 800; margin-top: 6px; background: transparent;")
        n_box.addWidget(lbl_apps_head)

        lbl_apps_desc = QLabel("Select executable files (.exe) or pick active running processes to control notification takeover popups reliably without typing errors.")
        lbl_apps_desc.setStyleSheet(f"color: {pal['text_secondary']}; font-size: 9.5px; font-weight: 500; background: transparent;")
        n_box.addWidget(lbl_apps_desc)

        # Action Buttons Row
        act_row = QHBoxLayout()
        act_row.setSpacing(6)

        btn_add_exe = QPushButton("📁 Browse .exe File")
        btn_add_exe.setFixedHeight(24)
        btn_add_exe.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_add_exe.setStyleSheet(f"QPushButton {{ background-color: {accent}; color: #ffffff; border: none; border-radius: 4px; font-size: 9.5px; font-weight: bold; padding: 0 8px; }}")
        btn_add_exe.clicked.connect(self.add_exe_file)

        btn_pick_running = QPushButton("⚡ Pick Running App")
        btn_pick_running.setFixedHeight(24)
        btn_pick_running.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_pick_running.setStyleSheet(f"QPushButton {{ background-color: {pal['sub_btn_bg']}; color: {pal['sub_btn_text']}; border-radius: 4px; border: 1px solid {pal['sub_btn_border']}; font-size: 9.5px; font-weight: bold; padding: 0 8px; }}")
        btn_pick_running.clicked.connect(self.add_running_app)

        act_row.addWidget(btn_add_exe)
        act_row.addWidget(btn_pick_running)
        act_row.addStretch()
        n_box.addLayout(act_row)

        # Container for Monitored App Cards List
        self.apps_scroll = QScrollArea()
        self.apps_scroll.setWidgetResizable(True)
        self.apps_scroll.setMinimumHeight(132)
        self.apps_scroll.setMaximumHeight(180)
        self.apps_scroll.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.apps_scroll.viewport().setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.apps_scroll.viewport().setAutoFillBackground(False)
        self.apps_scroll.setStyleSheet(f"QScrollArea, QScrollArea > QWidget > QWidget {{ background: transparent; border: none; }} {get_scrollbar_qss(accent, mode)}")

        self.apps_container_widget = QWidget()
        self.apps_container_widget.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.apps_container_widget.setStyleSheet("background: transparent; border: none;")
        self.apps_container_layout = QVBoxLayout(self.apps_container_widget)
        self.apps_container_layout.setContentsMargins(0, 0, 0, 0)
        self.apps_container_layout.setSpacing(4)

        self.render_priority_apps_list()

        self.apps_scroll.setWidget(self.apps_container_widget)
        self.apps_container_widget.setAutoFillBackground(False)
        n_box.addWidget(self.apps_scroll)

        layout.addWidget(notif_card)

        # Panel: Custom Brand Assets (Logo & Watermark Image Files)
        brand_card = GlassPanel(category_key="settings", corner_radius=12)
        b_box = QVBoxLayout(brand_card)
        b_box.setContentsMargins(16, 14, 16, 14)
        b_box.setSpacing(10)

        lbl_b_title = QLabel("🖼️ Brand Assets (Custom Logo & Watermark Images)")
        lbl_b_title.setStyleSheet(f"color: {accent}; font-size: 13px; font-weight: 800; background: transparent;")
        b_box.addWidget(lbl_b_title)

        # Custom Logo Row
        logo_row = QHBoxLayout()
        logo_row.setSpacing(6)
        self.logo_path_edit = QLineEdit()
        self.logo_path_edit.setFixedHeight(24)
        self.logo_path_edit.setReadOnly(True)
        cur_logo = self.settings.get("custom_logo_path", "")
        self.logo_path_edit.setText(cur_logo if cur_logo else "Default Built-in 3D Glass Logo")
        self.logo_path_edit.setStyleSheet(get_lineedit_qss(accent, mode))

        btn_upload_logo = QPushButton("📁 Browse Custom Logo")
        btn_upload_logo.setFixedHeight(24)
        btn_upload_logo.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_upload_logo.setStyleSheet(f"QPushButton {{ background-color: {accent}; color: #ffffff; border-radius: 4px; font-size: 9.5px; font-weight: bold; padding: 0 8px; }}")
        btn_upload_logo.clicked.connect(self.browse_custom_logo)

        btn_reset_logo = QPushButton("🔄 Reset Logo")
        btn_reset_logo.setFixedHeight(24)
        btn_reset_logo.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_reset_logo.setStyleSheet(f"QPushButton {{ background-color: {pal['sub_btn_bg']}; color: {pal['sub_btn_text']}; border-radius: 4px; border: 1px solid {pal['sub_btn_border']}; font-size: 9.5px; padding: 0 8px; }}")
        btn_reset_logo.clicked.connect(self.reset_custom_logo)

        logo_row.addWidget(self.logo_path_edit, 1)
        logo_row.addWidget(btn_upload_logo)
        logo_row.addWidget(btn_reset_logo)

        # Custom Watermark Row
        watermark_row = QHBoxLayout()
        watermark_row.setSpacing(6)
        self.watermark_path_edit = QLineEdit()
        self.watermark_path_edit.setFixedHeight(24)
        self.watermark_path_edit.setReadOnly(True)
        cur_wm = self.settings.get("custom_watermark_path", "")
        self.watermark_path_edit.setText(cur_wm if cur_wm else "Default Transparent Watermark")
        self.watermark_path_edit.setStyleSheet(get_lineedit_qss(accent, mode))

        btn_upload_watermark = QPushButton("📁 Browse Custom Watermark")
        btn_upload_watermark.setFixedHeight(24)
        btn_upload_watermark.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_upload_watermark.setStyleSheet(f"QPushButton {{ background-color: {accent}; color: #ffffff; border-radius: 4px; font-size: 9.5px; font-weight: bold; padding: 0 8px; }}")
        btn_upload_watermark.clicked.connect(self.browse_custom_watermark)

        btn_reset_watermark = QPushButton("🔄 Reset Watermark")
        btn_reset_watermark.setFixedHeight(24)
        btn_reset_watermark.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_reset_watermark.setStyleSheet(f"QPushButton {{ background-color: {pal['sub_btn_bg']}; color: {pal['sub_btn_text']}; border-radius: 4px; border: 1px solid {pal['sub_btn_border']}; font-size: 9.5px; padding: 0 8px; }}")
        btn_reset_watermark.clicked.connect(self.reset_custom_watermark)

        watermark_row.addWidget(self.watermark_path_edit, 1)
        watermark_row.addWidget(btn_upload_watermark)
        watermark_row.addWidget(btn_reset_watermark)

        b_box.addLayout(logo_row)
        b_box.addLayout(watermark_row)
        layout.addWidget(brand_card)

        layout.addStretch()

        scroll.setWidget(container)
        container.setAutoFillBackground(False)
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll)

    def browse_custom_logo(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select App Logo Image", "", "Images (*.png *.jpg *.jpeg *.ico *.svg)"
        )
        if file_path:
            self.settings.update_settings({"custom_logo_path": file_path})
            self.logo_path_edit.setText(file_path)

    def reset_custom_logo(self):
        self.settings.update_settings({"custom_logo_path": ""})
        self.logo_path_edit.setText("Default Built-in 3D Glass Logo")

    def browse_custom_watermark(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Background Watermark Image", "", "Images (*.png *.jpg *.jpeg *.ico *.svg)"
        )
        if file_path:
            self.settings.update_settings({"custom_watermark_path": file_path})
            self.watermark_path_edit.setText(file_path)

    def reset_custom_watermark(self):
        self.settings.update_settings({"custom_watermark_path": ""})
        self.watermark_path_edit.setText("Default Transparent Watermark")

    def render_priority_apps_list(self):
        if not hasattr(self, 'apps_container_layout'):
            return
        for i in reversed(range(self.apps_container_layout.count())):
            item = self.apps_container_layout.itemAt(i)
            if item and item.widget():
                item.widget().deleteLater()

        accent = resolve_accent_color(self.settings) if self.settings else "#38bdf8"
        mode = self.settings.get("theme_mode", "dark") if self.settings else "dark"
        pal = THEME_PALETTES.get(mode, THEME_PALETTES["dark"])

        raw_apps = self.settings.get("popup_notification_apps", ["WhatsApp", "Slack", "Microsoft Teams", "Discord", "Telegram", "Mail", "Outlook", "Chrome", "Edge"])
        normalized_apps = []

        for item in raw_apps:
            if isinstance(item, dict):
                normalized_apps.append(item)
            elif isinstance(item, str) and item.strip():
                name = item.strip()
                normalized_apps.append({"name": name, "exe_path": f"{name.lower()}.exe", "enabled": True})

        for idx, app_info in enumerate(normalized_apps):
            app_card = GlassPanel(category_key="settings", corner_radius=6)
            ac_layout = QHBoxLayout(app_card)
            ac_layout.setContentsMargins(10, 6, 10, 6)
            ac_layout.setSpacing(8)

            chk_enable = QCheckBox()
            chk_enable.setChecked(app_info.get("enabled", True))
            chk_enable.setStyleSheet(get_checkbox_qss(accent, mode))
            chk_enable.toggled.connect(lambda chk, i=idx: self.toggle_app_enabled(i, chk))

            lbl_name = QLabel(app_info.get("name", "Unknown App"))
            lbl_name.setStyleSheet(f"color: {pal['text_primary']}; font-size: 10.5px; font-weight: 700; background: transparent;")

            lbl_exe = QLabel(app_info.get("exe_path", ""))
            lbl_exe.setStyleSheet(f"color: {pal['text_secondary']}; font-size: 9px; font-weight: 500; background: transparent;")

            info_box = QVBoxLayout()
            info_box.setSpacing(1)
            info_box.addWidget(lbl_name)
            info_box.addWidget(lbl_exe)

            btn_del = QPushButton("🗑️")
            btn_del.setFixedSize(22, 22)
            btn_del.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_del.setStyleSheet("QPushButton { background: rgba(239, 68, 68, 0.15); color: #ef4444; border: 1px solid rgba(239, 68, 68, 0.3); border-radius: 4px; font-size: 9.5px; } QPushButton:hover { background: #ef4444; color: #ffffff; }")
            btn_del.clicked.connect(lambda _, i=idx: self.remove_priority_app(i))

            ac_layout.addWidget(chk_enable)
            ac_layout.addLayout(info_box, 1)
            ac_layout.addWidget(btn_del)

            self.apps_container_layout.addWidget(app_card)

    def toggle_app_enabled(self, index: int, enabled: bool):
        raw_apps = list(self.settings.get("popup_notification_apps", []))
        if 0 <= index < len(raw_apps):
            if isinstance(raw_apps[index], dict):
                raw_apps[index]["enabled"] = enabled
            elif isinstance(raw_apps[index], str):
                name = raw_apps[index]
                raw_apps[index] = {"name": name, "exe_path": f"{name.lower()}.exe", "enabled": enabled}
            self.settings.update_settings({"popup_notification_apps": raw_apps})

    def remove_priority_app(self, index: int):
        raw_apps = list(self.settings.get("popup_notification_apps", []))
        if 0 <= index < len(raw_apps):
            raw_apps.pop(index)
            self.settings.update_settings({"popup_notification_apps": raw_apps})
            self.render_priority_apps_list()

    def add_exe_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Application Executable (.exe)", "C:\\Program Files", "Executable Files (*.exe);;All Files (*.*)"
        )
        if file_path:
            exe_name = os.path.basename(file_path)
            app_name = os.path.splitext(exe_name)[0].capitalize()
            raw_apps = list(self.settings.get("popup_notification_apps", []))
            raw_apps.append({"name": app_name, "exe_path": file_path, "enabled": True})
            self.settings.update_settings({"popup_notification_apps": raw_apps})
            self.render_priority_apps_list()

    def add_running_app(self):
        try:
            import psutil
            procs = set()
            for p in psutil.process_iter(['name']):
                try:
                    name = p.info['name']
                    if name and name.endswith('.exe') and not name.lower().startswith(('svchost', 'system', 'idle', 'conhost', 'explorer', 'python', 'py.exe', 'cmd.exe')):
                        procs.add(name)
                except Exception:
                    pass
            sorted_procs = sorted(list(procs))
            if sorted_procs:
                item, ok = QInputDialog.getItem(self, "Add Running Process", "Select Active Running App Process:", sorted_procs, 0, False)
                if ok and item:
                    app_name = os.path.splitext(item)[0].capitalize()
                    raw_apps = list(self.settings.get("popup_notification_apps", []))
                    raw_apps.append({"name": app_name, "exe_path": item, "enabled": True})
                    self.settings.update_settings({"popup_notification_apps": raw_apps})
                    self.render_priority_apps_list()
        except Exception as e:
            print(f"[Add Running App Exception]: {e}")

    def apply_theme(self, accent_color: str, mode: str = "dark"):
        pal = THEME_PALETTES.get(mode, THEME_PALETTES["dark"])
        for gp in self.findChildren(GlassPanel):
            gp.apply_theme(accent_color, mode)
        for sc in self.findChildren(QScrollArea):
            sc.setStyleSheet(f"QScrollArea, QScrollArea > QWidget > QWidget {{ background: transparent; border: none; }} {get_scrollbar_qss(accent_color, mode)}")
        self.lbl_f_clock.setStyleSheet(f"color: {pal['text_primary']}; font-size: 11px; font-weight: 600; background: transparent; border: none; border-radius: 0px;")
        self.lbl_f_dismiss.setStyleSheet(f"color: {pal['text_primary']}; font-size: 11px; font-weight: 600; background: transparent; border: none; border-radius: 0px;")
        self.combo_dismiss.setStyleSheet(get_combobox_qss(accent_color, mode))
        for chk in self.findChildren(QCheckBox):
            chk.setStyleSheet(get_checkbox_qss(accent_color, mode))


# =============================================================================
# 6. APP LAUNCHER SHORTCUTS CONFIGURATION
# =============================================================================
class AppLauncherConfigWidget(QWidget):
    """Configures installed app shortcuts and executables shown in the island's App Launcher tab."""
    def __init__(self, storage: StorageManager, settings: SettingsManager, parent=None):
        super().__init__(parent)
        self.storage = storage
        self.settings = settings
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        accent = resolve_accent_color(self.settings) if self.settings else "#38bdf8"
        mode = self.settings.get("theme_mode", "dark") if self.settings else "dark"
        pal = THEME_PALETTES.get(mode, THEME_PALETTES["dark"])

        # Header / Add Shortcut Card
        add_card = GlassPanel(category_key="settings", corner_radius=12)
        a_box = QVBoxLayout(add_card)
        a_box.setContentsMargins(16, 12, 16, 12)
        a_box.setSpacing(8)

        lbl_title = QLabel("🚀 Island App Launcher Shortcuts Manager")
        lbl_title.setStyleSheet(f"color: {accent}; font-size: 13px; font-weight: 800; background: transparent;")
        lbl_desc = QLabel("Add, remove, and manage executable application shortcuts registered on the compact island's App Launcher grid.")
        lbl_desc.setStyleSheet(f"color: {pal['text_secondary']}; font-size: 10px; background: transparent;")
        a_box.addWidget(lbl_title)
        a_box.addWidget(lbl_desc)

        form_row = QHBoxLayout()
        self.txt_app_name = QLineEdit()
        self.txt_app_name.setPlaceholderText("App Name (e.g. VS Code)")
        self.txt_app_name.setStyleSheet(get_lineedit_qss(accent, mode))

        self.txt_app_path = QLineEdit()
        self.txt_app_path.setPlaceholderText("Executable Path (.exe) or URL")
        self.txt_app_path.setStyleSheet(get_lineedit_qss(accent, mode))

        btn_browse = QPushButton("📁 Browse...")
        btn_browse.setFixedHeight(28)
        btn_browse.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_browse.setStyleSheet(f"QPushButton {{ background: {pal['input_bg']}; color: {pal['text_primary']}; border: 1px solid {pal['input_border']}; border-radius: 5px; font-size: 10px; font-weight: bold; padding: 0 10px; }} QPushButton:hover {{ border: 1px solid {accent}; }}")
        btn_browse.clicked.connect(self.browse_app_file)

        btn_add = QPushButton("➕ Add Shortcut")
        btn_add.setFixedHeight(28)
        btn_add.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_add.setStyleSheet(f"QPushButton {{ background-color: {accent}; color: {get_accent_text_color(accent)}; border-radius: 5px; font-size: 10px; font-weight: 800; padding: 0 12px; }}")
        btn_add.clicked.connect(self.add_app_shortcut)

        form_row.addWidget(self.txt_app_name, 1)
        form_row.addWidget(self.txt_app_path, 2)
        form_row.addWidget(btn_browse)
        form_row.addWidget(btn_add)
        a_box.addLayout(form_row)
        layout.addWidget(add_card)

        # Configured Shortcuts List Card
        list_card = GlassPanel(category_key="default", corner_radius=12)
        l_box = QVBoxLayout(list_card)
        l_box.setContentsMargins(14, 12, 14, 12)
        l_box.setSpacing(8)

        lbl_list = QLabel("Configured Island Shortcuts:")
        lbl_list.setStyleSheet(f"color: {pal['text_primary']}; font-size: 11px; font-weight: bold; background: transparent;")
        l_box.addWidget(lbl_list)

        self.apps_list = QListWidget()
        self.apps_list.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.apps_list.viewport().setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.apps_list.viewport().setAutoFillBackground(False)
        self.apps_list.setSpacing(4)
        self.apps_list.setStyleSheet(get_list_widget_qss(accent, mode))
        l_box.addWidget(self.apps_list)

        layout.addWidget(list_card, 1)
        self.load_shortcuts()

    def browse_app_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Application Executable", "", "Executables (*.exe *.bat *.cmd);;All Files (*.*)")
        if path:
            self.txt_app_path.setText(path)
            if not self.txt_app_name.text().strip():
                base = os.path.splitext(os.path.basename(path))[0]
                self.txt_app_name.setText(base.replace("_", " ").title())

    def add_app_shortcut(self):
        name = self.txt_app_name.text().strip()
        path = self.txt_app_path.text().strip()
        if not name or not path:
            return

        apps = self.storage.load_app_launcher()
        new_app = {
            "name": name,
            "path": path,
            "icon": "🚀",
            "added_at": None
        }
        apps.append(new_app)
        self.storage.save_app_launcher(apps)
        self.txt_app_name.clear()
        self.txt_app_path.clear()
        self.load_shortcuts()

        # Smooth entrance animation for the newly added shortcut
        if self.apps_list.count() > 0:
            last_item = self.apps_list.item(self.apps_list.count() - 1)
            last_widget = self.apps_list.itemWidget(last_item)
            if last_widget:
                try:
                    effect = QGraphicsOpacityEffect(last_widget)
                    last_widget.setGraphicsEffect(effect)
                    effect.setOpacity(0.0)
                    anim = QPropertyAnimation(effect, b"opacity", self)
                    anim.setDuration(160)
                    anim.setStartValue(0.0)
                    anim.setEndValue(1.0)
                    anim.setEasingCurve(QEasingCurve.Type.OutQuad)
                    anim.finished.connect(lambda: last_widget.setGraphicsEffect(None))
                    anim.start()
                    self._add_anim = anim
                except Exception:
                    pass

    def remove_app_shortcut(self, index: int):
        apps = self.storage.load_app_launcher()
        if 0 <= index < len(apps):
            # Smooth fade-out exit animation before removal
            item = self.apps_list.item(index)
            widget = self.apps_list.itemWidget(item) if item else None
            if widget:
                try:
                    effect = QGraphicsOpacityEffect(widget)
                    widget.setGraphicsEffect(effect)
                    anim = QPropertyAnimation(effect, b"opacity", self)
                    anim.setDuration(140)
                    anim.setStartValue(1.0)
                    anim.setEndValue(0.0)
                    anim.setEasingCurve(QEasingCurve.Type.OutQuad)

                    def on_remove_anim_done():
                        cur_apps = self.storage.load_app_launcher()
                        if 0 <= index < len(cur_apps):
                            cur_apps.pop(index)
                            self.storage.save_app_launcher(cur_apps)
                        self.load_shortcuts()

                    anim.finished.connect(on_remove_anim_done)
                    anim.start()
                    self._del_anim = anim
                    return
                except Exception:
                    pass

            apps.pop(index)
            self.storage.save_app_launcher(apps)
            self.load_shortcuts()

    def load_shortcuts(self):
        # Cleanly tear down existing item widgets
        while self.apps_list.count():
            item = self.apps_list.takeItem(0)
            if item:
                w = self.apps_list.itemWidget(item)
                if w:
                    self.apps_list.removeItemWidget(item)
                    w.setParent(None)
                    w.deleteLater()
        self.apps_list.clear()

        for child in self.apps_list.viewport().findChildren(QWidget):
            child.setParent(None)
            child.deleteLater()

        mode = self.settings.get("theme_mode", "dark") if self.settings else "dark"
        pal = THEME_PALETTES.get(mode, THEME_PALETTES["dark"])
        apps = self.storage.load_app_launcher()

        for idx, app_info in enumerate(apps):
            item = QListWidgetItem(self.apps_list)
            item.setSizeHint(QSize(0, 40))

            row = QWidget()
            row.setStyleSheet("background: transparent; border: none; outline: none;")
            r_box = QHBoxLayout(row)
            r_box.setContentsMargins(10, 2, 10, 2)
            r_box.setSpacing(10)

            lbl_name = QLabel(f"🚀 {app_info.get('name', 'App')}")
            lbl_name.setStyleSheet(f"color: {pal['text_primary']}; font-size: 11px; font-weight: bold; background: transparent; border: none; outline: none;")

            lbl_path = QLabel(app_info.get('path', ''))
            lbl_path.setStyleSheet(f"color: {pal['text_muted']}; font-size: 9.5px; background: transparent; border: none; outline: none;")

            btn_del = QPushButton("🗑️ Remove")
            btn_del.setFixedHeight(22)
            btn_del.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_del.setStyleSheet("QPushButton { background: rgba(239, 68, 68, 0.15); color: #ef4444; border: 1px solid #ef4444; border-radius: 4px; font-size: 9.5px; font-weight: bold; padding: 0 8px; } QPushButton:hover { background: #ef4444; color: #ffffff; }")
            btn_del.clicked.connect(lambda _, i=idx: self.remove_app_shortcut(i))

            r_box.addWidget(lbl_name)
            r_box.addWidget(lbl_path, 1)
            r_box.addWidget(btn_del)

            self.apps_list.addItem(item)
            self.apps_list.setItemWidget(item, row)

        self.apps_list.viewport().update()
        self.apps_list.update()
        self.update()

    def apply_theme(self, accent_color: str, mode: str = "dark"):
        for gp in self.findChildren(GlassPanel):
            gp.apply_theme(accent_color, mode)
        self.load_shortcuts()


# =============================================================================
# 7. SYSTEM INTEGRATION & BACKUPS CONFIGURATION
# =============================================================================
class SystemBackupConfigWidget(QWidget):
    """Configures Windows autostart, theme sync, config export/import, and factory reset."""
    def __init__(self, settings: SettingsManager, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        accent = resolve_accent_color(self.settings) if self.settings else "#38bdf8"
        mode = self.settings.get("theme_mode", "dark") if self.settings else "dark"
        pal = THEME_PALETTES.get(mode, THEME_PALETTES["dark"])

        # Panel: Windows Startup & Integration
        win_card = GlassPanel(category_key="settings", corner_radius=12)
        w_box = QVBoxLayout(win_card)
        w_box.setContentsMargins(16, 14, 16, 14)
        w_box.setSpacing(10)

        lbl_w_title = QLabel("⚙️ Windows Integration & Startup")
        lbl_w_title.setStyleSheet(f"color: {accent}; font-size: 13px; font-weight: 800; background: transparent;")
        w_box.addWidget(lbl_w_title)

        self.chk_startup = QCheckBox("Start Dlives automatically when Windows boots up")
        self.chk_startup.setChecked(bool(self.settings.get("start_with_windows", False)))
        self.chk_startup.setStyleSheet(get_checkbox_qss(accent, mode))
        self.chk_startup.toggled.connect(lambda v: self.settings.set_start_with_windows(v))
        w_box.addWidget(self.chk_startup)

        self.chk_sync_win_theme = QCheckBox("Auto-sync Theme with Windows Light/Dark system appearance")
        self.chk_sync_win_theme.setChecked(bool(self.settings.get("sync_windows_theme", False)))
        self.chk_sync_win_theme.setStyleSheet(get_checkbox_qss(accent, mode))
        self.chk_sync_win_theme.toggled.connect(lambda v: self.settings.update_settings({"sync_windows_theme": v}))
        w_box.addWidget(self.chk_sync_win_theme)

        layout.addWidget(win_card)

        # Panel: Configuration Backups
        bak_card = GlassPanel(category_key="default", corner_radius=12)
        b_box = QVBoxLayout(bak_card)
        b_box.setContentsMargins(16, 14, 16, 14)
        b_box.setSpacing(10)

        lbl_b_title = QLabel("📦 Backup, Restore & Reset")
        lbl_b_title.setStyleSheet(f"color: {accent}; font-size: 13px; font-weight: 800; background: transparent;")
        b_box.addWidget(lbl_b_title)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        self.btn_export = QPushButton("📤 Export Settings to JSON")
        self.btn_import = QPushButton("📥 Import Settings from JSON")
        self.btn_reset_all = QPushButton("🔄 Reset All Preferences to Defaults")

        for b in (self.btn_export, self.btn_import):
            b.setFixedHeight(30)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setStyleSheet(f"QPushButton {{ background: {pal['input_bg']}; color: {pal['text_primary']}; border: 1px solid {pal['input_border']}; border-radius: 5px; font-size: 10.5px; font-weight: bold; padding: 0 14px; }} QPushButton:hover {{ border: 1px solid {accent}; }}")

        self.btn_reset_all.setFixedHeight(30)
        self.btn_reset_all.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_reset_all.setStyleSheet("QPushButton { background: rgba(239, 68, 68, 0.15); color: #ef4444; border: 1px solid #ef4444; border-radius: 5px; font-size: 10.5px; font-weight: bold; padding: 0 14px; } QPushButton:hover { background: #ef4444; color: #ffffff; }")

        self.btn_export.clicked.connect(self.export_settings)
        self.btn_import.clicked.connect(self.import_settings)
        self.btn_reset_all.clicked.connect(self.reset_all_settings)

        btn_row.addWidget(self.btn_export)
        btn_row.addWidget(self.btn_import)
        btn_row.addStretch()
        btn_row.addWidget(self.btn_reset_all)
        b_box.addLayout(btn_row)

        layout.addWidget(bak_card)
        layout.addStretch()

    def export_settings(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Export Dlives Preferences", "Dlives_Config.json", "JSON Files (*.json)")
        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(self.settings.settings, f, indent=2)
                QMessageBox.information(self, "Export Complete", "Preferences successfully exported to JSON file.")
            except Exception as e:
                QMessageBox.warning(self, "Export Error", f"Failed to export preferences: {e}")

    def import_settings(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Import Dlives Preferences", "", "JSON Files (*.json)")
        if file_path:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    self.settings.update_settings(data)
                    QMessageBox.information(self, "Import Complete", "Preferences imported and applied live successfully!")
            except Exception as e:
                QMessageBox.warning(self, "Import Error", f"Failed to import preferences: {e}")

    def reset_all_settings(self):
        reply = QMessageBox.question(self, "Reset All Preferences", "Are you sure you want to reset all Dlives preferences to factory defaults?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.settings.reset_defaults()
            QMessageBox.information(self, "Reset Complete", "All preferences have been reset to factory defaults.")

    def apply_theme(self, accent_color: str, mode: str = "dark"):
        for gp in self.findChildren(GlassPanel):
            gp.apply_theme(accent_color, mode)
        for chk in self.findChildren(QCheckBox):
            chk.setStyleSheet(get_checkbox_qss(accent_color, mode))


# =============================================================================
# 8. MAIN FULL APP WINDOW (PURE CONFIGURATION HUB)
# =============================================================================
class DlivesFullAppWindow(QMainWindow):
    """
    Standalone Frameless Configuration Hub for Dlives.
    Dedicated purely to configuring the compact Dynamic Island.
    """
    def __init__(self, storage: StorageManager, settings: SettingsManager, parent=None):
        super().__init__(parent)
        self.storage = storage
        self.settings = settings
        self.settings.settings_changed.connect(self.on_settings_changed)

        self.setWindowTitle("Dlives — Customization Studio & Island Configurator")
        self.setMinimumSize(880, 580)
        self.resize(960, 640)

        # Frameless Window Flags
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        # Set fallback dark palette so no unstyled child widget falls back to Windows default light (#f0f0f0)
        dark_pal = self.palette()
        dark_pal.setColor(QPalette.ColorRole.Window, QColor(0, 0, 0, 0))
        dark_pal.setColor(QPalette.ColorRole.WindowText, QColor(255, 255, 255))
        dark_pal.setColor(QPalette.ColorRole.Base, QColor(0, 0, 0, 0))
        dark_pal.setColor(QPalette.ColorRole.Text, QColor(255, 255, 255))
        self.setPalette(dark_pal)

        self.resizing_edge = None
        self.resize_start_geometry = None
        self.resize_start_global_pos = None
        self.border_width = 8

        self.nav_buttons = []
        self.init_ui()

    def init_ui(self):
        self.central_widget = QWidget(self)
        self.central_widget.setObjectName("central_widget")
        self.setCentralWidget(self.central_widget)
        self.central_layout = QVBoxLayout(self.central_widget)
        self.central_layout.setContentsMargins(0, 0, 0, 0)
        self.central_layout.setSpacing(0)

        # Custom Liquid Glass Title Bar
        self.title_bar = QWidget(self.central_widget)
        self.title_bar.setFixedHeight(42)
        self.title_bar_layout = QHBoxLayout(self.title_bar)
        self.title_bar_layout.setContentsMargins(16, 6, 12, 6)
        self.title_bar_layout.setSpacing(8)

        self.lbl_title_icon = QLabel()
        self.lbl_title_icon.setFixedSize(18, 18)
        logo_p = os.path.join(os.path.dirname(__file__), "assets", "dlives_logo.png")
        if not os.path.exists(logo_p):
            logo_p = os.path.join(os.path.dirname(__file__), "assets", "san_lives_logo.png")
        if not os.path.exists(logo_p):
            logo_p = os.path.join(os.path.dirname(__file__), "assets", "app_icon.png")
        if os.path.exists(logo_p):
            self.lbl_title_icon.setPixmap(QPixmap(logo_p).scaled(18, 18, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        else:
            self.lbl_title_icon.setText("⚙️")
        self.lbl_title_text = QLabel("Dlives • Customization Studio & Island Configurator")
        self.lbl_title_text.setStyleSheet("font-size: 12px; font-weight: 800; letter-spacing: 0.5px; background: transparent;")

        # Redesigned Polished Titlebar Window Controls
        self.btn_min = QPushButton("🗕")
        self.btn_min.setToolTip("Minimize")
        self.btn_max = QPushButton("🗖")
        self.btn_max.setToolTip("Maximize")
        self.btn_close = QPushButton("✕")
        self.btn_close.setToolTip("Close Studio")

        for b in (self.btn_min, self.btn_max, self.btn_close):
            b.setFixedSize(32, 28)
            b.setCursor(Qt.CursorShape.PointingHandCursor)

        self.btn_min.clicked.connect(self.showMinimized)
        self.btn_max.clicked.connect(self.toggle_maximize_restore)
        self.btn_close.clicked.connect(self.close)

        self.title_bar_layout.addWidget(self.lbl_title_icon)
        self.title_bar_layout.addWidget(self.lbl_title_text)
        self.title_bar_layout.addStretch()
        self.title_bar_layout.addWidget(self.btn_min)
        self.title_bar_layout.addWidget(self.btn_max)
        self.title_bar_layout.addWidget(self.btn_close)

        self.central_layout.addWidget(self.title_bar)

        # Workspace Container (Sidebar + Stacked Config Pages)
        workspace_layout = QHBoxLayout()
        workspace_layout.setContentsMargins(12, 4, 12, 12)
        workspace_layout.setSpacing(12)

        # Sidebar Navigation Panel
        self.sidebar_panel = GlassPanel(category_key="default", corner_radius=12)
        self.sidebar_panel.setFixedWidth(220)
        sidebar_box = QVBoxLayout(self.sidebar_panel)
        sidebar_box.setContentsMargins(10, 14, 10, 14)
        sidebar_box.setSpacing(4)

        lbl_nav_header = QLabel("ISLAND CONFIGURATOR")
        lbl_nav_header.setStyleSheet("font-size: 8.5px; font-weight: 900; letter-spacing: 0.8px; color: rgba(255,255,255,0.45); padding-left: 8px; margin-bottom: 6px; background: transparent;")
        sidebar_box.addWidget(lbl_nav_header)

        # Initialize Config Pages
        self.stacked_widget = QStackedWidget()

        self.tab_manager = TabManagerConfigWidget(self.settings)
        self.tab_theme = ThemeOpticsConfigWidget(self.settings)
        self.tab_position = IslandPositionConfigWidget(self.settings)
        self.tab_home_modules = HomeModulesConfigWidget(self.settings)
        self.tab_alarms_notifs = AlarmsNotifsConfigWidget(self.settings, self.storage)
        self.tab_app_launcher = AppLauncherConfigWidget(self.storage, self.settings)
        self.tab_system_backups = SystemBackupConfigWidget(self.settings)

        self.configs_meta = [
            ("🧩 Island Modules & Tabs", self.tab_manager),
            ("🎨 Theme & Glassmorphism", self.tab_theme),
            ("📍 Island Position & Physics", self.tab_position),
            ("🏠 Home Dashboard Cards", self.tab_home_modules),
            ("🔔 Alarms & Notifications", self.tab_alarms_notifs),
            ("🚀 App Launcher Shortcuts", self.tab_app_launcher),
            ("⚙️ System & Data Backups", self.tab_system_backups),
        ]

        for idx, (label, widget) in enumerate(self.configs_meta):
            escaped_label = label.replace("&", "&&") if "&&" not in label else label
            btn = QPushButton(escaped_label)
            btn.setFixedHeight(32)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _, i=idx: self.switch_view(i))
            sidebar_box.addWidget(btn)
            self.nav_buttons.append(btn)
            self.stacked_widget.addWidget(widget)

        sidebar_box.addStretch()
        workspace_layout.addWidget(self.sidebar_panel)
        workspace_layout.addWidget(self.stacked_widget, 1)

        self.central_layout.addLayout(workspace_layout)
        self.apply_theme()
        self.switch_view(0)

    def toggle_maximize_restore(self):
        if self.isMaximized():
            self.showNormal()
            self.btn_max.setText("🗖")
            self.btn_max.setToolTip("Maximize")
        else:
            self.showMaximized()
            self.btn_max.setText("🗗")
            self.btn_max.setToolTip("Restore Down")

    def switch_view(self, index: int):
        if 0 <= index < len(self.nav_buttons):
            prev_idx = self.stacked_widget.currentIndex()

            # Cancel running transition animation if switching rapidly
            if hasattr(self, '_view_fade_anim') and self._view_fade_anim:
                if self._view_fade_anim.state() == QPropertyAnimation.State.Running:
                    self._view_fade_anim.stop()
            if hasattr(self, '_fading_widget') and self._fading_widget:
                try:
                    self._fading_widget.setGraphicsEffect(None)
                except Exception:
                    pass
                self._fading_widget = None

            target_widget = self.stacked_widget.widget(index)
            self.stacked_widget.setCurrentIndex(index)

            if prev_idx != index and target_widget:
                try:
                    effect = QGraphicsOpacityEffect(target_widget)
                    target_widget.setGraphicsEffect(effect)
                    effect.setOpacity(0.0)

                    anim = QPropertyAnimation(effect, b"opacity", self)
                    anim.setDuration(160)
                    anim.setStartValue(0.0)
                    anim.setEndValue(1.0)
                    anim.setEasingCurve(QEasingCurve.Type.OutQuad)
                    self._fading_widget = target_widget

                    def on_view_anim_finished():
                        try:
                            if target_widget:
                                target_widget.setGraphicsEffect(None)
                            self._fading_widget = None
                        except Exception:
                            pass

                    anim.finished.connect(on_view_anim_finished)
                    anim.start()
                    self._view_fade_anim = anim
                except Exception:
                    pass

            accent = resolve_accent_color(self.settings) if self.settings else "#38bdf8"
            accent_txt = get_accent_text_color(accent)
            mode = self.settings.get("theme_mode", "dark") if self.settings else "dark"
            pal = THEME_PALETTES.get(mode, THEME_PALETTES["dark"])

            for idx, btn in enumerate(self.nav_buttons):
                if idx == index:
                    btn.setStyleSheet(f"QPushButton {{ background-color: {accent}; color: {accent_txt}; border-radius: 6px; font-size: 10.5px; font-weight: bold; text-align: left; padding-left: 10px; border: none; }}")
                else:
                    btn.setStyleSheet(f"QPushButton {{ background: transparent; color: {pal['text_primary']}; border-radius: 6px; font-size: 10px; font-weight: 600; text-align: left; padding-left: 10px; border: none; }} QPushButton:hover {{ background: {pal['input_bg']}; }}")

    def apply_theme(self):
        accent = resolve_accent_color(self.settings) if self.settings else "#38bdf8"
        mode = self.settings.get("theme_mode", "dark") if self.settings else "dark"
        pal = THEME_PALETTES.get(mode, THEME_PALETTES["dark"])

        bg_css = "rgba(0, 0, 0, 0.94)" if mode == "dark" else "rgba(245, 247, 250, 0.97)"
        border_css = "rgba(255, 255, 255, 0.08)" if mode == "dark" else "rgba(0, 0, 0, 0.08)"
        self.central_widget.setStyleSheet(f"""
            QWidget#central_widget {{
                background-color: {bg_css};
                border: 1px solid {border_css};
                border-radius: 12px;
                color: {pal['text_primary']};
            }}
            #central_widget QStackedWidget,
            #central_widget QStackedWidget > QWidget,
            #central_widget QScrollArea,
            #central_widget QScrollArea > QWidget,
            #central_widget QScrollArea > QWidget > QWidget {{
                background: transparent;
                background-color: transparent;
                border: none;
            }}
            #central_widget QLabel {{
                background: transparent;
                border: none;
                border-radius: 0px;
            }}
            #central_widget QFrame {{
                border: none;
            }}
            #central_widget QFrame#card_frame {{
                background: transparent;
                border: none;
            }}
        """)

        try:
            from system_monitor import apply_win32_acrylic
            apply_win32_acrylic(
                int(self.winId()),
                gradient_color_hex="#000000" if mode == "dark" else "#f8fafc",
                opacity=0.92,
                is_dark=(mode == "dark")
            )
        except Exception:
            pass

        self.lbl_title_text.setStyleSheet(f"color: {accent}; font-size: 12px; font-weight: 800; letter-spacing: 0.5px; background: transparent;")

        if hasattr(self, 'lbl_title_icon'):
            self.lbl_title_icon.setFixedSize(24, 24)
            custom_logo = self.settings.get("custom_logo_path", "") if self.settings else ""
            pix = get_accent_tinted_logo(accent, mode, 24, custom_logo)
            if not pix.isNull():
                self.lbl_title_icon.setPixmap(pix)

        # Polished Titlebar Window Controls Styling
        btn_glass_border = "rgba(255, 255, 255, 0.12)" if mode == "dark" else "rgba(0, 0, 0, 0.12)"
        btn_glass_bg = "rgba(255, 255, 255, 0.05)" if mode == "dark" else "rgba(0, 0, 0, 0.04)"
        btn_glass_hover = "rgba(255, 255, 255, 0.14)" if mode == "dark" else "rgba(0, 0, 0, 0.09)"

        btn_ctrl_style = f"""
            QPushButton {{
                background-color: {btn_glass_bg};
                color: {pal['text_primary']};
                border: 1px solid {btn_glass_border};
                border-radius: 6px;
                font-size: 11.5px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {btn_glass_hover};
                color: #ffffff;
                border: 1px solid rgba(255, 255, 255, 0.25);
            }}
            QPushButton:pressed {{
                background-color: rgba(255, 255, 255, 0.22);
            }}
        """
        btn_close_style = f"""
            QPushButton {{
                background-color: {btn_glass_bg};
                color: {pal['text_primary']};
                border: 1px solid {btn_glass_border};
                border-radius: 6px;
                font-size: 11.5px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #ef4444;
                color: #ffffff;
                border: 1px solid #dc2626;
            }}
            QPushButton:pressed {{
                background-color: #b91c1c;
                color: #ffffff;
            }}
        """
        self.btn_min.setStyleSheet(btn_ctrl_style)
        self.btn_max.setStyleSheet(btn_ctrl_style)
        self.btn_close.setStyleSheet(btn_close_style)

        for _, widget in self.configs_meta:
            if hasattr(widget, "apply_theme"):
                widget.apply_theme(accent, mode)

        self.switch_view(self.stacked_widget.currentIndex())

    def on_settings_changed(self, new_settings: dict):
        self.apply_theme()

    # --- Smooth Border Edge Resizing & Titlebar Dragging ---
    def _get_resize_edge(self, pos: QPoint):
        rect = self.rect()
        b = self.border_width
        x, y = pos.x(), pos.y()
        w, h = rect.width(), rect.height()

        left = x <= b
        right = x >= w - b
        top = y <= b
        bottom = y >= h - b

        if top and left: return "top_left"
        if top and right: return "top_right"
        if bottom and left: return "bottom_left"
        if bottom and right: return "bottom_right"
        if left: return "left"
        if right: return "right"
        if top: return "top"
        if bottom: return "bottom"
        return None

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and not self.isMaximized():
            edge = self._get_resize_edge(event.position().toPoint())
            if edge:
                self.resizing_edge = edge
                self.resize_start_geometry = self.geometry()
                self.resize_start_global_pos = event.globalPosition().toPoint()
                event.accept()
                return
            # Titlebar drag
            if self.title_bar.geometry().contains(event.position().toPoint()):
                self._titlebar_drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if not self.isMaximized():
            if self.resizing_edge and self.resize_start_geometry and self.resize_start_global_pos:
                delta = event.globalPosition().toPoint() - self.resize_start_global_pos
                rect = self.geometry()
                min_w = self.minimumWidth()
                min_h = self.minimumHeight()

                if "left" in self.resizing_edge:
                    new_w = max(min_w, self.resize_start_geometry.width() - delta.x())
                    self.setGeometry(self.resize_start_geometry.right() - new_w, rect.y(), new_w, rect.height())
                elif "right" in self.resizing_edge:
                    new_w = max(min_w, self.resize_start_geometry.width() + delta.x())
                    self.resize(new_w, rect.height())

                rect = self.geometry()
                if "top" in self.resizing_edge:
                    new_h = max(min_h, self.resize_start_geometry.height() - delta.y())
                    self.setGeometry(rect.x(), self.resize_start_geometry.bottom() - new_h, rect.width(), new_h)
                elif "bottom" in self.resizing_edge:
                    new_h = max(min_h, self.resize_start_geometry.height() + delta.y())
                    self.resize(rect.width(), new_h)

                event.accept()
                return

            if hasattr(self, '_titlebar_drag_pos') and self._titlebar_drag_pos is not None:
                self.move(event.globalPosition().toPoint() - self._titlebar_drag_pos)
                event.accept()
                return

            edge = self._get_resize_edge(event.position().toPoint())
            cursors = {
                "top": Qt.CursorShape.SizeVerCursor,
                "bottom": Qt.CursorShape.SizeVerCursor,
                "left": Qt.CursorShape.SizeHorCursor,
                "right": Qt.CursorShape.SizeHorCursor,
                "top_left": Qt.CursorShape.SizeFDiagCursor,
                "bottom_right": Qt.CursorShape.SizeFDiagCursor,
                "top_right": Qt.CursorShape.SizeBDiagCursor,
                "bottom_left": Qt.CursorShape.SizeBDiagCursor
            }
            self.setCursor(cursors.get(edge, Qt.CursorShape.ArrowCursor))

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self.resizing_edge = None
        self.resize_start_geometry = None
        self.resize_start_global_pos = None
        self._titlebar_drag_pos = None
        super().mouseReleaseEvent(event)

# Backward Compatibility Alias
SanLivesFullAppWindow = DlivesFullAppWindow
