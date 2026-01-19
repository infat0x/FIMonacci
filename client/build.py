#!/usr/bin/env python3
"""
FIMonacci Agent - Build Script
Creates standalone executable using PyInstaller

This build script packages the FIMonacci GUI client with all features:
- Individual file and folder monitoring
- PII detection and protection
- Content change tracking (non-PII files)
- Entropy calculation for ransomware detection
- Hidden file monitoring
- Real-time file system monitoring with watchdog
- Modern GUI with Pearl Aqua theme
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

# Build configuration
APP_NAME = "FIMonacci Agent"
APP_ICON = "icon.ico"
MAIN_SCRIPT = "app.py"
OUTPUT_DIR = "dist"
VENV_DIR = "build_venv"


def setup_venv():
    """Create and setup virtual environment for building"""
    script_dir = Path(__file__).parent
    venv_path = script_dir / VENV_DIR

    # Check if venv already exists
    if venv_path.exists():
        print(f"Using existing virtual environment: {VENV_DIR}")
    else:
        print(f"Creating virtual environment: {VENV_DIR}")
        subprocess.check_call([sys.executable, "-m", "venv", str(venv_path)])
        print("Virtual environment created successfully!")

    # Get the python executable in venv
    if sys.platform == "win32":
        venv_python = venv_path / "Scripts" / "python.exe"
        venv_pip = venv_path / "Scripts" / "pip.exe"
    else:
        venv_python = venv_path / "bin" / "python"
        venv_pip = venv_path / "bin" / "pip"

    return str(venv_python), str(venv_pip)


def check_dependencies(pip_executable):
    """Check if required packages are installed in venv"""
    required = ['pyinstaller', 'customtkinter', 'watchdog', 'requests', 'psutil', 'pillow']

    print("Installing/upgrading required packages in virtual environment...")

    # Try to upgrade pip, but don't fail if it errors (Windows pip self-upgrade issue)
    try:
        subprocess.check_call([pip_executable, "install", "--upgrade", "pip"], stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError:
        print("  Note: Could not upgrade pip (this is normal on Windows)")

    subprocess.check_call([pip_executable, "install"] + required)

    # Check for optional Windows dependencies
    if sys.platform == "win32":
        print("Installing pywin32 for Windows...")
        subprocess.check_call([pip_executable, "install", "pywin32"])

    print("Dependencies installed successfully!")


def create_icon():
    """Create a default icon if none exists"""
    icon_path = Path(__file__).parent / APP_ICON
    if not icon_path.exists():
        print("Note: No icon.ico found. Using default icon.")
        return None
    return str(icon_path)


def build_exe():
    """Build the executable"""
    print("=" * 60)
    print("FIMonacci Agent - Build Script")
    print("=" * 60)

    # Setup virtual environment
    print("\n[1/5] Setting up virtual environment...")
    venv_python, venv_pip = setup_venv()

    # Check dependencies
    print("\n[2/5] Checking dependencies...")
    check_dependencies(venv_pip)
    
    # Get paths
    script_dir = Path(__file__).parent
    main_script = script_dir / MAIN_SCRIPT
    output_dir = script_dir / OUTPUT_DIR
    
    if not main_script.exists():
        print(f"Error: {MAIN_SCRIPT} not found!")
        sys.exit(1)
    
    # Clean previous build
    print("\n[3/5] Cleaning previous build...")
    build_dir = script_dir / "build"
    spec_file = script_dir / f"{Path(MAIN_SCRIPT).stem}.spec"
    portable_dir = script_dir / "FIMonacci_Agent"

    for path in [build_dir, output_dir, spec_file, portable_dir]:
        if path.exists():
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()
            print(f"  Removed: {path.name}")

    # Check for icon and ensure it exists
    icon = create_icon()
    icon_path = (script_dir / APP_ICON).resolve()
    if not icon_path.exists():
        print(f"[ERROR] {APP_ICON} not found after creation. Aborting build.")
        sys.exit(1)

    # Build PyInstaller command
    print("\n[4/5] Building executable...")

    # Determine path separator for --add-data (Windows uses ; Unix uses :)
    sep = ";" if sys.platform == "win32" else ":"

    cmd = [
        venv_python, "-m", "PyInstaller",
        "--name", APP_NAME.replace(" ", "_"),
        "--onefile",
        "--windowed",  # Hide console window
        "--clean",
        "--noconfirm",
        "--icon", str(icon_path),  # embed icon via absolute path
        # Include customtkinter data
        "--collect-data", "customtkinter",
        # Include PIL/Pillow data
        "--collect-all", "PIL",
        # Include client module
        "--add-data", f"{script_dir / 'client.py'}{sep}.",
        # Include icon so Tk window can load it at runtime
        "--add-data", f"{icon_path}{sep}.",
        # Include logo image for GUI header
        "--add-data", f"{script_dir / 'logo.png'}{sep}.",
        # Hidden imports
        "--hidden-import", "requests",
        "--hidden-import", "urllib3",
        "--hidden-import", "watchdog",
        "--hidden-import", "watchdog.observers",
        "--hidden-import", "watchdog.events",
        "--hidden-import", "psutil",
        "--hidden-import", "PIL",
        "--hidden-import", "PIL.Image",
        "--hidden-import", "PIL.ImageTk",
        "--hidden-import", "PIL._tkinter_finder",
    ]
    
    # Add Windows-specific imports on Windows
    if sys.platform == "win32":
        cmd.extend([
            "--hidden-import", "win32security",
            "--hidden-import", "win32api",
            "--hidden-import", "pywintypes",
        ])
    
    # Add the main script
    cmd.append(str(main_script))
    
    # Run PyInstaller
    print(f"  Running: {' '.join(cmd[:5])}...")
    result = subprocess.run(cmd, cwd=str(script_dir))
    
    if result.returncode != 0:
        print("\n❌ Build failed!")
        sys.exit(1)
    
    # Copy client.py to dist folder (needed for import)
    print("\n[5/5] Finalizing...")
    
    # Find the exe
    exe_name = f"{APP_NAME.replace(' ', '_')}.exe"
    exe_path = output_dir / exe_name
    
    if exe_path.exists():
        # Create a portable folder with the exe
        portable_dir = script_dir / "FIMonacci_Agent"
        if portable_dir.exists():
            shutil.rmtree(portable_dir)
        portable_dir.mkdir()
        
        # Copy exe
        shutil.copy(exe_path, portable_dir / exe_name)
        
        print("\n" + "=" * 60)
        print("[SUCCESS] BUILD SUCCESSFUL!")
        print("=" * 60)
        print(f"\nExecutable location:")
        print(f"  {exe_path}")
        print(f"\nPortable folder:")
        print(f"  {portable_dir}")
        print(f"\nTo distribute, copy the entire 'FIMonacci_Agent' folder.")
        # NOTE: avoid unicode/emoji here (Windows terminals can be cp1252)
        print("\nFeatures included in this build:")
        print("  - Monitor individual files AND folders")
        print("  - PII detection (8 types) with content protection")
        print("  - Content change tracking for non-PII files")
        print("  - Entropy calculation (ransomware detection)")
        print("  - Hidden file monitoring")
        print("  - Real-time monitoring with watchdog")
        print("  - Modern GUI with drag-and-drop support")
        print("=" * 60)
    else:
        print(f"\n[ERROR] Executable not found at {exe_path}")
        sys.exit(1)


def main():
    """Main entry point"""
    try:
        build_exe()
    except KeyboardInterrupt:
        print("\n\nBuild cancelled.")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] Build error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

