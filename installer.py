import os
import sys
import shutil
import ctypes
import subprocess
import winreg
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize
from PyQt6.QtGui import QIcon, QPixmap, QFont, QColor, QPainter, QPainterPath, QPen, QBrush
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QProgressBar, QCheckBox, QFrame, QFileDialog, QLineEdit
)

APP_NAME = "Dlives"
APP_VERSION = "3.2.1"
DEFAULT_INSTALL_DIR = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "Programs", "Dlives")

def get_bundle_dir():
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))

def create_shortcut(target_path, shortcut_path, icon_path=None, description=""):
    try:
        os.makedirs(os.path.dirname(shortcut_path), exist_ok=True)
        import win32com.client
        shell = win32com.client.Dispatch("WScript.Shell")
        shortcut = shell.CreateShortCut(shortcut_path)
        shortcut.TargetPath = target_path
        shortcut.WorkingDirectory = os.path.dirname(target_path)
        if icon_path and os.path.exists(icon_path):
            shortcut.IconLocation = f"{icon_path},0"
        else:
            shortcut.IconLocation = f"{target_path},0"
        shortcut.Description = description
        shortcut.Save()
        return True
    except Exception as e:
        # Fallback to PowerShell COM execution with robust single-quoted paths
        try:
            ico = icon_path if (icon_path and os.path.exists(icon_path)) else target_path
            ps_cmd = (
                f"$ws = New-Object -ComObject WScript.Shell; "
                f"$s = $ws.CreateShortcut('{shortcut_path}'); "
                f"$s.TargetPath = '{target_path}'; "
                f"$s.WorkingDirectory = '{os.path.dirname(target_path)}'; "
                f"$s.IconLocation = '{ico},0'; "
                f"$s.Description = '{description}'; "
                f"$s.Save()"
            )
            subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_cmd], capture_output=True)
            return os.path.exists(shortcut_path)
        except Exception:
            return False

def register_uninstaller(install_dir, exe_path):
    try:
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\Dlives"
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path) as key:
            winreg.SetValueEx(key, "DisplayName", 0, winreg.REG_SZ, "Dlives")
            winreg.SetValueEx(key, "DisplayVersion", 0, winreg.REG_SZ, APP_VERSION)
            winreg.SetValueEx(key, "Publisher", 0, winreg.REG_SZ, "Dlives Team")
            winreg.SetValueEx(key, "DisplayIcon", 0, winreg.REG_SZ, f"{exe_path},0")
            winreg.SetValueEx(key, "InstallLocation", 0, winreg.REG_SZ, install_dir)
            uninst_bat = os.path.join(install_dir, "Uninstall.bat")
            winreg.SetValueEx(key, "UninstallString", 0, winreg.REG_SZ, f'"{uninst_bat}"')
            winreg.SetValueEx(key, "NoModify", 0, winreg.REG_DWORD, 1)
            winreg.SetValueEx(key, "NoRepair", 0, winreg.REG_DWORD, 1)
            # Add EstimatedSize in KB (~50MB = 51200KB)
            winreg.SetValueEx(key, "EstimatedSize", 0, winreg.REG_DWORD, 52000)
    except Exception as e:
        print("Register uninstaller err:", e)

def refresh_shell_icons():
    try:
        ctypes.windll.shell32.SHChangeNotify(0x08000000, 0x1000, None, None)
    except Exception:
        pass

