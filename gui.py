"""
gui.py – Premium dark-themed GUI for Disk Dumper.

© 2026 Murthy Sai Krishna. All rights reserved.
Unauthorized modification or removal of this notice is prohibited.

Built with CustomTkinter for a modern, sleek appearance.
Run: python gui.py  (as Administrator)
"""

import os
import sys
import math
import threading
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk

from disk_utils import (
    is_admin,
    list_physical_disks,
    list_logical_drives,
    _human_readable_size,
)
from gui_dumper import GUIDumper
from hasher import compute_hash_silent, compute_drive_hash_silent, SUPPORTED_ALGORITHMS
from copyright_guard import enforce_copyright, AUTHOR, COPYRIGHT_NOTICE
from themes import get_theme, list_themes, save_preference, load_preference


# ─── Color Theme ──────────────────────────────────────────────────────────────

# Colors are loaded from the saved theme preference (mutable; updated in-place)
_current_theme_name = load_preference()
COLORS = get_theme(_current_theme_name)


# ─── Custom Circular Progress Widget ─────────────────────────────────────────

class CircularProgress(ctk.CTkCanvas):
    """Animated circular progress indicator."""

    def __init__(self, master, size=180, width=12, **kwargs):
        super().__init__(
            master, width=size, height=size,
            bg=COLORS["bg_card"], highlightthickness=0, **kwargs
        )
        self.size = size
        self.line_width = width
        self._progress = 0.0
        self._target = 0.0
        self._animating = False
        self._draw()

    def _draw(self):
        self.delete("all")
        pad = self.line_width + 4
        cx, cy = self.size / 2, self.size / 2
        r = (self.size - 2 * pad) / 2

        # Background circle
        self.create_oval(
            pad, pad, self.size - pad, self.size - pad,
            outline=COLORS["progress_bg"], width=self.line_width
        )

        # Progress arc
        if self._progress > 0:
            extent = self._progress * 360
            self.create_arc(
                pad, pad, self.size - pad, self.size - pad,
                start=90, extent=-extent,
                outline=COLORS["accent"], width=self.line_width,
                style="arc"
            )

        # Glow dot at the end of the arc
        if self._progress > 0.01:
            angle = math.radians(90 - self._progress * 360)
            gx = cx + r * math.cos(angle)
            gy = cy - r * math.sin(angle)
            dot_r = self.line_width / 2 + 2
            self.create_oval(
                gx - dot_r, gy - dot_r, gx + dot_r, gy + dot_r,
                fill=COLORS["accent"], outline=""
            )

        # Center text
        pct_text = f"{self._progress * 100:.1f}%"
        self.create_text(
            cx, cy - 8, text=pct_text,
            fill=COLORS["text_primary"],
            font=("Segoe UI", 28, "bold")
        )
        self.create_text(
            cx, cy + 22, text="Complete",
            fill=COLORS["text_secondary"],
            font=("Segoe UI", 11)
        )

    def set_progress(self, value: float):
        """Set progress 0.0 – 1.0."""
        self._progress = max(0.0, min(1.0, value))
        self._draw()


# ─── Sidebar Button ──────────────────────────────────────────────────────────

class SidebarButton(ctk.CTkButton):
    """Custom sidebar navigation button."""

    def __init__(self, master, text, icon, command=None, **kwargs):
        super().__init__(
            master,
            text=f"  {icon}  {text}",
            command=command,
            anchor="w",
            height=45,
            corner_radius=10,
            font=ctk.CTkFont(family="Segoe UI", size=14),
            fg_color="transparent",
            text_color=COLORS["text_secondary"],
            hover_color=COLORS["bg_hover"],
            **kwargs,
        )
        self._active = False

    def set_active(self, active: bool):
        self._active = active
        if active:
            self.configure(
                fg_color=COLORS["accent_dim"],
                text_color=COLORS["accent"],
            )
        else:
            self.configure(
                fg_color="transparent",
                text_color=COLORS["text_secondary"],
            )


# ─── Main Application ────────────────────────────────────────────────────────

