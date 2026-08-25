import json
import os
import re
import shutil
import sys
import tempfile
from datetime import datetime
from PyQt6.QtCore import QObject, pyqtSignal, QTimer

def sanitize_filename(name: str, default: str = "untitled") -> str:
    """Sanitizes user input into a safe, valid Windows filename."""
    if not name or not isinstance(name, str):
        return default
    clean = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', name.strip())
    clean = clean.strip('. ')
    base_upper = clean.upper().split('.')[0]
    if base_upper in {"CON", "PRN", "AUX", "NUL", "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9", "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9"}:
        clean = f"_{clean}"
    if not clean:
        clean = default
    return clean[:100]

def get_app_data_dir() -> str:
    """Single centralized source of truth for application user data directory: %APPDATA%\\Dlives."""
    appdata = os.getenv("APPDATA") or os.path.expanduser("~")
    old_dirs = [os.path.join(appdata, "SanLives"), os.path.join(appdata, "DLives"), os.path.join(appdata, "DynamicIslandPro")]
    data_dir = os.path.join(appdata, "Dlives")

    # One-time migration check: if old data dir exists and new doesn't, copy all user data over
    if not os.path.exists(data_dir):
        for old_dir in old_dirs:
            if os.path.exists(old_dir):
                try:
                    import shutil
                    print(f"[DATA MIGRATION]: Automatic one-time migration from '{old_dir}' to '{data_dir}'...", flush=True)
                    shutil.copytree(old_dir, data_dir)
                    print("[DATA MIGRATION]: Migration completed successfully!", flush=True)
                    break
                except Exception as e:
                    print(f"[DATA MIGRATION EXCEPTION]: Failed to migrate data: {e}", flush=True)

    os.makedirs(data_dir, exist_ok=True)
    return data_dir

def get_base_dir() -> str:
    """Backwards compatible alias returning get_app_data_dir()."""
    return get_app_data_dir()

def safe_atomic_write_json(file_path: str, data):
    """Writes JSON data atomically using a temporary file with retry loop & fallback."""
    dir_name = os.path.dirname(file_path)
    os.makedirs(dir_name, exist_ok=True)
    temp_name = None
    try:
        with tempfile.NamedTemporaryFile('w', dir=dir_name, delete=False, encoding='utf-8') as tf:
            json.dump(data, tf, indent=2, ensure_ascii=False)
            temp_name = tf.name

        for attempt in range(5):
            try:
                os.replace(temp_name, file_path)
                temp_name = None
                return
            except OSError:
                import time
                time.sleep(0.05)

        # Direct write fallback if os.replace is locked by Windows file handle
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Error performing atomic JSON write to {file_path}: {e}")
    finally:
        if temp_name and os.path.exists(temp_name):
            try:
                os.remove(temp_name)
            except Exception:
                pass

def safe_atomic_write_text(file_path: str, text: str):
    """Writes text data atomically using a temporary file with retry loop & fallback."""
    dir_name = os.path.dirname(file_path)
    temp_name = None
    try:
        with tempfile.NamedTemporaryFile('w', dir=dir_name, delete=False, encoding='utf-8') as tf:
            tf.write(text)
            temp_name = tf.name

        for attempt in range(5):
            try:
                os.replace(temp_name, file_path)
                temp_name = None
                return
            except OSError:
                import time
                time.sleep(0.05)

        # Direct write fallback if os.replace is locked by Windows file handle
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(text)
    except Exception as e:
        print(f"Error performing atomic text write to {file_path}: {e}")
    finally:
        if temp_name and os.path.exists(temp_name):
            try:
                os.remove(temp_name)
            except Exception:
                pass