class InstallWorker(QThread):
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(bool, str)

    def __init__(self, install_dir, create_desktop, create_start_menu):
        super().__init__()
        self.install_dir = install_dir
        self.create_desktop = create_desktop
        self.create_start_menu = create_start_menu

    def run(self):
        try:
            # Initialize COM for this thread
            try:
                import pythoncom
                pythoncom.CoInitialize()
            except Exception:
                pass

            bundle_dir = get_bundle_dir()
            self.progress.emit(10, "Preparing installation directory...")
            os.makedirs(self.install_dir, exist_ok=True)

            # Kill if running to avoid locked files
            subprocess.run(["taskkill", "/F", "/IM", "Dlives.exe"], capture_output=True)

            self.progress.emit(30, "Copying application binaries...")
            dest_exe = os.path.join(self.install_dir, "Dlives.exe")

            # Locate payload directory or single executable file
            possible_exe_sources = [
                os.path.join(bundle_dir, "Dlives_Payload.bin"),
                os.path.join(bundle_dir, "Dlives_Payload", "Dlives_Payload.bin"),
                os.path.join(bundle_dir, "Dlives_Payload", "Dlives.exe"),
                os.path.join(bundle_dir, "Dlives_Payload"),
                os.path.join(bundle_dir, "Dlives.exe"),
                os.path.join(bundle_dir, "Dlives", "Dlives.exe"),
                os.path.join(os.path.dirname(os.path.abspath(__file__)), "dist_app", "Dlives.exe"),
                os.path.join(os.path.dirname(os.path.abspath(__file__)), "dist", "Dlives.exe"),
                os.path.join(os.path.dirname(os.path.abspath(__file__)), "Dlives.exe"),
            ]

            copied_exe = False
            for src_p in possible_exe_sources:
                if os.path.exists(src_p) and os.path.isfile(src_p):
                    shutil.copy2(src_p, dest_exe)
                    copied_exe = True
                    print(f"[INSTALLER SUCCESS]: Copied binary '{src_p}' -> '{dest_exe}'")
                    break

            if not copied_exe:
                # Check for payload folder
                src_dir = os.path.join(bundle_dir, "Dlives_Payload")
                if not os.path.exists(src_dir) or not os.path.isdir(src_dir):
                    src_dir = os.path.join(bundle_dir, "Dlives")
                if os.path.exists(src_dir) and os.path.isdir(src_dir):
                    for item in os.listdir(src_dir):
                        s = os.path.join(src_dir, item)
                        d = os.path.join(self.install_dir, item)
                        if os.path.isdir(s):
                            shutil.copytree(s, d, dirs_exist_ok=True)
                        else:
                            shutil.copy2(s, d)
                    copied_exe = os.path.exists(dest_exe)

            if not os.path.exists(dest_exe):
                raise FileNotFoundError(f"Could not locate Dlives.exe payload executable in bundle '{bundle_dir}'!")

            # Copy icon and assets if available
            src_ico = os.path.join(bundle_dir, "app_icon.ico")
            if not os.path.exists(src_ico):
                src_ico = os.path.join(bundle_dir, "Dlives_Payload", "app_icon.ico")
            if not os.path.exists(src_ico):
                src_ico = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app_icon.ico")

            dest_ico = os.path.join(self.install_dir, "app_icon.ico")
            if os.path.exists(src_ico):
                shutil.copy2(src_ico, dest_ico)

            # Copy assets folder if present
            src_assets = os.path.join(bundle_dir, "assets")
            if not os.path.exists(src_assets):
                src_assets = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
            if os.path.exists(src_assets) and os.path.isdir(src_assets):
                dest_assets = os.path.join(self.install_dir, "assets")
                shutil.copytree(src_assets, dest_assets, dirs_exist_ok=True)

            self.progress.emit(60, "Creating Windows uninstaller...")
            uninst_bat = os.path.join(self.install_dir, "Uninstall.bat")
            bat_script = f'''@echo off
taskkill /F /IM Dlives.exe >nul 2>&1
reg delete "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\Dlives" /f >nul 2>&1
del "%USERPROFILE%\\Desktop\\Dlives.lnk" >nul 2>&1
del "%USERPROFILE%\\OneDrive\\Desktop\\Dlives.lnk" >nul 2>&1
del "%APPDATA%\\Microsoft\\Windows\\Start Menu\\Programs\\Dlives.lnk" >nul 2>&1
echo Dlives successfully uninstalled.
rd /s /q "{self.install_dir}"
'''
            with open(uninst_bat, "w", encoding="utf-8") as f:
                f.write(bat_script)

            register_uninstaller(self.install_dir, dest_exe)

            self.progress.emit(80, "Creating shortcuts...")
            icon_target = dest_ico if os.path.exists(dest_ico) else dest_exe
            if self.create_desktop:
                desktop_dirs = [
                    os.path.join(os.environ.get("USERPROFILE", ""), "Desktop"),
                    os.path.join(os.environ.get("USERPROFILE", ""), "OneDrive", "Desktop")
                ]
                for d in desktop_dirs:
                    if os.path.exists(d):
                        create_shortcut(dest_exe, os.path.join(d, "Dlives.lnk"), icon_target, "Dlives Dynamic Island")

            if self.create_start_menu:
                start_menu = os.path.join(os.environ.get("APPDATA", ""), "Microsoft", "Windows", "Start Menu", "Programs")
                if os.path.exists(start_menu):
                    create_shortcut(dest_exe, os.path.join(start_menu, "Dlives.lnk"), icon_target, "Dlives Dynamic Island")

            refresh_shell_icons()
            self.progress.emit(100, "Installation complete!")
            self.finished.emit(True, dest_exe)
        except Exception as e:
            self.finished.emit(False, str(e))

class InstallerWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Dlives Setup")
        self.setFixedSize(500, 360)
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.CustomizeWindowHint | Qt.WindowType.WindowCloseButtonHint | Qt.WindowType.WindowMinimizeButtonHint)
        self.setStyleSheet("""
            QWidget {
                background-color: #0b0f19;
                color: #f8fafc;
                font-family: 'Segoe UI', sans-serif;
            }
            QLabel {
                background: transparent;
            }
            QLineEdit {
                background-color: #1e293b;
                color: #f8fafc;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 11px;
            }
            QCheckBox {
                color: #cbd5e1;
                font-size: 11px;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border-radius: 4px;
                border: 1px solid #475569;
                background-color: #1e293b;
            }
            QCheckBox::indicator:checked {
                background-color: #38bdf8;
                border-color: #38bdf8;
            }
            QProgressBar {
                background-color: #1e293b;
                border: 1px solid #334155;
                border-radius: 4px;
                text-align: center;
                color: transparent;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #38bdf8, stop:1 #818cf8);
                border-radius: 3px;
            }
        """)

        bundle_dir = get_bundle_dir()
        ico_path = os.path.join(bundle_dir, "app_icon.ico")
        if not os.path.exists(ico_path):
            ico_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app_icon.ico")
        if os.path.exists(ico_path):
            self.setWindowIcon(QIcon(ico_path))

        self.installed_exe_path = ""
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        # Header with Logo & Brand
        header = QHBoxLayout()
        header.setSpacing(12)

        bundle_dir = get_bundle_dir()
        logo_path = os.path.join(bundle_dir, "assets", "san_lives_logo.png")
        if not os.path.exists(logo_path):
            logo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "san_lives_logo.png")

        logo_lbl = QLabel()
        logo_lbl.setFixedSize(48, 48)
        if os.path.exists(logo_path):
            pix = QPixmap(logo_path).scaled(48, 48, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            logo_lbl.setPixmap(pix)
        else:
            logo_lbl.setText("⚡")
            logo_lbl.setStyleSheet("font-size: 32px;")
        header.addWidget(logo_lbl)

        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        title_lbl = QLabel("Dlives Setup")
        title_lbl.setStyleSheet("font-size: 18px; font-weight: 800; color: #ffffff;")
        sub_lbl = QLabel(f"Version {APP_VERSION} — Next-Gen Dynamic Island for Windows")
        sub_lbl.setStyleSheet("font-size: 11px; color: #94a3b8;")
        title_box.addWidget(title_lbl)
        title_box.addWidget(sub_lbl)
        header.addLayout(title_box)
        header.addStretch()
        layout.addLayout(header)

        # Divider
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("background-color: #1e293b; max-height: 1px;")
        layout.addWidget(line)

        # Install Directory
        dir_lbl = QLabel("Install Location:")
        dir_lbl.setStyleSheet("font-size: 11px; font-weight: 600; color: #cbd5e1;")
        layout.addWidget(dir_lbl)

        dir_box = QHBoxLayout()
        dir_box.setSpacing(6)
        self.dir_input = QLineEdit(DEFAULT_INSTALL_DIR)
        self.dir_input.setReadOnly(True)
        dir_box.addWidget(self.dir_input, 1)

        self.btn_browse = QPushButton("Browse...")
        self.btn_browse.setFixedHeight(30)
        self.btn_browse.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_browse.setStyleSheet("QPushButton { background-color: #1e293b; color: #cbd5e1; border: 1px solid #334155; border-radius: 6px; padding: 0 12px; font-size: 10.5px; } QPushButton:hover { background-color: #334155; color: #ffffff; }")
        self.btn_browse.clicked.connect(self.browse_directory)
        dir_box.addWidget(self.btn_browse)
        layout.addLayout(dir_box)

        # Options
        self.chk_desktop = QCheckBox("Create Desktop Shortcut")
        self.chk_desktop.setChecked(True)
        self.chk_start_menu = QCheckBox("Create Start Menu Shortcut")
        self.chk_start_menu.setChecked(True)
        self.chk_launch = QCheckBox("Launch Dlives after setup completes")
        self.chk_launch.setChecked(True)

        layout.addWidget(self.chk_desktop)
        layout.addWidget(self.chk_start_menu)
        layout.addWidget(self.chk_launch)

        # Progress bar (Hidden initially)
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(8)
        self.progress_bar.setValue(0)
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)

        self.status_lbl = QLabel("")
        self.status_lbl.setStyleSheet("font-size: 10px; color: #38bdf8; font-style: italic;")
        self.status_lbl.hide()
        layout.addWidget(self.status_lbl)

        layout.addStretch()

        # Action Buttons
        btn_box = QHBoxLayout()
        btn_box.setSpacing(8)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setFixedHeight(34)
        self.cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cancel_btn.setStyleSheet("QPushButton { background-color: #1e293b; color: #94a3b8; border: 1px solid #334155; border-radius: 6px; font-size: 11px; font-weight: 600; padding: 0 16px; } QPushButton:hover { background-color: #334155; color: #ffffff; }")
        self.cancel_btn.clicked.connect(self.close)

        self.install_btn = QPushButton("Install Dlives")
        self.install_btn.setFixedHeight(34)
        self.install_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.install_btn.setStyleSheet("QPushButton { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #38bdf8, stop:1 #818cf8); color: #ffffff; border: none; border-radius: 6px; font-size: 11px; font-weight: bold; padding: 0 20px; } QPushButton:hover { opacity: 0.9; }")
        self.install_btn.clicked.connect(self.start_installation)

        btn_box.addStretch()
        btn_box.addWidget(self.cancel_btn)
        btn_box.addWidget(self.install_btn)
        layout.addLayout(btn_box)

    def browse_directory(self):
        d = QFileDialog.getExistingDirectory(self, "Select Install Directory", self.dir_input.text())
        if d:
            self.dir_input.setText(os.path.join(d, "Dlives"))

    def start_installation(self):
        self.btn_browse.setEnabled(False)
        self.chk_desktop.setEnabled(False)
        self.chk_start_menu.setEnabled(False)
        self.chk_launch.setEnabled(False)
        self.install_btn.setEnabled(False)
        self.cancel_btn.setEnabled(False)

        self.progress_bar.show()
        self.status_lbl.show()

        target_dir = self.dir_input.text().strip() or DEFAULT_INSTALL_DIR
        self.worker = InstallWorker(target_dir, self.chk_desktop.isChecked(), self.chk_start_menu.isChecked())
        self.worker.progress.connect(self.on_progress)
        self.worker.finished.connect(self.on_finished)
        self.worker.start()

    def on_progress(self, val, msg):
        self.progress_bar.setValue(val)
        self.status_lbl.setText(msg)

    def on_finished(self, success, result):
        if success:
            self.installed_exe_path = result
            self.progress_bar.setValue(100)
            self.status_lbl.setText("🎉 Installation completed successfully!")
            self.status_lbl.setStyleSheet("font-size: 11px; color: #10b981; font-weight: bold;")
            
            self.install_btn.setText("Finish & Launch")
            self.install_btn.setEnabled(True)
            self.install_btn.clicked.disconnect()
            self.install_btn.clicked.connect(self.on_finish_click)
            
            self.cancel_btn.setText("Close")
            self.cancel_btn.setEnabled(True)
        else:
            self.status_lbl.setText(f"❌ Error: {result}")
            self.status_lbl.setStyleSheet("font-size: 11px; color: #ef4444; font-weight: bold;")
            self.cancel_btn.setEnabled(True)

    def on_finish_click(self):
        if self.chk_launch.isChecked() and self.installed_exe_path and os.path.exists(self.installed_exe_path):
            os.startfile(self.installed_exe_path)
        self.close()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = InstallerWindow()
    win.show()
    sys.exit(app.exec())
