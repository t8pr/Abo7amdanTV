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

def get_window_on_monitor(monitor):
    """Finds the Brave window that is physically located on the given monitor."""
    EnumWindows = ctypes.windll.user32.EnumWindows
    EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int))
    GetWindowRect = ctypes.windll.user32.GetWindowRect
    IsWindowVisible = ctypes.windll.user32.IsWindowVisible

    class RECT(ctypes.Structure):
        _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long), ("right", ctypes.c_long), ("bottom", ctypes.c_long)]

    found_hwnd = None

    def foreach_window(hwnd, lParam):
        nonlocal found_hwnd
        if IsWindowVisible(hwnd):
            rect = RECT()
            GetWindowRect(hwnd, ctypes.byref(rect))
            
            if rect.left >= monitor.x and rect.left < monitor.x + monitor.width:
                buff = ctypes.create_unicode_buffer(256)
                ctypes.windll.user32.GetClassNameW(hwnd, buff, 256)
                if "Chrome_WidgetWin" in buff.value:
                    found_hwnd = hwnd
                    return False 
        return True

    EnumWindows(EnumWindowsProc(foreach_window), 0)
    return found_hwnd

def go_home():
    """Triggered by the Home/Esc key to return to the OS."""
    global tv_hwnd
    if tv_hwnd:
        ctypes.windll.user32.PostMessageW(tv_hwnd, 0x0112, 0xF060, 0)
    time.sleep(0.5)
    launch_browser()

def launch_browser(url="http://localhost:5000/os"):
    """Launch Brave perfectly on the TV and capture its handle."""
    global tv_hwnd
    tv_monitor = get_tv_display()
    if tv_monitor:
        args = [
            f"--app={url}",
            f"--window-position={tv_monitor.x},{tv_monitor.y}",
            "--start-fullscreen",
            "--new-window",
            "--disable-session-crashed-bubble"
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
                    time.sleep(2)
                    tv_hwnd = get_window_on_monitor(tv_monitor)
                    break
            except:
                continue

def close_tv_window():
    """Safely closes only the exact TV window we opened."""
    global tv_hwnd
    if tv_hwnd:
        
        ctypes.windll.user32.PostMessageW(tv_hwnd, 0x0112, 0xF060, 0)
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
