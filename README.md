# Windows Keylogger and System Monitor

This project implements a client-server application for monitoring Windows systems, capturing keystrokes, and taking screenshots. The client (`keyloggermax.py`) runs on the target Windows machine, while the server (`server.py`) collects and stores the data.

## Features

- **Keystroke Logging**: Captures and records all keystrokes.
- **Screenshot Capture**: Periodically takes screenshots of the active desktop.
- **Remote Data Collection**: Sends captured data to a remote server.
- **Server-side Data Storage**: The server receives and stores logs and screenshots, organized by client IP address.

## Installation

To set up the project, follow these steps:

1.  **Clone the repository**:

    ```bash
    git clone https://github.com/DarynOngera/w32loggr.git
    cd w32loggr
    ```

2.  **Create a virtual environment** (recommended):

    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
    ```

3.  **Install dependencies**:

    ```bash
    pip install -r requirements.txt
    ```

4.  **Build the client (Optional - for Windows executable)**:

    The `Makefile` includes a command to build the `keyloggermax.py` into a standalone executable using PyInstaller. This requires PyInstaller to be installed (`pip install pyinstaller`).

    ```bash
    make build
    ```
    This will generate the executable in the `dist/` directory.

## Usage

### Server Setup

Run the server application on your desired machine. This server will listen for incoming connections from the keylogger clients.

```bash
python server.py
```

The server will store received logs in the `remote_logs/` directory, organized by the client's IP address.

### Client Deployment (Windows)

Deploy the `keyloggermax.py` script (or its compiled executable from `dist/`) to the target Windows machine. Ensure that the script is configured to connect to your server's IP address and port.

To run the client:

```bash
python keyloggermax.py
```

**Note**: You may need to configure firewall rules on both the server and client machines to allow communication.

## Directory Structure

```
.gitignore
keyloggermax.py         # Client-side keylogger and system monitor
Makefile                # Build commands (e.g., for PyInstaller)
requirements.txt        # Python dependencies
server.py               # Server-side data collection and storage
SystemMonitor.spec      # PyInstaller spec file
.git/                   # Git repository files
build/                  # PyInstaller build artifacts
dist/                   # Compiled client executable (if built)
keys/                   # Directory for storing captured keystrokes (local client-side)
remote_logs/            # Server-side directory for collected logs and screenshots
├───<client_ip>/        # Logs from a specific client IP
└───screenshots/        # Captured screenshots
venv/                   # Python virtual environment
```

## Contributing

Contributions are welcome! Please feel free to submit pull requests or open issues for bugs and feature requests.

## License

This project is licensed under the MIT License - see the LICENSE file for details. (Note: A LICENSE file is not provided in the initial context, consider adding one.)
