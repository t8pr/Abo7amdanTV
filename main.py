import os
import sys
import subprocess
import time
import threading
import psutil
from flask import Flask, send_from_directory
from screeninfo import get_monitors

if getattr(sys, 'frozen', False):
    base_dir = sys._MEIPASS
else:
    base_dir = os.path.abspath(os.path.dirname(__file__))

template_dir = os.path.join(base_dir, 'templates')
imgs_dir = os.path.join(base_dir, 'imgs')

app = Flask(__name__, template_folder=template_dir, static_folder=template_dir, static_url_path='/static')
app.config['SECRET_KEY'] = 'abo7amdan_secret'

def get_tv_display():
    """Detect the large TV display."""
    try:
        monitors = get_monitors()
        if not monitors: return None
        for m in monitors:
            if m.name and "LCDTV16" in m.name: return m
        for m in monitors:
            if (m.width == 1360 and m.height == 768) or (m.width == 768 and m.height == 1360): return m
    except:
        return None

import ctypes
import ctypes.wintypes
tv_hwnd = None
is_launching = False

def get_os_hwnd():
    """Finds the exact Abo7amdanTV OS window instantly by title and class name."""
    EnumWindows = ctypes.windll.user32.EnumWindows
    EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int))
    GetWindowText = ctypes.windll.user32.GetWindowTextW
    GetWindowTextLength = ctypes.windll.user32.GetWindowTextLengthW
    IsWindowVisible = ctypes.windll.user32.IsWindowVisible

    found_hwnd = None
    def foreach_window(hwnd, lParam):
        nonlocal found_hwnd
        if IsWindowVisible(hwnd):
            class_buff = ctypes.create_unicode_buffer(256)
            ctypes.windll.user32.GetClassNameW(hwnd, class_buff, 256)
            if "Chrome_WidgetWin" not in class_buff.value:
                return True
                
            length = GetWindowTextLength(hwnd)
            if length > 0:
                buff = ctypes.create_unicode_buffer(length + 1)
                GetWindowText(hwnd, buff, length + 1)
                title = buff.value
                
                if ("Abo7amdanTV OS" in title or "localhost:5000" in title) and "Visual Studio Code" not in title:
                    found_hwnd = hwnd
                    return False
        return True
    EnumWindows(EnumWindowsProc(foreach_window), 0)
    return found_hwnd

launch_lock = threading.Lock()

def go_home():
    """Triggered by the Home/Esc key to return to the OS."""
    global tv_hwnd
    if not launch_lock.acquire(blocking=False):
        return
        
    try:
        if tv_hwnd and ctypes.windll.user32.IsWindowVisible(tv_hwnd):
            # Check if we are ALREADY on the home screen to prevent accidental restarts
            length = ctypes.windll.user32.GetWindowTextLengthW(tv_hwnd)
            buff = ctypes.create_unicode_buffer(length + 1)
            ctypes.windll.user32.GetWindowTextW(tv_hwnd, buff, length + 1)
            title = buff.value
            
            if "Abo7amdanTV OS" in title or "localhost:5000" in title:
                return # Already home, do nothing!
                
            # We are on Netflix. Send direct hardware close signal
            ctypes.windll.user32.PostMessageW(tv_hwnd, 0x0112, 0xF060, 0)
            
            # Wait for the window to physically disappear from the screen
            for _ in range(15):
                if not ctypes.windll.user32.IsWindowVisible(tv_hwnd):
                    break
                time.sleep(0.1)
                
            # If Netflix stubbornly refuses to close, force it via native keyboard overrides
            if ctypes.windll.user32.IsWindowVisible(tv_hwnd):
                ctypes.windll.user32.SetForegroundWindow(tv_hwnd)
                time.sleep(0.1)
                
                user32 = ctypes.windll.user32
                # Send Ctrl+W
                user32.keybd_event(0x11, 0, 0, 0) # Ctrl down
                user32.keybd_event(0x57, 0, 0, 0) # W down
                user32.keybd_event(0x57, 0, 0x0002, 0) # W up
                user32.keybd_event(0x11, 0, 0x0002, 0) # Ctrl up
                time.sleep(0.1)
                
                # Send Alt+F4
                user32.keybd_event(0x12, 0, 0, 0) # Alt down
                user32.keybd_event(0x73, 0, 0, 0) # F4 down
                user32.keybd_event(0x73, 0, 0x0002, 0) # F4 up
                user32.keybd_event(0x12, 0, 0x0002, 0) # Alt up
                
        tv_hwnd = None
        launch_browser()
    finally:
        # Release the lock after a short cooldown to prevent double-presses
        threading.Timer(2.5, launch_lock.release).start()

