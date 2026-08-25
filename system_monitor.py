import ctypes
import os
import psutil
import re
import time
from datetime import datetime, timezone, timedelta
from PyQt6.QtCore import QThread, pyqtSignal

# WinRT Imports for Real Windows Media Session & Notification Listener
try:
    import asyncio
    import winrt.windows.media.control as winrt_mc
    import winrt.windows.ui.notifications as winrt_un
    import winrt.windows.ui.notifications.management as winrt_nm
    import winrt.windows.storage.streams as winrt_ss
    HAS_WINRT = True
except Exception as e:
    HAS_WINRT = False
    print(f"WinRT import warning: {e}")

# Safe imports for audio & brightness
try:
    from comtypes import CLSCTX_ALL
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
    HAS_PYCAW = True
except Exception:
    HAS_PYCAW = False

try:
    import screen_brightness_control as sbc
    HAS_SBC = True
except Exception:
    HAS_SBC = False

# Virtual Key Codes for Keyboard Lock & Media
VK_CAPITAL = 0x14      # Caps Lock
VK_NUMLOCK = 0x90      # Num Lock
VK_MEDIA_NEXT_TRACK = 0xB0
VK_MEDIA_PREV_TRACK = 0xB1
VK_MEDIA_PLAY_PAUSE = 0xB3

# Win32 Acrylic C-API Structures
class MARGINS(ctypes.Structure):
    _fields_ = [
        ('cxLeftWidth', ctypes.c_int),
        ('cxRightWidth', ctypes.c_int),
        ('cyTopHeight', ctypes.c_int),
        ('cyBottomHeight', ctypes.c_int)
    ]

class ACCENT_POLICY(ctypes.Structure):
    _fields_ = [
        ('AccentState', ctypes.c_int),
        ('AccentFlags', ctypes.c_int),
        ('GradientColor', ctypes.c_int),
        ('AnimationId', ctypes.c_int)
    ]

class WINDOWCOMPOSITIONATTRIB_DATA(ctypes.Structure):
    _fields_ = [
        ('Attribute', ctypes.c_int),
        ('Data', ctypes.c_void_p),
        ('SizeOfData', ctypes.c_size_t)
    ]

def apply_win32_acrylic(hwnd: int, gradient_color_hex: str = "#0b0f19", opacity: float = 0.85, is_dark: bool = True) -> bool:
    """
    Applies true hardware-accelerated frosted glass blur (Windows Acrylic / BlurBehind / Mica)
    to a Qt window using Win32 DWM and user32.SetWindowCompositionAttribute.
    """
    if not hwnd or os.name != 'nt':
        return False

    success = False

    # 1. Enable Immersive Dark Mode in DWM
    try:
        DWMWA_USE_IMMERSIVE_DARK_MODE = 20
        dark_val = ctypes.c_int(1 if is_dark else 0)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            ctypes.c_void_p(hwnd),
            DWMWA_USE_IMMERSIVE_DARK_MODE,
            ctypes.byref(dark_val),
            ctypes.sizeof(dark_val)
        )
    except Exception:
        pass

    # 2. Extend DWM Frame into Client Area for native glass rendering
    try:
        margins = MARGINS(-1, -1, -1, -1)
        ctypes.windll.dwmapi.DwmExtendFrameIntoClientArea(
            ctypes.c_void_p(hwnd),
            ctypes.byref(margins)
        )
    except Exception:
        pass

    # 3. Windows 11 DWM System Backdrop (Acrylic = 3, Mica = 2)
    try:
        DWMWA_SYSTEMBACKDROP_TYPE = 38
        backdrop_val = ctypes.c_int(3)  # DWMSBT_TRANSIENTWINDOW (Acrylic blur)
        hr = ctypes.windll.dwmapi.DwmSetWindowAttribute(
            ctypes.c_void_p(hwnd),
            DWMWA_SYSTEMBACKDROP_TYPE,
            ctypes.byref(backdrop_val),
            ctypes.sizeof(backdrop_val)
        )
        if hr == 0:
            success = True
    except Exception:
        pass

    # 4. Windows 10 & 11 SetWindowCompositionAttribute (Acrylic / BlurBehind)
    try:
        h = gradient_color_hex.lstrip("#")
        if len(h) == 6:
            r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        else:
            r, g, b = (11, 15, 25) if is_dark else (240, 244, 250)

        alpha = max(0, min(255, int(opacity * 255)))
        # Win32 ABGR format: (A << 24) | (B << 16) | (G << 8) | R
        gradient_color = (alpha << 24) | (b << 16) | (g << 8) | r

        accent = ACCENT_POLICY()
        accent.AccentState = 4  # ACCENT_ENABLE_ACRYLICBLURBEHIND (or 3 for BlurBehind)
        accent.AccentFlags = 2  # Draw border/full
        accent.GradientColor = gradient_color
        accent.AnimationId = 0

        data = WINDOWCOMPOSITIONATTRIB_DATA()
        data.Attribute = 19  # WCA_ACCENT_POLICY
        data.Data = ctypes.cast(ctypes.byref(accent), ctypes.c_void_p)
        data.SizeOfData = ctypes.sizeof(accent)

        user32 = ctypes.windll.user32
        if hasattr(user32, "SetWindowCompositionAttribute"):
            user32.SetWindowCompositionAttribute.restype = ctypes.c_bool
            user32.SetWindowCompositionAttribute.argtypes = [ctypes.c_void_p, ctypes.POINTER(WINDOWCOMPOSITIONATTRIB_DATA)]
            res = user32.SetWindowCompositionAttribute(ctypes.c_void_p(hwnd), ctypes.byref(data))
            if res:
                success = True
    except Exception as e:
        print(f"[Win32 Acrylic Exception]: {e}")

    return success


