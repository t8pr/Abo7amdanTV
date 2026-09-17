import os
import sys
import subprocess
import time
import threading
import psutil
import pyautogui
from flask import Flask, send_from_directory
from screeninfo import get_monitors

pyautogui.FAILSAFE = False


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
        
        
        return None
    except:
        return None

import ctypes
import keyboard

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
            length = GetWindowTextLength(hwnd)
            if length > 0:
                buff = ctypes.create_unicode_buffer(length + 1)
                GetWindowText(hwnd, buff, length + 1)
                title = buff.value
                
                # Must be a Chromium browser window
                class_buff = ctypes.create_unicode_buffer(256)
                ctypes.windll.user32.GetClassNameW(hwnd, class_buff, 256)
                if "Chrome_WidgetWin" not in class_buff.value:
                    return True
                
                # Catch it instantly even while loading (localhost:5000), but exclude VSCode
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
            # Send direct hardware close signal
            ctypes.windll.user32.PostMessageW(tv_hwnd, 0x0112, 0xF060, 0)
            
            # Wait for the window to physically disappear from the screen
            for _ in range(15):
                if not ctypes.windll.user32.IsWindowVisible(tv_hwnd):
                    break
                time.sleep(0.1)
                
            # If Netflix stubbornly refuses to close, force it via keyboard overrides
            if ctypes.windll.user32.IsWindowVisible(tv_hwnd):
                ctypes.windll.user32.SetForegroundWindow(tv_hwnd)
                time.sleep(0.1)
                pyautogui.hotkey('ctrl', 'w')
                time.sleep(0.1)
                pyautogui.hotkey('alt', 'f4')
                
        tv_hwnd = None
        launch_browser()
    finally:
        threading.Timer(2.5, launch_lock.release).start()

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
                    
                    # Wait up to 10 seconds for the window to appear (IPC can be slow)
                    for _ in range(100):
                        tv_hwnd = get_os_hwnd()
                        if tv_hwnd:
                            break
                        time.sleep(0.1)
                    
                    if tv_hwnd:
                        # 1. Force the window physically into the TV monitor
                        ctypes.windll.user32.MoveWindow(tv_hwnd, tv_monitor.x, tv_monitor.y, tv_monitor.width, tv_monitor.height, True)
                        
                        # 2. Aggressively ensure focus before sending F11
                        for _ in range(15):
                            ctypes.windll.user32.SetForegroundWindow(tv_hwnd)
                            time.sleep(0.1)
                            if ctypes.windll.user32.GetForegroundWindow() == tv_hwnd:
                                time.sleep(0.3) # Give Chromium a moment to breathe so F11 doesn't get swallowed
                                keyboard.send('f11')
                                break
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
            pyautogui.hotkey('ctrl', 'w')
            
    tv_hwnd = None

def tv_monitor_loop():
    """Runs continuously. Auto-launches when TV connects, auto-closes when TV disconnects."""
    time.sleep(2)
    was_tv_on = False
    
    while True:
        try:
            tv = get_tv_display()
            is_tv_on = tv is not None
            
            
            if is_tv_on and not was_tv_on:
                print("TV detected. Launching OS...")
                launch_browser()
            
            
            elif not is_tv_on and was_tv_on:
                print("TV turned off. Closing OS window...")
                close_tv_window()
                    
            was_tv_on = is_tv_on
        except Exception as e:
            pass
            
        time.sleep(3)

@app.route('/os')
def os_root():
    return send_from_directory(template_dir, 'index.html')

@app.route('/imgs/<path:filename>')
def serve_imgs(filename):
    return send_from_directory(imgs_dir, filename)

if __name__ == '__main__':
    
    keyboard.add_hotkey('home', go_home)
    keyboard.add_hotkey('esc', go_home)
    
    
    threading.Thread(target=tv_monitor_loop, daemon=True).start()
    
    
    app.run(host="127.0.0.1", port=5000)