def hotkey_poller():
    """Polls async keystate. Uses 0% CPU and never swallows keystrokes."""
    VK_HOME = 0x24
    VK_BROWSER_HOME = 0xAC
    VK_ESCAPE = 0x1B
    user32 = ctypes.windll.user32
    while True:
        if (user32.GetAsyncKeyState(VK_HOME) & 0x8000) or \
           (user32.GetAsyncKeyState(VK_BROWSER_HOME) & 0x8000) or \
           (user32.GetAsyncKeyState(VK_ESCAPE) & 0x8000):
            go_home()
            time.sleep(1) # Prevent rapid multi-triggers
        time.sleep(0.05) # 50ms poll rate is extremely lightweight

def enforce_single_instance():
    """Prevents multiple background daemons from running simultaneously and causing lag."""
    mutex_name = "Global\\Abo7amdanTV_OS_Mutex"
    kernel32 = ctypes.windll.kernel32
    mutex = kernel32.CreateMutexW(None, False, mutex_name)
    if kernel32.GetLastError() == 183: # ERROR_ALREADY_EXISTS
        print("An instance is already running. Exiting.")
        sys.exit(0)
    return mutex # Keep a reference alive

def force_foreground(hwnd):
    """Bypasses Windows ForegroundLockTimeout to brutally steal focus on boot."""
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    
    if user32.GetForegroundWindow() == hwnd:
        return True
        
    foreground_hwnd = user32.GetForegroundWindow()
    if not foreground_hwnd:
        user32.SetForegroundWindow(hwnd)
        return user32.GetForegroundWindow() == hwnd
        
    foreground_thread = user32.GetWindowThreadProcessId(foreground_hwnd, None)
    current_thread = kernel32.GetCurrentThreadId()
    
    if foreground_thread != current_thread:
        user32.AttachThreadInput(current_thread, foreground_thread, True)
        user32.BringWindowToTop(hwnd)
        user32.ShowWindow(hwnd, 5) # SW_SHOW
        user32.SetForegroundWindow(hwnd)
        user32.AttachThreadInput(current_thread, foreground_thread, False)
    else:
        user32.SetForegroundWindow(hwnd)
        
    return user32.GetForegroundWindow() == hwnd

def launch_browser(url="http://localhost:5000/os"):
    """Launch Brave perfectly on the TV and capture its handle."""
    global tv_hwnd
    tv_monitor = get_tv_display()
    if tv_monitor:
        args = [
            f"--window-position={tv_monitor.x},{tv_monitor.y}",
            "--start-fullscreen",
            "--disable-session-crashed-bubble",
            f"--app={url}"
        ]
        brave_paths = [
            "brave.exe",
            r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
            r"C:\Program Files (x86)\BraveSoftware\Brave-Browser\Application\brave.exe",
            os.path.expanduser(r"~\AppData\Local\BraveSoftware\Brave-Browser\Application\brave.exe")
        ]
        for path in brave_paths:
            try:
                if path == "brave.exe" or os.path.exists(path):
                    subprocess.Popen([path] + args)
                    
                    while True:
                        tv_hwnd = get_os_hwnd()
                        if tv_hwnd:
                            break
                        time.sleep(0.2)
                    
                    # 1. Physically move the window to the TV monitor instantly
                    ctypes.windll.user32.MoveWindow(tv_hwnd, tv_monitor.x, tv_monitor.y, tv_monitor.width, tv_monitor.height, True)
                    
                    # 2. Aggressively steal focus so the user can interact instantly
                    for _ in range(5):
                        if force_foreground(tv_hwnd):
                            break
                        time.sleep(0.2)
                        
                    break
            except:
                continue