def _run_winrt_in_worker_thread(async_func, timeout_sec=2.0):
    import concurrent.futures
    import ctypes

    COINIT_MULTITHREADED = 0x0
    COINIT_DISABLE_OLE1DDE = 0x4

    def _worker():
        try:
            ctypes.windll.ole32.CoInitializeEx(None, COINIT_MULTITHREADED | COINIT_DISABLE_OLE1DDE)
        except Exception:
            pass
        try:
            return asyncio.run(async_func())
        finally:
            try:
                ctypes.windll.ole32.CoUninitialize()
            except Exception:
                pass

    executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    try:
        future = executor.submit(_worker)
        res = future.result(timeout=timeout_sec)
        executor.shutdown(wait=False, cancel_futures=True)
        return res
    except Exception as e:
        executor.shutdown(wait=False, cancel_futures=True)
        return {"error": str(e)}


def _get_pycaw_volume_interface():
    if not HAS_PYCAW:
        return None
    try:
        try:
            from comtypes import CoInitialize
            CoInitialize()
        except Exception:
            pass
        devices = AudioUtilities.GetSpeakers()
        if not devices:
            return None
        if hasattr(devices, 'EndpointVolume'):
            return devices.EndpointVolume
        elif hasattr(devices, 'Activate'):
            interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            return interface.QueryInterface(IAudioEndpointVolume)
        return None
    except Exception as e:
        print(f"[Sound Pycaw Interface Error]: {e}")
        return None


