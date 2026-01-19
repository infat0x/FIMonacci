#!/usr/bin/env python3
"""
FIMonacci Agent - Linux Build Script
Creates standalone executable using PyInstaller for Linux

This build script packages the FIMonacci GUI client for Linux with all features:
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
APP_NAME = "FIMonacci_Agent"
APP_ICON = "icon.png"  # Linux uses PNG icons
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

    # Try to upgrade pip, but don't fail if it errors
    try:
        subprocess.check_call([pip_executable, "install", "--upgrade", "pip"], stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError:
        print("  Note: Could not upgrade pip (continuing anyway)")

    subprocess.check_call([pip_executable, "install"] + required)
    print("Dependencies installed successfully!")


def create_default_icon():
    """Create a default PNG icon if none exists"""
    icon_path = Path(__file__).parent / APP_ICON
    if not icon_path.exists():
        print("Note: No icon.png found. Creating default icon...")
        # Try to convert .ico to .png if available
        ico_path = Path(__file__).parent / "icon.ico"
        if ico_path.exists():
            try:
                from PIL import Image
                img = Image.open(ico_path)
                img.save(icon_path, "PNG")
                print(f"  Created {APP_ICON} from icon.ico")
                return str(icon_path)
            except ImportError:
                print("  PIL not installed, cannot convert icon")
            except Exception as e:
                print(f"  Could not convert icon: {e}")

        print("  Building without custom icon")
        return None
    return str(icon_path)


def build_exe():
    """Build the Linux executable"""
    print("=" * 60)
    print("FIMonacci Agent - Linux Build Script")
    print("=" * 60)

    # Check platform
    if sys.platform == "win32":
        print("\n⚠️  WARNING: This script is designed for Linux!")
        print("    You're running on Windows. The binary will be for Windows.")
        print("    To build for Linux, run this script on a Linux machine.")
        response = input("\nContinue anyway? (y/N): ").strip().lower()
        if response != 'y':
            print("Build cancelled.")
            sys.exit(0)

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
    portable_dir = script_dir / "FIMonacci_Agent_Linux"

    for path in [build_dir, output_dir, spec_file, portable_dir]:
        if path.exists():
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()
            print(f"  Removed: {path.name}")

    # Check for icon
    icon = create_default_icon()

    # Build PyInstaller command
    print("\n[4/5] Building executable...")

    # Determine path separator (Windows uses ; Unix uses :)
    sep = ";" if sys.platform == "win32" else ":"

    cmd = [
        venv_python, "-m", "PyInstaller",
        "--name", APP_NAME,
        "--onefile",
        "--windowed",  # No console window
        "--clean",
        "--noconfirm",
        # Include customtkinter data
        "--collect-data", "customtkinter",
        # Include PIL/Pillow data
        "--collect-all", "PIL",
        # Include client module
        "--add-data", f"{script_dir / 'client.py'}{sep}.",
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

    # Add icon if available
    if icon:
        icon_path = (script_dir / APP_ICON).resolve()
        cmd.extend(["--icon", str(icon_path)])
        cmd.extend(["--add-data", f"{icon_path}{sep}."])

    # Add the main script
    cmd.append(str(main_script))

    # Run PyInstaller
    print(f"  Running: {' '.join(cmd[:5])}...")
    result = subprocess.run(cmd, cwd=str(script_dir))

    if result.returncode != 0:
        print("\n❌ Build failed!")
        sys.exit(1)

    # Finalize
    print("\n[5/5] Finalizing...")

    # Find the executable
    exe_name = APP_NAME
    exe_path = output_dir / exe_name

    if exe_path.exists():
        # Make executable
        os.chmod(exe_path, 0o755)

        # Create a portable folder with the exe
        portable_dir = script_dir / "FIMonacci_Agent_Linux"
        if portable_dir.exists():
            shutil.rmtree(portable_dir)
        portable_dir.mkdir()

        # Copy executable
        shutil.copy(exe_path, portable_dir / exe_name)
        os.chmod(portable_dir / exe_name, 0o755)

        # Create a launcher script
        launcher_script = portable_dir / "run.sh"
        launcher_script.write_text(f"""#!/bin/bash
# FIMonacci Agent Launcher
cd "$(dirname "$0")"
./{exe_name}
""")
        os.chmod(launcher_script, 0o755)

        print("\n" + "=" * 60)
        print("[SUCCESS] BUILD SUCCESSFUL!")
        print("=" * 60)
        print(f"\nExecutable location:")
        print(f"  {exe_path}")
        print(f"\nPortable folder:")
        print(f"  {portable_dir}")
        print(f"\nTo run:")
        print(f"  cd {portable_dir}")
        print(f"  ./run.sh")
        print(f"\nOr directly:")
        print(f"  ./{exe_name}")
        print(f"\nTo distribute, copy the entire 'FIMonacci_Agent_Linux' folder.")
        print("\n✨ Features included in this build:")
        print("  ✅ Monitor individual files AND folders")
        print("  ✅ PII detection with content protection")
        print("  ✅ Content change tracking for non-PII files")
        print("  ✅ Entropy calculation (ransomware detection)")
        print("  ✅ Hidden file monitoring")
        print("  ✅ Real-time monitoring with watchdog")
        print("  ✅ Modern GUI with drag-and-drop support")
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
