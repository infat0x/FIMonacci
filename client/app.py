#!/usr/bin/env python3
"""
FIMonacci Agent - Desktop GUI Application
Modern File Integrity Monitoring Client with Pearl Aqua Theme
"""

import os
import sys
import json
import threading
import webbrowser
import queue
from collections import deque
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Callable
import tkinter as tk
from tkinter import filedialog, messagebox

# Handle PyInstaller bundled path
if getattr(sys, 'frozen', False):
    APPLICATION_PATH = Path(sys.executable).parent
    if str(APPLICATION_PATH) not in sys.path:
        sys.path.insert(0, str(APPLICATION_PATH))
else:
    APPLICATION_PATH = Path(__file__).parent

# Third-party imports
try:
    import customtkinter as ctk
except ImportError:
    print("CustomTkinter not found. Installing...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "customtkinter"])
    import customtkinter as ctk

# Import the client module
try:
    from client import FIMonacciClient, FIMFileEventHandler
except ImportError:
    sys.path.insert(0, str(Path(__file__).parent))
    from client import FIMonacciClient, FIMFileEventHandler

# Set appearance mode and color theme
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# ═══════════════════════════════════════════════════════════════
#   Design System - Pearl Aqua Edition
# ═══════════════════════════════════════════════════════════════

# Spacing constants
SPACING = {
    "xs": 4,
    "sm": 8,
    "md": 16,
    "lg": 24,
    "xl": 32,
}

# Size constants
SIZES = {
    "input_height": 44,
    "button_height": 44,
    "button_height_lg": 52,
    "icon_button": 36,
    "card_radius": 16,
    "button_radius": 10,
    "tag_radius": 8,
}

# Color palette
COLORS = {
    # Core Palette
    "pearl_aqua": "#75dddd",
    "pearl_aqua_hover": "#5fd4d4",
    "frosted_blue": "#84c7d0",
    "lavender_grey": "#9297c4",
    "lavender_purple": "#9368b7",
    "lavender_purple_hover": "#7d58a0",
    "raspberry_plum": "#aa3e98",
    
    # Dark Theme Backgrounds
    "bg_primary": "#0a0a14",
    "bg_secondary": "#12121f",
    "bg_tertiary": "#1a1a2e",
    "bg_card": "#16162a",
    "bg_input": "#0e0e1a",
    "bg_hover": "#1e1e3a",
    
    # Text
    "text_primary": "#f0f4f8",
    "text_secondary": "#a0aec0",
    "text_muted": "#64748b",
    "text_on_accent": "#0a0a14",
    
    # Status
    "success": "#10b981",
    "success_hover": "#059669",
    "warning": "#f59e0b",
    "error": "#ef4444",
    "error_hover": "#dc2626",
    
    # Borders
    "border": "#2a2a45",
    "border_focus": "#75dddd",
    "border_subtle": "#1e1e35",
}

# Font configuration
FONTS = {
    "title": ("Inter", 24, "bold"),
    "subtitle": ("Inter", 13),
    "section": ("Inter", 13, "bold"),
    "body": ("Inter", 13),
    "small": ("Inter", 11),
    "tiny": ("Inter", 10),
    "button": ("Inter", 13, "bold"),
    "button_sm": ("Inter", 12),
    "mono": ("JetBrains Mono", 12),
}


def resource_path(rel: str) -> Path:
    """Resolve resource path - supports PyInstaller _MEIPASS"""
    base = Path(getattr(sys, "_MEIPASS", APPLICATION_PATH))
    return base / rel


class _DebugStream:
    """File-like stream that forwards writes to a callback (thread-safe)."""

    def __init__(self, write_callback, passthrough=None):
        self._write_callback = write_callback
        self._passthrough = passthrough

    def write(self, s):
        try:
            if s:
                self._write_callback(str(s))
        except Exception:
            # Never let logging crash the app
            pass
        if self._passthrough:
            try:
                self._passthrough.write(s)
                self._passthrough.flush()
            except Exception:
                pass

    def flush(self):
        if self._passthrough:
            try:
                self._passthrough.flush()
            except Exception:
                pass


class FIMonacciApp(ctk.CTk):
    """Main Application Window"""
    
    def __init__(self):
        super().__init__()
        
        # Window configuration
        self.title("FIMonacci Agent")
        self.geometry("960x720")
        self.minsize(860, 640)

        # Set icon if available (from bundled resources or local)
        icon_path = resource_path("icon.ico")
        if icon_path.exists():
            try:
                self.iconbitmap(str(icon_path))
            except Exception:
                pass
        
        # Configure grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        # State variables
        self.client: Optional[FIMonacciClient] = None
        self.observer = None
        self.is_monitoring = False
        self.monitored_paths: List[str] = []
        self.pii_paths: List[str] = []  # Paths manually flagged as containing PII
        self.exclusion_patterns: List[str] = []
        self.config_file = APPLICATION_PATH / "app_config.json"

        # Debug console (in-app) — required for windowed PyInstaller builds (no terminal)
        self._debug_window = None
        self._debug_textbox = None
        self._debug_autoscroll_var = ctk.BooleanVar(value=True)
        self._debug_queue: "queue.Queue[str]" = queue.Queue()
        self._debug_partial = ""
        self._debug_history = deque(maxlen=5000)  # ring buffer of rendered lines
        self._debug_line_count = 0

        # Redirect stdout/stderr into the debug console (still safe if window never opened)
        self._stdout_original = getattr(sys, "stdout", None)
        self._stderr_original = getattr(sys, "stderr", None)
        sys.stdout = _DebugStream(self._enqueue_debug, passthrough=self._stdout_original)
        sys.stderr = _DebugStream(self._enqueue_debug, passthrough=self._stderr_original)

        # Drain debug queue on UI thread
        self.after(150, self._drain_debug_queue)
        
        # Load saved configuration
        self.load_config()
        
        # Build UI
        self._create_ui()

        # Hotkey to open debug window
        self.bind_all("<Control-Shift-d>", lambda e: self._toggle_debug_window())
        self.bind_all("<Control-Shift-D>", lambda e: self._toggle_debug_window())
        
        # Bind close event
        self.protocol("WM_DELETE_WINDOW", self._on_closing)
    
    def _create_ui(self):
        """Create the main user interface"""
        # Main container
        self.main_frame = ctk.CTkFrame(self, fg_color=COLORS["bg_primary"], corner_radius=0)
        self.main_frame.grid(row=0, column=0, sticky="nsew")
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(1, weight=1)
        
        # Header
        self._create_header()
        
        # Content area
        self.content_frame = ctk.CTkScrollableFrame(
            self.main_frame,
            fg_color=COLORS["bg_primary"],
            scrollbar_fg_color=COLORS["bg_secondary"],
            scrollbar_button_color=COLORS["pearl_aqua"],
            scrollbar_button_hover_color=COLORS["frosted_blue"]
        )
        self.content_frame.grid(row=1, column=0, sticky="nsew", padx=SPACING["xl"], pady=(SPACING["md"], SPACING["lg"]))
        self.content_frame.grid_columnconfigure(0, weight=1)
        
        # Sections
        self._create_server_section()
        self._create_folders_section()
        self._create_exclusions_section()
        self._create_control_section()
        
        # Status Bar
        self._create_status_bar()
    
    def _create_header(self):
        """Create header with logo, title and status"""
        header = ctk.CTkFrame(
            self.main_frame,
            fg_color=COLORS["bg_secondary"],
            height=90,
            corner_radius=0
        )
        header.grid(row=0, column=0, sticky="ew")
        header.grid_columnconfigure(1, weight=1)
        header.grid_columnconfigure(3, weight=0)
        header.grid_propagate(False)

        # Logo container - clean professional style
        logo_container = ctk.CTkFrame(
            header,
            fg_color="transparent",
            width=64,
            height=64
        )
        logo_container.grid(row=0, column=0, padx=(SPACING["xl"], SPACING["md"]), pady=13)
        logo_container.grid_propagate(False)

        # Try to load logo image, fallback to emoji if not found
        try:
            from PIL import Image
            logo_path = resource_path("logo.png")
            if logo_path.exists():
                pil_image = Image.open(str(logo_path))
                logo_img = ctk.CTkImage(
                    light_image=pil_image,
                    dark_image=pil_image,
                    size=(56, 56)
                )
                logo_label = ctk.CTkLabel(
                    logo_container,
                    image=logo_img,
                    text=""
                )
                # Keep reference to prevent garbage collection
                logo_label.image = logo_img
            else:
                # Fallback to emoji if logo not found
                logo_label = ctk.CTkLabel(
                    logo_container,
                    text="🛡️",
                    font=ctk.CTkFont(size=32),
                    text_color=COLORS["pearl_aqua"]
                )
        except Exception:
            # Fallback to emoji on any error
            logo_label = ctk.CTkLabel(
                logo_container,
                text="🛡️",
                font=ctk.CTkFont(size=32),
                text_color=COLORS["pearl_aqua"]
            )
        logo_label.place(relx=0.5, rely=0.5, anchor="center")
        
        # Title section
        title_frame = ctk.CTkFrame(header, fg_color="transparent")
        title_frame.grid(row=0, column=1, sticky="w", pady=13)
        
        title_label = ctk.CTkLabel(
            title_frame,
            text="FIMonacci Agent",
            font=ctk.CTkFont(family=FONTS["title"][0], size=FONTS["title"][1], weight=FONTS["title"][2]),
            text_color=COLORS["text_primary"]
        )
        title_label.pack(anchor="w")
        
        subtitle_label = ctk.CTkLabel(
            title_frame,
            text="File Integrity Monitoring Client",
            font=ctk.CTkFont(family=FONTS["subtitle"][0], size=FONTS["subtitle"][1]),
            text_color=COLORS["text_secondary"]
        )
        subtitle_label.pack(anchor="w", pady=(2, 0))
        
        # Status badge
        self.status_badge = ctk.CTkFrame(
            header,
            fg_color=COLORS["bg_tertiary"],
            corner_radius=24,
            height=40
        )
        self.status_badge.grid(row=0, column=2, padx=SPACING["xl"], pady=13)
        
        self.status_dot = ctk.CTkLabel(
            self.status_badge,
            text="●",
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text_muted"],
            width=24
        )
        self.status_dot.pack(side="left", padx=(SPACING["md"], SPACING["xs"]), pady=SPACING["sm"])
        
        self.status_text = ctk.CTkLabel(
            self.status_badge,
            text="Idle",
            font=ctk.CTkFont(family=FONTS["body"][0], size=FONTS["body"][1], weight="bold"),
            text_color=COLORS["text_secondary"]
        )
        self.status_text.pack(side="left", padx=(0, SPACING["md"]), pady=SPACING["sm"])

        # Debug button (opens in-app debug console)
        self.debug_btn = ctk.CTkButton(
            header,
            text="Debug",
            font=ctk.CTkFont(family=FONTS["button_sm"][0], size=FONTS["button_sm"][1], weight="bold"),
            fg_color=COLORS["bg_tertiary"],
            hover_color=COLORS["bg_hover"],
            text_color=COLORS["text_primary"],
            width=86,
            height=40,
            corner_radius=20,
            border_width=1,
            border_color=COLORS["border"],
            command=self._toggle_debug_window
        )
        self.debug_btn.grid(row=0, column=3, padx=(0, SPACING["xl"]), pady=13, sticky="e")
    
    def _create_section(self, title: str, icon: str = "") -> ctk.CTkFrame:
        """Create a section with header and card container"""
        # Section container
        section = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        section.pack(fill="x", pady=(SPACING["md"], SPACING["sm"]))
        section.grid_columnconfigure(0, weight=1)
        
        # Header row
        header_row = ctk.CTkFrame(section, fg_color="transparent")
        header_row.pack(fill="x", pady=(0, SPACING["sm"]))
        header_row.grid_columnconfigure(0, weight=1)
        
        # Title with icon
        title_text = f"{icon}  {title}" if icon else title
        title_label = ctk.CTkLabel(
            header_row,
            text=title_text,
            font=ctk.CTkFont(family=FONTS["section"][0], size=FONTS["section"][1], weight=FONTS["section"][2]),
            text_color=COLORS["pearl_aqua"],
            anchor="w"
        )
        title_label.pack(side="left")
        
        # Card
        card = ctk.CTkFrame(
            section,
            fg_color=COLORS["bg_card"],
            corner_radius=SIZES["card_radius"],
            border_width=1,
            border_color=COLORS["border"]
        )
        card.pack(fill="x")
        
        return header_row, card
    
    def _create_server_section(self):
        """Server configuration section"""
        header_row, card = self._create_section("Server Configuration", "🌐")
        
        # Card content with proper grid layout
        card.grid_columnconfigure(0, weight=1)
        
        # URL Label
        url_label = ctk.CTkLabel(
            card,
            text="Server URL",
            font=ctk.CTkFont(family=FONTS["small"][0], size=FONTS["small"][1]),
            text_color=COLORS["text_secondary"],
            anchor="w"
        )
        url_label.grid(row=0, column=0, columnspan=2, padx=SPACING["lg"], pady=(SPACING["lg"], SPACING["xs"]), sticky="w")
        
        # Input row frame
        input_row = ctk.CTkFrame(card, fg_color="transparent")
        input_row.grid(row=1, column=0, columnspan=2, padx=SPACING["lg"], pady=(0, SPACING["lg"]), sticky="ew")
        input_row.grid_columnconfigure(0, weight=1)
        
        # Server URL Entry
        self.server_url_entry = ctk.CTkEntry(
            input_row,
            placeholder_text="http://localhost:5000",
            font=ctk.CTkFont(family=FONTS["body"][0], size=FONTS["body"][1]),
            height=SIZES["input_height"],
            fg_color=COLORS["bg_input"],
            border_color=COLORS["border"],
            border_width=2,
            text_color=COLORS["text_primary"],
            placeholder_text_color=COLORS["text_muted"],
            corner_radius=SIZES["button_radius"]
        )
        self.server_url_entry.grid(row=0, column=0, sticky="ew", padx=(0, SPACING["sm"]))
        
        # Load saved URL
        if hasattr(self, 'saved_server_url') and self.saved_server_url:
            self.server_url_entry.insert(0, self.saved_server_url)
        
        # Test button
        self.test_btn = ctk.CTkButton(
            input_row,
            text="Test Connection",
            font=ctk.CTkFont(family=FONTS["button_sm"][0], size=FONTS["button_sm"][1]),
            fg_color=COLORS["bg_tertiary"],
            hover_color=COLORS["bg_hover"],
            text_color=COLORS["text_primary"],
            height=SIZES["input_height"],
            width=150,
            corner_radius=SIZES["button_radius"],
            border_width=1,
            border_color=COLORS["border"],
            command=self._test_connection
        )
        self.test_btn.grid(row=0, column=1, sticky="e")
    
    def _create_folders_section(self):
        """Monitored paths section (folders and individual files)"""
        header_row, card = self._create_section("Monitored Paths", "📁")

        # Add File button
        add_file_btn = ctk.CTkButton(
            header_row,
            text="+ Add File",
            font=ctk.CTkFont(family=FONTS["button_sm"][0], size=FONTS["button_sm"][1]),
            fg_color=COLORS["frosted_blue"],
            hover_color=COLORS["pearl_aqua_hover"],
            text_color=COLORS["text_on_accent"],
            height=32,
            width=100,
            corner_radius=SIZES["tag_radius"],
            command=self._add_file
        )
        add_file_btn.pack(side="right", padx=(SPACING["xs"], 0))

        # Add Folder button
        add_folder_btn = ctk.CTkButton(
            header_row,
            text="+ Add Folder",
            font=ctk.CTkFont(family=FONTS["button_sm"][0], size=FONTS["button_sm"][1]),
            fg_color=COLORS["pearl_aqua"],
            hover_color=COLORS["pearl_aqua_hover"],
            text_color=COLORS["text_on_accent"],
            height=32,
            width=110,
            corner_radius=SIZES["tag_radius"],
            command=self._add_folder
        )
        add_folder_btn.pack(side="right", padx=(SPACING["xs"], 0))

        # Store card reference
        self.folders_card = card

        # Paths container
        self.folders_container = ctk.CTkFrame(card, fg_color="transparent")
        self.folders_container.pack(fill="x", padx=SPACING["lg"], pady=SPACING["lg"])

        self._refresh_folders_list()
    
    def _create_exclusions_section(self):
        """Exclusions section"""
        header_row, card = self._create_section("Exclusions", "🚫")
        
        # Add button in header
        add_btn = ctk.CTkButton(
            header_row,
            text="+ Add Pattern",
            font=ctk.CTkFont(family=FONTS["button_sm"][0], size=FONTS["button_sm"][1]),
            fg_color=COLORS["lavender_purple"],
            hover_color=COLORS["lavender_purple_hover"],
            text_color=COLORS["text_primary"],
            height=32,
            width=110,
            corner_radius=SIZES["tag_radius"],
            command=self._add_exclusion
        )
        add_btn.pack(side="right")
        
        # Store card reference
        self.exclusions_card = card
        
        # Info text
        info_label = ctk.CTkLabel(
            card,
            text="Patterns to exclude from monitoring (e.g., *.log, *.tmp, __pycache__, .git)",
            font=ctk.CTkFont(family=FONTS["small"][0], size=FONTS["small"][1]),
            text_color=COLORS["text_muted"],
            anchor="w"
        )
        info_label.pack(anchor="w", padx=SPACING["lg"], pady=(SPACING["lg"], SPACING["sm"]))
        
        # Exclusions container
        self.exclusions_container = ctk.CTkFrame(card, fg_color="transparent")
        self.exclusions_container.pack(fill="x", padx=SPACING["lg"], pady=(0, SPACING["lg"]))
        
        self._refresh_exclusions_list()
    
    def _create_control_section(self):
        """Monitoring control section"""
        header_row, card = self._create_section("Monitoring Control", "⚡")
        
        # Button container with equal columns
        btn_container = ctk.CTkFrame(card, fg_color="transparent")
        btn_container.pack(fill="x", padx=SPACING["lg"], pady=SPACING["lg"])
        btn_container.grid_columnconfigure((0, 1), weight=1, uniform="btn")
        
        # Start button
        self.start_btn = ctk.CTkButton(
            btn_container,
            text="▶  Start Monitoring",
            font=ctk.CTkFont(family=FONTS["button"][0], size=FONTS["button"][1], weight=FONTS["button"][2]),
            fg_color=COLORS["success"],
            hover_color=COLORS["success_hover"],
            text_color="#ffffff",
            height=SIZES["button_height_lg"],
            corner_radius=SIZES["button_radius"],
            command=self._start_monitoring
        )
        self.start_btn.grid(row=0, column=0, sticky="ew", padx=(0, SPACING["sm"]))
        
        # Stop button
        self.stop_btn = ctk.CTkButton(
            btn_container,
            text="⏹  Stop Monitoring",
            font=ctk.CTkFont(family=FONTS["button"][0], size=FONTS["button"][1], weight=FONTS["button"][2]),
            fg_color=COLORS["error"],
            hover_color=COLORS["error_hover"],
            text_color="#ffffff",
            height=SIZES["button_height_lg"],
            corner_radius=SIZES["button_radius"],
            state="disabled",
            command=self._stop_monitoring
        )
        self.stop_btn.grid(row=0, column=1, sticky="ew", padx=(SPACING["sm"], 0))
        
        # Divider
        divider = ctk.CTkFrame(card, fg_color=COLORS["border_subtle"], height=1)
        divider.pack(fill="x", padx=SPACING["lg"], pady=(0, SPACING["md"]))
        
        # Options container
        options_frame = ctk.CTkFrame(card, fg_color="transparent")
        options_frame.pack(fill="x", padx=SPACING["lg"], pady=(0, SPACING["lg"]))
        
        # Auto-start checkbox
        self.autostart_var = ctk.BooleanVar(value=getattr(self, 'saved_autostart', False))
        autostart_cb = ctk.CTkCheckBox(
            options_frame,
            text="Auto-start monitoring on launch",
            font=ctk.CTkFont(family=FONTS["body"][0], size=FONTS["body"][1]),
            text_color=COLORS["text_secondary"],
            fg_color=COLORS["pearl_aqua"],
            hover_color=COLORS["frosted_blue"],
            checkmark_color=COLORS["text_on_accent"],
            border_color=COLORS["border"],
            corner_radius=4,
            border_width=2,
            variable=self.autostart_var
        )
        autostart_cb.pack(side="left", padx=(0, SPACING["xl"]))
        
        # Minimize checkbox
        self.minimize_var = ctk.BooleanVar(value=getattr(self, 'saved_minimize', False))
        minimize_cb = ctk.CTkCheckBox(
            options_frame,
            text="Minimize to system tray",
            font=ctk.CTkFont(family=FONTS["body"][0], size=FONTS["body"][1]),
            text_color=COLORS["text_secondary"],
            fg_color=COLORS["pearl_aqua"],
            hover_color=COLORS["frosted_blue"],
            checkmark_color=COLORS["text_on_accent"],
            border_color=COLORS["border"],
            corner_radius=4,
            border_width=2,
            variable=self.minimize_var
        )
        minimize_cb.pack(side="left")
    
    def _create_status_bar(self):
        """Status bar at bottom"""
        status_bar = ctk.CTkFrame(
            self.main_frame,
            fg_color=COLORS["bg_secondary"],
            height=44,
            corner_radius=0
        )
        status_bar.grid(row=2, column=0, sticky="ew")
        status_bar.grid_propagate(False)
        status_bar.grid_columnconfigure(1, weight=1)
        
        # Activity label
        self.activity_label = ctk.CTkLabel(
            status_bar,
            text="Ready",
            font=ctk.CTkFont(family=FONTS["small"][0], size=FONTS["small"][1]),
            text_color=COLORS["text_muted"]
        )
        self.activity_label.grid(row=0, column=0, padx=SPACING["lg"], pady=12, sticky="w")
        
        # Version
        version_label = ctk.CTkLabel(
            status_bar,
            text="v1.0.0",
            font=ctk.CTkFont(family=FONTS["tiny"][0], size=FONTS["tiny"][1]),
            text_color=COLORS["text_muted"]
        )
        version_label.grid(row=0, column=2, padx=SPACING["lg"], pady=12, sticky="e")
    
    def _refresh_folders_list(self):
        """Refresh paths list (folders and files)"""
        for widget in self.folders_container.winfo_children():
            widget.destroy()

        if not self.monitored_paths:
            empty = ctk.CTkLabel(
                self.folders_container,
                text="No paths added yet. Click '+ Add Folder' or '+ Add File' to begin.",
                font=ctk.CTkFont(family=FONTS["body"][0], size=FONTS["body"][1]),
                text_color=COLORS["text_muted"]
            )
            empty.pack(pady=SPACING["md"])
            return

        for idx, path in enumerate(self.monitored_paths):
            # Determine if path is a file or folder
            path_obj = Path(path)
            is_file = path_obj.is_file()
            is_dir = path_obj.is_dir()
            exists = path_obj.exists()

            item = ctk.CTkFrame(
                self.folders_container,
                fg_color=COLORS["bg_secondary"],
                corner_radius=SIZES["tag_radius"],
                height=56  # Increased height to fit checkbox
            )
            item.pack(fill="x", pady=(0 if idx == 0 else SPACING["xs"], 0))
            item.pack_propagate(False)

            # Icon - different for files vs folders
            if not exists:
                icon_text = "⚠️"  # Warning for non-existent paths
            elif is_file:
                icon_text = "📄"  # File icon
            elif is_dir:
                icon_text = "📂"  # Folder icon
            else:
                icon_text = "📁"  # Default folder icon

            icon = ctk.CTkLabel(
                item,
                text=icon_text,
                font=ctk.CTkFont(size=16),
                width=40
            )
            icon.pack(side="left", padx=(SPACING["md"], SPACING["xs"]))

            # Left side container for path and checkbox
            left_container = ctk.CTkFrame(item, fg_color="transparent")
            left_container.pack(side="left", fill="both", expand=True, padx=SPACING["xs"])

            # Path with type indicator
            path_display = path
            if not exists:
                path_display = f"{path} (Not Found)"

            path_lbl = ctk.CTkLabel(
                left_container,
                text=path_display,
                font=ctk.CTkFont(family=FONTS["body"][0], size=FONTS["body"][1]),
                text_color=COLORS["text_primary"] if exists else COLORS["text_muted"],
                anchor="w"
            )
            path_lbl.pack(anchor="w", pady=(SPACING["xs"], 0))

            # PII Checkbox
            pii_checked = path in self.pii_paths
            pii_var = tk.BooleanVar(value=pii_checked)

            pii_checkbox = ctk.CTkCheckBox(
                left_container,
                text="Contains PII (send hash only)",
                font=ctk.CTkFont(family=FONTS["small"][0], size=FONTS["small"][1]),
                text_color=COLORS["text_muted"],
                fg_color=COLORS["warning"],
                hover_color=COLORS["warning"],
                checkmark_color=COLORS["text_on_accent"],
                border_color=COLORS["border"],
                corner_radius=4,
                border_width=2,
                variable=pii_var,
                command=lambda p=path, v=pii_var: self._toggle_pii_flag(p, v.get())
            )
            pii_checkbox.pack(anchor="w", pady=(2, SPACING["xs"]))

            # Remove button
            remove_btn = ctk.CTkButton(
                item,
                text="✕",
                font=ctk.CTkFont(size=14),
                fg_color="transparent",
                hover_color=COLORS["error"],
                text_color=COLORS["text_muted"],
                width=SIZES["icon_button"],
                height=SIZES["icon_button"],
                corner_radius=SIZES["tag_radius"],
                command=lambda p=path: self._remove_folder(p)
            )
            remove_btn.pack(side="right", padx=SPACING["sm"])
    
    def _refresh_exclusions_list(self):
        """Refresh exclusions list with wrapping tags"""
        for widget in self.exclusions_container.winfo_children():
            widget.destroy()
        
        if not self.exclusion_patterns:
            self.exclusion_patterns = ["*.log", "*.tmp", "*.temp", "__pycache__", ".git", ".venv", "node_modules"]
        
        # Use a frame that wraps
        tags_frame = ctk.CTkFrame(self.exclusions_container, fg_color="transparent")
        tags_frame.pack(fill="x", anchor="w")
        
        for pattern in self.exclusion_patterns:
            tag = ctk.CTkFrame(
                tags_frame,
                fg_color=COLORS["bg_tertiary"],
                corner_radius=SIZES["tag_radius"]
            )
            tag.pack(side="left", padx=(0, SPACING["xs"]), pady=SPACING["xs"])
            
            tag_text = ctk.CTkLabel(
                tag,
                text=pattern,
                font=ctk.CTkFont(family=FONTS["small"][0], size=FONTS["small"][1]),
                text_color=COLORS["text_secondary"]
            )
            tag_text.pack(side="left", padx=(SPACING["sm"], SPACING["xs"]), pady=SPACING["xs"])
            
            remove_btn = ctk.CTkButton(
                tag,
                text="×",
                font=ctk.CTkFont(size=12),
                fg_color="transparent",
                hover_color=COLORS["raspberry_plum"],
                text_color=COLORS["text_muted"],
                width=24,
                height=24,
                corner_radius=4,
                command=lambda p=pattern: self._remove_exclusion(p)
            )
            remove_btn.pack(side="left", padx=(0, SPACING["xs"]), pady=SPACING["xs"])
    
    # ═══════════════════════════════════════════════════════════════
    #   Actions & Event Handlers
    # ═══════════════════════════════════════════════════════════════
    
    def _add_folder(self):
        """Add a folder to monitor"""
        folder = filedialog.askdirectory(title="Select Folder to Monitor")
        if folder:
            if folder not in self.monitored_paths:
                self.monitored_paths.append(folder)
                self._refresh_folders_list()
                self._log_activity(f"Added folder: {folder}")
                self.save_config()
            else:
                messagebox.showwarning("Duplicate", "This path is already being monitored.")

    def _add_file(self):
        """Add an individual file to monitor"""
        file = filedialog.askopenfilename(title="Select File to Monitor")
        if file:
            if file not in self.monitored_paths:
                self.monitored_paths.append(file)
                self._refresh_folders_list()
                self._log_activity(f"Added file: {file}")
                self.save_config()
            else:
                messagebox.showwarning("Duplicate", "This path is already being monitored.")

    def _remove_folder(self, path: str):
        """Remove a monitored path (file or folder)"""
        if path in self.monitored_paths:
            self.monitored_paths.remove(path)
            # Also remove from PII paths if present
            if path in self.pii_paths:
                self.pii_paths.remove(path)
            self._refresh_folders_list()
            path_type = "file" if Path(path).is_file() else "folder"
            self._log_activity(f"Removed {path_type}: {path}")
            self.save_config()

    def _toggle_pii_flag(self, path: str, is_pii: bool):
        """Toggle PII flag for a path"""
        if is_pii:
            if path not in self.pii_paths:
                self.pii_paths.append(path)
                self._log_activity(f"Marked as PII: {path}")
        else:
            if path in self.pii_paths:
                self.pii_paths.remove(path)
                self._log_activity(f"Unmarked PII: {path}")
        self.save_config()
    
    def _add_exclusion(self):
        dialog = ExclusionDialog(self)
        self.wait_window(dialog)
        if dialog.result:
            pattern = dialog.result.strip()
            if pattern and pattern not in self.exclusion_patterns:
                self.exclusion_patterns.append(pattern)
                self._refresh_exclusions_list()
                self._log_activity(f"Added exclusion: {pattern}")
                self.save_config()
    
    def _remove_exclusion(self, pattern: str):
        if pattern in self.exclusion_patterns:
            self.exclusion_patterns.remove(pattern)
            self._refresh_exclusions_list()
            self._log_activity(f"Removed exclusion: {pattern}")
            self.save_config()
    
    def _test_connection(self):
        url = self.server_url_entry.get().strip()
        if not url:
            messagebox.showerror("Error", "Please enter a server URL")
            return
        
        self._log_activity("Testing connection...")
        self.test_btn.configure(state="disabled", text="Testing...")
        
        def test():
            try:
                import requests
                test_url = url if url.startswith(('http://', 'https://')) else f'http://{url}'
                response = requests.get(f"{test_url.rstrip('/')}/api/status", timeout=5)
                if response.status_code == 200:
                    self.after(0, self._connection_success)
                else:
                    self.after(0, lambda: self._connection_failed(f"Server returned {response.status_code}"))
            except requests.exceptions.ConnectionError:
                self.after(0, lambda: self._connection_failed("Could not connect to server"))
            except Exception as e:
                self.after(0, lambda: self._connection_failed(str(e)))
        
        threading.Thread(target=test, daemon=True).start()
    
    def _connection_success(self):
        self.test_btn.configure(state="normal", text="Test Connection")
        self._log_activity("✓ Connection successful!")
        self._update_status("Connected", COLORS["success"])
        messagebox.showinfo("Success", "Successfully connected to FIMonacci server!")
    
    def _connection_failed(self, error: str):
        self.test_btn.configure(state="normal", text="Test Connection")
        self._log_activity(f"✗ Connection failed: {error}")
        self._update_status("Disconnected", COLORS["error"])
        messagebox.showerror("Connection Failed", f"Could not connect:\n{error}")
    
    def _start_monitoring(self):
        url = self.server_url_entry.get().strip()
        if not url:
            messagebox.showerror("Error", "Please enter a server URL")
            return
        if not self.monitored_paths:
            messagebox.showerror("Error", "Please add at least one path (file or folder) to monitor")
            return
        
        try:
            self._log_activity("Starting monitoring...")
            self._update_status("Connecting...", COLORS["warning"])

            url = url if url.startswith(('http://', 'https://')) else f'http://{url}'
            config_path = str(APPLICATION_PATH / "client_config.json")
            # Pass PII paths to client
            self.client = FIMonacciClient(url, config_path=config_path, pii_paths=self.pii_paths)
            
            def monitor():
                try:
                    from watchdog.observers import Observer
                    
                    cache_path = APPLICATION_PATH / "hash_cache.json"
                    hash_cache = {}
                    if cache_path.exists():
                        try:
                            with open(cache_path, 'r') as f:
                                hash_cache = json.load(f)
                        except:
                            pass
                    
                    self.observer = Observer()
                    event_handler = FIMFileEventHandler(self.client, hash_cache)
                    
                    for path in self.monitored_paths:
                        if Path(path).exists():
                            self.observer.schedule(event_handler, path, recursive=True)
                            self._log_activity(f"Monitoring: {path}")
                    
                    self.observer.start()
                    self.is_monitoring = True
                    self.after(0, self._monitoring_started)
                    
                    for path in self.monitored_paths:
                        if Path(path).exists():
                            try:
                                self.client.scan_and_upload(path, exclusions=self.exclusion_patterns)
                            except Exception as e:
                                self._log_activity(f"Scan error: {e}")
                                
                except Exception as e:
                    self.after(0, lambda: self._monitoring_error(str(e)))
            
            threading.Thread(target=monitor, daemon=True).start()
            
        except Exception as e:
            self._log_activity(f"Error: {e}")
            self._update_status("Error", COLORS["error"])
            messagebox.showerror("Error", f"Failed to start monitoring:\n{e}")
    
    def _monitoring_started(self):
        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self._update_status("Monitoring", COLORS["success"])
        self._log_activity("✓ Monitoring active")
        self.save_config()
    
    def _monitoring_error(self, error: str):
        self._update_status("Error", COLORS["error"])
        self._log_activity(f"✗ Error: {error}")
        messagebox.showerror("Error", f"Monitoring error:\n{error}")
    
    def _stop_monitoring(self):
        try:
            if self.observer:
                self.observer.stop()
                self.observer.join(timeout=5)
                self.observer = None
            
            self.is_monitoring = False
            self.client = None
            
            self.start_btn.configure(state="normal")
            self.stop_btn.configure(state="disabled")
            self._update_status("Stopped", COLORS["warning"])
            self._log_activity("Monitoring stopped")
        except Exception as e:
            self._log_activity(f"Error stopping: {e}")
    
    def _update_status(self, text: str, color: str):
        self.status_text.configure(text=text)
        self.status_dot.configure(text_color=color)
    
    def _log_activity(self, message: str):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.activity_label.configure(text=f"[{timestamp}] {message}")
        # Also send to debug console history
        self._enqueue_debug(f"[UI] {message}\n")

    # ═══════════════════════════════════════════════════════════════
    #   Debug Console
    # ═══════════════════════════════════════════════════════════════

    def _enqueue_debug(self, s: str):
        """Thread-safe: called from any thread (including stdout/stderr)."""
        try:
            self._debug_queue.put_nowait(s)
        except Exception:
            pass

    def _drain_debug_queue(self):
        """UI-thread: render queued debug output and update debug window if open."""
        try:
            while True:
                try:
                    chunk = self._debug_queue.get_nowait()
                except queue.Empty:
                    break

                if not chunk:
                    continue

                self._debug_partial += str(chunk)
                while "\n" in self._debug_partial:
                    line, self._debug_partial = self._debug_partial.split("\n", 1)
                    self._append_debug_line(line)
        finally:
            self.after(150, self._drain_debug_queue)

    def _append_debug_line(self, line: str):
        ts = datetime.now().strftime("%H:%M:%S")
        rendered = f"[{ts}] {line}\n"
        self._debug_history.append(rendered)

        if not self._debug_textbox:
            return

        try:
            self._debug_textbox.insert("end", rendered)
            self._debug_line_count += 1

            # Periodically trim textbox by rebuilding from ring buffer
            if self._debug_line_count > 5200:
                self._debug_textbox.delete("1.0", "end")
                self._debug_textbox.insert("end", "".join(self._debug_history))
                self._debug_line_count = len(self._debug_history)

            if self._debug_autoscroll_var.get():
                self._debug_textbox.see("end")
        except Exception:
            # If widget got destroyed unexpectedly
            self._debug_textbox = None

    def _toggle_debug_window(self):
        if self._debug_window and self._debug_window.winfo_exists():
            self._close_debug_window()
        else:
            self._open_debug_window()

    def _open_debug_window(self):
        if self._debug_window and self._debug_window.winfo_exists():
            self._debug_window.focus()
            return

        win = ctk.CTkToplevel(self)
        win.title("FIMonacci Agent — Debug Console")
        win.geometry("980x540")
        win.minsize(820, 420)
        win.configure(fg_color=COLORS["bg_primary"])
        win.protocol("WM_DELETE_WINDOW", self._close_debug_window)

        # Layout
        win.grid_columnconfigure(0, weight=1)
        win.grid_rowconfigure(1, weight=1)

        top = ctk.CTkFrame(win, fg_color=COLORS["bg_secondary"], corner_radius=12)
        top.grid(row=0, column=0, padx=SPACING["lg"], pady=(SPACING["lg"], SPACING["sm"]), sticky="ew")
        top.grid_columnconfigure(0, weight=1)

        title = ctk.CTkLabel(
            top,
            text="Debug Console (Ctrl+Shift+D)",
            font=ctk.CTkFont(family=FONTS["section"][0], size=FONTS["section"][1], weight=FONTS["section"][2]),
            text_color=COLORS["text_primary"]
        )
        title.grid(row=0, column=0, padx=SPACING["md"], pady=SPACING["sm"], sticky="w")

        controls = ctk.CTkFrame(top, fg_color="transparent")
        controls.grid(row=0, column=1, padx=SPACING["md"], pady=SPACING["sm"], sticky="e")

        autoscroll = ctk.CTkCheckBox(
            controls,
            text="Auto-scroll",
            variable=self._debug_autoscroll_var,
            fg_color=COLORS["pearl_aqua"],
            hover_color=COLORS["frosted_blue"],
            text_color=COLORS["text_secondary"],
            border_color=COLORS["border"],
            corner_radius=4
        )
        autoscroll.pack(side="left", padx=(0, SPACING["sm"]))

        clear_btn = ctk.CTkButton(
            controls,
            text="Clear",
            width=80,
            height=32,
            fg_color=COLORS["bg_tertiary"],
            hover_color=COLORS["bg_hover"],
            text_color=COLORS["text_primary"],
            corner_radius=10,
            command=self._clear_debug_console
        )
        clear_btn.pack(side="left", padx=(0, SPACING["sm"]))

        copy_btn = ctk.CTkButton(
            controls,
            text="Copy",
            width=80,
            height=32,
            fg_color=COLORS["bg_tertiary"],
            hover_color=COLORS["bg_hover"],
            text_color=COLORS["text_primary"],
            corner_radius=10,
            command=self._copy_debug_console
        )
        copy_btn.pack(side="left", padx=(0, SPACING["sm"]))

        save_btn = ctk.CTkButton(
            controls,
            text="Save...",
            width=80,
            height=32,
            fg_color=COLORS["pearl_aqua"],
            hover_color=COLORS["pearl_aqua_hover"],
            text_color=COLORS["text_on_accent"],
            corner_radius=10,
            command=self._save_debug_console
        )
        save_btn.pack(side="left", padx=(0, SPACING["sm"]))

        entropy_btn = ctk.CTkButton(
            controls,
            text="Open entropy log",
            height=32,
            fg_color=COLORS["bg_tertiary"],
            hover_color=COLORS["bg_hover"],
            text_color=COLORS["text_primary"],
            corner_radius=10,
            command=self._open_entropy_log
        )
        entropy_btn.pack(side="left")

        textbox = ctk.CTkTextbox(
            win,
            fg_color=COLORS["bg_card"],
            text_color=COLORS["text_primary"],
            border_color=COLORS["border"],
            border_width=1,
            corner_radius=12,
            font=ctk.CTkFont(family=FONTS["mono"][0], size=11)
        )
        textbox.grid(row=1, column=0, padx=SPACING["lg"], pady=(0, SPACING["lg"]), sticky="nsew")

        # Populate with existing history
        try:
            existing = "".join(self._debug_history)
            if existing:
                textbox.insert("end", existing)
                textbox.see("end")
                self._debug_line_count = len(self._debug_history)
        except Exception:
            pass

        self._debug_window = win
        self._debug_textbox = textbox

    def _close_debug_window(self):
        try:
            if self._debug_window and self._debug_window.winfo_exists():
                self._debug_window.destroy()
        except Exception:
            pass
        self._debug_window = None
        self._debug_textbox = None

    def _clear_debug_console(self):
        self._debug_history.clear()
        self._debug_partial = ""
        self._debug_line_count = 0
        if self._debug_textbox:
            try:
                self._debug_textbox.delete("1.0", "end")
            except Exception:
                pass

    def _copy_debug_console(self):
        try:
            text = "".join(self._debug_history)
            self.clipboard_clear()
            self.clipboard_append(text)
            self._log_activity("Copied debug console to clipboard")
        except Exception as e:
            messagebox.showerror("Copy Failed", f"Could not copy debug text:\n{e}")

    def _save_debug_console(self):
        try:
            path = filedialog.asksaveasfilename(
                title="Save Debug Log",
                defaultextension=".log",
                filetypes=[("Log files", "*.log"), ("Text files", "*.txt"), ("All files", "*.*")]
            )
            if not path:
                return
            with open(path, "w", encoding="utf-8") as f:
                f.write("".join(self._debug_history))
            self._log_activity(f"Saved debug log: {path}")
        except Exception as e:
            messagebox.showerror("Save Failed", f"Could not save debug log:\n{e}")

    def _open_entropy_log(self):
        candidates = [
            APPLICATION_PATH / "entropy_debug.log",
            Path.cwd() / "entropy_debug.log",
        ]
        for p in candidates:
            if p.exists():
                try:
                    os.startfile(str(p))  # Windows
                    return
                except Exception:
                    break
        messagebox.showinfo(
            "Not Found",
            "Could not find 'entropy_debug.log' yet.\n\nIt will appear after entropy is calculated for at least one file."
        )
    
    def load_config(self):
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                self.saved_server_url = config.get('server_url', '')
                self.monitored_paths = config.get('monitored_paths', [])
                self.pii_paths = config.get('pii_paths', [])  # Load PII paths
                self.exclusion_patterns = config.get('exclusion_patterns', [])
                self.saved_autostart = config.get('autostart', False)
                self.saved_minimize = config.get('minimize_to_tray', False)
            except Exception as e:
                print(f"Error loading config: {e}")
    
    def save_config(self):
        config = {
            'server_url': self.server_url_entry.get().strip() if hasattr(self, 'server_url_entry') else '',
            'monitored_paths': self.monitored_paths,
            'pii_paths': self.pii_paths,  # Save PII paths
            'exclusion_patterns': self.exclusion_patterns,
            'autostart': self.autostart_var.get() if hasattr(self, 'autostart_var') else False,
            'minimize_to_tray': self.minimize_var.get() if hasattr(self, 'minimize_var') else False
        }
        try:
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            print(f"Error saving config: {e}")
    
    def _on_closing(self):
        if self.is_monitoring:
            if messagebox.askyesno("Confirm Exit", "Monitoring is active. Stop and exit?"):
                self._stop_monitoring()
                self.save_config()
                # Restore stdout/stderr
                sys.stdout = self._stdout_original
                sys.stderr = self._stderr_original
                self.destroy()
        else:
            self.save_config()
            # Restore stdout/stderr
            sys.stdout = self._stdout_original
            sys.stderr = self._stderr_original
            self.destroy()


class ExclusionDialog(ctk.CTkToplevel):
    """Dialog for adding exclusion patterns"""
    
    def __init__(self, parent):
        super().__init__(parent)
        self.result = None
        
        self.title("Add Exclusion Pattern")
        self.geometry("420x220")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        
        self.configure(fg_color=COLORS["bg_primary"])
        
        # Content
        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=SPACING["xl"], pady=SPACING["xl"])
        
        # Label
        label = ctk.CTkLabel(
            content,
            text="Enter exclusion pattern:",
            font=ctk.CTkFont(family=FONTS["body"][0], size=FONTS["body"][1]),
            text_color=COLORS["text_primary"]
        )
        label.pack(anchor="w", pady=(0, SPACING["xs"]))
        
        # Help text
        help_text = ctk.CTkLabel(
            content,
            text="Examples: *.log, *.tmp, __pycache__, .git, node_modules",
            font=ctk.CTkFont(family=FONTS["small"][0], size=FONTS["small"][1]),
            text_color=COLORS["text_muted"]
        )
        help_text.pack(anchor="w", pady=(0, SPACING["md"]))
        
        # Entry
        self.entry = ctk.CTkEntry(
            content,
            font=ctk.CTkFont(family=FONTS["body"][0], size=FONTS["body"][1]),
            height=SIZES["input_height"],
            fg_color=COLORS["bg_input"],
            border_color=COLORS["border"],
            border_width=2,
            text_color=COLORS["text_primary"],
            corner_radius=SIZES["button_radius"]
        )
        self.entry.pack(fill="x", pady=(0, SPACING["lg"]))
        self.entry.focus()
        self.entry.bind("<Return>", lambda e: self._confirm())
        
        # Buttons
        btn_frame = ctk.CTkFrame(content, fg_color="transparent")
        btn_frame.pack(fill="x")
        
        cancel_btn = ctk.CTkButton(
            btn_frame,
            text="Cancel",
            font=ctk.CTkFont(family=FONTS["button_sm"][0], size=FONTS["button_sm"][1]),
            fg_color=COLORS["bg_tertiary"],
            hover_color=COLORS["bg_hover"],
            text_color=COLORS["text_primary"],
            width=100,
            height=SIZES["button_height"],
            corner_radius=SIZES["button_radius"],
            border_width=1,
            border_color=COLORS["border"],
            command=self.destroy
        )
        cancel_btn.pack(side="right", padx=(SPACING["sm"], 0))
        
        add_btn = ctk.CTkButton(
            btn_frame,
            text="Add Pattern",
            font=ctk.CTkFont(family=FONTS["button_sm"][0], size=FONTS["button_sm"][1]),
            fg_color=COLORS["pearl_aqua"],
            hover_color=COLORS["pearl_aqua_hover"],
            text_color=COLORS["text_on_accent"],
            width=110,
            height=SIZES["button_height"],
            corner_radius=SIZES["button_radius"],
            command=self._confirm
        )
        add_btn.pack(side="right")
        
        # Center dialog
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")
    
    def _confirm(self):
        self.result = self.entry.get()
        self.destroy()


def main():
    app = FIMonacciApp()
    app.mainloop()


if __name__ == "__main__":
    main()