class SystemMonitor:
    @staticmethod
    def purge_system_ram() -> bool:
        """Purges memory working sets using Win32 EmptyWorkingSet C-API."""
        try:
            psapi = ctypes.windll.psapi
            res = psapi.EmptyWorkingSet(-1)
            return bool(res)
        except Exception as e:
            print(f"RAM purge exception: {e}")
            return False

    @staticmethod
    def is_mic_muted() -> bool:
        if not HAS_PYCAW:
            return False
        try:
            vol_iface = _get_pycaw_volume_interface()
            if vol_iface:
                return bool(vol_iface.GetMute())
            return False
        except Exception:
            return False

    @staticmethod
    def set_mic_mute(muted: bool):
        if not HAS_PYCAW:
            return
        try:
            vol_iface = _get_pycaw_volume_interface()
            if vol_iface:
                vol_iface.SetMute(bool(muted), None)
        except Exception as e:
            print(f"Set mic mute exception: {e}")

    @staticmethod
    def get_master_mute() -> bool:
        try:
            vol_iface = _get_pycaw_volume_interface()
            if vol_iface:
                return bool(vol_iface.GetMute())
            return False
        except Exception as e:
            print(f"[Sound Control Error]: get_master_mute failed: {e}")
            return False

    @staticmethod
    def set_master_mute(muted: bool):
        try:
            vol_iface = _get_pycaw_volume_interface()
            if vol_iface:
                vol_iface.SetMute(bool(muted), None)
                print(f"[Sound Control Success]: System master mute set to {muted} via Pycaw.")
            else:
                print("[Sound Control Error]: Pycaw volume interface unavailable for master mute.")
        except Exception as e:
            print(f"[Sound Control Exception]: set_master_mute({muted}) failed: {e}")

    @staticmethod
    def get_master_volume() -> int:
        try:
            vol_iface = _get_pycaw_volume_interface()
            if vol_iface:
                return int(round(vol_iface.GetMasterVolumeLevelScalar() * 100))
            return 50
        except Exception as e:
            print(f"[Sound Telemetry Error]: get_master_volume exception: {e}")
            return 50

    @staticmethod
    def set_master_volume(level: int):
        try:
            vol_iface = _get_pycaw_volume_interface()
            if vol_iface:
                scalar = max(0.0, min(1.0, level / 100.0))
                vol_iface.SetMasterVolumeLevelScalar(scalar, None)
                print(f"[Sound Control Success]: Master volume set to {level}% (scalar={scalar:.2f}) via Pycaw.")
            else:
                print("[Sound Control Error]: Pycaw volume interface unavailable for master volume.")
        except Exception as e:
            print(f"[Sound Control Exception]: set_master_volume({level}%) failed: {e}")

    @staticmethod
    def play_alarm_sound_effect(sound_path: str = None):
        """Plays alarm audio notification with custom file support, bundled default tone asset, and multi-stage fallback."""
        import sys
        default_wav = os.path.join(os.path.dirname(__file__), "assets", "sounds", "default_alarm.wav")
        if getattr(sys, 'frozen', False):
            meipass = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
            frozen_wav = os.path.join(meipass, "assets", "sounds", "default_alarm.wav")
            if os.path.exists(frozen_wav):
                default_wav = frozen_wav

        target_file = None
        if not sound_path or sound_path in ["default_alarm", "system_exclamation", "system_asterisk", "system_notification"]:
            if os.path.exists(default_wav):
                target_file = default_wav
        elif os.path.exists(sound_path):
            target_file = sound_path

        if target_file and os.path.exists(target_file):
            try:
                import winsound
                print(f"[Sound Alarm Action]: Playing alarm sound file '{target_file}' via winsound...", flush=True)
                winsound.PlaySound(target_file, winsound.SND_FILENAME | winsound.SND_ASYNC)
                print("[Sound Alarm Success]: PlaySound executed cleanly.", flush=True)
                return
            except Exception as e:
                print(f"[Sound Alarm Warning]: PlaySound filename failed: {e}", flush=True)

        # Fallback to system exclamation sound alias
        try:
            import winsound
            print("[Sound Alarm Action]: Attempting winsound.PlaySound('SystemExclamation')...", flush=True)
            winsound.PlaySound("SystemExclamation", winsound.SND_ALIAS | winsound.SND_ASYNC)
            print("[Sound Alarm Success]: PlaySound executed cleanly.", flush=True)
            return
        except Exception as e1:
            print(f"[Sound Alarm Warning]: PlaySound failed: {e1}", flush=True)

        try:
            import winsound
            winsound.MessageBeep(winsound.MB_ICONASTERISK)
        except Exception:
            pass

    @staticmethod
    def get_brightness() -> int:
        if not HAS_SBC:
            return 100
        try:
            val = sbc.get_brightness()
            if isinstance(val, list) and val:
                return int(val[0])
            elif isinstance(val, int):
                return val
            return 100
        except Exception:
            return 100

    @staticmethod
    def set_brightness(level: int):
        if not HAS_SBC:
            return
        try:
            sbc.set_brightness(level)
        except Exception as e:
            print(f"Set brightness exception: {e}")

    @staticmethod
    def is_caps_lock_on() -> bool:
        try:
            return bool(ctypes.windll.user32.GetKeyState(VK_CAPITAL) & 1)
        except Exception:
            return False

    @staticmethod
    def is_num_lock_on() -> bool:
        try:
            return bool(ctypes.windll.user32.GetKeyState(VK_NUMLOCK) & 1)
        except Exception:
            return False

    @staticmethod
    def get_battery_info():
        try:
            battery = psutil.sensors_battery()
            if battery is not None:
                return {
                    'percent': int(battery.percent),
                    'charging': bool(battery.power_plugged)
                }
        except Exception:
            pass
        return {'percent': 100, 'charging': False}


    @staticmethod
    def get_cpu_usage() -> int:
        try:
            return int(psutil.cpu_percent(interval=None))
        except Exception:
            return 0

    @staticmethod
    def get_per_cpu_usage() -> list:
        try:
            return [int(x) for x in psutil.cpu_percent(interval=None, percpu=True)]
        except Exception:
            return [0]

    @staticmethod
    def get_ram_details() -> dict:
        try:
            v = psutil.virtual_memory()
            total_gb = round(v.total / (1024 ** 3), 1)
            used_gb = round(v.used / (1024 ** 3), 1)
            return {'total_gb': total_gb, 'used_gb': used_gb, 'percent': int(v.percent)}
        except Exception:
            return {'total_gb': 16.0, 'used_gb': 8.0, 'percent': 50}

    @staticmethod
    def get_process_count() -> int:
        try:
            return len(psutil.pids())
        except Exception:
            return 0

    @staticmethod
    def get_disk_info() -> dict:
        try:
            usage = psutil.disk_usage('C:\\')
            total_gb = round(usage.total / (1024 ** 3), 1)
            used_gb = round(usage.used / (1024 ** 3), 1)
            percent = int(usage.percent)
            return {'total_gb': total_gb, 'used_gb': used_gb, 'percent': percent}
        except Exception:
            return {'total_gb': 500, 'used_gb': 250, 'percent': 50}

    @staticmethod
    def get_uptime_string() -> str:
        try:
            boot_time = psutil.boot_time()
            uptime_seconds = int(time.time() - boot_time)
            hours = uptime_seconds // 3600
            minutes = (uptime_seconds % 3600) // 60
            days = hours // 24
            hours = hours % 24
            if days > 0:
                return f"{days}d {hours}h {minutes}m"
            return f"{hours}h {minutes}m"
        except Exception:
            return "0h 0m"

    @staticmethod
    def get_boot_timestamp() -> str:
        try:
            boot_time = psutil.boot_time()
            return datetime.fromtimestamp(boot_time).strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            return "--"

    @staticmethod
    def get_network_io() -> dict:
        try:
            net = psutil.net_io_counters()
            sent_mb = round(net.bytes_sent / (1024 * 1024), 1)
            recv_mb = round(net.bytes_recv / (1024 * 1024), 1)
            return {'sent_mb': sent_mb, 'recv_mb': recv_mb}
        except Exception:
            return {'sent_mb': 0, 'recv_mb': 0}

    @staticmethod
    def get_disk_io() -> dict:
        try:
            dio = psutil.disk_io_counters()
            read_mb = round(dio.read_bytes / (1024 * 1024), 1) if dio else 0
            write_mb = round(dio.write_bytes / (1024 * 1024), 1) if dio else 0
            return {'read_mb': read_mb, 'write_mb': write_mb}
        except Exception:
            return {'read_mb': 0, 'write_mb': 0}

    @staticmethod
    def get_wifi_network_info() -> dict:
        try:
            ssid = ""
            signal = ""
            # On Windows, query netsh wlan show interfaces for active Wi-Fi SSID and Signal
            try:
                import subprocess
                flags = 0x08000000 if os.name == 'nt' else 0  # CREATE_NO_WINDOW
                proc = subprocess.run(
                    ["netsh", "wlan", "show", "interfaces"],
                    capture_output=True,
                    text=True,
                    timeout=1.5,
                    creationflags=flags
                )
                if proc.returncode == 0 and proc.stdout:
                    for line in proc.stdout.splitlines():
                        line_str = line.strip()
                        if line_str.startswith("SSID") and not line_str.startswith("BSSID"):
                            parts = line_str.split(":", 1)
                            if len(parts) > 1:
                                ssid = parts[1].strip()
                        elif line_str.startswith("Signal"):
                            parts = line_str.split(":", 1)
                            if len(parts) > 1:
                                signal = parts[1].strip()
            except Exception:
                pass

            stats = psutil.net_if_stats()
            active_iface = None
            is_connected = False
            for name, stat in stats.items():
                if stat.isup and not name.startswith("Loopback") and not "vEthernet" in name:
                    is_connected = True
                    active_iface = name
                    break

            if is_connected and active_iface:
                clean_name = active_iface.replace("Ethernet", "Ethernet").replace("Wi-Fi", "Wi-Fi Network")
                return {
                    "connected": True,
                    "name": clean_name,
                    "ssid": ssid,
                    "signal": signal
                }
            elif ssid:
                return {
                    "connected": True,
                    "name": "Wi-Fi Network",
                    "ssid": ssid,
                    "signal": signal
                }
            return {"connected": False, "name": "Disconnected", "ssid": "", "signal": ""}
        except Exception:
            return {"connected": False, "name": "Offline", "ssid": "", "signal": ""}

    @staticmethod
    def is_hotspot_active() -> bool:
        """Detects if Windows Mobile Hotspot / Virtual Wi-Fi Direct interface is active."""
        try:
            stats = psutil.net_if_stats()
            for name, stat in stats.items():
                if stat.isup:
                    lower_name = name.lower()
                    if "wi-fi direct" in lower_name or "hotspot" in lower_name or ("local area connection*" in lower_name and "vethernet" not in lower_name):
                        return True
            try:
                import subprocess
                flags = 0x08000000 if os.name == 'nt' else 0
                res = subprocess.run(["netsh", "wlan", "show", "hostednetwork"], capture_output=True, text=True, timeout=1.0, creationflags=flags)
                if res.returncode == 0 and "Status                 : Started" in res.stdout:
                    return True
            except Exception:
                pass
            return False
        except Exception:
            return False

    @staticmethod
    def get_windows_theme_mode() -> str:
        """Queries Windows AppsUseLightTheme registry setting to detect system Dark/Light mode."""
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize")
            val, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
            winreg.CloseKey(key)
            return "light" if val == 1 else "dark"
        except Exception:
            return "dark"

    @staticmethod
    def is_focus_assist_or_fullscreen_active() -> bool:
        """Detects if Windows Focus Assist / Do Not Disturb or Fullscreen D3D gaming is active."""
        try:
            import ctypes
            state = ctypes.c_int()
            res = ctypes.windll.shell32.SHQueryUserNotificationState(ctypes.byref(state))
            if res == 0:
                # 2: QUNS_BUSY, 3: QUNS_RUNNING_D3D_FULL_SCREEN, 4: QUNS_PRESENTATION_MODE, 6: QUNS_QUIET_TIME (Focus Assist)
                return state.value in (2, 3, 4, 6)
            return False
        except Exception:
            return False

    @staticmethod
    def media_next():
        """Simulates VK_MEDIA_NEXT_TRACK to skip to the next track."""
        try:
            import ctypes
            VK_MEDIA_NEXT_TRACK = 0xB0
            ctypes.windll.user32.keybd_event(VK_MEDIA_NEXT_TRACK, 0, 0, 0)
            ctypes.windll.user32.keybd_event(VK_MEDIA_NEXT_TRACK, 0, 2, 0)
        except Exception as e:
            print(f"[Media Next Error]: {e}")

    @staticmethod
    def media_play_pause():
        """Simulates VK_MEDIA_PLAY_PAUSE to toggle media playback."""
        try:
            import ctypes
            VK_MEDIA_PLAY_PAUSE = 0xB3
            ctypes.windll.user32.keybd_event(VK_MEDIA_PLAY_PAUSE, 0, 0, 0)
            ctypes.windll.user32.keybd_event(VK_MEDIA_PLAY_PAUSE, 0, 2, 0)
        except Exception as e:
            print(f"[Media Play/Pause Error]: {e}")

    @staticmethod
    def media_previous():
        """Simulates VK_MEDIA_PREV_TRACK to return to the previous track."""
        try:
            import ctypes
            VK_MEDIA_PREV_TRACK = 0xB1
            ctypes.windll.user32.keybd_event(VK_MEDIA_PREV_TRACK, 0, 0, 0)
            ctypes.windll.user32.keybd_event(VK_MEDIA_PREV_TRACK, 0, 2, 0)
        except Exception as e:
            print(f"[Media Prev Error]: {e}")

    @staticmethod
    def get_top_cpu_process() -> str:
        try:
            top_p = None
            max_cpu = -1.0
            for p in psutil.process_iter(['name', 'cpu_percent']):
                try:
                    cpu_p = p.info.get('cpu_percent') or 0.0
                    if cpu_p > max_cpu:
                        max_cpu = cpu_p
                        top_p = p.info.get('name') or "System"
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            if top_p:
                return f"{top_p} ({max_cpu:.1f}%)"
            return "System (0.0%)"
        except Exception:
            return "--"

    @staticmethod
    def get_now_playing_info() -> dict:
        """Retrieves rich Now Playing metadata & thumbnail via Windows Media Session API in worker thread."""
        if not HAS_WINRT:
            return {"is_playing": False, "status": "none"}

        async def _async_fetch():
            try:
                manager = await asyncio.wait_for(winrt_mc.GlobalSystemMediaTransportControlsSessionManager.request_async(), timeout=1.5)
                session = manager.get_current_session()
                if not session:
                    return {"is_playing": False, "status": "none"}

                playback = session.get_playback_info()
                status_enum = playback.playback_status if playback else None
                is_playing = (status_enum == winrt_mc.GlobalSystemMediaTransportControlsSessionPlaybackStatus.PLAYING)
                status_str = "playing" if is_playing else ("paused" if status_enum == winrt_mc.GlobalSystemMediaTransportControlsSessionPlaybackStatus.PAUSED else "stopped")

                props = await asyncio.wait_for(session.try_get_media_properties_async(), timeout=1.5)
                title = props.title if props and props.title else "Unknown Track"
                artist = props.artist if props and props.artist else "Unknown Artist"

                app_id = session.source_app_user_model_id or "Media Player"
                app_name = app_id.split("!")[0].split("\\")[-1].replace(".exe", "").capitalize()
                if "spotify" in app_id.lower():
                    app_name = "Spotify"
                elif "chrome" in app_id.lower():
                    app_name = "YouTube — Chrome"
                elif "msedge" in app_id.lower():
                    app_name = "Edge"

                pos_sec, dur_sec = 0, 0
                try:
                    timeline = session.get_timeline_properties()
                    if timeline:
                        dur_sec = int(timeline.end_time.total_seconds())
                        base_pos = timeline.position.total_seconds()
                        if is_playing and timeline.last_updated_time:
                            import datetime
                            now_utc = datetime.datetime.now(datetime.timezone.utc)
                            elapsed = (now_utc - timeline.last_updated_time).total_seconds()
                            pos_sec = int(min(dur_sec, max(0, base_pos + elapsed)))
                        else:
                            pos_sec = int(base_pos)
                except Exception:
                    pass

                thumb_bytes = None
                if props and props.thumbnail:
                    try:
                        stream = await asyncio.wait_for(props.thumbnail.open_read_async(), timeout=1.0)
                        size = stream.size
                        if size > 0:
                            reader = winrt_ss.DataReader(stream)
                            await asyncio.wait_for(reader.load_async(size), timeout=1.0)
                            buf = bytearray(size)
                            reader.read_bytes(buf)
                            thumb_bytes = bytes(buf)
                    except Exception:
                        pass

                return {
                    "is_playing": is_playing,
                    "status": status_str,
                    "title": title,
                    "artist": artist,
                    "app_name": app_name,
                    "app_id": app_id,
                    "position_sec": pos_sec,
                    "duration_sec": dur_sec,
                    "thumbnail_bytes": thumb_bytes
                }
            except Exception as e:
                return {"is_playing": False, "status": "none", "error": str(e)}

        res = _run_winrt_in_worker_thread(_async_fetch, timeout_sec=2.0)
        return res if isinstance(res, dict) else {"is_playing": False, "status": "none"}

    @staticmethod
    def set_media_position(seconds: int) -> bool:
        """Seeks active Windows Media Session to specified position in seconds via WinRT."""
        if not HAS_WINRT:
            return False

        async def _async_seek():
            try:
                manager = await asyncio.wait_for(winrt_mc.GlobalSystemMediaTransportControlsSessionManager.request_async(), timeout=1.5)
                session = manager.get_current_session()
                if session:
                    ticks = int(seconds * 10_000_000)
                    print(f"[Media Seek]: Calling try_change_playback_position_async({seconds}s / {ticks} ticks) on active session ({session.source_app_user_model_id})...")
                    res = await asyncio.wait_for(session.try_change_playback_position_async(ticks), timeout=1.5)
                    print(f"[Media Seek Result]: {res}")
                    return bool(res)
                return False
            except Exception as e:
                print(f"[Media Seek Exception]: {e}")
                return False

        res = _run_winrt_in_worker_thread(_async_seek, timeout_sec=2.0)
        return bool(res)

    @staticmethod
    def trigger_media_play_pause():
        """Real session Play/Pause action via Windows Media Session API in worker thread."""
        if not HAS_WINRT:
            return
        async def _async_action():
            try:
                manager = await asyncio.wait_for(winrt_mc.GlobalSystemMediaTransportControlsSessionManager.request_async(), timeout=1.5)
                session = manager.get_current_session()
                if session:
                    playback = session.get_playback_info()
                    if playback and playback.playback_status == winrt_mc.GlobalSystemMediaTransportControlsSessionPlaybackStatus.PLAYING:
                        await asyncio.wait_for(session.try_pause_async(), timeout=1.5)
                    else:
                        await asyncio.wait_for(session.try_play_async(), timeout=1.5)
            except Exception as e:
                print("Media play/pause error:", e)

        _run_winrt_in_worker_thread(_async_action, timeout_sec=2.0)

    @staticmethod
    def trigger_media_next():
        """Real session Skip Next action via Windows Media Session API in worker thread."""
        if not HAS_WINRT:
            return
        async def _async_action():
            try:
                manager = await asyncio.wait_for(winrt_mc.GlobalSystemMediaTransportControlsSessionManager.request_async(), timeout=1.5)
                session = manager.get_current_session()
                if session:
                    await asyncio.wait_for(session.try_skip_next_async(), timeout=1.5)
            except Exception as e:
                print("Media next error:", e)

        _run_winrt_in_worker_thread(_async_action, timeout_sec=2.0)

    @staticmethod
    def trigger_media_prev():
        """Real session Skip Previous action via Windows Media Session API in worker thread."""
        if not HAS_WINRT:
            return
        async def _async_action():
            try:
                manager = await asyncio.wait_for(winrt_mc.GlobalSystemMediaTransportControlsSessionManager.request_async(), timeout=1.5)
                session = manager.get_current_session()
                if session:
                    await asyncio.wait_for(session.try_skip_previous_async(), timeout=1.5)
            except Exception as e:
                print("Media prev error:", e)

        _run_winrt_in_worker_thread(_async_action, timeout_sec=2.0)

    @staticmethod
    def get_windows_notifications() -> dict:
        """Retrieves recent toast notifications via UserNotificationListener API in worker thread."""
        if not HAS_WINRT:
            print("[Notif] Access result: unsupported (HAS_WINRT is False)", flush=True)
            return {"status": "unsupported", "notifications": []}

        async def _async_fetch():
            try:
                print("[Notif] Requesting access...", flush=True)
                listener = winrt_nm.UserNotificationListener.current
                access = await asyncio.wait_for(listener.request_access_async(), timeout=1.5)
                print(f"[Notif] Access result: {access}", flush=True)
                if access != winrt_nm.UserNotificationListenerAccessStatus.ALLOWED:
                    print(f"[Notif] Access denied or ungranted status: {access}", flush=True)
                    return {"status": "denied", "notifications": []}

                print("[Notif] Listener subscribed: Toast notification query executing...", flush=True)
                notifs = await asyncio.wait_for(listener.get_notifications_async(winrt_un.NotificationKinds.TOAST), timeout=1.5)
                
                # Only capture notifications created during current session (after app start time - 10s grace)
                app_start = getattr(SystemMonitor, '_app_start_time', None)
                if app_start is None:
                    app_start = datetime.now(timezone.utc) - timedelta(seconds=10)
                    SystemMonitor._app_start_time = app_start

                items = []
                for n in list(notifs):
                    try:
                        if hasattr(n, "creation_time") and n.creation_time:
                            c_time = n.creation_time
                            if hasattr(c_time, "tzinfo") and c_time.tzinfo is None:
                                c_time = c_time.replace(tzinfo=timezone.utc)
                            if c_time < app_start:
                                continue

                        app_name = n.app_info.display_info.display_name if n.app_info and n.app_info.display_info else "App"
                        app_id = n.app_info.app_user_model_id if n.app_info else ""
                        binding = n.notification.visual.get_binding(winrt_un.KnownNotificationBindings.toast_generic)
                        title_text = ""
                        body_text = ""
                        if binding:
                            elems = [e.text for e in binding.get_text_elements()]
                            if len(elems) > 0:
                                title_text = elems[0]
                            if len(elems) > 1:
                                body_text = " ".join(elems[1:])

                        launch_url = ""
                        full_str = f"{title_text} {body_text}"
                        url_match = re.search(r'https?://[^\s>"]+', full_str)
                        if url_match:
                            launch_url = url_match.group(0)

                        print(f"[Notif] Notification received: app='{app_name}', title='{title_text}'", flush=True)

                        items.append({
                            "id": str(n.id),
                            "app_name": app_name,
                            "app_id": app_id,
                            "title": title_text or "Notification",
                            "body": body_text,
                            "launch_url": launch_url,
                            "timestamp": datetime.now().strftime("%H:%M")
                        })
                    except Exception as e_item:
                        print(f"[Notif Item Exception]: {e_item}", flush=True)

                print(f"[Notif] Saved to storage: Captured {len(items)} notification(s)", flush=True)
                return {"status": "allowed", "notifications": items}
            except Exception as e:
                print(f"[Notif Exception]: {e}", flush=True)
                return {"status": "error", "notifications": [], "error": str(e)}

        res = _run_winrt_in_worker_thread(_async_fetch, timeout_sec=2.0)
        return res if isinstance(res, dict) else {"status": "error", "notifications": []}

    @staticmethod
    def focus_app_window(app_name: str, app_id: str = ""):
        """Brings the source app window to the foreground."""
        try:
            user32 = ctypes.windll.user32
            target_query = app_name.lower().split(" ")[0]

            def enum_windows_callback(hwnd, extra):
                if user32.IsWindowVisible(hwnd):
                    length = user32.GetWindowTextLengthW(hwnd)
                    if length > 0:
                        buff = ctypes.create_unicode_buffer(length + 1)
                        user32.GetWindowTextW(hwnd, buff, length + 1)
                        title = buff.value.lower()
                        if target_query in title:
                            user32.ShowWindow(hwnd, 9)  # SW_RESTORE
                            user32.SetForegroundWindow(hwnd)
                            return False
                return True

            WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.c_int)
            user32.EnumWindows(WNDENUMPROC(enum_windows_callback), 0)
        except Exception as e:
            print("Focus app window error:", e)