def close_tv_window():
    """Safely closes only the exact TV window we opened."""
    global tv_hwnd
    if tv_hwnd and ctypes.windll.user32.IsWindowVisible(tv_hwnd):
        ctypes.windll.user32.PostMessageW(tv_hwnd, 0x0112, 0xF060, 0)
        
        # Wait up to 1.5 seconds for it to die gracefully
        for _ in range(15):
            if not ctypes.windll.user32.IsWindowVisible(tv_hwnd):
                break
            time.sleep(0.1)
            
        # Force kill if it's being stubborn
        if ctypes.windll.user32.IsWindowVisible(tv_hwnd):
            ctypes.windll.user32.SetForegroundWindow(tv_hwnd)
            time.sleep(0.1)
            user32 = ctypes.windll.user32
            # Send Ctrl+W
            user32.keybd_event(0x11, 0, 0, 0)
            user32.keybd_event(0x57, 0, 0, 0)
            user32.keybd_event(0x57, 0, 0x0002, 0)
            user32.keybd_event(0x11, 0, 0x0002, 0)
            
    tv_hwnd = None

def enforce_main_monitor(tv_monitor):
    """Teleports any normal Brave windows that accidentally opened on the TV back to the main screen."""
    EnumWindows = ctypes.windll.user32.EnumWindows
    EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int))
    GetWindowText = ctypes.windll.user32.GetWindowTextW
    GetWindowTextLength = ctypes.windll.user32.GetWindowTextLengthW
    IsWindowVisible = ctypes.windll.user32.IsWindowVisible

    def foreach_window(hwnd, lParam):
        if IsWindowVisible(hwnd):
            class_buff = ctypes.create_unicode_buffer(256)
            ctypes.windll.user32.GetClassNameW(hwnd, class_buff, 256)
            if "Chrome_WidgetWin" in class_buff.value:
                length = GetWindowTextLength(hwnd)
                if length > 0:
                    buff = ctypes.create_unicode_buffer(length + 1)
                    GetWindowText(hwnd, buff, length + 1)
                    title = buff.value
                    
                    # If it's a Brave window, but NOT our TV OS or Netflix
                    if "Abo7amdanTV OS" not in title and "localhost:5000" not in title and "Netflix" not in title:
                        rect = ctypes.wintypes.RECT()
                        ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect))
                        center_x = (rect.left + rect.right) // 2
                        center_y = (rect.top + rect.bottom) // 2
                        
                        # If the center of the normal window is stuck on the TV monitor
                        if tv_monitor.x <= center_x <= (tv_monitor.x + tv_monitor.width):
                            if tv_monitor.y <= center_y <= (tv_monitor.y + tv_monitor.height):
                                # Teleport it safely to the primary monitor (top-left offset)
                                ctypes.windll.user32.MoveWindow(hwnd, 100, 100, 1280, 720, True)
        return True
    EnumWindows(EnumWindowsProc(foreach_window), 0)

def tv_monitor_loop():
    """Runs continuously. Auto-launches when TV connects, auto-closes when TV disconnects."""
    global is_launching
    while True:
        try:
            tv_monitor = get_tv_display()
            is_tv_on = tv_monitor is not None

            if is_tv_on:
                enforce_main_monitor(tv_monitor)
                if not tv_hwnd and not is_launching:
                    is_launching = True
                    launch_browser()
                    is_launching = False
            else:
                if tv_hwnd:
                    close_tv_window()
        except Exception as e:
            pass
        time.sleep(1.5)

@app.route('/os')
def os_root():
    return send_from_directory(template_dir, 'index.html')

@app.route('/imgs/<path:filename>')
def serve_imgs(filename):
    return send_from_directory(imgs_dir, filename)

if __name__ == '__main__':
    _mutex = enforce_single_instance()
    
    threading.Thread(target=hotkey_poller, daemon=True).start()
    
    threading.Thread(target=tv_monitor_loop, daemon=True).start()
    
    
    app.run(host="127.0.0.1", port=5000)
