"""
themes.py – Color theme definitions and preference persistence for Disk Dumper GUI.

© 2026 Murthy Sai Krishna. All rights reserved.
Unauthorized modification or removal of this notice is prohibited.

Provides multiple color palettes that can be swapped at runtime.
"""

import json
import os

# ─── Preference File ─────────────────────────────────────────────────────────

_PREF_PATH = os.path.join(os.path.expanduser("~"), ".diskdumper_theme.json")
DEFAULT_THEME = "Emerald Night"


# ─── Theme Definitions ───────────────────────────────────────────────────────

THEMES: dict[str, dict[str, str]] = {

    # ── 1. Emerald Night (original) ──────────────────────────────────────
    "Emerald Night": {
        "bg_dark":          "#0d1117",
        "bg_card":          "#161b22",
        "bg_sidebar":       "#0d1117",
        "bg_hover":         "#1c2333",
        "bg_input":         "#1c2333",
        "border":           "#30363d",
        "accent":           "#00d4aa",
        "accent_hover":     "#00f0c0",
        "accent_dim":       "#0a3d35",
        "text_primary":     "#f0f6fc",
        "text_secondary":   "#8b949e",
        "text_dim":         "#484f58",
        "success":          "#3fb950",
        "warning":          "#d29922",
        "error":            "#f85149",
        "blue":             "#58a6ff",
        "purple":           "#bc8cff",
        "progress_bg":      "#1c2333",
        "progress_fill":    "#00d4aa",
        "btn_start":        "#238636",
        "btn_start_hover":  "#2ea043",
        "btn_pause":        "#9e6a03",
        "btn_pause_hover":  "#bb8009",
        "btn_stop":         "#da3633",
        "btn_stop_hover":   "#f85149",
    },

    # ── 2. Ocean Blue ────────────────────────────────────────────────────
    "Ocean Blue": {
        "bg_dark":          "#0b1222",
        "bg_card":          "#111d2e",
        "bg_sidebar":       "#0b1222",
        "bg_hover":         "#162a42",
        "bg_input":         "#162a42",
        "border":           "#1e3a5f",
        "accent":           "#4ea8f0",
        "accent_hover":     "#6dc0ff",
        "accent_dim":       "#132d4a",
        "text_primary":     "#e8f0fa",
        "text_secondary":   "#8aa4c0",
        "text_dim":         "#4a6580",
        "success":          "#3fb950",
        "warning":          "#e0a020",
        "error":            "#f85149",
        "blue":             "#4ea8f0",
        "purple":           "#b490f0",
        "progress_bg":      "#162a42",
        "progress_fill":    "#4ea8f0",
        "btn_start":        "#1a7a3a",
        "btn_start_hover":  "#229a48",
        "btn_pause":        "#9e6a03",
        "btn_pause_hover":  "#bb8009",
        "btn_stop":         "#c53030",
        "btn_stop_hover":   "#e04040",
    },

    # ── 3. Crimson Dark ──────────────────────────────────────────────────
    "Crimson Dark": {
        "bg_dark":          "#140a0e",
        "bg_card":          "#1e1015",
        "bg_sidebar":       "#140a0e",
        "bg_hover":         "#2c1520",
        "bg_input":         "#2c1520",
        "border":           "#4a2030",
        "accent":           "#ff5577",
        "accent_hover":     "#ff7799",
        "accent_dim":       "#3d1525",
        "text_primary":     "#f5e8ec",
        "text_secondary":   "#b08898",
        "text_dim":         "#6a4555",
        "success":          "#4aca6a",
        "warning":          "#f0aa30",
        "error":            "#ff4444",
        "blue":             "#5dadec",
        "purple":           "#c488f0",
        "progress_bg":      "#2c1520",
        "progress_fill":    "#ff5577",
        "btn_start":        "#2a8a40",
        "btn_start_hover":  "#35a850",
        "btn_pause":        "#aa7010",
        "btn_pause_hover":  "#cc8820",
        "btn_stop":         "#cc2233",
        "btn_stop_hover":   "#ee3344",
    },

    # ── 4. Amber Glow ────────────────────────────────────────────────────
    "Amber Glow": {
        "bg_dark":          "#12100a",
        "bg_card":          "#1c1810",
        "bg_sidebar":       "#12100a",
        "bg_hover":         "#2a2418",
        "bg_input":         "#2a2418",
        "border":           "#44381e",
        "accent":           "#f0a830",
        "accent_hover":     "#ffc050",
        "accent_dim":       "#3a2e10",
        "text_primary":     "#f5f0e0",
        "text_secondary":   "#b0a080",
        "text_dim":         "#6a6040",
        "success":          "#50b860",
        "warning":          "#f0a830",
        "error":            "#e84040",
        "blue":             "#60aae0",
        "purple":           "#b888e0",
        "progress_bg":      "#2a2418",
        "progress_fill":    "#f0a830",
        "btn_start":        "#2a7a30",
        "btn_start_hover":  "#359840",
        "btn_pause":        "#a07010",
        "btn_pause_hover":  "#c08820",
        "btn_stop":         "#c03030",
        "btn_stop_hover":   "#e04040",
    },

    # ── 5. Light Mode ────────────────────────────────────────────────────
    "Light Mode": {
        "bg_dark":          "#f0f2f5",
        "bg_card":          "#ffffff",
        "bg_sidebar":       "#e8eaef",
        "bg_hover":         "#dce0e8",
        "bg_input":         "#f5f6f8",
        "border":           "#c8ccd4",
        "accent":           "#0066cc",
        "accent_hover":     "#0080f0",
        "accent_dim":       "#d0e4f8",
        "text_primary":     "#1a1a2e",
        "text_secondary":   "#555570",
        "text_dim":         "#8888a0",
        "success":          "#1a8a35",
        "warning":          "#b07810",
        "error":            "#cc2020",
        "blue":             "#2070cc",
        "purple":           "#7040b0",
        "progress_bg":      "#dce0e8",
        "progress_fill":    "#0066cc",
        "btn_start":        "#1a8a35",
        "btn_start_hover":  "#22a845",
        "btn_pause":        "#b07810",
        "btn_pause_hover":  "#d09018",
        "btn_stop":         "#cc2020",
        "btn_stop_hover":   "#e83030",
    },
}


# ─── Public API ───────────────────────────────────────────────────────────────

def list_themes() -> list[str]:
    """Return the names of all available themes."""
    return list(THEMES.keys())


def get_theme(name: str) -> dict[str, str]:
    """Return the color palette for *name*, falling back to default."""
    return THEMES.get(name, THEMES[DEFAULT_THEME]).copy()


def save_preference(name: str) -> None:
    """Persist the chosen theme name to disk."""
    try:
        with open(_PREF_PATH, "w") as f:
            json.dump({"theme": name}, f)
    except OSError:
        pass


def load_preference() -> str:
    """Load the saved theme name, or return the default."""
    try:
        with open(_PREF_PATH, "r") as f:
            data = json.load(f)
            name = data.get("theme", DEFAULT_THEME)
            if name in THEMES:
                return name
    except (OSError, json.JSONDecodeError, KeyError):
        pass
    return DEFAULT_THEME