class TelemetryWorkerThread(QThread):
    """Dedicated background thread for hardware telemetry monitoring to prevent GUI micro-stuttering."""
    telemetry_updated = pyqtSignal(dict)

    def __init__(self, interval_ms=250, parent=None):
        super().__init__(parent)
        self.interval_ms = interval_ms
        self.running = True

    def stop(self):
        self.running = False
        self.quit()
        self.wait(500)

    def run(self):
        while self.running:
            try:
                caps_on = SystemMonitor.is_caps_lock_on()
                num_on = SystemMonitor.is_num_lock_on()
                battery = SystemMonitor.get_battery_info()
                volume = SystemMonitor.get_master_volume()
                brightness = SystemMonitor.get_brightness()
                cpu = SystemMonitor.get_cpu_usage()
                per_cpu = SystemMonitor.get_per_cpu_usage()
                ram_info = SystemMonitor.get_ram_details()
                proc_count = SystemMonitor.get_process_count()
                disk = SystemMonitor.get_disk_info()
                uptime = SystemMonitor.get_uptime_string()
                boot_timestamp = SystemMonitor.get_boot_timestamp()
                net_io = SystemMonitor.get_network_io()
                disk_io = SystemMonitor.get_disk_io()
                top_proc = SystemMonitor.get_top_cpu_process()
                net_info = SystemMonitor.get_wifi_network_info()
                mic_muted = SystemMonitor.is_mic_muted()

                data = {
                    'caps_on': caps_on,
                    'num_on': num_on,
                    'battery': battery,
                    'volume': volume,
                    'brightness': brightness,
                    'cpu': cpu,
                    'per_cpu': per_cpu,
                    'ram_info': ram_info,
                    'ram': ram_info.get('percent', 0),
                    'proc_count': proc_count,
                    'disk': disk,
                    'uptime': uptime,
                    'boot_timestamp': boot_timestamp,
                    'net_io': net_io,
                    'disk_io': disk_io,
                    'net_info': net_info,
                    'mic_muted': mic_muted,
                    'charging': battery.get('charging', False)
                }
                self.telemetry_updated.emit(data)
            except Exception as e:
                print(f"Telemetry worker thread exception: {e}")

            self.msleep(self.interval_ms)