class DiskDumperApp(ctk.CTk):
    """Premium dark-themed Disk Dumper GUI."""

    def __init__(self):
        super().__init__()

        # Window setup
        self.title(f"Disk Dumper – Bit-to-Bit Storage Extractor  •  © {AUTHOR}")
        self.geometry("1100x720")
        self.minsize(950, 650)
        self.configure(fg_color=COLORS["bg_dark"])

        # Center window
        self.update_idletasks()
        x = (self.winfo_screenwidth() - 1100) // 2
        y = (self.winfo_screenheight() - 720) // 2
        self.geometry(f"+{x}+{y}")

        # Fonts
        self.font_title = ctk.CTkFont(family="Segoe UI", size=22, weight="bold")
        self.font_heading = ctk.CTkFont(family="Segoe UI", size=16, weight="bold")
        self.font_body = ctk.CTkFont(family="Segoe UI", size=13)
        self.font_small = ctk.CTkFont(family="Segoe UI", size=11)
        self.font_mono = ctk.CTkFont(family="Consolas", size=12)

        # State
        self.dumper = GUIDumper()
        self.dumper.on_progress = self._on_progress
        self.dumper.on_error = self._on_error
        self.dumper.on_complete = self._on_complete
        self.dumper.on_state_change = self._on_state_change

        self.devices = []  # combined list of physical + logical
        self.selected_device = None

        # Track current theme
        self._theme_name = _current_theme_name

        # Build UI
        self._build_sidebar()
        self._build_pages()
        self._show_page("dashboard")

        # Protocol
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ── Sidebar ───────────────────────────────────────────────────────────

    def _build_sidebar(self):
        self.sidebar = ctk.CTkFrame(
            self, width=220, corner_radius=0,
            fg_color=COLORS["bg_sidebar"],
            border_width=1, border_color=COLORS["border"],
        )
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        # Logo
        logo_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent", height=80)
        logo_frame.pack(fill="x", padx=16, pady=(20, 10))
        logo_frame.pack_propagate(False)

        ctk.CTkLabel(
            logo_frame, text="💾 DISK",
            font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"),
            text_color=COLORS["accent"],
        ).pack(anchor="w")
        ctk.CTkLabel(
            logo_frame, text="    DUMPER",
            font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"),
            text_color=COLORS["text_primary"],
        ).pack(anchor="w")
        ctk.CTkLabel(
            logo_frame, text="v1.0 • Bit-to-Bit Extractor",
            font=self.font_small,
            text_color=COLORS["text_dim"],
        ).pack(anchor="w", pady=(4, 0))

        # Separator
        sep = ctk.CTkFrame(self.sidebar, height=1, fg_color=COLORS["border"])
        sep.pack(fill="x", padx=16, pady=10)

        # Nav buttons
        self.nav_buttons = {}
        nav_items = [
            ("dashboard", "Dashboard", "📊"),
            ("devices",   "Devices",   "💿"),
            ("hash",      "Hash Verify", "🔐"),
            ("log",       "Error Log", "📋"),
            ("settings",  "Settings",  "⚙️"),
        ]
        for key, label, icon in nav_items:
            btn = SidebarButton(
                self.sidebar, text=label, icon=icon,
                command=lambda k=key: self._show_page(k),
            )
            btn.pack(fill="x", padx=12, pady=3)
            self.nav_buttons[key] = btn

        # Bottom status
        spacer = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        spacer.pack(fill="both", expand=True)

        self.status_label = ctk.CTkLabel(
            self.sidebar, text="● Idle",
            font=self.font_small,
            text_color=COLORS["text_dim"],
        )
        self.status_label.pack(padx=16, pady=(0, 8), anchor="w")

        admin_text = "✅ Administrator" if is_admin() else "❌ Not Admin"
        admin_color = COLORS["success"] if is_admin() else COLORS["error"]
        ctk.CTkLabel(
            self.sidebar, text=admin_text,
            font=self.font_small,
            text_color=admin_color,
        ).pack(padx=16, pady=(0, 8), anchor="w")

        # ── Copyright Notice (DO NOT REMOVE) ──────────────────────────────
        sep2 = ctk.CTkFrame(self.sidebar, height=1, fg_color=COLORS["border"])
        sep2.pack(fill="x", padx=16, pady=(4, 8))

        ctk.CTkLabel(
            self.sidebar, text=f"© {AUTHOR}",
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            text_color=COLORS["accent"],
        ).pack(padx=16, pady=(0, 2), anchor="w")
        ctk.CTkLabel(
            self.sidebar, text="All rights reserved.",
            font=ctk.CTkFont(family="Segoe UI", size=9),
            text_color=COLORS["text_dim"],
        ).pack(padx=16, pady=(0, 12), anchor="w")

    # ── Pages Container ───────────────────────────────────────────────────

    def _build_pages(self):
        self.page_container = ctk.CTkFrame(
            self, fg_color=COLORS["bg_dark"], corner_radius=0
        )
        self.page_container.pack(side="right", fill="both", expand=True)

        self.pages = {}
        self._build_dashboard_page()
        self._build_devices_page()
        self._build_hash_page()
        self._build_log_page()
        self._build_settings_page()

    def _show_page(self, name: str):
        for key, btn in self.nav_buttons.items():
            btn.set_active(key == name)
        for page in self.pages.values():
            page.pack_forget()
        self.pages[name].pack(fill="both", expand=True, padx=20, pady=20)

        # Refresh devices on Devices page
        if name == "devices":
            self._refresh_devices()

    # ── Dashboard Page ────────────────────────────────────────────────────

    def _build_dashboard_page(self):
        page = ctk.CTkScrollableFrame(
            self.page_container, fg_color="transparent"
        )
        self.pages["dashboard"] = page

        # Header
        ctk.CTkLabel(
            page, text="Dashboard",
            font=self.font_title,
            text_color=COLORS["text_primary"],
        ).pack(anchor="w", pady=(0, 20))

        # ── Top row: Source + Output config ──
        config_frame = ctk.CTkFrame(page, fg_color="transparent")
        config_frame.pack(fill="x", pady=(0, 16))

        # Source card
        src_card = self._card(config_frame, "Source Device")
        src_card.pack(side="left", fill="both", expand=True, padx=(0, 8))

        self.source_label = ctk.CTkLabel(
            src_card.content, text="No device selected",
            font=self.font_body,
            text_color=COLORS["text_secondary"],
            wraplength=350,
        )
        self.source_label.pack(anchor="w", pady=(4, 8))

        ctk.CTkButton(
            src_card.content, text="Select Device",
            font=self.font_body, height=35,
            fg_color=COLORS["accent_dim"],
            hover_color=COLORS["bg_hover"],
            text_color=COLORS["accent"],
            corner_radius=8,
            command=lambda: self._show_page("devices"),
        ).pack(anchor="w")

        # Output card
        out_card = self._card(config_frame, "Output File")
        out_card.pack(side="right", fill="both", expand=True, padx=(8, 0))

        out_row = ctk.CTkFrame(out_card.content, fg_color="transparent")
        out_row.pack(fill="x", pady=(4, 8))

        self.output_entry = ctk.CTkEntry(
            out_row, placeholder_text="disk_dump.img",
            font=self.font_mono, height=35,
            fg_color=COLORS["bg_input"],
            border_color=COLORS["border"],
            text_color=COLORS["text_primary"],
        )
        self.output_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.output_entry.insert(0, "disk_dump.img")

        ctk.CTkButton(
            out_row, text="Browse", width=80,
            font=self.font_body, height=35,
            fg_color=COLORS["accent_dim"],
            hover_color=COLORS["bg_hover"],
            text_color=COLORS["accent"],
            corner_radius=8,
            command=self._browse_output,
        ).pack(side="right")

        # Format + sector size row
        opt_row = ctk.CTkFrame(out_card.content, fg_color="transparent")
        opt_row.pack(fill="x")

        ctk.CTkLabel(
            opt_row, text="Sector size:",
            font=self.font_small, text_color=COLORS["text_secondary"],
        ).pack(side="left")

        self.sector_var = ctk.StringVar(value="4096")
        ctk.CTkOptionMenu(
            opt_row, values=["512", "4096", "8192", "16384", "65536"],
            variable=self.sector_var, width=100, height=30,
            font=self.font_small,
            fg_color=COLORS["bg_input"],
            button_color=COLORS["accent_dim"],
            button_hover_color=COLORS["bg_hover"],
            dropdown_fg_color=COLORS["bg_card"],
            dropdown_hover_color=COLORS["bg_hover"],
        ).pack(side="left", padx=8)

        # ── Progress Section ──
        progress_frame = ctk.CTkFrame(
            page, fg_color=COLORS["bg_card"],
            corner_radius=14,
            border_width=1, border_color=COLORS["border"],
        )
        progress_frame.pack(fill="x", pady=(0, 16))

        progress_inner = ctk.CTkFrame(progress_frame, fg_color="transparent")
        progress_inner.pack(fill="x", padx=24, pady=24)

        # Left: Circular progress
        left_progress = ctk.CTkFrame(progress_inner, fg_color="transparent")
        left_progress.pack(side="left", padx=(0, 30))

        self.circular_progress = CircularProgress(left_progress, size=180, width=12)
        self.circular_progress.pack()

        # Right: Stats
        right_stats = ctk.CTkFrame(progress_inner, fg_color="transparent")
        right_stats.pack(side="left", fill="both", expand=True)

        stats_grid = ctk.CTkFrame(right_stats, fg_color="transparent")
        stats_grid.pack(fill="x", pady=(10, 0))

        self.stat_labels = {}
        stats = [
            ("speed",   "⚡ Speed",     "0 B/s",     0, 0),
            ("eta",     "⏱ ETA",       "—",          0, 1),
            ("copied",  "📦 Copied",    "0 B",       1, 0),
            ("total",   "📏 Total",     "0 B",       1, 1),
            ("errors",  "⚠ Errors",    "0",          2, 0),
            ("sectors", "🔢 Sectors",   "0",         2, 1),
        ]
        for key, label, default, row, col in stats:
            cell = ctk.CTkFrame(stats_grid, fg_color="transparent")
            cell.grid(row=row, column=col, padx=10, pady=8, sticky="w")
            stats_grid.columnconfigure(col, weight=1, minsize=200)

            ctk.CTkLabel(
                cell, text=label,
                font=self.font_small,
                text_color=COLORS["text_dim"],
            ).pack(anchor="w")
            val = ctk.CTkLabel(
                cell, text=default,
                font=ctk.CTkFont(family="Consolas", size=16, weight="bold"),
                text_color=COLORS["text_primary"],
            )
            val.pack(anchor="w")
            self.stat_labels[key] = val

        # Linear progress bar
        self.progress_bar = ctk.CTkProgressBar(
            progress_frame, height=6,
            fg_color=COLORS["progress_bg"],
            progress_color=COLORS["accent"],
            corner_radius=3,
        )
        self.progress_bar.pack(fill="x", padx=24, pady=(0, 20))
        self.progress_bar.set(0)

        # ── Control Buttons ──
        btn_frame = ctk.CTkFrame(page, fg_color="transparent")
        btn_frame.pack(fill="x", pady=(0, 16))

        self.btn_start = ctk.CTkButton(
            btn_frame, text="▶  Start Dump", width=180, height=48,
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            fg_color=COLORS["btn_start"],
            hover_color=COLORS["btn_start_hover"],
            corner_radius=12,
            command=self._start_dump,
        )
        self.btn_start.pack(side="left", padx=(0, 10))

        self.btn_pause = ctk.CTkButton(
            btn_frame, text="⏸  Pause", width=140, height=48,
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            fg_color=COLORS["btn_pause"],
            hover_color=COLORS["btn_pause_hover"],
            corner_radius=12,
            command=self._toggle_pause,
            state="disabled",
        )
        self.btn_pause.pack(side="left", padx=(0, 10))

        self.btn_stop = ctk.CTkButton(
            btn_frame, text="⏹  Stop", width=140, height=48,
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            fg_color=COLORS["btn_stop"],
            hover_color=COLORS["btn_stop_hover"],
            corner_radius=12,
            command=self._stop_dump,
            state="disabled",
        )
        self.btn_stop.pack(side="left")

        # Resume button (hidden by default)
        self.btn_resume_session = ctk.CTkButton(
            btn_frame, text="🔄  Resume Previous", width=180, height=48,
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            fg_color=COLORS["accent_dim"],
            hover_color=COLORS["bg_hover"],
            text_color=COLORS["accent"],
            corner_radius=12,
            command=self._resume_dump,
        )
        self.btn_resume_session.pack(side="right")

    # ── Devices Page ──────────────────────────────────────────────────────

    def _build_devices_page(self):
        page = ctk.CTkScrollableFrame(
            self.page_container, fg_color="transparent"
        )
        self.pages["devices"] = page

        header = ctk.CTkFrame(page, fg_color="transparent")
        header.pack(fill="x", pady=(0, 16))

        ctk.CTkLabel(
            header, text="Devices",
            font=self.font_title,
            text_color=COLORS["text_primary"],
        ).pack(side="left")

        ctk.CTkButton(
            header, text="🔄  Refresh", width=110, height=35,
            font=self.font_body,
            fg_color=COLORS["accent_dim"],
            hover_color=COLORS["bg_hover"],
            text_color=COLORS["accent"],
            corner_radius=8,
            command=self._refresh_devices,
        ).pack(side="right")

        self.devices_container = ctk.CTkFrame(page, fg_color="transparent")
        self.devices_container.pack(fill="both", expand=True)

    def _refresh_devices(self):
        # Clear existing
        for w in self.devices_container.winfo_children():
            w.destroy()

        self.devices = []

        # Loading indicator
        loading = ctk.CTkLabel(
            self.devices_container, text="Scanning devices…",
            font=self.font_body, text_color=COLORS["text_secondary"],
        )
        loading.pack(pady=20)

        def scan():
            try:
                physical_list = list_physical_disks()
                logical_list = list_logical_drives()
            except Exception as err:
                err_msg = str(err)
                self.after(0, lambda e=err_msg: self._show_device_error(e))
                return

            self.after(0, lambda p=physical_list, l=logical_list: self._display_devices(p, l))

        threading.Thread(target=scan, daemon=True).start()

    def _show_device_error(self, error: str):
        for w in self.devices_container.winfo_children():
            w.destroy()
        ctk.CTkLabel(
            self.devices_container, text=f"Error: {error}",
            font=self.font_body, text_color=COLORS["error"],
        ).pack(pady=20)

    def _display_devices(self, physical, logical):
        for w in self.devices_container.winfo_children():
            w.destroy()
        self.devices = []

        # Physical disks
        if physical:
            ctk.CTkLabel(
                self.devices_container, text="Physical Disks",
                font=self.font_heading,
                text_color=COLORS["text_primary"],
            ).pack(anchor="w", pady=(0, 8))

            for d in physical:
                desc = f"Disk {d['index']} – {d['model']}"
                info = f"{d['size_hr']} • {d['media_type']}"
                self._device_card(d["path"], "💽", desc, info, d["size"])

        # Logical drives
        if logical:
            ctk.CTkLabel(
                self.devices_container, text="Logical Drives",
                font=self.font_heading,
                text_color=COLORS["text_primary"],
            ).pack(anchor="w", pady=(16, 8))

            for d in logical:
                label_str = f" [{d['label']}]" if d["label"] else ""
                desc = f"{d['letter']}:{label_str} Drive"
                info = f"{d['size_hr']} • {d['file_system']} • {d['drive_type']}"
                icon = "💿" if d["drive_type"] == "Fixed" else "🔌"
                self._device_card(d["path"], icon, desc, info, d["size"])

    def _device_card(self, path, icon, desc, info, size):
        self.devices.append({"path": path, "desc": desc, "size": size})

        card = ctk.CTkFrame(
            self.devices_container,
            fg_color=COLORS["bg_card"],
            corner_radius=10,
            border_width=1,
            border_color=COLORS["border"],
            height=70,
        )
        card.pack(fill="x", pady=4)
        card.pack_propagate(False)

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=16, pady=10)

        # Icon + text
        left = ctk.CTkFrame(inner, fg_color="transparent")
        left.pack(side="left", fill="y")

        ctk.CTkLabel(
            left, text=f"{icon}  {desc}",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            text_color=COLORS["text_primary"],
        ).pack(anchor="w")
        ctk.CTkLabel(
            left, text=f"{path} • {info}",
            font=self.font_small,
            text_color=COLORS["text_secondary"],
        ).pack(anchor="w")

        # Select button
        ctk.CTkButton(
            inner, text="Select", width=90, height=32,
            font=self.font_body,
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            text_color=COLORS["bg_dark"],
            corner_radius=8,
            command=lambda p=path, d=desc: self._select_device(p, d),
        ).pack(side="right")

    def _select_device(self, path: str, desc: str):
        self.selected_device = {"path": path, "desc": desc}
        self.source_label.configure(
            text=f"✅  {desc}\n     {path}",
            text_color=COLORS["success"],
        )
        self._show_page("dashboard")

    # ── Hash Page ─────────────────────────────────────────────────────────

    def _build_hash_page(self):
        page = ctk.CTkScrollableFrame(
            self.page_container, fg_color="transparent"
        )
        self.pages["hash"] = page

        ctk.CTkLabel(
            page, text="Hash Verification",
            font=self.font_title,
            text_color=COLORS["text_primary"],
        ).pack(anchor="w", pady=(0, 20))

        card = self._card(page, "Compute Hash")
        card.pack(fill="x", pady=(0, 16))

        # ── Source type toggle ─────────────────────────────────────────────
        source_row = ctk.CTkFrame(card.content, fg_color="transparent")
        source_row.pack(fill="x", pady=(8, 12))

        ctk.CTkLabel(
            source_row, text="Source:",
            font=self.font_body, text_color=COLORS["text_secondary"],
        ).pack(side="left", padx=(0, 10))

        self.hash_source_var = ctk.StringVar(value="📄 File")
        self.hash_source_toggle = ctk.CTkSegmentedButton(
            source_row, values=["📄 File", "💽 Drive"],
            variable=self.hash_source_var,
            font=self.font_body,
            fg_color=COLORS["bg_input"],
            selected_color=COLORS["accent"],
            selected_hover_color=COLORS["accent_hover"],
            unselected_color=COLORS["bg_card"],
            unselected_hover_color=COLORS["bg_hover"],
            text_color=COLORS["bg_dark"],
            text_color_disabled=COLORS["text_secondary"],
            command=self._on_hash_source_change,
        )
        self.hash_source_toggle.pack(side="left")

        # ── File selection row ─────────────────────────────────────────────
        self.hash_file_row = ctk.CTkFrame(card.content, fg_color="transparent")
        self.hash_file_row.pack(fill="x", pady=(0, 12))

        self.hash_file_entry = ctk.CTkEntry(
            self.hash_file_row, placeholder_text="Path to image file…",
            font=self.font_mono, height=38,
            fg_color=COLORS["bg_input"],
            border_color=COLORS["border"],
            text_color=COLORS["text_primary"],
        )
        self.hash_file_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))

        ctk.CTkButton(
            self.hash_file_row, text="Browse", width=80, height=38,
            font=self.font_body,
            fg_color=COLORS["accent_dim"],
            hover_color=COLORS["bg_hover"],
            text_color=COLORS["accent"],
            corner_radius=8,
            command=self._browse_hash_file,
        ).pack(side="right")

        # ── Drive selection row (hidden by default) ────────────────────────
        self.hash_drive_row = ctk.CTkFrame(card.content, fg_color="transparent")
        # Not packed initially – toggled by _on_hash_source_change

        ctk.CTkLabel(
            self.hash_drive_row, text="Drive:",
            font=self.font_body, text_color=COLORS["text_secondary"],
        ).pack(side="left", padx=(0, 10))

        self.hash_drive_var = ctk.StringVar(value="Select a drive…")
        self.hash_drive_paths = {}  # display_name → device_path
        self.hash_drive_menu = ctk.CTkOptionMenu(
            self.hash_drive_row, values=["Select a drive…"],
            variable=self.hash_drive_var, width=380, height=38,
            font=self.font_body,
            fg_color=COLORS["bg_input"],
            button_color=COLORS["accent_dim"],
            button_hover_color=COLORS["bg_hover"],
            dropdown_fg_color=COLORS["bg_card"],
            dropdown_hover_color=COLORS["bg_hover"],
        )
        self.hash_drive_menu.pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            self.hash_drive_row, text="🔄 Refresh", width=90, height=38,
            font=self.font_body,
            fg_color=COLORS["accent_dim"],
            hover_color=COLORS["bg_hover"],
            text_color=COLORS["accent"],
            corner_radius=8,
            command=self._refresh_hash_drives,
        ).pack(side="right")

        # ── Algorithm + Compute button ─────────────────────────────────────
        algo_row = ctk.CTkFrame(card.content, fg_color="transparent")
        algo_row.pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(
            algo_row, text="Algorithm:",
            font=self.font_body, text_color=COLORS["text_secondary"],
        ).pack(side="left")

        self.hash_algo_var = ctk.StringVar(value="sha256")
        ctk.CTkOptionMenu(
            algo_row, values=["sha256", "md5"],
            variable=self.hash_algo_var, width=120, height=35,
            font=self.font_body,
            fg_color=COLORS["bg_input"],
            button_color=COLORS["accent_dim"],
            dropdown_fg_color=COLORS["bg_card"],
        ).pack(side="left", padx=10)

        ctk.CTkButton(
            algo_row, text="🔐  Compute Hash",
            width=160, height=38,
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            text_color=COLORS["bg_dark"],
            corner_radius=8,
            command=self._compute_hash,
        ).pack(side="right")

        # ── Result + Copy button ───────────────────────────────────────────
        result_row = ctk.CTkFrame(card.content, fg_color="transparent")
        result_row.pack(fill="x", pady=(8, 0))

        self.hash_result_label = ctk.CTkLabel(
            result_row, text="",
            font=self.font_mono,
            text_color=COLORS["text_primary"],
            wraplength=520,
        )
        self.hash_result_label.pack(side="left", anchor="w", fill="x", expand=True)

        self.btn_copy_hash = ctk.CTkButton(
            result_row, text="📋 Copy", width=90, height=32,
            font=self.font_body,
            fg_color=COLORS["accent_dim"],
            hover_color=COLORS["bg_hover"],
            text_color=COLORS["accent"],
            corner_radius=8,
            command=self._copy_hash,
            state="disabled",
        )
        self.btn_copy_hash.pack(side="right", padx=(8, 0))

        # ── Compare section ────────────────────────────────────────────────
        compare_card = self._card(page, "Compare Hash")
        compare_card.pack(fill="x")

        self.expected_hash_entry = ctk.CTkEntry(
            compare_card.content,
            placeholder_text="Paste expected hash here…",
            font=self.font_mono, height=38,
            fg_color=COLORS["bg_input"],
            border_color=COLORS["border"],
            text_color=COLORS["text_primary"],
        )
        self.expected_hash_entry.pack(fill="x", pady=(8, 8))

        self.compare_result = ctk.CTkLabel(
            compare_card.content, text="",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
        )
        self.compare_result.pack(anchor="w")

        ctk.CTkButton(
            compare_card.content, text="Compare",
            width=120, height=35,
            font=self.font_body,
            fg_color=COLORS["accent_dim"],
            hover_color=COLORS["bg_hover"],
            text_color=COLORS["accent"],
            corner_radius=8,
            command=self._compare_hash,
        ).pack(anchor="w", pady=(4, 0))

    def _on_hash_source_change(self, value):
        """Toggle between File and Drive input rows."""
        if "File" in value:
            self.hash_drive_row.pack_forget()
            self.hash_file_row.pack(fill="x", pady=(0, 12),
                                    after=self.hash_source_toggle.master)
        else:
            self.hash_file_row.pack_forget()
            self.hash_drive_row.pack(fill="x", pady=(0, 12),
                                     after=self.hash_source_toggle.master)
            self._refresh_hash_drives()

    def _refresh_hash_drives(self):
        """Populate the drive dropdown with physical + logical drives."""
        def scan():
            try:
                physical = list_physical_disks()
                logical = list_logical_drives()
            except Exception as err:
                self.after(0, lambda e=str(err): self.hash_drive_var.set(f"Error: {e}"))
                return

            names = []
            paths = {}
            for d in physical:
                name = f"💽 Disk {d['index']} – {d['model']} ({d['size_hr']})"
                names.append(name)
                paths[name] = d["path"]
            for d in logical:
                label_str = f" [{d['label']}]" if d["label"] else ""
                name = f"💿 {d['letter']}:{label_str} ({d['size_hr']}, {d['file_system']})"
                names.append(name)
                paths[name] = d["path"]

            def update():
                self.hash_drive_paths = paths
                if names:
                    self.hash_drive_menu.configure(values=names)
                    self.hash_drive_var.set(names[0])
                else:
                    self.hash_drive_menu.configure(values=["No drives found"])
                    self.hash_drive_var.set("No drives found")

            self.after(0, update)

        threading.Thread(target=scan, daemon=True).start()

    def _copy_hash(self):
        """Copy the computed hash digest to the clipboard."""
        text = self.hash_result_label.cget("text")
        if text and ":" in text:
            digest = text.split(":", 1)[1].strip()
            self.clipboard_clear()
            self.clipboard_append(digest)
            # Brief visual feedback
            self.btn_copy_hash.configure(text="✅ Copied!")
            self.after(1500, lambda: self.btn_copy_hash.configure(text="📋 Copy"))

    # ── Log Page ──────────────────────────────────────────────────────────

    def _build_log_page(self):
        page = ctk.CTkFrame(self.page_container, fg_color="transparent")
        self.pages["log"] = page

        ctk.CTkLabel(
            page, text="Error Log",
            font=self.font_title,
            text_color=COLORS["text_primary"],
        ).pack(anchor="w", pady=(0, 16))

        self.log_text = ctk.CTkTextbox(
            page, font=self.font_mono, height=500,
            fg_color=COLORS["bg_card"],
            border_color=COLORS["border"],
            border_width=1,
            text_color=COLORS["text_secondary"],
            corner_radius=10,
        )
        self.log_text.pack(fill="both", expand=True)
        self.log_text.insert("1.0", "No errors logged yet.\n")
        self.log_text.configure(state="disabled")

    # ── Settings Page ─────────────────────────────────────────────────────

    def _build_settings_page(self):
        page = ctk.CTkScrollableFrame(
            self.page_container, fg_color="transparent"
        )
        self.pages["settings"] = page

        ctk.CTkLabel(
            page, text="Settings",
            font=self.font_title,
            text_color=COLORS["text_primary"],
        ).pack(anchor="w", pady=(0, 8))

        ctk.CTkLabel(
            page, text="Choose a color theme for the interface.",
            font=self.font_body,
            text_color=COLORS["text_secondary"],
        ).pack(anchor="w", pady=(0, 20))

        # Theme cards grid
        grid = ctk.CTkFrame(page, fg_color="transparent")
        grid.pack(fill="x")

        for idx, theme_name in enumerate(list_themes()):
            palette = get_theme(theme_name)
            is_active = (theme_name == self._theme_name)

            card = ctk.CTkFrame(
                grid,
                fg_color=COLORS["bg_card"] if not is_active else COLORS["accent_dim"],
                corner_radius=14,
                border_width=2,
                border_color=COLORS["accent"] if is_active else COLORS["border"],
            )
            card.grid(row=idx // 2, column=idx % 2, padx=8, pady=8, sticky="nsew")
            grid.columnconfigure(idx % 2, weight=1)

            inner = ctk.CTkFrame(card, fg_color="transparent")
            inner.pack(fill="both", expand=True, padx=16, pady=14)

            # Title row
            title_row = ctk.CTkFrame(inner, fg_color="transparent")
            title_row.pack(fill="x", pady=(0, 10))

            active_marker = "  ✓ Active" if is_active else ""
            ctk.CTkLabel(
                title_row, text=f"{theme_name}{active_marker}",
                font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
                text_color=COLORS["accent"] if is_active else COLORS["text_primary"],
            ).pack(side="left")

            # Color swatches
            swatch_row = ctk.CTkFrame(inner, fg_color="transparent")
            swatch_row.pack(fill="x", pady=(0, 10))

            swatch_keys = ["bg_dark", "bg_card", "accent", "accent_dim",
                           "text_primary", "success", "warning", "error"]
            for key in swatch_keys:
                color = palette.get(key, "#888")
                sw = ctk.CTkFrame(
                    swatch_row, width=28, height=28,
                    fg_color=color, corner_radius=6,
                    border_width=1, border_color=palette.get("border", "#444"),
                )
                sw.pack(side="left", padx=2)

            # Apply button
            if not is_active:
                ctk.CTkButton(
                    inner, text="Apply", width=90, height=32,
                    font=self.font_body,
                    fg_color=palette["accent"],
                    hover_color=palette["accent_hover"],
                    text_color=palette["bg_dark"],
                    corner_radius=8,
                    command=lambda n=theme_name: self._apply_theme(n),
                ).pack(anchor="w")
            else:
                ctk.CTkLabel(
                    inner, text="Currently active",
                    font=self.font_small,
                    text_color=COLORS["text_dim"],
                ).pack(anchor="w")

    # ── Theme Application ─────────────────────────────────────────────────

    def _apply_theme(self, theme_name: str):
        """Switch to a new theme and rebuild the entire UI."""
        global _current_theme_name
        _current_theme_name = theme_name
        self._theme_name = theme_name
        COLORS.update(get_theme(theme_name))
        save_preference(theme_name)
        self._rebuild_ui()

    def _rebuild_ui(self):
        """Destroy and rebuild all UI elements with the current COLORS."""
        # Preserve runtime state
        selected_device = self.selected_device
        output_text = self.output_entry.get() if hasattr(self, "output_entry") else "disk_dump.img"
        sector_val = self.sector_var.get() if hasattr(self, "sector_var") else "4096"

        # Determine light vs dark appearance
        is_light = COLORS["bg_dark"].lower() in ("#f0f2f5", "#ffffff", "#fafafa")
        ctk.set_appearance_mode("light" if is_light else "dark")

        # Update window bg
        self.configure(fg_color=COLORS["bg_dark"])

        # Destroy existing UI
        self.sidebar.destroy()
        self.page_container.destroy()

        # Rebuild
        self._build_sidebar()
        self._build_pages()

        # Restore state
        self.selected_device = selected_device
        if selected_device:
            self.source_label.configure(
                text=f"✅  {selected_device['desc']}\n     {selected_device['path']}",
                text_color=COLORS["success"],
            )
        self.output_entry.delete(0, "end")
        self.output_entry.insert(0, output_text)
        self.sector_var.set(sector_val)

        # Show settings page so user sees the result
        self._show_page("settings")

    # ── Helpers ───────────────────────────────────────────────────────────

    def _card(self, parent, title: str) -> ctk.CTkFrame:
        """Create a styled card with a heading. Access .content to add children."""
        frame = ctk.CTkFrame(
            parent, fg_color=COLORS["bg_card"],
            corner_radius=14,
            border_width=1, border_color=COLORS["border"],
        )
        inner = ctk.CTkFrame(frame, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=20, pady=16)

        ctk.CTkLabel(
            inner, text=title,
            font=self.font_heading,
            text_color=COLORS["text_primary"],
        ).pack(anchor="w")

        frame.content = inner
        return frame

    def _browse_output(self):
        path = filedialog.asksaveasfilename(
            title="Save Disk Image As",
            defaultextension=".img",
            filetypes=[
                ("Disk Image", "*.img"),
                ("Raw Image", "*.raw"),
                ("DD Image", "*.dd"),
                ("All files", "*.*"),
            ],
        )
        if path:
            self.output_entry.delete(0, "end")
            self.output_entry.insert(0, path)

    def _browse_hash_file(self):
        path = filedialog.askopenfilename(
            title="Select Image File",
            filetypes=[
                ("Disk Images", "*.img *.raw *.dd"),
                ("All files", "*.*"),
            ],
        )
        if path:
            self.hash_file_entry.delete(0, "end")
            self.hash_file_entry.insert(0, path)

    # ── Dump Actions ──────────────────────────────────────────────────────

    def _start_dump(self):
        if not self.selected_device:
            messagebox.showwarning("No Device", "Please select a source device first.")
            return

        output = self.output_entry.get().strip()
        if not output:
            messagebox.showwarning("No Output", "Please specify an output file path.")
            return

        if os.path.isfile(output):
            if not messagebox.askyesno("Overwrite?", f"File '{output}' exists. Overwrite?"):
                return

        sector = int(self.sector_var.get())

        # Reset UI
        self.circular_progress.set_progress(0)
        self.progress_bar.set(0)
        stat_defaults = {
            "speed": "0 B/s", "eta": "—", "copied": "0 B",
            "total": "0 B", "errors": "0", "sectors": "0",
        }
        for key, label in self.stat_labels.items():
            label.configure(text=stat_defaults.get(key, "0"))
        self._clear_log()

        # Buttons
        self.btn_start.configure(state="disabled")
        self.btn_pause.configure(state="normal", text="⏸  Pause")
        self.btn_stop.configure(state="normal")

        self.dumper.start(
            self.selected_device["path"], output,
            sector_size=sector, resume=False,
        )

    def _resume_dump(self):
        output = self.output_entry.get().strip()
        if not output:
            messagebox.showwarning("No Output", "Enter the output file path to resume.")
            return

        state = GUIDumper.check_resume(output)
        if not state:
            messagebox.showinfo("No State", f"No resume state found for:\n{output}")
            return

        self.selected_device = {"path": state["source"], "desc": state["source"]}
        self.source_label.configure(
            text=f"🔄  Resuming: {state['source']}",
            text_color=COLORS["warning"],
        )

        # Buttons
        self.btn_start.configure(state="disabled")
        self.btn_pause.configure(state="normal", text="⏸  Pause")
        self.btn_stop.configure(state="normal")

        self.dumper.start(
            state["source"], output,
            sector_size=state.get("sector_size", 4096),
            resume=True,
        )

    def _toggle_pause(self):
        if self.dumper.state == "running":
            self.dumper.pause()
            self.btn_pause.configure(text="▶  Resume")
        elif self.dumper.state == "paused":
            self.dumper.resume()
            self.btn_pause.configure(text="⏸  Pause")

    def _stop_dump(self):
        if messagebox.askyesno("Stop Dump", "Stop the dump? State will be saved for resume."):
            self.dumper.stop()

    # ── Callbacks (from background thread → GUI via after) ────────────────

    def _on_progress(self, offset, total, speed, eta, errors):
        self.after(0, lambda: self._update_progress(offset, total, speed, eta, errors))

    def _on_error(self, offset, error_msg):
        self.after(0, lambda: self._append_log(
            f"[{__import__('time').strftime('%H:%M:%S')}] Offset 0x{offset:X}: {error_msg}"
        ))

    def _on_complete(self, success, message):
        self.after(0, lambda: self._dump_finished(success, message))

    def _on_state_change(self, state):
        state_labels = {
            "idle": "● Idle",
            "running": "● Running",
            "paused": "● Paused",
            "done": "● Complete",
        }
        colors = {
            "idle": COLORS["text_dim"],
            "running": COLORS["success"],
            "paused": COLORS["warning"],
            "done": COLORS["accent"],
        }
        self.after(0, lambda: self.status_label.configure(
            text=state_labels.get(state, f"● {state}"),
            text_color=colors.get(state, COLORS["text_dim"]),
        ))

    def _update_progress(self, offset, total, speed, eta, errors):
        pct = offset / total if total > 0 else 0

        self.circular_progress.set_progress(pct)
        self.progress_bar.set(pct)

        self.stat_labels["speed"].configure(text=f"{_human_readable_size(int(speed))}/s")
        self.stat_labels["copied"].configure(text=_human_readable_size(offset))
        self.stat_labels["total"].configure(text=_human_readable_size(total))
        self.stat_labels["errors"].configure(
            text=str(errors),
            text_color=COLORS["error"] if errors > 0 else COLORS["text_primary"],
        )

        sector_size = int(self.sector_var.get())
        sectors = offset // sector_size
        self.stat_labels["sectors"].configure(text=f"{sectors:,}")

        # ETA formatting
        if eta > 0:
            minutes, seconds = divmod(int(eta), 60)
            hours, minutes = divmod(minutes, 60)
            if hours > 0:
                eta_str = f"{hours}h {minutes}m {seconds}s"
            elif minutes > 0:
                eta_str = f"{minutes}m {seconds}s"
            else:
                eta_str = f"{seconds}s"
        else:
            eta_str = "—"
        self.stat_labels["eta"].configure(text=eta_str)

    def _dump_finished(self, success, message):
        self.btn_start.configure(state="normal")
        self.btn_pause.configure(state="disabled", text="⏸  Pause")
        self.btn_stop.configure(state="disabled")

        if success:
            self.circular_progress.set_progress(1.0)
            self.progress_bar.set(1.0)
            messagebox.showinfo("✅ Dump Complete", message)
        else:
            messagebox.showwarning("Dump Stopped", message)

    # ── Hash Actions ──────────────────────────────────────────────────────

    def _compute_hash(self):
        source_mode = self.hash_source_var.get()
        algo = self.hash_algo_var.get()

        if "File" in source_mode:
            # File mode
            file_path = self.hash_file_entry.get().strip()
            if not file_path or not os.path.isfile(file_path):
                messagebox.showwarning("File Not Found", "Please select a valid file.")
                return
            target = file_path
            use_drive = False
        else:
            # Drive mode
            selected = self.hash_drive_var.get()
            device_path = self.hash_drive_paths.get(selected)
            if not device_path:
                messagebox.showwarning("No Drive", "Please select a valid drive.")
                return
            target = device_path
            use_drive = True

        self.hash_result_label.configure(text="Computing…", text_color=COLORS["warning"])
        self.btn_copy_hash.configure(state="disabled")

        def run():
            try:
                if use_drive:
                    digest = compute_drive_hash_silent(target, algo)
                else:
                    digest = compute_hash_silent(target, algo)

                def on_done(d=digest):
                    self.hash_result_label.configure(
                        text=f"{algo.upper()}: {d}",
                        text_color=COLORS["accent"],
                    )
                    self.btn_copy_hash.configure(state="normal")

                self.after(0, on_done)
            except Exception as err:
                err_msg = str(err)
                self.after(0, lambda e=err_msg: self.hash_result_label.configure(
                    text=f"Error: {e}",
                    text_color=COLORS["error"],
                ))

        threading.Thread(target=run, daemon=True).start()

    def _compare_hash(self):
        computed = self.hash_result_label.cget("text")
        expected = self.expected_hash_entry.get().strip()

        if not computed or ":" not in computed:
            self.compare_result.configure(
                text="⚠ Compute a hash first",
                text_color=COLORS["warning"],
            )
            return
        if not expected:
            self.compare_result.configure(
                text="⚠ Enter expected hash",
                text_color=COLORS["warning"],
            )
            return

        digest = computed.split(":", 1)[1].strip()
        if digest.lower() == expected.lower():
            self.compare_result.configure(
                text="✅ Hashes MATCH!",
                text_color=COLORS["success"],
            )
        else:
            self.compare_result.configure(
                text="❌ Hashes DO NOT match!",
                text_color=COLORS["error"],
            )

    # ── Log ───────────────────────────────────────────────────────────────

    def _append_log(self, text: str):
        self.log_text.configure(state="normal")
        # Clear default message
        current = self.log_text.get("1.0", "end").strip()
        if current == "No errors logged yet.":
            self.log_text.delete("1.0", "end")
        self.log_text.insert("end", text + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _clear_log(self):
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.insert("1.0", "No errors logged yet.\n")
        self.log_text.configure(state="disabled")

    # ── Close ─────────────────────────────────────────────────────────────

    def _on_close(self):
        if self.dumper.is_running():
            if messagebox.askyesno(
                "Dump in Progress",
                "A dump is in progress. Stop and save state before exiting?"
            ):
                self.dumper.stop()
                self.after(1000, self.destroy)
            return
        self.destroy()


# ─── Entry Point ──────────────────────────────────────────────────────────────

def main():
    # Copyright integrity check – DO NOT REMOVE
    enforce_copyright(is_gui=True)

    # Admin check
    if not is_admin():
        # Need a temp Tk root for messagebox to work before CTk is created
        _root = tk.Tk()
        _root.withdraw()
        messagebox.showwarning(
            "Administrator Required",
            "Disk Dumper needs Administrator privileges to access raw disk sectors.\n\n"
            "Please right-click your terminal / IDE and select 'Run as Administrator'.",
        )
        _root.destroy()
        sys.exit(1)

    # Determine appearance from saved theme
    saved = load_preference()
    is_light = get_theme(saved)["bg_dark"].lower() in ("#f0f2f5", "#ffffff", "#fafafa")
    ctk.set_appearance_mode("light" if is_light else "dark")
    ctk.set_default_color_theme("dark-blue")

    app = DiskDumperApp()
    app.mainloop()


if __name__ == "__main__":
    main()
