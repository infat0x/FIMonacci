# FIMonacci Agent

Desktop GUI application for file integrity monitoring.

## Quick Start (Development)

```bash
# Install dependencies
pip install -r requirements.txt

# Run the GUI app
python app.py
```

## Building Executable

Both build scripts automatically create and use a virtual environment (`build_venv`) to avoid conflicts with system-managed packages on Linux. This solves the "externally-managed-environment" error.

### Windows
```cmd
build.bat
```

Or manually:
```bash
python build.py
```

The executable will be created in `dist/FIMonacci_Agent.exe` and a portable folder `FIMonacci_Agent/`.

### Linux
```bash
# Build for Linux (automatically creates venv)
python3 build_linux.py
```

The executable will be created in `dist/FIMonacci_Agent` and a portable folder `FIMonacci_Agent_Linux/`.

**To run on Linux:**
```bash
cd FIMonacci_Agent_Linux
./run.sh
```

Or directly:
```bash
./FIMonacci_Agent
```

**Notes:**
- The Linux build must be run on a Linux machine. Cross-compilation from Windows to Linux is not supported by PyInstaller.
- Both build scripts create a temporary virtual environment (`build_venv/`) which can be safely deleted after building.
- The build scripts handle all dependencies automatically - no need to manually install packages.

## Files

- `app.py` - GUI application with Pearl Aqua theme
- `client.py` - Core monitoring client (command-line)
- `build.py` - Build script for creating executable
- `build.bat` - Windows batch file for easy building

## Command-Line Usage

For headless/CLI operation:
```bash
python client.py -u http://server:5000 -p /path/to/monitor --continuous
```

## Configuration

The app saves configuration to `app_config.json`:
- Server URL
- Monitored folders
- Exclusion patterns
- Auto-start preference