class NowPlayingWorkerThread(QThread):
    """Dedicated background worker thread for non-blocking WinRT Media Session updates."""
    media_info_updated = pyqtSignal(dict)

    def __init__(self, interval_ms=1000, parent=None):
        super().__init__(parent)
        self.interval_ms = interval_ms
        self.running = True

    def stop(self):
        self.running = False
        self.quit()
        self.wait(150)

    def run(self):
        try:
            try:
                import ctypes
                COINIT_MULTITHREADED = 0x0
                ctypes.windll.ole32.CoInitializeEx(None, COINIT_MULTITHREADED)
            except Exception:
                pass

            while self.running:
                try:
                    info = SystemMonitor.get_now_playing_info()
                    self.media_info_updated.emit(info)
                except Exception as e:
                    print(f"[Now Playing Worker Thread Exception]: {e}")
                for _ in range(max(1, int(self.interval_ms / 100))):
                    if not self.running:
                        break
                    self.msleep(100)
        except Exception as e:
            print(f"[Now Playing Worker Thread Fatal Exception]: {e}")


class NotificationsWorkerThread(QThread):
    """Dedicated background worker thread for non-blocking WinRT Notifications fetching."""
    notifications_ready = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)

    def run(self):
        try:
            try:
                import ctypes
                COINIT_MULTITHREADED = 0x0
                ctypes.windll.ole32.CoInitializeEx(None, COINIT_MULTITHREADED)
            except Exception:
                pass

            res = SystemMonitor.get_windows_notifications()
            self.notifications_ready.emit(res)
        except Exception as e:
            print(f"[Notifications Worker Thread Exception]: {e}")