class StorageManager(QObject):
    """Handles storage operations for tasks, multi-notes, calendar, alarms, clipboard, and file shelf."""
    note_content_changed = pyqtSignal(str, str)  # note_id, text
    note_deleted_externally = pyqtSignal(str, str) # note_id, filename
    notes_index_changed = pyqtSignal()          # Emitted when notes list structure changes
    home_pins_changed = pyqtSignal()             # Emitted when notes pinned to home change
    clipboard_changed = pyqtSignal()             # Emitted when clipboard history changes
    alarms_changed = pyqtSignal()                # Emitted when alarms change
    timetable_changed = pyqtSignal()             # Emitted when timetable changes
    calendar_changed = pyqtSignal()              # Emitted when calendar changes
    custom_sounds_changed = pyqtSignal()         # Emitted when custom sound library changes
    fileshelf_changed = pyqtSignal()             # Emitted when file shelf library changes

    def __init__(self, parent=None):
        super().__init__(parent)
        base_dir = get_base_dir()
        self.base_dir = base_dir
        self.tasks_file = os.path.join(base_dir, "tasks.json")
        self.legacy_notes_file = os.path.join(base_dir, "notes.txt")
        self.notes_dir = os.path.join(base_dir, "notes")
        self.notes_index_file = os.path.join(base_dir, "notes_index.json")
        self.calendar_file = os.path.join(base_dir, "calendar.json")
        self.alarms_file = os.path.join(base_dir, "alarms.json")
        self.clipboard_file = os.path.join(base_dir, "clipboard.json")
        self.fileshelf_file = os.path.join(base_dir, "fileshelf.json")
        self.apps_file = os.path.join(base_dir, "apps.json")
        self.icons_dir = os.path.join(base_dir, "icons")
        os.makedirs(self.icons_dir, exist_ok=True)
        self.timetable_file = os.path.join(base_dir, "timetable.json")
        self.custom_sounds_file = os.path.join(base_dir, "custom_sounds.json")
        self._note_cache = {}
        self._dirty_note_buffers = {}
        self.notes_autosave_timer = QTimer(self)
        self.notes_autosave_timer.setInterval(3000)  # 3-second auto-save interval
        self.notes_autosave_timer.timeout.connect(self.flush_dirty_notes)
        self.notes_autosave_timer.start()

        # File System Watcher for external note file modifications/deletions/additions
        from PyQt6.QtCore import QFileSystemWatcher
        os.makedirs(self.notes_dir, exist_ok=True)
        self.notes_watcher = QFileSystemWatcher(self)
        if os.path.exists(self.notes_dir):
            self.notes_watcher.addPath(self.notes_dir)
        self.notes_watcher.directoryChanged.connect(self.sync_external_note_files)
        self.notes_watcher.fileChanged.connect(self.sync_external_note_files)

        # Initialize notes index on startup if not present
        self.load_notes_index()

    def sync_external_note_deletions(self):
        """Backwards compatible alias for sync_external_note_files."""
        self.sync_external_note_files()

    def sync_external_note_files(self):
        """Scans notes_dir for files deleted, modified, or newly added externally in File Explorer."""
        if not os.path.exists(self.notes_index_file):
            index = []
        else:
            try:
                with open(self.notes_index_file, "r", encoding="utf-8") as f:
                    index = json.load(f)
            except Exception:
                index = []

        if not isinstance(index, list):
            index = []

        index_changed = False
        remaining_index = []
        known_filenames = set()

        # 1. Detect external deletions
        for item in index:
            filename = item.get("filename")
            if not filename:
                continue
            filepath = os.path.join(self.notes_dir, filename)
            if not os.path.exists(filepath):
                print(f"[External Note Deletion Detected]: '{filename}' missing on disk!")
                index_changed = True
                self._note_cache.pop(filename, None)
                self._dirty_note_buffers.pop(filename, None)
                self.note_deleted_externally.emit(item.get("id", ""), filename)
            else:
                remaining_index.append(item)
                known_filenames.add(filename)

        # 2. Detect external additions (new .txt files dropped into notes_dir)
        try:
            for fname in os.listdir(self.notes_dir):
                if fname.endswith(".txt") and fname not in known_filenames:
                    fpath = os.path.join(self.notes_dir, fname)
                    if os.path.isfile(fpath):
                        # Extract title from first non-empty line or clean filename
                        title = os.path.splitext(fname)[0].replace("_", " ").title()
                        try:
                            with open(fpath, "r", encoding="utf-8") as tf:
                                lines = [l.strip() for l in tf.readlines() if l.strip()]
                                if lines:
                                    title = lines[0][:40]
                        except Exception:
                            pass

                        import time
                        new_id = f"note_ext_{int(time.time() * 1000)}_{len(remaining_index)}"
                        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
                        new_note = {
                            "id": new_id,
                            "title": title,
                            "filename": fname,
                            "created_at": now_str,
                            "updated_at": now_str,
                            "is_pinned": False,
                            "is_pinned_home": False
                        }
                        print(f"[External Note Addition Detected]: New file '{fname}' indexed as '{title}'!")
                        remaining_index.append(new_note)
                        known_filenames.add(fname)
                        index_changed = True
        except Exception as e:
            print(f"Error scanning notes_dir for new files: {e}")

        # 3. Detect external modifications (content changed on disk)
        for item in remaining_index:
            fname = item.get("filename")
            if not fname or fname in self._dirty_note_buffers:
                continue
            fpath = os.path.join(self.notes_dir, fname)
            if os.path.exists(fpath):
                try:
                    with open(fpath, "r", encoding="utf-8") as f:
                        disk_content = f.read()
                    cached_content = self._note_cache.get(fname)
                    if cached_content is not None and disk_content != cached_content:
                        self._note_cache[fname] = disk_content
                        print(f"[External Note Edit Detected]: '{fname}' updated from disk!")
                        self.note_content_changed.emit(item.get("id", ""), disk_content)
                    elif cached_content is None:
                        self._note_cache[fname] = disk_content
                except Exception:
                    pass

        # Update watcher paths for all .txt files
        try:
            current_watched = set(self.notes_watcher.files())
            for fname in known_filenames:
                fpath = os.path.join(self.notes_dir, fname)
                if os.path.exists(fpath) and fpath not in current_watched:
                    self.notes_watcher.addPath(fpath)
        except Exception:
            pass

        if index_changed:
            if not remaining_index:
                default_note = {
                    "id": "note_default_001",
                    "title": "Welcome Note",
                    "filename": "welcome_note.txt",
                    "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "is_pinned": True,
                    "is_pinned_home": True
                }
                self.save_note_content(default_note["filename"], "Welcome to San Lives!\n\n• Quick Notes & Pinning\n• Alarms & Timetable Schedule\n• System Controls & Mini Taskbar\n• File Shelf & Drop Zone", immediate=True)
                remaining_index = [default_note]

            self.save_notes_index(remaining_index)
            self.notes_index_changed.emit()
            self.home_pins_changed.emit()

    # Custom App Launcher Storage
    def load_apps(self) -> list:
        if os.path.exists(self.apps_file):
            try:
                with open(self.apps_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        return data
            except Exception as e:
                print(f"Corrupted apps.json recovered: {e}")
        return []

    def save_apps(self, apps: list):
        safe_atomic_write_json(self.apps_file, apps)

    def resolve_exe_path(self, command: str) -> str:
        """Resolves target executable path from command string or shortcut."""
        if not command:
            return ""
        cmd_clean = command.strip().strip('"')
        if os.path.exists(cmd_clean):
            return cmd_clean

        # Check common Windows paths
        lower_cmd = cmd_clean.lower()
        if "msedge" in lower_cmd:
            edge_paths = [
                r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
                r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"
            ]
            for ep in edge_paths:
                if os.path.exists(ep):
                    return ep
        if lower_cmd == "explorer":
            return r"C:\Windows\explorer.exe"
        if lower_cmd == "notepad":
            return r"C:\Windows\notepad.exe"
        if "cmd" in lower_cmd or "wt" in lower_cmd:
            cmd_p = r"C:\Windows\System32\cmd.exe"
            if os.path.exists(cmd_p):
                return cmd_p

        # Check first token
        parts = cmd_clean.split()
        if parts:
            first = parts[0].strip('"')
            if os.path.exists(first):
                return first
            if len(parts) > 1 and parts[0].lower() == "start":
                cand = parts[1].strip('"')
                if os.path.exists(cand):
                    return cand

        # Try shutil.which
        which_path = shutil.which(cmd_clean)
        if which_path and os.path.exists(which_path):
            return which_path

        return ""

    def extract_and_cache_app_icon(self, command_or_path: str, app_id: str) -> str:
        """Extracts high-res application icon and caches it as PNG in %APPDATA%\\DLives\\icons\\."""
        if not hasattr(self, 'icons_dir'):
            base_dir = get_base_dir()
            self.icons_dir = os.path.join(base_dir, "icons")
        os.makedirs(self.icons_dir, exist_ok=True)

        icon_dest = os.path.join(self.icons_dir, f"{app_id}.png")
        if os.path.exists(icon_dest) and os.path.getsize(icon_dest) > 0:
            return icon_dest

        exe_path = self.resolve_exe_path(command_or_path)
        if not exe_path or not os.path.exists(exe_path):
            return ""

        try:
            from PyQt6.QtWidgets import QFileIconProvider
            from PyQt6.QtCore import QFileInfo
            provider = QFileIconProvider()
            qicon = provider.icon(QFileInfo(exe_path))
            if not qicon.isNull():
                pix = qicon.pixmap(48, 48)
                if not pix.isNull() and pix.width() > 0:
                    pix.save(icon_dest, "PNG")
                    return icon_dest
        except Exception as e:
            print(f"[Icon Extraction Error ({app_id})]: {e}")

        return ""

    def load_app_launcher(self) -> list:
        apps = self.load_apps()
        if not apps:
            apps = [
                {"id": "app_browser", "name": "Browser", "icon": "🌐", "command": "start msedge"},
                {"id": "app_explorer", "name": "Explorer", "icon": "📁", "command": "explorer"},
                {"id": "app_terminal", "name": "Terminal", "icon": "💻", "command": "start wt || start cmd"},
                {"id": "app_notepad", "name": "Notepad", "icon": "📝", "command": "notepad"}
            ]
            self.save_apps(apps)

        # Auto-extract & cache icons for apps missing cached icon files
        changed = False
        for app in apps:
            app_id = app.get("id", "")
            cmd = app.get("command", "")
            cur_icon_path = app.get("icon_path", "")
            if not cur_icon_path or not os.path.exists(cur_icon_path):
                cached = self.extract_and_cache_app_icon(cmd, app_id)
                if cached:
                    app["icon_path"] = cached
                    changed = True
        if changed:
            self.save_apps(apps)
        return apps

    def save_app_launcher(self, apps: list):
        self.save_apps(apps)

    def add_app_launcher_shortcut(self, name: str, command: str, icon: str = "🚀") -> dict:
        apps = self.load_apps()
        app_id = f"app_{int(datetime.now().timestamp()*1000)}"
        icon_path = self.extract_and_cache_app_icon(command, app_id)
        new_app = {
            "id": app_id,
            "name": name,
            "icon": icon,
            "icon_path": icon_path,
            "command": command
        }
        apps.append(new_app)
        self.save_apps(apps)
        return new_app

    def remove_app_launcher_shortcut(self, app_id: str):
        apps = self.load_apps()
        remaining = [a for a in apps if a.get("id") != app_id]
        self.save_apps(remaining)
        # Clean up cached icon file if present
        if hasattr(self, 'icons_dir'):
            icon_file = os.path.join(self.icons_dir, f"{app_id}.png")
            if os.path.exists(icon_file):
                try:
                    os.remove(icon_file)
                except Exception:
                    pass

    # Multi-Notes Storage Architecture
    def load_notes_index(self) -> list:
        os.makedirs(self.notes_dir, exist_ok=True)

        if os.path.exists(self.notes_index_file):
            try:
                with open(self.notes_index_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        return data
            except Exception as e:
                print(f"Notes index recovery exception: {e}")

        # Migration from legacy single notes.txt if index missing
        legacy_content = ""
        if os.path.exists(self.legacy_notes_file):
            try:
                with open(self.legacy_notes_file, "r", encoding="utf-8") as f:
                    legacy_content = f.read()
            except Exception:
                pass

        default_note = {
            "id": "note_default_001",
            "title": "Quick Note",
            "filename": "quick_note.txt",
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "is_pinned": True,
            "is_pinned_home": True
        }

        welcome_text = legacy_content if legacy_content else "Welcome to Dlives!\n\n• Quick Notes & Pinning\n• Alarms & Timetable Schedule\n• System Controls & Mini Taskbar\n• File Shelf & Drop Zone"
        self.save_note_content(default_note["filename"], welcome_text, immediate=True)
        initial_index = [default_note]
        safe_atomic_write_json(self.notes_index_file, initial_index)
        return initial_index

    def save_notes_index(self, index: list):
        old_index = []
        if os.path.exists(self.notes_index_file):
            try:
                with open(self.notes_index_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        old_index = data
            except Exception:
                old_index = []

        old_home_pins = [(n.get("id"), n.get("title")) for n in old_index if n.get("is_pinned_home", False)]
        new_home_pins = [(n.get("id"), n.get("title")) for n in index if n.get("is_pinned_home", False)]
        old_pinned = [n.get("id") for n in old_index if n.get("is_pinned", False)]
        new_pinned = [n.get("id") for n in index if n.get("is_pinned", False)]
        old_ids = [n.get("id") for n in old_index]
        new_ids = [n.get("id") for n in index]

        safe_atomic_write_json(self.notes_index_file, index)

        if old_home_pins != new_home_pins or old_ids != new_ids:
            self.home_pins_changed.emit()
        if old_pinned != new_pinned or old_ids != new_ids:
            self.notes_index_changed.emit()

    def queue_note_save(self, filename: str, content: str):
        """Buffers note edits in memory without disk I/O on keystrokes."""
        if not filename:
            return
        if self._note_cache.get(filename) == content and filename not in self._dirty_note_buffers:
            return
        self._dirty_note_buffers[filename] = content
        self._note_cache[filename] = content

    def flush_dirty_notes(self):
        """Flushes buffered note changes to disk and updates notes_index.json metadata once."""
        if not self._dirty_note_buffers:
            return

        dirty_items = list(self._dirty_note_buffers.items())
        self._dirty_note_buffers.clear()

        os.makedirs(self.notes_dir, exist_ok=True)
        index = self.load_notes_index()
        index_updated = False
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")

        for filename, content in dirty_items:
            try:
                filepath = os.path.join(self.notes_dir, filename)
                safe_atomic_write_text(filepath, content)

                # Update index metadata timestamp
                for item in index:
                    if item.get("filename") == filename:
                        item["updated_at"] = now_str
                        index_updated = True
                        break
            except Exception as e:
                print(f"Error flushing note {filename}: {e}")

        if index_updated:
            self.save_notes_index(index)

    def load_note_content(self, filename: str) -> str:
        if filename in self._dirty_note_buffers:
            return self._dirty_note_buffers[filename]
        os.makedirs(self.notes_dir, exist_ok=True)
        filepath = os.path.join(self.notes_dir, filename)
        if os.path.exists(filepath):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
                    self._note_cache[filename] = content
                    return content
            except Exception as e:
                print(f"Error loading note file {filename}: {e}")
        return ""

    def save_note_content(self, filename: str, content: str, immediate: bool = False):
        """Saves note content. Buffers by default, or writes immediately if specified."""
        self.queue_note_save(filename, content)
        if immediate:
            self.flush_dirty_notes()

        index = self.load_notes_index()
        note_id = ""
        for item in index:
            if item.get("filename") == filename:
                note_id = item.get("id", "")
                break
        if note_id:
            self.note_content_changed.emit(note_id, content)

    def get_pinned_note(self) -> dict:
        index = self.load_notes_index()
        for item in index:
            if item.get("is_pinned", False):
                return item
        return index[0] if index else {}

    def get_home_pinned_notes(self) -> list:
        """Returns up to 2 notes pinned to the Home page."""
        index = self.load_notes_index()
        home_pinned = [n for n in index if n.get("is_pinned_home", False)]
        return home_pinned[:2]

    def toggle_home_pin(self, note_id: str) -> bool:
        """Toggles a note's is_pinned_home property, enforcing a maximum cap of 2 pinned notes."""
        index = self.load_notes_index()
        target = next((n for n in index if n.get("id") == note_id), None)
        if not target:
            return False

        currently_pinned = [n for n in index if n.get("is_pinned_home", False)]

        if target.get("is_pinned_home", False):
            target["is_pinned_home"] = False
        else:
            if len(currently_pinned) >= 2:
                # Unpin the oldest pinned note to enforce cap of 2
                currently_pinned[0]["is_pinned_home"] = False
            target["is_pinned_home"] = True

        self.save_notes_index(index)
        return target.get("is_pinned_home", False)

    def create_note(self, title: str = "New Note") -> dict:
        now = datetime.now()
        timestamp_str = now.strftime("%Y%m%d_%H%M%S")
        sanitized_title = sanitize_filename(title, "New_Note")
        filename = f"{timestamp_str}_{sanitized_title}.txt"
        import uuid
        note_id = f"note_{int(now.timestamp()*1000)}_{uuid.uuid4().hex[:6]}"

        note = {
            "id": note_id,
            "title": title.strip() or "New Note",
            "filename": filename,
            "created_at": now.strftime("%Y-%m-%d %H:%M"),
            "updated_at": now.strftime("%Y-%m-%d %H:%M"),
            "is_pinned": False,
            "is_pinned_home": False
        }

        self.save_note_content(filename, "", immediate=True)
        index = self.load_notes_index()
        index.insert(0, note)
        self.save_notes_index(index)
        return note

    def delete_note(self, note_id: str):
        index = self.load_notes_index()
        note_to_delete = None
        for n in index:
            if n.get("id") == note_id:
                note_to_delete = n
                break

        if note_to_delete:
            index.remove(note_to_delete)
            filepath = os.path.join(self.notes_dir, note_to_delete.get("filename", ""))
            if os.path.exists(filepath):
                try:
                    os.remove(filepath)
                except Exception as e:
                    print(f"Error removing note file: {e}")

            if index and not any(n.get("is_pinned") for n in index):
                index[0]["is_pinned"] = True

            self.save_notes_index(index)

    def rename_note(self, note_id: str, new_title: str):
        index = self.load_notes_index()
        for n in index:
            if n.get("id") == note_id:
                n["title"] = new_title.strip() or "Untitled"
                n["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")
                break
        self.save_notes_index(index)

    # Legacy load_notes / save_notes helper compatibility
    def load_notes(self) -> str:
        pinned = self.get_pinned_note()
        if pinned:
            return self.load_note_content(pinned.get("filename", ""))
        return ""

    def save_notes(self, text: str):
        pinned = self.get_pinned_note()
        if pinned:
            self.save_note_content(pinned.get("filename", ""), text)

    # Tasks
    def load_tasks(self) -> list:
        if os.path.exists(self.tasks_file):
            try:
                with open(self.tasks_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        return [t for t in data if isinstance(t, dict)]
            except Exception as e:
                print(f"Corrupted tasks.json recovered: {e}")
        return []

    def save_tasks(self, tasks: list):
        safe_atomic_write_json(self.tasks_file, tasks)

    # Calendar Events
    def load_calendar(self) -> dict:
        if os.path.exists(self.calendar_file):
            try:
                with open(self.calendar_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        cleaned = {}
                        for k, v in data.items():
                            if isinstance(k, str) and isinstance(v, list):
                                cleaned[k] = [ev for ev in v if isinstance(ev, dict)]
                        return cleaned
            except Exception as e:
                print(f"Corrupted calendar.json recovered: {e}")
        return {}

    def save_calendar(self, calendar_data: dict):
        safe_atomic_write_json(self.calendar_file, calendar_data)
        self.calendar_changed.emit()

    def add_calendar_event(self, date_str: str, event_title: str):
        cal = self.load_calendar()
        if date_str not in cal:
            cal[date_str] = []
        cal[date_str].append({"id": f"evt_{int(datetime.now().timestamp()*1000)}", "title": event_title})
        self.save_calendar(cal)

    def delete_calendar_event(self, date_str: str, event_id_or_title: str):
        cal = self.load_calendar()
        if date_str in cal:
            cal[date_str] = [
                ev for ev in cal[date_str] 
                if (ev.get("id") if isinstance(ev, dict) else ev) != event_id_or_title and 
                   (ev.get("title") if isinstance(ev, dict) else ev) != event_id_or_title
            ]
            if not cal[date_str]:
                del cal[date_str]
            self.save_calendar(cal)

    # Alarms
    def load_alarms(self) -> list:
        if os.path.exists(self.alarms_file):
            try:
                with open(self.alarms_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        return [a for a in data if isinstance(a, dict) and a.get("time")]
            except Exception as e:
                print(f"Corrupted alarms.json recovered: {e}")
        return []

    def save_alarms(self, alarms: list):
        safe_atomic_write_json(self.alarms_file, alarms)
        self.alarms_changed.emit()

    # Timetable Schedule
    def load_timetable(self) -> list:
        if os.path.exists(self.timetable_file):
            try:
                with open(self.timetable_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        return [t for t in data if isinstance(t, dict) and t.get("time")]
            except Exception as e:
                print(f"Corrupted timetable.json recovered: {e}")
        return []

    def save_timetable(self, timetable: list):
        safe_atomic_write_json(self.timetable_file, timetable)
        self.timetable_changed.emit()

    def delete_timetable_task(self, task_id_or_title: str):
        tt = self.load_timetable()
        target = str(task_id_or_title)
        filtered = [
            t for t in tt 
            if not ((t.get("id") and str(t.get("id")) == target) or (t.get("title") and str(t.get("title")) == target))
        ]
        if len(filtered) != len(tt):
            self.save_timetable(filtered)

    def toggle_timetable_task(self, task_id_or_title: str, completed: bool = None):
        tt = self.load_timetable()
        changed = False
        target = str(task_id_or_title)
        for t in tt:
            t_id = str(t.get("id", ""))
            t_title = str(t.get("title", ""))
            if (t_id and t_id == target) or (t_title and t_title == target):
                curr = t.get("is_completed", t.get("completed", False))
                new_state = (not curr) if completed is None else bool(completed)
                t["is_completed"] = new_state
                t["completed"] = new_state
                changed = True
                break
        if changed:
            self.save_timetable(tt)

    # Clipboard History
    def load_clipboard(self) -> list:
        if os.path.exists(self.clipboard_file):
            try:
                with open(self.clipboard_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        return [c for c in data if (isinstance(c, dict) and c.get("text")) or isinstance(c, str)]
            except Exception as e:
                print(f"Corrupted clipboard.json recovered: {e}")
        return []

    def save_clipboard(self, history: list):
        safe_atomic_write_json(self.clipboard_file, history)
        self.clipboard_changed.emit()

    def add_clipboard_entry(self, text: str):
        if not text or not isinstance(text, str) or not text.strip():
            return
        clips = self.load_clipboard()
        clips = [c for c in clips if (c.get("text") if isinstance(c, dict) else c) != text]
        clips.insert(0, {"text": text, "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")})

        if len(clips) > 50:
            clips = clips[:50]
        self.save_clipboard(clips)

    def delete_clipboard_entry(self, text: str) -> bool:
        clips = self.load_clipboard()
        filtered = [c for c in clips if (c.get("text") if isinstance(c, dict) else c) != text]
        if len(filtered) != len(clips):
            self.save_clipboard(filtered)
            return True
        return False

    def clear_clipboard(self):
        self.save_clipboard([])

    # File Shelf
    def load_shelf(self) -> list:
        if os.path.exists(self.fileshelf_file):
            try:
                with open(self.fileshelf_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        return [f for f in data if isinstance(f, dict) and f.get("path")]
            except Exception as e:
                print(f"Corrupted fileshelf.json recovered: {e}")
        return []

    def save_shelf(self, files: list):
        safe_atomic_write_json(self.fileshelf_file, files)
        self.fileshelf_changed.emit()

    def add_shelf_file(self, file_path: str):
        if not file_path or not isinstance(file_path, str) or not os.path.exists(file_path):
            return
        shelf = self.load_shelf()
        shelf = [f for f in shelf if (f.get("path") if isinstance(f, dict) else f) != file_path]
        shelf.insert(0, {
            "name": os.path.basename(file_path),
            "path": file_path,
            "added_at": datetime.now().strftime("%Y-%m-%d %H:%M")
        })

        if len(shelf) > 30:
            shelf = shelf[:30]
        self.save_shelf(shelf)

    def delete_shelf_file(self, file_path: str) -> bool:
        shelf = self.load_shelf()
        filtered = [f for f in shelf if (f.get("path") if isinstance(f, dict) else f) != file_path]
        if len(filtered) != len(shelf):
            self.save_shelf(filtered)
            return True
        return False

    def clear_shelf(self):
        self.save_shelf([])

    # Custom Alarm Sounds Library
    def load_custom_sounds(self) -> list:
        if os.path.exists(self.custom_sounds_file):
            try:
                with open(self.custom_sounds_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        return [s for s in data if isinstance(s, dict) and s.get("path")]
            except Exception as e:
                print(f"Corrupted custom_sounds.json recovered: {e}")
        return []

    def save_custom_sounds(self, sounds: list):
        safe_atomic_write_json(self.custom_sounds_file, sounds)
        self.custom_sounds_changed.emit()

    def add_custom_sound(self, title: str, file_path: str) -> dict:
        sounds = self.load_custom_sounds()
        sound_id = f"sound_{int(datetime.now().timestamp() * 1000)}"
        new_item = {
            "id": sound_id,
            "title": title or os.path.basename(file_path),
            "path": file_path,
            "created_at": datetime.now().isoformat()
        }
        sounds.append(new_item)
        self.save_custom_sounds(sounds)
        return new_item

    def delete_custom_sound(self, sound_id: str) -> bool:
        sounds = self.load_custom_sounds()
        filtered = [s for s in sounds if s.get("id") != sound_id and s.get("path") != sound_id]
        if len(filtered) != len(sounds):
            self.save_custom_sounds(filtered)
            return True
        return False