class PriorityNotificationWorkerThread(QThread):
    """Dedicated background worker thread for priority notifications (Zero GUI thread blocking)."""
    priority_notification_found = pyqtSignal(dict)

    def __init__(self, settings, interval_ms=2500, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.interval_ms = interval_ms
        self.running = True
        self.seen_notification_ids = set()

    def stop(self):
        self.running = False
        self.quit()
        self.wait(150)

    def run(self):
        try:
            try:
                import ctypes
                COINIT_MULTITHREADED = 0x0
                ctypes.windll.ole32.CoInitializeEx(None, COINIT_MULTITHREADED)
            except Exception:
                pass

            while self.running:
                if self.settings.get("notification_popup_enabled", True):
                    priority_apps = [a.lower().strip() for a in self.settings.get("popup_notification_apps", []) if a.strip()]
                    if priority_apps:
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
                                        self.priority_notification_found.emit(notif)
                                        break
                        except Exception:
                            pass

                for _ in range(max(1, int(self.interval_ms / 100))):
                    if not self.running:
                        break
                    self.msleep(100)
        except Exception as e:
            print(f"[Priority Notif Worker Exception]: {e}")


class AlarmSchedulerWorkerThread(QThread):
    """
    Dedicated, isolated background worker thread for Alarms & Timetable scheduling.
    Runs in its own OS thread with high-precision sub-second timing.
    Completely decoupled from UI event loops, live synchronization, and paint passes.
    """
    alarm_due = pyqtSignal(dict)

    def __init__(self, storage, parent=None):
        super().__init__(parent)
        self.storage = storage
        self.running = True
        self.triggered_keys_today = set()
        self.last_checked_date = ""

    def stop(self):
        self.running = False
        self.quit()
        self.wait(150)

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
            print(f"[SCHEDULER THREAD PREPOPULATE ALARMS ERROR]: {e}", flush=True)

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
            print(f"[SCHEDULER THREAD PREPOPULATE TIMETABLE ERROR]: {e}", flush=True)

    def run(self):
        while self.running:
            try:
                now_dt = datetime.now()
                now_str = now_dt.strftime("%H:%M")
                now_total_min = now_dt.hour * 60 + now_dt.minute
                today_str = now_dt.strftime("%Y-%m-%d")

                day_abbrs = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
                today_day = day_abbrs[now_dt.weekday()]

                # Midnight rollover / Startup Init
                if today_str != self.last_checked_date:
                    is_initial_startup = (self.last_checked_date == "")
                    self.last_checked_date = today_str
                    self.triggered_keys_today.clear()
                    if is_initial_startup:
                        self.prepopulate_past_keys_today(now_dt)
                    try:
                        timetable = self.storage.load_timetable()
                        dirty = False
                        for entry in timetable:
                            if entry.get("days") and entry.get("is_completed", False):
                                entry["is_completed"] = False
                                dirty = True
                        if dirty:
                            self.storage.save_timetable(timetable)
                    except Exception:
                        pass

                # Check Alarms
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

                    if a_min < 0:
                        continue

                    diff_min = now_total_min - a_min
                    if 0 <= diff_min <= 1:
                        days = alarm.get("days", [])
                        day_match = (not days) or any(str(d).lower().startswith(today_day.lower()[:3]) for d in days)
                        if day_match:
                            trigger_key = f"alarm_{alarm.get('id')}_{today_str}_{alarm_time}"
                            if trigger_key not in self.triggered_keys_today:
                                self.triggered_keys_today.add(trigger_key)
                                label = alarm.get("label", "Alarm")
                                sound_val = alarm.get("sound", "system_exclamation")
                                print(f"[SCHEDULER THREAD]: Alarm due! Scheduled={alarm_time}, SystemTime={now_dt.strftime('%H:%M:%S')}, Label='{label}'", flush=True)
                                self.alarm_due.emit({
                                    "title": label,
                                    "is_timetable": False,
                                    "time_str": now_str,
                                    "days": days,
                                    "task_id": "",
                                    "sound_path": sound_val
                                })
                                break

                # Check Timetable
                timetable = self.storage.load_timetable()
                for entry in timetable:
                    if entry.get("is_completed", False):
                        continue
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

                    if tt_min < 0:
                        continue

                    diff_min = now_total_min - tt_min
                    if 0 <= diff_min <= 1:
                        days = entry.get("days", [])
                        day_match = (not days) or any(str(d).lower().startswith(today_day.lower()[:3]) for d in days)
                        if day_match:
                            entry_id = str(entry.get("id", ""))
                            trigger_key = f"timetable_{entry_id}_{today_str}_{tt_time}"
                            if trigger_key not in self.triggered_keys_today:
                                self.triggered_keys_today.add(trigger_key)
                                title_str = entry.get("title", "Timetable Task")
                                sound_val = entry.get("sound", "system_exclamation")
                                print(f"[SCHEDULER THREAD]: Timetable due! Scheduled={tt_time}, SystemTime={now_dt.strftime('%H:%M:%S')}, Task='{title_str}'", flush=True)
                                self.alarm_due.emit({
                                    "title": title_str,
                                    "is_timetable": True,
                                    "time_str": now_str,
                                    "days": days,
                                    "task_id": entry_id,
                                    "sound_path": sound_val
                                })
                                break
            except Exception as e:
                print(f"[Scheduler Worker Thread Exception]: {e}", flush=True)

            # Sleep 500ms between checks
            for _ in range(5):
                if not self.running:
                    break
                self.msleep(100)

